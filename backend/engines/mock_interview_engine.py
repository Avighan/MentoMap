"""
MockInterviewEngine — `mock_interview` LLM-graded transcript scorer.

The renderer captures the student's answers to interview questions. On
completion it POSTs the transcript and the engine builds a grading prompt
from the JSON `rubric` (a list of {dimension, description} entries) and
asks the LLM for per-dimension 0-100 scores. The LLM's structured output
is averaged into a final score, with dimension_scores already broken
down by rubric.

This engine *does* use the LLM unlike the others (which are pure compute).
But the same shape — engine returns dimension_scores — keeps the report
pipeline unchanged. If the LLM call fails, we fall back to a heuristic
based on average response length so the user still gets *some* score.

Default dimensions: communication + clarity_of_thought + composure.
"""
import json
from typing import Any, Dict, List, Optional

from engines._grader_common import coerce_weights, distribute_dimension_scores
from engines import scoring_registry

_DEFAULT_DIMENSION_WEIGHTS = {
    "communication": 0.4,
    "clarity_of_thought": 0.3,
    "composure": 0.3,
}


def _heuristic_score(transcript: List[Dict[str, str]]) -> int:
    """Fallback scoring when LLM is unavailable: rewards substantive answers."""
    if not transcript:
        return 0
    word_counts = []
    for t in transcript:
        ans = (t.get("answer") or "").strip()
        word_counts.append(len(ans.split()))
    if not word_counts:
        return 0
    avg = sum(word_counts) / len(word_counts)
    # 50 words ≈ "good substantive answer" → 70 points; tapers around there.
    if avg < 5:
        return 20
    if avg < 15:
        return 40
    if avg < 30:
        return 60
    if avg < 60:
        return 75
    return 85


class MockInterviewEngine:
    def __init__(self, game_config: Dict[str, Any], llm_callable: Optional[Any] = None):
        """
        Args:
            llm_callable: optional injected function with signature
                (system_prompt: str, user_prompt: str) -> str returning JSON.
                If None, engine attempts `from llm import grade_text` lazily.
        """
        self.game_config = game_config or {}
        self.rubric: List[Dict[str, str]] = list(self.game_config.get("rubric") or [])
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )
        self._llm = llm_callable

    def _grade_with_llm(self, transcript: List[Dict[str, str]]) -> Optional[Dict[str, int]]:
        if not self._llm:
            return None
        rubric_lines = "\n".join(
            f"- {r.get('dimension')}: {r.get('description', '')}" for r in self.rubric
        )
        transcript_lines = "\n\n".join(
            f"Q: {t.get('question', '')}\nA: {t.get('answer', '')}" for t in transcript
        )
        prompt = (
            "You are an interview coach. Grade the candidate on each dimension"
            " 0-100. Return ONLY JSON: {\"<dim>\": <int 0-100>, ...}.\n\n"
            f"Rubric:\n{rubric_lines}\n\nTranscript:\n{transcript_lines}"
        )
        try:
            raw = self._llm("You grade interview transcripts.", prompt)
            data = json.loads(raw)
            return {k: max(0, min(100, int(v))) for k, v in data.items() if isinstance(v, (int, float))}
        except Exception:
            return None

    def grade_results(self, transcript: List[Dict[str, str]]) -> Dict[str, Any]:
        if not transcript:
            return {
                "score": 0,
                "method": "no_transcript",
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        llm_scores = self._grade_with_llm(transcript)
        method = "llm" if llm_scores else "heuristic"

        if llm_scores:
            # Filter to declared rubric dimensions if any.
            if self.rubric:
                allowed = {r.get("dimension") for r in self.rubric}
                llm_scores = {k: v for k, v in llm_scores.items() if k in allowed}
            if llm_scores:
                avg = scoring_registry.compute(
                    "dimension_average", {"dimension_scores": llm_scores}, {},
                ).total
                # Map rubric dimensions onto the engine's weighted dimension map.
                # If rubric uses the same dimension keys as weights, surface
                # them directly. Otherwise distribute the averaged score.
                if set(llm_scores.keys()) == set(self.weights.keys()):
                    dim_scores = llm_scores
                else:
                    dim_scores = distribute_dimension_scores(avg, self.weights)
                    # Also include rubric-named scores as supplementary.
                    dim_scores.update(llm_scores)
                return {
                    "score": avg,
                    "method": method,
                    "rubric_scores": llm_scores,
                    "dimension_scores": dim_scores,
                }
            method = "heuristic"  # llm replied but with no usable dims

        score = _heuristic_score(transcript)
        return {
            "score": score,
            "method": method,
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
