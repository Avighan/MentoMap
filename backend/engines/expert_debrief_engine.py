"""Expert Debrief Engine — per-round 100-200 word commentary explaining
why the expert_pick was the strong move.

Phase B.5 of the HBR/CapSim parity uplift. Surfaces *after* the player
commits a decision_panel submission so the player has earned the right
to see the framework view (avoids spoiling the decision).

Round JSON shape:

    {
      "id": "round_1",
      "expert_debrief": {
        "title": "Why we'd lean into the premium tilt",
        "body":  "Holding margin while ... value-destruction trap.",
        "expert_voice": "Prof. Aaker (paraphrased)",
        "tags": ["pricing", "competitive_strategy"],
        "citations": [{"label": "Aaker, Strategic Mkt Mgmt 11e", "url": null}]
      }
    }

Pure helpers — no LLM calls, no state mutation. Wiring lives in
executive_ux.build_executive_payload (per-round, like decision_panel).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def get_expert_debrief_config(current_round: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return current_round.expert_debrief or None when not opted in."""
    if not isinstance(current_round, dict):
        return None
    cfg = current_round.get("expert_debrief")
    if not isinstance(cfg, dict):
        return None
    # Require at minimum a title or body
    if not cfg.get("title") and not cfg.get("body"):
        return None
    return cfg


def build_expert_debrief_payload(
    state: Any,
    current_round: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Build the expert-debrief payload for the current round.

    Gating rule: returns None if the player has not yet committed the
    round's decision_panel submission. This keeps the framework view
    earned (no spoilers).

    Reads:
      - current_round.expert_debrief: title, body, expert_voice, tags, citations
      - state._decision_panel_submission[round_id]: presence implies committed

    Returns None when no expert_debrief config is declared on the round.
    """
    cfg = get_expert_debrief_config(current_round)
    if not cfg:
        return None

    round_id = current_round.get("id") if isinstance(current_round, dict) else None
    submissions = getattr(state, "_decision_panel_submission", None) or {}
    has_submission = (
        isinstance(submissions, dict)
        and round_id is not None
        and bool(submissions.get(round_id))
    )

    # If the round has a decision_panel and the player hasn't committed yet,
    # gate the debrief. If the round has no decision_panel at all, just show.
    has_panel = (
        isinstance(current_round, dict)
        and isinstance(current_round.get("decision_panel"), dict)
        and bool((current_round.get("decision_panel") or {}).get("controls"))
    )
    if has_panel and not has_submission:
        return None

    return {
        "round_id": round_id,
        "title": cfg.get("title"),
        "body": cfg.get("body"),
        "expert_voice": cfg.get("expert_voice"),
        "tags": cfg.get("tags") or [],
        "citations": cfg.get("citations") or [],
        "locked": False,
    }
