"""
The Mumbai Manufacturer — Tier B pilot game (custom settlement math).

Unlike Dealcraft (flat per-choice effects), this game closes out every
round with a settlement step: ship inventory against real quarterly
demand, charge holding cost on leftover stock, drift the bullwhip index
based on how far the order signal ran from true demand, hit customer
satisfaction on a stockout, and convert any cash shortfall into bank
debt (with interest accruing on existing debt each subsequent round).
That state-transition logic doesn't fit the stateless
`weighted_kpi_normalize`/`settlement_engine` scoring formulas — those
only score a final KPI snapshot — so it lives here as a dedicated engine
module, per the pilot's brief. Final scoring is then a normal call into
the `settlement_engine` registry formula over the resulting KPI state.

Four scheduled crisis events (fixed after specific rounds, not random)
are layered on top using the same flat-effects shape as Dealcraft.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from engines import scoring_registry

_GAME_PATH = os.path.join(os.path.dirname(__file__), "mumbai_manufacturer.json")


def load_game() -> Dict[str, Any]:
    with open(_GAME_PATH) as f:
        return json.load(f)


def _round_by_id(game: Dict[str, Any], round_id: str) -> Dict[str, Any]:
    for r in game["rounds"]:
        if r["id"] == round_id:
            return r
    raise ValueError(f"Unknown round_id '{round_id}'")


def _choice_by_id(container: Dict[str, Any], choice_id: str) -> Dict[str, Any]:
    for c in container["choices"]:
        if c["id"] == choice_id:
            return c
    raise ValueError(f"Unknown choice_id '{choice_id}' in '{container.get('id', container.get('title'))}'")


def event_after_round(game: Dict[str, Any], round_id: str) -> Optional[Dict[str, Any]]:
    for ev in game.get("scheduled_events", []):
        if ev["after_round"] == round_id:
            return ev
    return None


def apply_effects(state: Dict[str, float], effects: Dict[str, float]) -> Dict[str, float]:
    new_state = dict(state)
    for kpi, delta in effects.items():
        new_state[kpi] = new_state.get(kpi, 0) + delta
    return new_state


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def settle_round(state: Dict[str, float], choice_id: str, quarter_demand: float, game: Dict[str, Any]) -> Dict[str, float]:
    """Run the post-choice settlement step for one round.

    Order: interest on existing debt -> bullwhip drift -> ship/hold ->
    stockout or lean-fill CSAT adjustment -> convert any cash shortfall
    to bank debt. Returns a new state dict; does not mutate the input.
    """
    cfg = game["settlement_config"]
    state = dict(state)

    # 1. Interest accrues on debt carried in from previous rounds.
    if state.get("bank_debt", 0) > 0:
        state["cash"] -= state["bank_debt"] * cfg["bank_debt_interest_rate"]

    # 2. Bullwhip drift: how far did the order signal (inventory on hand
    #    going into settlement) run from true demand?
    inventory = state.get("current_inventory", 0)
    amplification_ratio = (inventory / quarter_demand) if quarter_demand > 0 else 1.0
    bullwhip_delta = round(amplification_ratio * 35 - 6)
    bullwhip_delta = _clamp(bullwhip_delta, -15, 18)
    if choice_id in cfg.get("bullwhip_reducing_choice_ids", []):
        bullwhip_delta -= 8
    if choice_id in cfg.get("bullwhip_increasing_choice_ids", []):
        bullwhip_delta += 4
    state["bullwhip_index"] = _clamp(state.get("bullwhip_index", 0) + bullwhip_delta, 0, 100)

    # 3. Ship against demand; charge holding cost on any leftover.
    shipped = min(inventory, quarter_demand)
    state["cash"] += shipped * cfg["unit_revenue"]
    leftover = max(0.0, inventory - shipped)
    state["cash"] -= leftover * cfg["holding_cost_per_unit"]

    # 4. Stockout hurts CSAT proportionally; a lean (near-zero) leftover
    #    with demand fully met is rewarded as a good fill rate.
    if quarter_demand > 0 and inventory < quarter_demand:
        stockout_ratio = (quarter_demand - inventory) / quarter_demand
        csat_penalty = round(2 + 6 * min(1.0, stockout_ratio))
        state["customer_satisfaction"] = state.get("customer_satisfaction", 0) - csat_penalty
    elif leftover <= 0.1 * quarter_demand:
        state["customer_satisfaction"] = state.get("customer_satisfaction", 0) + 2

    state["current_inventory"] = leftover

    # 5. Never let cash go negative — convert any shortfall into debt.
    if state["cash"] < 0:
        shortfall = -state["cash"]
        state["bank_debt"] = state.get("bank_debt", 0) + shortfall
        state["cash"] = 0.0

    return state


def apply_choice(state: Dict[str, float], game: Dict[str, Any], round_id: str, choice_id: str) -> Dict[str, float]:
    """Apply one round's choice effects, then run the settlement step."""
    round_def = _round_by_id(game, round_id)
    choice = _choice_by_id(round_def, choice_id)
    state = apply_effects(state, choice.get("effects", {}))
    state = settle_round(state, choice_id, round_def["quarter_demand"], game)
    return state


def apply_event(state: Dict[str, float], game: Dict[str, Any], round_id: str, choice_id: str) -> Dict[str, float]:
    """Apply the scheduled crisis event (if any) fired after `round_id`.

    No-op (returns state unchanged) if no event is scheduled after that
    round — callers can call this unconditionally after every round.
    """
    event = event_after_round(game, round_id)
    if event is None:
        return state
    choice = _choice_by_id(event, choice_id)
    return apply_effects(state, choice.get("effects", {}))


def play_full_game(game: Dict[str, Any], round_choice_ids: List[str], event_choice_ids: Dict[str, str]) -> Dict[str, float]:
    """Play every round in order, firing each round's scheduled event
    (if any) immediately after that round's settlement.

    `round_choice_ids` must have exactly one entry per round, in round
    order. `event_choice_ids` maps event id -> choice id for whichever
    events are scheduled in this game (see `scheduled_events`).
    """
    if len(round_choice_ids) != len(game["rounds"]):
        raise ValueError(
            f"Expected {len(game['rounds'])} choices (one per round), got {len(round_choice_ids)}"
        )
    state = dict(game["initial_state"])
    for round_def, choice_id in zip(game["rounds"], round_choice_ids):
        state = apply_choice(state, game, round_def["id"], choice_id)
        event = event_after_round(game, round_def["id"])
        if event is not None:
            if event["id"] not in event_choice_ids:
                raise ValueError(f"Missing choice for scheduled event '{event['id']}'")
            state = apply_event(state, game, round_def["id"], event_choice_ids[event["id"]])
    return state


def score_run(final_state: Dict[str, float], game: Dict[str, Any]) -> scoring_registry.ScoringResult:
    cfg = game["scoring_config"]
    kpis = dict(final_state)
    kpis["cash_net_debt"] = kpis.get("cash", 0) - kpis.get("bank_debt", 0)
    return scoring_registry.compute(
        cfg["formula"],
        {"kpis": kpis},
        {"categories": cfg["categories"], "grade_table": cfg["grade_table"]},
    )
