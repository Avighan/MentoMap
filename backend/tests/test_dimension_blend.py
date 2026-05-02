import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from engines.dimension_utils import aggregate_behavioral_signals


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
