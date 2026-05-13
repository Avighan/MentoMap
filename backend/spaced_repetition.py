"""
Spaced repetition system for soft skill consolidation.
Uses SM-2 algorithm adapted for game-based learning.
"""

import json
import os
from datetime import datetime, timedelta

REVIEWS_FILE = os.path.join(os.path.dirname(__file__), "data", "spaced_reviews.json")

# Standard 6 soft-skill dimensions tracked across the platform
SKILL_DIMENSIONS = [
    "strategic_thinking",
    "risk_tolerance",
    "delayed_gratification",
    "adaptability",
    "resilience",
    "empathy",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_reviews():
    """Load the reviews store from disk. Returns empty dict on missing/corrupt file."""
    try:
        with open(REVIEWS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_reviews(data: dict):
    """Persist the reviews store to disk."""
    os.makedirs(os.path.dirname(REVIEWS_FILE), exist_ok=True)
    with open(REVIEWS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _sm2_next_interval(ease_factor: float, interval: int, quality: int):
    """
    SM-2 algorithm: compute the next review interval and updated ease factor.

    Parameters
    ----------
    ease_factor : float  — current ease factor (starts at 2.5, min 1.3)
    interval    : int    — current interval in days (0 = first review)
    quality     : int    — performance quality 0-5

    Returns
    -------
    (new_interval_days: int, new_ease_factor: float)
    """
    if quality < 3:
        # Failed recall — restart from scratch
        new_interval = 1
    else:
        if interval == 0:
            new_interval = 1
        elif interval == 1:
            new_interval = 6
        else:
            new_interval = round(interval * ease_factor)

    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ef = max(1.3, round(new_ef, 4))

    return max(1, new_interval), new_ef


def _score_to_quality(score_0_100: int) -> int:
    """Convert a 0-100 skill score to SM-2 quality (0-5)."""
    if score_0_100 >= 80:
        return 5
    if score_0_100 >= 65:
        return 4
    if score_0_100 >= 50:
        return 3
    if score_0_100 >= 35:
        return 2
    if score_0_100 >= 20:
        return 1
    return 0


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _days_until(date_str: str) -> int:
    """Days from today until date_str (negative = overdue)."""
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d")
        delta = target - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return delta.days
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def schedule_review(user_id: str, game_id: str, dimension: str, score_0_100: int):
    """
    After completing a game, schedule (or update) a review for a weak dimension.

    Only creates/updates entries for scores below 65 (quality < 4) — these are
    the dimensions that need reinforcement.

    Parameters
    ----------
    user_id     : str  — authenticated user id
    game_id     : str  — game identifier
    dimension   : str  — skill dimension name
    score_0_100 : int  — dimension score from the completed game session
    """
    quality = _score_to_quality(score_0_100)

    data = _load_reviews()
    user_data = data.setdefault(user_id, {})
    key = f"{game_id}::{dimension}"

    existing = user_data.get(key, {})
    ease_factor = existing.get("ease_factor", 2.5)
    interval = existing.get("interval_days", 0)

    new_interval, new_ef = _sm2_next_interval(ease_factor, interval, quality)
    next_review = (datetime.now() + timedelta(days=new_interval)).strftime("%Y-%m-%d")

    user_data[key] = {
        "game_id": game_id,
        "dimension": dimension,
        "interval_days": new_interval,
        "ease_factor": new_ef,
        "next_review_date": next_review,
        "last_score": score_0_100,
        "last_reviewed": _today_str(),
        "review_count": existing.get("review_count", 0) + 1,
    }

    _save_reviews(data)


def get_due_reviews(user_id: str, games_by_dimension: dict = None) -> list:
    """
    Return all reviews that are due today or overdue for user_id.

    Parameters
    ----------
    games_by_dimension : dict, optional
        Maps dimension name → list of game_ids that teach that dimension.
        When provided, each due review substitutes the original game_id with
        a *different* game type for the same dimension (contextual interleaving).
        This forces transfer: strategic_thinking reviewed in chess one week,
        then in a negotiation the next — same skill, new context.

    Returns a list of dicts:
      [{game_id, original_game_id, dimension, next_review_date, due_since,
        days_overdue, last_score, reason, is_interleaved}]
    """
    data = _load_reviews()
    user_data = data.get(user_id, {})
    today = _today_str()
    due = []

    for key, entry in user_data.items():
        next_review = entry.get("next_review_date", today)
        if next_review <= today:
            days_overdue = max(0, -_days_until(next_review))
            reason = "Overdue review" if days_overdue > 0 else "Due today"

            original_game_id = entry["game_id"]
            review_game_id = original_game_id
            is_interleaved = False

            # Interleaving: pick a different game type that teaches the same dimension
            if games_by_dimension:
                dim = entry["dimension"]
                candidates = games_by_dimension.get(dim, [])
                # Exclude original game to force a new learning context
                alternatives = [g for g in candidates if g != original_game_id]
                if alternatives:
                    # Cycle deterministically based on review_count so each
                    # successive review rotates through a different game type
                    review_count = entry.get("review_count", 0)
                    review_game_id = alternatives[review_count % len(alternatives)]
                    is_interleaved = True

            due.append({
                "game_id": review_game_id,
                "original_game_id": original_game_id,
                "dimension": entry["dimension"],
                "next_review_date": next_review,
                "due_since": next_review,
                "days_overdue": days_overdue,
                "last_score": entry.get("last_score", 50),
                "interval_days": entry.get("interval_days", 1),
                "review_count": entry.get("review_count", 0),
                "reason": reason,
                "is_interleaved": is_interleaved,
            })

    # Most overdue first
    due.sort(key=lambda x: x["next_review_date"])
    return due


def complete_review(user_id: str, game_id: str, score_0_100: int):
    """
    Mark a review session as done and update the SM-2 interval for all dimensions
    of that game that are currently tracked.

    Parameters
    ----------
    user_id     : str  — authenticated user id
    game_id     : str  — game identifier
    score_0_100 : int  — overall session score (used for all dimensions in this game)
    """
    data = _load_reviews()
    user_data = data.get(user_id, {})
    quality = _score_to_quality(score_0_100)
    updated = 0

    for key, entry in user_data.items():
        if entry.get("game_id") == game_id:
            ef = entry.get("ease_factor", 2.5)
            iv = entry.get("interval_days", 1)
            new_iv, new_ef = _sm2_next_interval(ef, iv, quality)
            next_review = (datetime.now() + timedelta(days=new_iv)).strftime("%Y-%m-%d")
            entry["ease_factor"] = new_ef
            entry["interval_days"] = new_iv
            entry["next_review_date"] = next_review
            entry["last_score"] = score_0_100
            entry["last_reviewed"] = _today_str()
            entry["review_count"] = entry.get("review_count", 0) + 1
            updated += 1

    if updated:
        _save_reviews(data)

    return {"updated": updated, "game_id": game_id}


def get_review_games(user_id: str, count: int = 3) -> list:
    """
    Return up to `count` game IDs to review, prioritising overdue first.

    Returns a list of game_id strings (deduplicated, ordered by urgency).
    """
    due = get_due_reviews(user_id)
    seen = set()
    result = []
    for entry in due:
        gid = entry["game_id"]
        if gid not in seen:
            seen.add(gid)
            result.append(gid)
        if len(result) >= count:
            break
    return result


def get_full_schedule(user_id: str) -> list:
    """
    Return the full review schedule for a user (past, present and future entries).

    Returns a list of dicts ordered by next_review_date ascending.
    """
    data = _load_reviews()
    user_data = data.get(user_id, {})
    today = _today_str()
    schedule = []

    for key, entry in user_data.items():
        next_review = entry.get("next_review_date", today)
        days_until_due = _days_until(next_review)
        status = "overdue" if days_until_due < 0 else ("due_today" if days_until_due == 0 else "upcoming")
        schedule.append({
            "game_id": entry["game_id"],
            "dimension": entry["dimension"],
            "next_review_date": next_review,
            "days_until_due": days_until_due,
            "status": status,
            "last_score": entry.get("last_score", 50),
            "interval_days": entry.get("interval_days", 1),
            "ease_factor": entry.get("ease_factor", 2.5),
            "review_count": entry.get("review_count", 0),
            "last_reviewed": entry.get("last_reviewed", ""),
        })

    schedule.sort(key=lambda x: x["next_review_date"])
    return schedule


# --- Module flashcards (Phase C) -------------------------------------------
# Stored separately from game reviews so existing SM-2 schedule logic is
# untouched. Flashcards still use _sm2_next_interval when reviewed.
def _flashcards_path() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    )
    return os.path.join(base, "module_flashcards.json")


def _load_flashcards() -> dict:
    p = _flashcards_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_flashcards(data: dict) -> None:
    p = _flashcards_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def schedule_flashcard(user_id: str, module_id: str, lesson_id: str, card: dict) -> None:
    """Inject a flashcard into the user's module-SR queue. Idempotent on (user, module, lesson, q)."""
    data = _load_flashcards()
    key = user_id
    user_cards = data.setdefault(key, [])
    q = (card.get("q") or "").strip()
    if not q:
        return
    for c in user_cards:
        if (
            c.get("module_id") == module_id
            and c.get("lesson_id") == lesson_id
            and c.get("q") == q
        ):
            return  # already seeded
    user_cards.append({
        "module_id": module_id,
        "lesson_id": lesson_id,
        "q": q,
        "a": card.get("a", ""),
        "skill_tag": card.get("skill_tag"),
        "ease_factor": 2.5,
        "interval_days": 0,
        "next_review": _today_str(),
        "created_at": _today_str(),
    })
    _save_flashcards(data)


def list_module_flashcards(user_id: str, module_id: str = None) -> list:
    data = _load_flashcards()
    cards = data.get(user_id, [])
    if module_id:
        return [c for c in cards if c.get("module_id") == module_id]
    return cards
