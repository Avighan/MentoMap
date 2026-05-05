"""
LabTitrationEngine — score computation for the `lab_titration` game type.

Like MusicMatchEngine, the renderer (frontend `TitrationLabRenderer`) runs the
simulator entirely client-side. On completion the renderer POSTs the recorded
volume of titrant added to `/api/run/<id>/lab-titration/complete`, which calls
this engine to:

  - re-derive the equivalence-point volume from the JSON `titration` config
    (never trust a client-supplied "ideal_mL")
  - score the player's stop volume against the tolerance in the JSON
  - distribute the score across dimension weights (default: precision +
    patience — the two skills titration most directly trains)

Output mirrors `puzzle_match_engine.get_game_summary` so the existing report
pipeline picks it up via `state.dimension_scores` + run-log entry.
"""
from typing import Any, Dict, Optional


_DEFAULT_DIMENSION_WEIGHTS = {
    "attention_to_detail": 0.5,
    "delayed_gratification": 0.5,  # patience near the endpoint
}


def _coerce_weights(weights: Optional[Dict[str, float]]) -> Dict[str, float]:
    if not weights or not isinstance(weights, dict):
        return dict(_DEFAULT_DIMENSION_WEIGHTS)
    cleaned = {k: float(v) for k, v in weights.items() if isinstance(v, (int, float)) and v > 0}
    if not cleaned:
        return dict(_DEFAULT_DIMENSION_WEIGHTS)
    total = sum(cleaned.values())
    if total <= 0:
        return dict(_DEFAULT_DIMENSION_WEIGHTS)
    return {k: v / total for k, v in cleaned.items()}


def _ideal_volume_mL(titration_cfg: Dict[str, Any]) -> float:
    """Equivalence-point volume for strong-acid + strong-base.

    For 1:1 stoichiometry: V_titrant = (Ca * Va) / Cb.
    Falls back to JSON-declared `scoring.ideal_volume_mL` if present, then to a
    safe default of 25 mL so we never divide by zero.
    """
    declared = (titration_cfg.get("scoring") or {}).get("ideal_volume_mL")
    if isinstance(declared, (int, float)) and declared > 0:
        return float(declared)
    analyte = titration_cfg.get("analyte") or {}
    titrant = titration_cfg.get("titrant") or {}
    ca = float(analyte.get("concentration_M") or 0)
    va = float(analyte.get("volume_mL") or 0)
    cb = float(titrant.get("concentration_M") or 0)
    if cb > 0:
        return (ca * va) / cb
    return 25.0


class LabTitrationEngine:
    """Stateless scorer for lab_titration games."""

    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.titration = self.game_config.get("titration") or {}
        self.weights = _coerce_weights(self.game_config.get("dimension_scoring_weights"))

    def grade_result(self, added_mL: float) -> Dict[str, Any]:
        """
        Args:
            added_mL: total volume of titrant the student added before stopping.

        Returns: dict with score (0-100), correctness band, ideal_mL, diff_mL,
        and dimension_scores.
        """
        try:
            added = float(added_mL)
        except (TypeError, ValueError):
            added = 0.0
        if added < 0:
            added = 0.0

        ideal = _ideal_volume_mL(self.titration)
        tolerance = float((self.titration.get("scoring") or {}).get("tolerance_mL") or 0.5)
        if tolerance <= 0:
            tolerance = 0.5
        diff = abs(added - ideal)

        # Same banding the renderer used, kept on the server so the score
        # cannot be inflated by tampering with the client.
        if diff <= tolerance:
            score, band = 100, "perfect"
        elif diff <= tolerance * 3:
            score, band = 70, "close"
        elif diff <= tolerance * 6:
            score, band = 40, "off"
        else:
            score, band = 10, "way_off"

        # Dimensions scaled by relative weight so the largest weight maps a
        # perfect score to 100 and others scale down proportionally.
        max_w = max(self.weights.values()) if self.weights else 1.0
        dimension_scores: Dict[str, int] = {
            dim: int(round(score * weight / max_w)) for dim, weight in self.weights.items()
        }

        return {
            "score": score,
            "band": band,
            "added_mL": round(added, 3),
            "ideal_mL": round(ideal, 3),
            "diff_mL": round(diff, 3),
            "tolerance_mL": tolerance,
            "dimension_scores": dimension_scores,
        }
