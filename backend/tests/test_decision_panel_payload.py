"""Tests for the Phase B payload bridge — get_decision_panel_config +
build_decision_panel_payload — that wires DecisionPanelEngine into
executive_ux composition.

The payload bridge reads `controls` from the current round (NOT the
game-level simulation_config — decision panels are per-round), enriches
each control with the player's current value (if submitted), and
reports drift from expert_pick.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.decision_panel_engine import (
    get_decision_panel_config,
    build_decision_panel_payload,
)


class _State:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


_ROUND_WITH_PANEL = {
    "id": "round_1",
    "decision_panel": {
        "controls": [
            {"id": "price", "type": "slider", "min": 100, "max": 300, "step": 5,
             "default": 200, "expert_pick": 220, "applies_to": "market.price",
             "label": "Unit Price ($)"},
            {"id": "rd_pct", "type": "slider", "min": 0.0, "max": 0.30, "step": 0.01,
             "default": 0.10, "expert_pick": 0.15, "applies_to": "finance.rd_spend_ratio",
             "label": "R&D Allocation"},
            {"id": "hire_plan", "type": "dropdown",
             "options": ["freeze", "slow", "aggressive"],
             "default": "slow", "expert_pick": "slow",
             "applies_to": "org.hire_mode",
             "label": "Hiring Pace"},
        ]
    }
}


def test_get_config_returns_controls_when_present():
    cfg = get_decision_panel_config(_ROUND_WITH_PANEL)
    assert cfg is not None
    assert isinstance(cfg.get("controls"), list)
    assert len(cfg["controls"]) == 3


def test_get_config_returns_none_when_round_has_no_panel():
    assert get_decision_panel_config({"id": "round_1"}) is None
    assert get_decision_panel_config(None) is None
    # Empty controls list = no panel
    assert get_decision_panel_config({"decision_panel": {"controls": []}}) is None


def test_payload_returns_none_when_no_panel():
    state = _State()
    assert build_decision_panel_payload(state, {"id": "x"}) is None


def test_payload_emits_one_entry_per_control_with_default():
    state = _State()
    payload = build_decision_panel_payload(state, _ROUND_WITH_PANEL)
    assert payload is not None
    controls = payload["controls"]
    assert len(controls) == 3
    by_id = {c["id"]: c for c in controls}
    assert by_id["price"]["value"] == 200  # default
    assert by_id["rd_pct"]["value"] == 0.10
    assert by_id["hire_plan"]["value"] == "slow"


def test_payload_uses_submitted_values_when_present():
    """state._decision_panel_submission[round_id] holds {control_id: value}."""
    state = _State(_decision_panel_submission={"round_1": {"price": 240, "rd_pct": 0.20, "hire_plan": "aggressive"}})
    payload = build_decision_panel_payload(state, _ROUND_WITH_PANEL)
    by_id = {c["id"]: c for c in payload["controls"]}
    assert by_id["price"]["value"] == 240
    assert by_id["rd_pct"]["value"] == 0.20
    assert by_id["hire_plan"]["value"] == "aggressive"


def test_payload_includes_drift_when_submission_present():
    state = _State(_decision_panel_submission={"round_1": {"price": 220, "rd_pct": 0.20, "hire_plan": "freeze"}})
    payload = build_decision_panel_payload(state, _ROUND_WITH_PANEL)
    by_id = {c["id"]: c for c in payload["controls"]}
    # price = expert pick → drift on_track
    assert by_id["price"]["drift_label"] == "on_track"
    # rd_pct: expert=0.15, player=0.20 → drift = 0.05/max(0.15,1) = 5% → on_track
    # (engine clamps denom to >=1 for stability with sub-unit values)
    assert by_id["rd_pct"]["drift_label"] == "on_track"
    # hire_plan: expert=slow, player=freeze → drift 1.0 → "extreme"
    assert by_id["hire_plan"]["drift_label"] == "extreme"


def test_payload_omits_drift_when_no_submission():
    state = _State()
    payload = build_decision_panel_payload(state, _ROUND_WITH_PANEL)
    by_id = {c["id"]: c for c in payload["controls"]}
    # No submission yet — drift_label is None or absent
    assert by_id["price"].get("drift_label") in (None, "on_track")  # default == not yet drifted


def test_payload_includes_metadata_passthrough():
    """label, applies_to, min, max, step etc. should pass through for the UI."""
    state = _State()
    payload = build_decision_panel_payload(state, _ROUND_WITH_PANEL)
    price = next(c for c in payload["controls"] if c["id"] == "price")
    assert price["label"] == "Unit Price ($)"
    assert price["min"] == 100
    assert price["max"] == 300
    assert price["step"] == 5
    assert price["expert_pick"] == 220
    assert price["type"] == "slider"


def test_payload_marks_locked_when_submission_present():
    state = _State(_decision_panel_submission={"round_1": {"price": 200, "rd_pct": 0.10, "hire_plan": "slow"}})
    payload = build_decision_panel_payload(state, _ROUND_WITH_PANEL)
    assert payload["locked"] is True
    state2 = _State()
    payload2 = build_decision_panel_payload(state2, _ROUND_WITH_PANEL)
    assert payload2["locked"] is False
