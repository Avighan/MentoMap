"""Phase B placeholder: interview simulation endpoints."""
from flask import Blueprint, jsonify

bp = Blueprint("module_interview_sim", __name__)


@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/start")
def start(module_id, lesson_id):
    return jsonify({"error": "not_implemented", "phase": "B"}), 501


@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/turn")
def turn(module_id, lesson_id):
    return jsonify({"error": "not_implemented", "phase": "B"}), 501


@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/end")
def end(module_id, lesson_id):
    return jsonify({"error": "not_implemented", "phase": "B"}), 501
