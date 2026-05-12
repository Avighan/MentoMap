"""Phase C: cohort live session scheduling + RSVPs."""
from flask import Blueprint, jsonify, request

import cohort_live_sessions as _cls
from auth import require_auth

bp = Blueprint("cohort_live_sessions", __name__)

PREFIX = "/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions"


def _user() -> dict:
    return getattr(request, "current_user", None) or {}


def _user_id() -> str:
    u = _user()
    return str(u.get("user_id") or u.get("username") or "")


def _require_teacher_or_admin():
    role = (_user().get("role") or "")
    if role not in ("teacher", "trainer", "school_admin", "admin"):
        return jsonify({"error": "forbidden"}), 403
    return None


@bp.route(PREFIX, methods=["GET"])
@require_auth
def list_sessions(cohort_id, module_id):
    return jsonify({"sessions": _cls.list_sessions(cohort_id, module_id)})


@bp.route(PREFIX, methods=["POST"])
@require_auth
def create_session(cohort_id, module_id):
    forbidden = _require_teacher_or_admin()
    if forbidden:
        return forbidden
    body = request.get_json(silent=True) or {}
    required = {"week", "title", "host_name", "scheduled_at", "meeting_url"}
    missing = [k for k in required if not body.get(k)]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400
    return jsonify(_cls.create_session(cohort_id, module_id, body))


@bp.route(f"{PREFIX}/<session_id>", methods=["PATCH"])
@require_auth
def update_session(cohort_id, module_id, session_id):
    forbidden = _require_teacher_or_admin()
    if forbidden:
        return forbidden
    body = request.get_json(silent=True) or {}
    out = _cls.update_session(cohort_id, module_id, session_id, body)
    if not out:
        return jsonify({"error": "not found"}), 404
    return jsonify(out)


@bp.route(f"{PREFIX}/<session_id>", methods=["DELETE"])
@require_auth
def delete_session(cohort_id, module_id, session_id):
    forbidden = _require_teacher_or_admin()
    if forbidden:
        return forbidden
    ok = _cls.delete_session(cohort_id, module_id, session_id)
    return jsonify({"deleted": ok}), (200 if ok else 404)


@bp.post(f"{PREFIX}/<session_id>/rsvp")
@require_auth
def rsvp(cohort_id, module_id, session_id):
    user_id = _user_id()
    body = request.get_json(silent=True) or {}
    out = _cls.toggle_rsvp(cohort_id, module_id, session_id, user_id, bool(body.get("attending", True)))
    if not out:
        return jsonify({"error": "not found"}), 404
    return jsonify(out)
