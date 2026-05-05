"""Tests for LabTitrationEngine — server-side grader for `lab_titration` games."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engines.lab_titration_engine import LabTitrationEngine  # noqa: E402


_BASE_GAME = {
    "game_type": "lab_titration",
    "titration": {
        "analyte": {"name": "HCl", "concentration_M": 0.1, "volume_mL": 25},
        "titrant": {"name": "NaOH", "concentration_M": 0.1},
        "scoring": {"ideal_volume_mL": 25, "tolerance_mL": 0.5},
    },
}


def _engine(overrides=None):
    cfg = json.loads(json.dumps(_BASE_GAME))
    if overrides:
        cfg.update(overrides)
    return LabTitrationEngine(cfg)


def test_perfect_within_tolerance_yields_100():
    engine = _engine()
    result = engine.grade_result(25.0)
    assert result["score"] == 100
    assert result["band"] == "perfect"
    assert result["ideal_mL"] == 25.0
    assert result["diff_mL"] == 0.0


def test_close_band_yields_70():
    # diff = 1.0, tolerance = 0.5 → 1.0 <= 3*0.5 → close
    result = _engine().grade_result(26.0)
    assert result["score"] == 70
    assert result["band"] == "close"


def test_off_band_yields_40():
    # diff = 2.0, tolerance = 0.5 → 2.0 > 1.5, <= 3.0 → off
    result = _engine().grade_result(27.0)
    assert result["score"] == 40
    assert result["band"] == "off"


def test_way_off_band_yields_10():
    result = _engine().grade_result(40.0)
    assert result["score"] == 10
    assert result["band"] == "way_off"


def test_ideal_mL_derived_from_stoichiometry_when_not_declared():
    # Drop scoring.ideal_volume_mL → engine should compute Ca*Va/Cb = 0.1*25/0.1 = 25
    cfg = json.loads(json.dumps(_BASE_GAME))
    cfg["titration"]["scoring"] = {"tolerance_mL": 0.5}
    engine = LabTitrationEngine(cfg)
    result = engine.grade_result(25.0)
    assert result["ideal_mL"] == 25.0
    assert result["score"] == 100


def test_ideal_mL_with_different_concentrations():
    # 0.2 M HCl, 50 mL, vs 0.1 M NaOH → ideal = 0.2*50/0.1 = 100 mL
    cfg = {
        "game_type": "lab_titration",
        "titration": {
            "analyte": {"concentration_M": 0.2, "volume_mL": 50},
            "titrant": {"concentration_M": 0.1},
            "scoring": {"tolerance_mL": 0.5},
        },
    }
    engine = LabTitrationEngine(cfg)
    result = engine.grade_result(100.0)
    assert result["ideal_mL"] == 100.0
    assert result["score"] == 100


def test_negative_added_clamped_to_zero():
    result = _engine().grade_result(-5.0)
    assert result["added_mL"] == 0.0
    # diff = 25 → way_off
    assert result["band"] == "way_off"


def test_invalid_added_treated_as_zero():
    result = _engine().grade_result("not a number")
    assert result["added_mL"] == 0.0


def test_default_dimension_scores():
    # Defaults: attention_to_detail=0.5, delayed_gratification=0.5 → equal weight
    result = _engine().grade_result(25.0)
    dims = result["dimension_scores"]
    assert "attention_to_detail" in dims
    assert "delayed_gratification" in dims
    # Equal weights → both scaled to score (100)
    assert dims["attention_to_detail"] == 100
    assert dims["delayed_gratification"] == 100


def test_custom_dimension_scores():
    cfg = json.loads(json.dumps(_BASE_GAME))
    cfg["dimension_scoring_weights"] = {"focus": 0.8, "patience": 0.2}
    engine = LabTitrationEngine(cfg)
    result = engine.grade_result(25.0)
    dims = result["dimension_scores"]
    # max weight (focus 0.8) → 100; patience 0.2/0.8 * 100 = 25
    assert dims["focus"] == 100
    assert dims["patience"] == 25


def test_real_game_json_loads():
    games_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "games")
    )
    path = os.path.join(games_dir, "titration-acid-base-endpoint.json")
    if not os.path.exists(path):
        pytest.skip("titration game JSON not present")
    with open(path) as f:
        cfg = json.load(f)
    engine = LabTitrationEngine(cfg)
    perfect = engine.grade_result(25.0)
    way_off = engine.grade_result(50.0)
    assert perfect["score"] == 100
    assert way_off["score"] == 10


def test_zero_tolerance_falls_back_to_default():
    cfg = json.loads(json.dumps(_BASE_GAME))
    cfg["titration"]["scoring"]["tolerance_mL"] = 0
    engine = LabTitrationEngine(cfg)
    result = engine.grade_result(25.0)
    # Falls back to 0.5 default → 25.0 still within tolerance
    assert result["tolerance_mL"] == 0.5
    assert result["score"] == 100
