"""Tests for the Mumbai Manufacturer pilot game
(backend/games/mumbai_manufacturer.json + _engine + the new
"settlement_engine" scoring-registry formula).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines import scoring_registry
from games.mumbai_manufacturer_engine import (
    apply_choice,
    apply_event,
    event_after_round,
    load_game,
    play_full_game,
    score_run,
    settle_round,
)


def test_game_json_loads():
    game = load_game()
    assert game["game_id"] == "mumbai_manufacturer"
    assert len(game["rounds"]) == 7
    for r in game["rounds"]:
        assert "quarter_demand" in r
        assert len(r["choices"]) == 4
    assert len(game["scheduled_events"]) == 4
    scheduled_after = {ev["after_round"] for ev in game["scheduled_events"]}
    assert scheduled_after == {"round_1", "round_2", "round_3", "round_5"}


def test_settlement_engine_formula_is_registered():
    assert "settlement_engine" in scoring_registry.available()


def test_full_valid_playthrough_computes_a_score():
    game = load_game()
    round_choices = [r["choices"][0]["id"] for r in game["rounds"]]
    event_choices = {ev["id"]: ev["choices"][0]["id"] for ev in game["scheduled_events"]}
    final_state = play_full_game(game, round_choices, event_choices)
    result = score_run(final_state, game)
    assert 0 <= result.total <= 100
    assert result.band
    assert set(result.dimensions) == {"Financial", "Operational", "Customer", "Strategic", "Risk"}
    # Never let cash go negative — any shortfall must convert to debt instead.
    assert final_state["cash"] >= 0


def test_stockout_reduces_customer_satisfaction():
    game = load_game()
    state = dict(game["initial_state"])
    state["current_inventory"] = 100  # far below round_1's quarter_demand of 8000
    starting_csat = state["customer_satisfaction"]
    new_state = settle_round(state, "mrp_system", game["rounds"][0]["quarter_demand"], game)
    assert new_state["customer_satisfaction"] < starting_csat


def test_cash_shortfall_converts_to_bank_debt_not_negative_cash():
    game = load_game()
    state = dict(game["initial_state"])
    state["cash"] = 100  # nowhere near enough to cover a round's spend
    new_state = apply_choice(state, game, "round_7", "vertical_integration")  # -150,000,000 effect
    assert new_state["cash"] == 0
    assert new_state["bank_debt"] > 0


def test_scheduled_event_fires_after_its_round_and_nowhere_else():
    game = load_game()
    assert event_after_round(game, "round_1")["id"] == "monsoon_disruption"
    assert event_after_round(game, "round_4") is None


def test_unknown_round_id_rejected():
    game = load_game()
    with pytest.raises(ValueError, match="round_id"):
        apply_choice(game["initial_state"], game, "round_99", "mrp_system")


def test_unknown_event_choice_id_rejected():
    game = load_game()
    event = event_after_round(game, "round_1")
    with pytest.raises(ValueError, match="choice_id"):
        apply_event(game["initial_state"], game, "round_1", "not_a_real_choice")


def test_wrong_number_of_round_choices_rejected():
    game = load_game()
    with pytest.raises(ValueError, match="Expected 7 choices"):
        play_full_game(game, ["mrp_system"], {})


def test_missing_event_choice_rejected():
    game = load_game()
    round_choices = [r["choices"][0]["id"] for r in game["rounds"]]
    with pytest.raises(ValueError, match="monsoon_disruption"):
        play_full_game(game, round_choices, {})  # no event choices supplied at all
