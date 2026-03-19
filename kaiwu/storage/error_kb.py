"""错误知识库 — 记录错误模式和解决方案，避免重复犯错

蒸馏自 CL 项目 engine/error_kb.py，去掉 CL 依赖，改用 ~/.kaiwu/ 存储。
存储在 ~/.kaiwu/error_kb.json（明文 JSON，便于调试和社区贡献）。
遇到匹配错误时注入已知解决方案，平时 0 额外 token。
"""

import base64
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Optional

from loguru import logger

from kaiwu.config import ERROR_KB_PATH, DATA_DIR

MAX_ENTRIES = 200


def _fingerprint(error_text: str) -> str:
    """提取错误指纹：去掉路径、数字等变量部分，保留错误模式"""
    # Windows 路径：C:\Users\xxx\... 或 D:\project\...
    text = re.sub(r'[A-Za-z]:[/\\][\w./\\:\-]+', '<PATH>', error_text)
    # Unix 路径：/home/xxx/... 或 ./relative/...
    text = re.sub(r'(?:\./|/(?!v1/))[\w./\-]+', '<PATH>', text)
    text = re.sub(r'line \d+', 'line <N>', text, flags=re.IGNORECASE)
    text = re.sub(r':\d+:\d+', ':<N>:<N>', text)
    text = re.sub(r'\d+\.\d+\.\d+', '<VER>', text)
    text = text.strip()[:200].lower()
    return hashlib.md5(text.encode()).hexdigest()[:16]


def _extract_error_key(error_text: str) -> str:
    """提取错误的核心关键词（用于快速匹配和展示）"""
    patterns = [
        r"(ModuleNotFoundError|ImportError):\s*(.+)",
        r"(SyntaxError):\s*(.+)",
        r"(TypeError|ValueError|KeyError|AttributeError):\s*(.+)",
        r"(FileNotFoundError|PermissionError):\s*(.+)",
        r"(npm ERR!)\s*(.+)",
        r"(Error|ENOENT|EACCES):\s*(.+)",
        r"(Cannot find module)\s*(.+)",
        r"(command not found):\s*(.+)",
    ]
    for pat in patterns:
        m = re.search(pat, error_text, re.IGNORECASE)
        if m:
            return f"{m.group(1)}: {m.group(2)[:80]}"
    for line in reversed(error_text.split("\n")):
        if "error" in line.lower():
            return line.strip()[:100]
    return error_text.strip()[:80]


def _fuzzy_match(query: str, entries: dict) -> Optional[dict]:
    """模糊匹配：提取关键词做交集匹配"""
    query_words = set(re.findall(r'[a-zA-Z_]\w+|[\u4e00-\u9fff]+', query.lower()))
    if not query_words:
        return None

    best_entry = None
    best_score = 0

    for fp, entry in entries.items():
        if not entry.get("solution"):
            continue
        error_words = set(re.findall(
            r'[a-zA-Z_]\w+|[\u4e00-\u9fff]+',
            (entry.get("key", "") + " " + entry.get("error", "")).lower()
        ))
        overlap = len(query_words & error_words)
        union = len(query_words | error_words)
        if union > 0:
            score = overlap / union
            if score > best_score and score > 0.5:
                best_score = score
                best_entry = entry

    return best_entry


class ErrorKB:
    """错误知识库"""

    def __init__(self, path: Optional[Path] = None):
        """初始化错误知识库

        Args:
            path: 存储路径，默认 ~/.kaiwu/error_kb.json
        """
        self._path = path or ERROR_KB_PATH
        self._data = self._load()
        # 合并预置错误库
        self._merge_preset()

    def _load(self) -> dict:
        """加载知识库（兼容旧版 base64 格式，自动迁移为明文）"""
        if not self._path.exists():
            return {"entries": {}, "version": 2}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            raw_entries = raw.get("entries", {})
            version = raw.get("version", 1)
            entries = {}

            if not raw_entries:
                return {"entries": {}, "version": 2}

            # 探测格式：取第一个 value 判断是 base64 字符串还是 dict
            first_val = next(iter(raw_entries.values()))

            if isinstance(first_val, str):
                # 旧格式：base64 编码，逐条解码迁移
                for fp, encoded in raw_entries.items():
                    try:
                        decoded = base64.b64decode(encoded).decode("utf-8")
                        entries[fp] = json.loads(decoded)
                    except Exception:
                        continue
                logger.info(f"已从旧版 base64 格式迁移 {len(entries)} 条错误记录")
            elif isinstance(first_val, dict):
                # 新格式：明文 JSON dict
                entries = raw_entries
            else:
                logger.warning(f"未知的 error_kb 格式，重置为空")
                return {"entries": {}, "version": 2}

            return {"entries": entries, "version": 2}
        except Exception as e:
            logger.warning(f"加载错误知识库失败: {e}")
            return {"entries": {}, "version": 2}

    def _merge_preset(self):
        """合并预置错误库 data/error_kb.json"""
        preset_path = DATA_DIR / "error_kb.json"
        if not preset_path.exists():
            return
        try:
            preset = json.loads(preset_path.read_text(encoding="utf-8"))
            for entry in preset.get("entries", []):
                fp = _fingerprint(entry.get("error", ""))
                if fp not in self._data["entries"]:
                    self._data["entries"][fp] = {
                        "key": entry.get("key", ""),
                        "error": entry.get("error", "")[:300],
                        "solution": entry.get("solution", ""),
                        "count": 0,
                        "first_seen": entry.get("first_seen", "preset"),
                        "last_seen": "preset",
                        "context": entry.get("context", ""),
                        "source": "preset",
                    }
            logger.debug(f"合并预置错误库: {len(preset.get('entries', []))} 条")
        except Exception as e:
            logger.debug(f"加载预置错误库失败: {e}")

    def _save(self):
        """保存知识库（明文 JSON，人类可读）"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(
                    {"entries": self._data["entries"], "version": 2},
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.warning(f"保存错误知识库失败: {e}")

    def record_error(self, error_text: str, context: str = "") -> str:
        """记录一个错误（尚未解决），返回 fingerprint"""
        fp = _fingerprint(error_text)
        key = _extract_error_key(error_text)
        entry = self._data["entries"].get(fp, {
            "key": key,
            "error": error_text[:300],
            "solution": "",
            "count": 0,
            "first_seen": time.strftime("%Y-%m-%d %H:%M"),
            "context": context[:100],
        })
        entry["count"] = entry.get("count", 0) + 1
        entry["last_seen"] = time.strftime("%Y-%m-%d %H:%M")
        self._data["entries"][fp] = entry
        self._trim()
        self._save()
        return fp

    def record_solution(self, error_fp: str, solution: str):
        """记录错误的解决方案"""
        if error_fp in self._data["entries"]:
            self._data["entries"][error_fp]["solution"] = solution[:500]
            self._save()

    def has_solution(self, error_fp: str) -> bool:
        """检查某个指纹对应的错误是否已有解决方案"""
        entry = self._data["entries"].get(error_fp)
        return bool(entry and entry.get("solution"))

    def find_solution(self, error_text: str) -> Optional[dict]:
        """查找匹配错误的已知解决方案

        Returns:
            dict with {source, key, solution} or None
        """
        # 第一层：精确指纹匹配
        fp = _fingerprint(error_text)
        entry = self._data["entries"].get(fp)
        if entry and entry.get("solution"):
            try:
                from kaiwu.llm_client import record_local_hit
                record_local_hit()
            except Exception:
                pass
            return {
                "source": "local_exact",
                "key": entry["key"],
                "solution": entry["solution"],
                "confidence": 0.95,
            }

        # 第二层：模糊关键词匹配
        fuzzy = _fuzzy_match(error_text, self._data["entries"])
        if fuzzy:
            try:
                from kaiwu.llm_client import record_local_hit
                record_local_hit()
            except Exception:
                pass
            return {
                "source": "local_fuzzy",
                "key": fuzzy["key"],
                "solution": fuzzy["solution"],
                "confidence": 0.7,
            }

        return None

    def get_stats(self) -> dict:
        """获取知识库统计"""
        entries = self._data["entries"]
        solved = sum(1 for e in entries.values() if e.get("solution"))
        return {
            "total": len(entries),
            "solved": solved,
            "unsolved": len(entries) - solved,
        }

    def get_all_entries(self) -> list[dict]:
        """获取所有条目（用于导出/贡献）"""
        return list(self._data["entries"].values())

    def _trim(self):
        """保持有界大小"""
        entries = self._data["entries"]
        if len(entries) > MAX_ENTRIES:
            sorted_keys = sorted(
                entries.keys(),
                key=lambda k: (
                    bool(entries[k].get("solution")),
                    entries[k].get("last_seen", ""),
                ),
            )
            for k in sorted_keys[:len(entries) - MAX_ENTRIES]:
                del entries[k]
