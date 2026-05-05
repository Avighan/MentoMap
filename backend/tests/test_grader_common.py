"""Tests for the shared scoring helpers used by all grader engines."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines._grader_common import (  # noqa: E402
    band_score_by_diff,
    coerce_weights,
    distribute_dimension_scores,
)


def test_coerce_weights_uses_defaults_when_missing():
    defaults = {"a": 0.5, "b": 0.5}
    assert coerce_weights(None, defaults) == defaults
    assert coerce_weights({}, defaults) == defaults
    assert coerce_weights("not a dict", defaults) == defaults


def test_coerce_weights_normalizes_to_one():
    out = coerce_weights({"a": 2, "b": 6}, {"x": 1.0})
    total = sum(out.values())
    assert abs(total - 1.0) < 1e-9
    assert out["a"] < out["b"]


def test_coerce_weights_filters_non_positive():
    defaults = {"x": 1.0}
    # All non-positive → falls back to defaults
    assert coerce_weights({"a": 0, "b": -1}, defaults) == defaults
    # Mixed → keeps positives
    out = coerce_weights({"a": 0, "b": 1}, defaults)
    assert out == {"b": 1.0}


def test_distribute_dimension_scores_max_weight_gets_full_score():
    weights = {"focus": 0.6, "patience": 0.4}
    dims = distribute_dimension_scores(100, weights)
    assert dims["focus"] == 100  # max weight → 100
    assert dims["patience"] == round(100 * 0.4 / 0.6)


def test_distribute_dimension_scores_zero_weights_safe():
    assert distribute_dimension_scores(50, {}) == {}


def test_band_score_by_diff_perfect_close_off_way_off():
    assert band_score_by_diff(0, 1) == (100, "perfect")
    assert band_score_by_diff(2, 1) == (70, "close")
    assert band_score_by_diff(5, 1) == (40, "off")
    assert band_score_by_diff(20, 1) == (10, "way_off")


def test_band_score_zero_tolerance_falls_back():
    # Should treat tolerance<=0 as 1.0 to avoid div-by-zero
    score, band = band_score_by_diff(0.5, 0)
    assert score == 100
    assert band == "perfect"
