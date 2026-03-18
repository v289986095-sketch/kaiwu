"""知识库加载器 — 加载 knowledge/ 目录下的 md 文件，注入到 DeepSeek prompt 中"""

from pathlib import Path
from typing import Optional

from loguru import logger

from kaiwu.config import KNOWLEDGE_DIR

# 缓存
_knowledge_cache: dict[str, str] = {}


def load_knowledge(name: str) -> str:
    """加载指定知识库文件内容

    Args:
        name: 文件名（不含 .md 后缀），如 'china_kb', 'python_compat', 'deps_pitfalls'

    Returns:
        文件内容字符串，加载失败返回空字符串
    """
    if name in _knowledge_cache:
        return _knowledge_cache[name]

    path = KNOWLEDGE_DIR / f"{name}.md"
    if not path.exists():
        logger.debug(f"知识库文件不存在: {path}")
        return ""

    try:
        content = path.read_text(encoding="utf-8")
        _knowledge_cache[name] = content
        return content
    except Exception as e:
        logger.warning(f"加载知识库 {name} 失败: {e}")
        return ""


def load_all_knowledge() -> str:
    """加载所有知识库文件，合并为一个字符串"""
    parts = []
    if not KNOWLEDGE_DIR.exists():
        return ""

    for md_file in sorted(KNOWLEDGE_DIR.glob("*.md")):
        name = md_file.stem
        content = load_knowledge(name)
        if content:
            parts.append(f"## {name}\n\n{content}")

    return "\n\n---\n\n".join(parts)


def get_knowledge_summary(max_chars: int = 2000) -> str:
    """获取知识库精华摘要（用于注入配置文件兜底层）"""
    full = load_all_knowledge()
    if len(full) <= max_chars:
        return full
    return full[:max_chars] + "\n\n... (完整内容请通过 kaiwu MCP Server 获取)"
