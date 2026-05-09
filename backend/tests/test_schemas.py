"""Schema validation tests."""
import pytest
from schemas import validate_bundle


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
