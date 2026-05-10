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

def test_advance_across_one_boundary_applies_drift_once():
    state = _empty_state()
    advance_to_tick(state, 4, CFG)  # mon → tue
    assert "drift" in state
    # earnings on mon for TECHN: 0.10 * 0.6 = 0.06 plus seeded noise
    assert state["drift"].get("TECHN", 0.0) > 0.05

def test_advance_across_multiple_boundaries_compounds():
    state = _empty_state()
    advance_to_tick(state, 12, CFG)  # mon → tue → wed → thu (3 boundaries)
    # drift should reflect noise from 3 overnight applications + 1 earnings
    assert "drift" in state
    assert "TECHN" in state["drift"]
