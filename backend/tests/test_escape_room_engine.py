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
