# backend/tests/test_stocksim_calendar.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from engines.stocksim.calendar import current_day, tick_to_day, day_index_to_id

DAYS = [
    {"id": "mon", "label": "Monday", "ticks": 4},
    {"id": "tue", "label": "Tuesday", "ticks": 4},
    {"id": "wed", "label": "Wednesday", "ticks": 4},
    {"id": "thu", "label": "Thursday", "ticks": 4},
    {"id": "fri", "label": "Friday", "ticks": 4},
]

def test_tick_to_day_first_tick_of_day():
    assert tick_to_day(0, DAYS) == DAYS[0]
    assert tick_to_day(4, DAYS) == DAYS[1]
    assert tick_to_day(7, DAYS) == DAYS[1]

def test_tick_to_day_last_tick_clamps_to_final_day():
    assert tick_to_day(19, DAYS) == DAYS[4]
    assert tick_to_day(99, DAYS) == DAYS[4]

def test_current_day_uses_state_current_tick():
    state = {"current_tick": 9}
    sm_cfg = {"calendar_mode": "week", "days": DAYS}
    d = current_day(state, sm_cfg)
    assert d["id"] == "wed"
    assert d["index"] == 2
    assert d["of"] == 5

def test_current_day_returns_none_when_calendar_mode_absent():
    assert current_day({"current_tick": 0}, {}) is None

def test_day_index_to_id():
    assert day_index_to_id(0, DAYS) == "mon"
    assert day_index_to_id(4, DAYS) == "fri"
    assert day_index_to_id(99, DAYS) == "fri"


def test_tick_to_day_empty_days_returns_none():
    assert tick_to_day(0, []) is None


def test_tick_to_day_negative_tick_returns_first_day():
    # Documented behavior: negative ticks fall through to first day.
    assert tick_to_day(-1, DAYS) == DAYS[0]


def test_current_day_missing_current_tick_defaults_to_zero():
    state = {}
    sm_cfg = {"calendar_mode": "week", "days": DAYS}
    d = current_day(state, sm_cfg)
    assert d["id"] == "mon"
    assert d["index"] == 0


def test_current_day_returns_none_when_days_empty():
    sm_cfg = {"calendar_mode": "week", "days": []}
    assert current_day({"current_tick": 0}, sm_cfg) is None


def test_day_index_to_id_negative_clamps_to_first():
    assert day_index_to_id(-5, DAYS) == "mon"


def test_day_index_to_id_empty_days_returns_none():
    assert day_index_to_id(0, []) is None


import math
from engines.stocksim.calendar import apply_overnight_drift

SM_CFG_WEEK = {
    "calendar_mode": "week",
    "days": DAYS,
    "earnings_schedule": {
        "TECHN":      {"day": "tue", "surprise": 0.05},
        "BHARATBANK": {"day": "wed", "surprise": -0.03},
    },
}

def test_apply_overnight_drift_zero_when_seed_makes_noise_zero(monkeypatch):
    state = {"current_tick": 4, "drift": {}}
    # Force base_noise = 0 by stubbing the gaussian
    import engines.stocksim.calendar as calmod
    monkeypatch.setattr(calmod, "_normal", lambda mu, sigma, seed: 0.0)
    apply_overnight_drift(state, SM_CFG_WEEK, "mon", "tue")
    # No earnings on Monday → drift for both should be 0 (no noise + no earnings)
    assert state["drift"].get("TECHN", 0.0) == 0.0
    assert state["drift"].get("BHARATBANK", 0.0) == 0.0

def test_apply_overnight_drift_applies_earnings_when_day_matches(monkeypatch):
    state = {"current_tick": 8, "drift": {}}
    import engines.stocksim.calendar as calmod
    monkeypatch.setattr(calmod, "_normal", lambda mu, sigma, seed: 0.0)
    # Tue earnings for TECHN: surprise +0.05, factor 0.6 → drift = 0.03
    apply_overnight_drift(state, SM_CFG_WEEK, "tue", "wed")
    assert math.isclose(state["drift"]["TECHN"], 0.03, abs_tol=1e-9)
    assert state["drift"].get("BHARATBANK", 0.0) == 0.0

def test_apply_overnight_drift_noop_when_calendar_mode_absent():
    state = {"current_tick": 0, "drift": {}}
    apply_overnight_drift(state, {}, "mon", "tue")
    assert state["drift"] == {}
