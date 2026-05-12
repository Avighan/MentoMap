"""Phase C: skill report + share-card + certificate routes."""
from flask import Blueprint, jsonify, request

from auth import require_auth

bp = Blueprint("module_skill_report", __name__)


def _user_id() -> str:
    user = getattr(request, "current_user", None) or {}
    return str(user.get("user_id") or user.get("username") or "")


@bp.get("/api/modules/<module_id>/skill-report")
@require_auth
def report(module_id):
    from module_skill_report import build_report
    import modules_engine

    user_id = _user_id()
    module = modules_engine.get_module(module_id) or {}
    game_ids = set()
    for w in module.get("weeks", []):
        for l in w.get("lessons", []):
            if l.get("game_id"):
                game_ids.add(l["game_id"])
            for g_ in (l.get("games") or []):
                if isinstance(g_, dict) and g_.get("id"):
                    game_ids.add(g_["id"])
    runs = []
    try:
        # Best-effort: storage.py has list_runs() for all runs; filter by user/game.
        from storage import list_runs
        for r in (list_runs() or []):
            if r.get("user_id") == user_id and r.get("game_id") in game_ids and r.get("report"):
                runs.append(r)
    except Exception:
        pass
    return jsonify(build_report(user_id, module_id, runs=runs))


@bp.get("/api/modules/<module_id>/skill-report/card.png")
def card_png(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501


@bp.get("/api/modules/<module_id>/certificate")
def certificate(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501
