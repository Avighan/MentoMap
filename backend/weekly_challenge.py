"""
Weekly challenges — lightweight goals like "Play 3 games this week" or
"Score 80+ on a strategy game". Stored per-user and reset at ISO-week
boundaries (Mon 00:00 UTC). Sibling of `daily_challenge.py`; intentionally
kept separate to keep that module's "one game per day" semantics clean.

Storage: `data/weekly_challenges.json`
  {
    "<user_id>": {
      "iso_week": "2026-W19",
      "challenges": [
        {"id": "play_3", "kind": "play_count", "target": 3, "progress": 1, "claimed": false, "title": "...", "reward_xp": 50},
        ...
      ]
    }
  }
"""
import datetime as _dt
import hashlib
import json
import os
from typing import Any, Dict, List, Optional

WEEKLY_FILE = os.path.join(os.path.dirname(__file__), "data", "weekly_challenges.json")

# Pool of challenges. Each week we deterministically pick 3 of these for
# each user (seeded by user_id + iso_week so they're stable within the week
# but vary user-to-user and week-to-week).
_CHALLENGE_POOL: List[Dict[str, Any]] = [
    {"id": "play_3", "kind": "play_count", "target": 3,
     "title": "Play 3 games this week", "reward_xp": 50,
     "icon": "🎮"},
    {"id": "play_5", "kind": "play_count", "target": 5,
     "title": "Play 5 games this week", "reward_xp": 100,
     "icon": "🎯"},
    {"id": "score_80", "kind": "high_score", "target": 80,
     "title": "Score 80+ on any game", "reward_xp": 60,
     "icon": "⭐"},
    {"id": "score_90", "kind": "high_score", "target": 90,
     "title": "Score 90+ on any game", "reward_xp": 100,
     "icon": "🌟"},
    {"id": "two_game_types", "kind": "distinct_types", "target": 2,
     "title": "Try 2 different game types", "reward_xp": 70,
     "icon": "🌈"},
    {"id": "strategy_game", "kind": "play_type",
     "target_type": "strategy", "target": 1,
     "title": "Play 1 strategy game", "reward_xp": 50,
     "icon": "♟️"},
    {"id": "story_game", "kind": "play_type",
     "target_type": "story_branching", "target": 1,
     "title": "Play 1 story-branching game", "reward_xp": 50,
     "icon": "📖"},
    {"id": "reflection", "kind": "reflection_count", "target": 5,
     "title": "Submit 5 reflections", "reward_xp": 60,
     "icon": "💭"},
    {"id": "streak_3", "kind": "streak_days", "target": 3,
     "title": "Maintain a 3-day streak", "reward_xp": 80,
     "icon": "🔥"},
]


def _iso_week_key(date: Optional[_dt.date] = None) -> str:
    d = date or _dt.datetime.utcnow().date()
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _load_all() -> Dict[str, Any]:
    try:
        with open(WEEKLY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_all(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(WEEKLY_FILE), exist_ok=True)
    with open(WEEKLY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _select_challenges(user_id: str, iso_week: str, count: int = 3) -> List[Dict[str, Any]]:
    """Deterministically pick `count` challenges from the pool — same
    user gets same challenges all week, different users see variety."""
    seed = f"{user_id}::{iso_week}".encode()
    digest = hashlib.md5(seed).hexdigest()
    seed_int = int(digest, 16)
    pool = list(_CHALLENGE_POOL)
    pool.sort(key=lambda c: hashlib.md5(f"{c['id']}::{seed_int}".encode()).hexdigest())
    return [
        {**c, "progress": 0, "claimed": False, "completed": False}
        for c in pool[:count]
    ]


def get_user_challenges(user_id: str) -> List[Dict[str, Any]]:
    """Return the user's 3 challenges for the current ISO week, creating
    a fresh set if a new week has started or the user is new."""
    if not user_id:
        return []
    iso_week = _iso_week_key()
    data = _load_all()
    entry = data.get(user_id) or {}
    if entry.get("iso_week") != iso_week:
        entry = {"iso_week": iso_week, "challenges": _select_challenges(user_id, iso_week)}
        data[user_id] = entry
        _save_all(data)
    return entry.get("challenges") or []


def record_event(user_id: str, kind: str, value: int = 1, **kwargs) -> List[Dict[str, Any]]:
    """Increment progress on any matching challenges.

    Args:
        kind: one of 'play_count', 'high_score', 'distinct_types',
              'play_type', 'reflection_count', 'streak_days'.
        value: usually 1 for counters; for high_score / streak_days, pass
               the *current* score / day-count and we max it.
        kwargs: optional `game_type` (for play_type / distinct_types).

    Returns: the user's full challenge list after update.
    """
    if not user_id:
        return []
    iso_week = _iso_week_key()
    data = _load_all()
    entry = data.get(user_id) or {}
    if entry.get("iso_week") != iso_week:
        entry = {"iso_week": iso_week, "challenges": _select_challenges(user_id, iso_week)}
    challenges = entry.get("challenges") or []
    game_type = kwargs.get("game_type")

    for c in challenges:
        if c.get("kind") != kind:
            continue
        # Type-filter for play_type / distinct_types
        if kind == "play_type" and c.get("target_type") != game_type:
            continue
        if kind in ("high_score", "streak_days"):
            # Take the max — these are absolute thresholds, not counters.
            c["progress"] = max(int(c.get("progress", 0)), int(value))
        elif kind == "distinct_types":
            seen = set(c.get("seen_types") or [])
            if game_type:
                seen.add(game_type)
            c["seen_types"] = sorted(seen)
            c["progress"] = len(seen)
        else:
            c["progress"] = int(c.get("progress", 0)) + int(value)
        if c["progress"] >= int(c.get("target", 1)):
            c["completed"] = True

    entry["challenges"] = challenges
    data[user_id] = entry
    _save_all(data)
    return challenges


def claim_reward(user_id: str, challenge_id: str) -> Optional[Dict[str, Any]]:
    """Mark a completed challenge as claimed; returns the challenge or None."""
    iso_week = _iso_week_key()
    data = _load_all()
    entry = data.get(user_id) or {}
    if entry.get("iso_week") != iso_week:
        return None
    for c in entry.get("challenges") or []:
        if c.get("id") == challenge_id and c.get("completed") and not c.get("claimed"):
            c["claimed"] = True
            data[user_id] = entry
            _save_all(data)
            return c
    return None
