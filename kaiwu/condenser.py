"""上下文压缩引擎 — 将长历史压缩为结构化摘要

基于 OpenHands Context Condensation + ACON 论文方案：
- 超阈值触发（默认 15 轮）
- 生成四段结构化摘要：目标/进度/决策/待处理
- 最近 5 轮保留原文，不压缩
- 长观察（工具输出、文件树等）本地压缩，零 token 消耗
"""

import json
import re
from typing import Any

from loguru import logger

from kaiwu.config import (
    CONDENSE_THRESHOLD,
    CONDENSE_KEEP_RECENT,
    MAX_OBSERVATION_TOKENS,
    DEFAULT_TIMEOUT,
)
from kaiwu.llm_client import call_llm
from kaiwu.quota import check_quota, record_call

# ── 压缩提示词 ──────────────────────────────────────────────────────

_CONDENSE_SYSTEM = """\
你是一位软件项目助手，负责将 AI 编程助手的工作历史压缩为结构化摘要。

# 输出要求

严格以 JSON 格式返回：

```json
{
  "task_goal": "任务的最终目标（一句话）",
  "progress_summary": "已完成的工作摘要（不超过 150 字）",
  "anchors": [
    "技术决策1：如 框架: FastAPI",
    "技术决策2：如 数据库: SQLite，路径 ./data/app.db",
    "约定3：如 编码规范: 所有文件 UTF-8"
  ],
  "pending_issues": [
    "尚未解决的问题或待完成的子任务"
  ],
  "key_files": ["涉及的关键文件路径列表"]
}
```

# 原则

1. anchors 是最重要的——记录所有已做的技术决策，后续步骤必须遵守
2. anchors 每条不超过 50 字，格式："类别: 具体内容"
3. pending_issues 列出当前阻塞点和下一步要做的事
4. key_files 只列实际已创建/修改的文件，不要猜测
5. progress_summary 突出完成了什么，不要重复列已在 anchors 里的信息
6. 只输出 JSON，不要有任何其他文字

# anchors 来源约束（严格遵守）

anchors 只能记录工作历史中**实际发生的决策和操作**：
- 用户明确选择的方案（如"用户选了 FastAPI"、"用户要求用 SQLite"）
- 已经执行的操作结果（如"已安装 xyz 库"、"数据库表已创建"）
- 已确认的项目约定（如"API 前缀为 /api/v1"、"端口 8000"）

anchors 不能包含：
- 你自己的技术推荐或偏好（如"建议用 xxx"）
- 未在历史中出现的技术判断
- 性能断言、年份断言、排名断言
"""

# ── 噪声目录（压缩文件树用）──────────────────────────────────────────

_NOISE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "dist", "build", ".egg-info", ".eggs", ".next", ".nuxt",
    ".svelte-kit", "coverage", ".nyc_output", "htmlcov",
    ".DS_Store", "Thumbs.db", ".idea", ".vscode",
}

# ── 关键事实提取模式 ────────────────────────────────────────────────

_FACT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"(?:使用|选择|采用|安装)了?\s*(\w[\w.+-]*)\s*(?:框架|库|包)", re.I), "框架"),
    (re.compile(r"数据库[：:]\s*(\w+)", re.I), "数据库"),
    (re.compile(r"(?:python|node|java|go)\s*([\d.]+)", re.I), "版本"),
    (re.compile(r"(?:入口|主文件)[：:]\s*([\w./]+\.\w+)", re.I), "入口文件"),
    (re.compile(r"(?:端口|port)[：:]\s*(\d{2,5})", re.I), "端口"),
    (re.compile(r"(?:编码|encoding)[：:]\s*(utf-?8|gbk|gb2312|ascii)", re.I), "编码"),
    (re.compile(r"(?:FastAPI|Flask|Django|Express|Next\.js|Vue|React)", re.I), "框架"),
    (re.compile(r"(?:SQLite|MySQL|PostgreSQL|MongoDB|Redis)", re.I), "数据库"),
    (re.compile(r"(?:文件路径|保存到|输出到)[：:]\s*([\w./\\-]+\.\w+)", re.I), "文件路径"),
]


# ── 核心函数 ────────────────────────────────────────────────────────

def should_condense(turn_count: int, threshold: int = CONDENSE_THRESHOLD) -> bool:
    """判断是否需要压缩

    当轮数达到阈值且是阈值的倍数时触发（15, 30, 45, ...）
    """
    if turn_count < threshold:
        return False
    return turn_count % threshold == 0


def condense_history(history: list[dict], task_goal: str) -> dict[str, Any]:
    """调用 DeepSeek 压缩历史轨迹为结构化摘要

    Args:
        history: 历史轮次列表，每轮包含 action/result/turn 字段
        task_goal: 原始任务目标

    Returns:
        {task_goal, progress_summary, anchors, pending_issues, key_files}
        失败时返回空结构（不抛异常）
    """
    empty_result: dict[str, Any] = {
        "task_goal": task_goal,
        "progress_summary": "",
        "anchors": [],
        "pending_issues": [],
        "key_files": [],
    }

    if not history:
        return empty_result

    # 检查额度
    allowed, msg = check_quota()
    if not allowed:
        logger.info(f"压缩被限流: {msg}")
        return empty_result

    # 组装历史文本（截断保护）
    history_lines: list[str] = []
    for h in history[-30:]:  # 最多取最近 30 轮
        turn = h.get("turn", "?")
        action = str(h.get("action", ""))[:200]
        result = str(h.get("result", ""))[:200]
        history_lines.append(f"Turn {turn}: {action}")
        if result:
            history_lines.append(f"  结果: {result}")

    history_text = "\n".join(history_lines)
    if len(history_text) > 4000:
        history_text = history_text[:4000] + "\n...[已截断]"

    user_message = f"# 任务目标\n\n{task_goal}\n\n# 工作历史（{len(history)} 轮）\n\n{history_text}"

    try:
        raw = call_llm(
            messages=[
                {"role": "system", "content": _CONDENSE_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            max_tokens=500,
            temperature=0.2,
            timeout=DEFAULT_TIMEOUT,
            purpose="condense",
        )
        record_call()

        # 解析 JSON
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        result = json.loads(text)

        # 校验和填充
        result.setdefault("task_goal", task_goal)
        result.setdefault("progress_summary", "")
        result.setdefault("anchors", [])
        result.setdefault("pending_issues", [])
        result.setdefault("key_files", [])

        logger.info(
            f"历史压缩完成: {len(result['anchors'])} 锚点, "
            f"{len(result['pending_issues'])} 待处理"
        )
        return result

    except json.JSONDecodeError as e:
        logger.warning(f"压缩返回 JSON 解析失败: {e}")
        return empty_result
    except Exception as e:
        logger.warning(f"历史压缩调用失败: {e}")
        return empty_result


def compress_observation(text: str, max_chars: int = 0) -> str:
    """压缩单条长观察（工具返回值、文件内容、错误日志等）

    纯文本处理，零 token 消耗。

    策略（按优先级）：
    1. 短文本直接返回
    2. 文件树：过滤噪声目录
    3. Traceback：只保留最后 30 行
    4. 其他长文本：头尾截断

    Args:
        text: 原始文本
        max_chars: 最大字符数（0 = 使用默认值 MAX_OBSERVATION_TOKENS * 3）

    Returns:
        压缩后的文本
    """
    if max_chars <= 0:
        max_chars = MAX_OBSERVATION_TOKENS * 3  # ~1500 chars

    if len(text) <= max_chars:
        return text

    # 策略 2：文件树（包含大量路径行）
    if _looks_like_file_tree(text):
        return _compress_file_tree(text, max_chars)

    # 策略 3：Traceback
    if _looks_like_traceback(text):
        return _compress_traceback(text, max_lines=30)

    # 策略 4：通用头尾截断
    head_chars = int(max_chars * 0.7)
    tail_chars = max_chars - head_chars - 30  # 30 for separator
    return (
        text[:head_chars]
        + "\n\n...[已截断，省略中间部分]...\n\n"
        + text[-tail_chars:]
    )


def extract_key_facts(text: str) -> list[str]:
    """从一段文本中提取关键事实（用于决策锚点自动识别）

    识别技术决策、版本号、文件路径等。
    返回最多 5 条，每条不超过 50 字。
    """
    facts: list[str] = []
    seen_categories: set[str] = set()

    for pattern, category in _FACT_PATTERNS:
        matches = pattern.findall(text)
        for match in matches:
            if category in seen_categories:
                continue
            fact = f"{category}: {match}"
            if len(fact) <= 50:
                facts.append(fact)
                seen_categories.add(category)
            if len(facts) >= 5:
                return facts

    return facts


# ── 内部辅助 ────────────────────────────────────────────────────────

def _looks_like_file_tree(text: str) -> bool:
    """判断文本是否像文件树（大量路径行）"""
    lines = text.splitlines()[:50]
    path_count = sum(1 for l in lines if "/" in l or "\\" in l or l.strip().startswith("├") or l.strip().startswith("└"))
    return path_count > len(lines) * 0.5


def _looks_like_traceback(text: str) -> bool:
    """判断文本是否像 Python traceback"""
    indicators = ["Traceback (most recent call last)", "File \"", "Error:", "Exception:"]
    return any(ind in text for ind in indicators)


def _compress_file_tree(text: str, max_chars: int) -> str:
    """压缩文件树：过滤噪声目录"""
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # 检查路径中是否包含噪声目录
        parts = stripped.replace("\\", "/").split("/")
        if any(p.strip("├└│── ") in _NOISE_DIRS for p in parts):
            continue
        lines.append(line)

    result = "\n".join(lines)
    if len(result) > max_chars:
        # 仍然太长，截断
        kept = lines[:max_chars // 50]  # 估算每行约 50 字符
        omitted = len(lines) - len(kept)
        result = "\n".join(kept) + f"\n... ({omitted} 项已省略)"
    return result


def _compress_traceback(text: str, max_lines: int = 30) -> str:
    """压缩 traceback：只保留最后 N 行"""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text

    omitted = len(lines) - max_lines
    return f"... ({omitted} 行已省略)\n" + "\n".join(lines[-max_lines:])
