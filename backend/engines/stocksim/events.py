"""Deterministic news + market event scheduler.

Events defined in config['events'][] with `tick_pattern`:
  - "every_N"   → fires on ticks N, 2N, 3N…
  - "once_at_T" → fires only on tick T
  - "random_p" + seed → probability per tick (not used in v1, hook for later)

Each event has: id, headline, category, severity, optional symbols[].
"""
from __future__ import annotations


def news_at(state: dict, tick: int, config: dict) -> list[dict]:
    """Return list of news items active at this tick (deterministic)."""
    events = config.get("events", [])
    out = []
    for ev in events:
        pat = ev.get("tick_pattern", "")
        if pat.startswith("every_"):
            try:
                n = int(pat.split("_")[1])
                if n > 0 and tick > 0 and tick % n == 0:
                    out.append({
                        "id": ev["id"],
                        "headline": ev.get("headline", ""),
                        "category": ev.get("category", "info"),
                        "severity": ev.get("severity", "info"),
                        "symbols": ev.get("symbols", []),
                    })
            except (ValueError, IndexError):
                pass
        elif pat.startswith("once_at_"):
            try:
                t = int(pat.split("_")[2])
                if tick == t:
                    out.append({
                        "id": ev["id"],
                        "headline": ev.get("headline", ""),
                        "category": ev.get("category", "info"),
                        "severity": ev.get("severity", "info"),
                        "symbols": ev.get("symbols", []),
                    })
            except (ValueError, IndexError):
                pass
    return out


def event_at(state: dict, tick: int, config: dict) -> dict | None:
    """Return single high-impact event for this tick, if any.

    Distinguished from news by `severity == 'major'`. Used by EventOverlay.
    Circuit breakers come from state['halted_symbols'], not from this.
    """
    items = news_at(state, tick, config)
    for n in items:
        if n.get("severity") == "major":
            return n
    return None
