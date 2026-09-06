"""Tests for the HelioGrid pilot game (backend/games/heliogrid.json +
_engine + the "benchmark_scorecard" scoring-registry formula)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from games.heliogrid_engine import (
    is_fired,
    load_game,
    play_full_game,
    resolve_quarter,
    score_run,
    validate_action,
)


def _balanced_action():
    return {
        "listPrice": 162000,
        "discounts": {"campus_estates": 5, "process_plants": 0, "retail_chains": 8, "installer_guild": 10},
        "salesAlloc": {"campus_estates": 30, "process_plants": 15, "retail_chains": 30, "installer_guild": 25},
        "headcount": 12,
        "commsSpend": 60000,
        "researchSpend": 40000,
        "featureSpend": {"efficiency": 60000, "mass": 30000, "latency": 40000},
    }


def test_game_json_loads():
    game = load_game()
    assert game["game_id"] == "heliogrid"
    assert game["quarters"] == 8
    assert set(game["segments"]) == {
        "campus_estates", "process_plants", "retail_chains", "installer_guild",
    }


def test_full_valid_playthrough_computes_a_score():
    game = load_game()
    actions = [_balanced_action() for _ in range(game["quarters"])]
    final_state = play_full_game(game, actions)
    result = score_run(final_state, game)
    assert 0 <= result.total <= 100
    assert result.band
    assert result.label
    assert set(result.dimensions) == {"cumulative_profit", "market_share_pct", "csat", "cumulative_revenue"}


def test_rival_drifts_toward_the_in_focus_segment():
    game = load_game()
    state = dict(game["initial_state"])
    action = _balanced_action()
    q0_rival_before = state["rival"]["latency"]
    new_state = resolve_quarter(state, action, 0, game)  # quarter 0 -> campus_estates in focus (latency want=32)
    assert abs(new_state["rival"]["latency"] - 32) < abs(q0_rival_before - 32)


def test_high_price_and_zero_investment_can_get_the_player_fired():
    game = load_game()
    bad_action = {
        "listPrice": 90000,
        "discounts": {"campus_estates": 0, "process_plants": 0, "retail_chains": 0, "installer_guild": 0},
        "salesAlloc": {"campus_estates": 25, "process_plants": 25, "retail_chains": 25, "installer_guild": 25},
        "headcount": 60,
        "commsSpend": 0,
        "researchSpend": 300000,
        "featureSpend": {"efficiency": 0, "mass": 0, "latency": 0},
    }
    actions = [bad_action for _ in range(game["quarters"])]
    final_state = play_full_game(game, actions)
    assert is_fired(final_state, game)
    result = score_run(final_state, game)
    assert result.total <= game["scoring_config"]["fired_score_cap"]
    assert result.label == game["scoring_config"]["fired_label"]


def test_sales_alloc_must_sum_to_100():
    game = load_game()
    action = _balanced_action()
    action["salesAlloc"] = {"campus_estates": 10, "process_plants": 10, "retail_chains": 10, "installer_guild": 10}
    with pytest.raises(ValueError, match="salesAlloc"):
        validate_action(action, game)


def test_discount_out_of_range_rejected():
    game = load_game()
    action = _balanced_action()
    action["discounts"]["campus_estates"] = 45
    with pytest.raises(ValueError, match="discounts"):
        validate_action(action, game)


def test_spend_over_budget_rejected():
    game = load_game()
    action = _balanced_action()
    action["researchSpend"] = 10_000_000
    with pytest.raises(ValueError, match="budget"):
        validate_action(action, game)


def test_wrong_number_of_quarter_actions_rejected():
    game = load_game()
    with pytest.raises(ValueError, match="Expected 8 quarter actions"):
        play_full_game(game, [_balanced_action()] * 3)
