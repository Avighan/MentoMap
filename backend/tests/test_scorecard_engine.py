"""Tests for engines/scorecard_engine.py — final weighted scorecard with benchmarks."""

import copy
import pytest

from engines.scorecard_engine import ScorecardEngine


_FAKE_BENCHMARKS = {
    "saas_smb": {
        "label": "SaaS — SMB",
        "gross_margin_pct": {"good": [70, 80], "great": [80, 90]},
        "ltv_to_cac": {"good": [3, 4], "great": [4, 8]},
        "monthly_churn_pct_lower_better": {"good": [2, 4], "great": [0.5, 2]},
    },
    "marketplace": {
        "label": "Marketplace",
        "take_rate_pct": {"good": [10, 20], "great": [20, 35]},
    },
}


def test_build_scorecard_returns_overall_dimensions_band():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    out = eng.build_scorecard(
        state={"gross_margin_pct": 85, "ltv_to_cac": 5},
        weights={"gross_margin_pct": 0.5, "ltv_to_cac": 0.5},
        business_model="saas_smb",
    )
    assert "overall_score" in out
    assert "overall_band" in out
    assert "dimensions" in out
    assert isinstance(out["dimensions"], list)
    assert 0 <= out["overall_score"] <= 100


def test_great_band_value_scores_above_75():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    out = eng.build_scorecard(
        state={"gross_margin_pct": 85},  # mid of great band [80, 90]
        weights={"gross_margin_pct": 1.0},
        business_model="saas_smb",
    )
    assert out["overall_score"] >= 75
    assert out["dimensions"][0]["band"] == "great"


def test_below_good_band_scores_under_50():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    out = eng.build_scorecard(
        state={"gross_margin_pct": 50},  # well below good [70, 80]
        weights={"gross_margin_pct": 1.0},
        business_model="saas_smb",
    )
    assert out["overall_score"] < 50
    assert out["dimensions"][0]["band"] == "below"


def test_lower_better_metric_inverts():
    """For _lower_better metrics, a low value should score HIGH."""
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    low_churn = eng.build_scorecard(
        state={"monthly_churn_pct": 1.0},  # mid of great band [0.5, 2]
        weights={"monthly_churn_pct": 1.0},
        business_model="saas_smb",
    )
    high_churn = eng.build_scorecard(
        state={"monthly_churn_pct": 8.0},  # well above good upper [4]
        weights={"monthly_churn_pct": 1.0},
        business_model="saas_smb",
    )
    assert low_churn["overall_score"] > high_churn["overall_score"]
    assert low_churn["dimensions"][0]["band"] == "great"
    assert high_churn["dimensions"][0]["band"] == "below"


def test_weights_normalize_when_not_summing_to_one():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    out = eng.build_scorecard(
        state={"gross_margin_pct": 85, "ltv_to_cac": 5},
        weights={"gross_margin_pct": 2.0, "ltv_to_cac": 2.0},  # sums to 4, not 1
        business_model="saas_smb",
    )
    assert 0 <= out["overall_score"] <= 100


def test_unknown_business_model_falls_back_gracefully():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    out = eng.build_scorecard(
        state={"gross_margin_pct": 85},
        weights={"gross_margin_pct": 1.0},
        business_model="not_a_real_model",
    )
    # Falls back: produces a card but flags it
    assert "warning" in out or out["overall_score"] == 0 or out["overall_band"] == "unknown"


def test_missing_kpi_is_skipped_not_zero_scored():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    out = eng.build_scorecard(
        state={"gross_margin_pct": 85},  # ltv_to_cac is missing
        weights={"gross_margin_pct": 0.5, "ltv_to_cac": 0.5},
        business_model="saas_smb",
    )
    # Score should reflect only the 1 KPI we provided
    dims_named = {d["name"] for d in out["dimensions"]}
    assert "gross_margin_pct" in dims_named
    assert "ltv_to_cac" not in dims_named
    assert out["overall_score"] >= 75  # gross_margin_pct=85 is great


def test_overall_band_thresholds():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    great_card = eng.build_scorecard(
        state={"gross_margin_pct": 88},
        weights={"gross_margin_pct": 1.0},
        business_model="saas_smb",
    )
    below_card = eng.build_scorecard(
        state={"gross_margin_pct": 30},
        weights={"gross_margin_pct": 1.0},
        business_model="saas_smb",
    )
    assert great_card["overall_band"] == "great"
    assert below_card["overall_band"] == "below"


def test_does_not_mutate_input_state():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    state = {"gross_margin_pct": 85, "ltv_to_cac": 5}
    snapshot = copy.deepcopy(state)
    eng.build_scorecard(
        state=state,
        weights={"gross_margin_pct": 0.5, "ltv_to_cac": 0.5},
        business_model="saas_smb",
    )
    assert state == snapshot


def test_dimension_contribution_sums_to_overall_score():
    eng = ScorecardEngine(benchmarks=_FAKE_BENCHMARKS)
    out = eng.build_scorecard(
        state={"gross_margin_pct": 85, "ltv_to_cac": 5},
        weights={"gross_margin_pct": 0.6, "ltv_to_cac": 0.4},
        business_model="saas_smb",
    )
    contribution_sum = sum(d["contribution"] for d in out["dimensions"])
    assert abs(contribution_sum - out["overall_score"]) < 1e-2
