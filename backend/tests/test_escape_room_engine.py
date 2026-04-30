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
