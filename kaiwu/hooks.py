"""规则引擎 — 工具使用前后的规则检查（loop_guard）

从 data/rules.json 动态加载规则，
在工具使用前(pre_use)和使用后(post_use)检查是否触发。

支持的动作类型：
- force_hint: 强制提示（不阻塞，注入到上下文）
- auto_fix: 自动修复建议
- block: 阻止执行
- warn: 警告信息

规则支持 tool="*" 通配（工具无关规则）。
"""

import json
import re
from pathlib import Path
from typing import Any

from loguru import logger

from kaiwu.config import DATA_DIR

# ── 规则缓存 ────────────────────────────────────────────────────────

_rules_cache: list[dict] | None = None
_rules_mtime: float = 0.0

RULES_PATH = DATA_DIR / "rules.json"


def _load_rules() -> list[dict]:
    """加载规则文件，支持热重载（文件变更时自动刷新）"""
    global _rules_cache, _rules_mtime

    if not RULES_PATH.exists():
        logger.debug(f"规则文件不存在: {RULES_PATH}，使用空规则集")
        _rules_cache = []
        return _rules_cache

    try:
        current_mtime = RULES_PATH.stat().st_mtime
    except OSError:
        if _rules_cache is not None:
            return _rules_cache
        return []

    # 缓存命中且文件未修改
    if _rules_cache is not None and current_mtime == _rules_mtime:
        return _rules_cache

    # 重新加载
    try:
        raw = RULES_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        rules = data if isinstance(data, list) else data.get("rules", [])
        _rules_cache = rules
        _rules_mtime = current_mtime
        logger.debug(f"已加载 {len(rules)} 条规则")
        return rules
    except Exception as e:
        logger.warning(f"加载规则文件失败: {e}")
        _rules_cache = _rules_cache or []
        return _rules_cache


def _match_pattern(pattern: str, text: str) -> bool:
    """检查 text 是否匹配 pattern

    支持：
    - 正则表达式（以 / 开头和结尾，如 /Error.*timeout/i）
    - 简单包含匹配（其他情况）
    """
    if not pattern or not text:
        return False

    # 正则模式：/pattern/flags
    if pattern.startswith("/") and "/" in pattern[1:]:
        last_slash = pattern.rindex("/")
        regex_str = pattern[1:last_slash]
        flags_str = pattern[last_slash + 1:]

        flags = 0
        if "i" in flags_str:
            flags |= re.IGNORECASE
        if "s" in flags_str:
            flags |= re.DOTALL

        try:
            return bool(re.search(regex_str, text, flags))
        except re.error as e:
            logger.debug(f"正则解析失败: {pattern} -> {e}")
            return False

    # 包含 | 或 正则特殊字符时，视为正则表达式
    if "|" in pattern or any(c in pattern for c in r".*+?()[]{}^$\\"):
        try:
            return bool(re.search(pattern, text, re.IGNORECASE))
        except re.error:
            pass

    # 简单包含匹配（大小写不敏感）
    return pattern.lower() in text.lower()


def check_rules(
    tool_name: str,
    event: str,
    result_text: str,
) -> list[dict[str, Any]]:
    """检查工具使用是否触发规则

    Args:
        tool_name: 工具名称（如 "bash", "write", "read"）
        event: 事件类型，"pre_use"（执行前）或 "post_use"（执行后）
        result_text: pre_use 时为工具输入/命令内容，post_use 时为输出结果。
                     pre_use 时此参数不可为空，否则 params_match 类规则无法触发。

    Returns:
        触发的规则动作列表，每项包含：
        {
            "action": "force_hint" | "auto_fix" | "block" | "warn",
            "message": "提示/警告/修复建议内容",
            "rule_id": "规则 ID（如果有）",
            "severity": "info" | "warning" | "error"
        }
        未触发时返回空列表。
    """
    rules = _load_rules()
    if not rules:
        return []

    triggered: list[dict[str, Any]] = []

    for rule in rules:
        # 支持两种格式：扁平格式 和 嵌套 trigger 格式
        trigger = rule.get("trigger", {})
        if isinstance(trigger, dict) and trigger:
            rule_tool = trigger.get("tool", "*")
            rule_event = trigger.get("event", "*")
            condition = trigger.get("condition", "")
            pattern = trigger.get("pattern", "")
        else:
            rule_tool = rule.get("tool", "*")
            rule_event = rule.get("event", "*")
            condition = rule.get("condition", "")
            pattern = rule.get("pattern", "")

        # ── 匹配工具名 ────────────────────────────────────────
        if rule_tool != "*" and rule_tool != tool_name:
            # 支持逗号分隔的多工具列表
            if "," in rule_tool:
                tools = [t.strip() for t in rule_tool.split(",")]
                if tool_name not in tools:
                    continue
            else:
                continue

        # ── 匹配事件类型 ──────────────────────────────────────
        if rule_event != "*" and rule_event != event:
            # 支持逗号分隔的多事件
            if "," in rule_event:
                events = [e.strip() for e in rule_event.split(",")]
                if event not in events:
                    continue
            else:
                continue

        # ── condition 校验 ────────────────────────────────────
        # params_match: 只在 pre_use 时有意义，匹配工具输入/命令
        # result_contains: 只在 post_use 时有意义，匹配工具输出
        if condition == "params_match" and event != "pre_use":
            continue
        if condition == "result_contains" and event != "post_use":
            continue

        # ── 匹配内容模式 ──────────────────────────────────────
        if pattern and not _match_pattern(pattern, result_text):
            continue

        # ── 规则命中，提取动作 ────────────────────────────────
        action = rule.get("action", "warn")
        message = rule.get("message", "")
        rule_id = rule.get("id", rule.get("name", "unnamed"))
        severity = rule.get("severity", _default_severity(action))

        triggered.append({
            "action": action,
            "message": message,
            "rule_id": rule_id,
            "severity": severity,
        })

        logger.debug(
            f"规则触发: [{rule_id}] {action} on {tool_name}/{event} "
            f"-> {message[:50]}"
        )

    return triggered


def _default_severity(action: str) -> str:
    """根据动作类型返回默认严重级别"""
    severity_map = {
        "block": "error",
        "force_hint": "info",
        "auto_fix": "warning",
        "warn": "warning",
    }
    return severity_map.get(action, "info")


def get_rules_stats() -> dict[str, Any]:
    """获取规则库统计信息"""
    rules = _load_rules()
    action_counts: dict[str, int] = {}
    tool_counts: dict[str, int] = {}
    for rule in rules:
        action = rule.get("action", "warn")
        action_counts[action] = action_counts.get(action, 0) + 1
        tool = rule.get("tool", "*")
        tool_counts[tool] = tool_counts.get(tool, 0) + 1

    return {
        "total": len(rules),
        "by_action": action_counts,
        "by_tool": tool_counts,
        "rules_path": str(RULES_PATH),
        "file_exists": RULES_PATH.exists(),
    }
