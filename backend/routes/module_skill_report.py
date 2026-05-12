"""Phase C placeholder: skill report + certificate."""
from flask import Blueprint, jsonify

bp = Blueprint("module_skill_report", __name__)


@bp.get("/api/modules/<module_id>/skill-report")
def report(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501


@bp.get("/api/modules/<module_id>/skill-report/card.png")
def card_png(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501


@bp.get("/api/modules/<module_id>/certificate")
def certificate(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501
