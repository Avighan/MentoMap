"""Round takeaway generator — game-specific, deterministic (no LLM call).

Called from app.py right after a round's choice has been applied:

    takeaway = generate_round_takeaway(prev_round, outcome, game=game)
    ...
    outcome["takeaway"] = takeaway

(see app.py ~3501). If this raises, app.py falls back to a fixed dict of
exactly this shape:

    {
      "roundId": str,
      "takeawayTitle": str,
      "takeawayPoints": [str, str],
    }

That fallback is the contract this module must also satisfy — the
frontend (GamePlayPage.jsx's takeawayData / RoundTakeawayModal) reads
`roundId` / `takeawayTitle` / `takeawayPoints` off whichever of the two
it gets, so this always returns that exact shape.

`prev_round` is the round dict the player just acted in (title, id,
choices/tabs). `outcome` is the dict apply_choice() built for that
choice — the fields read here (round_id, round_title, goal, choice,
events, score_before, score_after, state_before_events,
state_after_events) are all present in app.py's own outcome construction
around the takeaway call site. Every read below is defensive (`.get()`
with fallbacks) since apply_choice() lives in a module not restored in
this pass and its exact outcome shape can vary by game type.
"""
from typing import Any, Dict, List, Optional


# Same skip-list compute_score() (app.py) uses so score-relevant resource
# deltas line up with what the player's score actually reflects.
_SKIP_KEYS = {"round_index", "dimension_scores", "memory_tags", "learning_outcomes"}

_FALLBACK_POINTS = [
    "Keep the round goal in mind and pick the option that best supports it.",
    "Watch one key resource and avoid draining it too fast.",
]


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, dict) and isinstance(value.get("value"), (int, float)):
        return float(value["value"])
    return None


def _choice_label(choice: Any, prev_round: Dict[str, Any]) -> Optional[str]:
    if isinstance(choice, dict):
        if choice.get("label"):
            return str(choice["label"])
        choice_id = choice.get("id")
    elif isinstance(choice, str):
        choice_id = choice
    else:
        return None

    if not choice_id:
        return None

    for c in prev_round.get("choices", []) or []:
        if isinstance(c, dict) and c.get("id") == choice_id:
            return c.get("label") or str(choice_id)
    for tab in prev_round.get("tabs", []) or []:
        for c in tab.get("choices", []) or []:
            if isinstance(c, dict) and c.get("id") == choice_id:
                return c.get("label") or str(choice_id)
    return str(choice_id)


def _resource_deltas(before: Any, after: Any) -> List[tuple]:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return []
    deltas = []
    for key, after_val in after.items():
        if key in _SKIP_KEYS or key.startswith("_"):
            continue
        a = _as_number(after_val)
        b = _as_number(before.get(key))
        if a is None or b is None:
            continue
        delta = a - b
        if delta != 0:
            deltas.append((key, delta))
    deltas.sort(key=lambda kd: abs(kd[1]), reverse=True)
    return deltas


def _humanize_key(key: str) -> str:
    return key.replace("_", " ").strip()


def _title_for_score_delta(score_delta: Optional[float]) -> str:
    if score_delta is None:
        return "Round wrap-up"
    if score_delta >= 10:
        return "Strong round — score climbing"
    if score_delta > 0:
        return "Solid progress this round"
    if score_delta == 0:
        return "Holding steady"
    if score_delta > -10:
        return "A rough round — regroup"
    return "Significant setback — course-correct"


def generate_round_takeaway(
    prev_round: Optional[Dict[str, Any]],
    outcome: Optional[Dict[str, Any]],
    game: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a short, deterministic natural-language takeaway for the round
    the player just completed. Never raises — worst case it returns the
    same generic-points fallback app.py itself would fall back to."""
    prev_round = prev_round or {}
    outcome = outcome or {}

    round_id = str(outcome.get("round_id") or prev_round.get("id") or "unknown_round")
    round_title = outcome.get("round_title") or prev_round.get("title") or "This round"

    score_before = _as_number(outcome.get("score_before"))
    score_after = _as_number(outcome.get("score_after"))
    score_delta = (score_after - score_before) if (score_before is not None and score_after is not None) else None

    choice_label = _choice_label(outcome.get("choice"), prev_round)
    resource_deltas = _resource_deltas(outcome.get("state_before_events"), outcome.get("state_after_events"))
    events = [e for e in (outcome.get("events") or []) if isinstance(e, str) and e.strip()]

    points: List[str] = []

    if choice_label:
        points.append(f'You chose "{choice_label}" in {round_title}.')

    if score_delta is not None:
        sign = "+" if score_delta >= 0 else ""
        points.append(
            f"Your score moved from {score_before:.0f} to {score_after:.0f} ({sign}{score_delta:.0f})."
        )

    if resource_deltas:
        key, delta = resource_deltas[0]
        direction = "rose" if delta > 0 else "fell"
        points.append(f"{_humanize_key(key).capitalize()} {direction} by {abs(delta):.0f}.")
        if len(resource_deltas) > 1:
            key2, delta2 = resource_deltas[1]
            if abs(delta2) >= abs(delta) * 0.5:
                direction2 = "rose" if delta2 > 0 else "fell"
                points.append(f"{_humanize_key(key2).capitalize()} also {direction2}, by {abs(delta2):.0f}.")

    if events and len(points) < 3:
        points.append(f"Along the way: {events[0]}")

    if not points:
        points = list(_FALLBACK_POINTS)
    elif len(points) == 1:
        points.append(_FALLBACK_POINTS[1])

    return {
        "roundId": round_id,
        "takeawayTitle": _title_for_score_delta(score_delta),
        "takeawayPoints": points[:4],
    }
