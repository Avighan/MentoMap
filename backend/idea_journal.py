"""Per-user persistent idea journal keyed by (user_id, module_id).

Each entry: {entry_id, lesson_id?, lesson_title?, content, type, timestamp, starred, history[]}
Storage: backend/data/idea_journals/<user_id>__<module_id>.json
Append-only with edit history retained for teacher visibility.
"""
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional


def _data_dir() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    )
    d = os.path.join(base, "idea_journals")
    os.makedirs(d, exist_ok=True)
    return d


def _path(user_id: str, module_id: str) -> str:
    safe = f"{user_id}__{module_id}".replace("/", "_")
    return os.path.join(_data_dir(), f"{safe}.json")


def _load(user_id: str, module_id: str) -> List[Dict[str, Any]]:
    p = _path(user_id, module_id)
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save(user_id: str, module_id: str, entries: List[Dict[str, Any]]) -> None:
    p = _path(user_id, module_id)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def append_entry(user_id: str, module_id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    entries = _load(user_id, module_id)
    new = {
        "entry_id": uuid.uuid4().hex[:12],
        "lesson_id": entry.get("lesson_id"),
        "lesson_title": entry.get("lesson_title"),
        "content": entry.get("content", ""),
        "type": entry.get("type", "free_form"),
        "timestamp": entry.get("timestamp") or _now_iso(),
        "starred": False,
        "history": [],
    }
    entries.append(new)
    _save(user_id, module_id, entries)
    return new


def edit_entry(user_id: str, module_id: str, entry_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    entries = _load(user_id, module_id)
    for e in entries:
        if e["entry_id"] == entry_id:
            e.setdefault("history", []).append({
                "content": e.get("content", ""),
                "timestamp": e.get("timestamp"),
            })
            if "content" in patch:
                e["content"] = patch["content"]
            e["timestamp"] = _now_iso()
            _save(user_id, module_id, entries)
            return e
    return None


def star_entry(user_id: str, module_id: str, entry_id: str, starred: bool) -> bool:
    entries = _load(user_id, module_id)
    for e in entries:
        if e["entry_id"] == entry_id:
            e["starred"] = bool(starred)
            _save(user_id, module_id, entries)
            return True
    return False


def list_entries(user_id: str, module_id: str) -> List[Dict[str, Any]]:
    return _load(user_id, module_id)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
