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
