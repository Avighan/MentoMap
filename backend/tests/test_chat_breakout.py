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


def test_get_breakout_state_creates_scoped_state():
    from app import _get_breakout_state
    run = {"breakouts": {}}
    s = _get_breakout_state(run, "ch3_s2")
    assert s["history"] == []
    assert s["turn"] == 0
    assert s["closed"] is False
    # Idempotent
    s["history"].append({"speaker": "ai", "message": "hi"})
    s2 = _get_breakout_state(run, "ch3_s2")
    assert s2 is s
    # Different scene = isolated
    s3 = _get_breakout_state(run, "ch4_s1")
    assert s3 is not s


def test_pick_breakout_outcome_chooses_highest_band_below_score():
    from app import _pick_breakout_outcome
    bands = {
        "great": {"min_score": 75, "label": "x"},
        "ok":    {"min_score": 45, "label": "y"},
        "poor":  {"min_score": 0,  "label": "z"},
    }
    assert _pick_breakout_outcome(80, bands) == "great"
    assert _pick_breakout_outcome(75, bands) == "great"
    assert _pick_breakout_outcome(60, bands) == "ok"
    assert _pick_breakout_outcome(45, bands) == "ok"
    assert _pick_breakout_outcome(20, bands) == "poor"
    assert _pick_breakout_outcome(0, bands) == "poor"


def test_pick_breakout_outcome_returns_none_if_no_band_matches():
    from app import _pick_breakout_outcome
    bands = {"great": {"min_score": 90, "label": "x"}}
    assert _pick_breakout_outcome(50, bands) is None


def test_score_breakout_turn_baseline_50():
    from app import _score_breakout_turn
    assert _score_breakout_turn({}) == 50


def test_score_breakout_turn_positive_impacts_raise_score():
    from app import _score_breakout_turn
    s = _score_breakout_turn({"relationship_impact": 10, "assertiveness_impact": 5, "empathy_impact": 8})
    assert s > 50
    assert s <= 100


def test_score_breakout_turn_negative_impacts_lower_score():
    from app import _score_breakout_turn
    s = _score_breakout_turn({"relationship_impact": -10, "assertiveness_impact": -5, "empathy_impact": -8})
    assert s < 50
    assert s >= 0


def test_score_breakout_turn_handles_dict_impact_objects():
    from app import _score_breakout_turn
    s = _score_breakout_turn({
        "relationship_impact": {"value": 10, "confidence": "high"},
        "empathy_impact": {"value": 5, "confidence": "medium"},
    })
    assert s > 50


import json as _json


@pytest.fixture
def client():
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _seed_run(monkeypatch, scene):
    """Seed a fake run + game so the endpoint can resolve them."""
    fake_run = {
        "run_id": "r1",
        "game_id": "test-game",
        "state": type("S", (), {})(),  # bare object — set attrs as needed
        "log": [],
        "breakouts": {},
        "current_scene_id": scene["scene_id"],
    }
    fake_game = {
        "game_id": "test-game",
        "game_type": "story_branching",
        "story_intro": {"scenes": [scene]},
    }
    import app as appmod
    monkeypatch.setattr(appmod, "get_run", lambda rid: fake_run if rid == "r1" else (_ for _ in ()).throw(KeyError(rid)))
    monkeypatch.setattr(appmod, "get_game_or_400", lambda gid: (fake_game, None))
    return fake_run, fake_game


def test_breakout_chat_returns_ai_message_and_increments_turn(monkeypatch, client):
    scene = {
        "scene_id": "ch3_s2",
        "narrative": "x",
        "chat_breakout": {
            "ai_persona": {"name": "Marlow", "avatar": "🦅"},
            "opening_message": "We're listening.",
            "max_turns": 3,
            "outcome_bands": {"great": {"min_score": 75, "label": "ok"}, "poor": {"min_score": 0, "label": "no"}},
            "next_scene_by_outcome": {"great": "ch3_s3_g", "poor": "ch3_s3_p"},
            "state_delta_by_outcome": {"great": {}, "poor": {}},
        },
    }
    _seed_run(monkeypatch, scene)
    import app as appmod
    monkeypatch.setattr(appmod, "update_run", lambda rid, r: None)
    monkeypatch.setattr(
        appmod, "negotiation_ai_response",
        lambda **kw: {"response": "We hear you.", "analysis": {"relationship_impact": 5, "empathy_impact": 5}},
    )
    resp = client.post("/api/run/r1/breakout-chat", json={"scene_id": "ch3_s2", "message": "Hello captain"})
    assert resp.status_code == 200, resp.data
    body = resp.get_json()
    assert body["ai_message"] == "We hear you."
    assert body["turn"] == 1
    assert body["closed"] is False


def test_breakout_chat_closes_at_max_turns_and_returns_outcome(monkeypatch, client):
    scene = {
        "scene_id": "ch3_s2",
        "narrative": "x",
        "chat_breakout": {
            "ai_persona": {"name": "Marlow"},
            "opening_message": "ok",
            "max_turns": 1,
            "outcome_bands": {"great": {"min_score": 75, "label": "ok"}, "poor": {"min_score": 0, "label": "no"}},
            "next_scene_by_outcome": {"great": "ch3_s3_g", "poor": "ch3_s3_p"},
            "state_delta_by_outcome": {"great": {}, "poor": {}},
        },
    }
    _seed_run(monkeypatch, scene)
    import app as appmod
    monkeypatch.setattr(appmod, "update_run", lambda rid, r: None)
    monkeypatch.setattr(
        appmod, "negotiation_ai_response",
        lambda **kw: {"response": "Deal.", "analysis": {"relationship_impact": 30, "empathy_impact": 30, "assertiveness_impact": 10}},
    )
    resp = client.post("/api/run/r1/breakout-chat", json={"scene_id": "ch3_s2", "message": "Let's share credit"})
    body = resp.get_json()
    assert body["closed"] is True
    assert body["outcome"] == "great"
    assert body["next_scene_id"] == "ch3_s3_g"
    # Verify the breakout was logged for the report scorer
    log = appmod.get_run("r1").get("log", [])
    assert any(e.get("type") == "chat_breakout" and e.get("scene_id") == "ch3_s2" for e in log)


def test_breakout_chat_400_when_scene_not_a_breakout(monkeypatch, client):
    scene = {"scene_id": "ch1_s1", "narrative": "x", "choices": [{"id": "a", "next_scene": "x"}]}
    _seed_run(monkeypatch, scene)
    resp = client.post("/api/run/r1/breakout-chat", json={"scene_id": "ch1_s1", "message": "hi"})
    assert resp.status_code == 400
    assert "not a chat_breakout" in resp.get_json()["error"].lower() or "breakout" in resp.get_json()["error"].lower()


def test_breakout_chat_applies_state_delta_on_close(monkeypatch, client):
    # State object with a numeric attribute that should get the delta applied
    class FakeState:
        pass
    fake_state = FakeState()
    fake_state.trust = 40  # plain int

    scene = {
        "scene_id": "ch3_s2",
        "narrative": "x",
        "chat_breakout": {
            "ai_persona": {"name": "Marlow"},
            "opening_message": "ok",
            "max_turns": 1,
            "outcome_bands": {"great": {"min_score": 75, "label": "ok"}, "poor": {"min_score": 0, "label": "no"}},
            "next_scene_by_outcome": {"great": "ch3_s3_g", "poor": "ch3_s3_p"},
            "state_delta_by_outcome": {"great": {"trust": 15}, "poor": {"trust": -10}},
        },
    }
    fake_run = {
        "run_id": "r2",
        "game_id": "test-game",
        "state": fake_state,
        "log": [],
        "breakouts": {},
        "current_scene_id": scene["scene_id"],
    }
    fake_game = {
        "game_id": "test-game",
        "game_type": "story_branching",
        "story_intro": {"scenes": [scene]},
    }
    import app as appmod
    monkeypatch.setattr(appmod, "get_run", lambda rid: fake_run if rid == "r2" else (_ for _ in ()).throw(KeyError(rid)))
    monkeypatch.setattr(appmod, "get_game_or_400", lambda gid: (fake_game, None))
    monkeypatch.setattr(appmod, "update_run", lambda rid, r: None)  # no-op persist
    monkeypatch.setattr(
        appmod, "negotiation_ai_response",
        lambda **kw: {"response": "Deal.", "analysis": {"relationship_impact": 30, "empathy_impact": 30, "assertiveness_impact": 10}},
    )
    resp = client.post("/api/run/r2/breakout-chat", json={"scene_id": "ch3_s2", "message": "Let's share credit"})
    assert resp.status_code == 200, resp.data
    body = resp.get_json()
    assert body["closed"] is True
    assert body["outcome"] == "great"
    # Delta of +15 should have been applied
    assert fake_state.trust == 55


def test_the_treaty_loads_with_breakouts():
    import json, os
    path = os.path.join(os.path.dirname(__file__), "..", "games", "the-treaty.json")
    d = json.load(open(path))
    scenes = (d.get("story_intro") or {}).get("scenes", []) or (d.get("story") or {}).get("branches", [])
    breakout_scenes = [s for s in scenes if "chat_breakout" in s]
    assert len(breakout_scenes) == 3, f"expected 3 breakouts, got {len(breakout_scenes)}"
    from schemas import _validate_story_branching_type_game
    errors = []
    _validate_story_branching_type_game(d, errors)
    assert errors == [], errors


def test_bazaar_deal_loads_with_breakouts():
    import json, os
    path = os.path.join(os.path.dirname(__file__), "..", "games", "the-great-bazaar-deal.json")
    d = json.load(open(path))
    scenes = (d.get("story_intro") or {}).get("scenes", []) or (d.get("story") or {}).get("branches", [])
    breakout_scenes = [s for s in scenes if "chat_breakout" in s]
    assert len(breakout_scenes) == 3
    from schemas import _validate_story_branching_type_game
    errors = []
    _validate_story_branching_type_game(d, errors)
    assert errors == [], errors


def test_street_market_loads_with_breakouts():
    import json, os
    path = os.path.join(os.path.dirname(__file__), "..", "games", "the-street-market-negotiator.json")
    d = json.load(open(path))
    scenes = (d.get("story_intro") or {}).get("scenes", []) or (d.get("story") or {}).get("branches", [])
    breakout_scenes = [s for s in scenes if "chat_breakout" in s]
    assert len(breakout_scenes) == 3
    from schemas import _validate_story_branching_type_game
    errors = []
    _validate_story_branching_type_game(d, errors)
    assert errors == [], errors
