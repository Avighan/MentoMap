"""
API routes for the HBR/CapSim-parity "operational" engines that ship
under engines/ but, like engine_routes.py's decision_panel/competitor_ai,
were never wired to a route: project_management_engine, finance_engine
(the mutation side of each — their read-only *_payload builders are
already composed by engines/executive_ux.py and wired into app.py).

Evidence:
  - engines/project_management_engine.py docstring: mutation helpers
    (update_task, add_raid, resolve_raid, advance_day) are "called by
    core/exec_effects.py" — a module that does not exist in this checkout,
    so nothing currently calls them.
  - engines/finance_engine.py: apply_funding_round / roll_forward_period
    are likewise plain functions with no caller anywhere in app.py or
    routes/ (grep confirms project_management_engine and finance_engine
    are imported ONLY from engines/executive_ux.py and from tests).
  - `grep -rn "generate-engine-config\|@app\.\(get\|post\)" app.py | grep -i
    engine` shows the only engine-shaped route already in app.py is the
    unrelated /api/admin/generate-engine-config admin tool — nothing for
    project_management or finance actions.

Confidence note: unlike engine_routes.py's /decision-panel (whose exact
path is spelled out in a frontend JSDoc comment), there is no frontend
call site for these — DecisionPanelWidget.jsx is the only exec-engine
widget with a documented route. The routes below are this module's best
reasonable inference of what "additional_engine_routes" should expose
given the unwired mutation helpers in these two engines, not a confirmed
frontend contract.

NOTE: like engine_routes.py, this module imports project_management_engine
and finance_engine directly (both pure-stdlib) rather than through
engines/executive_ux.py, which currently fails to import because it also
pulls in several engine modules (market_engine.py, org_engine.py, etc.)
that do not exist in this checkout.
"""
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from storage import get_run, update_run
from game_storage import load_game
from storage_interface import SessionNotFoundError, SessionExpiredError, StorageIOError

from engines.project_management_engine import (
    get_pm_config, build_pm_payload, update_task, add_raid, resolve_raid, advance_day,
)
from engines.finance_engine import (
    get_finance_config, build_finance_payload, apply_funding_round, roll_forward_period,
)


additional_engines_bp = Blueprint("additional_engines", __name__, url_prefix="/api/run")


class _StateProxy:
    """See routes/engine_routes.py's _StateProxy for the rationale — kept
    as a separate copy here so this module has no import-time dependency
    on that one."""

    def __init__(self, state):
        object.__setattr__(self, "_state", state)

    def __getattr__(self, name):
        state = object.__getattribute__(self, "_state")
        if isinstance(state, dict):
            if name in state:
                return state[name]
            raise AttributeError(name)
        return getattr(state, name)

    def __setattr__(self, name, value):
        state = object.__getattribute__(self, "_state")
        if isinstance(state, dict):
            state[name] = value
        else:
            setattr(state, name, value)


def _load_run(run_id: str):
    try:
        run = get_run(run_id)
    except SessionNotFoundError:
        return None, (jsonify({"error": "Run not found"}), 404)
    except SessionExpiredError:
        return None, (jsonify({"error": "Run has expired"}), 410)
    except StorageIOError as e:
        return None, (jsonify({"error": str(e)}), 500)

    if "game" not in run or run.get("game") is None:
        run["game"] = load_game(run.get("game_id", ""))
    if not run.get("game"):
        return None, (jsonify({"error": "Game data not found"}), 404)
    return run, None


def _state_and_proxy(run: Dict[str, Any]):
    if run.get("state") is None:
        run["state"] = dict((run["game"] or {}).get("initial_state") or {})
    state = run["state"]
    return state, _StateProxy(state)


# ==================== project management ====================

@additional_engines_bp.route("/<run_id>/pm/task", methods=["POST"])
def pm_update_task(run_id):
    run, err = _load_run(run_id)
    if err:
        return err
    if not get_pm_config(run["game"]):
        return jsonify({"error": "Game has no project_management configured"}), 400

    body = request.get_json(silent=True) or {}
    task_id = body.get("task_id")
    patch = body.get("patch")
    if not task_id or not isinstance(patch, dict):
        return jsonify({"error": "Missing 'task_id' or 'patch' (dict) in request body"}), 400

    _, proxy = _state_and_proxy(run)
    try:
        update_task(proxy, task_id, patch)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Task update failed: {e}"}), 500

    update_run(run_id, run)
    return jsonify({"success": True, "project_management": build_pm_payload(proxy, run["game"])})


@additional_engines_bp.route("/<run_id>/pm/raid/add", methods=["POST"])
def pm_raid_add(run_id):
    run, err = _load_run(run_id)
    if err:
        return err
    if not get_pm_config(run["game"]):
        return jsonify({"error": "Game has no project_management configured"}), 400

    body = request.get_json(silent=True) or {}
    category = body.get("category")
    items = body.get("items")
    if category not in ("risks", "assumptions", "issues", "dependencies"):
        return jsonify({"error": "'category' must be one of risks/assumptions/issues/dependencies"}), 400
    if not isinstance(items, list) or not items:
        return jsonify({"error": "Missing 'items' (non-empty list) in request body"}), 400

    _, proxy = _state_and_proxy(run)
    try:
        add_raid(proxy, category, items)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"RAID add failed: {e}"}), 500

    update_run(run_id, run)
    return jsonify({"success": True, "project_management": build_pm_payload(proxy, run["game"])})


@additional_engines_bp.route("/<run_id>/pm/raid/resolve", methods=["POST"])
def pm_raid_resolve(run_id):
    run, err = _load_run(run_id)
    if err:
        return err
    if not get_pm_config(run["game"]):
        return jsonify({"error": "Game has no project_management configured"}), 400

    body = request.get_json(silent=True) or {}
    category = body.get("category")
    ids = body.get("ids")
    if category not in ("risks", "assumptions", "issues", "dependencies"):
        return jsonify({"error": "'category' must be one of risks/assumptions/issues/dependencies"}), 400
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "Missing 'ids' (non-empty list) in request body"}), 400

    _, proxy = _state_and_proxy(run)
    try:
        resolve_raid(proxy, category, ids)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"RAID resolve failed: {e}"}), 500

    update_run(run_id, run)
    return jsonify({"success": True, "project_management": build_pm_payload(proxy, run["game"])})


@additional_engines_bp.route("/<run_id>/pm/advance-day", methods=["POST"])
def pm_advance_day(run_id):
    run, err = _load_run(run_id)
    if err:
        return err
    if not get_pm_config(run["game"]):
        return jsonify({"error": "Game has no project_management configured"}), 400

    body = request.get_json(silent=True) or {}
    days = body.get("days", 1)
    try:
        days = int(days)
    except (TypeError, ValueError):
        return jsonify({"error": "'days' must be an integer"}), 400

    _, proxy = _state_and_proxy(run)
    try:
        advance_day(proxy, days)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Advance day failed: {e}"}), 500

    update_run(run_id, run)
    return jsonify({"success": True, "project_management": build_pm_payload(proxy, run["game"])})


# ==================== finance ====================

@additional_engines_bp.route("/<run_id>/finance/roll-forward", methods=["POST"])
def finance_roll_forward(run_id):
    run, err = _load_run(run_id)
    if err:
        return err
    if not get_finance_config(run["game"]):
        return jsonify({"error": "Game has no finance configured"}), 400

    body = request.get_json(silent=True) or {}
    period_label = body.get("period_label")
    period_inputs = body.get("period_inputs")
    if period_inputs is not None and not isinstance(period_inputs, dict):
        return jsonify({"error": "'period_inputs' must be a dict when provided"}), 400

    _, proxy = _state_and_proxy(run)
    try:
        result = roll_forward_period(proxy, run["game"], period_label=period_label, period_inputs=period_inputs)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Roll-forward failed: {e}"}), 500

    update_run(run_id, run)
    return jsonify({
        "success": True,
        "period": result,
        "finance": build_finance_payload(proxy, run["game"]),
    })


@additional_engines_bp.route("/<run_id>/finance/funding-round", methods=["POST"])
def finance_funding_round(run_id):
    run, err = _load_run(run_id)
    if err:
        return err
    if not get_finance_config(run["game"]):
        return jsonify({"error": "Game has no finance configured"}), 400

    body = request.get_json(silent=True) or {}
    round_spec = body.get("round_spec")
    if not isinstance(round_spec, dict):
        return jsonify({"error": "Missing 'round_spec' (dict) in request body"}), 400

    _, proxy = _state_and_proxy(run)
    try:
        apply_funding_round(proxy, round_spec)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Funding round failed: {e}"}), 500

    update_run(run_id, run)
    return jsonify({"success": True, "finance": build_finance_payload(proxy, run["game"])})
