"""用量统计 — 记录 DeepSeek 调用次数（v1.0 不限额）

v1.0 策略：所有功能免费开放，DeepSeek 用户自带 Key。
调用次数仅做统计，不做限流。未配置 Key 时给出清晰引导。
"""

import json
import time
from pathlib import Path

from loguru import logger

from kaiwu.config import USAGE_PATH, get_config


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _load_usage() -> dict:
    """加载今日用量"""
    try:
        if USAGE_PATH.exists():
            data = json.loads(USAGE_PATH.read_text(encoding="utf-8"))
            if data.get("date") == _today():
                return data
    except Exception:
        pass
    return {"date": _today(), "calls": 0}


def _save_usage(usage: dict):
    """保存用量"""
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        USAGE_PATH.write_text(json.dumps(usage, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"保存用量失败: {e}")


NO_KEY_MSG = (
    "未配置 DeepSeek API Key，无法使用 AI 增强功能。\n\n"
    "配置方法（二选一）：\n"
    "  方式一：交互式配置\n"
    "    kaiwu config\n\n"
    "  方式二：命令行直接设置\n"
    "    kaiwu config set providers.deepseek.api_key sk-xxx\n\n"
    "获取 Key：\n"
    "  1. 访问 platform.deepseek.com 注册账号\n"
    "  2. 进入「API Keys」页面，点击「创建 API Key」\n"
    "  3. 新用户赠送 500 万 tokens 免费额度\n"
    "  4. 用完后充值 ¥2 起步，日常使用约 ¥0.1/天"
)


def check_quota() -> tuple[bool, str]:
    """检查是否可以调用 DeepSeek

    v1.0 不限次数，仅检查是否配置了 API Key。
    """
    config = get_config()

    if not config.llm_api_key:
        return False, NO_KEY_MSG

    return True, ""


def record_call():
    """记录一次 DeepSeek 调用（仅统计，不限流）"""
    usage = _load_usage()
    usage["calls"] = usage.get("calls", 0) + 1
    _save_usage(usage)


def get_usage_info() -> dict:
    """获取用量信息"""
    config = get_config()
    usage = _load_usage()
    return {
        "plan": config.plan,
        "date": usage["date"],
        "calls_today": usage["calls"],
        "limit": "unlimited",
        "has_api_key": bool(config.llm_api_key),
    }
