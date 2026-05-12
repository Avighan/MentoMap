"""Failing tests for the Pitch Coach scoring service (TDD red phase).

The service in services/pitch_coach.py does not exist yet — these tests fail at
collection time with ModuleNotFoundError.
"""
from services.pitch_coach import score_transcript, PitchScore  # noqa: F401


def test_score_transcript_returns_5_axes():
    transcript = (
        "Hi, I'm Aarav. I noticed pencils roll off desks. "
        "I made a pencil holder. My friends need this. "
        "Can you test it next week?"
    )
    score = score_transcript(transcript)
    assert isinstance(score, PitchScore)
    for axis in ("hook", "problem", "solution", "customer", "ask"):
        assert axis in score.scores
        assert 0 <= score.scores[axis] <= 10


def test_score_transcript_populates_strengths_and_improvements():
    score = score_transcript("Test pitch.")
    for axis in score.scores:
        assert axis in score.strengths
        assert axis in score.improvements


def test_short_transcript_does_not_crash():
    score = score_transcript("um")
    assert isinstance(score, PitchScore)
