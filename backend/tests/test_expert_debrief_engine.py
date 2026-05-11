"""Tests for expert_debrief_engine — per-round 100-200 word commentary
explaining why expert_pick was the strong move, surfaced after the
player commits a decision_panel submission.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.expert_debrief_engine import (
    get_expert_debrief_config,
    build_expert_debrief_payload,
)


class _State:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


_ROUND_WITH_DEBRIEF = {
    "id": "round_1",
    "decision_panel": {
        "controls": [{"id": "price", "type": "slider", "min": 100, "max": 300,
                      "default": 200, "expert_pick": 220, "applies_to": "market.price"}]
    },
    "expert_debrief": {
        "title": "Why we'd lean into the premium tilt",
        "body": (
            "Holding margin while the new entrants chase volume is a textbook "
            "Aaker move. Your R&D escalation funds the product gap that lets "
            "you justify the premium. Cutting price here would cede the margin "
            "story that funds next-quarter R&D — a classic value-destruction trap."
        ),
        "expert_voice": "Prof. Aaker (paraphrased)",
        "tags": ["pricing", "competitive_strategy"],
    }
}


def test_get_config_returns_debrief_when_present():
    cfg = get_expert_debrief_config(_ROUND_WITH_DEBRIEF)
    assert cfg is not None
    assert cfg.get("title")
    assert cfg.get("body")


def test_get_config_returns_none_when_absent():
    assert get_expert_debrief_config({"id": "r"}) is None
    assert get_expert_debrief_config(None) is None
    assert get_expert_debrief_config({"expert_debrief": {}}) is None


def test_payload_returns_none_when_no_config():
    state = _State()
    assert build_expert_debrief_payload(state, {"id": "r"}) is None


def test_payload_returns_none_until_decision_committed():
    """Spec: debrief only unlocks after the player commits decision_panel.
    If no submission yet for this round, return None (or locked sentinel)."""
    state = _State()  # no _decision_panel_submission
    payload = build_expert_debrief_payload(state, _ROUND_WITH_DEBRIEF)
    # Either None (gated) or a payload with locked=True
    assert payload is None or payload.get("locked") is True


def test_payload_unlocked_after_decision_committed():
    state = _State(_decision_panel_submission={"round_1": {"price": 220}})
    payload = build_expert_debrief_payload(state, _ROUND_WITH_DEBRIEF)
    assert payload is not None
    assert payload.get("locked") is False
    assert payload["title"] == "Why we'd lean into the premium tilt"
    assert "Aaker" in payload["body"]
    assert payload["expert_voice"] == "Prof. Aaker (paraphrased)"


def test_payload_passes_through_tags():
    state = _State(_decision_panel_submission={"round_1": {"price": 220}})
    payload = build_expert_debrief_payload(state, _ROUND_WITH_DEBRIEF)
    assert "pricing" in payload.get("tags", [])
    assert "competitive_strategy" in payload.get("tags", [])


def test_payload_includes_round_id():
    state = _State(_decision_panel_submission={"round_1": {"price": 220}})
    payload = build_expert_debrief_payload(state, _ROUND_WITH_DEBRIEF)
    assert payload.get("round_id") == "round_1"
