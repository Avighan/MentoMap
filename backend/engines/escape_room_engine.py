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
        run_state["hotspots_examined"] = []
        return run_state

    def handle_action(
        self,
        run_state: Dict[str, Any],
        game_def: Dict[str, Any],
        action: Dict[str, Any],
    ) -> tuple:
        """
        Dispatch an action verb. Returns (new_state, deltas).
        deltas = {"skill_tags": [...], "knowledge_delta": 0, "events": [...]}
        """
        verb = action.get("action")
        if verb == "examine":
            return self._examine(run_state, game_def, action)
        raise ValueError(f"unknown action verb: {verb}")

    def _examine(self, run_state, game_def, action):
        target = action.get("target", "")
        if not target.startswith("hotspot:"):
            raise ValueError(f"examine target must be a hotspot: {target}")
        hotspot_id = target.split(":", 1)[1]
        hotspot = self._find_hotspot(game_def, run_state["current_room"], hotspot_id)
        if hotspot is None:
            raise ValueError(f"unknown hotspot: {hotspot_id}")
        if hotspot_id not in run_state["hotspots_examined"]:
            run_state["hotspots_examined"].append(hotspot_id)
        tags = list(hotspot.get("skill_tags_on_examine", []))
        run_state["skill_tag_log"].append({"action": "examine", "target": hotspot_id, "tags": tags})
        return run_state, {"skill_tags": tags, "knowledge_delta": 0, "events": []}

    def _find_hotspot(self, game_def, room_id, hotspot_id):
        for room in game_def.get("rooms", []):
            if room["id"] != room_id:
                continue
            for hs in room.get("hotspots", []):
                if hs["id"] == hotspot_id:
                    return hs
        return None
