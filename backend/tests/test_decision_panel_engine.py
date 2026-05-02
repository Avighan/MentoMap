import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from engines.decision_panel_engine import DecisionPanelEngine


CONTROLS = [
    {"id": "price", "type": "slider", "min": 100, "max": 300, "step": 5,
     "default": 200, "expert_pick": 220, "applies_to": "market.price"},
    {"id": "rd_pct", "type": "slider", "min": 0.0, "max": 0.30, "step": 0.01,
     "default": 0.10, "expert_pick": 0.15, "applies_to": "finance.rd_spend_ratio"},
    {"id": "hire_plan", "type": "dropdown",
     "options": ["freeze", "slow", "aggressive"],
     "default": "slow", "expert_pick": "slow", "applies_to": "org.hire_mode"},
]


def test_validate_passes_within_range():
    eng = DecisionPanelEngine()
    ok, errs = eng.validate_submission(CONTROLS, {"price": 220, "rd_pct": 0.15, "hire_plan": "slow"})
    assert ok
    assert errs == []


def test_validate_rejects_slider_out_of_range():
    eng = DecisionPanelEngine()
    ok, errs = eng.validate_submission(CONTROLS, {"price": 999, "rd_pct": 0.15, "hire_plan": "slow"})
    assert not ok
    assert any("price" in e for e in errs)


def test_validate_rejects_dropdown_invalid():
    eng = DecisionPanelEngine()
    ok, errs = eng.validate_submission(CONTROLS, {"price": 200, "rd_pct": 0.15, "hire_plan": "panic"})
    assert not ok
    assert any("hire_plan" in e for e in errs)


def test_apply_submission_writes_dotted_path():
    eng = DecisionPanelEngine()
    state = {}
    eng.apply_submission(state, CONTROLS, {"price": 240, "rd_pct": 0.20, "hire_plan": "aggressive"})
    assert state["market"]["price"] == 240
    assert state["finance"]["rd_spend_ratio"] == 0.20
    assert state["org"]["hire_mode"] == "aggressive"


def test_compute_drift_numeric_on_track():
    eng = DecisionPanelEngine()
    drift = eng.compute_drift(CONTROLS, {"price": 220, "rd_pct": 0.15, "hire_plan": "slow"})
    assert drift["price"]["drift_pct"] == 0.0
    assert drift["price"]["drift_label"] == "on_track"
    assert drift["hire_plan"]["drift_label"] == "on_track"


def test_compute_drift_numeric_extreme():
    eng = DecisionPanelEngine()
    drift = eng.compute_drift(CONTROLS, {"price": 110, "rd_pct": 0.0, "hire_plan": "freeze"})
    # price: |110-220|/220 = 0.5 → wide
    assert drift["price"]["drift_label"] == "wide"
    # hire_plan: not equal → 1.0 → extreme
    assert drift["hire_plan"]["drift_label"] == "extreme"


def test_commit_round_raises_on_invalid():
    eng = DecisionPanelEngine()
    with pytest.raises(ValueError):
        eng.commit_round({}, CONTROLS, {"price": 9999, "rd_pct": 0.15, "hire_plan": "slow"})


def test_commit_round_returns_full_payload():
    eng = DecisionPanelEngine()
    out = eng.commit_round({}, CONTROLS, {"price": 220, "rd_pct": 0.15, "hire_plan": "slow"})
    assert "state" in out
    assert "drift" in out
    assert "applied" in out
    assert out["applied"]["price"] == 220
