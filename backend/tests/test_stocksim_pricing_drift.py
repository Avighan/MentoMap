# backend/tests/test_stocksim_pricing_drift.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.stocksim.pricing import price_at

CFG = {
    "stocks": [{"symbol": "TECHN", "name": "TechNova", "starting_price": 1000, "volatility": 0.02}],
    "calendar_mode": "week",
}

def test_price_at_with_no_drift_state_unchanged():
    state = {"seed": 42, "drift": {}}
    p_no_drift = price_at(state, "TECHN", 5, CFG)
    state2 = {"seed": 42}  # no drift key at all
    p_no_key = price_at(state2, "TECHN", 5, CFG)
    assert abs(p_no_drift["mid"] - p_no_key["mid"]) < 1e-9

def test_price_at_with_positive_drift_increases_mid():
    state = {"seed": 42, "drift": {}}
    p0 = price_at(state, "TECHN", 5, CFG)
    state["drift"] = {"TECHN": 0.05}
    p1 = price_at(state, "TECHN", 5, CFG)
    assert p1["mid"] > p0["mid"]
    assert abs(p1["mid"] - p0["mid"] * 1.05) / p0["mid"] < 0.005  # roughly +5%
