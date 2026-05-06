import pytest
from schemas import _validate_story_branching_type_game, validate_bundle


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
    g = _make_game({"chat_breakout": {
        "opening_message": "hi",
        "max_turns": 3,
        "outcome_bands": {"ok": {"min_score": 0, "label": "x"}},
        "next_scene_by_outcome": {"ok": "ch1_s1"},
    }})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert any("ai_persona" in e for e in errors), errors


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


def _make_terminal_scene(extra=None):
    scene = {
        "scene_id": "ch1_s1",
        "chapter": "ch1",
        "title": "Test",
        "narrative": "Test narrative",
        "transitions_to_gameplay": True,
        "choices": [],
    }
    if extra:
        scene.update(extra)
    return scene


def test_validate_bundle_propagates_chat_breakout_errors():
    """validate_bundle must raise when chat_breakout block is malformed."""
    bundle = {
        "games": [
            {
                "game_id": "bad-cb",
                "title": "Bad CB",
                "game_type": "story_branching",
                "initial_state": {},
                "story_intro": {
                    "scenes": [
                        _make_terminal_scene({
                            "chat_breakout": {
                                "ai_persona": {"name": "A"},
                                "opening_message": "hi",
                                "max_turns": 3,
                                "outcome_bands": {"great": {"min_score": 75, "label": "x"}},
                                "next_scene_by_outcome": {"poor": "x"},
                            }
                        })
                    ]
                },
            }
        ]
    }
    with pytest.raises(ValueError, match="next_scene_by_outcome"):
        validate_bundle(bundle)


def test_chat_breakout_max_turns_out_of_range():
    g = _make_game({"chat_breakout": {
        "ai_persona": {"name": "A"},
        "opening_message": "hi",
        "max_turns": 0,
        "outcome_bands": {"ok": {"min_score": 0, "label": "x"}},
        "next_scene_by_outcome": {"ok": "ch1_s1"},
    }})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert any("max_turns" in e for e in errors), errors


def test_chat_breakout_max_turns_bool_rejected():
    g = _make_game({"chat_breakout": {
        "ai_persona": {"name": "A"},
        "opening_message": "hi",
        "max_turns": True,  # bool subclass of int — must be rejected
        "outcome_bands": {"ok": {"min_score": 0, "label": "x"}},
        "next_scene_by_outcome": {"ok": "ch1_s1"},
    }})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert any("max_turns" in e for e in errors), errors


def test_chat_breakout_band_missing_min_score_or_label():
    g = _make_game({"chat_breakout": {
        "ai_persona": {"name": "A"},
        "opening_message": "hi",
        "max_turns": 3,
        "outcome_bands": {"ok": {"label": "x"}, "bad": {"min_score": 50}},
        "next_scene_by_outcome": {"ok": "ch1_s1", "bad": "ch1_s1"},
    }})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert any("min_score" in e for e in errors), errors
    assert any("label" in e for e in errors), errors


def test_chat_breakout_next_scene_value_must_be_nonempty_string():
    g = _make_game({"chat_breakout": {
        "ai_persona": {"name": "A"},
        "opening_message": "hi",
        "max_turns": 3,
        "outcome_bands": {"ok": {"min_score": 0, "label": "x"}, "bad": {"min_score": 50, "label": "y"}},
        "next_scene_by_outcome": {"ok": "", "bad": 42},
    }})
    errors = []
    _validate_story_branching_type_game(g, errors)
    assert any("next_scene_by_outcome.ok" in e for e in errors), errors
    assert any("next_scene_by_outcome.bad" in e for e in errors), errors


def test_validate_bundle_passes_with_valid_chat_breakout():
    bundle = {
        "games": [
            {
                "game_id": "ok-cb",
                "title": "OK CB",
                "game_type": "story_branching",
                "initial_state": {},
                "story_intro": {
                    "scenes": [
                        _make_terminal_scene({
                            "chat_breakout": {
                                "ai_persona": {"name": "Marlow", "avatar": "🦅"},
                                "opening_message": "We're listening.",
                                "max_turns": 5,
                                "outcome_bands": {
                                    "great": {"min_score": 75, "label": "ok"},
                                    "poor": {"min_score": 0, "label": "ok"},
                                },
                                "next_scene_by_outcome": {"great": "ch1_s1", "poor": "ch1_s1"},
                            }
                        })
                    ]
                },
            }
        ]
    }
    validate_bundle(bundle)  # must not raise
