"""
Multiplayer Engine — asynchronous turn-based matches (cohort pairing, PvP-by-mail).

Distinct from `engines.realtime_multiplayer_engine`: matches here are meant to
be played over hours/days (default turn_time_limit is 24h, match_timeout is
7 days) rather than live in one sitting — e.g. a teacher pairing an entire
cohort for a negotiation game where each side replies whenever they log in.

Matches persist as JSON under `storage_path` (one file, `matches.json`),
guarded by a threading.Lock and refreshed via mtime-based caching, matching
the rest of this codebase's storage engines (see modules_engine.py).
"""

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = {
    "mode": "async_turns",
    "max_players": 2,
    "turn_time_limit": 86400,     # seconds per turn before it's considered stale
    "match_timeout": 604800,      # seconds of total inactivity before a match expires
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MultiplayerEngine:
    def __init__(self, multiplayer_config: Optional[Dict[str, Any]] = None, storage_path: Optional[str] = None):
        self.config: Dict[str, Any] = dict(_DEFAULT_CONFIG)
        self.config.update(multiplayer_config or {})

        if storage_path is None:
            _backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage_path = os.path.join(_backend_dir, "game_sessions", "multiplayer")
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)
        self.matches_file = os.path.join(self.storage_path, "matches.json")

        self._lock = threading.Lock()
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_mtime: Optional[float] = None

    # ---------- storage ----------

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.matches_file):
            return {}
        try:
            mtime = os.path.getmtime(self.matches_file)
            if self._cache is not None and self._cache_mtime == mtime:
                return self._cache
            with open(self.matches_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cache = data
            self._cache_mtime = mtime
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read %s: %s", self.matches_file, e)
            return {}

    def _save(self, data: Dict[str, Any]) -> None:
        tmp_path = self.matches_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self.matches_file)
        self._cache = data
        self._cache_mtime = os.path.getmtime(self.matches_file)

    # ---------- match lifecycle ----------

    def create_match(self, game_id: str, creator_id: str, match_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new waiting match with `creator_id` as its first player."""
        settings = dict(self.config)
        settings.update(match_settings or {})
        match_id = uuid.uuid4().hex[:12]
        now = _now_iso()
        match = {
            "match_id": match_id,
            "game_id": game_id,
            "creator_id": str(creator_id),
            "players": [str(creator_id)],
            "max_players": settings.get("max_players", 2),
            "match_settings": settings,
            "status": "waiting",
            "current_turn_player": None,
            "turns": [],
            "state": {},
            "created_at": now,
            "updated_at": now,
            "last_activity_at": now,
        }
        with self._lock:
            data = self._load()
            data[match_id] = match
            self._save(data)
        return match

    def join_match(self, match_id: str, user_id: str) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
            match = data.get(match_id)
            if not match:
                return {"success": False, "error": "Match not found"}
            user_id = str(user_id)
            if user_id in match["players"]:
                return {"success": True, "match": match, "already_joined": True}
            if match["status"] != "waiting":
                return {"success": False, "error": "Match is not accepting new players"}
            if len(match["players"]) >= match.get("max_players", 2):
                return {"success": False, "error": "Match is full"}

            match["players"].append(user_id)
            if len(match["players"]) >= match.get("max_players", 2):
                match["status"] = "in_progress"
                match["current_turn_player"] = match["players"][0]
            match["updated_at"] = _now_iso()
            match["last_activity_at"] = match["updated_at"]
            data[match_id] = match
            self._save(data)
            return {"success": True, "match": match}

    def list_available_matches(self, game_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Matches still joinable or playable — optionally filtered to one game."""
        data = self._load()
        out = []
        for match in data.values():
            if game_id and match.get("game_id") != game_id:
                continue
            if match.get("status") not in ("waiting", "in_progress"):
                continue
            out.append(match)
        out.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return out

    def submit_turn(self, match_id: str, user_id: str, action_data: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            data = self._load()
            match = data.get(match_id)
            if not match:
                return {"success": False, "error": "Match not found"}
            user_id = str(user_id)
            if user_id not in match["players"]:
                return {"success": False, "error": "Not a participant in this match"}
            if match["status"] != "in_progress":
                return {"success": False, "error": f"Match is {match['status']}, not in progress"}

            mode = match.get("match_settings", {}).get("mode", "async_turns")
            if mode == "async_turns" and match.get("current_turn_player") and match["current_turn_player"] != user_id:
                return {"success": False, "error": "It is not your turn"}

            now = _now_iso()
            match.setdefault("turns", []).append({
                "user_id": user_id,
                "action_data": action_data,
                "submitted_at": now,
            })

            players = match["players"]
            idx = players.index(user_id)
            match["current_turn_player"] = players[(idx + 1) % len(players)]

            max_turns = match.get("match_settings", {}).get("max_turns")
            if max_turns and len(match["turns"]) >= int(max_turns) * len(players):
                match["status"] = "completed"
                match["current_turn_player"] = None

            match["updated_at"] = now
            match["last_activity_at"] = now
            data[match_id] = match
            self._save(data)
            return {"success": True, "match": match}

    def get_match_state(self, match_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        data = self._load()
        return data.get(match_id)

    def update_heartbeat(self, session_id: str, player_id: str) -> None:
        """Record that `player_id` is still active in `session_id` (keeps cleanup from expiring live matches)."""
        with self._lock:
            data = self._load()
            match = data.get(session_id)
            if not match:
                return
            match.setdefault("heartbeats", {})[str(player_id)] = _now_iso()
            match["last_activity_at"] = _now_iso()
            data[session_id] = match
            self._save(data)

    def cleanup_stale_sessions(self) -> int:
        """Expire matches with no activity for longer than `match_timeout`. Returns count expired."""
        timeout = self.config.get("match_timeout", _DEFAULT_CONFIG["match_timeout"])
        now_dt = datetime.now(timezone.utc)
        expired = 0
        with self._lock:
            data = self._load()
            changed = False
            for match in data.values():
                if match.get("status") in ("completed", "forfeited", "expired"):
                    continue
                last = match.get("last_activity_at") or match.get("updated_at") or match.get("created_at")
                try:
                    last_dt = datetime.fromisoformat(last)
                except (TypeError, ValueError):
                    continue
                if (now_dt - last_dt).total_seconds() > timeout:
                    match["status"] = "expired"
                    match["updated_at"] = _now_iso()
                    changed = True
                    expired += 1
            if changed:
                self._save(data)
        if expired:
            logger.info("multiplayer_engine: expired %d stale match(es)", expired)
        return expired
