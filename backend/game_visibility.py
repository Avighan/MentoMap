"""Admin-controlled game hiding, independent of a game's own `visible` field.

app.py's game-listing routes already filter on each game's own
`visible`/`game_type` fields; the comment above that filtering
("also respect game_visibility.json (admin hides)") is the evidence for
this module — a second, centrally-managed hide-list an admin can use
without editing every individual game file. Stored as one small JSON file
at `data/game_visibility.json`: `{"hidden_game_ids": [...], "hidden_game_types": [...]}`.
"""
import json
import os
import threading
from typing import List, Set

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(_THIS_DIR, "data")
    os.makedirs(base, exist_ok=True)
    return base


def _path() -> str:
    return os.path.join(_data_dir(), "game_visibility.json")


_LOCK = threading.Lock()


def _load() -> dict:
    path = _path()
    if not os.path.exists(path):
        return {"hidden_game_ids": [], "hidden_game_types": []}
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"hidden_game_ids": [], "hidden_game_types": []}
    data.setdefault("hidden_game_ids", [])
    data.setdefault("hidden_game_types", [])
    return data


def _save(data: dict) -> None:
    path = _path()
    tmp_path = path + ".tmp"
    with _LOCK:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)


def get_hidden_games() -> Set[str]:
    return set(_load().get("hidden_game_ids", []))


def get_hidden_game_types() -> Set[str]:
    return set(_load().get("hidden_game_types", []))


def hide_game(game_id: str) -> None:
    data = _load()
    if game_id not in data["hidden_game_ids"]:
        data["hidden_game_ids"].append(game_id)
        _save(data)


def unhide_game(game_id: str) -> None:
    data = _load()
    if game_id in data["hidden_game_ids"]:
        data["hidden_game_ids"].remove(game_id)
        _save(data)


def hide_game_type(game_type: str) -> None:
    data = _load()
    if game_type not in data["hidden_game_types"]:
        data["hidden_game_types"].append(game_type)
        _save(data)


def unhide_game_type(game_type: str) -> None:
    data = _load()
    if game_type in data["hidden_game_types"]:
        data["hidden_game_types"].remove(game_type)
        _save(data)
