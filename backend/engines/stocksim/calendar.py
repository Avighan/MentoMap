# backend/engines/stocksim/calendar.py
"""Calendar-week helpers for the week-format stock market simulator.

These helpers are pure: they take a state dict + sm_cfg dict and return
metadata. They never mutate state (drift application lives separately).
"""
from typing import Optional


def tick_to_day(tick: int, days: list) -> Optional[dict]:
    """Return the day dict that owns the given tick index. Clamps to the last day.

    Args:
        tick: Tick index. Assumed non-negative; negative values fall through
            the cumulative walk and return ``days[0]`` (first day).
        days: List of day dicts each with at least ``{"ticks": int}``.

    Returns:
        The day dict whose tick range covers ``tick``, or ``None`` if ``days``
        is empty. Ticks past the final day clamp to the last day.
    """
    if not days:
        return None
    cumulative = 0
    for d in days:
        cumulative += int(d.get("ticks", 0))
        if tick < cumulative:
            return d
    return days[-1]


def day_index_to_id(idx: int, days: list) -> Optional[str]:
    """Return the day id at ``idx``. Clamps to first/last on out-of-range.

    Returns ``None`` if ``days`` is empty.
    """
    if not days:
        return None
    if idx < 0:
        return days[0].get("id")
    if idx >= len(days):
        return days[-1].get("id")
    return days[idx].get("id")


def current_day(state: dict, sm_cfg: dict) -> Optional[dict]:
    """Return enriched current-day metadata, or None if calendar_mode != 'week'.

    Args:
        state: Run state dict. Must be a dict; ``state["current_tick"]`` is
            read with default 0. Passing ``None`` will raise ``AttributeError``.
        sm_cfg: ``stock_market_config`` dict. Tolerates ``None`` via the
            ``(sm_cfg or {})`` guard, but expects ``calendar_mode == "week"``
            and a non-empty ``days`` list to return metadata.

    Returns:
        Dict with ``id``, ``label``, ``index``, ``of`` keys, or ``None`` when
        calendar mode is absent or days are empty.
    """
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
