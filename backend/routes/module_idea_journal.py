"""Phase C placeholder: idea journal CRUD + export."""
from flask import Blueprint, jsonify

bp = Blueprint("module_idea_journal", __name__)


@bp.route("/api/modules/<module_id>/idea-journal", methods=["GET", "POST", "PATCH"])
def journal(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501


@bp.get("/api/modules/<module_id>/idea-journal/export")
def export(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501
