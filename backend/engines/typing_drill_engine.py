"""
TypingDrillEngine — `typing_drill` accuracy + speed scorer.

JSON declares one or more passages: [{id, text}, ...]. The renderer captures
keystrokes; on submit it POSTs {passage_id, typed_text, elapsed_s} per
passage. The engine computes:

  - WPM = (chars_typed / 5) / minutes
  - accuracy = 1 - (Levenshtein-ish character mismatches / target_len)

Score blends both: 70% accuracy + 30% speed (capped at a per-grade target
WPM). Default dimensions: focus + processing_speed.
"""
from typing import Any, Dict, List

from engines._grader_common import coerce_weights, distribute_dimension_scores

_DEFAULT_DIMENSION_WEIGHTS = {
    "focus": 0.6,
    "processing_speed": 0.4,
}


def _accuracy(typed: str, target: str) -> float:
    """Cheap char-by-char accuracy (not full edit distance — fine for drills)."""
    if not target:
        return 1.0 if not typed else 0.0
    matches = sum(1 for i, ch in enumerate(target) if i < len(typed) and typed[i] == ch)
    return matches / len(target)


class TypingDrillEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.passages: List[Dict[str, Any]] = list(self.game_config.get("passages") or [])
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )
        self.target_wpm = float(self.game_config.get("target_wpm") or 30.0)

    def grade_results(self, attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.passages:
            return {"score": 0, "wpm": 0, "accuracy_pct": 0,
                    "dimension_scores": {dim: 0 for dim in self.weights}}

        targets: Dict[str, str] = {p.get("id"): p.get("text") or "" for p in self.passages if p.get("id")}

        total_chars = 0
        total_seconds = 0.0
        accuracies: List[float] = []
        per_passage: List[Dict[str, Any]] = []
        for a in (attempts or []):
            pid = a.get("passage_id") or a.get("id")
            if pid not in targets:
                continue
            target = targets[pid]
            typed = str(a.get("typed_text") or "")
            try:
                elapsed = float(a.get("elapsed_s") or 0)
            except (TypeError, ValueError):
                elapsed = 0
            acc = _accuracy(typed, target)
            accuracies.append(acc)
            total_chars += len(typed)
            total_seconds += max(elapsed, 0)
            per_passage.append({
                "passage_id": pid,
                "accuracy_pct": int(round(acc * 100)),
                "elapsed_s": round(elapsed, 2),
            })

        avg_acc = sum(accuracies) / len(accuracies) if accuracies else 0.0
        wpm = ((total_chars / 5) / (total_seconds / 60)) if total_seconds > 0 else 0
        speed_ratio = min(1.0, wpm / self.target_wpm) if self.target_wpm > 0 else 0

        score = int(round((avg_acc * 70) + (speed_ratio * 30)))
        score = max(0, min(100, score))

        return {
            "score": score,
            "wpm": round(wpm, 1),
            "target_wpm": self.target_wpm,
            "accuracy_pct": int(round(avg_acc * 100)),
            "passages_attempted": len(per_passage),
            "per_passage": per_passage,
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
