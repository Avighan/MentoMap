import pytest
from schemas import _validate_story_branching_type_game


def _make_game(scene_extra=None):
    scene = {
        "scene_id": "ch1_s1",
        "chapter": "ch1",
        "title": "Test",
        "narrative": "Test narrative",
        "choices": [{"id": "a", "label": "X", "next_scene": "ch1_s2"}],
    }
    if scene_extra:
        scene.update(scene_extra)
    return {
        "game_id": "test-game",
        "title": "Test",
        "game_type": "story_branching",
        "initial_state": {"trust": {"value": 50, "min": 0, "max": 100}},
        "story_intro": {"scenes": [scene]},
        "chapters": [{"chapter_id": "ch1", "number": 1, "title": "T", "always_unlocked": True}],
    }


def test_chat_breakout_missing_ai_persona():
    g = _make_game({"chat_breakout": {"opening_message": "hi", "max_turns": 3, "outcome_bands": {}, "next_scene_by_outcome": {}}})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert any("chat_breakout" in e and "ai_persona" in e for e in errors), errors


def test_chat_breakout_missing_opening_message():
    g = _make_game({"chat_breakout": {"ai_persona": {"name": "A"}, "max_turns": 3, "outcome_bands": {"ok": {"min_score": 0, "label": "x"}}, "next_scene_by_outcome": {"ok": "x"}}})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert any("opening_message" in e for e in errors), errors


def test_chat_breakout_outcome_band_keys_must_match_next_scene_keys():
    g = _make_game({"chat_breakout": {
        "ai_persona": {"name": "A"},
        "opening_message": "hi",
        "max_turns": 3,
        "outcome_bands": {"great": {"min_score": 75, "label": "x"}, "ok": {"min_score": 0, "label": "y"}},
        "next_scene_by_outcome": {"great": "s2", "poor": "s3"},
    }})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert any("next_scene_by_outcome" in e for e in errors), errors


def test_chat_breakout_valid():
    g = _make_game({"chat_breakout": {
        "ai_persona": {"name": "Marlow", "avatar": "🦅"},
        "opening_message": "We're listening.",
        "max_turns": 5,
        "outcome_bands": {"great": {"min_score": 75, "label": "ok"}, "poor": {"min_score": 0, "label": "ok"}},
        "next_scene_by_outcome": {"great": "ch1_s2_g", "poor": "ch1_s2_p"},
    }})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert not any("chat_breakout" in e for e in errors), errors


def test_no_chat_breakout_block_is_valid():
    """Story scenes without chat_breakout must validate normally."""
    g = _make_game()
    errors = []
    _validate_story_branching_type_game(g, errors)
    # Other validation may produce errors unrelated to chat_breakout, but no chat_breakout-related errors
    assert not any("chat_breakout" in e for e in errors), errors
