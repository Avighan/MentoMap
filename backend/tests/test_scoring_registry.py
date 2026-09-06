"""Tests for engines/scoring_registry.py — the config-driven scoring-formula
registry that every grader engine now routes its final scoring step through.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402

from engines import scoring_registry  # noqa: E402


def test_available_lists_all_builtin_formulas():
    names = scoring_registry.available()
    for expected in [
        "proximity_band",
        "fraction_correct",
        "penalized_fraction",
        "mae_accuracy",
        "speed_accuracy_factor",
        "speed_accuracy_capped",
        "points_ceiling_ratio",
        "dimension_average",
        "benchmark_scorecard",
        "weighted_kpi_normalize",
        "expert_drift",
    ]:
        assert expected in names


def test_get_unknown_formula_raises_with_helpful_message():
    with pytest.raises(KeyError, match="Unknown scoring formula"):
        scoring_registry.get("does_not_exist")


def test_register_adds_a_new_formula():
    class _Dummy:
        def compute(self, state, config):
            return scoring_registry.ScoringResult(total=1, band="x", label="x")

    scoring_registry.register("dummy_for_test", _Dummy())
    assert "dummy_for_test" in scoring_registry.available()
    assert scoring_registry.compute("dummy_for_test", {}, {}).total == 1


# ---- proximity_band ----

def test_proximity_band_perfect():
    result = scoring_registry.compute(
        "proximity_band", {"diff": 0, "tolerance": 1}, {"weights": {"focus": 1.0}},
    )
    assert result.total == 100
    assert result.band == "perfect"
    assert result.dimensions == {"focus": 100}


def test_proximity_band_way_off():
    result = scoring_registry.compute(
        "proximity_band", {"diff": 50, "tolerance": 1}, {"weights": {}},
    )
    assert result.total == 10
    assert result.band == "way_off"


# ---- fraction_correct ----

def test_fraction_correct_partial():
    result = scoring_registry.compute(
        "fraction_correct", {"correct": 3, "total": 4}, {"weights": {"a": 1.0}},
    )
    assert result.total == 75
    assert result.dimensions == {"a": 75}


def test_fraction_correct_zero_total_is_zero():
    result = scoring_registry.compute("fraction_correct", {"correct": 0, "total": 0}, {})
    assert result.total == 0


# ---- penalized_fraction ----

def test_penalized_fraction_invalid_multiplier_and_penalty():
    result = scoring_registry.compute(
        "penalized_fraction",
        {"correct": 81, "total": 81, "valid": False, "penalty_points": 15},
        {"invalid_multiplier": 0.8, "weights": {}},
    )
    # base=1.0 -> *0.8 = 0.8 -> 80 -> -15 = 65
    assert result.total == 65


def test_penalized_fraction_clamped_to_zero():
    result = scoring_registry.compute(
        "penalized_fraction",
        {"correct": 5, "total": 81, "valid": True, "penalty_points": 100},
        {"weights": {}},
    )
    assert result.total == 0


# ---- mae_accuracy ----

def test_mae_accuracy_perfect_prediction():
    result = scoring_registry.compute(
        "mae_accuracy",
        {"predicted": {"dominant": 75, "recessive": 25}, "expected": {"dominant": 75, "recessive": 25}},
        {"weights": {}},
    )
    assert result.total == 100
    assert result.raw["mean_abs_error_pct"] == 0


def test_mae_accuracy_missing_prediction_counts_as_zero():
    result = scoring_registry.compute(
        "mae_accuracy",
        {"predicted": {}, "expected": {"dominant": 100}},
        {"weights": {}},
    )
    assert result.total == 0


def test_mae_accuracy_no_expected_is_no_data():
    result = scoring_registry.compute("mae_accuracy", {"predicted": {}, "expected": {}}, {})
    assert result.total == 0
    assert result.band == "no_data"


# ---- speed_accuracy_factor ----

def test_speed_accuracy_factor_matches_mental_math_formula():
    # accuracy=1.0, speed_factor=1.0 -> (1-0.75)/0.5=0.5 -> 0.5*0.2=0.1 -> +0.8 = 0.9 -> 90
    result = scoring_registry.compute(
        "speed_accuracy_factor", {"accuracy": 1.0, "speed_factor": 1.0}, {"weights": {}},
    )
    assert result.total == 90


def test_speed_accuracy_factor_max_speed_bonus():
    result = scoring_registry.compute(
        "speed_accuracy_factor", {"accuracy": 1.0, "speed_factor": 1.25}, {"weights": {}},
    )
    assert result.total == 100


# ---- speed_accuracy_capped ----

def test_speed_accuracy_capped_caps_at_target():
    # Even 2x faster than target should not exceed the speed_weight contribution
    fast = scoring_registry.compute(
        "speed_accuracy_capped", {"accuracy": 1.0, "actual": 60, "target": 30}, {"weights": {}},
    )
    at_target = scoring_registry.compute(
        "speed_accuracy_capped", {"accuracy": 1.0, "actual": 30, "target": 30}, {"weights": {}},
    )
    assert fast.total == at_target.total == 100


def test_speed_accuracy_capped_zero_target_is_zero_speed():
    result = scoring_registry.compute(
        "speed_accuracy_capped", {"accuracy": 1.0, "actual": 10, "target": 0}, {"weights": {}},
    )
    assert result.total == 70  # accuracy_weight default 70, no speed contribution


# ---- points_ceiling_ratio ----

def test_points_ceiling_ratio_full_credit():
    result = scoring_registry.compute(
        "points_ceiling_ratio", {"raw_points": 5, "ceiling": 5}, {"weights": {}},
    )
    assert result.total == 100


def test_points_ceiling_ratio_zero_ceiling_safe():
    result = scoring_registry.compute(
        "points_ceiling_ratio", {"raw_points": 0, "ceiling": 0}, {"weights": {}},
    )
    assert result.total == 0


# ---- dimension_average ----

def test_dimension_average_simple_mean():
    result = scoring_registry.compute(
        "dimension_average",
        {"dimension_scores": {"communication": 80, "clarity_of_thought": 60}},
        {},
    )
    assert result.total == 70
    assert result.dimensions == {"communication": 80, "clarity_of_thought": 60}


def test_dimension_average_empty_is_no_data():
    result = scoring_registry.compute("dimension_average", {"dimension_scores": {}}, {})
    assert result.total == 0
    assert result.band == "no_data"


# ---- benchmark_scorecard ----

_FAKE_BENCHMARKS = {
    "saas_smb": {
        "label": "SaaS — SMB",
        "gross_margin_pct": {"good": [70, 80], "great": [80, 90]},
    },
}


def test_benchmark_scorecard_wraps_scorecard_engine():
    result = scoring_registry.compute(
        "benchmark_scorecard",
        {"state": {"gross_margin_pct": 85}},
        {"weights": {"gross_margin_pct": 1.0}, "business_model": "saas_smb",
         "benchmarks": _FAKE_BENCHMARKS},
    )
    assert result.total >= 75
    assert result.band == "great"
    assert "gross_margin_pct" in result.dimensions


# ---- weighted_kpi_normalize (new formula) ----

_KPI_CONFIG = {
    "categories": [
        {
            "name": "financial",
            "kpis": [
                {"name": "revenue", "min": 0, "max": 100, "weight": 0.5},
                {"name": "margin_pct", "min": 0, "max": 100, "weight": 0.5},
            ],
        },
    ],
    "grade_table": [
        {"min": 90, "grade": "A", "label": "Outstanding"},
        {"min": 75, "grade": "B", "label": "Solid"},
        {"min": 0, "grade": "F", "label": "Needs Improvement"},
    ],
}


def test_weighted_kpi_normalize_full_marks():
    result = scoring_registry.compute(
        "weighted_kpi_normalize", {"kpis": {"revenue": 100, "margin_pct": 100}}, _KPI_CONFIG,
    )
    assert result.total == 100
    assert result.band == "A"
    assert result.label == "Outstanding"
    assert result.dimensions["financial"] == 100


def test_weighted_kpi_normalize_clamps_out_of_range_values():
    result = scoring_registry.compute(
        "weighted_kpi_normalize", {"kpis": {"revenue": 500, "margin_pct": -50}}, _KPI_CONFIG,
    )
    # revenue clamps to 100 (contributes 50), margin_pct clamps to 0 (contributes 0)
    assert result.total == 50


def test_weighted_kpi_normalize_missing_kpi_skipped():
    result = scoring_registry.compute(
        "weighted_kpi_normalize", {"kpis": {"revenue": 100}}, _KPI_CONFIG,
    )
    assert result.total == 50  # only revenue's 50-point contribution


def test_weighted_kpi_normalize_grade_table_lookup_picks_highest_matching_min():
    mid = scoring_registry.compute(
        "weighted_kpi_normalize", {"kpis": {"revenue": 80, "margin_pct": 80}}, _KPI_CONFIG,
    )
    assert mid.total == 80
    assert mid.band == "B"


# ---- expert_drift (new formula) ----

_DRIFT_ROUNDS_STATE = {
    "rounds": [
        {
            "controls": [
                {"id": "price", "type": "slider", "expert_pick": 200},
                {"id": "rd_pct", "type": "slider", "expert_pick": 0.15},
            ],
            "submission": {"price": 200, "rd_pct": 0.15},
        },
        {
            "controls": [
                {"id": "price", "type": "slider", "expert_pick": 200},
            ],
            "submission": {"price": 220},
        },
    ],
}


def test_expert_drift_perfect_run_scores_100():
    result = scoring_registry.compute(
        "expert_drift",
        {"rounds": [_DRIFT_ROUNDS_STATE["rounds"][0]]},
        {},
    )
    assert result.total == 100
    assert result.dimensions == {"price": 100, "rd_pct": 100}


def test_expert_drift_aggregates_across_rounds():
    result = scoring_registry.compute("expert_drift", _DRIFT_ROUNDS_STATE, {})
    # price: round1 drift=0, round2 drift=|220-200|/200=0.10 -> avg=0.05 -> dim=95
    assert result.dimensions["price"] == 95
    assert result.dimensions["rd_pct"] == 100
    assert 0 < result.total < 100


def test_expert_drift_no_rounds_is_no_data():
    result = scoring_registry.compute("expert_drift", {"rounds": []}, {})
    assert result.total == 0
    assert result.band == "no_data"


def test_expert_drift_uses_grade_table_when_provided():
    result = scoring_registry.compute(
        "expert_drift",
        {"rounds": [_DRIFT_ROUNDS_STATE["rounds"][0]]},
        {"grade_table": [{"min": 90, "grade": "A", "label": "Outstanding"},
                          {"min": 0, "grade": "F", "label": "Needs Improvement"}]},
    )
    assert result.band == "A"
    assert result.label == "Outstanding"


def test_expert_drift_categorical_control_binary_drift():
    result = scoring_registry.compute(
        "expert_drift",
        {"rounds": [{
            "controls": [{"id": "hire_plan", "type": "dropdown", "expert_pick": "slow"}],
            "submission": {"hire_plan": "aggressive"},
        }]},
        {},
    )
    assert result.dimensions["hire_plan"] == 0
    assert result.total == 0


def test_expert_drift_weights_favor_high_weight_controls():
    equal = scoring_registry.compute("expert_drift", _DRIFT_ROUNDS_STATE, {})
    weighted = scoring_registry.compute(
        "expert_drift", _DRIFT_ROUNDS_STATE, {"weights": {"price": 5.0, "rd_pct": 1.0}},
    )
    # price drifts more than rd_pct across the run, so upweighting price
    # should pull the aggregate score down relative to equal weighting.
    assert weighted.total < equal.total
