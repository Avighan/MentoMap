"""Game-content storage: reads/writes the JSON files under `backend/games/`.

Two shapes of file live there:

  * Most files (dealcraft.json, g6-math-fractions.json, ...) are one game
    each, fields at the top level (`game_id`, `game_type`, `initial_state`,
    ...) — `load_game()`/`load_bundle()` read these directly.

  * A handful of "special" files (negotiation_game.json, debate-scenarios.json,
    investor_pitch.json, and the 7 VALID_SESSION_TYPES files like
    job_interview.json) additionally nest their real content under a
    self-named wrapper key, e.g. `{"negotiation_game": {...}, "title": ...}`
    at the top *and* the same fields again inside `negotiation_game`. Two
    call sites in app.py disagree on which shape to pass into the `save_*`
    functions: the admin CRUD routes (e.g. `save_debate_scenarios(DEBATE_GAME, ...)`
    at app.py's admin debate routes) pass the *unwrapped* inner dict, while
    the storybook-image background job explicitly re-wraps
    (`{"debate_game": game_data}`) with a comment noting "save writes raw
    JSON". Both are made to work here: `_write_wrapped()` treats a dict
    whose only key is the wrapper key as already-wrapped and writes it
    as-is; anything else gets wrapped before writing. That's a real
    inconsistency between call sites, resolved by making the writer
    tolerant of both rather than picking one and breaking the other.
"""
import json
import logging
import os
import shutil
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
GAMES_DIR = os.path.join(_THIS_DIR, "games")

_LOCK = threading.Lock()

# game_id -> (mtime, data) cache for load_game()
_GAME_CACHE: Dict[str, Any] = {}
_GAME_CACHE_MTIME: Dict[str, float] = {}

_SPECIAL_FILES = {
    "negotiation": ("negotiation_game.json", "negotiation_game"),
    "debate": ("debate-scenarios.json", "debate_game"),
    "pitch": ("investor_pitch.json", "investor_pitch_game"),
}

VALID_SESSION_TYPES = (
    "job_interview", "group_discussion", "client_meeting",
    "conflict_mediation", "public_speaking", "stakeholder_update",
    "ai_discussion",
)
_SESSION_WRAPPER_KEY = "session_game"

_SPECIAL_FILENAMES = {fname for fname, _ in _SPECIAL_FILES.values()} | {
    f"{t}.json" for t in VALID_SESSION_TYPES
}


def _game_path(game_id: str) -> str:
    return os.path.join(GAMES_DIR, f"{game_id}.json")


def _read_json(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read %s: %s", path, e)
        return None


def _read_wrapped(path: str, wrapper_key: str) -> Optional[dict]:
    """Read a special file, returning its nested wrapper-key content."""
    data = _read_json(path)
    if data is None:
        return None
    inner = data.get(wrapper_key)
    return inner if isinstance(inner, dict) else data


def _write_wrapped(path: str, data: dict, wrapper_key: str, create_backup: bool = True) -> bool:
    if not isinstance(data, dict):
        return False
    if set(data.keys()) == {wrapper_key}:
        payload = data
    else:
        payload = {wrapper_key: data}
    try:
        with _LOCK:
            if create_backup and os.path.exists(path):
                backup_path = f"{path}.bak"
                shutil.copyfile(path, backup_path)
            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(payload, f, indent=2)
            os.replace(tmp_path, path)
        return True
    except (OSError, TypeError, ValueError) as e:
        logger.warning("Failed to write %s: %s", path, e)
        return False


def load_game(game_id: str) -> Optional[dict]:
    """Load a single game's JSON by id, cached by file mtime."""
    path = _game_path(game_id)
    if not os.path.exists(path):
        return None
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    if game_id not in _GAME_CACHE or _GAME_CACHE_MTIME.get(game_id) != mtime:
        data = _read_json(path)
        if data is None:
            return None
        _GAME_CACHE[game_id] = data
        _GAME_CACHE_MTIME[game_id] = mtime
    return _GAME_CACHE[game_id]


def save_game(game_data: dict, create_backup: bool = False) -> bool:
    """Write a single game dict back to `games/<game_id>.json`, unwrapped."""
    game_id = game_data.get("game_id") if isinstance(game_data, dict) else None
    if not game_id:
        return False
    path = _game_path(game_id)
    try:
        with _LOCK:
            if create_backup and os.path.exists(path):
                shutil.copyfile(path, f"{path}.bak")
            tmp_path = path + ".tmp"
            with open(tmp_path, "w") as f:
                json.dump(game_data, f, indent=2)
            os.replace(tmp_path, path)
        _GAME_CACHE[game_id] = game_data
        _GAME_CACHE_MTIME[game_id] = os.path.getmtime(path)
        return True
    except (OSError, TypeError, ValueError) as e:
        logger.warning("Failed to save game %s: %s", game_id, e)
        return False


def load_bundle() -> Dict[str, Any]:
    """Assemble the multi-game bundle from individual files in `games/`."""
    games: List[dict] = []
    if os.path.isdir(GAMES_DIR):
        for fname in sorted(os.listdir(GAMES_DIR)):
            if not fname.endswith(".json") or fname in _SPECIAL_FILENAMES:
                continue
            game_id = fname[:-len(".json")]
            try:
                data = load_game(game_id)
            except Exception as e:  # noqa: BLE001 — one bad file shouldn't sink the bundle
                logger.warning("Skipping unloadable game file %s: %s", fname, e)
                continue
            if isinstance(data, dict) and "game_id" in data:
                games.append(data)

    bundle: Dict[str, Any] = {
        "games": games,
        "global_stress_event": None,
        "negotiation_game": load_negotiation_game(),
        "debate_game": load_debate_scenarios(),
        "investor_pitch_game": load_investor_pitch(),
        "session_games": load_all_session_games(),
    }
    return bundle


# ---------------------------------------------------------------------------
# Negotiation / Debate / Investor-pitch special files
# ---------------------------------------------------------------------------

def load_negotiation_game() -> Optional[dict]:
    fname, key = _SPECIAL_FILES["negotiation"]
    return _read_wrapped(os.path.join(GAMES_DIR, fname), key)


def save_negotiation_game(data: dict, create_backup: bool = True) -> bool:
    fname, key = _SPECIAL_FILES["negotiation"]
    return _write_wrapped(os.path.join(GAMES_DIR, fname), data, key, create_backup)


def load_debate_scenarios() -> Optional[dict]:
    fname, key = _SPECIAL_FILES["debate"]
    return _read_wrapped(os.path.join(GAMES_DIR, fname), key)


def save_debate_scenarios(data: dict, create_backup: bool = True) -> bool:
    fname, key = _SPECIAL_FILES["debate"]
    return _write_wrapped(os.path.join(GAMES_DIR, fname), data, key, create_backup)


def load_investor_pitch() -> Optional[dict]:
    fname, key = _SPECIAL_FILES["pitch"]
    return _read_wrapped(os.path.join(GAMES_DIR, fname), key)


def save_investor_pitch(data: dict, create_backup: bool = True) -> bool:
    fname, key = _SPECIAL_FILES["pitch"]
    return _write_wrapped(os.path.join(GAMES_DIR, fname), data, key, create_backup)


# ---------------------------------------------------------------------------
# "Session" games (job_interview, group_discussion, ...)
# ---------------------------------------------------------------------------

def load_session_game(game_type: str) -> Optional[dict]:
    if game_type not in VALID_SESSION_TYPES:
        return None
    return _read_wrapped(os.path.join(GAMES_DIR, f"{game_type}.json"), _SESSION_WRAPPER_KEY)


def save_session_game(game_type: str, data: dict, create_backup: bool = True) -> bool:
    if game_type not in VALID_SESSION_TYPES:
        return False
    return _write_wrapped(os.path.join(GAMES_DIR, f"{game_type}.json"), data, _SESSION_WRAPPER_KEY, create_backup)


def load_all_session_games() -> Dict[str, dict]:
    out = {}
    for gtype in VALID_SESSION_TYPES:
        data = load_session_game(gtype)
        if data is not None:
            out[gtype] = data
    return out
