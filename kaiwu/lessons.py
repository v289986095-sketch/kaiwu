"""报错诊断 — 三层错误诊断引擎

Layer 1: 本地 ErrorKB 精确匹配（指纹匹配，毫秒级，零 token 消耗）
Layer 2: 本地 ErrorKB 模糊匹配（关键词重叠，零 token 消耗）
Layer 3: DeepSeek 分析（消耗 token，新解决方案回写到 ErrorKB）

设计原则：能本地解决的绝不调 API，节省 token 同时降低延迟。
"""

import json
from typing import Any

from loguru import logger

from kaiwu.config import DEFAULT_TIMEOUT, DEFAULT_MAX_TOKENS
from kaiwu.llm_client import call_llm
from kaiwu.quota import check_quota, record_call
from kaiwu.storage import get_error_kb

# ── DeepSeek 诊断提示词 ────────────────────────────────────────────

_DIAGNOSE_SYSTEM = """\
你是一位错误分类助手，帮 AI 编程助手快速定位错误类型和修复方向。

# 你的职责边界（严格遵守）

你只负责：
1. 判断错误类型（语法/类型/依赖/配置/逻辑/网络）
2. 指出修复方向（"检查 X 的配置"、"升级 Y 到兼容版本"）
3. 提醒中国环境特殊问题（编码/镜像/路径）

你绝对不能做：
- 给出具体的修复代码（主 AI 自己会写）
- 猜测具体的变量值、配置值、版本号
- 断言根因（用"可能是..."而非"就是..."）
- 写入年份断言、性能断言、主观排名
- 提供世界知识型事实（如某库的发布日期、某公司的信息）

你的判断会注入主 AI 上下文。如果你猜错了具体值，主 AI 会被误导。
所以只给方向，不给具体值。

# 输出要求

严格以 JSON 格式返回：

```json
{
  "root_cause": "根本原因的一句话描述",
  "fix_suggestion": "修复建议（具体可操作的步骤）",
  "confidence": 0.85
}
```

# 诊断原则

1. **先看错误类型**：区分语法错误、类型错误、依赖缺失、配置问题、逻辑错误
2. **关注最后一行**：通常是最直接的错误信息
3. **注意中国环境**：网络问题（npm/pip 超时）、编码问题（GBK/UTF-8）、路径问题（Windows 反斜杠）
4. **修复建议要具体**：给出可以直接执行的命令或代码片段，不要笼统的"检查配置"
5. **confidence 诚实**：看不懂的错误给低置信度

# 注意事项

- 只输出 JSON，不要有任何其他文字
- root_cause 不超过 100 字
- fix_suggestion 不超过 300 字
"""

# ── 空结果（兜底） ──────────────────────────────────────────────────

_EMPTY_RESULT: dict[str, Any] = {
    "root_cause": "",
    "fix_suggestion": "",
    "confidence": 0.0,
    "source": "none",
}


def get_lessons(error_text: str, context: str = "", session_id: str = "",
                project_name: str = "") -> dict[str, Any]:
    """三层错误诊断：本地精确 → 本地模糊 → DeepSeek 分析

    v0.2.1 新增：循环检测。如果同 session 内连续 3+ 次同类错误，
    返回 is_looping=true + 升级建议，指示主 AI 换路径。

    Args:
        error_text: 错误信息文本（stderr、stack trace 等）
        context: 可选的额外上下文（如出错的文件内容、执行的命令）
        session_id: 会话 ID（传入则注入技术栈上下文 + 循环检测）
        project_name: 当前项目名（传入后优先参考同项目的错误模式）

    Returns:
        {root_cause, fix_suggestion, confidence, source,
         is_looping?, loop_suggestion?, error_count?}
    """
    if not error_text.strip():
        return {**_EMPTY_RESULT}

    kb = get_error_kb()

    # ── Layer 1: 精确匹配 ──────────────────────────────────────
    exact = kb.find_solution(error_text)
    if exact and exact.get("source") == "local_exact":
        logger.info(f"错误诊断命中精确匹配: {exact.get('key', '')[:50]}")
        result = {
            "root_cause": exact.get("key", ""),
            "fix_suggestion": exact.get("solution", ""),
            "confidence": exact.get("confidence", 0.95),
            "source": "local_exact",
        }
        return _attach_loop_detection(result, session_id)

    # ── Layer 2: 模糊匹配 ──────────────────────────────────────
    if exact and exact.get("source") == "local_fuzzy":
        logger.info(f"错误诊断命中模糊匹配: {exact.get('key', '')[:50]}")
        result = {
            "root_cause": exact.get("key", ""),
            "fix_suggestion": exact.get("solution", ""),
            "confidence": exact.get("confidence", 0.7),
            "source": "local_fuzzy",
        }
        return _attach_loop_detection(result, session_id)

    # ── Layer 3: DeepSeek 分析 ─────────────────────────────────

    # 先记录这个未知错误
    error_fp = kb.record_error(error_text, context)

    # 检查额度
    allowed, msg = check_quota()
    if not allowed:
        logger.info(f"错误诊断被限流: {msg}")
        return {**_EMPTY_RESULT, "source": "quota_exceeded", "message": msg}

    try:
        user_parts = [f"# 错误信息\n\n```\n{error_text[:2000]}\n```"]
        if context:
            user_parts.append(f"\n# 上下文\n\n{context[:1000]}")

        # 注入会话上下文（让 DeepSeek 知道技术栈决策）
        if session_id:
            try:
                from kaiwu.session import SessionManager, build_session_context
                mgr = SessionManager()
                session = mgr.resolve_session(session_id)
                if session:
                    session_ctx = build_session_context(session, max_chars=800)
                    user_parts.append(f"\n{session_ctx}")
            except Exception as e:
                logger.debug(f"加载会话上下文失败: {e}")

        raw = call_llm(
            messages=[
                {"role": "system", "content": _DIAGNOSE_SYSTEM},
                {"role": "user", "content": "\n".join(user_parts)},
            ],
            max_tokens=DEFAULT_MAX_TOKENS,
            temperature=0.2,
            timeout=DEFAULT_TIMEOUT,
            purpose="lessons",
        )
        record_call()

        # 解析 JSON
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        result = json.loads(text)

        root_cause = result.get("root_cause", "")
        fix_suggestion = result.get("fix_suggestion", "")
        confidence = result.get("confidence", 0.5)

        # 回写到 ErrorKB —— 下次相同错误就不用调 API 了
        if fix_suggestion:
            solution_text = f"{root_cause}\n修复: {fix_suggestion}"
            kb.record_solution(error_fp, solution_text[:500])
            logger.info(f"新解决方案已写入 ErrorKB: {error_fp}")

        # 自动记录到 Session error_history（用于循环检测）
        if session_id:
            try:
                from kaiwu.session import SessionManager
                from kaiwu.storage.error_kb import _extract_error_key
                mgr = SessionManager()
                error_type = _extract_error_key(error_text)
                mgr.record_error(session_id, error_type, error_fp)
            except Exception as e:
                logger.debug(f"自动记录错误到 session 失败: {e}")

        return _attach_loop_detection({
            "root_cause": root_cause,
            "fix_suggestion": fix_suggestion,
            "confidence": confidence,
            "source": "llm",
        }, session_id)

    except json.JSONDecodeError as e:
        logger.warning(f"DeepSeek 诊断返回 JSON 解析失败: {e}")
        return _attach_loop_detection({**_EMPTY_RESULT, "source": "parse_error"}, session_id)
    except Exception as e:
        logger.warning(f"错误诊断调用失败: {e}")
        return _attach_loop_detection({**_EMPTY_RESULT, "source": "error"}, session_id)


def _attach_loop_detection(result: dict, session_id: str) -> dict:
    """如果有 session_id，附加循环检测信息到诊断结果"""
    if not session_id:
        return result
    try:
        from kaiwu.session import SessionManager
        mgr = SessionManager()
        stats = mgr.get_error_stats(session_id, window=3)
        result["error_count"] = stats.get("error_count", 0)
        result["is_looping"] = stats.get("is_looping", False)
        if stats.get("is_looping"):
            result["loop_suggestion"] = stats.get("suggestion", "")
            logger.warning(
                f"循环检测触发: session={session_id}, "
                f"type={stats.get('loop_type', '')}, "
                f"consecutive={stats.get('consecutive', 0)}"
            )
    except Exception as e:
        logger.debug(f"循环检测失败（不影响诊断）: {e}")
    return result
