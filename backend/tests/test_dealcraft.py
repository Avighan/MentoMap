"""Tests for the Dealcraft pilot game (backend/games/dealcraft.json + _engine)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from games.dealcraft_engine import apply_choice, load_game, play_choices, score_run


def test_game_json_loads():
    game = load_game()
    assert game["game_id"] == "dealcraft"
    assert len(game["rounds"]) == 7
    for r in game["rounds"]:
        assert len(r["choices"]) == 4
        for c in r["choices"]:
            assert "id" in c and "label" in c and "effects" in c


def test_full_valid_playthrough_computes_a_score():
    game = load_game()
    choice_ids = [r["choices"][0]["id"] for r in game["rounds"]]
    final_state = play_choices(game, choice_ids)
    result = score_run(final_state, game)
    assert 0 <= result.total <= 100
    assert result.band  # a grade letter was assigned
    assert result.label
    assert set(result.dimensions) == {"Results", "Skill", "Reputation", "Judgment", "Resilience"}


def test_different_playthroughs_produce_different_scores():
    game = load_game()
    aggressive = [r["choices"][1]["id"] for r in game["rounds"]]  # 2nd choice each round
    ethical = ["map_interests", "invite_their_proposal", "share_switching_concerns",
               "split_the_pain", "host_joint_workshop", "disclose_the_error", "celebrate_jointly"]
    score_a = score_run(play_choices(game, aggressive), game).total
    score_b = score_run(play_choices(game, ethical), game).total
    assert score_a != score_b


def test_disclosing_the_error_raises_integrity_more_than_ignoring_it():
    game = load_game()
    state = dict(game["initial_state"])
    disclosed = apply_choice(state, game, "round_6", "disclose_the_error")
    ignored = apply_choice(state, game, "round_6", "ignore_it")
    assert disclosed["integrity"] > ignored["integrity"]


def test_unknown_round_id_rejected():
    game = load_game()
    with pytest.raises(ValueError, match="round_id"):
        apply_choice(game["initial_state"], game, "round_99", "map_interests")


def test_unknown_choice_id_rejected():
    game = load_game()
    with pytest.raises(ValueError, match="choice_id"):
        apply_choice(game["initial_state"], game, "round_1", "not_a_real_choice")


def test_wrong_number_of_choices_rejected():
    game = load_game()
    with pytest.raises(ValueError, match="Expected 7 choices"):
        play_choices(game, ["map_interests", "justified_anchor"])  # only 2, need 7
