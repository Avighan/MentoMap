"""
Market Actors Engine — executive-tier subsystem modeling named market
participants (competitors, allies, press, regulators, ...) and their
behavior over time, distinct from the numeric share-table in market_engine
and from the dedicated competitor_ai_engine's roster.

Activated only when game JSON declares `simulation_config.market_actors`.
No committed games/*.json declares this key yet (matches
executive_ux.py's own docstring: "each game can opt into any subset ...
96 SEL games are unaffected") — the schema below is inferred from the
key's name and modeled directly on this repo's existing, structurally
identical `simulation_config.market.competitors` / `competitor_ai.firms`
shape (id, name, kind, policy, state, scripted_moves), which is this
codebase's established convention for authoring a named external actor:

    simulation_config.market_actors = [
      {"id": "fast_follower", "name": "Fast-Follower Startup",
       "kind": "competitor",              # competitor | ally | journalist | regulator | ...
       "policy": "fast_follow",           # authoring-time behavior label
       "state": {"share_pct": 8, "mood": "aggressive", "trust": 50},
       "scripted_moves": [
         {"round": 2, "label": "VC asks for monthly KPI letter",
          "intensity": "low", "narrative": "..."}
       ]}
    ]

Runtime overrides (optional):
    state._market_actor_state: {actor_id: {field: value, ...}} merged over
        the authored `state` block (e.g. a choice nudges an actor's mood)

Round progression for scripted_moves uses state.round_index (0-based;
compared against each move's authored `round`, which is engine-agnostic
and simply an ordinal the game author chose).

All helpers are pure functions of (state, game) — they read state, never
mutate it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


# ────────────────────────────────────────────────────────────────────
# Schema activation
# ────────────────────────────────────────────────────────────────────

def get_actors_config(game: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Return the market_actors list, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("market_actors")
    if not isinstance(cfg, list) or not cfg:
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Sub-computations
# ────────────────────────────────────────────────────────────────────

def compute_actor_state(actor: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    base = dict(actor.get("state") or {})
    base.update(overrides.get(actor.get("id"), {}) or {})
    return base


def compute_scripted_moves(actor: Dict[str, Any], current_round_index: int) -> Dict[str, Any]:
    moves = actor.get("scripted_moves") or []
    triggered = [m for m in moves if int(m.get("round", 0) or 0) <= current_round_index]
    upcoming = [m for m in moves if int(m.get("round", 0) or 0) > current_round_index]
    upcoming.sort(key=lambda m: m.get("round", 0))
    return {
        "triggered": triggered,
        "next": upcoming[0] if upcoming else None,
        "remaining_count": len(upcoming),
    }


def build_actor_entry(state: Any, actor: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    current_round_index = int(_get(state, "round_index", 0) or 0)
    actor_state = compute_actor_state(actor, overrides)
    moves = compute_scripted_moves(actor, current_round_index)
    return {
        "id": actor.get("id"),
        "name": actor.get("name", "Market Actor"),
        "kind": actor.get("kind", "competitor"),
        "policy": actor.get("policy"),
        "state": actor_state,
        "triggered_moves": moves["triggered"],
        "next_move": moves["next"],
        "remaining_moves": moves["remaining_count"],
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_actors_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    market_actors isn't configured for this game."""
    actors_cfg = get_actors_config(game)
    if not actors_cfg:
        return None
    overrides = _get(state, "_market_actor_state", {}) or {}
    out = []
    for actor in actors_cfg:
        try:
            out.append(build_actor_entry(state, actor, overrides))
        except Exception:
            continue
    by_kind: Dict[str, int] = {}
    for a in out:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    return {
        "actors": out,
        "n": len(out),
        "by_kind": by_kind,
    }
