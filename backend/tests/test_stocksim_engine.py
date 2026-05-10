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


def test_news_at_legacy_tick_pattern_still_matches():
    """Legacy tick_pattern matchers must continue to fire after the bare-tick refactor."""
    state = {}
    config = {"events": [
        {"id": "every3", "tick_pattern": "every_3", "headline": "h", "symbols": ["X"], "severity": "info"},
        {"id": "once5",  "tick_pattern": "once_at_5", "headline": "h", "symbols": ["X"], "severity": "info"},
    ]}
    # every_3 fires on tick 3, 6, 9...
    assert any(item["id"] == "every3" for item in news_at(state, 3, config))
    assert any(item["id"] == "every3" for item in news_at(state, 6, config))
    assert not any(item["id"] == "every3" for item in news_at(state, 4, config))
    # once_at_5 fires only on tick 5
    assert any(item["id"] == "once5" for item in news_at(state, 5, config))
    assert not any(item["id"] == "once5" for item in news_at(state, 4, config))


def test_finalize_run_emits_trade_log_enriched():
    from engines.stocksim.scoring import enrich_trade_log
    state = {
        "trade_log": [
            {"tick": 4, "symbol": "TECHV", "side": "buy", "qty": 5, "price": 215, "realized_pnl": 0},
            {"tick": 10, "symbol": "TECHV", "side": "sell", "qty": 5, "price": 225, "realized_pnl": 50},
        ],
        "quote_history": {
            "TECHV": {4: {"mid": 215}, 10: {"mid": 225}},
            "INFOS": {4: {"mid": 380}, 10: {"mid": 390}},
        },
    }
    config = {"news": [{"tick": 4, "affected_symbols": ["TECHV"], "headline": "h", "reason": "r"}],
              "stocks": [{"symbol": "TECHV", "peers": [{"symbol": "INFOS"}]}]}
    enriched = enrich_trade_log(state, config, config["news"])
    assert len(enriched) == 2
    assert enriched[0]["news_at_tick"][0]["reason"] == "r"
    assert "INFOS" in enriched[0]["peer_perf_at_tick"]
