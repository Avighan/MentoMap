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
@require_auth
def card_png(module_id):
    from flask import Response
    from share_card import render_card
    from module_skill_report import build_report
    from auth import get_user_by_username

    user_id = _user_id()
    # Resolve display name (auth.get_user_by_username returns the user record).
    user = {}
    try:
        user = get_user_by_username(user_id) or {}
    except Exception:
        user = {}
    name_source = (
        user.get("display_name") or user.get("username") or user_id or "Founder"
    )
    name = str(name_source).split()[0] if name_source else "Founder"
    age = user.get("age") if isinstance(user, dict) else None
    report = build_report(user_id, module_id, runs=[])
    dims = report.get("dimensions") or {}
    if dims:
        top_k, top_v = sorted(dims.items(), key=lambda x: -x[1])[0]
    else:
        top_k, top_v = "strategic_thinking", 50
    headline = (
        f"{name} finished {report['module_title']}. "
        f"They scored {top_v} on {top_k.replace('_', ' ')}."
    )
    png = render_card(
        first_name=name,
        age=age,
        module_title=report["module_title"],
        dimensions=dims,
        headline=headline,
        cohort=user.get("cohort_name") if isinstance(user, dict) else None,
    )
    return Response(
        png,
        mimetype="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@bp.get("/api/modules/<module_id>/certificate")
@require_auth
def certificate(module_id):
    import modules_engine
    from certificate import generate_certificate_html
    from auth import get_user_by_username

    user_id = _user_id()
    status = modules_engine.check_module_completion(user_id, module_id)
    if not status["certificate_eligible"]:
        return jsonify({**status, "error": "module not complete"}), 409

    try:
        user = get_user_by_username(user_id) or {}
    except Exception:
        user = {}
    module = modules_engine.get_module(module_id) or {}
    player_name = (
        user.get("display_name")
        or user.get("username")
        or user_id
        or "Founder"
    )
    html = generate_certificate_html(
        player_name=player_name,
        game_title=module.get("title") or module_id,
        game_theme="Entrepreneurship Workshop",
        mento_score=100.0,
        mento_rank="A",
        badges=[],
        run_id=module_id,
    )
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}
