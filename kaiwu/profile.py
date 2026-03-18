"""用户画像 — 从经验库自动学习用户编码习惯和偏好

核心思路：不依赖 LLM，纯本地统计分析，零 token 消耗。
每次 record_outcome 成功后触发增量更新，画像越用越准。

存储在 ~/.kaiwu/profile.json。

画像维度：
1. task_type_dist   — 任务类型分布（哪类任务做得多）
2. framework_prefs  — 框架/库偏好（用了几次、成功率）
3. style_hints      — 编码风格线索（命名、缩进、语言等）
4. efficiency       — 效率指标（平均轮数、成功率、擅长领域）
5. tool_patterns    — 工具使用模式（常用工具序列）
6. recent_projects  — 最近活跃项目
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from kaiwu.config import PROFILE_PATH, EXPERIENCE_PATH


# ── 框架/库关键词检测 ─────────────────────────────────────────────

_FRAMEWORK_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("FastAPI",     re.compile(r"\bfastapi\b", re.I)),
    ("Flask",       re.compile(r"\bflask\b", re.I)),
    ("Django",      re.compile(r"\bdjango\b", re.I)),
    ("Express",     re.compile(r"\bexpress\b", re.I)),
    ("React",       re.compile(r"\breact\b", re.I)),
    ("Vue",         re.compile(r"\bvue\b", re.I)),
    ("Next.js",     re.compile(r"\bnext\.?js\b", re.I)),
    ("Svelte",      re.compile(r"\bsvelte\b", re.I)),
    ("TypeScript",  re.compile(r"\btypescript\b", re.I)),
    ("Tailwind",    re.compile(r"\btailwind\b", re.I)),
    ("SQLite",      re.compile(r"\bsqlite\b", re.I)),
    ("PostgreSQL",  re.compile(r"\bpostgres(?:ql)?\b", re.I)),
    ("MySQL",       re.compile(r"\bmysql\b", re.I)),
    ("MongoDB",     re.compile(r"\bmongo(?:db)?\b", re.I)),
    ("Redis",       re.compile(r"\bredis\b", re.I)),
    ("Docker",      re.compile(r"\bdocker\b", re.I)),
    ("pytest",      re.compile(r"\bpytest\b", re.I)),
    ("Playwright",  re.compile(r"\bplaywright\b", re.I)),
    ("Selenium",    re.compile(r"\bselenium\b", re.I)),
    ("pandas",      re.compile(r"\bpandas\b", re.I)),
    ("numpy",       re.compile(r"\bnumpy\b", re.I)),
    ("Element Plus", re.compile(r"\belement[- ]?plus\b", re.I)),
    ("Ant Design",  re.compile(r"\bantd?\b|\bant[- ]?design\b", re.I)),
    ("Vite",        re.compile(r"\bvite\b", re.I)),
    ("Webpack",     re.compile(r"\bwebpack\b", re.I)),
]

# ── 编码风格关键词 ────────────────────────────────────────────────

_STYLE_INDICATORS = {
    "snake_case": re.compile(r"\b[a-z]+_[a-z]+\b"),
    "camelCase":  re.compile(r"\b[a-z]+[A-Z][a-z]+\b"),
    "中文注释":   re.compile(r"[\u4e00-\u9fff]{3,}"),
    "UTF-8":      re.compile(r"\butf-?8\b", re.I),
    "GBK":        re.compile(r"\bgbk\b", re.I),
}


class UserProfile:
    """用户画像：从经验库统计分析，自动学习用户偏好"""

    def __init__(self, path: Optional[Path] = None):
        self._path = path or PROFILE_PATH
        self._data: dict = self._load()

    def _load(self) -> dict:
        """加载已有画像"""
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._empty_profile()

    @staticmethod
    def _empty_profile() -> dict:
        return {
            "version": 1,
            "updated_at": 0,
            "total_tasks": 0,
            "task_type_dist": {},
            "framework_prefs": {},
            "style_hints": {},
            "efficiency": {
                "avg_turns": 0.0,
                "success_rate": 0.0,
                "total_success": 0,
                "total_fail": 0,
                "best_task_types": [],
            },
            "tool_patterns": {},
            "recent_projects": [],
        }

    def _save(self):
        """持久化画像"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data["updated_at"] = time.time()
        try:
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning(f"保存用户画像失败: {e}")

    # ── 核心：从经验库全量重建画像 ──────────────────────────────

    def rebuild_from_experiences(self):
        """从 experiences.json 全量重建画像（冷启动或校正时用）"""
        experiences = self._load_all_experiences()
        if not experiences:
            return

        profile = self._empty_profile()
        profile["total_tasks"] = len(experiences)

        all_turns: list[int] = []
        success_count = 0
        fail_count = 0
        type_turns: dict[str, list[int]] = {}

        for exp in experiences:
            task_type = exp.get("task_type", "general")
            summary = exp.get("summary", "") or exp.get("fix_strategy", "")
            key_steps = exp.get("key_steps", [])
            task_desc = exp.get("task_description", "")
            success = exp.get("success", True)
            turns = exp.get("turns_taken", 0)
            project = exp.get("project_name", "")
            tool_seq = exp.get("tool_sequence", [])
            deprecated = exp.get("deprecated", False)

            if deprecated:
                continue

            # 1. 任务类型分布
            profile["task_type_dist"][task_type] = (
                profile["task_type_dist"].get(task_type, 0) + 1
            )

            # 2. 框架偏好
            text_pool = f"{task_desc} {summary} {' '.join(key_steps)}"
            self._extract_frameworks(text_pool, success, profile["framework_prefs"])

            # 3. 编码风格
            self._extract_style(text_pool, profile["style_hints"])

            # 4. 效率统计
            if success:
                success_count += 1
            else:
                fail_count += 1
            if turns > 0:
                all_turns.append(turns)
                type_turns.setdefault(task_type, []).append(turns)

            # 5. 工具模式
            if tool_seq:
                self._extract_tool_patterns(tool_seq, profile["tool_patterns"])

            # 6. 项目
            if project and project not in profile["recent_projects"]:
                profile["recent_projects"].append(project)

        # 计算效率
        total = success_count + fail_count
        profile["efficiency"]["total_success"] = success_count
        profile["efficiency"]["total_fail"] = fail_count
        profile["efficiency"]["success_rate"] = (
            round(success_count / total, 2) if total > 0 else 0.0
        )
        profile["efficiency"]["avg_turns"] = (
            round(sum(all_turns) / len(all_turns), 1) if all_turns else 0.0
        )

        # 擅长领域：成功次数多且平均轮数低的 task_type
        best_types: list[dict] = []
        for tt, turns_list in type_turns.items():
            type_success = sum(1 for t in turns_list if t > 0)
            if type_success >= 2:
                best_types.append({
                    "type": tt,
                    "count": profile["task_type_dist"].get(tt, 0),
                    "avg_turns": round(sum(turns_list) / len(turns_list), 1),
                })
        best_types.sort(key=lambda x: (-x["count"], x["avg_turns"]))
        profile["efficiency"]["best_task_types"] = best_types[:5]

        # 项目只保留最近 10 个
        profile["recent_projects"] = profile["recent_projects"][-10:]

        self._data = profile
        self._save()
        logger.info(
            f"用户画像已重建: {total} 条经验, "
            f"成功率 {profile['efficiency']['success_rate']}, "
            f"框架 {len(profile['framework_prefs'])} 个"
        )

    # ── 增量更新（每次 record 成功后调用） ───────────────────────

    def incremental_update(
        self,
        task_type: str,
        summary: str,
        key_steps: list[str],
        success: bool,
        turns: int,
        project_name: str = "",
        tool_sequence: list[dict] | None = None,
    ):
        """增量更新画像（不重新扫描全量经验库，O(1) 操作）"""
        self._data.setdefault("total_tasks", 0)
        self._data["total_tasks"] += 1

        # 1. 任务类型分布
        dist = self._data.setdefault("task_type_dist", {})
        dist[task_type] = dist.get(task_type, 0) + 1

        # 2. 框架偏好
        text_pool = f"{summary} {' '.join(key_steps)}"
        fw_prefs = self._data.setdefault("framework_prefs", {})
        self._extract_frameworks(text_pool, success, fw_prefs)

        # 3. 编码风格
        style = self._data.setdefault("style_hints", {})
        self._extract_style(text_pool, style)

        # 4. 效率
        eff = self._data.setdefault("efficiency", {
            "avg_turns": 0.0, "success_rate": 0.0,
            "total_success": 0, "total_fail": 0, "best_task_types": [],
        })
        if success:
            eff["total_success"] = eff.get("total_success", 0) + 1
        else:
            eff["total_fail"] = eff.get("total_fail", 0) + 1
        total = eff["total_success"] + eff["total_fail"]
        eff["success_rate"] = round(eff["total_success"] / total, 2) if total > 0 else 0.0

        # 增量平均轮数：running average
        if turns > 0:
            old_avg = eff.get("avg_turns", 0.0)
            old_count = max(total - 1, 0)
            eff["avg_turns"] = round(
                (old_avg * old_count + turns) / total, 1
            ) if total > 0 else float(turns)

        # 5. 工具模式
        if tool_sequence:
            tp = self._data.setdefault("tool_patterns", {})
            self._extract_tool_patterns(tool_sequence, tp)

        # 6. 项目
        if project_name:
            projects = self._data.setdefault("recent_projects", [])
            if project_name in projects:
                projects.remove(project_name)
            projects.append(project_name)
            self._data["recent_projects"] = projects[-10:]

        self._save()

    # ── 生成注入文本 ──────────────────────────────────────────────

    def get_injection_text(self, task_type: str = "", max_chars: int = 400) -> str:
        """生成可注入 LLM 的画像摘要

        格式紧凑，控制在 max_chars 以内。
        只输出有价值的信息，空值不输出。
        """
        if self._data.get("total_tasks", 0) < 3:
            return ""

        parts: list[str] = []

        # 框架偏好 TOP 5
        fw = self._data.get("framework_prefs", {})
        if fw:
            top_fw = sorted(fw.items(), key=lambda x: x[1].get("count", 0), reverse=True)[:5]
            fw_text = ", ".join(
                f"{name}({info['count']}次)" for name, info in top_fw
                if info.get("count", 0) >= 2
            )
            if fw_text:
                parts.append(f"[常用技术] {fw_text}")

        # 擅长领域
        best = self._data.get("efficiency", {}).get("best_task_types", [])
        if best:
            best_text = ", ".join(f"{b['type']}(avg {b['avg_turns']}轮)" for b in best[:3])
            parts.append(f"[擅长领域] {best_text}")

        # 编码风格
        style = self._data.get("style_hints", {})
        if style:
            top_style = sorted(style.items(), key=lambda x: x[1], reverse=True)[:3]
            style_items = [f"{k}" for k, v in top_style if v >= 3]
            if style_items:
                parts.append(f"[编码风格] {', '.join(style_items)}")

        # 效率
        eff = self._data.get("efficiency", {})
        avg = eff.get("avg_turns", 0)
        rate = eff.get("success_rate", 0)
        if avg > 0:
            parts.append(f"[效率] 平均 {avg} 轮完成, 成功率 {rate}")

        # 最近项目
        projects = self._data.get("recent_projects", [])
        if projects:
            parts.append(f"[活跃项目] {', '.join(projects[-3:])}")

        text = "\n".join(parts)
        if len(text) > max_chars:
            text = text[:max_chars - 3] + "..."

        return text

    def get_raw(self) -> dict:
        """返回完整画像数据（供 CLI 展示）"""
        return self._data.copy()

    # ── 内部方法 ──────────────────────────────────────────────────

    @staticmethod
    def _extract_frameworks(text: str, success: bool, fw_prefs: dict):
        """从文本中提取框架使用记录"""
        for name, pattern in _FRAMEWORK_PATTERNS:
            if pattern.search(text):
                entry = fw_prefs.setdefault(name, {"count": 0, "success": 0, "fail": 0})
                entry["count"] = entry.get("count", 0) + 1
                if success:
                    entry["success"] = entry.get("success", 0) + 1
                else:
                    entry["fail"] = entry.get("fail", 0) + 1

    @staticmethod
    def _extract_style(text: str, style_hints: dict):
        """从文本中提取编码风格线索"""
        for indicator, pattern in _STYLE_INDICATORS.items():
            matches = pattern.findall(text)
            if len(matches) >= 2:
                style_hints[indicator] = style_hints.get(indicator, 0) + 1

    @staticmethod
    def _extract_tool_patterns(tool_seq: list[dict], tool_patterns: dict):
        """提取工具使用频率"""
        for step in tool_seq[:10]:
            name = step.get("tool_name", step.get("name", ""))
            if name:
                tool_patterns[name] = tool_patterns.get(name, 0) + 1

    @staticmethod
    def _load_all_experiences() -> list[dict]:
        """从 experiences.json 加载全部经验"""
        if not EXPERIENCE_PATH.exists():
            return []
        try:
            data = json.loads(EXPERIENCE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return list(data.values())
            return []
        except Exception:
            return []


# ── 模块级便捷函数 ────────────────────────────────────────────────

def update_profile_incremental(
    task_type: str,
    summary: str,
    key_steps: list[str],
    success: bool,
    turns: int,
    project_name: str = "",
    tool_sequence: list[dict] | None = None,
):
    """便捷函数：增量更新用户画像（recorder.py 调用）"""
    try:
        profile = UserProfile()
        profile.incremental_update(
            task_type=task_type,
            summary=summary,
            key_steps=key_steps,
            success=success,
            turns=turns,
            project_name=project_name,
            tool_sequence=tool_sequence,
        )
    except Exception as e:
        logger.debug(f"增量更新画像失败（不影响主流程）: {e}")


def get_profile_context(task_type: str = "", max_chars: int = 400) -> str:
    """便捷函数：获取画像注入文本（planner.py 调用）"""
    try:
        profile = UserProfile()
        return profile.get_injection_text(task_type=task_type, max_chars=max_chars)
    except Exception:
        return ""


def rebuild_profile():
    """便捷函数：全量重建画像（CLI 或首次使用）"""
    try:
        profile = UserProfile()
        profile.rebuild_from_experiences()
    except Exception as e:
        logger.warning(f"重建画像失败: {e}")
