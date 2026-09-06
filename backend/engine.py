"""Core round-based game engine: RunState + choice/free-text application,
market simulation, and competitor AI decisions.

`RunState` is a flexible attribute bag AND a plain dict at once — it has
to be both. app.py constructs it as `RunState(**state_dict)` throughout
and reads/writes per-game resources via `hasattr`/`setattr`/`.round_index`
(attribute style, see the many `state = RunState(**state_dict)` call
sites). But `storage.create_run()` stores whatever it's given as
`run["state"]`, and the three pilot-game engines under `backend/games/`
(dealcraft_engine.py etc., which predate this restoration and are
already fully working/tested) operate on that same state purely as a
plain `Dict[str, float]` — `.get(...)`, `dict(state)`, item access. Since
both families read `run["state"]` off the exact same storage layer,
RunState subclasses `dict` so it satisfies both: attribute access for
the generic engine, and native dict semantics (`isinstance(state, dict)`
is True, `.get()` works, JSON-serializes natively) for the pilot engines.
"""
import copy
from typing import Any, Dict, List, Optional, Tuple

_MANAGED_FIELDS = {
    "round_index": 0,
    "score": 0.0,
    "dimension_scores": {},
    "competitor_states": [],
    "log": [],
    "completed": False,
}


class RunState(dict):
    def __init__(self, **kwargs):
        super().__init__()
        for field, default in _MANAGED_FIELDS.items():
            value = kwargs.pop(field, None)
            self[field] = value if value is not None else copy.deepcopy(default)
        # Whatever's left is per-game resource state, e.g. {"value": N, "min":..., "max":...}.
        for key, value in kwargs.items():
            self[key] = value

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def to_dict(self) -> Dict[str, Any]:
        return dict(self)


def _as_state(state) -> RunState:
    if isinstance(state, RunState):
        return state
    if isinstance(state, dict):
        return RunState(**state)
    return state


def _resource_value(obj):
    if isinstance(obj, dict):
        return obj.get("value")
    if isinstance(obj, (int, float)):
        return obj
    return None


def _set_resource_value(obj, value):
    if isinstance(obj, dict):
        obj["value"] = value
        return obj
    return value


def _apply_delta(state: RunState, delta: Dict[str, float]) -> None:
    for key, amount in (delta or {}).items():
        if not isinstance(amount, (int, float)):
            continue
        current = getattr(state, key, None)
        current_val = _resource_value(current)
        if current_val is None:
            setattr(state, key, amount)
            continue
        new_val = current_val + amount
        if isinstance(current, dict):
            lo, hi = current.get("min"), current.get("max")
            if isinstance(lo, (int, float)):
                new_val = max(lo, new_val)
            if isinstance(hi, (int, float)):
                new_val = min(hi, new_val)
        setattr(state, key, _set_resource_value(current, new_val))


def _find_choice(round_data: dict, choice_id) -> Optional[dict]:
    for c in round_data.get("choices", []) or []:
        if c.get("id") == choice_id:
            return c
    return None


def apply_choice(game: dict, state, choice_id, stress_event=None, time_to_decide=None) -> Tuple[RunState, dict]:
    """Apply one (or several, if `choice_id` is a list) chosen option(s)
    for the current round: sums their `delta` dicts onto state's
    resources, tags skill_tags, and returns an `outcome` dict describing
    what happened (read by app.py's /choose response builder and by
    services/round_takeaway_service.generate_round_takeaway).
    """
    state = _as_state(state)
    rounds = game.get("rounds", []) or []
    round_index = min(state.round_index, max(len(rounds) - 1, 0))
    round_data = rounds[round_index] if rounds else {}

    choice_ids = choice_id if isinstance(choice_id, list) else [choice_id]
    chosen = [c for c in (_find_choice(round_data, cid) for cid in choice_ids) if c]

    events: List[str] = []
    skill_tags: List[str] = []
    for c in chosen:
        _apply_delta(state, c.get("delta") or {})
        if c.get("feedback"):
            events.append(c["feedback"])
        skill_tags.extend(c.get("skill_tags", []) or [])

    if isinstance(stress_event, dict) and stress_event.get("delta"):
        _apply_delta(state, stress_event["delta"])
        if stress_event.get("description"):
            events.append(stress_event["description"])

    state.log.append({
        "round_id": round_data.get("round_id") or round_data.get("id"),
        "choice_id": choice_id,
        "net_change": sum(
            v for c in chosen for v in (c.get("delta") or {}).values() if isinstance(v, (int, float))
        ),
        "skill_tags": skill_tags,
        "time_to_decide": time_to_decide,
        "type": "choice",
    })

    outcome = {
        "round_title": round_data.get("round_title") or round_data.get("title", ""),
        "goal": round_data.get("goal", ""),
        "choice": choice_id,
        "events": events,
        "state_after_events": state.to_dict(),
        "skill_tags": skill_tags,
    }
    return state, outcome


def apply_free_text_response(game: dict, state, free_text: str, eval_result: dict,
                              time_to_decide=None) -> Tuple[RunState, dict]:
    """Score a free-text answer via `eval_result` (produced upstream by a
    grader — see llm.py's evaluate_free_text_response) and apply a
    resource delta scaled by `eval_result["score"]` (0-100, 50 = neutral)
    against the round's configured `free_text_max_delta`.
    """
    state = _as_state(state)
    rounds = game.get("rounds", []) or []
    round_index = min(state.round_index, max(len(rounds) - 1, 0))
    round_data = rounds[round_index] if rounds else {}

    score = eval_result.get("score", 50) if isinstance(eval_result, dict) else 50
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 50.0
    scale = (score - 50) / 50  # -1..1
    max_delta = round_data.get("free_text_max_delta") or {}
    delta = {k: v * scale for k, v in max_delta.items() if isinstance(v, (int, float))}
    if delta:
        _apply_delta(state, delta)

    events = []
    if isinstance(eval_result, dict) and eval_result.get("feedback"):
        events.append(eval_result["feedback"])

    state.log.append({
        "round_id": round_data.get("round_id") or round_data.get("id"),
        "free_text": free_text,
        "net_change": sum(delta.values()) if delta else 0,
        "type": "free_text_response",
    })

    outcome = {
        "round_title": round_data.get("round_title") or round_data.get("title", ""),
        "goal": round_data.get("goal", ""),
        "choice": "free_text",
        "events": events,
        "state_after_events": state.to_dict(),
    }
    return state, outcome


def next_round(state, game: dict) -> None:
    """Advance to the next round in place. Honors a simple conditional
    branch (`state._next_round_id`, queued by a choice's own branching
    config elsewhere) before falling back to a plain increment.
    """
    state = _as_state(state)
    rounds = game.get("rounds", []) or []
    branch_target = getattr(state, "_next_round_id", None)
    if branch_target:
        idx = next(
            (i for i, r in enumerate(rounds) if r.get("round_id") == branch_target or r.get("id") == branch_target),
            None,
        )
        state._next_round_id = None
        if idx is not None:
            state.round_index = idx
            return
    state.round_index += 1


def process_market_dynamics(state, competitor_states: List[Any], market_config: dict) -> Dict[str, dict]:
    """Distribute market share across the player and any competitors,
    proportional to each participant's `market_fit`/`product_quality`
    resources (an even split when neither is tracked).
    """
    state = _as_state(state)

    def _strength(p) -> float:
        get = (lambda k: p.get(k)) if isinstance(p, dict) else (lambda k: getattr(p, k, None))
        fit = _resource_value(get("market_fit"))
        quality = _resource_value(get("product_quality"))
        vals = [v for v in (fit, quality) if isinstance(v, (int, float))]
        return sum(vals) / len(vals) if vals else 50.0

    participants = [("player", state)] + [
        (
            (c.get("competitor_id", f"competitor_{i}") if isinstance(c, dict) else getattr(c, "competitor_id", f"competitor_{i}")),
            c,
        )
        for i, c in enumerate(competitor_states or [])
    ]

    strengths = {pid: max(_strength(p), 1.0) for pid, p in participants}
    total = sum(strengths.values()) or 1.0
    return {
        pid: {
            "share": round(strength / total, 4),
            "demand_multiplier": round(0.5 + (strength / total), 4),
        }
        for pid, strength in strengths.items()
    }


def evaluate_competitor_decisions(competitor: Any, state, market_shares: dict,
                                   personality_config: dict, round_index: int) -> Dict[str, Any]:
    """Heuristic competitor AI: `personality_config.aggressiveness` (0-1)
    picks between cutting price for share vs. investing in quality.
    """
    aggressiveness = (personality_config or {}).get("aggressiveness", 0.5)
    try:
        aggressiveness = float(aggressiveness)
    except (TypeError, ValueError):
        aggressiveness = 0.5

    if aggressiveness >= 0.5:
        action = "cut_price"
        price_delta = -5 * aggressiveness
        quality_delta = 2 * (1 - aggressiveness)
    else:
        action = "invest_quality"
        price_delta = 2 * aggressiveness
        quality_delta = 5 * (1 - aggressiveness)

    return {
        "action": action,
        "price_delta": round(price_delta, 2),
        "quality_delta": round(quality_delta, 2),
        "round_index": round_index,
    }


def apply_competitor_decision(competitor: Any, decision: Dict[str, Any], market_multiplier: float) -> None:
    """Apply an `evaluate_competitor_decisions` decision onto a
    competitor's tracked resources, scaled by its current market demand.
    """
    is_dict = isinstance(competitor, dict)
    get = (lambda k, d=0: competitor.get(k, d)) if is_dict else (lambda k, d=0: getattr(competitor, k, d))
    set_ = (lambda k, v: competitor.__setitem__(k, v)) if is_dict else (lambda k, v: setattr(competitor, k, v))

    price = _resource_value(get("price", 0)) or 0
    quality = _resource_value(get("product_quality", 0)) or 0
    set_("price", price + decision.get("price_delta", 0) * market_multiplier)
    set_("product_quality", quality + decision.get("quality_delta", 0) * market_multiplier)


def apply_decay_rules(competitor: Any, resource_metadata: Dict[str, dict]) -> None:
    """Apply a passive per-round decay to a competitor's resources, per
    each resource's `decay_rate` in `resource_metadata` (game-config-defined)."""
    is_dict = isinstance(competitor, dict)
    for key, meta in (resource_metadata or {}).items():
        decay_rate = (meta or {}).get("decay_rate")
        if not isinstance(decay_rate, (int, float)) or decay_rate == 0:
            continue
        current = competitor.get(key) if is_dict else getattr(competitor, key, None)
        value = _resource_value(current)
        if value is None:
            continue
        new_value = value * (1 - decay_rate)
        if is_dict:
            competitor[key] = new_value
        else:
            setattr(competitor, key, new_value)
