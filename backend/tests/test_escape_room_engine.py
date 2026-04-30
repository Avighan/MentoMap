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
    assert state["rooms_visited"] == ["staff_room"]
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


def test_solve_factual_ordering_puzzle():
    g = _minimal_game_def()
    g["puzzles"] = [{"id": "p3", "type": "factual",
                     "ordering_items": [
                         {"id": "a", "correct_position": 2},
                         {"id": "b", "correct_position": 1},
                         {"id": "c", "correct_position": 3}],
                     "skill_tags_correct": ["critical_thinking"],
                     "skill_tags_wrong": []}]
    engine = EscapeRoomEngine()
    state = engine.start({}, g)
    new_state, _ = engine.handle_action(state, g, {"action": "solve_puzzle", "puzzle_id": "p3", "answer": ["b", "a", "c"]})
    assert new_state["puzzles_solved"]["p3"]["correct"] is True
    # Wrong order
    state2 = engine.start({}, g)
    new_state2, _ = engine.handle_action(state2, g, {"action": "solve_puzzle", "puzzle_id": "p3", "answer": ["a", "b", "c"]})
    assert new_state2["puzzles_solved"]["p3"]["correct"] is False


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


def _climax_game_def():
    g = _minimal_game_def()
    g["climax"] = {
        "options": [
            {"id": "compliant_bystander", "label": "Walk away", "gating": None,
             "skill_tags": []},
            {"id": "cautious_investigator", "label": "Tell teacher", "gating": None,
             "skill_tags": ["critical_thinking"]},
            {"id": "quiet_protector", "label": "Quiet help",
             "gating": {"evidence_min": 4}, "skill_tags": ["empathy", "courage"]},
            {"id": "whistleblower", "label": "Confront",
             "gating": {"evidence_min": 7, "synthesis_correct": True},
             "skill_tags": ["courage", "ethical_reasoning"]},
        ]
    }
    return g


def test_climax_unlocked_no_evidence_only_baseline():
    engine = EscapeRoomEngine()
    state = engine.start({}, _climax_game_def())
    unlocked = engine.gating_status(state, _climax_game_def())
    assert sorted(unlocked) == ["cautious_investigator", "compliant_bystander"]


def test_climax_unlocked_mid_tier():
    engine = EscapeRoomEngine()
    state = engine.start({}, _climax_game_def())
    state["evidence_collected"] = ["a", "b", "c", "d"]
    unlocked = engine.gating_status(state, _climax_game_def())
    assert "quiet_protector" in unlocked
    assert "whistleblower" not in unlocked


def test_climax_unlocked_top_tier_requires_synthesis():
    engine = EscapeRoomEngine()
    g = _climax_game_def()
    state = engine.start({}, g)
    state["evidence_collected"] = ["a","b","c","d","e","f","g"]
    state["evidence_board_state"] = {"correct": False, "accuracy": 0.7, "attempts": 1, "groupings": {}}
    unlocked = engine.gating_status(state, g)
    assert "whistleblower" not in unlocked

    state["evidence_board_state"] = {"correct": True, "accuracy": 1.0, "attempts": 1, "groupings": {}}
    unlocked = engine.gating_status(state, g)
    assert "whistleblower" in unlocked


def test_climax_choose_locked_option_raises():
    import pytest
    engine = EscapeRoomEngine()
    g = _climax_game_def()
    state = engine.start({}, g)
    with pytest.raises(ValueError, match="locked"):
        engine.handle_action(state, g, {"action": "climax_choose", "choice": "whistleblower"})


def test_climax_choose_sets_outcome_label_and_emits_tags():
    engine = EscapeRoomEngine()
    g = _climax_game_def()
    state = engine.start({}, g)
    new_state, deltas = engine.handle_action(state, g, {"action": "climax_choose", "choice": "compliant_bystander"})
    assert new_state["outcome_label"] == "compliant_bystander"
    assert deltas["skill_tags"] == []


def test_climax_choose_double_raises():
    import pytest
    engine = EscapeRoomEngine()
    g = _climax_game_def()
    state = engine.start({}, g)
    engine.handle_action(state, g, {"action": "climax_choose", "choice": "cautious_investigator"})
    with pytest.raises(ValueError, match="already chosen"):
        engine.handle_action(state, g, {"action": "climax_choose", "choice": "compliant_bystander"})


def test_move_to_room_changes_current_room():
    g = _minimal_game_def()
    g["rooms"][0]["exits"] = [{"to": "classroom", "bbox": [0.9, 0.4, 1.0, 0.7]}]
    engine = EscapeRoomEngine()
    state = engine.start({}, g)
    new_state, deltas = engine.handle_action(state, g, {"action": "move_to_room", "target": "classroom"})
    assert new_state["current_room"] == "classroom"
    assert {"type": "room_change", "from": "staff_room", "to": "classroom"} in deltas["events"]


def test_move_appends_to_rooms_visited():
    g = _minimal_game_def()
    g["rooms"][0]["exits"] = [{"to": "classroom", "bbox": [0, 0, 0, 0]}]
    engine = EscapeRoomEngine()
    state = engine.start({}, g)
    engine.handle_action(state, g, {"action": "move_to_room", "target": "classroom"})
    assert state["rooms_visited"] == ["staff_room", "classroom"]
    # Idempotent on re-visit
    g["rooms"][1]["exits"] = [{"to": "staff_room", "bbox": [0, 0, 0, 0]}]
    engine.handle_action(state, g, {"action": "move_to_room", "target": "staff_room"})
    assert state["rooms_visited"] == ["staff_room", "classroom"]


def test_move_to_room_invalid_exit_raises():
    import pytest
    g = _minimal_game_def()  # no exits defined
    engine = EscapeRoomEngine()
    state = engine.start({}, g)
    with pytest.raises(ValueError, match="no exit"):
        engine.handle_action(state, g, {"action": "move_to_room", "target": "classroom"})


def test_request_hint_returns_first_then_second_then_solution():
    g = _minimal_game_def()
    g["puzzles"] = [{"id": "p1", "type": "factual", "options": ["a","b"], "correct": 0,
                     "skill_tags_correct": [], "skill_tags_wrong": []}]
    g["hints"] = {"p1": ["nudge", "pointer", "solution"]}
    engine = EscapeRoomEngine()
    state = engine.start({}, g)

    s1, d1 = engine.handle_action(state, g, {"action": "request_hint", "puzzle_id": "p1"})
    assert d1["events"][0] == {"type": "hint", "puzzle_id": "p1", "level": 1, "text": "nudge"}
    s2, d2 = engine.handle_action(s1, g, {"action": "request_hint", "puzzle_id": "p1"})
    assert d2["events"][0]["text"] == "pointer"
    s3, d3 = engine.handle_action(s2, g, {"action": "request_hint", "puzzle_id": "p1"})
    assert d3["events"][0]["text"] == "solution"
    s4, d4 = engine.handle_action(s3, g, {"action": "request_hint", "puzzle_id": "p1"})
    # past last hint = repeat last
    assert d4["events"][0]["text"] == "solution"
    assert s4["hints_used"]["p1"] == 4


def test_compute_fingerprint_aggregates_skill_tag_log():
    g = _minimal_game_def()
    engine = EscapeRoomEngine()
    state = engine.start({}, g)
    state["skill_tag_log"] = [
        {"action": "examine", "target": "x", "tags": ["empathy"]},
        {"action": "solve_puzzle", "target": "p1", "tags": ["empathy", "critical_thinking"]},
        {"action": "climax_choose", "target": "whistleblower", "tags": ["courage", "ethical_reasoning"]},
    ]
    fp = engine.compute_fingerprint(state)
    assert fp["empathy"] == 2
    assert fp["critical_thinking"] == 1
    assert fp["courage"] == 1
    assert fp["ethical_reasoning"] == 1
    assert sum(fp.values()) == 5
