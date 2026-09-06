"""Real unit tests for backend/engine.py, restored on this branch."""
from engine import (
    RunState,
    apply_choice,
    next_round,
    process_market_dynamics,
    evaluate_competitor_decisions,
    apply_competitor_decision,
    apply_decay_rules,
)


def _game():
    return {
        "game_id": "test_game",
        "rounds": [
            {
                "id": "r1",
                "title": "Round 1",
                "goal": "Pick wisely",
                "choices": [
                    {"id": "a", "label": "A", "delta": {"cash": -100, "reputation": 5},
                     "feedback": "You chose A", "skill_tags": ["negotiation"]},
                    {"id": "b", "label": "B", "delta": {"cash": 50}},
                ],
            },
            {"id": "r2", "title": "Round 2", "choices": [{"id": "c", "delta": {"cash": 10}}]},
        ],
    }


def test_runstate_is_both_dict_and_attribute_bag():
    state = RunState(cash=100, round_index=2)
    assert state["cash"] == 100
    assert state.cash == 100  # attribute access
    assert state.round_index == 2
    assert isinstance(state, dict)
    assert state.to_dict() == dict(state)


def test_runstate_defaults_for_managed_fields():
    state = RunState(cash=100)
    assert state.round_index == 0
    assert state.score == 0.0
    assert state.log == []
    assert state.completed is False


def test_apply_choice_applies_delta_and_logs():
    game = _game()
    state = RunState(cash=500, reputation=0)
    new_state, outcome = apply_choice(game, state, "a")
    assert new_state.cash == 400
    assert new_state.reputation == 5
    assert outcome["choice"] == "a"
    assert outcome["events"] == ["You chose A"]
    assert outcome["skill_tags"] == ["negotiation"]
    assert len(new_state.log) == 1
    assert new_state.log[0]["net_change"] == -95


def test_apply_choice_accepts_plain_dict_state():
    game = _game()
    new_state, outcome = apply_choice(game, {"cash": 500}, "b")
    assert isinstance(new_state, RunState)
    assert new_state.cash == 550


def test_apply_choice_clamps_to_resource_min_max():
    game = _game()
    state = RunState(cash={"value": 30, "min": 0, "max": 1000})
    new_state, _ = apply_choice(game, state, "a")  # delta -100
    assert new_state.cash["value"] == 0  # clamped at min, not negative


def test_next_round_increments_round_index():
    game = _game()
    state = RunState(round_index=0)
    next_round(state, game)
    assert state.round_index == 1


def test_process_market_dynamics_shares_sum_reasonably():
    state = RunState(market_fit=80, product_quality=80)
    competitors = [{"competitor_id": "rival", "market_fit": 40, "product_quality": 40}]
    shares = process_market_dynamics(state, competitors, {})
    assert set(shares) == {"player", "rival"}
    assert shares["player"]["share"] > shares["rival"]["share"]


def test_evaluate_competitor_decisions_aggressive_vs_conservative():
    aggressive = evaluate_competitor_decisions({}, RunState(), {}, {"aggressiveness": 0.9}, 0)
    conservative = evaluate_competitor_decisions({}, RunState(), {}, {"aggressiveness": 0.1}, 0)
    assert aggressive["action"] == "cut_price"
    assert conservative["action"] == "invest_quality"


def test_apply_competitor_decision_scales_by_market_multiplier():
    competitor = {"price": 100, "product_quality": 50}
    decision = {"price_delta": -10, "quality_delta": 4}
    apply_competitor_decision(competitor, decision, market_multiplier=0.5)
    assert competitor["price"] == 95
    assert competitor["product_quality"] == 52


def test_apply_decay_rules_reduces_resource_by_rate():
    competitor = {"inventory": 200}
    apply_decay_rules(competitor, {"inventory": {"decay_rate": 0.1}})
    assert competitor["inventory"] == 180
