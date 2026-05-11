"""
REST endpoints for the retention/UX modules in the audit-followup batch:
  - weekly_challenge       (3 weekly goals + claim flow)
  - game_requests          (student-facing content velocity)
  - reflection_prompts     (age-bucketed prompts)
  - parent_visibility      (daily soft-skill summary)
  - offline_activities     (printable activity cards)

Auth model: most endpoints try to derive the user from a Bearer token via
`auth.decode_token`, which is the convention the rest of the codebase
uses; if auth isn't available we still respond (with anonymous user_id)
so the test harness and unauthenticated demo flows continue to work.
"""
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

import weekly_challenge
import game_requests
import reflection_prompts
import parent_visibility
import offline_activities


retention_bp = Blueprint("retention", __name__)


def _current_user_id() -> Optional[str]:
    """Best-effort token decode. Returns None if not authenticated."""
    auth_header = (request.headers.get("Authorization") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    if not token:
        return None
    try:
        from auth import decode_token  # local import to avoid hard dependency at module load
        payload = decode_token(token) or {}
        return payload.get("user_id") or payload.get("sub") or payload.get("username")
    except Exception:
        return None


def _is_admin() -> bool:
    auth_header = (request.headers.get("Authorization") or "").strip()
    if not auth_header.lower().startswith("bearer "):
        return False
    try:
        from auth import decode_token
        payload = decode_token(auth_header[7:].strip()) or {}
        role = payload.get("role") or payload.get("user_role") or ""
        return role in {"admin", "super_admin", "school_admin"}
    except Exception:
        return False


# ==================== WEEKLY CHALLENGES ====================

@retention_bp.route("/api/weekly-challenges", methods=["GET"])
def list_weekly_challenges():
    """Return the current user's 3 weekly challenges + progress."""
    user_id = _current_user_id() or request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401
    challenges = weekly_challenge.get_user_challenges(user_id)
    return jsonify({"challenges": challenges})


@retention_bp.route("/api/weekly-challenges/<challenge_id>/claim", methods=["POST"])
def claim_weekly_challenge(challenge_id: str):
    user_id = _current_user_id() or (request.get_json(silent=True) or {}).get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401
    claimed = weekly_challenge.claim_reward(user_id, challenge_id)
    if not claimed:
        return jsonify({"error": "Challenge not completed or already claimed"}), 400
    return jsonify({"success": True, "challenge": claimed})


# ==================== GAME REQUESTS (CONTENT VELOCITY) ====================

@retention_bp.route("/api/game-requests", methods=["POST"])
def create_game_request():
    """Student-facing — submit a request for a new game."""
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401
    body = request.get_json(silent=True) or {}
    title = body.get("title")
    topic = body.get("topic")
    if not title or not topic:
        return jsonify({"error": "title and topic are required"}), 400
    try:
        req = game_requests.create_request(
            user_id=user_id,
            title=title,
            topic=topic,
            game_type_hint=body.get("game_type_hint"),
            audience=body.get("audience"),
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"success": True, "request": req}), 201


@retention_bp.route("/api/game-requests", methods=["GET"])
def list_game_requests():
    status = request.args.get("status")
    try:
        limit = int(request.args.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    items = game_requests.list_requests(status=status, limit=limit)
    return jsonify({"requests": items})


@retention_bp.route("/api/game-requests/<request_id>/upvote", methods=["POST"])
def upvote_game_request(request_id: str):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401
    updated = game_requests.upvote(user_id, request_id)
    if not updated:
        return jsonify({"error": "Request not found"}), 404
    return jsonify({"success": True, "request": updated})


@retention_bp.route("/api/admin/game-requests/<request_id>", methods=["PATCH"])
def admin_update_game_request(request_id: str):
    if not _is_admin():
        return jsonify({"error": "Admin only"}), 403
    body = request.get_json(silent=True) or {}
    status = body.get("status")
    fulfilled_game_id = body.get("fulfilled_game_id")
    updated = game_requests.update_status(request_id, status, fulfilled_game_id)
    if not updated:
        return jsonify({"error": "Invalid status or request not found"}), 400
    return jsonify({"success": True, "request": updated})


# ==================== REFLECTION PROMPTS ====================

@retention_bp.route("/api/reflection-prompts", methods=["GET"])
def get_reflection_prompts():
    """Return age-appropriate reflection prompts.

    Query: ?age=12  → returns the band's full prompt list so the client
    can rotate. ?age=12&choice_index=2 → returns a single prompt.
    """
    try:
        age = int(request.args.get("age") or 13)
    except (TypeError, ValueError):
        age = 13
    band = reflection_prompts.get_band(age)
    idx = request.args.get("choice_index")
    if idx is not None:
        try:
            single = reflection_prompts.get_prompt(age, int(idx))
        except (TypeError, ValueError):
            single = reflection_prompts.get_prompt(age, 0)
        return jsonify({"age": age, "band": band, "prompt": single})
    return jsonify({
        "age": age,
        "band": band,
        "prompts": reflection_prompts.get_all_prompts(age),
    })


# ==================== PARENT DAILY SUMMARY ====================

@retention_bp.route("/api/parent/daily-summary", methods=["GET"])
def parent_daily_summary():
    """
    Returns today's soft-skill summary for the parent's child.

    Query: ?child_id=...&date=YYYY-MM-DD (date optional, defaults today)

    The data source is a list of run records pulled from storage. We try
    a couple of common storage helpers so this works whether the project
    persists runs in `data/runs.json` or via `storage.get_runs_for_user`.
    """
    parent_id = _current_user_id()
    child_id = request.args.get("child_id")
    if not parent_id and not child_id:
        return jsonify({"error": "Authentication or child_id required"}), 401
    target_child = child_id or parent_id
    target_date = request.args.get("date")

    runs = _runs_for_child(target_child)
    summary = parent_visibility.build_daily_summary(target_child, runs, target_date=target_date)
    return jsonify(summary)


def _runs_for_child(child_id: str):
    """Best-effort fetch — try several known storage helpers, fall back to []."""
    try:
        from storage import get_runs_for_user  # type: ignore
        rs = get_runs_for_user(child_id)
        if isinstance(rs, list):
            return rs
    except Exception:
        pass
    try:
        import storage  # type: ignore
        if hasattr(storage, "RUNS") and isinstance(storage.RUNS, dict):
            return [r for r in storage.RUNS.values()
                    if isinstance(r, dict) and r.get("user_id") == child_id]
    except Exception:
        pass
    return []


# ==================== OFFLINE ACTIVITY CARDS ====================

@retention_bp.route("/api/offline-activities", methods=["GET"])
def list_offline_activities():
    """List offline activity cards. Filter by ?dim=empathy&age=8."""
    dim = request.args.get("dim")
    age = request.args.get("age")
    age_int: Optional[int] = None
    if age is not None:
        try:
            age_int = int(age)
        except (TypeError, ValueError):
            age_int = None
    cards = offline_activities.list_cards(dimension=dim, age=age_int)
    return jsonify({
        "count": len(cards),
        "cards": cards,
        "library_total": offline_activities.card_count(),
    })


@retention_bp.route("/api/offline-activities/match", methods=["GET"])
def match_offline_activity():
    """Return one best-fit card for a given dimension + age."""
    dim = request.args.get("dim")
    try:
        age = int(request.args.get("age") or 10)
    except (TypeError, ValueError):
        age = 10
    if not dim:
        return jsonify({"error": "dim is required"}), 400
    card = offline_activities.get_activity_card(dim, age)
    if not card:
        return jsonify({"error": "No card available"}), 404
    return jsonify({"card": card})
