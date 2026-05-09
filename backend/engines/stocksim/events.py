"""Deterministic news + market event scheduler with recent-reason side effect.

Events defined in config['events'][] match a tick via either:
  - tick_pattern: "every_N"   → fires on ticks N, 2N, 3N…
  - tick_pattern: "once_at_T" → fires only on tick T
  - "tick": N (canonical v2)  → fires only on tick N

Each event has: id, headline, category, severity, optional symbols[].

Side effect: when an event matches AND has a non-empty `reason` or
`headline`, news_at writes state['recent_reasons'][sym] = {tick, reason}
for each affected symbol. The `/state` route reads this within a
2-tick window to power the "Why is it moving?" chip on each quote.
event_at() delegates to news_at() and inherits this side effect.
"""
from __future__ import annotations


def news_at(state: dict, tick: int, config: dict) -> list[dict]:
    """Return list of news items active at this tick (deterministic)."""
    events = config.get("events", [])
    out = []
    for ev in events:
        matched = False
        pat = ev.get("tick_pattern", "")
        if pat.startswith("every_"):
            try:
                n = int(pat.split("_")[1])
                if n > 0 and tick > 0 and tick % n == 0:
                    matched = True
            except (ValueError, IndexError):
                pass
        elif pat.startswith("once_at_"):
            try:
                t = int(pat.split("_")[2])
                if tick == t:
                    matched = True
            except (ValueError, IndexError):
                pass
        else:
            # v2 canonical: bare {"tick": N}
            ev_tick = ev.get("tick")
            if isinstance(ev_tick, int) and not isinstance(ev_tick, bool) and ev_tick == tick:
                matched = True

        if not matched:
            continue

        out.append({
            "id": ev["id"],
            "headline": ev.get("headline", ""),
            "category": ev.get("category", "info"),
            "severity": ev.get("severity", "info"),
            "symbols": ev.get("symbols", []),
        })

        # v2: stamp recent_reasons for the why-moving chip (any severity, any matcher).
        reason = ev.get("reason") or ev.get("headline") or ""
        if reason:
            recent = state.setdefault("recent_reasons", {})
            for sym in (ev.get("symbols") or ev.get("affected_symbols") or []):
                recent[sym] = {"tick": tick, "reason": reason}
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
