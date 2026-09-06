"""
Dealcraft — Tier A pilot game (discrete branching choices).

Seven rounds, four choices each, flat per-KPI effects. This is the
simplest of the three Phase 1 pilots: applying a choice is just adding
its effects dict onto the running KPI state, and scoring is a direct call
into the existing `weighted_kpi_normalize` registry formula using the
game's own `scoring_config`.

No Flask/storage dependency — `apply_choice`/`play_choices`/`score_run`
all take and return plain dicts so they can be unit tested (and reused
by a future route handler) without booting the app.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from engines import scoring_registry

_GAME_PATH = os.path.join(os.path.dirname(__file__), "dealcraft.json")


def load_game() -> Dict[str, Any]:
    with open(_GAME_PATH) as f:
        return json.load(f)


def _round_by_id(game: Dict[str, Any], round_id: str) -> Dict[str, Any]:
    for r in game["rounds"]:
        if r["id"] == round_id:
            return r
    raise ValueError(f"Unknown round_id '{round_id}'")


def _choice_by_id(round_def: Dict[str, Any], choice_id: str) -> Dict[str, Any]:
    for c in round_def["choices"]:
        if c["id"] == choice_id:
            return c
    raise ValueError(f"Unknown choice_id '{choice_id}' in round '{round_def['id']}'")


def apply_choice(state: Dict[str, float], game: Dict[str, Any], round_id: str, choice_id: str) -> Dict[str, float]:
    """Return a new KPI state with the chosen round's effects applied.

    Raises ValueError for an unknown round_id/choice_id — the caller (a
    route handler, or a test) decides how to surface that as a 400.
    """
    round_def = _round_by_id(game, round_id)
    choice = _choice_by_id(round_def, choice_id)
    new_state = dict(state)
    for kpi, delta in choice.get("effects", {}).items():
        new_state[kpi] = new_state.get(kpi, 0) + delta
    return new_state


def play_choices(game: Dict[str, Any], choice_ids: List[str]) -> Dict[str, float]:
    """Play a full run given one choice_id per round, in round order.

    `choice_ids` must have exactly one entry per round in `game["rounds"]`.
    """
    if len(choice_ids) != len(game["rounds"]):
        raise ValueError(
            f"Expected {len(game['rounds'])} choices (one per round), got {len(choice_ids)}"
        )
    state = dict(game["initial_state"])
    for round_def, choice_id in zip(game["rounds"], choice_ids):
        state = apply_choice(state, game, round_def["id"], choice_id)
    return state


def score_run(final_state: Dict[str, float], game: Dict[str, Any]) -> scoring_registry.ScoringResult:
    cfg = game["scoring_config"]
    return scoring_registry.compute(
        cfg["formula"],
        {"kpis": final_state},
        {"categories": cfg["categories"], "grade_table": cfg["grade_table"]},
    )
