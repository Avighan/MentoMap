"""
Org Engine — executive-tier org chart / headcount / culture subsystem for
simulation games.

Activated only when game JSON declares `simulation_config.org`. When absent,
`build_org_payload` returns None and existing games are unaffected.

Schema (derived from games/series-a-founders-journey.json, a real committed
example):

    simulation_config.org = {
      "leaders": [
        {"name": "You", "role": "CEO", "reports": ["VP Eng", "Head of Sales"]},
        {"name": "Maya", "role": "VP Eng", "reports": ["EM 1", "EM 2", ...]},
        ...
      ],
      "span_limit": 7,
      "open_reqs": [
        {"id": "vp_marketing", "title": "VP Marketing", "level": "VP",
         "comp_band": [180000, 240000]}
      ],
      "culture": {
        "trust": 62, "velocity": 70, "ownership": 58,
        "psychological_safety": 65, "transparency": 60
      }
    }

Note: `reports` entries are role/title labels (strings), not headcount ids —
span of control is simply len(reports) per authored leader.

Runtime overrides (optional):
    state._org_filled_reqs: set/list of open_req ids that have since been filled
    state._org_culture_deltas: {trait: +/-delta} applied on top of authored culture

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

def get_org_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the org block, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("org")
    if not isinstance(cfg, dict):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Sub-computations
# ────────────────────────────────────────────────────────────────────

def compute_org_chart(cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    leaders = cfg.get("leaders")
    if not isinstance(leaders, list) or not leaders:
        return None
    span_limit = int(cfg.get("span_limit", 8) or 8)
    out = []
    total_direct_reports = 0
    over_span_count = 0
    for l in leaders:
        reports = list(l.get("reports") or [])
        span = len(reports)
        over = span > span_limit
        if over:
            over_span_count += 1
        total_direct_reports += span
        out.append({
            "name": l.get("name", "Leader"),
            "role": l.get("role", ""),
            "reports": reports,
            "span_of_control": span,
            "over_span_limit": over,
        })
    return {
        "leaders": out,
        "span_limit": span_limit,
        "leader_count": len(out),
        "total_direct_reports": total_direct_reports,
        "leaders_over_span_limit": over_span_count,
    }


def compute_headcount(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Approximate headcount = named leaders + their distinct direct reports
    (reports may repeat titles across leaders, so we count raw slots, not
    unique names — this matches how the authored data is shaped)."""
    leaders = cfg.get("leaders") or []
    leader_count = len(leaders)
    report_slots = sum(len(l.get("reports") or []) for l in leaders)
    open_reqs = cfg.get("open_reqs") or []
    return {
        "current_headcount": leader_count + report_slots,
        "leader_count": leader_count,
        "report_slots": report_slots,
        "open_reqs_count": len(open_reqs),
        "planned_headcount": leader_count + report_slots + len(open_reqs),
    }


def compute_open_reqs(state: Any, cfg: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    reqs = cfg.get("open_reqs")
    if not isinstance(reqs, list) or not reqs:
        return None
    filled = set(_get(state, "_org_filled_reqs", set()) or [])
    out = []
    for r in reqs:
        rid = r.get("id")
        band = r.get("comp_band") or [None, None]
        out.append({
            "id": rid,
            "title": r.get("title", "Role"),
            "level": r.get("level"),
            "comp_band_low": band[0] if len(band) > 0 else None,
            "comp_band_high": band[1] if len(band) > 1 else None,
            "status": "filled" if rid in filled else "open",
        })
    return out


def compute_culture(state: Any, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    culture = cfg.get("culture")
    if not isinstance(culture, dict) or not culture:
        return None
    deltas = _get(state, "_org_culture_deltas", {}) or {}
    traits = {}
    for trait, base in culture.items():
        val = float(base or 0) + float(deltas.get(trait, 0) or 0)
        traits[trait] = max(0.0, min(100.0, val))
    culture_index = sum(traits.values()) / len(traits) if traits else 0.0
    weakest = min(traits, key=traits.get) if traits else None
    return {
        "traits": traits,
        "culture_index": round(culture_index, 1),
        "weakest_trait": weakest,
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_org_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    org isn't configured for this game."""
    cfg = get_org_config(game)
    if not cfg:
        return None
    payload: Dict[str, Any] = {
        "org_chart": None,
        "headcount": None,
        "open_reqs": None,
        "culture": None,
    }
    try:
        payload["org_chart"] = compute_org_chart(cfg)
    except Exception:
        pass
    try:
        payload["headcount"] = compute_headcount(cfg)
    except Exception:
        pass
    try:
        payload["open_reqs"] = compute_open_reqs(state, cfg)
    except Exception:
        pass
    try:
        payload["culture"] = compute_culture(state, cfg)
    except Exception:
        pass
    return payload
