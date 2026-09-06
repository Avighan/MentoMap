"""Per-game player ratings (1-5 stars + optional feedback).

Called from app.py's `/api/run/<run_id>/rate` and
`/api/games/<game_id>/ratings` routes. One JSON file at
`data/game_ratings.json`, keyed by game_id -> list of rating entries.
"""
import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(_THIS_DIR, "data")
    os.makedirs(base, exist_ok=True)
    return base


def _path() -> str:
    return os.path.join(_data_dir(), "game_ratings.json")


_LOCK = threading.Lock()


def _load() -> Dict[str, List[dict]]:
    path = _path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: Dict[str, List[dict]]) -> None:
    path = _path()
    tmp_path = path + ".tmp"
    with _LOCK:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)


def rate_game(game_id: str, user_id: str, run_id: str, rating: int,
              feedback: str = "") -> Dict[str, Any]:
    data = _load()
    entries = data.setdefault(game_id, [])
    entry = {
        "user_id": user_id,
        "run_id": run_id,
        "rating": int(rating),
        "feedback": feedback or "",
        "rated_at": datetime.now().isoformat(),
    }
    # One rating per (user, run) — replace if this run was already rated.
    existing_idx = next(
        (i for i, e in enumerate(entries) if e.get("user_id") == user_id and e.get("run_id") == run_id),
        None,
    )
    if existing_idx is not None:
        entries[existing_idx] = entry
    else:
        entries.append(entry)
    _save(data)
    return entry


def get_game_ratings(game_id: str) -> Dict[str, Any]:
    entries = _load().get(game_id, [])
    count = len(entries)
    average = round(sum(e.get("rating", 0) for e in entries) / count, 2) if count else 0
    return {
        "game_id": game_id,
        "average_rating": average,
        "count": count,
        "ratings": entries,
    }


def get_all_avg_ratings() -> Dict[str, float]:
    data = _load()
    out = {}
    for game_id, entries in data.items():
        if entries:
            out[game_id] = round(sum(e.get("rating", 0) for e in entries) / len(entries), 2)
    return out
