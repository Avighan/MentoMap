"""
Student-facing game requests — the content velocity loop.

Students who run out of games in a category can request a new one. Each
request becomes a "ticket" the AI Game Builder (admin side) can pick up.
A simple JSON store keeps things lightweight; popular requests are
upvoted, surfacing high-demand topics to admins.

Storage: `data/game_requests.json`
  {
    "requests": [
      {"id": "...", "user_id": "...", "title": "...", "topic": "...",
       "game_type_hint": "story_branching", "audience": "grade_7",
       "votes": ["user_1", "user_2"], "status": "open",
       "created_at": "...", "fulfilled_game_id": null}
    ]
  }
"""
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

REQUESTS_FILE = os.path.join(os.path.dirname(__file__), "data", "game_requests.json")
_VALID_STATUSES = {"open", "in_progress", "fulfilled", "rejected"}


def _load() -> Dict[str, Any]:
    try:
        with open(REQUESTS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"requests": []}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(REQUESTS_FILE), exist_ok=True)
    with open(REQUESTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def create_request(user_id: str, title: str, topic: str,
                   game_type_hint: Optional[str] = None,
                   audience: Optional[str] = None) -> Dict[str, Any]:
    """Add a new game request. Auto-creates the ticket as 'open'."""
    if not user_id or not title or not topic:
        raise ValueError("user_id, title, and topic are required")
    title = title.strip()[:200]
    topic = topic.strip()[:500]
    data = _load()
    req = {
        "id": str(uuid.uuid4())[:8],
        "user_id": user_id,
        "title": title,
        "topic": topic,
        "game_type_hint": (game_type_hint or "").strip()[:50] or None,
        "audience": (audience or "").strip()[:50] or None,
        "votes": [user_id],  # creator auto-votes
        "status": "open",
        "created_at": time.time(),
        "fulfilled_game_id": None,
    }
    data["requests"].append(req)
    _save(data)
    return req


def list_requests(status: Optional[str] = None,
                  limit: int = 50) -> List[Dict[str, Any]]:
    """List requests, sorted by votes desc then recency. Filter by status if given."""
    data = _load()
    items = data.get("requests") or []
    if status and status in _VALID_STATUSES:
        items = [r for r in items if r.get("status") == status]
    items = sorted(
        items,
        key=lambda r: (-len(r.get("votes") or []), -float(r.get("created_at") or 0)),
    )
    return items[: max(1, int(limit))]


def upvote(user_id: str, request_id: str) -> Optional[Dict[str, Any]]:
    """Add user_id to votes if not already present. No-op if already voted."""
    if not user_id or not request_id:
        return None
    data = _load()
    for r in data.get("requests") or []:
        if r.get("id") == request_id:
            votes = list(r.get("votes") or [])
            if user_id not in votes:
                votes.append(user_id)
                r["votes"] = votes
                _save(data)
            return r
    return None


def update_status(request_id: str, status: str,
                  fulfilled_game_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Admin-side update — mark a request as in_progress / fulfilled / rejected."""
    if status not in _VALID_STATUSES:
        return None
    data = _load()
    for r in data.get("requests") or []:
        if r.get("id") == request_id:
            r["status"] = status
            if fulfilled_game_id:
                r["fulfilled_game_id"] = fulfilled_game_id
            _save(data)
            return r
    return None
