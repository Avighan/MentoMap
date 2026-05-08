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
    assert c["stt"] > 0  # STT applies on sell
    assert c["total"] > 0


def test_charges_capped_at_5pct_raises():
    from engines.stocksim.charges import compute_charges, ChargesError
    bad_cfg = {"brokerage_per_trade": 9999, "stt_buy_pct": 0, "stt_sell_pct": 0,
               "exchange_pct": 0, "gst_pct": 0}
    # Trade value is ₹100, brokerage alone ₹9999 → way above 5%
    with pytest.raises(ChargesError):
        compute_charges(side="buy", qty=1, price=100.0, cfg=bad_cfg)
