"""planner / lessons / condenser 模块测试

planner: _parse_plan_json 解析各种格式
lessons: 三层匹配逻辑 + 循环检测附加
condenser: should_condense / compress_observation / extract_key_facts
"""

import json
import pytest
from unittest.mock import patch, MagicMock

# ================================================================
# planner: _parse_plan_json
# ================================================================

from kaiwu.planner import _parse_plan_json


class TestParsePlanJson:
    """测试 _parse_plan_json 的各种输入格式"""

    def test_pure_json(self):
        text = '{"steps": [{"seq": 1, "action": "read file", "reason": "understand"}], "trap_warnings": []}'
        result = _parse_plan_json(text)
        assert len(result["steps"]) == 1
        assert result["steps"][0]["action"] == "read file"

    def test_markdown_code_block(self):
        text = '```json\n{"steps": [{"seq": 1, "action": "test", "reason": "r"}], "trap_warnings": ["watch out"]}\n```'
        result = _parse_plan_json(text)
        assert len(result["steps"]) == 1
        assert len(result["trap_warnings"]) == 1

    def test_markdown_without_json_tag(self):
        text = '```\n{"steps": [], "trap_warnings": ["a"]}\n```'
        result = _parse_plan_json(text)
        assert result["trap_warnings"] == ["a"]

    def test_text_before_json(self):
        text = 'Here is my plan:\n\n{"steps": [{"seq": 1, "action": "do it", "reason": "why"}], "trap_warnings": []}'
        result = _parse_plan_json(text)
        assert len(result["steps"]) == 1

    def test_text_before_and_after_json(self):
        text = 'Plan:\n{"steps": [], "confidence": 0.9}\nHope this helps!'
        result = _parse_plan_json(text)
        assert result["confidence"] == 0.9

    def test_text_with_markdown_block_in_middle(self):
        text = 'I analyzed the task:\n\n```json\n{"steps": [{"seq": 1, "action": "a", "reason": "b"}], "trap_warnings": []}\n```\n\nLet me know if you need more.'
        result = _parse_plan_json(text)
        assert len(result["steps"]) == 1

    def test_truncated_json_repair(self):
        """模拟 max_tokens 截断的 JSON"""
        text = '{"steps": [{"seq": 1, "action": "read", "reason": "understand"}, {"seq": 2, "action": "write", "reason": "impl'
        # 截断了，应该尝试修复
        # 这个 case 可能修复也可能失败，关键是不 crash
        try:
            result = _parse_plan_json(text)
            assert "steps" in result
        except json.JSONDecodeError:
            pass  # 修复失败也 OK，只要不 crash

    def test_empty_json_object(self):
        result = _parse_plan_json("{}")
        assert result == {}

    def test_nested_json(self):
        text = '{"steps": [{"seq": 1, "action": "deploy", "reason": "go live"}], "trap_warnings": ["CORS"], "edge_cases": ["empty input"]}'
        result = _parse_plan_json(text)
        assert result["edge_cases"] == ["empty input"]

    def test_no_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _parse_plan_json("This is just plain text with no JSON at all.")

    def test_multiple_json_blocks_raises(self):
        """两个独立 JSON 对象拼在一起，无法解析"""
        with pytest.raises(json.JSONDecodeError):
            _parse_plan_json('{"steps": []} and also {"other": true}')

    def test_json_with_chinese(self):
        text = '{"steps": [{"seq": 1, "action": "读取配置文件", "reason": "了解现有结构"}], "trap_warnings": ["注意 UTF-8 编码"]}'
        result = _parse_plan_json(text)
        assert "读取" in result["steps"][0]["action"]


# ================================================================
# planner: get_plan (mocked LLM)
# ================================================================

class TestGetPlan:
    """测试 get_plan 的整体流程（mock LLM 调用）"""

    def test_empty_task_returns_empty(self):
        from kaiwu.planner import get_plan
        result = get_plan("")
        assert result["source"] == "empty"
        assert result["steps"] == []

    def test_whitespace_task_returns_empty(self):
        from kaiwu.planner import get_plan
        result = get_plan("   ")
        assert result["source"] == "empty"

    @patch("kaiwu.planner.check_quota", return_value=(False, "no key"))
    def test_quota_exceeded(self, mock_quota):
        from kaiwu.planner import get_plan
        result = get_plan("build a web app")
        assert result["source"] == "quota_exceeded"

    @patch("kaiwu.planner.check_quota", return_value=(True, ""))
    @patch("kaiwu.planner.call_llm")
    @patch("kaiwu.planner.record_call")
    def test_successful_plan(self, mock_record, mock_llm, mock_quota):
        mock_llm.return_value = json.dumps({
            "steps": [{"seq": 1, "action": "read files", "reason": "understand"}],
            "trap_warnings": ["watch encoding"],
            "confidence": 0.85,
        })
        from kaiwu.planner import get_plan
        result = get_plan("implement login API")
        assert result["source"] == "llm"
        assert len(result["steps"]) == 1
        assert result["confidence"] == 0.85

    @patch("kaiwu.planner.check_quota", return_value=(True, ""))
    @patch("kaiwu.planner.call_llm")
    @patch("kaiwu.planner.record_call")
    def test_llm_returns_markdown_wrapped(self, mock_record, mock_llm, mock_quota):
        mock_llm.return_value = '```json\n{"steps": [{"seq": 1, "action": "test", "reason": "r"}], "trap_warnings": []}\n```'
        from kaiwu.planner import get_plan
        result = get_plan("write tests")
        assert result["source"] == "llm"
        assert len(result["steps"]) == 1

    @patch("kaiwu.planner.check_quota", return_value=(True, ""))
    @patch("kaiwu.planner.call_llm")
    @patch("kaiwu.planner.record_call")
    def test_llm_returns_garbage(self, mock_record, mock_llm, mock_quota):
        mock_llm.return_value = "I cannot help with that."
        from kaiwu.planner import get_plan
        result = get_plan("do something")
        assert result["source"] == "parse_error"
        assert result["steps"] == []


# ================================================================
# lessons: get_lessons (mocked LLM)
# ================================================================

class TestGetLessons:
    """测试 lessons 三层匹配"""

    def test_empty_error_returns_empty(self):
        from kaiwu.lessons import get_lessons
        result = get_lessons("")
        assert result["confidence"] == 0.0

    @patch("kaiwu.lessons.get_error_kb")
    def test_layer1_exact_match(self, mock_get_kb):
        mock_kb = MagicMock()
        mock_kb.find_solution.return_value = {
            "key": "UnicodeDecodeError",
            "solution": "use encoding=utf-8",
            "confidence": 0.95,
            "source": "local_exact",
        }
        mock_get_kb.return_value = mock_kb

        from kaiwu.lessons import get_lessons
        result = get_lessons("UnicodeDecodeError: gbk codec")
        assert result["source"] == "local_exact"
        assert result["confidence"] == 0.95

    @patch("kaiwu.lessons.get_error_kb")
    def test_layer2_fuzzy_match(self, mock_get_kb):
        mock_kb = MagicMock()
        mock_kb.find_solution.return_value = {
            "key": "ModuleNotFoundError",
            "solution": "pip install Pillow",
            "confidence": 0.7,
            "source": "local_fuzzy",
        }
        mock_get_kb.return_value = mock_kb

        from kaiwu.lessons import get_lessons
        result = get_lessons("ModuleNotFoundError: No module named PIL")
        assert result["source"] == "local_fuzzy"

    @patch("kaiwu.lessons.get_error_kb")
    @patch("kaiwu.lessons.check_quota", return_value=(True, ""))
    @patch("kaiwu.lessons.call_llm")
    @patch("kaiwu.lessons.record_call")
    def test_layer3_llm_fallback(self, mock_record, mock_llm, mock_quota, mock_get_kb):
        mock_kb = MagicMock()
        mock_kb.find_solution.return_value = None  # no local match
        mock_kb.record_error.return_value = "fp_123"
        mock_get_kb.return_value = mock_kb

        mock_llm.return_value = json.dumps({
            "root_cause": "Invalid bcrypt salt",
            "fix_suggestion": "Check salt generation",
            "confidence": 0.8,
        })

        from kaiwu.lessons import get_lessons
        result = get_lessons("ValueError: Invalid salt")
        assert result["source"] == "llm"
        assert result["confidence"] == 0.8

    @patch("kaiwu.lessons.get_error_kb")
    @patch("kaiwu.lessons.check_quota", return_value=(False, "no key"))
    def test_layer3_quota_exceeded(self, mock_quota, mock_get_kb):
        mock_kb = MagicMock()
        mock_kb.find_solution.return_value = None
        mock_kb.record_error.return_value = "fp_123"
        mock_get_kb.return_value = mock_kb

        from kaiwu.lessons import get_lessons
        result = get_lessons("SomeUnknownError: weird")
        assert result["source"] == "quota_exceeded"


# ================================================================
# condenser: should_condense
# ================================================================

from kaiwu.condenser import should_condense, compress_observation, extract_key_facts


class TestShouldCondense:

    def test_below_threshold(self):
        assert should_condense(10) is False

    def test_at_threshold(self):
        assert should_condense(15) is True

    def test_above_threshold_not_multiple(self):
        assert should_condense(20) is False

    def test_double_threshold(self):
        assert should_condense(30) is True

    def test_triple_threshold(self):
        assert should_condense(45) is True

    def test_zero(self):
        assert should_condense(0) is False

    def test_custom_threshold(self):
        assert should_condense(10, threshold=10) is True
        assert should_condense(10, threshold=5) is True
        assert should_condense(7, threshold=5) is False


# ================================================================
# condenser: compress_observation
# ================================================================

class TestCompressObservation:

    def test_short_text_unchanged(self):
        text = "hello world"
        assert compress_observation(text) == text

    def test_long_text_truncated(self):
        text = "x" * 5000
        result = compress_observation(text, max_chars=1000)
        assert len(result) <= 1100  # some overhead for separator
        assert "已截断" in result

    def test_traceback_compressed(self):
        lines = ["Traceback (most recent call last):"]
        for i in range(50):
            lines.append(f'  File "module{i}.py", line {i}')
            lines.append(f"    func{i}()")
        lines.append("ValueError: bad value")
        text = "\n".join(lines)
        result = compress_observation(text, max_chars=500)
        assert "ValueError" in result

    def test_file_tree_compressed(self):
        lines = []
        for i in range(100):
            lines.append(f"src/module{i}/file{i}.py")
        # Add some noise dirs
        lines.append("node_modules/something/file.js")
        lines.append("__pycache__/cache.pyc")
        text = "\n".join(lines)
        result = compress_observation(text, max_chars=500)
        assert len(result) <= 600


# ================================================================
# condenser: extract_key_facts
# ================================================================

class TestExtractKeyFacts:

    def test_extract_framework(self):
        facts = extract_key_facts("我们使用了 FastAPI 框架来构建后端")
        assert any("FastAPI" in f for f in facts)

    def test_extract_database(self):
        facts = extract_key_facts("数据库: SQLite，存储在 ./data/app.db")
        assert any("SQLite" in f for f in facts)

    def test_extract_port(self):
        facts = extract_key_facts("服务运行在端口: 8080")
        assert any("8080" in f for f in facts)

    def test_extract_encoding(self):
        facts = extract_key_facts("所有文件统一编码: utf-8")
        assert any("utf-8" in f.lower() for f in facts)

    def test_no_facts(self):
        facts = extract_key_facts("just some random text without any technical decisions")
        # May or may not find facts, but should not crash
        assert isinstance(facts, list)

    def test_multiple_facts(self):
        text = "使用了 React 框架，数据库: PostgreSQL，端口: 3000"
        facts = extract_key_facts(text)
        assert len(facts) >= 2

    def test_max_5_facts(self):
        text = (
            "使用了 FastAPI 框架，数据库: MySQL，端口: 8000，"
            "编码: utf-8，入口文件: main.py，版本 python 3.12，"
            "还有 React 和 Redis"
        )
        facts = extract_key_facts(text)
        assert len(facts) <= 5


# ================================================================
# condenser: condense_history (mocked LLM)
# ================================================================

class TestCondenseHistory:

    def test_empty_history(self):
        from kaiwu.condenser import condense_history
        result = condense_history([], "build app")
        assert result["progress_summary"] == ""
        assert result["anchors"] == []

    @patch("kaiwu.condenser.check_quota", return_value=(False, "no key"))
    def test_quota_exceeded(self, mock_quota):
        from kaiwu.condenser import condense_history
        result = condense_history([{"turn": 1, "action": "read"}], "build app")
        assert result["progress_summary"] == ""

    @patch("kaiwu.condenser.check_quota", return_value=(True, ""))
    @patch("kaiwu.condenser.call_llm")
    @patch("kaiwu.condenser.record_call")
    def test_successful_condense(self, mock_record, mock_llm, mock_quota):
        mock_llm.return_value = json.dumps({
            "task_goal": "build login",
            "progress_summary": "Implemented JWT auth",
            "anchors": ["framework: FastAPI"],
            "pending_issues": ["add rate limiting"],
            "key_files": ["main.py"],
        })
        from kaiwu.condenser import condense_history
        history = [{"turn": i, "action": f"step {i}", "result": f"done {i}"} for i in range(20)]
        result = condense_history(history, "build login")
        assert result["progress_summary"] == "Implemented JWT auth"
        assert len(result["anchors"]) == 1


# ================================================================
# scene: 关键词补充验证
# ================================================================

class TestSceneKeywords:
    """验证新增的关键词能正确匹配"""

    def test_vue_matches_web(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("Vue3 + Element Plus admin panel")
        scene_names = [s[0] for s in scenes]
        assert "web" in scene_names

    def test_angular_matches_web(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("Angular dashboard component")
        scene_names = [s[0] for s in scenes]
        assert "web" in scene_names

    def test_svelte_matches_web(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("Svelte app with vite")
        scene_names = [s[0] for s in scenes]
        assert "web" in scene_names

    def test_docker_matches_deploy(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("docker-compose deployment")
        scene_names = [s[0] for s in scenes]
        assert "china_deploy" in scene_names

    def test_mongodb_matches_database(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("MongoDB aggregation pipeline")
        scene_names = [s[0] for s in scenes]
        assert "database" in scene_names

    def test_express_matches_backend(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("Express.js REST API")
        scene_names = [s[0] for s in scenes]
        assert "backend_api" in scene_names

    def test_scrapy_matches_scraping(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("Scrapy spider for news")
        scene_names = [s[0] for s in scenes]
        assert "web_scraping" in scene_names

    def test_wechat_miniprogram(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("wechat miniprogram login")
        scene_names = [s[0] for s in scenes]
        assert "wechat_pay" in scene_names

    def test_jest_matches_test(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("jest unit test React component")
        scene_names = [s[0] for s in scenes]
        assert "test_case" in scene_names

    def test_numpy_matches_data_analysis(self):
        from kaiwu.scene import detect_scenes_multi
        scenes = detect_scenes_multi("numpy matrix computation")
        scene_names = [s[0] for s in scenes]
        assert "data_analysis" in scene_names
