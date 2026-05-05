"""
PendulumLabEngine — score for a `pendulum_lab` discovery sim.

Student measures a pendulum's period at one or more lengths, then derives
g from the formula T = 2π·sqrt(L/g) → g = 4π²·L / T². The engine grades
the derived g against the true value (9.81 m/s² by default, configurable
per game JSON) using the same band-by-diff scoring used in the titration
engine. Default dimensions: attention_to_detail (careful timing) and
delayed_gratification (waiting for many periods to average out reaction-
time error).
"""
import math
from typing import Any, Dict, List

from engines._grader_common import (
    band_score_by_diff,
    coerce_weights,
    distribute_dimension_scores,
)

_DEFAULT_DIMENSION_WEIGHTS = {
    "attention_to_detail": 0.6,
    "delayed_gratification": 0.4,
}

_DEFAULT_TRUE_G = 9.81  # m/s²


def _derive_g(length_m: float, period_s: float) -> float:
    if period_s <= 0 or length_m <= 0:
        return 0.0
    return (4 * math.pi ** 2 * length_m) / (period_s ** 2)


class PendulumLabEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.pendulum = self.game_config.get("pendulum") or {}
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )

    def grade_results(self, measurements: List[Dict[str, float]]) -> Dict[str, Any]:
        """
        Args:
            measurements: list of {length_m, period_s} the student recorded.

        Returns: dict with derived_g, true_g, diff, score, band, dimension_scores.
        """
        true_g = float(self.pendulum.get("true_g") or _DEFAULT_TRUE_G)
        tolerance = float(
            (self.pendulum.get("scoring") or {}).get("tolerance_g") or 0.3
        )

        gs: List[float] = []
        for m in measurements or []:
            try:
                L = float(m.get("length_m") or 0)
                T = float(m.get("period_s") or 0)
            except (TypeError, ValueError):
                continue
            g = _derive_g(L, T)
            if g > 0:
                gs.append(g)

        if not gs:
            return {
                "score": 0,
                "band": "no_data",
                "derived_g": 0.0,
                "true_g": round(true_g, 3),
                "diff": round(true_g, 3),
                "tolerance": tolerance,
                "measurements": 0,
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        derived = sum(gs) / len(gs)
        diff = abs(derived - true_g)
        score, band = band_score_by_diff(diff, tolerance)
        return {
            "score": score,
            "band": band,
            "derived_g": round(derived, 3),
            "true_g": round(true_g, 3),
            "diff": round(diff, 3),
            "tolerance": tolerance,
            "measurements": len(gs),
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
