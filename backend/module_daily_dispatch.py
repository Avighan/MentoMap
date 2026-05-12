"""Daily dispatch: pick today's tip for a user mid-module and post it as a
notification.

Schedule: APScheduler 'cron' at 18:00 IST (registered in app.py inside
``_run_scheduler()``). For each user whose module progress shows they are
within 28 days of starting, fetch their day-N message from the bank and
create a deduped notification.

The dispatch bank lives at:
    <DATA_DIR>/module_daily_dispatch/<module_id>.json

Where ``DATA_DIR`` is ``$MENTO_DATA_DIR`` if set (used by tests), otherwise
``backend/data``.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _data_dir() -> str:
    return os.environ.get("MENTO_DATA_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    )


def _bank_path(module_id: str) -> str:
    return os.path.join(_data_dir(), "module_daily_dispatch", f"{module_id}.json")


def _load_bank(module_id: str) -> list:
    p = _bank_path(module_id)
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except (json.JSONDecodeError, OSError):
        return []


def _days_between(start_iso: str, today_iso: str) -> int:
    a = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    b = datetime.fromisoformat(today_iso.replace("Z", "+00:00"))
    return (b.date() - a.date()).days


def message_for_user_today(
    module_id: str, started_at_iso: str, today_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Return today's dispatch message for a user, or None if the user is
    outside the dispatch window (before day 1 or after the last day in the bank)."""
    today = today_iso or datetime.now(timezone.utc).isoformat()
    day = _days_between(started_at_iso, today) + 1  # day 1 == start day
    if day < 1:
        return None
    bank = _load_bank(module_id)
    for m in bank:
        if m.get("day") == day:
            return m
    return None


def _user_opted_in(user_id: str) -> bool:
    """Default ON during pilot. Off only if the user explicitly set
    preferences.module_daily_dispatch = False."""
    try:
        from player_profile import get_profile  # local import to avoid cycles at module import
        prof = get_profile(user_id) or {}
        prefs = prof.get("preferences") or {}
        return prefs.get("module_daily_dispatch", True) is not False
    except Exception:
        return True


def run_daily_dispatch(
    module_id: str = "mento_entrepreneur_4week",
    today_iso: Optional[str] = None,
) -> int:
    """Push today's tip to every user currently in-progress on the module.
    Returns the number of notifications sent."""
    today = today_iso or datetime.now(timezone.utc).isoformat()
    sent = 0
    try:
        import modules_engine
        import notifications as _notif
    except Exception:
        return 0

    try:
        progress_map = modules_engine.list_all_module_progress(module_id) or {}
    except Exception:
        return 0

    for user_id, prog in progress_map.items():
        started = (prog or {}).get("started_at")
        if not started:
            continue
        if not _user_opted_in(user_id):
            continue
        msg = message_for_user_today(module_id, started, today)
        if not msg:
            continue
        dedupe_key = f"dispatch_{module_id}_day{msg['day']}"
        try:
            if _notif.has_notification(user_id, dedupe_key):
                continue
            action_url = f"/modules/{module_id}"
            if msg.get("lesson_id"):
                action_url = f"{action_url}#{msg['lesson_id']}"
            _notif.create_notification(
                user_id=user_id,
                notif_type="module_daily_dispatch",
                title=msg.get("title", "Mento tip"),
                body=msg.get("body", ""),
                action_url=action_url,
                icon="📬",
                dedupe_key=dedupe_key,
            )
            sent += 1
        except Exception:
            continue
    return sent
