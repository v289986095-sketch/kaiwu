"""场景检测 — 根据任务描述识别匹配的编码场景

三种检测方式：
1. detect_scene(task) — 纯关键词匹配（零 token 消耗）
2. get_scene(task) — 关键词匹配 + 加载场景 .md 文件内容
3. get_scene_with_llm(task) — 两阶段：关键词优先，无匹配时 LLM 兜底

场景 .md 文件存放在 kaiwu/scenes/ 目录。
用户积累的场景增强内容存放在 ~/.kaiwu/scene_enrichments.json。
"""

import json
import re
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from kaiwu.config import (
    KAIWU_HOME,
    SCENES_DIR,
    ENRICHMENTS_PATH,
    DEFAULT_TIMEOUT,
)
from kaiwu.llm_client import call_llm
from kaiwu.quota import check_quota, record_call

# 用户自定义场景目录（优先于内置场景）
USER_SCENES_DIR = KAIWU_HOME / "scenes"

# ── 19 个场景的关键词表 ──────────────────────────────────────────────

_SCENE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("docx", ["word", "docx", ".docx", "word文档", "申请书", "公文", "合同", "简历"]),
    ("pdf", ["pdf", ".pdf", "合并pdf", "拆分pdf", "pdf水印", "pdf加密", "扫描件"]),
    ("pptx", ["ppt", "pptx", ".pptx", "演示文稿", "幻灯片", "slide", "deck", "汇报材料"]),
    ("xlsx", ["excel", "xlsx", ".xlsx", "电子表格", "财务表格"]),
    ("react", ["react", "jsx", "tsx", "组件", "component", "shadcn", "nextjs", "next.js"]),
    ("dataviz", ["图表", "chart", "echarts", "可视化", "dashboard", "仪表盘", "plotly", "d3"]),
    ("game_dev", ["游戏", "game", "canvas", "sprite", "碰撞", "collision", "2d游戏", "小游戏"]),
    ("test_case", ["测试", "test", "pytest", "unittest", "单元测试", "用例", "assert", "mock"]),
    ("code_review", ["审查", "review", "code review", "代码审查", "CR", "走查"]),
    ("web", ["网页", "html", "页面", "landing", "前端", "tailwind", "css", "website", "网站"]),
    ("backend_api", ["api", "fastapi", "flask", "django", "后端", "接口", "endpoint", "路由"]),
    ("database", ["数据库", "database", "sql", "mysql", "postgres", "sqlite", "建表", "migration"]),
    ("data_analysis", ["pandas", "数据分析", "dataframe", "excel分析"]),
    ("web_scraping", ["爬虫", "scraping", "crawl", "抓取", "spider", "selenium", "playwright爬"]),
    ("copywriting", ["文案", "营销", "广告", "推文", "软文", "slogan", "标题党"]),
    ("shell_script", ["shell", "bash", "脚本.sh", ".sh", "运维脚本", "部署脚本"]),
    ("python_script", ["python脚本", "py脚本", "命令行工具", "cli工具"]),
    ("china_deploy", ["部署", "deploy", "nginx", "systemd", "gunicorn", "宝塔", "服务器", "云服务器", "备案"]),
    ("wechat_pay", ["微信支付", "wechat pay", "支付宝", "alipay", "小程序支付", "jsapi", "回调通知"]),
]

# 所有合法场景名（包含用户自定义场景）
def _get_all_scenes() -> list[str]:
    """获取所有场景名，包括用户自定义场景"""
    scenes = [s[0] for s in _SCENE_KEYWORDS]
    if USER_SCENES_DIR.exists():
        for f in USER_SCENES_DIR.glob("*.md"):
            name = f.stem
            if name not in scenes:
                scenes.append(name)
    return scenes

_ALL_SCENES = _get_all_scenes()

# ── LLM 场景检测提示词 ──────────────────────────────────────────────

_DETECT_SYSTEM = f"""\
你是一个任务分类器。根据用户的任务描述，判断它属于以下哪个编码场景。

可选场景：{', '.join(_ALL_SCENES)}

# 输出要求

只输出一个 JSON：
```json
{{"scene": "场景名", "confidence": 0.85}}
```

- 如果无法确定，scene 设为空字符串，confidence 设为 0
- 只输出 JSON，不要有其他文字
"""


# ── 关键词匹配 ──────────────────────────────────────────────────────

def detect_scene(task: str) -> Optional[str]:
    """纯关键词匹配检测场景（零 token 消耗）

    Args:
        task: 任务描述文本

    Returns:
        匹配到的场景名（如 "react", "web"），无匹配返回 None
    """
    if not task.strip():
        return None

    # 预处理：去除中文标点，转小写
    task_lower = _normalize_task(task)

    best_scene: Optional[str] = None
    best_score: int = 0

    for scene_name, keywords in _SCENE_KEYWORDS:
        score = _score_scene(task_lower, task, keywords)
        if score > best_score:
            best_score = score
            best_scene = scene_name

    if best_scene:
        logger.debug(f"关键词匹配场景: {best_scene} (score={best_score})")

    return best_scene


def detect_scenes_multi(task: str, max_scenes: int = 3) -> list[tuple[str, int]]:
    """支持返回多个场景（如"爬取数据后做可视化"同时命中 web_scraping + dataviz）

    Args:
        task: 任务描述
        max_scenes: 最多返回场景数

    Returns:
        [(场景名, 分数), ...] 按分数降序，最多 max_scenes 个
    """
    if not task.strip():
        return []

    task_lower = _normalize_task(task)

    scores: list[tuple[str, int]] = []
    for scene_name, keywords in _SCENE_KEYWORDS:
        score = _score_scene(task_lower, task, keywords)
        if score > 0:
            scores.append((scene_name, score))

    # 按分数降序
    scores.sort(key=lambda x: x[1], reverse=True)

    # 过滤：第二名分数至少是第一名的 30%
    if len(scores) > 1 and scores[0][1] > 0:
        threshold = scores[0][1] * 0.3
        scores = [(s, sc) for s, sc in scores if sc >= threshold]

    return scores[:max_scenes]


def _normalize_task(task: str) -> str:
    """预处理任务文本：去除中文标点，转小写"""
    # 去除中文标点
    task = re.sub(r'[，。！？、；：""''【】（）《》…—]', ' ', task)
    return task.lower()


def _score_scene(task_lower: str, task_orig: str, keywords: list[str]) -> int:
    """计算场景匹配分数

    特殊处理：如果任务含 "不用 X" / "不要 X"，降低 X 场景权重
    """
    score = 0
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in task_lower:
            # 负样本过滤：检查是否有否定前缀
            neg_patterns = [f"不用{kw}", f"不要{kw}", f"别用{kw}", f"不使用{kw}"]
            is_negated = any(neg in task_orig for neg in neg_patterns)
            if is_negated:
                score -= len(kw)
            else:
                score += len(kw)

    return max(score, 0)


# ── 场景内容加载 ────────────────────────────────────────────────────

def _load_scene_file(scene_name: str) -> str:
    """加载场景 .md 文件内容

    优先级: ~/.kaiwu/scenes/ > 包内 kaiwu/scenes/
    用户自定义场景可覆盖内置场景，也可新增自定义场景。
    """
    # 优先加载用户自定义场景
    user_path = USER_SCENES_DIR / f"{scene_name}.md"
    if user_path.exists():
        try:
            content = user_path.read_text(encoding="utf-8")
            logger.debug(f"加载用户自定义场景: {user_path}")
            return content
        except Exception as e:
            logger.warning(f"加载用户自定义场景失败: {user_path} -> {e}")

    # 回退到内置场景
    path = SCENES_DIR / f"{scene_name}.md"
    if not path.exists():
        logger.debug(f"场景文件不存在: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning(f"加载场景文件失败: {path} -> {e}")
        return ""


def _load_enrichments(scene_name: str) -> str:
    """加载用户积累的场景增强内容"""
    if not ENRICHMENTS_PATH.exists():
        return ""
    try:
        data = json.loads(ENRICHMENTS_PATH.read_text(encoding="utf-8"))
        enrichments = data.get(scene_name, [])
        if not enrichments:
            return ""
        # 每条增强内容拼接
        parts = [f"- {e}" if isinstance(e, str) else f"- {e.get('content', '')}"
                 for e in enrichments]
        return "\n".join(parts)
    except Exception as e:
        logger.debug(f"加载场景增强失败: {e}")
        return ""


def get_scene(task: str) -> dict[str, Any]:
    """关键词匹配 + 加载场景完整内容（零 token 消耗）

    Args:
        task: 任务描述

    Returns:
        {
            "scene": "场景名" | None,
            "content": "场景 .md 内容",
            "enrichments": "用户增强内容",
            "source": "keyword" | "none"
        }
    """
    scene_name = detect_scene(task)

    if not scene_name:
        return {
            "scene": None,
            "content": "",
            "enrichments": "",
            "source": "none",
        }

    content = _load_scene_file(scene_name)
    enrichments = _load_enrichments(scene_name)

    return {
        "scene": scene_name,
        "content": content,
        "enrichments": enrichments,
        "source": "keyword",
    }


# ── LLM 兜底检测 ───────────────────────────────────────────────────

def _detect_scene_with_llm(task: str) -> Optional[str]:
    """使用 DeepSeek 进行场景检测（消耗 token）"""
    allowed, msg = check_quota()
    if not allowed:
        logger.info(f"场景 LLM 检测被限流: {msg}")
        return None

    try:
        raw = call_llm(
            messages=[
                {"role": "system", "content": _DETECT_SYSTEM},
                {"role": "user", "content": f"任务描述：{task[:500]}"},
            ],
            max_tokens=100,
            temperature=0.1,
            timeout=DEFAULT_TIMEOUT,
        )
        record_call()

        # 解析 JSON
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        result = json.loads(text)
        scene = result.get("scene", "")
        confidence = result.get("confidence", 0)

        # 验证场景名合法且置信度足够
        if scene in _ALL_SCENES and confidence >= 0.5:
            logger.info(f"LLM 场景检测: {scene} (confidence={confidence})")
            return scene

        logger.debug(f"LLM 场景检测置信度不足: scene={scene}, confidence={confidence}")
        return None

    except Exception as e:
        logger.warning(f"LLM 场景检测失败: {e}")
        return None


def get_scene_with_llm(task: str) -> dict[str, Any]:
    """两阶段场景检测：关键词优先，LLM 兜底

    支持多场景：如"爬取数据后做可视化"同时返回 web_scraping + dataviz。

    Args:
        task: 任务描述

    Returns:
        {
            "scene": "主场景名" | None,
            "scenes": ["场景1", "场景2"],  # 多场景列表
            "content": "主场景 .md 内容",
            "enrichments": "用户增强内容",
            "source": "keyword" | "llm" | "none"
        }
    """
    # 第一阶段：多场景关键词匹配
    multi = detect_scenes_multi(task)
    scene_name = multi[0][0] if multi else None
    all_scenes = [s for s, _ in multi]
    source = "keyword" if scene_name else "none"

    # 第二阶段：关键词无匹配，LLM 兜底
    if not scene_name:
        scene_name = _detect_scene_with_llm(task)
        if scene_name:
            all_scenes = [scene_name]
            source = "llm"

    if not scene_name:
        return {
            "scene": None,
            "scenes": [],
            "content": "",
            "enrichments": "",
            "source": "none",
        }

    content = _load_scene_file(scene_name)
    enrichments = _load_enrichments(scene_name)

    # 如果有多场景，合并次要场景的关键规范
    if len(all_scenes) > 1:
        for extra_scene in all_scenes[1:]:
            extra_content = _load_scene_file(extra_scene)
            if extra_content:
                # 只取前 500 字符的关键规范
                content += f"\n\n---\n# 附加场景: {extra_scene}\n\n{extra_content[:500]}"

    return {
        "scene": scene_name,
        "scenes": all_scenes,
        "content": content,
        "enrichments": enrichments,
        "source": source,
    }
