"""Mento Score: the cross-game 0-100 performance score shown at game-over.

Call sites (see app.py) pass a `state` object that is sometimes a plain
dict and sometimes a typed GameState (engine.py) — `_get()` below reads
either. The seven-category breakdown (`resource_optimization`,
`decision_quality`, `speed_efficiency`, `achievement_progress`,
`learning_engagement`, `competitive_performance`, `risk_management`) and
their dict keys are load-bearing: app.py's report-building code
(`_category_labels` in the mento-score-breakdown block) indexes
`breakdown`/`weights` by exactly these keys, so the schema here is derived
from that usage rather than invented independently.
"""
import math
from typing import Any, Dict, List, Optional

CATEGORY_WEIGHTS: Dict[str, float] = {
    "resource_optimization": 0.20,
    "decision_quality": 0.25,
    "speed_efficiency": 0.10,
    "achievement_progress": 0.15,
    "learning_engagement": 0.10,
    "competitive_performance": 0.10,
    "risk_management": 0.10,
}

RANKS = [
    (90, "A (Excellent)"),
    (75, "B (Strong)"),
    (60, "C (Average)"),
    (40, "D (Needs Improvement)"),
    (0, "F (Struggling)"),
]


def _get(state: Any, key: str, default=None):
    if state is None:
        return default
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _score_resource_optimization(state: Any, game_config: dict) -> float:
    initial = (game_config or {}).get("initial_state", {}) or {}
    resources = _get(state, "resources", None)
    if isinstance(resources, dict) and isinstance(initial.get("resources"), dict):
        gains = 0
        total = 0
        for key, start_val in initial["resources"].items():
            if not isinstance(start_val, (int, float)):
                continue
            end_val = resources.get(key, start_val)
            total += 1
            if isinstance(end_val, (int, float)) and start_val != 0:
                gains += max(-1.0, min(1.0, (end_val - start_val) / abs(start_val)))
        if total:
            return _clamp(50 + (gains / total) * 50)

    cash = _get(state, "cash", None)
    start_cash = initial.get("cash")
    if isinstance(cash, (int, float)) and isinstance(start_cash, (int, float)) and start_cash:
        return _clamp(50 + ((cash - start_cash) / abs(start_cash)) * 50)

    return 50.0


def _score_decision_quality(run_log: List[dict]) -> float:
    if not run_log:
        return 50.0
    positive, total = 0, 0
    for entry in run_log:
        if not isinstance(entry, dict):
            continue
        outcome = entry.get("outcome") or entry.get("result")
        net_change = entry.get("net_change")
        total += 1
        if isinstance(net_change, (int, float)):
            if net_change > 0:
                positive += 1
        elif outcome in ("good", "success", "positive", "correct"):
            positive += 1
        elif outcome in ("bad", "failure", "negative", "incorrect"):
            pass
        else:
            positive += 0.5  # neutral/unknown outcome
    if total == 0:
        return 50.0
    return _clamp((positive / total) * 100)


def _score_speed_efficiency(state: Any, game_config: dict, run_log: List[dict]) -> float:
    total_rounds = len((game_config or {}).get("rounds", []) or [])
    round_index = _get(state, "round_index", None)
    if total_rounds and isinstance(round_index, (int, float)):
        completion = round_index / total_rounds
        return _clamp(completion * 100)
    if run_log:
        return _clamp(100 - min(len(run_log), 50))
    return 50.0


def _score_achievement_progress(game_config: dict, achievements: List[Any]) -> float:
    total = len((game_config or {}).get("achievements", []) or [])
    earned = len(achievements or [])
    if total == 0:
        return 50.0 if earned == 0 else 100.0
    return _clamp((earned / total) * 100)


def _score_learning_engagement(run_log: List[dict]) -> float:
    if not run_log:
        return 40.0
    reflective = sum(
        1 for e in run_log
        if isinstance(e, dict) and e.get("type") in (
            "reflection", "free_text_response", "engine_complete", "metacognition",
        )
    )
    base = min(len(run_log) * 2, 60)
    return _clamp(base + min(reflective * 5, 40))


def _score_competitive_performance(state: Any, competitors: List[Any], multiplayer_active: bool,
                                    total_players: int) -> float:
    if not competitors and not multiplayer_active:
        return 50.0
    my_score = _get(state, "score", None)
    if not isinstance(my_score, (int, float)):
        return 50.0
    competitor_scores = []
    for c in competitors or []:
        c_score = c.get("score") if isinstance(c, dict) else getattr(c, "score", None)
        if isinstance(c_score, (int, float)):
            competitor_scores.append(c_score)
    if not competitor_scores:
        return 50.0
    better_than = sum(1 for s in competitor_scores if my_score >= s)
    return _clamp((better_than / len(competitor_scores)) * 100)


def _score_risk_management(run_log: List[dict]) -> float:
    if not run_log:
        return 50.0
    changes = [
        entry.get("net_change") for entry in run_log
        if isinstance(entry, dict) and isinstance(entry.get("net_change"), (int, float))
    ]
    if len(changes) < 2:
        return 50.0
    mean = sum(changes) / len(changes)
    variance = sum((c - mean) ** 2 for c in changes) / len(changes)
    volatility = math.sqrt(variance)
    # Lower volatility (relative to the typical swing size) -> steadier, better
    # risk management. Scaled so wildly swingy runs trend toward 0-30.
    scale = max(1.0, abs(mean) + 1.0)
    return _clamp(100 - min((volatility / scale) * 40, 100))


def _rank_for_score(score: float) -> str:
    for threshold, label in RANKS:
        if score >= threshold:
            return label
    return RANKS[-1][1]


def calculate_mento_score(
    state: Any,
    game_config: Optional[dict] = None,
    run_log: Optional[List[dict]] = None,
    achievements: Optional[List[Any]] = None,
    competitors: Optional[List[Any]] = None,
    multiplayer_active: bool = False,
    total_players: int = 1,
) -> Dict[str, Any]:
    game_config = game_config or {}
    run_log = run_log or []
    achievements = achievements or []
    competitors = competitors or []

    breakdown = {
        "resource_optimization": _score_resource_optimization(state, game_config),
        "decision_quality": _score_decision_quality(run_log),
        "speed_efficiency": _score_speed_efficiency(state, game_config, run_log),
        "achievement_progress": _score_achievement_progress(game_config, achievements),
        "learning_engagement": _score_learning_engagement(run_log),
        "competitive_performance": _score_competitive_performance(
            state, competitors, multiplayer_active, total_players
        ),
        "risk_management": _score_risk_management(run_log),
    }

    overall = sum(breakdown[k] * CATEGORY_WEIGHTS[k] for k in breakdown)
    overall = round(_clamp(overall), 1)

    return {
        "score": overall,
        "breakdown": {k: round(v, 1) for k, v in breakdown.items()},
        "weights": dict(CATEGORY_WEIGHTS),
        "rank": _rank_for_score(overall),
        # No cross-user population data is available at scoring time, so the
        # percentile is a direct function of the score rather than a true
        # empirical percentile — documented limitation, not a stand-in bug.
        "percentile": int(round(_clamp(overall))),
    }
