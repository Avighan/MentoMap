"""Pitch Coach scoring service for Mento Entrepreneur Workshop.

Provides LLM-backed rubric scoring across 5 axes (hook / problem / solution /
customer / ask), Whisper STT transcription, and TTS voice-reply generation.

All functions degrade gracefully: no LLM key → deterministic fallback scores;
no TTS → RuntimeError with a clear message.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Optional dependencies – wrapped so module import never fails
# ---------------------------------------------------------------------------

try:
    from llm import llm_call  # type: ignore
except ImportError:
    llm_call = None  # type: ignore

try:
    from services.tts_service import synthesize  # type: ignore
except ImportError:
    synthesize = None  # type: ignore

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

AXES = ("hook", "problem", "solution", "customer", "ask")

_RUBRIC_SYSTEM_PROMPT = """\
You are Mento, a kind but rigorous coach for a 10-14yo Indian student practicing a 60-second startup pitch.
Score the pitch on 5 axes, each 0-10:
- hook: does the opening grab attention?
- problem: is the problem real, specific, and felt?
- solution: is the solution clear and concrete?
- customer: is "who this is for" specific?
- ask: is the call-to-action precise (not vague "we need help")?

For EACH axis output one strength (1 short sentence) and one improvement (1 specific sentence with a concrete rewrite example).

Return ONLY this JSON shape:
{
  "scores": {"hook": 0, "problem": 0, "solution": 0, "customer": 0, "ask": 0},
  "strengths": {"hook": "...", "problem": "...", "solution": "...", "customer": "...", "ask": "..."},
  "improvements": {"hook": "...", "problem": "...", "solution": "...", "customer": "...", "ask": "..."},
  "summary": "<2-3 sentence overall verdict, warm tone, age-appropriate>"
}"""

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class PitchScore:
    """Structured result from scoring a pitch transcript."""

    scores: Dict[str, int] = field(default_factory=dict)
    strengths: Dict[str, str] = field(default_factory=dict)
    improvements: Dict[str, str] = field(default_factory=dict)
    summary: str = ""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _fallback_score() -> PitchScore:
    """Return a neutral PitchScore used when LLM is unavailable or returns {}."""
    return PitchScore(
        scores={a: 5 for a in AXES},
        strengths={a: "" for a in AXES},
        improvements={a: "" for a in AXES},
        summary="(LLM not configured)",
    )


def _clamp(value: int, lo: int = 0, hi: int = 10) -> int:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_transcript(transcript: str) -> PitchScore:
    """Score a pitch transcript against the 5-axis Mento rubric.

    Falls back to neutral scores (5 on every axis) when no LLM is available
    or when the LLM returns an empty / malformed response.
    """
    if llm_call is None:
        return _fallback_score()

    data: Dict = llm_call(
        system_prompt=_RUBRIC_SYSTEM_PROMPT,
        user_prompt=f"Pitch transcript:\n{transcript}",
        response_json=True,
        temperature=0.3,
        max_tokens=900,
        purpose="pitch_coach_rubric",
        fallback={},
    )

    if not data:
        return _fallback_score()

    raw_scores = data.get("scores", {}) if isinstance(data.get("scores"), dict) else {}
    raw_strengths = data.get("strengths", {}) if isinstance(data.get("strengths"), dict) else {}
    raw_improvements = data.get("improvements", {}) if isinstance(data.get("improvements"), dict) else {}
    summary = str(data.get("summary", ""))

    scores: Dict[str, int] = {}
    strengths: Dict[str, str] = {}
    improvements: Dict[str, str] = {}

    for axis in AXES:
        try:
            scores[axis] = _clamp(int(raw_scores.get(axis, 5)))
        except (TypeError, ValueError):
            scores[axis] = 5

        strengths[axis] = str(raw_strengths.get(axis, ""))
        improvements[axis] = str(raw_improvements.get(axis, ""))

    return PitchScore(
        scores=scores,
        strengths=strengths,
        improvements=improvements,
        summary=summary,
    )


def transcribe(audio_bytes: bytes, filename: str = "pitch.webm") -> str:
    """Transcribe audio bytes to text using OpenAI Whisper.

    Lazy-imports ``openai`` so the module can be imported without the package
    installed.  Raises ``RuntimeError`` if OpenAI is unavailable.
    """
    try:
        import openai  # type: ignore  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("openai package not installed; cannot transcribe audio") from exc

    import io  # noqa: PLC0415

    client = openai.OpenAI()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename  # Whisper API needs a filename for format detection
    response = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return response.text


def voice_reply_for(score: PitchScore) -> bytes:
    """Generate a short spoken coaching reply for the given PitchScore.

    Uses the worst-scoring axis to pick the most relevant improvement tip,
    then synthesises speech via the TTS service.

    Raises:
        RuntimeError: if the TTS service is unavailable.
    """
    if synthesize is None:
        raise RuntimeError("TTS service unavailable")

    # Determine worst axis (lowest score; tie-break by AXES order)
    worst_axis: str = min(AXES, key=lambda a: score.scores.get(a, 5))

    improvement_tip = score.improvements.get(worst_axis, "")
    narration = f"{score.summary} {improvement_tip}".strip()
    narration = narration[:600]  # keep TTS request short

    audio_bytes: Optional[bytes] = synthesize(narration, provider="openai", lang="en")
    return audio_bytes  # type: ignore[return-value]
