"""Phase B placeholder: pitch coach endpoint."""
from flask import Blueprint, jsonify

bp = Blueprint("module_pitch_coach", __name__)


@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/pitch-coach")
def pitch_coach(module_id, lesson_id):
    return jsonify({"error": "not_implemented", "phase": "B"}), 501
