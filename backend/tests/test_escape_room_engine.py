import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.escape_room_engine import EscapeRoomEngine


def _minimal_game_def():
    return {
        "id": "test-game",
        "type": "mystery_room",
        "rooms": [
            {"id": "staff_room", "background_image": "/x.png", "hotspots": [], "exits": []},
            {"id": "classroom", "background_image": "/y.png", "hotspots": [], "exits": []},
        ],
        "items": [],
        "puzzles": [],
        "evidence_board": {"buckets": [], "correct_groupings": {}},
        "climax": {"options": []},
        "hints": {},
    }


def test_start_initializes_state():
    engine = EscapeRoomEngine()
    state = engine.start(run_state={}, game_def=_minimal_game_def())
    assert state["current_room"] == "staff_room"
    assert state["inventory"] == []
    assert state["evidence_collected"] == []
    assert state["evidence_board_state"] == {}
    assert state["climax_unlocked"] == []
    assert state["outcome_label"] is None
    assert state["knowledge_score"] == 0
    assert state["puzzles_solved"] == {}
    assert state["hints_used"] == {}
    assert state["hotspots_examined"] == []


def test_examine_logs_skill_tags_and_marks_seen():
    game_def = _minimal_game_def()
    game_def["rooms"][0]["hotspots"] = [
        {
            "id": "complaint_letter",
            "bbox": [0.4, 0.3, 0.5, 0.4],
            "skill_tags_on_examine": ["critical_thinking"],
        }
    ]
    engine = EscapeRoomEngine()
    state = engine.start({}, game_def)

    new_state, deltas = engine.handle_action(
        state, game_def, {"action": "examine", "target": "hotspot:complaint_letter"}
    )

    assert "complaint_letter" in new_state["hotspots_examined"]
    assert deltas["skill_tags"] == ["critical_thinking"]
    assert {"action": "examine", "target": "complaint_letter", "tags": ["critical_thinking"]} in new_state["skill_tag_log"]


def test_examine_unknown_hotspot_raises():
    import pytest
    engine = EscapeRoomEngine()
    state = engine.start({}, _minimal_game_def())
    with pytest.raises(ValueError, match="unknown hotspot"):
        engine.handle_action(state, _minimal_game_def(), {"action": "examine", "target": "hotspot:nope"})


def test_pickup_adds_item_to_inventory_and_evidence():
    game_def = _minimal_game_def()
    game_def["rooms"][0]["hotspots"] = [
        {"id": "key_spot", "bbox": [0,0,0.1,0.1], "yields_item": "staff_room_key"}
    ]
    game_def["items"] = [
        {"id": "staff_room_key", "icon": "/k.png", "is_evidence": True,
         "skill_tags_on_pickup": ["strategic_thinking"]}
    ]
    engine = EscapeRoomEngine()
    state = engine.start({}, game_def)

    new_state, deltas = engine.handle_action(
        state, game_def, {"action": "pickup", "target": "hotspot:key_spot"}
    )
    assert "staff_room_key" in new_state["inventory"]
    assert "staff_room_key" in new_state["evidence_collected"]
    assert deltas["skill_tags"] == ["strategic_thinking"]


def test_pickup_twice_is_idempotent():
    game_def = _minimal_game_def()
    game_def["rooms"][0]["hotspots"] = [
        {"id": "key_spot", "bbox": [0,0,0.1,0.1], "yields_item": "k1"}
    ]
    game_def["items"] = [{"id": "k1", "icon": "/k.png", "is_evidence": False}]
    engine = EscapeRoomEngine()
    state = engine.start({}, game_def)
    engine.handle_action(state, game_def, {"action": "pickup", "target": "hotspot:key_spot"})
    engine.handle_action(state, game_def, {"action": "pickup", "target": "hotspot:key_spot"})
    assert state["inventory"].count("k1") == 1


def test_solve_factual_puzzle_correct_increments_knowledge():
    game_def = _minimal_game_def()
    game_def["puzzles"] = [
        {"id": "p1", "type": "factual", "options": ["a","b","c"], "correct": 1,
         "skill_tags_correct": ["critical_thinking"], "skill_tags_wrong": []}
    ]
    engine = EscapeRoomEngine()
    state = engine.start({}, game_def)

    new_state, deltas = engine.handle_action(
        state, game_def, {"action": "solve_puzzle", "puzzle_id": "p1", "answer": 1}
    )
    assert new_state["puzzles_solved"]["p1"] == {"answer": 1, "correct": True, "attempts": 1}
    assert new_state["knowledge_score"] == 100  # 1/1 factual puzzles correct = 100
    assert deltas["skill_tags"] == ["critical_thinking"]


def test_solve_factual_puzzle_wrong_then_right():
    game_def = _minimal_game_def()
    game_def["puzzles"] = [
        {"id": "p1", "type": "factual", "options": ["a","b","c"], "correct": 1,
         "skill_tags_correct": ["critical_thinking"], "skill_tags_wrong": ["resilience"]}
    ]
    engine = EscapeRoomEngine()
    state = engine.start({}, game_def)
    engine.handle_action(state, game_def, {"action": "solve_puzzle", "puzzle_id": "p1", "answer": 0})
    assert state["puzzles_solved"]["p1"]["correct"] is False
    assert state["puzzles_solved"]["p1"]["attempts"] == 1
    new_state, _ = engine.handle_action(state, game_def, {"action": "solve_puzzle", "puzzle_id": "p1", "answer": 1})
    assert new_state["puzzles_solved"]["p1"]["correct"] is True
    assert new_state["puzzles_solved"]["p1"]["attempts"] == 2


def test_solve_interpretive_puzzle_emits_per_option_tags():
    game_def = _minimal_game_def()
    game_def["puzzles"] = [
        {"id": "p4", "type": "interpretive", "options": ["a","b","c"],
         "skill_tags_per_option": [["empathy"], ["empathy", "creativity"], ["creativity"]]}
    ]
    engine = EscapeRoomEngine()
    state = engine.start({}, game_def)
    new_state, deltas = engine.handle_action(state, game_def, {"action": "solve_puzzle", "puzzle_id": "p4", "answer": 1})
    assert new_state["puzzles_solved"]["p4"] == {"answer": 1, "correct": None, "attempts": 1}
    assert sorted(deltas["skill_tags"]) == ["creativity", "empathy"]


def test_submit_synthesis_correct():
    game_def = _minimal_game_def()
    game_def["evidence_board"] = {
        "buckets": ["a", "b", "irrelevant"],
        "correct_groupings": {"item1": "a", "item2": "b"},
        "skill_tags_correct": ["critical_thinking"],
        "skill_tags_partial": ["adaptability"],
    }
    engine = EscapeRoomEngine()
    state = engine.start({}, game_def)
    new_state, deltas = engine.handle_action(
        state, game_def,
        {"action": "submit_synthesis", "groupings": {"item1": "a", "item2": "b"}},
    )
    assert new_state["evidence_board_state"]["correct"] is True
    assert new_state["evidence_board_state"]["accuracy"] == 1.0
    assert new_state["evidence_board_state"]["attempts"] == 1
    assert deltas["skill_tags"] == ["critical_thinking"]


def test_submit_synthesis_partial_then_correct():
    game_def = _minimal_game_def()
    game_def["evidence_board"] = {
        "buckets": ["a", "b", "irrelevant"],
        "correct_groupings": {"item1": "a", "item2": "b"},
        "skill_tags_correct": ["critical_thinking"],
        "skill_tags_partial": ["adaptability"],
    }
    engine = EscapeRoomEngine()
    state = engine.start({}, game_def)
    engine.handle_action(state, game_def,
        {"action": "submit_synthesis", "groupings": {"item1": "b", "item2": "b"}})
    assert state["evidence_board_state"]["correct"] is False
    assert state["evidence_board_state"]["accuracy"] == 0.5
    new_state, deltas = engine.handle_action(state, game_def,
        {"action": "submit_synthesis", "groupings": {"item1": "a", "item2": "b"}})
    assert new_state["evidence_board_state"]["correct"] is True
    assert new_state["evidence_board_state"]["attempts"] == 2
    # adaptability awarded for re-arranging after wrong attempt
    assert "adaptability" in [t for entry in new_state["skill_tag_log"] for t in entry["tags"]]
