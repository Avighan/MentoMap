"""
MusicMatchEngine — score computation for the `music_match` game type
(ear-training pitch matching).

The renderer (frontend `MusicGameRenderer`) plays the game purely client-side
using Web Audio. On completion the renderer POSTs the per-round results to
`/api/run/<id>/music-match/complete`, which calls this engine to:

  - re-validate correctness against the JSON answer_id (never trust the client)
  - compute a 0-100 final score from accuracy
  - distribute that score across dimension weights from the game JSON

The output dict matches the shape `puzzle_match_engine.get_game_summary` produces,
so the existing report pipeline (`/api/run/<id>/report` + `mento_score.py`)
picks it up via `state.dimension_scores` and the run log entry without any
special-casing for music_match.

Default dimension weights — used if the game JSON does not declare
`dimension_scoring_weights` — emphasise focus and attention to detail, the
two skills most directly trained by ear-discrimination tasks.
"""
from typing import Any, Dict, List, Optional


_DEFAULT_DIMENSION_WEIGHTS = {
    "focus": 0.6,
    "attention_to_detail": 0.4,
}


def _coerce_weights(weights: Optional[Dict[str, float]]) -> Dict[str, float]:
    """Normalize a weights dict so values sum to ~1.0; fall back to defaults."""
    if not weights or not isinstance(weights, dict):
        return dict(_DEFAULT_DIMENSION_WEIGHTS)
    cleaned = {k: float(v) for k, v in weights.items() if isinstance(v, (int, float)) and v > 0}
    if not cleaned:
        return dict(_DEFAULT_DIMENSION_WEIGHTS)
    total = sum(cleaned.values())
    if total <= 0:
        return dict(_DEFAULT_DIMENSION_WEIGHTS)
    return {k: v / total for k, v in cleaned.items()}


class MusicMatchEngine:
    """Stateless scorer — no per-run state, no I/O."""

    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.music_rounds: List[Dict[str, Any]] = list(self.game_config.get("music_rounds") or [])
        self.weights = _coerce_weights(self.game_config.get("dimension_scoring_weights"))

    def grade_results(self, picks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Re-validate the player's picks against the game JSON.

        Args:
            picks: list of {round_id, picked_id} dicts from the client.

        Returns:
            {
                "score":          int 0-100,
                "correct":        int,
                "total":          int,
                "rounds":         [{round_id, picked_id, correct}, ...],
                "dimension_scores": {dim: int 0-100, ...},
            }
        """
        if not self.music_rounds:
            return {"score": 0, "correct": 0, "total": 0, "rounds": [], "dimension_scores": {}}

        # Build a quick lookup of round_id -> answer_id from the authoritative JSON.
        answers: Dict[str, str] = {}
        for r in self.music_rounds:
            rid = r.get("id")
            ans = r.get("answer_id")
            if rid and ans:
                answers[rid] = ans

        graded_rounds: List[Dict[str, Any]] = []
        correct = 0
        for p in (picks or []):
            rid = p.get("round_id") or p.get("id")
            picked_id = p.get("picked_id") or p.get("picked") or p.get("choice_id")
            is_correct = bool(rid and picked_id and answers.get(rid) == picked_id)
            if is_correct:
                correct += 1
            graded_rounds.append({"round_id": rid, "picked_id": picked_id, "correct": is_correct})

        total = len(self.music_rounds)
        # Score is accuracy on declared rounds, capped to total even if client sent extras.
        score = int(round((min(correct, total) / total) * 100)) if total > 0 else 0

        # Distribute score across dimensions per weights — each dim gets the same
        # 0-100 magnitude scaled by its weight so that the dimensions panel reads
        # the relative emphasis the JSON declared.
        dimension_scores: Dict[str, int] = {}
        for dim, weight in self.weights.items():
            # Weight 0.6 + score 100 → 100 * 0.6 / max_weight (renormalize)
            dimension_scores[dim] = int(round(score * weight / max(self.weights.values())))

        return {
            "score": score,
            "correct": correct,
            "total": total,
            "rounds": graded_rounds,
            "dimension_scores": dimension_scores,
        }
