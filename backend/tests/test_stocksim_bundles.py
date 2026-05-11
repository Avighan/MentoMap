"""Validate Phase B Tier-2 stock-market game bundles load and conform to v2 schema."""
import json
import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from schemas import _validate_stock_market_minigame as _validate

GAMES_DIR = Path(__file__).resolve().parent.parent / "games"


@pytest.mark.parametrize("slug", ["stock-market-day-trader", "stock-market-simulator"])
def test_stocksim_bundle_loads(slug):
    path = GAMES_DIR / f"{slug}.json"
    bundle = json.loads(path.read_text())
    # Run the v2 minigame validator
    _validate(bundle)  # must not raise
    cfg = bundle["minigame_config"]["stock_market_config"]
    assert cfg["realism_tier"] == 2
    assert cfg["tick_authority"] == "hybrid"
    assert "dimensions_config" in cfg
    assert isinstance(cfg["stocks"], list) and len(cfg["stocks"]) >= 1


def test_day_trader_is_short_session():
    path = GAMES_DIR / "stock-market-day-trader.json"
    cfg = json.loads(path.read_text())["minigame_config"]["stock_market_config"]
    assert cfg["tick_count"] == 22


def test_both_games_in_discover_whitelist():
    from app import _DISCOVER_WHITELIST
    assert "stock-market-day-trader" in _DISCOVER_WHITELIST
    assert "stock-market-simulator" in _DISCOVER_WHITELIST
