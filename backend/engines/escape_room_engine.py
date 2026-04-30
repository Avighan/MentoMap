"""
Escape Room Engine — orchestrates the mystery_room game type.

Pure-functional surface: every method takes (run_state, ...) and returns
the updated state. No Flask coupling.
"""
from typing import Any, Dict, List


class EscapeRoomEngine:
    """Orchestrator for mystery_room games."""

    def start(self, run_state: Dict[str, Any], game_def: Dict[str, Any]) -> Dict[str, Any]:
        """Initialise mystery-room state. Idempotent."""
        rooms = game_def.get("rooms", [])
        if not rooms:
            raise ValueError("mystery_room game must define at least one room")
        run_state["current_room"] = rooms[0]["id"]
        run_state["inventory"] = []
        run_state["evidence_collected"] = []
        run_state["evidence_board_state"] = {}
        run_state["climax_unlocked"] = []
        run_state["outcome_label"] = None
        run_state["knowledge_score"] = 0
        run_state["puzzles_solved"] = {}
        run_state["hints_used"] = {}
        run_state["skill_tag_log"] = []
        return run_state
