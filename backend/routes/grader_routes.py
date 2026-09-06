"""
API routes for the 12 grader engines added in the audit-followup batch.

Each route follows the music_match / lab_titration pattern:
  1. validate run + game_type
  2. load engine, call grade_results / grade_result
  3. write `dimension_scores` onto the run state so the existing
     /report pipeline picks them up unchanged

Blueprint URL prefix: /api/run — final routes are
  POST /api/run/<run_id>/<engine-name>/complete

Dispatch is table-driven via `_GRADER_REGISTRY` below instead of each
route inlining its own `from engines.X import Y` + `_grade(...)` call.
Adding a new grader is a matter of adding one registry entry and one
thin route function — no changes to `_grade`, `_load_run`, or `_record`
are ever needed for a new engine. The URL surface (one decorator per
engine) is kept exactly as before so route matching / 404 behavior for
every existing path is unchanged.
"""
import importlib
from typing import Any, Dict

from flask import Blueprint, jsonify, request

from storage import get_run, update_run
from game_storage import load_game


grader_bp = Blueprint("grader", __name__, url_prefix="/api/run")


def _load_run(run_id: str):
    run = get_run(run_id)
    if not run:
        return None, (jsonify({"error": "Run not found"}), 404)
    if "game" not in run or run["game"] is None:
        run["game"] = load_game(run.get("game_id", ""))
    if not run.get("game"):
        return None, (jsonify({"error": "Game data not found"}), 404)
    return run, None


def _expect_game_type(run: Dict[str, Any], expected: str):
    actual = (run.get("game") or {}).get("game_type")
    if actual != expected:
        return jsonify({
            "error": "Wrong game type for this endpoint",
            "expected": expected,
            "actual": actual,
        }), 400
    return None


def _expect_game_id(run: Dict[str, Any], expected: str):
    """Same idea as `_expect_game_type` but keyed on `game_id`.

    The three pilot games below each have a bespoke `game_type` in their
    JSON (dealcraft.json: "rounds", mumbai_manufacturer.json:
    "business_simulation_settlement", heliogrid.json:
    "continuous_lever_simulation") that doesn't match the pilot name used
    for dispatch here — `game_id` does match exactly in all three cases,
    so that's the field these routes actually key on.
    """
    actual = (run.get("game") or {}).get("game_id")
    if actual != expected:
        return jsonify({
            "error": "Wrong game for this endpoint",
            "expected": expected,
            "actual": actual,
        }), 400
    return None


def _record(run: Dict[str, Any], game_type: str, summary: Dict[str, Any]) -> None:
    """Write the engine's grading result into run state so /report picks it up."""
    state_obj = run.setdefault("state", {})
    if isinstance(state_obj, dict):
        state_obj["dimension_scores"] = summary.get("dimension_scores", {})
        state_obj["score"] = summary.get("score", 0)
        state_obj["completed"] = True
    else:
        # state may be a typed object — try attribute setters
        try:
            setattr(state_obj, "dimension_scores", summary.get("dimension_scores", {}))
            setattr(state_obj, "score", summary.get("score", 0))
            setattr(state_obj, "completed", True)
        except Exception:
            pass

    log = run.setdefault("log", [])
    log.append({
        "type": "engine_complete",
        "game_type": game_type,
        "summary": summary,
    })


def _grade(run_id: str, game_type: str, engine_factory, payload_key: str,
           method_name: str = "grade_results"):
    """Shared run-and-record harness for all 12 graders.

    `engine_factory` takes a game-config dict and returns the engine
    instance. `payload_key` is the field on the request body containing
    the user's submission. `method_name` is `grade_results` for most
    engines, `grade_result` for lab_titration / stoichiometry.
    """
    run, err = _load_run(run_id)
    if err:
        return err
    err = _expect_game_type(run, game_type)
    if err:
        return err

    body = request.get_json(silent=True) or {}
    submission = body.get(payload_key)
    if submission is None:
        return jsonify({"error": f"Missing '{payload_key}' in request body"}), 400

    try:
        engine = engine_factory(run["game"])
        method = getattr(engine, method_name)
        summary = method(submission)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Grader failed: {e}"}), 500

    _record(run, game_type, summary)
    update_run(run_id, run)
    return jsonify({"success": True, "summary": summary})


# ==================== engine registry ====================
#
# One entry per grader engine: which module/class to instantiate with the
# game config, which request-body field carries the submission, and which
# method to call to grade it. `_dispatch` resolves an entry lazily (same
# lazy-import timing the old per-route `from engines.X import Y` had) and
# hands off to the shared `_grade` harness above.

_GRADER_REGISTRY: Dict[str, Dict[str, Any]] = {
    "pendulum_lab": {
        "module": "engines.pendulum_lab_engine", "class_name": "PendulumLabEngine",
        "payload_key": "measurements",
    },
    "optics_lab": {
        "module": "engines.optics_lab_engine", "class_name": "OpticsLabEngine",
        "payload_key": "measurements",
    },
    "circuit_debugger": {
        "module": "engines.circuit_debugger_engine", "class_name": "CircuitDebuggerEngine",
        "payload_key": "node_voltages",
    },
    "genetics_cross": {
        "module": "engines.genetics_cross_engine", "class_name": "GeneticsCrossEngine",
        "payload_key": "predictions",
    },
    "stoichiometry_mixer": {
        "module": "engines.stoichiometry_mixer_engine", "class_name": "StoichiometryMixerEngine",
        "payload_key": "added_b_moles",
    },
    "mental_math": {
        "module": "engines.mental_math_engine", "class_name": "MentalMathEngine",
        "payload_key": "attempts",
    },
    "typing_drill": {
        "module": "engines.typing_drill_engine", "class_name": "TypingDrillEngine",
        "payload_key": "attempts",
    },
    "boggle": {
        "module": "engines.boggle_engine", "class_name": "BoggleEngine",
        "payload_key": "words",
    },
    "mock_interview": {
        "module": "engines.mock_interview_engine", "class_name": "MockInterviewEngine",
        "payload_key": "transcript",
    },
    "sudoku": {
        "module": "engines.sudoku_engine", "class_name": "SudokuEngine",
        "payload_key": "submission",
    },
    "logic_grid": {
        "module": "engines.logic_grid_engine", "class_name": "LogicGridEngine",
        "payload_key": "submission",
    },
    "geometry_constructor": {
        "module": "engines.geometry_constructor_engine", "class_name": "GeometryConstructorEngine",
        "payload_key": "points",
    },
}


def _dispatch(run_id: str, game_type: str):
    """Resolve `game_type`'s registry entry and run it through `_grade`.

    Kept separate from each route function so a new grader only needs a
    registry entry + a one-line route — never a change to how dispatch
    itself works.
    """
    entry = _GRADER_REGISTRY[game_type]
    module = importlib.import_module(entry["module"])
    engine_class = getattr(module, entry["class_name"])
    return _grade(
        run_id, game_type, engine_class, entry["payload_key"],
        entry.get("method_name", "grade_results"),
    )


# ==================== STEM LAB ENGINES ====================

@grader_bp.route("/<run_id>/pendulum-lab/complete", methods=["POST"])
def pendulum_lab_complete(run_id):
    return _dispatch(run_id, "pendulum_lab")


@grader_bp.route("/<run_id>/optics-lab/complete", methods=["POST"])
def optics_lab_complete(run_id):
    return _dispatch(run_id, "optics_lab")


@grader_bp.route("/<run_id>/circuit-debugger/complete", methods=["POST"])
def circuit_debugger_complete(run_id):
    return _dispatch(run_id, "circuit_debugger")


@grader_bp.route("/<run_id>/genetics-cross/complete", methods=["POST"])
def genetics_cross_complete(run_id):
    return _dispatch(run_id, "genetics_cross")


@grader_bp.route("/<run_id>/stoichiometry-mixer/complete", methods=["POST"])
def stoichiometry_mixer_complete(run_id):
    return _dispatch(run_id, "stoichiometry_mixer")


# ==================== SKILL-DRILL ENGINES ====================

@grader_bp.route("/<run_id>/mental-math/complete", methods=["POST"])
def mental_math_complete(run_id):
    return _dispatch(run_id, "mental_math")


@grader_bp.route("/<run_id>/typing-drill/complete", methods=["POST"])
def typing_drill_complete(run_id):
    return _dispatch(run_id, "typing_drill")


@grader_bp.route("/<run_id>/boggle/complete", methods=["POST"])
def boggle_complete(run_id):
    return _dispatch(run_id, "boggle")


@grader_bp.route("/<run_id>/mock-interview/complete", methods=["POST"])
def mock_interview_complete(run_id):
    # Mock interview optionally accepts an injected LLM callable; the
    # registry instantiates `MockInterviewEngine(game)` with the default
    # `llm_callable=None`, same as the lambda this route used to pass in —
    # the engine attempts its own lazy `llm` import and falls back to a
    # heuristic score if unavailable.
    return _dispatch(run_id, "mock_interview")


# ==================== LOGIC PUZZLE ENGINES ====================

@grader_bp.route("/<run_id>/sudoku/complete", methods=["POST"])
def sudoku_complete(run_id):
    return _dispatch(run_id, "sudoku")


@grader_bp.route("/<run_id>/logic-grid/complete", methods=["POST"])
def logic_grid_complete(run_id):
    return _dispatch(run_id, "logic_grid")


@grader_bp.route("/<run_id>/geometry-constructor/complete", methods=["POST"])
def geometry_constructor_complete(run_id):
    return _dispatch(run_id, "geometry_constructor")


# ==================== PHASE 1 PILOT GAMES ====================
#
# Dealcraft, Mumbai Manufacturer, and HelioGrid are multi-round/continuous-
# lever simulations, not the single-shot "submit everything, grade once"
# shape the STEM/skill-drill engines above share. Each round (or quarter)
# needs its own progression call before a final score can be computed, so
# these get their own route shape instead of being forced through
# `_dispatch`/`_grade`: a per-game "advance" endpoint that applies one
# round/quarter and persists the resulting state, plus one route generic
# to game_type — `/api/run/<run_id>/complete` — that scores whatever state
# has accumulated by then. All three engine modules live under
# `backend/games/` (not `backend/engines/`) since each pairs one specific
# game's JSON with the Python that plays it; see
# `games/{dealcraft,mumbai_manufacturer,heliogrid}_engine.py`.
#
# NOTE: these routes are written to the same `get_run`/`update_run`
# contract every other route in this module already depends on, but they
# have not been exercised end-to-end through Flask in this checkout —
# `storage.py` (imported at the top of this file) does not exist in this
# repo on any branch, so `from routes.grader_routes import grader_bp`
# itself cannot succeed here yet. The engine modules they call are fully
# unit-tested directly (see backend/tests/test_dealcraft.py,
# test_mumbai_manufacturer.py, test_heliogrid.py) without going through
# Flask at all.

_PILOT_GAME_MODULES = {
    "dealcraft": "games.dealcraft_engine",
    "mumbai_manufacturer": "games.mumbai_manufacturer_engine",
    "heliogrid": "games.heliogrid_engine",
}


def _pilot_engine(game_type: str):
    if game_type not in _PILOT_GAME_MODULES:
        return None
    return importlib.import_module(_PILOT_GAME_MODULES[game_type])


@grader_bp.route("/<run_id>/dealcraft/choose", methods=["POST"])
def dealcraft_choose(run_id):
    run, err = _load_run(run_id)
    if err:
        return err
    err = _expect_game_id(run, "dealcraft")
    if err:
        return err

    body = request.get_json(silent=True) or {}
    round_id, choice_id = body.get("round_id"), body.get("choice_id")
    if not round_id or not choice_id:
        return jsonify({"error": "Missing 'round_id' or 'choice_id' in request body"}), 400

    engine = _pilot_engine("dealcraft")
    state = run.setdefault("state", dict(run["game"]["initial_state"]))
    try:
        new_state = engine.apply_choice(state, run["game"], round_id, choice_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    run["state"] = new_state
    update_run(run_id, run)
    return jsonify({"success": True, "state": new_state})


@grader_bp.route("/<run_id>/mumbai_manufacturer/choose", methods=["POST"])
def mumbai_manufacturer_choose(run_id):
    """Apply one round's choice, then (if one is scheduled after this
    round) apply the scheduled crisis event's choice in the same call —
    the frontend surfaces the event as part of that round's resolution,
    so there's one round-trip per round rather than two.
    """
    run, err = _load_run(run_id)
    if err:
        return err
    err = _expect_game_id(run, "mumbai_manufacturer")
    if err:
        return err

    body = request.get_json(silent=True) or {}
    round_id, choice_id = body.get("round_id"), body.get("choice_id")
    event_choice_id = body.get("event_choice_id")
    if not round_id or not choice_id:
        return jsonify({"error": "Missing 'round_id' or 'choice_id' in request body"}), 400

    engine = _pilot_engine("mumbai_manufacturer")
    state = run.setdefault("state", dict(run["game"]["initial_state"]))
    try:
        new_state = engine.apply_choice(state, run["game"], round_id, choice_id)
        event = engine.event_after_round(run["game"], round_id)
        if event is not None:
            if not event_choice_id:
                return jsonify({
                    "error": f"Round '{round_id}' has a scheduled event; missing 'event_choice_id'",
                    "event": event,
                }), 400
            new_state = engine.apply_event(new_state, run["game"], round_id, event_choice_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    run["state"] = new_state
    update_run(run_id, run)
    return jsonify({"success": True, "state": new_state})


@grader_bp.route("/<run_id>/heliogrid/quarter", methods=["POST"])
def heliogrid_quarter(run_id):
    run, err = _load_run(run_id)
    if err:
        return err
    err = _expect_game_id(run, "heliogrid")
    if err:
        return err

    body = request.get_json(silent=True) or {}
    action = body.get("action")
    if not isinstance(action, dict):
        return jsonify({"error": "Missing 'action' object in request body"}), 400

    engine = _pilot_engine("heliogrid")
    state = run.setdefault("state", engine.load_game()["initial_state"])
    quarter_index = len(state.get("csat_history") or [])
    try:
        engine.validate_action(action, run["game"])
        new_state = engine.resolve_quarter(state, action, quarter_index, run["game"])
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    run["state"] = new_state
    update_run(run_id, run)
    return jsonify({"success": True, "state": new_state, "quarter_result": new_state.get("_last_quarter_result")})


@grader_bp.route("/<run_id>/complete", methods=["POST"])
def pilot_game_complete(run_id):
    """Generic completion route for any of the three pilot games — the
    STEM-drill routes above stay per-engine (`/<engine>/complete`) since
    each has a different `payload_key`; these three all just score
    whatever `run['state']` has accumulated through the /choose or
    /quarter calls above, so one route dispatching on game_type covers
    all three without three near-identical route bodies.
    """
    run, err = _load_run(run_id)
    if err:
        return err

    # Dispatch on game_id, not game_type — see _expect_game_id's docstring:
    # each pilot game's own game_type doesn't match its pilot name.
    game_id = (run.get("game") or {}).get("game_id")
    engine = _pilot_engine(game_id)
    if engine is None:
        return jsonify({
            "error": "Not a pilot game run",
            "actual_game_type": (run.get("game") or {}).get("game_type"),
            "expected_one_of": sorted(_PILOT_GAME_MODULES),
        }), 400

    state = run.get("state")
    if not state:
        return jsonify({"error": "Run has no state yet — play at least one round/quarter first"}), 400

    try:
        result = engine.score_run(state, run["game"])
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"Scoring failed: {e}"}), 500

    summary = result.as_dict()
    _record(run, game_id, summary)
    update_run(run_id, run)
    return jsonify({"success": True, "summary": summary})
