"""Class- and student-level rollups over `player_profile`'s per-user data.

Deliberately thin: `player_profile.py` already owns XP/history/dimension
tracking, so this module aggregates that data rather than keeping a
second copy. `_load_profiles()` is re-exported (not just used internally)
because app.py's `/api/analytics/dashboard` route calls
`learning_analytics._load_profiles()` directly, alongside `player_profile._load_profiles()`
elsewhere — matching that existing (if slightly unusual) direct-private-access
convention already used in this codebase.
"""
from typing import Any, Dict, List

import player_profile

_load_profiles = player_profile._load_profiles


def _history_scores(history: List[dict]) -> List[float]:
    scores = []
    for h in history or []:
        if not isinstance(h, dict):
            continue
        score = h.get("mento_score", h.get("score"))
        if isinstance(score, (int, float)):
            scores.append(float(score))
    return scores


def get_student_analytics(user_id: str) -> Dict[str, Any]:
    profile = player_profile.get_profile(user_id)
    history = profile.get("game_history", [])
    scores = _history_scores(history)

    return {
        "user_id": user_id,
        "display_name": profile.get("display_name", ""),
        "level": profile.get("level", 0),
        "games_completed": profile.get("games_completed", 0),
        "game_types_played": profile.get("game_types_played", []),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "highest_score": profile.get("highest_score", 0),
        "dimension_scores": profile.get("dimension_scores", {}),
        "badges_earned": profile.get("badges_earned", []),
        "streak_days": profile.get("streak_days", 0),
        "recent_activity": profile.get("recent_activity", []),
    }


def get_class_analytics() -> Dict[str, Any]:
    profiles = _load_profiles()
    student_summaries = []
    all_scores: List[float] = []
    dimension_totals: Dict[str, List[float]] = {}

    for user_id, raw in profiles.items():
        if not isinstance(raw, dict):
            continue
        history = raw.get("history", [])
        scores = _history_scores(history)
        all_scores.extend(scores)
        for dim, val in (raw.get("dimension_scores") or {}).items():
            if isinstance(val, (int, float)):
                dimension_totals.setdefault(dim, []).append(float(val))

        student_summaries.append({
            "user_id": user_id,
            "display_name": raw.get("display_name", ""),
            "games_completed": raw.get("games_completed", 0),
            "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "highest_score": raw.get("highest_score", 0),
        })

    return {
        "total_students": len(profiles),
        "total_games_completed": sum(s["games_completed"] for s in student_summaries),
        "class_average_score": round(sum(all_scores) / len(all_scores), 1) if all_scores else 0,
        "average_dimension_scores": {
            dim: round(sum(vals) / len(vals), 1) for dim, vals in dimension_totals.items()
        },
        "students": sorted(student_summaries, key=lambda s: s["average_score"], reverse=True),
    }
