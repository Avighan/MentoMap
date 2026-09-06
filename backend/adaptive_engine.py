"""Adaptive difficulty: reads player performance signals mid-run and
queues content/competitor adjustments for upcoming rounds.

Two distinct engines are constructed in app.py (`create_adaptive_engine`
vs `create_generic_adaptive_engine`) for two different call shapes: one
tied to a run's live `state`/`round_index` (per-game, competitive-game
difficulty curve), the other a stateless one-shot `evaluate(metrics)` used
by the standalone `/api/adaptive/evaluate` route with no run involved.
"""
from typing import Any, Dict, List


class AdaptiveEngine:
    def __init__(self, game: dict):
        self.game = game
        self.rules = game.get("adaptive_rules", {}) or {}

    def evaluate_and_adapt(self, state, round_index: int) -> List[Dict[str, Any]]:
        """Inspect the player's trajectory so far and decide on
        adaptations for the upcoming round (see `apply_competitive_adaptations`)."""
        if self.rules.get("difficulty_curve", "steady") == "steady":
            return []
        score = state.get("score", 0) if isinstance(state, dict) else getattr(state, "score", 0)
        adaptations: List[Dict[str, Any]] = []
        if isinstance(score, (int, float)):
            if score > 70:
                adaptations.append({"type": "increase_difficulty", "factor": 1.1})
            elif score < 30:
                adaptations.append({"type": "decrease_difficulty", "factor": 0.9})
        return adaptations

    def apply_modifications_to_round(self, round_data: dict, modifications: dict) -> dict:
        """Overlay queued `round_modifications` onto a round before it's served."""
        mods = modifications.get("round_modifications") if isinstance(modifications, dict) else modifications
        if not mods:
            return round_data
        for mod in mods if isinstance(mods, list) else [mods]:
            if not isinstance(mod, dict) or mod.get("type") not in ("increase_difficulty", "decrease_difficulty"):
                continue
            factor = mod.get("factor", 1.0)
            for choice in round_data.get("choices", []) or []:
                delta = choice.get("delta")
                if isinstance(delta, dict):
                    # Only scale penalties (negative deltas) — difficulty
                    # adaptation should make bad choices costlier/cheaper,
                    # not blunt the reward for good ones.
                    choice["delta"] = {
                        k: (v * factor if isinstance(v, (int, float)) and v < 0 else v)
                        for k, v in delta.items()
                    }
        return round_data


class GenericAdaptiveEngine:
    def __init__(self, game: dict):
        self.game = game

    def evaluate(self, metrics: dict) -> Dict[str, Any]:
        """Suggest a difficulty adjustment from caller-supplied metrics
        (e.g. `{"accuracy": 0.4, "avg_time_ms": 12000}`), independent of
        any run — used by the standalone `/api/adaptive/evaluate` route.
        """
        adjustments: Dict[str, Any] = {}
        accuracy = metrics.get("accuracy") if isinstance(metrics, dict) else None
        if isinstance(accuracy, (int, float)):
            if accuracy > 0.8:
                adjustments["difficulty"] = "increase"
            elif accuracy < 0.4:
                adjustments["difficulty"] = "decrease"
            else:
                adjustments["difficulty"] = "steady"
        avg_time_ms = metrics.get("avg_time_ms") if isinstance(metrics, dict) else None
        if isinstance(avg_time_ms, (int, float)):
            adjustments["pacing"] = "slow_down" if avg_time_ms > 15000 else "steady"
        return adjustments


def create_adaptive_engine(game: dict) -> AdaptiveEngine:
    return AdaptiveEngine(game)


def create_generic_adaptive_engine(game: dict) -> GenericAdaptiveEngine:
    return GenericAdaptiveEngine(game)


def apply_competitive_adaptations(state, adaptations: List[Dict[str, Any]]) -> None:
    """Queue adaptations for the next round to pick up via
    `pending_round_modifications` (read by app.py's round-building code,
    which passes it straight into `AdaptiveEngine.apply_modifications_to_round`)."""
    if isinstance(state, dict):
        state["pending_round_modifications"] = adaptations
    else:
        state.pending_round_modifications = adaptations
