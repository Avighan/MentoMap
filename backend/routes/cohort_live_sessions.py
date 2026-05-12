"""Phase C placeholder: cohort live session scheduling + RSVPs."""
from flask import Blueprint, jsonify

bp = Blueprint("cohort_live_sessions", __name__)

PREFIX = "/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions"


@bp.route(PREFIX, methods=["GET", "POST"])
def list_or_create(cohort_id, module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501


@bp.route(f"{PREFIX}/<session_id>", methods=["PATCH", "DELETE"])
def edit_or_delete(cohort_id, module_id, session_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501


@bp.post(f"{PREFIX}/<session_id>/rsvp")
def rsvp(cohort_id, module_id, session_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501
