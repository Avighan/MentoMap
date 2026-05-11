"""
MentalMathEngine — `mental_math` speed-run scorer.

JSON declares an array of problems: [{id, question, answer}, ...].
The renderer presents them with a per-problem timer; on completion it
POSTs the user's answers + per-problem elapsed times. The engine grades:

  - correctness (binary per problem against authoritative answer)
  - speed bonus (faster than the per-problem time_target_s gets up to
    20% bonus, slower gets a small penalty)

Final score = clamp(0..100, accuracy * 80 + speed * 20).
Default dimensions: focus + processing_speed.
"""
from typing import Any, Dict, List

from engines._grader_common import coerce_weights, distribute_dimension_scores

_DEFAULT_DIMENSION_WEIGHTS = {
    "focus": 0.5,
    "processing_speed": 0.5,
}


class MentalMathEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.problems: List[Dict[str, Any]] = list(self.game_config.get("problems") or [])
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )
        self.time_target_s = float(self.game_config.get("time_target_s") or 5.0)

    def grade_results(self, attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.problems:
            return {
                "score": 0,
                "correct": 0,
                "total": 0,
                "accuracy_pct": 0,
                "speed_factor": 0.0,
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        # Authoritative answer lookup.
        answers: Dict[str, Any] = {}
        for p in self.problems:
            pid = p.get("id")
            if pid:
                answers[pid] = p.get("answer")

        correct = 0
        elapsed_total = 0.0
        seen = 0
        graded: List[Dict[str, Any]] = []
        for a in (attempts or []):
            pid = a.get("id") or a.get("problem_id")
            given = a.get("answer")
            try:
                elapsed = float(a.get("elapsed_s") or self.time_target_s)
            except (TypeError, ValueError):
                elapsed = self.time_target_s
            if pid not in answers:
                continue
            seen += 1
            elapsed_total += elapsed
            # Compare numerically when possible, else string-equal.
            ok = False
            try:
                ok = abs(float(given) - float(answers[pid])) < 1e-6
            except (TypeError, ValueError):
                ok = str(given).strip() == str(answers[pid]).strip()
            if ok:
                correct += 1
            graded.append({"id": pid, "given": given, "correct": ok, "elapsed_s": elapsed})

        total = len(self.problems)
        accuracy = (correct / total) if total else 0
        avg_elapsed = (elapsed_total / seen) if seen else self.time_target_s

        # Speed factor: 1.0 at exactly the target, up to 1.25 if 2× faster,
        # down to 0.75 if 2× slower. Bounded.
        if avg_elapsed > 0:
            ratio = self.time_target_s / avg_elapsed
        else:
            ratio = 1.0
        speed_factor = max(0.75, min(1.25, ratio))

        raw = (accuracy * 0.8 + (speed_factor - 0.75) / 0.5 * 0.2) * 100
        score = max(0, min(100, int(round(raw))))

        return {
            "score": score,
            "correct": correct,
            "total": total,
            "accuracy_pct": int(round(accuracy * 100)),
            "avg_elapsed_s": round(avg_elapsed, 2),
            "speed_factor": round(speed_factor, 2),
            "graded": graded,
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
