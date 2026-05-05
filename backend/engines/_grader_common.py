"""
Shared helpers for the family of "frontend-sim + backend-grader" engines.

These engines (music_match, lab_titration, pendulum_lab, optics_lab,
circuit_debugger, genetics_cross, stoichiometry_mixer, mental_math,
typing_drill, boggle, mock_interview, sudoku, logic_grid,
geometry_constructor) all share the same basic shape:

  - the renderer runs the simulator client-side
  - on completion, the renderer POSTs raw observations to the backend
  - the backend re-derives correctness from the JSON config (the only
    authoritative source) and returns a score + dimension breakdown
  - the existing /report pipeline picks up `dimension_scores` with no
    special-casing per game type

The two helpers below capture the common scoring logic so each engine
stays focused on its domain (deriving the "correct" answer) rather than
re-implementing weight normalization and dimension distribution.
"""
from typing import Dict, Optional


def coerce_weights(
    weights: Optional[Dict[str, float]],
    defaults: Dict[str, float],
) -> Dict[str, float]:
    """Normalise a dimension-weights dict so values sum to ~1.0.

    Falls back to the engine-specific defaults if the input is missing,
    empty, non-numeric, or sums to zero. Mirrors the behaviour first
    introduced in `music_match_engine._coerce_weights` so behaviour stays
    consistent across engines.
    """
    if not weights or not isinstance(weights, dict):
        return dict(defaults)
    cleaned = {
        k: float(v)
        for k, v in weights.items()
        if isinstance(v, (int, float)) and v > 0
    }
    if not cleaned:
        return dict(defaults)
    total = sum(cleaned.values())
    if total <= 0:
        return dict(defaults)
    return {k: v / total for k, v in cleaned.items()}


def distribute_dimension_scores(
    score: int,
    weights: Dict[str, float],
) -> Dict[str, int]:
    """Spread a single 0-100 score across the dimensions in `weights`.

    The largest weight maps a perfect score to 100; smaller weights scale
    down proportionally. So if a game emphasises focus 0.6, attention 0.4,
    a perfect 100 yields focus=100, attention≈67 — the dimensions panel
    then surfaces *which* skill the game most trained, while still giving
    credit to secondary dimensions.
    """
    if not weights:
        return {}
    max_w = max(weights.values())
    if max_w <= 0:
        return {dim: 0 for dim in weights}
    return {dim: int(round(score * w / max_w)) for dim, w in weights.items()}


def band_score_by_diff(diff: float, tolerance: float) -> tuple:
    """Standard 4-band scoring for "how close to ideal" tasks.

    Used by lab_titration, pendulum, optics, stoichiometry — any game
    where the answer is a continuous number and proximity is the grade.
    """
    if tolerance <= 0:
        tolerance = 1.0
    if diff <= tolerance:
        return 100, "perfect"
    if diff <= tolerance * 3:
        return 70, "close"
    if diff <= tolerance * 6:
        return 40, "off"
    return 10, "way_off"
