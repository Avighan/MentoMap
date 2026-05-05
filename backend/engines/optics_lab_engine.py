"""
OpticsLabEngine — `optics_lab` lens/mirror discovery sim.

Student measures object distance (do) and image distance (di) for one or
more configurations, then derives focal length f via the thin-lens
equation: 1/f = 1/do + 1/di. The engine averages the per-trial f values
and grades against the true f from the JSON.

Default dimensions: attention_to_detail + pattern_recognition (noticing
that the equation holds across multiple object distances).
"""
from typing import Any, Dict, List

from engines._grader_common import (
    band_score_by_diff,
    coerce_weights,
    distribute_dimension_scores,
)

_DEFAULT_DIMENSION_WEIGHTS = {
    "attention_to_detail": 0.5,
    "pattern_recognition": 0.5,
}


def _derive_f(do_cm: float, di_cm: float) -> float:
    """Convex-lens convention: f, do, di all positive for real images."""
    if do_cm <= 0 or di_cm <= 0:
        return 0.0
    inv = (1.0 / do_cm) + (1.0 / di_cm)
    if inv <= 0:
        return 0.0
    return 1.0 / inv


class OpticsLabEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.optics = self.game_config.get("optics") or {}
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )

    def grade_results(self, measurements: List[Dict[str, float]]) -> Dict[str, Any]:
        true_f = float(self.optics.get("true_focal_length_cm") or 10.0)
        tolerance = float((self.optics.get("scoring") or {}).get("tolerance_cm") or 0.5)

        fs: List[float] = []
        for m in measurements or []:
            try:
                do = float(m.get("object_distance_cm") or 0)
                di = float(m.get("image_distance_cm") or 0)
            except (TypeError, ValueError):
                continue
            f = _derive_f(do, di)
            if f > 0:
                fs.append(f)

        if not fs:
            return {
                "score": 0,
                "band": "no_data",
                "derived_f_cm": 0.0,
                "true_f_cm": round(true_f, 3),
                "diff_cm": round(true_f, 3),
                "tolerance_cm": tolerance,
                "trials": 0,
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        derived = sum(fs) / len(fs)
        diff = abs(derived - true_f)
        score, band = band_score_by_diff(diff, tolerance)
        return {
            "score": score,
            "band": band,
            "derived_f_cm": round(derived, 3),
            "true_f_cm": round(true_f, 3),
            "diff_cm": round(diff, 3),
            "tolerance_cm": tolerance,
            "trials": len(fs),
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
