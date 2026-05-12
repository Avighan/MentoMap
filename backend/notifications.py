"""
Notification manager for MentoApp.

Stores per-user notifications in backend/data/notifications.json.
All file I/O is wrapped in try/except so notification failures never crash the app.
"""

import json
import os
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Optional

# ---------------------------------------------------------------------------
# Storage path
# ---------------------------------------------------------------------------
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_NOTIF_FILE = os.path.join(_DATA_DIR, "notifications.json")

# ---------------------------------------------------------------------------
# Valid notification types
# ---------------------------------------------------------------------------
NOTIF_TYPES = {
    "streak_risk",
    "achievement",
    "level_up",
    "game_complete",
    "welcome",
    "weekly_digest",
    "recommendation",
    "student_stuck",
    "student_completed",
    "module_daily_dispatch",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load() -> dict:
    """Load the notifications store. Returns {} on any error."""
    try:
        with open(_NOTIF_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    except Exception:
        return {}


def _save(data: dict) -> None:
    """Persist the notifications store. Silently swallows errors."""
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        tmp = _NOTIF_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, _NOTIF_FILE)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------

def create_notification(
    user_id: str,
    notif_type: str,
    title: str,
    body: str,
    action_url: Optional[str] = None,
    icon: Optional[str] = None,
    dedupe_key: Optional[str] = None,
) -> dict:
    """
    Create and persist a notification.

    notif_type must be one of: streak_risk | achievement | level_up |
                                game_complete | welcome | weekly_digest |
                                recommendation | module_daily_dispatch

    dedupe_key is an optional opaque key the caller can store on the
    notification (e.g. "dispatch_<module>_day<N>") so a subsequent send
    can detect "already delivered" via has_notification().

    Returns the notification dict:
        {id, user_id, type, title, body, action_url, icon, read, created_at, dedupe_key}
    """
    notif = {
        "id": str(uuid4()),
        "user_id": user_id,
        "type": notif_type if notif_type in NOTIF_TYPES else "game_complete",
        "title": title,
        "body": body,
        "action_url": action_url,
        "icon": icon,
        "dedupe_key": dedupe_key,
        "read": False,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    try:
        data = _load()
        user_notifs = data.get(user_id, [])
        user_notifs.append(notif)
        data[user_id] = user_notifs
        _save(data)
        cleanup_old(user_id)
    except Exception:
        pass
    return notif


def has_notification(user_id: str, dedupe_key: str) -> bool:
    """Return True iff a notification with the given dedupe_key was previously
    delivered to this user. Used to prevent duplicate daily-dispatch sends."""
    if not dedupe_key:
        return False
    try:
        data = _load()
        for n in data.get(user_id, []) or []:
            if n.get("dedupe_key") == dedupe_key:
                return True
    except Exception:
        pass
    return False


def get_notifications(
    user_id: str,
    limit: int = 20,
    unread_only: bool = False,
) -> list:
    """
    Return notifications for a user, sorted newest first.

    Args:
        user_id:     the user
        limit:       max items to return (default 20)
        unread_only: when True, return only unread notifications
    """
    try:
        data = _load()
        notifs = data.get(user_id, [])
        if unread_only:
            notifs = [n for n in notifs if not n.get("read", False)]
        # Sort newest first
        notifs = sorted(notifs, key=lambda n: n.get("created_at", ""), reverse=True)
        return notifs[:limit]
    except Exception:
        return []


def mark_read(user_id: str, notif_id: str) -> bool:
    """
    Mark a single notification as read.

    Returns True if found and updated, False otherwise.
    """
    try:
        data = _load()
        user_notifs = data.get(user_id, [])
        found = False
        for n in user_notifs:
            if n.get("id") == notif_id:
                n["read"] = True
                found = True
                break
        if found:
            data[user_id] = user_notifs
            _save(data)
        return found
    except Exception:
        return False


def mark_all_read(user_id: str) -> int:
    """
    Mark all notifications for a user as read.

    Returns the count of notifications that were marked.
    """
    try:
        data = _load()
        user_notifs = data.get(user_id, [])
        count = 0
        for n in user_notifs:
            if not n.get("read", False):
                n["read"] = True
                count += 1
        data[user_id] = user_notifs
        _save(data)
        return count
    except Exception:
        return 0


def get_unread_count(user_id: str) -> int:
    """Return the number of unread notifications for a user."""
    try:
        data = _load()
        user_notifs = data.get(user_id, [])
        return sum(1 for n in user_notifs if not n.get("read", False))
    except Exception:
        return 0


def delete_notification(user_id: str, notif_id: str) -> bool:
    """
    Delete a single notification.

    Returns True if found and deleted, False otherwise.
    """
    try:
        data = _load()
        user_notifs = data.get(user_id, [])
        new_notifs = [n for n in user_notifs if n.get("id") != notif_id]
        if len(new_notifs) == len(user_notifs):
            return False  # not found
        data[user_id] = new_notifs
        _save(data)
        return True
    except Exception:
        return False


def cleanup_old(user_id: str, keep: int = 50) -> None:
    """
    Remove oldest notifications beyond the keep limit for a user.
    Sorts by created_at ascending and deletes the oldest excess entries.
    """
    try:
        data = _load()
        user_notifs = data.get(user_id, [])
        if len(user_notifs) <= keep:
            return
        # Sort oldest first, keep the newest `keep` items
        sorted_notifs = sorted(user_notifs, key=lambda n: n.get("created_at", ""))
        data[user_id] = sorted_notifs[-keep:]
        _save(data)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Trigger helpers — convenience functions called from app.py
# ---------------------------------------------------------------------------

def trigger_welcome(user_id: str, display_name: str = "") -> None:
    """Send a welcome notification when a new user registers."""
    try:
        name = display_name or "there"
        create_notification(
            user_id=user_id,
            notif_type="welcome",
            title="Welcome to MentoApp!",
            body=(
                f"Hey {name}! You're ready to start your leadership journey. "
                "Play your first game to earn XP and unlock achievements."
            ),
            action_url="/games",
            icon="🎉",
        )
    except Exception:
        pass


def trigger_achievement(
    user_id: str,
    badge_name: str,
    badge_icon: str,
    xp_reward: int = 0,
) -> None:
    """Send a notification when the user earns an achievement badge."""
    try:
        xp_text = f" (+{xp_reward} XP)" if xp_reward else ""
        create_notification(
            user_id=user_id,
            notif_type="achievement",
            title=f"Achievement Unlocked: {badge_name}",
            body=f"You earned the '{badge_name}' badge{xp_text}. Keep it up!",
            action_url="/profile",
            icon=badge_icon or "🏅",
        )
    except Exception:
        pass


def trigger_level_up(user_id: str, new_level: int) -> None:
    """Send a notification when the user levels up."""
    try:
        create_notification(
            user_id=user_id,
            notif_type="level_up",
            title=f"Level Up! You reached Level {new_level}",
            body=(
                f"Congratulations — you've reached Level {new_level}! "
                "New challenges and content may now be unlocked."
            ),
            action_url="/profile",
            icon="⬆️",
        )
    except Exception:
        pass


def trigger_game_complete(
    user_id: str,
    game_title: str,
    xp_earned: int,
    streak_days: int = 0,
) -> None:
    """
    Send a notification when the user completes a game.
    Includes streak info when relevant.
    """
    try:
        streak_text = ""
        if streak_days and streak_days > 1:
            streak_text = f" You're on a {streak_days}-day streak!"
        create_notification(
            user_id=user_id,
            notif_type="game_complete",
            title=f"Game Complete: {game_title}",
            body=f"Great job finishing '{game_title}'! You earned {xp_earned} XP.{streak_text}",
            action_url="/games",
            icon="✅",
        )
    except Exception:
        pass


def trigger_streak_reminder(user_id: str, streak_days: int) -> None:
    """
    Send a streak-risk reminder only if the user hasn't already been reminded
    recently (within 20-23 hours window) to avoid spamming.
    """
    try:
        data = _load()
        user_notifs = data.get(user_id, [])

        # Check if a streak_risk notification was already sent in the last 20 hours
        cutoff = datetime.utcnow() - timedelta(hours=20)
        for n in user_notifs:
            if n.get("type") == "streak_risk":
                try:
                    sent_at = datetime.fromisoformat(n["created_at"].rstrip("Z"))
                    if sent_at >= cutoff:
                        return  # already reminded recently — skip
                except Exception:
                    pass

        create_notification(
            user_id=user_id,
            notif_type="streak_risk",
            title=f"Don't break your {streak_days}-day streak!",
            body=(
                f"You have a {streak_days}-day learning streak going. "
                "Play a game today to keep it alive!"
            ),
            action_url="/games",
            icon="🔥",
        )
    except Exception:
        pass


def trigger_student_stuck(
    teacher_user_id: str,
    student_name: str,
    game_title: str,
    duration_min: int,
) -> None:
    """Notify a teacher that a student has been on the same game for a long time."""
    try:
        create_notification(
            user_id=teacher_user_id,
            notif_type="student_stuck",
            title=f"{student_name} may need help",
            body=f"{student_name} has been playing '{game_title}' for {duration_min} minutes without completing it.",
            action_url="/admin",
            icon="⏰",
        )
    except Exception:
        pass


def trigger_student_completed(
    teacher_user_id: str,
    student_name: str,
    game_title: str,
    score: int,
) -> None:
    """Notify a teacher that a student completed a game."""
    try:
        create_notification(
            user_id=teacher_user_id,
            notif_type="student_completed",
            title=f"{student_name} completed a game!",
            body=f"{student_name} finished '{game_title}' with a score of {score}.",
            action_url="/admin",
            icon="✅",
        )
    except Exception:
        pass


def trigger_recommendation(
    user_id: str,
    game_title: str,
    game_id: str,
    reason: str,
) -> None:
    """Send a game recommendation notification."""
    try:
        create_notification(
            user_id=user_id,
            notif_type="recommendation",
            title=f"Recommended for you: {game_title}",
            body=reason,
            action_url=f"/games/{game_id}",
            icon="💡",
        )
    except Exception:
        pass
