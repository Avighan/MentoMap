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


import math
import random


_EARNINGS_DRIFT_FACTOR = 0.6  # spec §"Overnight Drift Formula"
_BASE_NOISE_SIGMA = 0.005


def _normal(mu: float, sigma: float, seed: int) -> float:
    """Box-Muller normal sample seeded for determinism."""
    rng = random.Random(seed)
    u1 = max(rng.random(), 1e-12)
    u2 = rng.random()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z


def apply_overnight_drift(state: dict, sm_cfg: dict, from_day_id: str, to_day_id: str) -> None:
    """Mutates state['drift'] (per-symbol multiplicative drift) for the overnight gap.

    Drift formula:
      drift[sym] = N(mu=0, sigma=0.005) + (surprise * 0.6 if day-N hosted that earnings else 0)

    Drift is additive on top of any prior drift so multiple overnights compound.
    """
    if (sm_cfg or {}).get("calendar_mode") != "week":
        return
    state.setdefault("drift", {})
    earnings = (sm_cfg.get("earnings_schedule") or {})
    base_seed = int(state.get("seed", 0))
    days = sm_cfg.get("days") or []
    day_idx = next((i for i, d in enumerate(days) if d.get("id") == from_day_id), 0)
    for sym, cfg in earnings.items():
        # Per-symbol seed so different stocks don't move identically.
        sym_seed = (hash(sym) ^ (base_seed * 1009) ^ (day_idx * 31)) & 0xFFFFFFFF
        noise = _normal(0.0, _BASE_NOISE_SIGMA, sym_seed)
        earnings_drift = 0.0
        if cfg.get("day") == from_day_id:
            earnings_drift = float(cfg.get("surprise", 0.0)) * _EARNINGS_DRIFT_FACTOR
        prior = state["drift"].get(sym, 0.0)
        state["drift"][sym] = prior + noise + earnings_drift
    # Symbols not in earnings_schedule still get noise drift.
    for stock in (sm_cfg.get("stocks") or []):
        sym = stock.get("symbol")
        if not sym or sym in earnings:
            continue
        sym_seed = (hash(sym) ^ (base_seed * 1009) ^ (day_idx * 31)) & 0xFFFFFFFF
        noise = _normal(0.0, _BASE_NOISE_SIGMA, sym_seed)
        state["drift"][sym] = state["drift"].get(sym, 0.0) + noise
