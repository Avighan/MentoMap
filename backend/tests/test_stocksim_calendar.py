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
