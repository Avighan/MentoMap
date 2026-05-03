"""
Executive UX — top-level builder that composes all exec subsystem payloads
into one envelope. Called from app.py alongside the existing
sim_ux_enrichment.build_ux_payload.

Each sub-engine is fully optional: a game can opt into any subset by declaring
the matching `simulation_config.<key>` block. When all are absent, this returns
an empty envelope (existing 96 SEL games are unaffected).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import finance_engine
from . import market_engine
from . import org_engine
from . import corporate_board_engine
from . import compliance_engine
from . import decision_engine
from . import crisis_engine
from . import intrapreneur_engine
from . import project_management_engine
from . import stochastic_engine
from . import market_actors_engine
from . import scorecard_engine
from . import competitor_ai_engine
from . import industry_report_engine
from . import decision_panel_engine


def build_executive_payload(
    state: Any,
    game: Dict[str, Any],
    current_round: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "finance": finance_engine.build_finance_payload(state, game),
        "market": market_engine.build_market_payload(state, game),
        "org": org_engine.build_org_payload(state, game),
        "corporate_board": corporate_board_engine.build_board_payload(state, game),
        "compliance": compliance_engine.build_compliance_payload(state, game),
        "decision_quality": decision_engine.build_decision_payload(state, game),
        "crisis": crisis_engine.build_crisis_payload(state, game, current_round),
        "intrapreneur": intrapreneur_engine.build_intrapreneur_payload(state, game),
        "project_management": project_management_engine.build_pm_payload(state, game),
        "stakeholder_map": build_stakeholder_map(state, game),
        "frameworks": build_framework_artifacts(state, game),
        "stochastic": stochastic_engine.build_stochastic_payload(state, game),
        "market_actors": market_actors_engine.build_actors_payload(state, game),
        "inbox": build_inbox_payload(state, game, current_round),
        "scorecard": scorecard_engine.build_scorecard_payload(state, game),
        "competitor_board": competitor_ai_engine.build_competitor_payload(state, game),
        "industry_report": industry_report_engine.build_industry_report_payload(state, game),
        "decision_panel": decision_panel_engine.build_decision_panel_payload(state, current_round),
    }
    # Quick "any executive subsystem active" flag for the frontend
    payload["any_executive_subsystem_active"] = any([
        finance_engine.get_finance_config(game),
        market_engine.get_market_config(game),
        org_engine.get_org_config(game),
        corporate_board_engine.get_board_config(game),
        compliance_engine.get_compliance_config(game),
        decision_engine.get_decision_config(game),
        crisis_engine.get_crisis_config(game),
        intrapreneur_engine.get_intrapreneur_config(game),
        project_management_engine.get_pm_config(game),
        bool(stochastic_engine.get_stochastic_config(game) or stochastic_engine.get_calibration_config(game)),
        bool(market_actors_engine.get_actors_config(game)),
        bool(scorecard_engine.get_scorecard_config(game)),
        bool(competitor_ai_engine.get_competitor_config(game)),
        bool(industry_report_engine.get_industry_report_config(game)),
        bool(decision_panel_engine.get_decision_panel_config(current_round)),
    ])
    return payload


# ────────────────────────────────────────────────────────────────────
# Inbox events (timed interrupts within a round)
# ────────────────────────────────────────────────────────────────────

def build_inbox_payload(state: Any, game: Dict[str, Any],
                         current_round: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Surface inbox_events declared on the current round.

    Round JSON:
      "inbox_events": [
        {"id": "ping_1", "trigger_after_seconds": 30, "from": "CTO",
         "subject": "Server's down", "body": "...",
         "choices": [{"id": "respond", "label": "Drop everything", "exec_effects": {...}}]}
      ]
    """
    if not isinstance(current_round, dict):
        return None
    events = current_round.get("inbox_events")
    if not isinstance(events, list) or not events:
        return None
    seen = getattr(state, "_inbox_seen", set()) or set()
    out = []
    for e in events:
        if not isinstance(e, dict): continue
        eid = e.get("id")
        out.append({
            "id": eid,
            "from": e.get("from", "Unknown"),
            "subject": e.get("subject", ""),
            "body": e.get("body", ""),
            "trigger_after_seconds": int(e.get("trigger_after_seconds", 0) or 0),
            "priority": e.get("priority", "normal"),
            "choices": e.get("choices") or [],
            "answered": eid in seen,
        })
    return {"events": out}


# ────────────────────────────────────────────────────────────────────
# Stakeholder map (power × interest × legitimacy)
# ────────────────────────────────────────────────────────────────────

def build_stakeholder_map(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a stakeholder mapping payload if the game declares stakeholders.

    Schema:
        simulation_config.stakeholders = [
          {"id": "alex_vc", "label": "Alex (Acme VC)",
           "power": 80, "interest": 70, "legitimacy": 85,
           "stance": "supportive"}
        ]
    Player-classified positions are stored on state._stakeholder_positions.
    """
    sim = (game or {}).get("simulation_config") or {}
    stakeholders = sim.get("stakeholders")
    if not isinstance(stakeholders, list) or not stakeholders:
        return None
    positions = getattr(state, "_stakeholder_positions", {}) or {}
    out = []
    for s in stakeholders:
        sid = s.get("id")
        pos = positions.get(sid, {})
        out.append({
            "id": sid,
            "label": s.get("label", sid),
            "power": int(pos.get("power", s.get("power", 50))),
            "interest": int(pos.get("interest", s.get("interest", 50))),
            "legitimacy": int(pos.get("legitimacy", s.get("legitimacy", 50))),
            "stance": pos.get("stance", s.get("stance", "neutral")),
            "quadrant": _quadrant(pos.get("power", s.get("power", 50)),
                                  pos.get("interest", s.get("interest", 50))),
        })
    return {
        "stakeholders": out,
        "n": len(out),
    }


def _quadrant(power: int, interest: int) -> str:
    """Mendelow's matrix: high/low power × high/low interest."""
    high_p = power >= 50
    high_i = interest >= 50
    if high_p and high_i:    return "manage_closely"
    if high_p and not high_i:return "keep_satisfied"
    if not high_p and high_i:return "keep_informed"
    return "monitor"


# ────────────────────────────────────────────────────────────────────
# Framework artifacts (OKR / SWOT / Porter / BCG)
# ────────────────────────────────────────────────────────────────────

def build_framework_artifacts(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sim = (game or {}).get("simulation_config") or {}
    frameworks = sim.get("frameworks")
    if not isinstance(frameworks, list) or not frameworks:
        return None
    user_artifacts = getattr(state, "artifacts", {}) or {}
    out = []
    for f in frameworks:
        fid = f.get("id")
        out.append({
            "id": fid,
            "type": f.get("type"),
            "label": f.get("label", fid),
            "schema": f.get("schema"),
            "user_data": user_artifacts.get(fid),
            "graded_score": (user_artifacts.get(fid) or {}).get("graded_score") if isinstance(user_artifacts.get(fid), dict) else None,
        })
    return {"artifacts": out}


def save_framework_artifact(state: Any, fid: str, data: Dict[str, Any]) -> None:
    artifacts = dict(getattr(state, "artifacts", {}) or {})
    artifacts[fid] = data
    try:
        setattr(state, "artifacts", artifacts)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────
# Multiplayer role slicing
# ────────────────────────────────────────────────────────────────────

# Role → which exec subsystems each role sees in multiplayer mode.
# 'all' means full visibility. Anything not in the list is omitted.
_ROLE_VISIBILITY = {
    "ceo":      {"finance", "market", "org", "corporate_board", "decision_quality",
                 "crisis", "stakeholder_map", "frameworks", "market_actors", "inbox"},
    "cfo":      {"finance", "compliance", "corporate_board", "decision_quality",
                 "stakeholder_map", "frameworks", "stochastic", "inbox"},
    "coo":      {"org", "project_management", "market", "decision_quality",
                 "stakeholder_map", "frameworks", "inbox"},
    "cto":      {"org", "project_management", "decision_quality", "frameworks",
                 "market_actors", "inbox"},
    "cmo":      {"market", "finance", "decision_quality", "stakeholder_map",
                 "frameworks", "market_actors", "inbox"},
    "ciso":     {"compliance", "corporate_board", "crisis", "decision_quality",
                 "frameworks", "inbox"},
    "vc":       {"finance", "market", "corporate_board", "decision_quality",
                 "frameworks", "stakeholder_map"},
    "founder":  "all",
    "pm":       {"project_management", "stakeholder_map", "decision_quality",
                 "frameworks", "inbox"},
    "intrapreneur": {"intrapreneur", "stakeholder_map", "frameworks",
                     "decision_quality", "corporate_board", "inbox"},
}


def slice_payload_for_role(payload: Dict[str, Any], role: str) -> Dict[str, Any]:
    """Return a filtered copy of the executive payload based on the player's role.

    Used by multiplayer routes so a CFO doesn't see the CTO's project dashboard
    and vice versa. Single-player flows pass role='founder' (sees everything).

    role names are case-insensitive; unknown roles fall through to 'founder'."""
    if not isinstance(payload, dict):
        return {}
    role = (role or "").lower().strip()
    visible = _ROLE_VISIBILITY.get(role, "all")
    if visible == "all":
        return payload
    out = dict(payload)
    keys_to_drop = [k for k in payload.keys() if k not in visible
                    and k not in ("any_executive_subsystem_active",)]
    for k in keys_to_drop:
        out[k] = None
    out["_mp_role"] = role
    out["_mp_visible_subsystems"] = sorted(list(visible))
    return out


def get_multiplayer_roles(game: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Return the configured multiplayer role definitions for an exec game.

    Game JSON:
      simulation_config.multiplayer:
        roles:
          - { id: "ceo",      label: "CEO",  description: "..." }
          - { id: "cfo",      label: "CFO",  description: "..." }
          - { id: "vc",       label: "Lead investor", description: "..." }
        min_players: 2
        max_players: 4
    """
    sim = (game or {}).get("simulation_config") or {}
    mp = sim.get("multiplayer") or {}
    roles = mp.get("roles")
    if not isinstance(roles, list) or not roles:
        return None
    return roles
