"""Phase C: idea journal CRUD + PDF export routes."""
from flask import Blueprint, jsonify, request

import idea_journal as _idea_journal
from auth import require_auth

bp = Blueprint("module_idea_journal", __name__)


def _user_id() -> str:
    user = getattr(request, "current_user", None) or {}
    return str(user.get("user_id") or user.get("username") or "")


@bp.route("/api/modules/<module_id>/idea-journal", methods=["GET"])
@require_auth
def list_idea_journal(module_id):
    user_id = _user_id()
    entries = _idea_journal.list_entries(user_id, module_id)
    return jsonify({"entries": entries})


@bp.route("/api/modules/<module_id>/idea-journal", methods=["POST"])
@require_auth
def post_idea_journal(module_id):
    user_id = _user_id()
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content required"}), 400
    entry = _idea_journal.append_entry(user_id, module_id, {
        "content": content[:5000],
        "type": (body.get("type") or "free_form")[:32],
        "lesson_id": body.get("lesson_id"),
        "lesson_title": body.get("lesson_title"),
    })
    return jsonify(entry)


@bp.route("/api/modules/<module_id>/idea-journal/<entry_id>", methods=["PATCH"])
@require_auth
def patch_idea_journal(module_id, entry_id):
    user_id = _user_id()
    body = request.get_json(silent=True) or {}
    if "content" in body:
        _idea_journal.edit_entry(user_id, module_id, entry_id, {"content": body["content"][:5000]})
    if "starred" in body:
        _idea_journal.star_entry(user_id, module_id, entry_id, bool(body["starred"]))
    entries = _idea_journal.list_entries(user_id, module_id)
    for e in entries:
        if e["entry_id"] == entry_id:
            return jsonify(e)
    return jsonify({"error": "not found"}), 404


@bp.get("/api/modules/<module_id>/idea-journal/export")
@require_auth
def export_idea_journal(module_id):
    from idea_journal_pdf import render_journal_pdf
    from datetime import datetime
    from flask import Response

    user_id = _user_id()
    try:
        import modules_engine
        module = modules_engine.get_module(module_id) or {}
    except Exception:
        module = {}
    try:
        from auth import get_user
        user = get_user(user_id) or {}
    except Exception:
        user = {}
    entries = _idea_journal.list_entries(user_id, module_id)
    pdf = render_journal_pdf(
        student_name=user.get("display_name") or user.get("username") or "Founder",
        module_title=module.get("title") or module_id,
        completion_date=datetime.now().strftime("%B %d, %Y"),
        entries=entries,
    )
    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="my-pitch-deck-{module_id}.pdf"',
    })
