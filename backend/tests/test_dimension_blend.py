import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from engines.dimension_utils import aggregate_behavioral_signals, compute_dimension_ci, blend_authored_behavioral


def test_aggregate_behavioral_signals_returns_dict_per_dimension():
    state = {
        "choice_history": [
            {"time_to_decide_ms": 8000, "deltas": {"money": 10}, "risk_level": "low"},
            {"time_to_decide_ms": 7500, "deltas": {"money": -5}, "risk_level": "low"},
            {"time_to_decide_ms": 12000, "deltas": {"money": 20}, "risk_level": "high"},
        ],
        "resource_trajectory": [
            {"money": 100},
            {"money": 110},
            {"money": 105},
            {"money": 125},
        ],
    }
    out = aggregate_behavioral_signals(state)
    assert isinstance(out, dict)
    for dim in ("strategic_thinking", "risk_tolerance", "delayed_gratification",
                "adaptability", "resilience", "empathy"):
        assert dim in out
        assert 0 <= out[dim] <= 100, f"{dim} score out of bounds: {out[dim]}"


def test_aggregate_with_empty_history_returns_neutral():
    state = {"choice_history": [], "resource_trajectory": []}
    out = aggregate_behavioral_signals(state)
    for dim in ("strategic_thinking", "risk_tolerance"):
        assert out[dim] == 50  # neutral when no signal


def test_recovery_pattern_increases_resilience():
    state = {
        "choice_history": [{"time_to_decide_ms": 5000, "deltas": {"money": -50}, "risk_level": "low"}] * 5,
        "resource_trajectory": [
            {"money": 100}, {"money": 50}, {"money": 60}, {"money": 80}, {"money": 95},
        ],
    }
    out = aggregate_behavioral_signals(state)
    assert out["resilience"] > 50, f"Expected resilience > 50 with recovery pattern, got {out['resilience']}"


def test_compute_dimension_ci_returns_low_high():
    samples = [60, 62, 58, 65, 61, 59, 63, 60, 62, 58]
    ci_low, ci_high = compute_dimension_ci(samples, alpha=0.10, B=200)
    assert ci_low < ci_high
    assert 50 < ci_low < 60
    assert 60 < ci_high < 70


def test_compute_dimension_ci_handles_single_sample():
    ci_low, ci_high = compute_dimension_ci([75], alpha=0.10, B=200)
    assert ci_low == ci_high == 75


def test_compute_dimension_ci_clips_to_0_100():
    ci_low, ci_high = compute_dimension_ci([95, 99, 100, 98, 97], alpha=0.10, B=200)
    assert ci_high <= 100
    assert ci_low >= 0


def test_blend_50_50():
    authored = {"strategic_thinking": 80, "empathy": 60}
    behavioral = {"strategic_thinking": 40, "empathy": 80}
    out = blend_authored_behavioral(authored, behavioral, w_authored=0.5, w_behavioral=0.5)
    assert out["strategic_thinking"] == 60
    assert out["empathy"] == 70


def test_blend_clips_to_0_100():
    authored = {"strategic_thinking": 120}
    behavioral = {"strategic_thinking": -20}
    out = blend_authored_behavioral(authored, behavioral, 0.5, 0.5)
    assert 0 <= out["strategic_thinking"] <= 100


def test_blend_uses_authored_when_behavioral_missing():
    out = blend_authored_behavioral({"empathy": 70}, {}, 0.5, 0.5)
    assert out["empathy"] == 70


def test_blend_returns_only_authored_keys():
    out = blend_authored_behavioral({"strategic_thinking": 50}, {"empathy": 80}, 0.5, 0.5)
    assert "empathy" not in out
    assert "strategic_thinking" in out


def test_rounds_scores_emit_v1_v2_and_ci():
    """_compute_rounds_dimension_scores must return {score_v1, score_v2, ci}.

    - score_v1 == legacy authored-only flat dict (back-compat).
    - score_v2 == 50/50 blend with behavioral signals.
    - ci has per-dimension {low, high} with low<=high and 0<=v<=100 across the board.
    """
    from app import _compute_rounds_dimension_scores

    state = {
        "choice_history": [
            {"time_to_decide_ms": 5000, "deltas": {"money": 10},
             "risk_level": "low", "skill_tags": ["empathy"]},
            {"time_to_decide_ms": 6000, "deltas": {"money": -5},
             "risk_level": "high", "skill_tags": ["risk_tolerance"]},
            {"time_to_decide_ms": 4000, "deltas": {"money": 20},
             "risk_level": "low", "skill_tags": ["strategic_thinking"]},
        ],
        "rounds_completed": [1, 2, 3],
        "total_rounds": 3,
        "resource_trajectory": [
            {"money": 100}, {"money": 110}, {"money": 105}, {"money": 125},
        ],
    }
    result = _compute_rounds_dimension_scores(state)

    assert isinstance(result, dict)
    assert "score_v1" in result
    assert "score_v2" in result
    assert "ci" in result

    v1 = result["score_v1"]
    v2 = result["score_v2"]
    ci = result["ci"]

    # score_v1 must contain the canonical six dimensions
    for dim in ("strategic_thinking", "risk_tolerance", "delayed_gratification",
                "adaptability", "resilience", "empathy"):
        assert dim in v1, f"score_v1 missing {dim}"
        assert 0 <= v1[dim] <= 100, f"score_v1[{dim}] out of bounds: {v1[dim]}"
        assert dim in v2, f"score_v2 missing {dim}"
        assert 0 <= v2[dim] <= 100, f"score_v2[{dim}] out of bounds: {v2[dim]}"
        assert dim in ci, f"ci missing {dim}"
        assert "low" in ci[dim] and "high" in ci[dim]
        assert ci[dim]["low"] <= ci[dim]["high"], (
            f"ci[{dim}]: low {ci[dim]['low']} > high {ci[dim]['high']}"
        )
        assert 0 <= ci[dim]["low"] <= 100
        assert 0 <= ci[dim]["high"] <= 100
