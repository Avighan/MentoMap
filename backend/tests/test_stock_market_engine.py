"""Unit tests for StockMarketEngine (real-time stock simulator)."""
import pytest
from engines.stock_market_engine import StockMarketEngine


VALID_CONFIG = {
    "tick_count": 22,
    "tick_interval_seconds": 8,
    "starting_capital": 100000,
    "realism_tier": 2,
    "tick_authority": "hybrid",
    "settlement": "T+1",
    "shorting_enabled": False,
    "circuit_breaker_pct": [5, 10, 20],
    "stocks": [
        {"symbol": "TECHV", "name": "TechVeda", "sector": "IT",
         "starting_price": 1200.0, "volatility": 0.025, "beta": 1.2},
        {"symbol": "FRESHB", "name": "FreshBasket", "sector": "FMCG",
         "starting_price": 450.0, "volatility": 0.015, "beta": 0.7},
    ],
    "sectors": ["IT", "FMCG"],
    "events": [],
    "charges": {
        "brokerage_per_trade": 20,
        "stt_buy_pct": 0.001,
        "stt_sell_pct": 0.001,
        "exchange_pct": 0.0000345,
        "gst_pct": 0.18,
    },
    "dimensions_config": {
        "risk_tolerance": {"weight": 1.0},
        "delayed_gratification": {"weight": 1.0},
        "strategic_thinking": {"weight": 1.0},
        "financial_literacy": {"weight": 1.0, "is_tag": True},
    },
}


def test_engine_constructs_with_valid_config():
    eng = StockMarketEngine(VALID_CONFIG)
    result = eng.validate()
    assert result["valid"] is True
    assert result["errors"] == []


def test_engine_rejects_missing_tick_count():
    bad = {**VALID_CONFIG}
    del bad["tick_count"]
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
    assert any("tick_count" in e for e in result["errors"])


def test_engine_rejects_zero_tick_count():
    bad = {**VALID_CONFIG, "tick_count": 0}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False


def test_engine_rejects_stock_missing_symbol():
    bad = {**VALID_CONFIG, "stocks": [{"name": "X", "starting_price": 100, "volatility": 0.02, "sector": "IT"}]}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
    assert any("symbol" in e for e in result["errors"])


def test_engine_rejects_negative_starting_price():
    bad = {**VALID_CONFIG, "stocks": [{"symbol": "X", "name": "X",
           "sector": "IT", "starting_price": -1, "volatility": 0.02, "beta": 1.0}]}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
    assert any("starting_price" in e for e in result["errors"])


def test_engine_rejects_zero_starting_price():
    bad = {**VALID_CONFIG, "stocks": [{"symbol": "X", "name": "X",
           "sector": "IT", "starting_price": 0, "volatility": 0.02, "beta": 1.0}]}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
    assert any("starting_price" in e for e in result["errors"])


def test_engine_rejects_bool_tick_count():
    bad = {**VALID_CONFIG, "tick_count": True}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
    assert any("tick_count" in e for e in result["errors"])


def test_engine_rejects_volatility_out_of_range():
    bad = {**VALID_CONFIG, "stocks": [{"symbol": "X", "name": "X",
           "sector": "IT", "starting_price": 100, "volatility": 1.5, "beta": 1.0}]}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False


def test_price_from_seed_is_deterministic():
    from engines.stocksim.pricing import price_from_seed
    cfg = VALID_CONFIG["stocks"][0]
    p1 = [price_from_seed(42, "TECHV", t, cfg) for _ in range(50) for t in [10]]
    assert all(p == p1[0] for p in p1)


def test_price_from_seed_pinned_values():
    """Golden-value test. Locks the pricing math forever.

    If this test fails, the pricing math changed - that's an explicit decision,
    not a bug. Update the pinned values intentionally.
    """
    from engines.stocksim.pricing import price_from_seed
    cfg = VALID_CONFIG["stocks"][0]  # TECHV starting 1200, vol 0.025
    q0 = price_from_seed(42, "TECHV", 0, cfg)
    assert abs(q0["mid"] - 1200.0) < 0.001  # tick 0 = starting price
    assert q0["bid"] < q0["mid"] < q0["ask"]
    # Pinned values — regenerated only on intentional math change.
    q10 = price_from_seed(42, "TECHV", 10, cfg)
    assert abs(q10["mid"] - 1289.64) < 0.005
    assert abs(q10["bid"] - 1288.99) < 0.005
    assert abs(q10["ask"] - 1290.28) < 0.005
    assert q10["volume"] == 13187


def test_price_floors_at_one_paisa():
    from engines.stocksim.pricing import price_from_seed
    cfg = {"symbol": "X", "name": "X", "sector": "IT",
           "starting_price": 0.05, "volatility": 0.99, "beta": 5.0}
    # Even with extreme volatility seed, never below 0.01
    for tick in range(50):
        q = price_from_seed(99999, "X", tick, cfg)
        assert q["mid"] >= 0.01


def test_price_caps_at_10x_starting():
    from engines.stocksim.pricing import price_from_seed
    cfg = {"symbol": "X", "name": "X", "sector": "IT",
           "starting_price": 100, "volatility": 0.99, "beta": 5.0}
    for tick in range(50):
        q = price_from_seed(11111, "X", tick, cfg)
        assert q["mid"] <= 1000.0


def test_bid_ask_spread_widens_on_high_volatility():
    from engines.stocksim.pricing import price_from_seed
    low_vol = {"symbol": "L", "name": "L", "sector": "IT",
               "starting_price": 100, "volatility": 0.005, "beta": 0.5}
    high_vol = {"symbol": "H", "name": "H", "sector": "IT",
                "starting_price": 100, "volatility": 0.05, "beta": 1.5}
    q_low = price_from_seed(7, "L", 5, low_vol)
    q_high = price_from_seed(7, "H", 5, high_vol)
    assert (q_high["ask"] - q_high["bid"]) > (q_low["ask"] - q_low["bid"])


def test_engine_price_at_uses_seed_from_state():
    eng = StockMarketEngine(VALID_CONFIG)
    state = {"seed": 42, "config": VALID_CONFIG}
    q = eng.price_at(state, "TECHV", 5)
    assert "mid" in q and "bid" in q and "ask" in q
    assert q["bid"] < q["mid"] < q["ask"]


def test_spread_minimum_paisa_for_low_price_stock():
    """Low-price + low-vol must still produce bid < mid < ask after rounding."""
    from engines.stocksim.pricing import price_from_seed
    cfg = {"symbol": "P", "name": "Penny", "sector": "IT",
           "starting_price": 1.0, "volatility": 0.005, "beta": 0.3}
    q = price_from_seed(42, "P", 5, cfg)
    assert q["bid"] < q["mid"] < q["ask"]


def test_charges_breakdown_buy():
    from engines.stocksim.charges import compute_charges
    charges_cfg = VALID_CONFIG["charges"]
    # Buy 10 shares @ ₹1000 = ₹10,000
    c = compute_charges(side="buy", qty=10, price=1000.0, cfg=charges_cfg)
    # brokerage 20 + STT (10000 * 0.001) = 10 + exchange (10000 * 0.0000345) = 0.345
    # = 30.345 + GST (18% on brokerage+exchange = 18% of 20.345 = 3.66)
    assert c["brokerage"] == 20.0
    assert abs(c["stt"] - 10.0) < 0.01
    assert abs(c["exchange"] - 0.345) < 0.01
    assert abs(c["gst"] - 3.66) < 0.05
    assert c["total"] > 30 and c["total"] < 35


def test_charges_breakdown_sell():
    from engines.stocksim.charges import compute_charges
    c = compute_charges(side="sell", qty=10, price=1000.0, cfg=VALID_CONFIG["charges"])
    # STT on sell = 10000 * 0.001 = 10.0
    assert abs(c["stt"] - 10.0) < 0.01
    assert c["brokerage"] == 20.0
    # total ≈ 30.345 + GST(18% of 20.345) = 30.345 + 3.66 ≈ 34.01
    assert 33.5 < c["total"] < 34.5


def test_charges_capped_at_5pct_raises():
    from engines.stocksim.charges import compute_charges, ChargesError
    bad_cfg = {"brokerage_per_trade": 9999, "stt_buy_pct": 0, "stt_sell_pct": 0,
               "exchange_pct": 0, "gst_pct": 0}
    # Trade value is ₹100, brokerage alone ₹9999 → way above 5%
    with pytest.raises(ChargesError):
        compute_charges(side="buy", qty=1, price=100.0, cfg=bad_cfg)


def test_charges_rejects_invalid_side():
    from engines.stocksim.charges import compute_charges
    with pytest.raises(ValueError, match="side must be"):
        compute_charges(side="LIMIT", qty=1, price=100.0, cfg=VALID_CONFIG["charges"])


def test_charges_rejects_zero_qty():
    from engines.stocksim.charges import compute_charges
    with pytest.raises(ValueError, match="qty must be positive"):
        compute_charges(side="buy", qty=0, price=100.0, cfg=VALID_CONFIG["charges"])


def test_charges_rejects_negative_price():
    from engines.stocksim.charges import compute_charges
    with pytest.raises(ValueError, match="price must be positive"):
        compute_charges(side="buy", qty=1, price=-50.0, cfg=VALID_CONFIG["charges"])


def test_charges_total_equals_sum_of_components():
    """Regression: total must equal sum of rounded components."""
    from engines.stocksim.charges import compute_charges
    c = compute_charges(side="buy", qty=10, price=1000.0, cfg=VALID_CONFIG["charges"])
    expected = round(c["brokerage"] + c["stt"] + c["exchange"] + c["gst"], 2)
    assert c["total"] == expected


def test_start_session_initializes_state():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    assert state["seed"] == 42
    assert state["cash"] == 100000
    assert state["holdings"] == {}
    assert state["pending_orders"] == []
    assert state["settlement_queue"] == []
    assert state["trade_log"] == []
    assert state["current_tick"] == 0
    assert state["realized_pnl"] == 0
    assert state["completed"] is False
    assert "dimension_counters" in state


def test_market_buy_fills_at_ask():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    quote = eng.price_at(state, "TECHV", 1)
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 5,
        "order_type": "market"
    })
    assert result["status"] == "filled"
    assert abs(result["fill"]["price"] - quote["ask"]) < 0.01
    assert state["holdings"].get("TECHV", {}).get("qty") == 5
    assert state["cash"] < 100000


def test_market_sell_fills_at_bid():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["holdings"]["TECHV"] = {"qty": 10, "avg_price": 1100.0, "settled_qty": 10}
    quote = eng.price_at(state, "TECHV", 1)
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "sell", "qty": 5,
        "order_type": "market"
    })
    assert result["status"] == "filled"
    assert abs(result["fill"]["price"] - quote["bid"]) < 0.01


def test_limit_buy_below_ask_queues():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    quote = eng.price_at(state, "TECHV", 1)
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 5,
        "order_type": "limit", "limit_price": quote["ask"] - 50.0
    })
    assert result["status"] == "queued"
    assert len(state["pending_orders"]) == 1


def test_limit_buy_above_ask_fills_immediately():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    quote = eng.price_at(state, "TECHV", 1)
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 5,
        "order_type": "limit", "limit_price": quote["ask"] + 50.0
    })
    assert result["status"] == "filled"
    assert state["pending_orders"] == []


def test_insufficient_funds_rejected():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["cash"] = 100
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 100,
        "order_type": "market"
    })
    assert result["status"] == "rejected"
    assert result["error_code"] == "INSUFFICIENT_FUNDS"


def test_insufficient_holdings_rejected():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "sell", "qty": 5,
        "order_type": "market"
    })
    assert result["status"] == "rejected"
    assert result["error_code"] == "INSUFFICIENT_HOLDINGS"


def test_invalid_qty_rejected():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 0,
        "order_type": "market"
    })
    assert result["status"] == "rejected"
    assert result["error_code"] == "INVALID_ORDER"


def test_t1_blocks_same_day_sell():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    eng.place_order(state, {"tick": 1, "symbol": "TECHV",
                            "side": "buy", "qty": 5, "order_type": "market"})
    result = eng.place_order(state, {"tick": 5, "symbol": "TECHV",
                                     "side": "sell", "qty": 5, "order_type": "market"})
    assert result["status"] == "rejected"
    assert result["error_code"] == "SETTLEMENT_PENDING"


def test_t1_allows_next_day_sell_after_advance():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    eng.place_order(state, {"tick": 1, "symbol": "TECHV",
                            "side": "buy", "qty": 5, "order_type": "market"})
    eng.advance_to_tick(state, 22)
    result = eng.place_order(state, {"tick": 22, "symbol": "TECHV",
                                     "side": "sell", "qty": 5, "order_type": "market"})
    assert result["status"] == "filled"


def test_stop_loss_triggers_on_price_cross():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["holdings"]["TECHV"] = {"qty": 10, "avg_price": 1200.0, "settled_qty": 10}
    state["pending_orders"].append({
        "order_id": "sl-1", "type": "stop_loss", "side": "sell",
        "symbol": "TECHV", "qty": 10, "stop_price": 99999.0,
        "placed_tick": 0,
    })
    eng.advance_to_tick(state, 5)
    assert state["holdings"].get("TECHV") is None or state["holdings"]["TECHV"]["qty"] == 0
    assert any(t.get("symbol") == "TECHV" and t.get("side") == "sell"
               for t in state["trade_log"])


def test_circuit_breaker_blocks_orders():
    cfg = {**VALID_CONFIG, "circuit_breaker_pct": [3]}
    eng = StockMarketEngine(cfg)
    state = eng.start_session(seed=42, profile="day_trader")
    triggered_tick = None
    for t in range(1, 23):
        q = eng.price_at(state, "TECHV", t)
        if abs(q["mid"] - 1200.0) / 1200.0 > 0.03:
            triggered_tick = t
            break
    if triggered_tick is None:
        pytest.skip("seed 42 didn't move TECHV >3% in 22 ticks")
    eng.advance_to_tick(state, triggered_tick)
    result = eng.place_order(state, {"tick": triggered_tick, "symbol": "TECHV",
                                     "side": "buy", "qty": 1, "order_type": "market"})
    assert result["status"] == "rejected"
    assert result["error_code"] == "MARKET_HALTED"


def test_sip_executes_on_scheduled_tick():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["pending_orders"].append({
        "order_id": "sip-1", "type": "sip", "side": "buy",
        "symbol": "TECHV", "amount": 1000.0, "schedule_tick": 5,
        "placed_tick": 0,
    })
    eng.advance_to_tick(state, 5)
    assert state["holdings"].get("TECHV", {}).get("qty", 0) > 0
    assert any(t.get("symbol") == "TECHV" and "sip" in str(t.get("order_id", ""))
               or t.get("symbol") == "TECHV" for t in state["trade_log"])


def test_news_at_is_deterministic():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    n1 = eng.news_at(state, 5)
    n2 = eng.news_at(state, 5)
    assert n1 == n2


def test_news_drops_periodically():
    cfg_with_events = {**VALID_CONFIG, "events": [
        {"id": "fii_flow_positive", "tick_pattern": "every_5",
         "symbols": ["TECHV"], "headline": "FII inflow ₹2400cr",
         "category": "fii_flow", "severity": "info"},
    ]}
    eng = StockMarketEngine(cfg_with_events)
    state = eng.start_session(seed=42, profile="day_trader")
    n5 = eng.news_at(state, 5)
    n10 = eng.news_at(state, 10)
    n6 = eng.news_at(state, 6)
    assert len(n5) >= 1
    assert len(n10) >= 1
    assert len(n6) == 0


def test_event_at_returns_none_when_quiet():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    assert eng.event_at(state, 3) is None


def test_news_once_at_T_fires_only_on_T():
    cfg = {**VALID_CONFIG, "events": [
        {"id": "earnings_call", "tick_pattern": "once_at_7",
         "headline": "Q3 results", "category": "earnings", "severity": "major"},
    ]}
    eng = StockMarketEngine(cfg)
    state = eng.start_session(seed=42, profile="day_trader")
    assert len(eng.news_at(state, 6)) == 0
    assert len(eng.news_at(state, 7)) == 1
    assert eng.news_at(state, 7)[0]["id"] == "earnings_call"
    assert len(eng.news_at(state, 8)) == 0


def test_event_at_returns_major_severity_when_present():
    cfg = {**VALID_CONFIG, "events": [
        {"id": "info_blip", "tick_pattern": "every_3",
         "headline": "minor blip", "severity": "info"},
        {"id": "rate_decision", "tick_pattern": "once_at_3",
         "headline": "RBI rate decision", "severity": "major"},
    ]}
    eng = StockMarketEngine(cfg)
    state = eng.start_session(seed=42, profile="day_trader")
    ev = eng.event_at(state, 3)
    assert ev is not None
    assert ev["id"] == "rate_decision"
    assert ev["severity"] == "major"


def test_news_returns_multiple_when_overlapping():
    cfg = {**VALID_CONFIG, "events": [
        {"id": "fii_in", "tick_pattern": "every_5",
         "headline": "FII inflow", "category": "fii_flow"},
        {"id": "dii_in", "tick_pattern": "every_5",
         "headline": "DII inflow", "category": "dii_flow"},
    ]}
    eng = StockMarketEngine(cfg)
    state = eng.start_session(seed=42, profile="day_trader")
    items = eng.news_at(state, 5)
    assert len(items) == 2
    ids = {n["id"] for n in items}
    assert ids == {"fii_in", "dii_in"}
