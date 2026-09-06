"""
Research dashboard blueprint.

app.py registers this blueprint right above a block of admin-only research
endpoints that already live directly in app.py (not in this file):

    POST /api/admin/research/assign-cohort   (app.py ~26069)
    GET  /api/research/status                (app.py ~26095)
    GET  /api/admin/research/export-csv      (app.py ~26129)

`grep -n -i research app.py` is how those were found — they read/write
player_profile fields research_cohort, research_pre_test_complete/scores/
date, research_post_test_complete/scores/date, research_games_target.
Those three cover cohort assignment, per-user status, and a raw CSV dump.

What's missing — and what the "Register research dashboard blueprint"
comment right above this blueprint's registration (app.py line 187)
implies — is an aggregate view: given a research cohort, how many
students are assigned, how many have completed pre/post assessment, and
what the average TEIQue-SF / dimension-score movement looks like. That's
what this blueprint adds, reusing the exact same player_profile fields
the existing export-csv route already reads.

Confidence note: this is inference, not a route confirmed by a frontend
call site — `grep -rn research frontend-react/src` turns up nothing that
calls a dashboard-shaped endpoint. This is the most defensible reading of
"research dashboard" given the existing research-cohort data model, not a
confirmed frontend contract.
"""
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify

import player_profile
from auth import require_admin


research_bp = Blueprint("research", __name__, url_prefix="/api/admin/research")

_TEIQUE_COLS = [
    "wellbeing_score", "self_control_score", "emotionality_score",
    "sociability_score", "global_ei_score",
]
_DIM_COLS = [
    "strategic_thinking", "risk_tolerance", "delayed_gratification",
    "adaptability", "resilience", "empathy", "ethical_reasoning", "creativity",
]


def _avg(values: List[float]) -> Optional[float]:
    values = [v for v in values if isinstance(v, (int, float))]
    return round(sum(values) / len(values), 2) if values else None


def _new_cohort_bucket(games_target: int) -> Dict[str, Any]:
    return {
        "assigned": 0,
        "pre_test_complete": 0,
        "post_test_complete": 0,
        "games_target": games_target,
        "pre_scores": {k: [] for k in _TEIQUE_COLS},
        "post_scores": {k: [] for k in _TEIQUE_COLS},
        "dim_scores": {k: [] for k in _DIM_COLS},
    }


@research_bp.route("/dashboard", methods=["GET"])
@require_admin
def research_dashboard():
    """Aggregate per-cohort research progress: enrollment, pre/post
    assessment completion, and average TEIQue-SF / dimension-score
    movement, for every cohort assigned via /api/admin/research/assign-cohort.
    """
    profiles = player_profile._load_profiles()
    cohorts: Dict[str, Dict[str, Any]] = {}

    for _uid, p in profiles.items():
        cohort = p.get("research_cohort")
        if not cohort:
            continue
        bucket = cohorts.setdefault(
            cohort, _new_cohort_bucket(p.get("research_games_target", 5))
        )
        bucket["assigned"] += 1
        if p.get("research_pre_test_complete"):
            bucket["pre_test_complete"] += 1
        if p.get("research_post_test_complete"):
            bucket["post_test_complete"] += 1

        pre = p.get("research_pre_test_scores") or {}
        post = p.get("research_post_test_scores") or {}
        for k in _TEIQUE_COLS:
            if isinstance(pre.get(k), (int, float)):
                bucket["pre_scores"][k].append(pre[k])
            if isinstance(post.get(k), (int, float)):
                bucket["post_scores"][k].append(post[k])

        dims = p.get("psychological_scores") or {}
        for k in _DIM_COLS:
            data = dims.get(k)
            if isinstance(data, dict) and data.get("count", 0) > 0:
                bucket["dim_scores"][k].append(data["total"] / max(1, data["count"]))

    out = []
    for cohort, bucket in cohorts.items():
        avg_pre = {k: _avg(v) for k, v in bucket["pre_scores"].items()}
        avg_post = {k: _avg(v) for k, v in bucket["post_scores"].items()}
        delta = {
            k: round(avg_post[k] - avg_pre[k], 2)
            for k in _TEIQUE_COLS
            if avg_pre.get(k) is not None and avg_post.get(k) is not None
        }
        out.append({
            "cohort": cohort,
            "assigned": bucket["assigned"],
            "pre_test_complete": bucket["pre_test_complete"],
            "post_test_complete": bucket["post_test_complete"],
            "games_target": bucket["games_target"],
            "avg_pre_teique": avg_pre,
            "avg_post_teique": avg_post,
            "teique_delta": delta,
            "avg_dimension_scores": {k: _avg(v) for k, v in bucket["dim_scores"].items()},
        })

    out.sort(key=lambda c: c["cohort"])
    return jsonify({
        "cohorts": out,
        "total_cohorts": len(out),
        "total_assigned": sum(c["assigned"] for c in out),
    })


@research_bp.route("/cohorts", methods=["GET"])
@require_admin
def research_cohorts():
    """Just the cohort names + headcount — a lighter call than /dashboard
    for populating a cohort picker."""
    profiles = player_profile._load_profiles()
    counts: Dict[str, int] = {}
    for p in profiles.values():
        cohort = p.get("research_cohort")
        if cohort:
            counts[cohort] = counts.get(cohort, 0) + 1
    cohorts = [{"cohort": c, "assigned": n} for c, n in sorted(counts.items())]
    return jsonify({"cohorts": cohorts})
