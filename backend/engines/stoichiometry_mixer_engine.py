"""
StoichiometryMixerEngine — `stoichiometry_mixer` reaction-balancing game.

Generalisation of the titration engine for any 1:1, 1:2, 2:1, or n:m
stoichiometry. The JSON declares the limiting reagent's moles and the
mole ratio (e.g. {"reactant_a_moles": 0.05, "ratio_a_to_b": "1:2"});
the student reports how much of reactant B they added. The engine
re-derives the stoichiometric requirement and grades by closeness.

Default dimensions: attention_to_detail + numerical_reasoning.
"""
from typing import Any, Dict

from engines._grader_common import (
    band_score_by_diff,
    coerce_weights,
    distribute_dimension_scores,
)

_DEFAULT_DIMENSION_WEIGHTS = {
    "attention_to_detail": 0.4,
    "numerical_reasoning": 0.6,
}


def _parse_ratio(text: str) -> tuple:
    """Parse 'a:b' string → (a, b) floats. Returns (1, 1) on parse error."""
    try:
        parts = (text or "1:1").split(":")
        return float(parts[0]), float(parts[1])
    except (ValueError, IndexError):
        return 1.0, 1.0


class StoichiometryMixerEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.reaction = self.game_config.get("reaction") or {}
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )

    def grade_results(self, added_b_moles: float) -> Dict[str, Any]:
        try:
            added = float(added_b_moles)
        except (TypeError, ValueError):
            added = 0.0
        if added < 0:
            added = 0.0

        a_moles = float(self.reaction.get("reactant_a_moles") or 0.05)
        ratio_a, ratio_b = _parse_ratio(self.reaction.get("ratio_a_to_b") or "1:1")
        if ratio_a <= 0:
            ratio_a = 1.0
        ideal_b = a_moles * (ratio_b / ratio_a)
        tolerance = float(
            (self.reaction.get("scoring") or {}).get("tolerance_moles") or (ideal_b * 0.05)
        )
        if tolerance <= 0:
            tolerance = max(ideal_b * 0.05, 0.001)

        diff = abs(added - ideal_b)
        score, band = band_score_by_diff(diff, tolerance)
        return {
            "score": score,
            "band": band,
            "added_b_moles": round(added, 5),
            "ideal_b_moles": round(ideal_b, 5),
            "diff_moles": round(diff, 5),
            "tolerance_moles": round(tolerance, 5),
            "ratio": f"{int(ratio_a)}:{int(ratio_b)}",
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
