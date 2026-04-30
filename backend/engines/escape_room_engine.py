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

    def handle_action(self, run_state, game_def, action):
        verb = action.get("action")
        dispatch = {
            "examine": self._examine,
            "pickup": self._pickup,
        }
        if verb not in dispatch:
            raise ValueError(f"unknown action verb: {verb}")
        return dispatch[verb](run_state, game_def, action)

    def _pickup(self, run_state, game_def, action):
        target = action.get("target", "")
        if not target.startswith("hotspot:"):
            raise ValueError(f"pickup target must be a hotspot: {target}")
        hotspot_id = target.split(":", 1)[1]
        hotspot = self._find_hotspot(game_def, run_state["current_room"], hotspot_id)
        if hotspot is None or "yields_item" not in hotspot:
            raise ValueError(f"hotspot has no item: {hotspot_id}")
        item_id = hotspot["yields_item"]
        item = next((i for i in game_def.get("items", []) if i["id"] == item_id), None)
        if item is None:
            raise ValueError(f"item not found in catalogue: {item_id}")
        if item_id not in run_state["inventory"]:
            run_state["inventory"].append(item_id)
            if item.get("is_evidence"):
                run_state["evidence_collected"].append(item_id)
        tags = list(item.get("skill_tags_on_pickup", []))
        run_state["skill_tag_log"].append({"action": "pickup", "target": item_id, "tags": tags})
        return run_state, {"skill_tags": tags, "knowledge_delta": 0, "events": [{"type": "pickup", "item": item_id}]}

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
