"""Tests for project_management_engine.compute_earned_value — EV/PV/AC + indices."""

import copy
import pytest

from engines.project_management_engine import compute_earned_value, build_pm_payload


class _State:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


_PM_GAME = {
    "simulation_config": {
        "project_management": {
            "methodology": "agile",
            "sprint_length_days": 14,
            "target_end_day": 30,
            "tasks": [
                {"id": "design", "name": "Design", "duration_days": 10,
                 "dependencies": [], "owner": "tl",
                 "status": "done", "progress_pct": 100,
                 "budget_cost": 100_000, "actual_cost": 95_000},
                {"id": "build", "name": "Build", "duration_days": 15,
                 "dependencies": ["design"], "owner": "eng",
                 "status": "in_progress", "progress_pct": 50,
                 "budget_cost": 200_000, "actual_cost": 130_000},
                {"id": "test", "name": "Test", "duration_days": 5,
                 "dependencies": ["build"], "owner": "qa",
                 "status": "not_started", "progress_pct": 0,
                 "budget_cost": 50_000, "actual_cost": 0},
            ],
            "resources": [],
            "raid": {"risks": [], "assumptions": [], "issues": [], "dependencies": []},
        }
    }
}


def test_compute_earned_value_returns_pv_ev_ac_keys():
    state = _State(_pm_runtime={"current_day": 15, "task_overrides": {}, "raid_overrides": {}})
    ev = compute_earned_value(state, _PM_GAME)
    assert ev is not None
    for k in ("planned_value", "earned_value", "actual_cost",
              "cost_variance", "schedule_variance", "cpi", "spi"):
        assert k in ev


def test_no_pm_config_returns_none():
    state = _State()
    assert compute_earned_value(state, {"game_type": "rounds"}) is None


def test_earned_value_is_budget_times_progress():
    """EV = sum(budget × progress%) across tasks."""
    state = _State(_pm_runtime={"current_day": 15, "task_overrides": {}, "raid_overrides": {}})
    ev = compute_earned_value(state, _PM_GAME)
    # design: 100k * 1.0 = 100k; build: 200k * 0.5 = 100k; test: 50k * 0 = 0 → 200k
    assert abs(ev["earned_value"] - 200_000) < 1e-6


def test_actual_cost_sums_actuals():
    state = _State(_pm_runtime={"current_day": 15, "task_overrides": {}, "raid_overrides": {}})
    ev = compute_earned_value(state, _PM_GAME)
    # design 95k + build 130k + test 0 = 225k
    assert abs(ev["actual_cost"] - 225_000) < 1e-6


def test_cpi_under_one_means_over_budget():
    """CPI = EV/AC. EV=200k, AC=225k → CPI < 1.0."""
    state = _State(_pm_runtime={"current_day": 15, "task_overrides": {}, "raid_overrides": {}})
    ev = compute_earned_value(state, _PM_GAME)
    assert ev["cpi"] < 1.0
    assert ev["cost_variance"] < 0  # CV = EV - AC = -25k


def test_planned_value_scales_with_current_day():
    """PV ≈ total_budget × (current_day / target_end_day)."""
    state_early = _State(_pm_runtime={"current_day": 0, "task_overrides": {}, "raid_overrides": {}})
    state_mid = _State(_pm_runtime={"current_day": 15, "task_overrides": {}, "raid_overrides": {}})
    ev_early = compute_earned_value(state_early, _PM_GAME)
    ev_mid = compute_earned_value(state_mid, _PM_GAME)
    assert ev_early["planned_value"] < ev_mid["planned_value"]


def test_zero_actual_cost_does_not_crash_cpi():
    """Edge case: AC=0 must not raise division-by-zero."""
    game_no_actuals = copy.deepcopy(_PM_GAME)
    for t in game_no_actuals["simulation_config"]["project_management"]["tasks"]:
        t["actual_cost"] = 0
    state = _State(_pm_runtime={"current_day": 5, "task_overrides": {}, "raid_overrides": {}})
    ev = compute_earned_value(state, game_no_actuals)
    assert ev is not None
    assert "cpi" in ev


def test_pm_payload_includes_earned_value():
    """build_pm_payload should expose EV alongside critical_path / burndown."""
    state = _State(_pm_runtime={"current_day": 15, "task_overrides": {}, "raid_overrides": {}})
    payload = build_pm_payload(state, _PM_GAME)
    assert "earned_value" in payload
    assert payload["earned_value"]["earned_value"] > 0
