"""Tests for module composite v2 (Task 13) and worksheet grader (Task 14)."""
import pytest

from modules_engine import compute_module_composite_v2
from llm import grade_worksheet_freetext, _WORKSHEET_GRADE_CACHE


def _sample_module():
    """Minimal 1-week module fixture with 4 lessons covering quiz/worksheet/reflection/game."""
    return {
        "module_id": "test_module_v2",
        "weeks": [
            {
                "week_id": "w1",
                "number": 1,
                "title": "Week 1",
                "lessons": [
                    {"lesson_id": "L1_quiz", "type": "quiz", "skill_tags": ["strategic_thinking"]},
                    {"lesson_id": "L2_ws", "type": "worksheet", "skill_tags": ["creativity"]},
                    {"lesson_id": "L3_refl", "type": "reflection", "skill_tags": ["empathy"]},
                    {"lesson_id": "L4_game", "type": "game", "skill_tags": ["strategic_thinking", "empathy"]},
                ],
            }
        ],
        "expected_time_minutes": 60,  # 60 min total expected
    }


def _sample_progress():
    """Progress with all 5 channels populated."""
    return {
        "module_id": "test_module_v2",
        "completed_lesson_ids": ["L1_quiz", "L2_ws", "L3_refl", "L4_game"],
        "quizzes": {
            "L1_quiz": {"score": 8, "max_score": 10, "ratio": 0.8, "passed": True},
        },
        "worksheets": {
            "L2_ws": {
                "answers": {"problem": "Working parents struggle to find tutoring."},
                "rubric": {"score": 70, "dim_signals": {"creativity": 5}},
            },
        },
        "reflections": {
            "L3_refl": {
                "answers": {"reflect": "I learned that being on time matters because trust compounds."},
            },
        },
        "game_runs": {"L4_game": ["run_abc"]},
        "lesson_meta": {
            "L1_quiz": {"time_spent_seconds": 600},
            "L2_ws": {"time_spent_seconds": 900},
            "L3_refl": {"time_spent_seconds": 600},
            "L4_game": {"time_spent_seconds": 1200},
        },
        "anchored_game_dim_avg": {
            "L4_game": {"strategic_thinking": 72, "empathy": 65},
        },
        "dim_baseline": {
            "strategic_thinking": 50,
            "empathy": 55,
            "creativity": 50,
        },
        "dim_current": {
            "strategic_thinking": 70,
            "empathy": 65,
            "creativity": 58,
        },
    }


def test_compute_module_composite_v2_returns_5_channels():
    out = compute_module_composite_v2(_sample_progress(), _sample_module())
    assert "score" in out
    assert "channels" in out
    for ch in ("quiz_avg", "rubric_avg", "reflection_depth", "anchored_game_dim_avg", "time_on_task"):
        assert ch in out["channels"], f"missing channel {ch}"
    assert "weights" in out
    assert "per_dim_delta" in out


def test_quiz_avg_channel():
    prog = _sample_progress()
    out = compute_module_composite_v2(prog, _sample_module())
    # 0.8 ratio -> 80 on a 0-100 scale
    assert out["channels"]["quiz_avg"] == 80


def test_rubric_avg_channel():
    out = compute_module_composite_v2(_sample_progress(), _sample_module())
    assert out["channels"]["rubric_avg"] == 70


def test_anchored_game_dim_avg_channel():
    out = compute_module_composite_v2(_sample_progress(), _sample_module())
    # mean of 72 and 65 = 68.5 -> 68 (int)
    assert out["channels"]["anchored_game_dim_avg"] == 68


def test_per_dim_delta():
    out = compute_module_composite_v2(_sample_progress(), _sample_module())
    deltas = out["per_dim_delta"]
    assert deltas["strategic_thinking"] == 20  # 70 - 50
    assert deltas["empathy"] == 10              # 65 - 55
    assert deltas["creativity"] == 8            # 58 - 50


def test_handles_empty_progress():
    """Bare progress should not crash; channels may be None or 0."""
    empty_prog = {"module_id": "test_module_v2", "completed_lesson_ids": []}
    out = compute_module_composite_v2(empty_prog, _sample_module())
    assert "channels" in out
    assert out["channels"]["quiz_avg"] is None or out["channels"]["quiz_avg"] == 0
    # Score still computable (None channels skipped)
    assert isinstance(out["score"], int)
    assert 0 <= out["score"] <= 100


def test_weights_sum_to_one():
    out = compute_module_composite_v2(_sample_progress(), _sample_module())
    assert abs(sum(out["weights"].values()) - 1.0) < 1e-6


def test_time_on_task_normalized():
    """Total time in sample = 3300s = 55min; expected = 60min; ratio ~ 0.917 -> 91 or 92."""
    out = compute_module_composite_v2(_sample_progress(), _sample_module())
    val = out["channels"]["time_on_task"]
    assert 80 <= val <= 100, f"got {val}"


# ---- Task 14: Worksheet LLM grader ------------------------------------------

@pytest.fixture(autouse=True)
def _clear_worksheet_cache():
    """Each worksheet test starts with an empty cache."""
    _WORKSHEET_GRADE_CACHE.clear()
    yield
    _WORKSHEET_GRADE_CACHE.clear()


def test_grade_worksheet_returns_expected_shape(monkeypatch):
    def fake_call(system_prompt, user_prompt, **kwargs):
        return {
            "score": 78,
            "strengths": ["Clear customer profile", "Specific metrics"],
            "improvements": ["Validate willingness to pay"],
            "dim_signals": {"creativity": 5, "commercial_acumen": 6},
        }
    monkeypatch.setattr("llm._call_llm_json", fake_call)
    rubric = {
        "anchors": {
            "novice": "Vague problem statement",
            "capable": "Specific user, specific pain",
            "strong": "Specific user + specific pain + measurable size",
            "exec": "All of strong, plus differentiated wedge",
        },
        "signals": ["mentions specific user", "quantifies pain"],
    }
    out = grade_worksheet_freetext(
        text="Working parents struggle to find affordable after-school tutoring; market is ~$2B.",
        lesson={"id": "lesson_idea_scorecard", "type": "idea_scorecard"},
        rubric=rubric,
    )
    assert out["score"] == 78
    assert "Validate willingness to pay" in out["improvements"]
    assert "Clear customer profile" in out["strengths"]


def test_grade_worksheet_caches_by_content_hash(monkeypatch):
    call_count = {"n": 0}
    def fake_call(system_prompt, user_prompt, **kwargs):
        call_count["n"] += 1
        return {"score": 70, "strengths": [], "improvements": [], "dim_signals": {}}
    monkeypatch.setattr("llm._call_llm_json", fake_call)
    rubric = {"anchors": {}, "signals": []}
    grade_worksheet_freetext("same text", {"id": "L1", "type": "reflection"}, rubric)
    grade_worksheet_freetext("same text", {"id": "L1", "type": "reflection"}, rubric)
    assert call_count["n"] == 1, "Second identical call should hit cache"


def test_grade_worksheet_handles_empty_text():
    out = grade_worksheet_freetext("", {"id": "L1", "type": "reflection"}, {"anchors": {}, "signals": []})
    assert out["score"] == 0
    assert out["dim_signals"] == {}
    assert out["strengths"] == []
    assert out["improvements"] == []


def test_grade_worksheet_clamps_score_and_signals(monkeypatch):
    def fake_call(system_prompt, user_prompt, **kwargs):
        return {
            "score": 250,
            "strengths": ["a"],
            "improvements": [],
            "dim_signals": {"creativity": 100, "commercial_acumen": -100},
        }
    monkeypatch.setattr("llm._call_llm_json", fake_call)
    out = grade_worksheet_freetext(
        "Some answer text here.",
        {"id": "L2", "type": "reflection"},
        {"anchors": {}, "signals": []},
    )
    assert 0 <= out["score"] <= 100
    for v in out["dim_signals"].values():
        assert -10 <= v <= 10


def test_grade_worksheet_rubric_version_invalidates_cache(monkeypatch):
    """Different rubric versions should produce different cache keys."""
    call_count = {"n": 0}
    def fake_call(system_prompt, user_prompt, **kwargs):
        call_count["n"] += 1
        return {"score": 60, "strengths": [], "improvements": [], "dim_signals": {}}
    monkeypatch.setattr("llm._call_llm_json", fake_call)
    grade_worksheet_freetext("identical text", {"id": "L1", "type": "reflection"},
                             {"anchors": {}, "signals": [], "version": "v1"})
    grade_worksheet_freetext("identical text", {"id": "L1", "type": "reflection"},
                             {"anchors": {}, "signals": [], "version": "v2"})
    assert call_count["n"] == 2, "Different rubric_version should bypass cache"
