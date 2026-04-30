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
            "solve_puzzle": self._solve_puzzle,
            "submit_synthesis": self._submit_synthesis,
            "climax_choose": self._climax_choose,
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

    def _solve_puzzle(self, run_state, game_def, action):
        puzzle_id = action.get("puzzle_id")
        answer = action.get("answer")
        puzzle = next((p for p in game_def.get("puzzles", []) if p["id"] == puzzle_id), None)
        if puzzle is None:
            raise ValueError(f"unknown puzzle: {puzzle_id}")

        prev = run_state["puzzles_solved"].get(puzzle_id, {"attempts": 0})
        attempts = prev["attempts"] + 1

        if puzzle["type"] == "factual":
            correct = (answer == puzzle["correct"])
            tags = list(puzzle["skill_tags_correct"]) if correct else list(puzzle.get("skill_tags_wrong", []))
            run_state["puzzles_solved"][puzzle_id] = {"answer": answer, "correct": correct, "attempts": attempts}
            if correct and not prev.get("correct"):
                run_state["knowledge_score"] = self._compute_knowledge_score(run_state, game_def)
        elif puzzle["type"] == "interpretive":
            per_option = puzzle.get("skill_tags_per_option", [])
            tags = list(per_option[answer]) if 0 <= answer < len(per_option) else []
            run_state["puzzles_solved"][puzzle_id] = {"answer": answer, "correct": None, "attempts": attempts}
        else:
            raise ValueError(f"unknown puzzle type: {puzzle['type']}")

        run_state["skill_tag_log"].append({"action": "solve_puzzle", "target": puzzle_id, "tags": tags})
        return run_state, {"skill_tags": tags, "knowledge_delta": 0, "events": [{"type": "puzzle_result", "puzzle_id": puzzle_id, "correct": run_state["puzzles_solved"][puzzle_id].get("correct")}]}

    def _submit_synthesis(self, run_state, game_def, action):
        groupings = action.get("groupings", {})
        board = game_def.get("evidence_board", {})
        correct_map = board.get("correct_groupings", {})
        if not correct_map:
            raise ValueError("evidence_board.correct_groupings is required")
        total = len(correct_map)
        matches = sum(1 for k, v in correct_map.items() if groupings.get(k) == v)
        accuracy = matches / total if total else 0
        is_correct = matches == total

        prev_attempts = run_state["evidence_board_state"].get("attempts", 0)
        prev_correct = run_state["evidence_board_state"].get("correct", False)
        attempts = prev_attempts + 1

        run_state["evidence_board_state"] = {
            "correct": is_correct,
            "accuracy": accuracy,
            "attempts": attempts,
            "groupings": dict(groupings),
        }

        if is_correct and prev_attempts > 0 and not prev_correct:
            # correct after a failed attempt — award both correct and partial (adaptability)
            tags = list(board.get("skill_tags_correct", [])) + list(board.get("skill_tags_partial", []))
        elif is_correct:
            tags = list(board.get("skill_tags_correct", []))
        elif prev_attempts > 0 and not prev_correct:
            # re-arranging after a failed attempt = adaptability
            tags = list(board.get("skill_tags_partial", []))
        else:
            tags = []
        run_state["skill_tag_log"].append({"action": "submit_synthesis", "target": "evidence_board", "tags": tags})
        return run_state, {"skill_tags": tags, "knowledge_delta": 0, "events": [{"type": "synthesis_result", "correct": is_correct, "accuracy": accuracy}]}

    def _compute_knowledge_score(self, run_state, game_def):
        factual = [p for p in game_def.get("puzzles", []) if p["type"] == "factual"]
        if not factual:
            return 0
        correct = sum(1 for p in factual if run_state["puzzles_solved"].get(p["id"], {}).get("correct"))
        return round(correct / len(factual) * 100)

    def _climax_choose(self, run_state, game_def, action):
        if run_state.get("outcome_label"):
            raise ValueError("climax already chosen")
        choice_id = action.get("choice")
        unlocked = self.gating_status(run_state, game_def)
        if choice_id not in unlocked:
            raise ValueError(f"climax option locked: {choice_id}")
        opt = next(o for o in game_def["climax"]["options"] if o["id"] == choice_id)
        run_state["outcome_label"] = choice_id
        tags = list(opt.get("skill_tags", []))
        run_state["skill_tag_log"].append({"action": "climax_choose", "target": choice_id, "tags": tags})
        return run_state, {"skill_tags": tags, "knowledge_delta": 0, "events": [{"type": "climax_chosen", "choice": choice_id}]}

    def gating_status(self, run_state: Dict[str, Any], game_def: Dict[str, Any]) -> List[str]:
        """Return the IDs of climax options the player has unlocked."""
        unlocked = []
        evidence_count = len(run_state.get("evidence_collected", []))
        synthesis_correct = run_state.get("evidence_board_state", {}).get("correct", False)
        for opt in game_def.get("climax", {}).get("options", []):
            gating = opt.get("gating")
            if gating is None:
                unlocked.append(opt["id"])
                continue
            if evidence_count < gating.get("evidence_min", 0):
                continue
            if gating.get("synthesis_correct") and not synthesis_correct:
                continue
            unlocked.append(opt["id"])
        return unlocked

    def _find_hotspot(self, game_def, room_id, hotspot_id):
        for room in game_def.get("rooms", []):
            if room["id"] != room_id:
                continue
            for hs in room.get("hotspots", []):
                if hs["id"] == hotspot_id:
                    return hs
        return None
