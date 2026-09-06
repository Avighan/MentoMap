"""
Simulation UX enrichment — "legibility layer" for simulation_config games
(originated with Summer Sports League; see games/summer-sports-league.json).

Round/choice JSON for these games carries UI hint fields that are otherwise
inert: `cost_tier`, `ledger_entries`, `ripple_bullets`, `emotional_beat`, etc.
(see app.py's choice-serialization passthrough list). This module turns those
into the actual payload the frontend renders:

  - annotate_choices_with_dynamic_cost: resolves each choice's `cost_tier`
    into an actual estimated rupee cost given the player's *current* money,
    so "significant" means something different at Rs.50 than at Rs.2000.
  - snapshot_state / build_ux_payload: diff state before/after a choice into
    human-readable delta bullets, and maintain a running "Money Diary"
    (`state_obj.ledger_history`) from each choice's `ledger_entries`.
"""

from typing import Any, Dict, List, Optional

# Rough share of current money a tier represents, for cost estimation.
_TIER_PCT = {
    "free": 0.0,
    "minor": 0.05,
    "moderate": 0.12,
    "significant": 0.22,
    "major": 0.35,
    "all_in": 0.85,
}

_SKIP_SNAPSHOT_KEYS = {"log", "competitor_states"}


def _num(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    """Extract a numeric value from either a bare number or a resource dict
    (`{"value": N, "min":..., "max":...}`, the shape RunState resources use)."""
    if isinstance(value, dict):
        value = value.get("value", default)
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    return default


def annotate_choices_with_dynamic_cost(choices: List[Dict[str, Any]], current_money: Any) -> List[Dict[str, Any]]:
    """Mutate `choices` in place, adding resolved_cost_rs/weekly_cost/dynamic_label/
    forecast_line to any choice that declares a `cost_tier`. Choices without a
    cost_tier are left untouched."""
    money = _num(current_money) or 0.0
    for choice in choices or []:
        if not isinstance(choice, dict):
            continue
        tier = choice.get("cost_tier")
        if not tier:
            continue
        pct = _TIER_PCT.get(tier, _TIER_PCT["moderate"])
        resolved = round(money * pct)
        choice["resolved_cost_rs"] = resolved
        choice["weekly_cost"] = resolved

        if pct <= 0:
            choice["dynamic_label"] = "No cost"
        elif pct < 0.08:
            choice["dynamic_label"] = "Affordable"
        elif pct < 0.18:
            choice["dynamic_label"] = "Noticeable spend"
        elif pct < 0.30:
            choice["dynamic_label"] = "Tight budget"
        else:
            choice["dynamic_label"] = "Risking it all"

        if resolved > 0:
            remaining = max(0, round(money - resolved))
            choice["forecast_line"] = f"Estimated cost ~Rs.{resolved} — you'd have about Rs.{remaining} left."
        else:
            choice["forecast_line"] = "This choice costs nothing right now."
    return choices


def snapshot_state(state_obj: Any) -> Dict[str, float]:
    """Numeric-only snapshot of every resource on `state_obj`, for later diffing.
    Nested `dimension_scores` are flattened to `dimension_scores.<dim>` keys."""
    data = state_obj.to_dict() if hasattr(state_obj, "to_dict") else dict(getattr(state_obj, "__dict__", {}) or {})
    snap: Dict[str, float] = {}
    for key, value in data.items():
        if key in _SKIP_SNAPSHOT_KEYS:
            continue
        if key == "dimension_scores" and isinstance(value, dict):
            for dim, score in value.items():
                num = _num(score, default=None)
                if num is not None:
                    snap[f"dimension_scores.{dim}"] = num
            continue
        num = _num(value, default=None)
        if num is not None:
            snap[key] = num
    return snap


def _resource_label_map(game: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    out = {}
    for key, val in (game.get("initial_state") or {}).items():
        if isinstance(val, dict) and (val.get("label") or val.get("icon")):
            out[key] = {"label": val.get("label", key), "icon": val.get("icon", "")}
    return out


def _week_label(game: Dict[str, Any], round_index: int) -> str:
    time_cfg = (game.get("simulation_config") or {}).get("time_config") or {}
    label = time_cfg.get("label", "Round")
    start = time_cfg.get("start", 1)
    try:
        return f"{label} {int(start) + int(round_index)}"
    except (TypeError, ValueError):
        return f"{label} {round_index}"


def build_ux_payload(
    state_obj: Any,
    game: Dict[str, Any],
    chosen: Optional[Dict[str, Any]],
    round_data: Optional[Dict[str, Any]],
    pre_snapshot: Optional[Dict[str, float]],
    round_index: int,
) -> Dict[str, Any]:
    """Build the `ux_legibility` payload for one round: what just changed
    (delta bullets), the running Money Diary, and any narrative flourishes
    the round/choice declares. Appends to `state_obj.ledger_history` when the
    chosen option carries `ledger_entries` — callers must persist the run
    afterward for the diary to survive a refresh."""
    round_data = round_data or {}
    chosen = chosen if isinstance(chosen, dict) else None
    labels = _resource_label_map(game)

    delta_bullets = []
    if pre_snapshot:
        post_snapshot = snapshot_state(state_obj)
        for key, post_val in post_snapshot.items():
            pre_val = pre_snapshot.get(key)
            if pre_val is None:
                continue
            diff = post_val - pre_val
            if abs(diff) < 1e-9:
                continue
            meta = labels.get(key, {})
            delta_bullets.append({
                "resource": key,
                "label": meta.get("label", key.replace("_", " ").replace(".", " ").title()),
                "icon": meta.get("icon", ""),
                "delta": round(diff, 2),
                "direction": "up" if diff > 0 else "down",
            })

    ledger_history = list(getattr(state_obj, "ledger_history", None) or [])
    entries = (chosen or {}).get("ledger_entries") or []
    if entries:
        money_val = _num(getattr(state_obj, "money", getattr(state_obj, "cash", None)), default=None)
        ledger_history.append({
            "round_index": round_index,
            "week_label": _week_label(game, round_index),
            "choice_id": chosen.get("id") if chosen else None,
            "entries": entries,
            "balance_after": money_val,
        })
        setattr(state_obj, "ledger_history", ledger_history)

    ripple_bullets = (chosen or {}).get("ripple_bullets") or round_data.get("ripple_bullets") or []
    ripple_headline = (chosen or {}).get("ripple_headline") or round_data.get("transition_headline")

    narrative = {
        "emotional_beat": round_data.get("emotional_beat"),
        "target_emotion": round_data.get("target_emotion"),
        "emotional_intensity": round_data.get("emotional_intensity"),
        "concept": round_data.get("concept"),
        "badge": round_data.get("badge"),
    }
    narrative = {k: v for k, v in narrative.items() if v is not None}

    return {
        "round_index": round_index,
        "delta_bullets": delta_bullets,
        "ledger_diary": {
            "recent_entries": ledger_history[-5:],
            "total_weeks_logged": len(ledger_history),
        },
        "ripple_bullets": ripple_bullets,
        "ripple_headline": ripple_headline,
        "narrative": narrative or None,
    }
