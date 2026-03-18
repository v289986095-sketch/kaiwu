"""项目上下文处理器 — 压缩文件树 + 提取技术栈

接收目录树和关键文件内容，过滤噪声，压缩为会话可用的项目摘要。
创建/更新会话的 project_summary 字段。
"""

import re
from typing import Optional

from loguru import logger

from kaiwu.session import SessionManager, Session

# ── 噪声目录 / 文件模式 ──────────────────────────────────────────────

from kaiwu.config import NOISE_DIRS as _NOISE_DIRS

_NOISE_PATTERNS = re.compile(
    r"(\.pyc$|\.pyo$|\.class$|\.o$|\.so$|\.dylib$"
    r"|\.min\.js$|\.min\.css$|\.map$|\.lock$"
    r"|package-lock\.json$|yarn\.lock$|pnpm-lock\.yaml$)"
)

# ── 关键文件（用于技术栈识别）──────────────────────────────────────────

_KEY_FILES = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "requirements.txt", "Pipfile", "Gemfile", "composer.json",
    "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "main.py", "app.py", "manage.py", "index.ts", "index.js",
    "tsconfig.json", "vite.config.ts", "vite.config.js",
    "next.config.js", "next.config.mjs", "nuxt.config.ts",
    ".env.example", "config.toml", "config.yaml", "config.yml",
}

# ── 技术栈关键词提取 ──────────────────────────────────────────────────

_TECH_PATTERNS: list[tuple[str, str]] = [
    # Python
    (r'"fastapi"', "FastAPI"),
    (r'"flask"', "Flask"),
    (r'"django"', "Django"),
    (r'"sqlalchemy"', "SQLAlchemy"),
    (r'"sqlite|aiosqlite"', "SQLite"),
    (r'"pytest"', "pytest"),
    (r'"pandas"', "pandas"),
    (r'"numpy"', "NumPy"),
    # JavaScript/TypeScript
    (r'"react"', "React"),
    (r'"vue"', "Vue"),
    (r'"next"', "Next.js"),
    (r'"nuxt"', "Nuxt"),
    (r'"svelte"', "Svelte"),
    (r'"express"', "Express"),
    (r'"vite"', "Vite"),
    (r'"tailwindcss"', "Tailwind CSS"),
    (r'"element-plus"', "Element Plus"),
    (r'"typescript"', "TypeScript"),
    # Database
    (r'"mysql|pymysql"', "MySQL"),
    (r'"psycopg|asyncpg|postgresql"', "PostgreSQL"),
    (r'"redis|aioredis"', "Redis"),
    (r'"mongodb|pymongo|motor"', "MongoDB"),
    # Other
    (r'"docker"', "Docker"),
    (r'Dockerfile', "Docker"),
]


def process_context(
    directory_tree: str,
    key_files: str = "",
    session_id: str = "",
    task: str = "",
) -> dict:
    """处理项目上下文，创建/更新会话

    Args:
        directory_tree: 项目文件树文本（ls -R / find / tree 的输出）
        key_files: 关键配置文件内容（package.json / pyproject.toml 等）
        session_id: 已有会话 ID（传入则更新，否则创建新会话）
        task: 任务描述（创建新会话时必须）

    Returns:
        {"session_id": "xxx", "project_summary": "压缩后的摘要", "tech_stack": [...]}
    """
    # ── 1. 过滤噪声、压缩文件树 ──────────────────────────────
    clean_tree = _filter_tree(directory_tree)
    compressed = _compress_tree(clean_tree, max_lines=100)

    # ── 2. 识别关键文件 ──────────────────────────────────────
    found_key_files = _find_key_files(directory_tree)

    # ── 3. 提取技术栈 ───────────────────────────────────────
    all_text = f"{directory_tree}\n{key_files}"
    tech_stack = _extract_tech_stack(all_text)

    # ── 4. 组装项目摘要 ─────────────────────────────────────
    summary_parts: list[str] = []

    if tech_stack:
        summary_parts.append("技术栈: " + ", ".join(tech_stack))

    if found_key_files:
        summary_parts.append("关键文件: " + ", ".join(found_key_files[:10]))

    if compressed:
        summary_parts.append(compressed)

    project_summary = "\n".join(summary_parts)

    # ── 5. 创建/更新会话 ────────────────────────────────────
    mgr = SessionManager()

    if session_id:
        session = mgr.resolve_session(session_id)
        if session:
            mgr.update_project_summary(session_id, project_summary)
        else:
            # session_id 无效，创建新会话
            session = mgr.create_session(task=task or "未指定任务", session_id=session_id)
            mgr.update_project_summary(session.session_id, project_summary)
            session_id = session.session_id
    else:
        session = mgr.create_session(task=task or "未指定任务")
        session_id = session.session_id
        mgr.update_project_summary(session_id, project_summary)

    # 如果提取到技术栈，自动添加为锚点
    for tech in tech_stack:
        mgr.add_anchor(session_id, f"技术栈: {tech}")

    return {
        "session_id": session_id,
        "project_summary": project_summary,
        "tech_stack": tech_stack,
    }


def _filter_tree(tree_text: str) -> list[str]:
    """过滤噪声目录和文件"""
    lines: list[str] = []
    for line in tree_text.splitlines():
        stripped = line.strip().rstrip("/")
        # 跳过空行
        if not stripped:
            continue

        # 检查路径中是否包含噪声目录
        parts = stripped.replace("\\", "/").split("/")
        if any(p in _NOISE_DIRS for p in parts):
            continue

        # 检查噪声文件模式
        if _NOISE_PATTERNS.search(stripped):
            continue

        lines.append(line)

    return lines


def _compress_tree(lines: list[str], max_lines: int = 100) -> str:
    """压缩文件树到指定行数"""
    if len(lines) <= max_lines:
        return "\n".join(lines)

    # 保留前 max_lines 行，加省略提示
    result = lines[:max_lines]
    omitted = len(lines) - max_lines
    result.append(f"... ({omitted} 项已省略)")
    return "\n".join(result)


def _find_key_files(tree_text: str) -> list[str]:
    """从文件树中识别关键文件"""
    found: list[str] = []
    for line in tree_text.splitlines():
        name = line.strip().rstrip("/").replace("\\", "/").split("/")[-1]
        if name in _KEY_FILES:
            found.append(name)
    return list(dict.fromkeys(found))  # 去重保序


def _extract_tech_stack(text: str) -> list[str]:
    """从文本内容中提取技术栈关键词"""
    stack: list[str] = []
    text_lower = text.lower()
    for pattern, label in _TECH_PATTERNS:
        if re.search(pattern, text_lower):
            if label not in stack:
                stack.append(label)
    return stack
