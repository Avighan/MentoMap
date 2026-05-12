"""Tests for the customer-interview simulator service.

Failing at collection time (red) until services/interview_sim.py exists.
"""
from services.interview_sim import (
    start_conversation,
    end_conversation,
    ConvState,
)


def test_start_returns_conv_id_and_persona():
    s = start_conversation(user_id="u1", module_id="m1", persona_id="kirana_uncle")
    assert isinstance(s, ConvState)
    assert s.conv_id
    assert s.persona["persona_id"] == "kirana_uncle"
    assert s.turns == []


def test_end_returns_transcript_and_depth_score():
    s = start_conversation(user_id="u1", module_id="m1", persona_id="kirana_uncle")
    s.turns = [
        {"role": "user", "text": "Why do you order so much milk?"},
        {"role": "persona", "text": "Because customers want fresh milk daily."},
        {"role": "user", "text": "Why is freshness so important?"},
        {"role": "persona", "text": "Because they complain if it's even one day old."},
    ]
    summary = end_conversation(s)
    assert "transcript" in summary
    assert "depth_score" in summary
    assert 0 <= summary["depth_score"] <= 5


def test_depth_score_counts_why_questions():
    s = start_conversation(user_id="u1", module_id="m1", persona_id="kirana_uncle")
    s.turns = [
        {"role": "user", "text": "Tell me about your day."},
        {"role": "persona", "text": "..."},
    ]
    summary = end_conversation(s)
    # No 'why' questions → depth_score = 0
    assert summary["depth_score"] == 0
