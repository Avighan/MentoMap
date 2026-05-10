"""Tests for grade_reflection_text — Task 11 of P0 plan."""
import pytest

from llm import grade_reflection_text


def test_grade_reflection_returns_expected_shape(monkeypatch):
    def fake_call(system_prompt, user_prompt, **kwargs):
        return {
            "score": 72,
            "dim_signals": {"empathy": 8, "strategic_thinking": 4},
            "strengths": ["Considered the other side's perspective"],
            "improvements": ["Could quantify the trade-off"],
        }
    monkeypatch.setattr("llm._call_llm_json", fake_call)
    out = grade_reflection_text(
        "I chose this because the team felt overwhelmed and I wanted to give them space.",
        dimension_focus=["empathy", "strategic_thinking"],
    )
    assert out["score"] == 72
    assert out["dim_signals"]["empathy"] == 8
    assert out["dim_signals"]["strategic_thinking"] == 4
    assert "Considered" in out["strengths"][0]


def test_grade_reflection_falls_back_on_empty():
    out = grade_reflection_text("", dimension_focus=["empathy"])
    assert out["score"] == 0
    assert out["dim_signals"] == {}
    assert out["strengths"] == []
    assert out["improvements"] == []


def test_grade_reflection_too_short_returns_low_score():
    out = grade_reflection_text("ok.", dimension_focus=["empathy"])
    assert out["score"] == 30
    assert out["dim_signals"] == {}
    assert "Add more detail" in out["improvements"]


def test_grade_reflection_clamps_signal_range(monkeypatch):
    def fake_call(system_prompt, user_prompt, **kwargs):
        return {
            "score": 200,  # out of 0-100
            "dim_signals": {"empathy": 50, "strategic_thinking": -50},  # out of -10..+10
            "strengths": [],
            "improvements": [],
        }
    monkeypatch.setattr("llm._call_llm_json", fake_call)
    out = grade_reflection_text(
        "A reflection with enough length to pass the short-text gate.",
        dimension_focus=["empathy", "strategic_thinking"],
    )
    assert 0 <= out["score"] <= 100
    for v in out["dim_signals"].values():
        assert -10 <= v <= 10


def test_grade_reflection_filters_unknown_dimensions(monkeypatch):
    def fake_call(system_prompt, user_prompt, **kwargs):
        return {
            "score": 60,
            "dim_signals": {"empathy": 5, "made_up_dim": 9},
            "strengths": [],
            "improvements": [],
        }
    monkeypatch.setattr("llm._call_llm_json", fake_call)
    out = grade_reflection_text(
        "A reflection with enough length to pass the short-text gate.",
        dimension_focus=["empathy"],
    )
    assert out["dim_signals"] == {"empathy": 5}
