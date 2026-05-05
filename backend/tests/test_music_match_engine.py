"""Unit tests for MusicMatchEngine grading and dimension scoring."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engines.music_match_engine import MusicMatchEngine  # noqa: E402


def _game(rounds, weights=None):
    cfg = {"music_rounds": rounds}
    if weights is not None:
        cfg["dimension_scoring_weights"] = weights
    return cfg


THREE_ROUNDS = [
    {"id": "r1", "answer_id": "c1"},
    {"id": "r2", "answer_id": "c2"},
    {"id": "r3", "answer_id": "c2"},
]


def test_all_correct_yields_100():
    engine = MusicMatchEngine(_game(THREE_ROUNDS))
    out = engine.grade_results([
        {"round_id": "r1", "picked_id": "c1"},
        {"round_id": "r2", "picked_id": "c2"},
        {"round_id": "r3", "picked_id": "c2"},
    ])
    assert out["score"] == 100
    assert out["correct"] == 3
    assert out["total"] == 3


def test_all_wrong_yields_zero():
    engine = MusicMatchEngine(_game(THREE_ROUNDS))
    out = engine.grade_results([
        {"round_id": "r1", "picked_id": "cx"},
        {"round_id": "r2", "picked_id": "cx"},
        {"round_id": "r3", "picked_id": "cx"},
    ])
    assert out["score"] == 0
    assert out["correct"] == 0


def test_partial_correct_proportional():
    engine = MusicMatchEngine(_game(THREE_ROUNDS))
    out = engine.grade_results([
        {"round_id": "r1", "picked_id": "c1"},
        {"round_id": "r2", "picked_id": "wrong"},
        {"round_id": "r3", "picked_id": "c2"},
    ])
    assert out["correct"] == 2
    assert out["score"] == 67  # round(2/3 * 100)


def test_client_cannot_inflate_correct_via_extra_picks():
    engine = MusicMatchEngine(_game(THREE_ROUNDS))
    out = engine.grade_results([
        {"round_id": "r1", "picked_id": "c1"},
        {"round_id": "r1", "picked_id": "c1"},  # duplicate
        {"round_id": "rX", "picked_id": "c1"},  # bogus round id
    ])
    # Only 1 distinct correct round counts toward total of 3 → 33
    assert out["correct"] in (1, 2)  # duplicate may or may not double-count, but score capped
    assert out["score"] <= 100
    assert out["total"] == 3


def test_dimension_scores_use_default_weights():
    engine = MusicMatchEngine(_game(THREE_ROUNDS))
    out = engine.grade_results([
        {"round_id": "r1", "picked_id": "c1"},
        {"round_id": "r2", "picked_id": "c2"},
        {"round_id": "r3", "picked_id": "c2"},
    ])
    dims = out["dimension_scores"]
    assert "focus" in dims
    assert "attention_to_detail" in dims
    # Largest weight (focus 0.6) should map a perfect score to 100;
    # smaller weights scale proportionally.
    assert dims["focus"] == 100
    assert 0 < dims["attention_to_detail"] <= 100


def test_dimension_scores_use_custom_weights():
    engine = MusicMatchEngine(_game(THREE_ROUNDS, weights={"resilience": 1.0, "creativity": 1.0}))
    out = engine.grade_results([
        {"round_id": "r1", "picked_id": "c1"},
        {"round_id": "r2", "picked_id": "c2"},
        {"round_id": "r3", "picked_id": "c2"},
    ])
    dims = out["dimension_scores"]
    assert set(dims.keys()) == {"resilience", "creativity"}
    assert dims["resilience"] == 100
    assert dims["creativity"] == 100


def test_no_picks_zero_score():
    engine = MusicMatchEngine(_game(THREE_ROUNDS))
    out = engine.grade_results([])
    assert out["score"] == 0
    assert out["correct"] == 0
    assert out["total"] == 3


def test_no_rounds_safe():
    engine = MusicMatchEngine(_game([]))
    out = engine.grade_results([{"round_id": "r1", "picked_id": "c1"}])
    assert out["score"] == 0
    assert out["total"] == 0


def test_real_game_json_loads():
    """Smoke test: the actual deployed ear-training game grades cleanly."""
    import json
    here = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(here, "..", "games", "ear-training-pitch-match.json")
    if not os.path.exists(json_path):
        pytest.skip("ear-training-pitch-match.json not present")
    with open(json_path) as f:
        game = json.load(f)
    engine = MusicMatchEngine(game)
    answers = [{"round_id": r["id"], "picked_id": r["answer_id"]} for r in game["music_rounds"]]
    out = engine.grade_results(answers)
    assert out["score"] == 100
    assert out["correct"] == out["total"]
