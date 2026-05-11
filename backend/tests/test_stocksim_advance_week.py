# backend/tests/test_stocksim_advance_week.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from engines.stocksim.orders import advance_to_tick

DAYS = [
    {"id": "mon", "label": "Monday", "ticks": 4},
    {"id": "tue", "label": "Tuesday", "ticks": 4},
    {"id": "wed", "label": "Wednesday", "ticks": 4},
    {"id": "thu", "label": "Thursday", "ticks": 4},
    {"id": "fri", "label": "Friday", "ticks": 4},
]

CFG = {
    "tick_count": 20,
    "tick_interval_seconds": 8,
    "starting_capital": 50000,
    "circuit_breaker_pct": [10],
    "charges": {"brokerage_pct": 0.0003, "stt_pct": 0.001, "exchange_pct": 3.45e-05, "gst_pct": 0.18},
    "stocks": [
        {"symbol": "TECHN", "name": "TechNova", "sector": "IT", "starting_price": 1000, "volatility": 0.02},
    ],
    "events": [],
    "calendar_mode": "week",
    "days": DAYS,
    "earnings_schedule": {"TECHN": {"day": "mon", "surprise": 0.10}},
}

def _empty_state():
    return {
        "seed": 42, "profile": "balanced", "cash": 50000, "holdings": {},
        "pending_orders": [], "settlement_queue": [], "trade_log": [],
        "current_tick": 0, "realized_pnl": 0.0, "completed": False,
        "dimension_counters": {}, "halted_symbols": {},
    }

def test_advance_within_same_day_does_not_apply_drift():
    state = _empty_state()
    advance_to_tick(state, 3, CFG)
    assert state.get("drift", {}) == {}  # still in mon

def test_advance_across_one_boundary_applies_drift_once(monkeypatch):
    # Stub _normal so the assertion isolates the earnings formula and is
    # not sensitive to PYTHONHASHSEED (hash(sym) is per-process random).
    import engines.stocksim.calendar as calmod
    monkeypatch.setattr(calmod, "_normal", lambda mu, sigma, seed: 0.0)
    state = _empty_state()
    advance_to_tick(state, 4, CFG)  # mon → tue
    assert "drift" in state
    # earnings on mon for TECHN: 0.10 * 0.6 = 0.06 (noise stubbed to 0).
    assert state["drift"]["TECHN"] == pytest.approx(0.06)

def test_advance_across_multiple_boundaries_compounds(monkeypatch):
    # Stub _normal to 0 so we can pin the expected drift exactly to the
    # earnings contribution from the single mon→tue crossing.
    import engines.stocksim.calendar as calmod
    monkeypatch.setattr(calmod, "_normal", lambda mu, sigma, seed: 0.0)
    state = _empty_state()
    advance_to_tick(state, 12, CFG)  # mon → tue → wed → thu (3 boundaries)
    # 3 overnights (noise each, stubbed to 0); earnings bonus fires only
    # on the mon→tue crossing → final drift equals 0.06 exactly.
    assert state["drift"]["TECHN"] == pytest.approx(0.06)
