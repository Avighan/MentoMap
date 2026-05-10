# backend/engines/stocksim/calendar.py
"""Calendar-week helpers for the week-format stock market simulator.

These helpers are pure: they take a state dict + sm_cfg dict and return
metadata. They never mutate state (drift application lives separately).
"""
from typing import Optional


def tick_to_day(tick: int, days: list) -> Optional[dict]:
    """Return the day dict that owns the given tick index. Clamps to the last day."""
    if not days:
        return None
    cumulative = 0
    for d in days:
        cumulative += int(d.get("ticks", 0))
        if tick < cumulative:
            return d
    return days[-1]


def day_index_to_id(idx: int, days: list) -> Optional[str]:
    if not days:
        return None
    if idx < 0:
        return days[0].get("id")
    if idx >= len(days):
        return days[-1].get("id")
    return days[idx].get("id")


def current_day(state: dict, sm_cfg: dict) -> Optional[dict]:
    """Return enriched current-day metadata, or None if calendar_mode != 'week'."""
    if (sm_cfg or {}).get("calendar_mode") != "week":
        return None
    days = sm_cfg.get("days") or []
    if not days:
        return None
    tick = int(state.get("current_tick", 0))
    d = tick_to_day(tick, days)
    if not d:
        return None
    idx = days.index(d) if d in days else 0
    return {
        "id": d.get("id"),
        "label": d.get("label"),
        "index": idx,
        "of": len(days),
    }
