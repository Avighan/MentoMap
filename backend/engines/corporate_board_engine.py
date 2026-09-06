"""
Corporate Board Engine — executive-tier board composition / vote / confidence
subsystem for simulation games.

Activated only when game JSON declares `simulation_config.corporate_board`.
When absent, `build_board_payload` returns None and existing games are
unaffected.

Schema (derived from games/series-a-founders-journey.json, a real committed
example):

    simulation_config.corporate_board = {
      "members": [
        {"id": "amir", "name": "Amir Patel", "role": "Lead Investor (Acme VC)",
         "alignment": 35},
        {"id": "you", "name": "You", "role": "CEO", "alignment": 100},
        ...
      ],
      "dd_checklist": [
        {"id": "data_room", "label": "Data room ready", "status": "in_progress"},
        {"id": "cap_table_clean", "label": "Cap table clean", "status": "done"},
        ...
      ]
    }

Runtime overrides (optional):
    state._board_member_alignment: {member_id: new_alignment_0_100}
    state._board_dd_status: {checklist_id: new_status}

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

def get_board_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the corporate_board block, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("corporate_board")
    if not isinstance(cfg, dict):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Sub-computations
# ────────────────────────────────────────────────────────────────────

def compute_board_members(state: Any, cfg: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    members = cfg.get("members")
    if not isinstance(members, list) or not members:
        return None
    overrides = _get(state, "_board_member_alignment", {}) or {}
    out = []
    for m in members:
        mid = m.get("id")
        alignment = float(overrides.get(mid, m.get("alignment", 50)) or 0)
        out.append({
            "id": mid,
            "name": m.get("name", "Board Member"),
            "role": m.get("role", ""),
            "alignment": alignment,
            "vote_lean": "yes" if alignment >= 50 else "no",
        })
    return out


def compute_board_confidence(members: Optional[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
    if not members:
        return None
    avg_alignment = sum(m["alignment"] for m in members) / len(members)
    yes_votes = sum(1 for m in members if m["vote_lean"] == "yes")
    majority_needed = len(members) // 2 + 1
    if avg_alignment >= 70:
        status = "strong_support"
    elif avg_alignment >= 50:
        status = "leaning_favorable"
    elif avg_alignment >= 30:
        status = "at_risk"
    else:
        status = "adversarial"
    return {
        "avg_alignment": round(avg_alignment, 1),
        "yes_votes": yes_votes,
        "no_votes": len(members) - yes_votes,
        "majority_needed": majority_needed,
        "would_pass_vote": yes_votes >= majority_needed,
        "status": status,
    }


def compute_dd_checklist(state: Any, cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    checklist = cfg.get("dd_checklist")
    if not isinstance(checklist, list) or not checklist:
        return None
    overrides = _get(state, "_board_dd_status", {}) or {}
    items = []
    done = 0
    for item in checklist:
        iid = item.get("id")
        status = overrides.get(iid, item.get("status", "todo"))
        if status == "done":
            done += 1
        items.append({
            "id": iid,
            "label": item.get("label", "Item"),
            "status": status,
        })
    return {
        "items": items,
        "total": len(items),
        "done": done,
        "completion_pct": round(done / len(items) * 100.0, 1) if items else 0.0,
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_board_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    corporate_board isn't configured for this game."""
    cfg = get_board_config(game)
    if not cfg:
        return None
    payload: Dict[str, Any] = {
        "members": None,
        "confidence": None,
        "dd_checklist": None,
    }
    try:
        payload["members"] = compute_board_members(state, cfg)
    except Exception:
        pass
    try:
        payload["confidence"] = compute_board_confidence(payload["members"])
    except Exception:
        pass
    try:
        payload["dd_checklist"] = compute_dd_checklist(state, cfg)
    except Exception:
        pass
    return payload
