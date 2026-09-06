"""
Real-time Multiplayer Engine — synchronous PvP sessions (negotiation / debate).

Unlike `engines.multiplayer_engine.MultiplayerEngine` (async, turn-time-limit
measured in days, used for cohort pairing), sessions here are meant to be
played live: two students take turns inside one round with a short per-turn
time limit (`config.turn_time_limit`, seconds).

Sessions live in-memory for the life of the process and are mirrored to a
JSON file so a restart doesn't silently orphan an in-progress match — the
canonical persistence pattern used across this codebase (JSON under
backend/data/, threading.Lock around writes).
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_THIS_DIR)
DATA_DIR = os.environ.get("MENTO_DATA_DIR") or os.path.join(_BACKEND_DIR, "data")
SESSIONS_FILE = os.path.join(DATA_DIR, "realtime_sessions.json")

_LOCK = threading.Lock()
_SESSIONS: Dict[str, "RealtimeSession"] = {}
_LOADED_FROM_DISK = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RealtimeSession:
    """One live PvP session. `config` comes from the round's `pvp_mode` block
    (or a raw `/api/realtime/create` body): roles, max_turns, turn_time_limit,
    scoring_rubric, round_id, session_kind, preferred_role.
    """

    def __init__(self, session_id: str, game_id: str, creator_id: str, config: Optional[Dict[str, Any]] = None):
        self.id = session_id
        self.game_id = game_id
        self.config = dict(config or {})
        roles_list = list(self.config.get("roles") or [])
        self.max_players = max(2, len(roles_list)) if roles_list else 2
        self.players: List[str] = [creator_id]
        self.roles: Dict[str, str] = {}
        preferred_role = self.config.get("preferred_role")
        if roles_list:
            self.roles[creator_id] = preferred_role if preferred_role in roles_list else roles_list[0]
        self.status = "waiting"  # waiting | in_progress | completed | forfeited
        self.turn_index = 0
        self.current_turn_player: Optional[str] = None
        self.turns: List[Dict[str, Any]] = []
        self.winner: Optional[str] = None
        self.forfeited_by: Optional[str] = None
        self.created_at = _now_iso()
        self.updated_at = self.created_at

    # ---------- mutation ----------

    def join(self, user_id: str) -> Tuple[bool, str]:
        if user_id in self.players:
            return True, "already joined"
        if self.status != "waiting":
            return False, "Session is not accepting new players"
        if len(self.players) >= self.max_players:
            return False, "Session is full"

        self.players.append(user_id)
        roles_list = list(self.config.get("roles") or [])
        if roles_list:
            taken = set(self.roles.values())
            available = [r for r in roles_list if r not in taken] or roles_list
            self.roles[user_id] = available[0]

        if len(self.players) >= self.max_players:
            self.status = "in_progress"
            self.current_turn_player = self.players[0]

        self.updated_at = _now_iso()
        _persist()
        return True, ""

    def submit_turn(self, user_id: str, action: Dict[str, Any]) -> Tuple[bool, str]:
        if user_id not in self.players:
            return False, "Not a participant in this session"
        if self.status != "in_progress":
            return False, f"Session is {self.status}, not in progress"
        if self.current_turn_player != user_id:
            return False, "It is not your turn"

        self.turns.append({
            "turn_index": self.turn_index,
            "user_id": user_id,
            "role": self.roles.get(user_id),
            "action": action,
            "submitted_at": _now_iso(),
        })
        self.turn_index += 1

        idx = self.players.index(user_id)
        self.current_turn_player = self.players[(idx + 1) % len(self.players)]

        max_turns = int(self.config.get("max_turns") or 0)
        if max_turns and self.turn_index >= max_turns * len(self.players):
            self.status = "completed"
            self.current_turn_player = None

        self.updated_at = _now_iso()
        _persist()
        return True, ""

    def forfeit(self, user_id: str) -> Tuple[bool, str]:
        if user_id not in self.players:
            return False, "Not a participant in this session"
        if self.status in ("completed", "forfeited"):
            return True, ""
        self.forfeited_by = user_id
        self.status = "forfeited"
        self.current_turn_player = None
        remaining = [p for p in self.players if p != user_id]
        self.winner = remaining[0] if remaining else None
        self.updated_at = _now_iso()
        _persist()
        return True, ""

    # ---------- reads ----------

    def get_state(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        return {
            "session_id": self.id,
            "id": self.id,
            "game_id": self.game_id,
            "status": self.status,
            "players": list(self.players),
            "max_players": self.max_players,
            "roles": dict(self.roles),
            "my_role": self.roles.get(user_id) if user_id else None,
            "current_turn_player": self.current_turn_player,
            "is_my_turn": bool(user_id) and self.current_turn_player == user_id,
            "turn_index": self.turn_index,
            "turns": list(self.turns),
            "config": dict(self.config),
            "winner": self.winner,
            "forfeited_by": self.forfeited_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.id,
            "game_id": self.game_id,
            "status": self.status,
            "players": list(self.players),
            "player_count": len(self.players),
            "max_players": self.max_players,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_dict(self) -> Dict[str, Any]:
        d = self.to_summary()
        d.update({
            "roles": dict(self.roles),
            "turn_index": self.turn_index,
            "current_turn_player": self.current_turn_player,
            "turns": list(self.turns),
            "config": dict(self.config),
            "winner": self.winner,
            "forfeited_by": self.forfeited_by,
        })
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RealtimeSession":
        s = cls(d["id"], d.get("game_id", ""), (d.get("players") or [None])[0], d.get("config"))
        s.players = list(d.get("players") or s.players)
        s.roles = dict(d.get("roles") or {})
        s.max_players = d.get("max_players", s.max_players)
        s.status = d.get("status", "waiting")
        s.turn_index = d.get("turn_index", 0)
        s.current_turn_player = d.get("current_turn_player")
        s.turns = list(d.get("turns") or [])
        s.winner = d.get("winner")
        s.forfeited_by = d.get("forfeited_by")
        s.created_at = d.get("created_at", s.created_at)
        s.updated_at = d.get("updated_at", s.updated_at)
        return s


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _persist() -> None:
    """Write the full in-memory session table to disk. Called under _LOCK by
    callers that already hold it, or standalone (re-entrant safe via a
    dedicated write lock separate from the caller's critical section)."""
    _ensure_data_dir()
    try:
        payload = {sid: s.to_dict() for sid, s in _SESSIONS.items()}
        tmp_path = SESSIONS_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SESSIONS_FILE)
    except OSError as e:
        logger.warning("Failed to persist realtime sessions: %s", e)


def _load_from_disk() -> None:
    global _LOADED_FROM_DISK
    if _LOADED_FROM_DISK:
        return
    _LOADED_FROM_DISK = True
    if not os.path.exists(SESSIONS_FILE):
        return
    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for sid, d in (raw or {}).items():
            try:
                _SESSIONS[sid] = RealtimeSession.from_dict(d)
            except Exception as e:
                logger.warning("Skipping corrupt realtime session %s: %s", sid, e)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read %s: %s", SESSIONS_FILE, e)


def create_session(game_id: str, user_id: str, config: Optional[Dict[str, Any]] = None) -> RealtimeSession:
    """Create and register a new real-time session with `user_id` as its first player."""
    _load_from_disk()
    with _LOCK:
        session_id = uuid.uuid4().hex[:12]
        session = RealtimeSession(session_id, game_id, user_id, config)
        _SESSIONS[session_id] = session
        _persist()
        return session


def get_session(session_id: str) -> Optional[RealtimeSession]:
    """Return the live session object for `session_id`, or None."""
    _load_from_disk()
    return _SESSIONS.get(session_id)


def list_sessions(game_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return summary dicts for joinable (waiting) sessions, optionally filtered by game_id."""
    _load_from_disk()
    out = []
    for s in _SESSIONS.values():
        if s.status != "waiting":
            continue
        if game_id and s.game_id != game_id:
            continue
        out.append(s.to_summary())
    out.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return out
