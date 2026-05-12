"""Scheduled live sessions for a cohort running a module.

Storage: backend/data/cohort_live_sessions.json keyed by "<cohort_id>__<module_id>".
Async cohorts simply have no entries -> student UI hides the banner.
"""
import json
import os
import uuid
from typing import Any, Dict, List, Optional


def _path() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    )
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "cohort_live_sessions.json")


def _key(cohort_id: str, module_id: str) -> str:
    return f"{cohort_id}__{module_id}"


def _load() -> Dict[str, List[Dict[str, Any]]]:
    p = _path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: Dict[str, List[Dict[str, Any]]]) -> None:
    p = _path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def list_sessions(cohort_id: str, module_id: str) -> List[Dict[str, Any]]:
    return _load().get(_key(cohort_id, module_id), [])


def create_session(cohort_id: str, module_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(data)
    data["session_id"] = uuid.uuid4().hex[:12]
    data.setdefault("rsvps", [])
    data.setdefault("status", "scheduled")
    data.setdefault("recording_url", None)
    store = _load()
    store.setdefault(_key(cohort_id, module_id), []).append(data)
    _save(store)
    return data


def update_session(cohort_id: str, module_id: str, session_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    store = _load()
    sessions = store.get(_key(cohort_id, module_id), [])
    for s in sessions:
        if s["session_id"] == session_id:
            for k, v in patch.items():
                if k != "session_id":
                    s[k] = v
            _save(store)
            return s
    return None


def delete_session(cohort_id: str, module_id: str, session_id: str) -> bool:
    store = _load()
    key = _key(cohort_id, module_id)
    sessions = store.get(key, [])
    new = [s for s in sessions if s["session_id"] != session_id]
    if len(new) == len(sessions):
        return False
    store[key] = new
    _save(store)
    return True


def toggle_rsvp(cohort_id: str, module_id: str, session_id: str, user_id: str, attending: bool) -> Optional[Dict[str, Any]]:
    store = _load()
    for s in store.get(_key(cohort_id, module_id), []):
        if s["session_id"] == session_id:
            rsvps = set(s.get("rsvps") or [])
            if attending:
                rsvps.add(user_id)
            else:
                rsvps.discard(user_id)
            s["rsvps"] = sorted(rsvps)
            _save(store)
            return s
    return None


def upcoming_for_user(user_id: str, user_cohort_id: Optional[str], module_id: str, within_days: int = 7) -> List[Dict[str, Any]]:
    """Sessions in next N days that the user can join."""
    if not user_cohort_id:
        return []
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) + timedelta(days=within_days)
    out: List[Dict[str, Any]] = []
    for s in list_sessions(user_cohort_id, module_id):
        try:
            ts = datetime.fromisoformat(s["scheduled_at"].replace("Z", "+00:00"))
            if ts <= cutoff and s.get("status") != "cancelled":
                out.append(s)
        except (KeyError, ValueError):
            continue
    return out
