"""记录器 + 审计逻辑单元测试"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pytest
from unittest.mock import patch, MagicMock

from kaiwu.storage.experience import TraceStep
from kaiwu.recorder import _should_audit, record_outcome


# ── 辅助函数 ──────────────────────────────────────────────────────

def make_steps(n, all_success=True, fail_indices=None, pivot_indices=None):
    """生成 n 个 TraceStep，可指定哪些步骤失败/pivot"""
    fail_indices = fail_indices or []
    pivot_indices = pivot_indices or []
    steps = []
    for i in range(1, n + 1):
        steps.append(TraceStep(
            turn=i,
            action=f"action {i}",
            outcome=f"outcome {i}",
            success=(i not in fail_indices),
            pivot=(i in pivot_indices),
        ))
    return steps


# ── _should_audit 门控 ────────────────────────────────────────────

def test_should_audit_empty_trace():
    assert _should_audit(True, 5, [], "strong") is False


def test_should_audit_none_trace():
    assert _should_audit(True, 5, None, "strong") is False


def test_should_audit_less_than_3_steps():
    steps = make_steps(2)
    assert _should_audit(True, 5, steps, "strong") is False


def test_should_audit_strong_task_failed():
    steps = make_steps(3)
    assert _should_audit(False, 3, steps, "strong") is True


def test_should_audit_strong_has_failed_step():
    steps = make_steps(3, fail_indices=[2])
    assert _should_audit(True, 3, steps, "strong") is True


def test_should_audit_strong_has_pivot():
    steps = make_steps(3, pivot_indices=[2])
    assert _should_audit(True, 3, steps, "strong") is True


def test_should_audit_strong_success_turns_ge_5():
    steps = make_steps(5)
    assert _should_audit(True, 5, steps, "strong") is True


def test_should_audit_strong_short_all_success():
    steps = make_steps(3)
    assert _should_audit(True, 2, steps, "strong") is False


def test_should_audit_weak_fail_turns_ge_5():
    steps = make_steps(5)
    assert _should_audit(False, 5, steps, "weak") is True


def test_should_audit_weak_fail_turns_lt_5():
    steps = make_steps(3)
    assert _should_audit(False, 3, steps, "weak") is False


def test_should_audit_weak_success_2_failed_steps():
    steps = make_steps(4, fail_indices=[1, 2])
    assert _should_audit(True, 4, steps, "weak") is True


def test_should_audit_weak_success_1_failed_step():
    steps = make_steps(4, fail_indices=[1])
    # 只有1个失败步骤，不满足 >= 2
    assert _should_audit(True, 4, steps, "weak") is False


def test_should_audit_weak_pivot():
    steps = make_steps(3, pivot_indices=[2])
    assert _should_audit(True, 3, steps, "weak") is True


def test_should_audit_weak_success_turns_ge_6():
    steps = make_steps(6)
    assert _should_audit(True, 6, steps, "weak") is True


def test_should_audit_weak_short_simple():
    steps = make_steps(3)
    assert _should_audit(True, 3, steps, "weak") is False


# ── record_outcome 向后兼容 ───────────────────────────────────────

@pytest.fixture
def mock_exp_store(tmp_path):
    """mock ExperienceStore，避免写真实文件"""
    from kaiwu.storage.experience import Experience, _make_exp_id
    mock_store = MagicMock()
    mock_exp = Experience(
        exp_id="test_exp_id_abc",
        task_type="web",
        task_description="实现用户登录功能，使用 JWT 认证",
        summary="JWT 登录",
    )
    mock_store.record.return_value = mock_exp
    return mock_store


@pytest.fixture
def mock_error_kb():
    mock_kb = MagicMock()
    mock_kb.record_error.return_value = "fp_abc123"
    return mock_kb


def test_record_outcome_no_trace_steps(mock_exp_store, mock_error_kb):
    with patch("kaiwu.recorder.get_experience_store", return_value=mock_exp_store), \
         patch("kaiwu.recorder.get_error_kb", return_value=mock_error_kb), \
         patch("kaiwu.recorder.check_quota", return_value=(False, "")):
        result = record_outcome(
            task="实现用户登录功能，使用 JWT 认证",
            task_type="web",
            success=True,
            turns=2,
        )
    assert isinstance(result, dict)
    assert "message" in result
    assert "exp_id" in result
    assert "轨迹审计" not in result["message"]


def test_record_outcome_short_trace_no_audit(mock_exp_store, mock_error_kb):
    steps = make_steps(2)  # < 3 步，不触发审计
    with patch("kaiwu.recorder.get_experience_store", return_value=mock_exp_store), \
         patch("kaiwu.recorder.get_error_kb", return_value=mock_error_kb), \
         patch("kaiwu.recorder.check_quota", return_value=(False, "")):
        result = record_outcome(
            task="实现用户登录功能，使用 JWT 认证",
            task_type="web",
            success=True,
            turns=2,
            trace_steps=steps,
            host_level="strong",
        )
    assert "轨迹审计" not in result["message"]


def test_record_outcome_success_returns_exp_id(mock_exp_store, mock_error_kb):
    with patch("kaiwu.recorder.get_experience_store", return_value=mock_exp_store), \
         patch("kaiwu.recorder.get_error_kb", return_value=mock_error_kb), \
         patch("kaiwu.recorder.check_quota", return_value=(False, "")):
        result = record_outcome(
            task="实现用户登录功能，使用 JWT 认证",
            task_type="web",
            success=True,
            turns=2,
        )
    assert result["exp_id"] != ""


def test_record_outcome_failure_returns_empty_exp_id(mock_exp_store, mock_error_kb):
    mock_exp_store.record.return_value = None
    with patch("kaiwu.recorder.get_experience_store", return_value=mock_exp_store), \
         patch("kaiwu.recorder.get_error_kb", return_value=mock_error_kb), \
         patch("kaiwu.recorder.check_quota", return_value=(False, "")):
        result = record_outcome(
            task="实现用户登录功能，使用 JWT 认证",
            task_type="web",
            success=False,
            error_summary="JWT secret 未配置",
            turns=3,
        )
    assert result["exp_id"] == ""


def test_record_outcome_returns_dict():
    with patch("kaiwu.recorder.get_experience_store") as mock_get_store, \
         patch("kaiwu.recorder.get_error_kb") as mock_get_kb, \
         patch("kaiwu.recorder.check_quota", return_value=(False, "")):
        mock_store = MagicMock()
        mock_store.record.return_value = None
        mock_get_store.return_value = mock_store
        mock_kb = MagicMock()
        mock_kb.record_error.return_value = "fp_xyz"
        mock_get_kb.return_value = mock_kb

        result = record_outcome(
            task="短任务",
            task_type="web",
            success=True,
        )
    assert isinstance(result, dict)
    assert "message" in result
    assert "exp_id" in result


if __name__ == "__main__":
    passed = failed = 0
    for name, func in list(globals().items()):
        if name.startswith("test_") and callable(func):
            try:
                func()
                print(f"  PASS: {name}")
                passed += 1
            except Exception as e:
                print(f"  FAIL: {name} — {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
