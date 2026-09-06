"""Run-session storage: one JSON file per run under `data/runs/`.

Mirrors the persistence style already used elsewhere in this codebase
(`modules_engine.py`, `idea_journal.py`): plain JSON files on disk, an
in-memory cache invalidated by file mtime, and a `threading.Lock` around
writes so concurrent requests within one process don't corrupt a file.

`RUNS` is a plain dict so existing call sites across `app.py` that do
`RUNS[run_id]["state"] = ...` (direct dict access, no disk round-trip)
keep working unchanged for the lifetime of a single request — the entry is
populated by `create_run()`/`get_run()` and mutated in place. `update_run()`
is what flushes a mutated entry back to disk.

`get_run()` reloads from disk only when the file's mtime has moved past
what we last cached — the common case (same process, same run, repeated
calls within a request or across requests) returns the *same* in-memory
object, which matters because some callers (see `engine.py`) store a
typed state object rather than a plain dict in `run["state"]`; a JSON
round-trip would flatten that back to a dict.
"""
import json
import logging
import os
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from storage_interface import SessionNotFoundError, SessionExpiredError, StorageIOError

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("MENTO_DATA_DIR") or os.path.join(_THIS_DIR, "data")
STORAGE_DIR = os.path.join(DATA_DIR, "runs")
LEADERBOARD_DIR = os.path.join(DATA_DIR, "leaderboards")
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(LEADERBOARD_DIR, exist_ok=True)

# Runs with no activity for this long are treated as expired. Generous by
# default since there's no product requirement pinning this down; override
# via env for tests / tighter deployments.
SESSION_TTL_SECONDS = int(os.environ.get("MENTO_RUN_TTL_SECONDS", str(24 * 3600)))

RUNS: Dict[str, dict] = {}
RUNS_MTIME: Dict[str, float] = {}

_WRITE_LOCK = threading.Lock()


def _run_path(run_id: str) -> str:
    safe = str(run_id).replace("/", "_")
    return os.path.join(STORAGE_DIR, f"{safe}.json")


def _json_default(obj):
    """Serialize non-dict run state (e.g. engine.py's GameState) to JSON."""
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def _persist(run_id: str, run: dict) -> None:
    path = _run_path(run_id)
    tmp_path = path + ".tmp"
    try:
        with _WRITE_LOCK:
            with open(tmp_path, "w") as f:
                json.dump(run, f, default=_json_default)
            os.replace(tmp_path, path)
            RUNS_MTIME[run_id] = os.path.getmtime(path)
    except (TypeError, ValueError, OSError) as e:
        raise StorageIOError(f"Failed to persist run {run_id}: {e}") from e


def create_run(game_id: str, initial_state: Any, game: Optional[dict] = None) -> str:
    """Create a new run for `game_id`, returning the new run_id."""
    run_id = uuid.uuid4().hex
    now = datetime.now().isoformat()
    run = {
        "run_id": run_id,
        "game_id": game_id,
        "game": game,
        "state": initial_state,
        "created_at": now,
        "last_accessed": now,
        "completed": False,
        "log": [],
    }
    RUNS[run_id] = run
    _persist(run_id, run)
    return run_id


def get_run(run_id: str) -> dict:
    """Return the run dict for `run_id`, loading/refreshing from disk as needed.

    Raises `SessionNotFoundError` if no run exists, `SessionExpiredError` if
    it exists but is past `SESSION_TTL_SECONDS` since last access, and
    `StorageIOError` if the file on disk is unreadable/corrupt.
    """
    path = _run_path(run_id)
    if not os.path.exists(path):
        if run_id in RUNS:
            # In-memory-only run (e.g. not yet flushed) — still usable.
            return RUNS[run_id]
        raise SessionNotFoundError(run_id)

    try:
        mtime = os.path.getmtime(path)
    except OSError as e:
        raise StorageIOError(f"Failed to stat run {run_id}: {e}") from e

    if run_id not in RUNS or RUNS_MTIME.get(run_id) != mtime:
        try:
            with open(path) as f:
                run = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise StorageIOError(f"Failed to read run {run_id}: {e}") from e
        RUNS[run_id] = run
        RUNS_MTIME[run_id] = mtime

    run = RUNS[run_id]

    last_accessed = run.get("last_accessed")
    if last_accessed and SESSION_TTL_SECONDS > 0:
        try:
            last_dt = datetime.fromisoformat(last_accessed)
            if (datetime.now() - last_dt).total_seconds() > SESSION_TTL_SECONDS:
                raise SessionExpiredError(run_id)
        except ValueError:
            pass  # malformed timestamp — don't block access over it

    run["last_accessed"] = datetime.now().isoformat()
    return run


def update_run(run_id: str, run: dict) -> None:
    """Persist a (presumably mutated) run dict back to disk and cache."""
    run["last_accessed"] = datetime.now().isoformat()
    RUNS[run_id] = run
    _persist(run_id, run)


def delete_run(run_id: str) -> None:
    RUNS.pop(run_id, None)
    RUNS_MTIME.pop(run_id, None)
    path = _run_path(run_id)
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError as e:
            raise StorageIOError(f"Failed to delete run {run_id}: {e}") from e


# ---------------------------------------------------------------------------
# Leaderboards — one JSON file per game_id under data/leaderboards/.
# ---------------------------------------------------------------------------

def _leaderboard_path(game_id: str) -> str:
    safe = str(game_id).replace("/", "_")
    return os.path.join(LEADERBOARD_DIR, f"{safe}.json")


def _load_leaderboard(game_id: str) -> List[dict]:
    path = _leaderboard_path(game_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _write_leaderboard(game_id: str, entries: List[dict]) -> None:
    path = _leaderboard_path(game_id)
    tmp_path = path + ".tmp"
    with _WRITE_LOCK:
        with open(tmp_path, "w") as f:
            json.dump(entries, f)
        os.replace(tmp_path, path)


def _extract_score(run: dict) -> float:
    """Best-effort extraction of a final score from a run dict.

    Run state is produced by several different code paths (the legacy
    rounds/engine.py GameState, the grader-registry `summary` shape from
    routes/grader_routes.py, ad-hoc `mento_score_result` dicts) so this
    checks the plausible locations in priority order rather than assuming
    one canonical shape.
    """
    for key in ("mento_score_result",):
        result = run.get(key)
        if isinstance(result, dict) and "score" in result:
            try:
                return float(result["score"])
            except (TypeError, ValueError):
                pass
    if "mento_score" in run:
        try:
            return float(run["mento_score"])
        except (TypeError, ValueError):
            pass
    state = run.get("state")
    if isinstance(state, dict) and "score" in state:
        try:
            return float(state["score"])
        except (TypeError, ValueError):
            pass
    elif state is not None and hasattr(state, "score"):
        try:
            return float(getattr(state, "score"))
        except (TypeError, ValueError):
            pass
    summary = run.get("summary")
    if isinstance(summary, dict) and "score" in summary:
        try:
            return float(summary["score"])
        except (TypeError, ValueError):
            pass
    return 0.0


def save_final_score(game_id: str, user_id: str, run: dict, game: Optional[dict] = None) -> dict:
    """Append/replace this user's leaderboard entry for `game_id`.

    One entry per user per game — a later run overwrites the earlier entry
    only if it scores higher, so the leaderboard reflects each player's
    personal best.
    """
    score = _extract_score(run)
    dimension_scores = {}
    state = run.get("state")
    if isinstance(state, dict):
        dimension_scores = state.get("dimension_scores") or {}
    elif state is not None:
        dimension_scores = getattr(state, "dimension_scores", {}) or {}

    entry = {
        "user_id": user_id,
        "display_name": run.get("display_name") or user_id,
        "score": score,
        "run_id": run.get("run_id"),
        "game_id": game_id,
        "dimension_scores": dimension_scores,
        "recorded_at": datetime.now().isoformat(),
    }

    entries = _load_leaderboard(game_id)
    existing_idx = next((i for i, e in enumerate(entries) if e.get("user_id") == user_id), None)
    if existing_idx is not None:
        if entries[existing_idx].get("score", 0) <= score:
            entries[existing_idx] = entry
        else:
            entry = entries[existing_idx]
    else:
        entries.append(entry)

    entries.sort(key=lambda e: e.get("score", 0), reverse=True)
    _write_leaderboard(game_id, entries)
    return entry


def get_leaderboard(game_id: str, limit: int = 10) -> dict:
    entries = _load_leaderboard(game_id)
    return {
        "game_id": game_id,
        "entries": entries[:limit],
        "total_entries": len(entries),
    }


def get_user_rank(game_id: str, user_id: str) -> dict:
    entries = _load_leaderboard(game_id)
    for idx, entry in enumerate(entries, start=1):
        if entry.get("user_id") == user_id:
            return {
                "found": True,
                "game_id": game_id,
                "user_id": user_id,
                "rank": idx,
                "score": entry.get("score", 0),
                "total_players": len(entries),
            }
    return {"found": False, "game_id": game_id, "user_id": user_id}
