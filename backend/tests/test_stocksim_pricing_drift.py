# backend/tests/test_stocksim_pricing_drift.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
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
    # Within 0.5% of exact +5% after 2-dp rounding on a ~1000 INR mid.
    assert abs(p1["mid"] - p0["mid"] * 1.05) / p0["mid"] < 0.005
    # All quote fields scale, not just mid (guards against copy-paste bugs).
    assert p1["bid"] > p0["bid"]
    assert p1["ask"] > p0["ask"]


def test_price_at_unknown_symbol_raises():
    state = {"seed": 1}
    with pytest.raises(ValueError, match="unknown symbol"):
        price_at(state, "NOPE", 0, CFG)


def test_price_at_with_negative_drift_decreases_all_fields():
    state_base = {"seed": 42, "drift": {}}
    state_neg  = {"seed": 42, "drift": {"TECHN": -0.10}}
    p0 = price_at(state_base, "TECHN", 5, CFG)
    p1 = price_at(state_neg,  "TECHN", 5, CFG)
    assert p1["mid"] < p0["mid"]
    assert p1["bid"] < p0["bid"]
    assert p1["ask"] < p0["ask"]


def test_price_at_extreme_negative_drift_returns_near_zero_without_clamping():
    # Pins the documented contract: price_at does NOT clamp post-multiplication.
    # Callers are responsible for keeping drift_pct within sane bounds.
    state = {"seed": 42, "drift": {"TECHN": -0.99}}
    q = price_at(state, "TECHN", 5, CFG)
    assert q["mid"] < 20.0  # ~1% of an unscaled ~1000 INR mid
    assert q["mid"] >= 0.0  # function does not raise; caller must validate range
