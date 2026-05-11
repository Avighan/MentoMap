"""Schema validation tests."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from schemas import _validate_stock_market_minigame, validate_bundle


def _stock_market_game(overrides: dict = None) -> dict:
    base = {
        "game_id": "test-stocksim-v1",
        "title": "Test",
        "initial_state": {},
        "game_type": "minigame",
        "minigame_config": {
            "subtype": "stock_market",
            "stock_market_config": {
                "tick_count": 22,
                "tick_interval_seconds": 8,
                "starting_capital": 100000,
                "realism_tier": 2,
                "stocks": [
                    {"symbol": "T", "name": "T", "sector": "IT",
                     "starting_price": 100, "volatility": 0.02},
                ],
                "sectors": ["IT"],
                "events": [],
                "charges": {
                    "brokerage_per_trade": 20, "stt_buy_pct": 0.001,
                    "stt_sell_pct": 0.001, "exchange_pct": 0.0000345,
                    "gst_pct": 0.18,
                },
                "dimensions_config": {
                    "risk_tolerance": {"weight": 1.0},
                },
            },
        },
    }
    if overrides:
        base["minigame_config"]["stock_market_config"].update(overrides)
    return base


def test_stock_market_v2_valid_bundle_passes():
    bundle = {"games": [_stock_market_game()]}
    validate_bundle(bundle)  # should not raise


def test_stock_market_v2_missing_tick_count_raises():
    g = _stock_market_game()
    del g["minigame_config"]["stock_market_config"]["tick_count"]
    with pytest.raises(ValueError, match="tick_count"):
        validate_bundle({"games": [g]})


def test_stock_market_v2_missing_stocks_raises():
    g = _stock_market_game()
    g["minigame_config"]["stock_market_config"]["stocks"] = []
    with pytest.raises(ValueError, match="stocks"):
        validate_bundle({"games": [g]})


def test_stock_market_v2_invalid_dimension_key_raises():
    g = _stock_market_game()
    g["minigame_config"]["stock_market_config"]["dimensions_config"] = {
        "made_up_dim": {"weight": 1.0}
    }
    with pytest.raises(ValueError, match="dimension"):
        validate_bundle({"games": [g]})


def test_stock_market_v2_boolean_tick_count_rejected():
    g = _stock_market_game()
    g["minigame_config"]["stock_market_config"]["tick_count"] = True
    with pytest.raises(ValueError, match="tick_count"):
        validate_bundle({"games": [g]})


def test_stock_market_v2_invalid_stock_field_types_rejected():
    # starting_price as string
    g = _stock_market_game()
    g["minigame_config"]["stock_market_config"]["stocks"][0]["starting_price"] = "100"
    with pytest.raises(ValueError, match="starting_price"):
        validate_bundle({"games": [g]})
    # volatility out of range
    g = _stock_market_game()
    g["minigame_config"]["stock_market_config"]["stocks"][0]["volatility"] = 5.0
    with pytest.raises(ValueError, match="volatility"):
        validate_bundle({"games": [g]})


def test_stock_market_legacy_format_passes():
    """Legacy stock_market games (direct keys, no stock_market_config) must still validate."""
    g = {
        "game_id": "legacy-stocksim-v1",
        "title": "Legacy",
        "initial_state": {},
        "game_type": "minigame",
        "minigame_config": {
            "subtype": "stock_market",
            "stocks": [{"symbol": "T", "starting_price": 100}],
            "num_ticks": 10,
        },
    }
    validate_bundle({"games": [g]})  # should not raise


def test_stock_market_v2_bad_event_symbol_rejected():
    g = _stock_market_game()
    g["minigame_config"]["stock_market_config"]["events"] = [
        {"id": "ev1", "symbols": ["BOGUS"]}
    ]
    with pytest.raises(ValueError, match="unknown symbol"):
        validate_bundle({"games": [g]})


def _wrap(cfg):
    """Wrap a stock_market_config in a full game bundle the validator expects."""
    return {
        "game_id": "test-stock-market",
        "minigame_config": {"subtype": "stock_market", "stock_market_config": cfg},
    }


def test_stock_market_v2_optional_fields_accepted():
    cfg = {
        "tick_interval_ms": 8000,
        "tick_count": 22,
        "starting_cash": 100000,
        "briefing": {
            "macro_tone": "RBI policy day. IT and banks in focus.",
            "sector_mood": {"IT": "positive", "Banking": "neutral"},
            "headline": "8 stocks. 22 ticks. Trade smart.",
            "sub": "Each tick = ~8 seconds.",
        },
        "stocks": [
            {
                "symbol": "TECHV", "name": "TechVista", "sector": "IT",
                "starting_price": 215, "volatility": 0.04,
                "fundamentals": {
                    "pe": 28.4, "sector_pe": 24.0, "roe": 22.1,
                    "debt_equity": 0.12, "market_cap_cr": 420000,
                    "quarterly_revenue_cr": [9400, 9820, 10250, 11140],
                },
                "peers": [{"symbol": "INFOS", "name": "InfoSwift", "pe": 24.0, "growth_yoy": 14, "roe": 25.0, "market_cap_cr": 720000}],
                "about": {"description": "Mid-cap IT services.", "key_people": [{"role": "CEO", "name": "R. Iyer"}], "founded": 1998, "hq": "Bengaluru"},
                "image_prompt": "modern server racks glowing blue",
            }
        ],
        "events": [{"id": "e1", "tick": 4, "headline": "h", "symbols": ["TECHV"], "reason": "Large contract", "impact": {"TECHV": 0.025}}],
    }
    _validate_stock_market_minigame(_wrap(cfg))  # must not raise


def test_stock_market_v2_rejects_quarterly_wrong_length():
    cfg = {
        "tick_interval_ms": 8000, "tick_count": 22, "starting_cash": 100000,
        "stocks": [{
            "symbol": "X", "name": "X", "sector": "X",
            "starting_price": 100, "volatility": 0.02,
            "fundamentals": {"quarterly_revenue_cr": [1, 2, 3]},
        }],
        "events": [],
    }
    with pytest.raises(ValueError, match="quarterly_revenue_cr"):
        _validate_stock_market_minigame(_wrap(cfg))


def test_stock_market_v2_legacy_config_still_valid():
    """A v1 config with no fundamentals/peers/about/briefing must still validate."""
    cfg = {
        "tick_interval_ms": 8000, "tick_count": 22, "starting_cash": 100000,
        "stocks": [{"symbol": "X", "name": "X", "sector": "X", "starting_price": 100, "volatility": 0.02}],
        "events": [{"id": "e1", "tick": 4, "headline": "h", "symbols": ["X"], "impact": {"X": 0.02}}],
    }
    _validate_stock_market_minigame(_wrap(cfg))  # must not raise


def test_stock_market_v2_rejects_bool_as_numeric_in_fundamentals():
    """Python's `isinstance(True, int)` is True; the validator must catch bool-as-numeric."""
    cfg = {
        "tick_interval_ms": 8000, "tick_count": 22, "starting_cash": 100000,
        "stocks": [{
            "symbol": "X", "name": "X", "sector": "X",
            "starting_price": 100, "volatility": 0.02,
            "fundamentals": {"pe": True},
        }],
        "events": [],
    }
    with pytest.raises(ValueError, match="fundamentals.pe"):
        _validate_stock_market_minigame(_wrap(cfg))
