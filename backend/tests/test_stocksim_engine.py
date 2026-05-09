import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.stocksim.events import news_at, event_at


def test_news_at_matches_direct_tick_field():
    """Production JSONs use {"tick": N}, not {"tick_pattern": "once_at_N"}. news_at must match both."""
    state = {}
    config = {"events": [{"id": "e1", "tick": 4, "headline": "h", "symbols": ["TECHV"],
                          "severity": "info", "reason": "Large contract"}]}
    out = news_at(state, 4, config)
    assert any(item["id"] == "e1" for item in out), "news_at should match events with bare 'tick' field"


def test_news_at_stamps_recent_reasons():
    """When an event with a reason matches, news_at must populate state['recent_reasons']."""
    state = {}
    config = {"events": [{"id": "e1", "tick": 4, "headline": "TechVista wins ₹500Cr",
                          "symbols": ["TECHV"], "severity": "info",
                          "reason": "Large contract → revenue"}]}
    news_at(state, 4, config)
    assert "TECHV" in state.get("recent_reasons", {})
    assert state["recent_reasons"]["TECHV"]["tick"] == 4
    assert "Large contract" in state["recent_reasons"]["TECHV"]["reason"]


def test_recent_reason_visible_within_two_ticks():
    """Reason should be readable for ticks 4, 5, 6, then expire at 7. Mirrors /state route logic."""
    state = {}
    config = {"events": [{"id": "e1", "tick": 4, "headline": "h", "symbols": ["TECHV"],
                          "severity": "info", "reason": "r"}]}
    news_at(state, 4, config)

    def visible_reason(state, tick, sym):
        rec = state.get("recent_reasons", {}).get(sym)
        if not rec:
            return None
        if tick - rec["tick"] <= 2:
            return rec["reason"]
        return None

    assert visible_reason(state, 4, "TECHV") == "r"
    assert visible_reason(state, 5, "TECHV") == "r"
    assert visible_reason(state, 6, "TECHV") == "r"
    assert visible_reason(state, 7, "TECHV") is None
