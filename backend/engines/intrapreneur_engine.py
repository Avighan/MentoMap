"""
Intrapreneur Engine — executive-tier internal-innovation subsystem for
simulation games modeling a new business unit / venture launched inside a
larger org (budget, political capital, sponsor alignment, stage gates).

Activated only when game JSON declares `simulation_config.intrapreneur`.
When absent, `build_intrapreneur_payload` returns None and existing games
are unaffected.

Schema (derived from games/new-bu-launch.json, a real committed example):

    simulation_config.intrapreneur = {
      "starting_budget": 8000000,
      "starting_political_capital": 50,
      "starting_team_size": 22,
      "stage_gates": [
        {"id": "g1_charter", "label": "G1 — Charter", "by_quarter": 1},
        {"id": "g2_first_arr", "label": "G2 — First ARR ($500K)", "by_quarter": 2},
        ...
      ],
      "sponsors": [
        {"id": "ceo", "name": "Atlas CEO", "level": "C-suite", "alignment": 60},
        ...
      ]
    }

Runtime state resources (checked with fallback to the config's starting_*):
    state.budget / state.money           — remaining budget
    state.political_capital              — current political capital
    state.team_size                      — current headcount
    state.quarter (or state.round_index) — used to evaluate stage-gate timing
    state._intrapreneur_gates_complete   — set/list of completed gate ids
    state._sponsor_alignment             — {sponsor_id: new_alignment_0_100}

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

def get_intrapreneur_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the intrapreneur block, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("intrapreneur")
    if not isinstance(cfg, dict):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Sub-computations
# ────────────────────────────────────────────────────────────────────

def compute_resources(state: Any, cfg: Dict[str, Any]) -> Dict[str, Any]:
    budget = _get(state, "budget", None)
    if budget is None:
        budget = _get(state, "money", cfg.get("starting_budget", 0))
    political_capital = _get(state, "political_capital", cfg.get("starting_political_capital", 0))
    team_size = _get(state, "team_size", cfg.get("starting_team_size", 0))
    return {
        "budget": budget,
        "political_capital": political_capital,
        "team_size": team_size,
        "starting_budget": cfg.get("starting_budget", 0),
        "starting_political_capital": cfg.get("starting_political_capital", 0),
        "starting_team_size": cfg.get("starting_team_size", 0),
    }


def compute_current_quarter(state: Any) -> int:
    q = _get(state, "quarter", None)
    if isinstance(q, (int, float)):
        return int(q)
    return int(_get(state, "round_index", 0) or 0) + 1


def compute_stage_gates(state: Any, cfg: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    gates = cfg.get("stage_gates")
    if not isinstance(gates, list) or not gates:
        return None
    completed = set(_get(state, "_intrapreneur_gates_complete", set()) or [])
    current_quarter = compute_current_quarter(state)
    out = []
    for g in gates:
        gid = g.get("id")
        by_q = int(g.get("by_quarter", 0) or 0)
        if gid in completed:
            status = "met"
        elif current_quarter > by_q:
            status = "overdue"
        elif current_quarter == by_q:
            status = "due"
        else:
            status = "upcoming"
        out.append({
            "id": gid,
            "label": g.get("label", "Gate"),
            "by_quarter": by_q,
            "status": status,
        })
    return out


def compute_sponsors(state: Any, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sponsors = cfg.get("sponsors")
    if not isinstance(sponsors, list) or not sponsors:
        return None
    overrides = _get(state, "_sponsor_alignment", {}) or {}
    out = []
    for s in sponsors:
        sid = s.get("id")
        alignment = float(overrides.get(sid, s.get("alignment", 50)) or 0)
        out.append({
            "id": sid,
            "name": s.get("name", "Sponsor"),
            "level": s.get("level"),
            "alignment": alignment,
        })
    avg = sum(s["alignment"] for s in out) / len(out) if out else 0.0
    return {
        "sponsors": out,
        "avg_alignment": round(avg, 1),
        "at_risk_sponsors": [s["name"] for s in out if s["alignment"] < 40],
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_intrapreneur_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    intrapreneur isn't configured for this game."""
    cfg = get_intrapreneur_config(game)
    if not cfg:
        return None
    payload: Dict[str, Any] = {
        "resources": None,
        "current_quarter": None,
        "stage_gates": None,
        "sponsors": None,
    }
    try:
        payload["resources"] = compute_resources(state, cfg)
    except Exception:
        pass
    try:
        payload["current_quarter"] = compute_current_quarter(state)
    except Exception:
        pass
    try:
        payload["stage_gates"] = compute_stage_gates(state, cfg)
    except Exception:
        pass
    try:
        payload["sponsors"] = compute_sponsors(state, cfg)
    except Exception:
        pass
    return payload
