"""
Crisis Engine — executive-tier crisis-event subsystem for simulation games.

Activated only when game JSON declares `simulation_config.crisis`. When
absent, `build_crisis_payload` returns None and existing games are
unaffected.

Schema (derived from games/series-a-founders-journey.json and
games/the-founders-gauntlet.json, real committed examples):

    simulation_config.crisis = {
      "rounds": ["q4_security_incident"],       # round ids flagged as crises
      "decision_window_seconds": 120            # default countdown
    }

The matching round in game["rounds"] carries the crisis detail (also
verbatim from series-a-founders-journey.json):

    {
      "id": "q4_security_incident",
      "is_crisis_round": true,
      "decision_window_seconds": 120,           # optional per-round override
      "title": "Q4 — Security Incident",
      "scenario": "An engineer pushed a code change that leaked ...",
      "cascade_events": [
        {"label": "Customer notification required", "severity": "high"},
        {"label": "Rotate all keys", "severity": "medium"},
        {"label": "Press inquiry possible", "severity": "low"}
      ],
      "choices": [...]
    }

Unlike the other sub-engines, `build_crisis_payload` also takes
`current_round` — a crisis is inherently round-scoped.

Runtime overrides (optional):
    state._crisis_responses: {round_id: choice_id} already-submitted choices

All helpers are pure functions of (state, game, current_round) — they read
state, never mutate it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_SEVERITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}


def _get(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


# ────────────────────────────────────────────────────────────────────
# Schema activation
# ────────────────────────────────────────────────────────────────────

def get_crisis_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the crisis block, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("crisis")
    if not isinstance(cfg, dict):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Sub-computations
# ────────────────────────────────────────────────────────────────────

def is_crisis_round(cfg: Dict[str, Any], current_round: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(current_round, dict):
        return False
    if current_round.get("is_crisis_round"):
        return True
    crisis_round_ids = set(cfg.get("rounds") or [])
    return current_round.get("id") in crisis_round_ids


def compute_cascade_summary(current_round: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    events = current_round.get("cascade_events")
    if not isinstance(events, list) or not events:
        return None
    stakes_score = sum(_SEVERITY_WEIGHT.get(e.get("severity", "low"), 1) for e in events)
    return {
        "events": [
            {"label": e.get("label", "Event"), "severity": e.get("severity", "low")}
            for e in events
        ],
        "stakes_score": stakes_score,
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_crisis_payload(
    state: Any,
    game: Dict[str, Any],
    current_round: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    crisis isn't configured for this game; otherwise returns a payload that
    is `active=False` on non-crisis rounds and `active=True` with full
    detail on a crisis round."""
    cfg = get_crisis_config(game)
    if not cfg:
        return None

    all_crisis_round_ids: List[str] = list(cfg.get("rounds") or [])
    default_window = int(cfg.get("decision_window_seconds", 120) or 120)

    payload: Dict[str, Any] = {
        "configured_crisis_rounds": all_crisis_round_ids,
        "default_decision_window_seconds": default_window,
        "active": False,
        "round_id": None,
        "title": None,
        "scenario": None,
        "decision_window_seconds": None,
        "cascade": None,
        "responded": False,
    }

    if not current_round or not is_crisis_round(cfg, current_round):
        return payload

    try:
        round_id = current_round.get("id")
        responses = _get(state, "_crisis_responses", {}) or {}
        payload.update({
            "active": True,
            "round_id": round_id,
            "title": current_round.get("title"),
            "scenario": current_round.get("scenario"),
            "decision_window_seconds": int(
                current_round.get("decision_window_seconds", default_window) or default_window
            ),
            "cascade": compute_cascade_summary(current_round),
            "responded": round_id in responses,
            "response_choice_id": responses.get(round_id),
        })
    except Exception:
        pass
    return payload
