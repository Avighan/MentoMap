"""
API routes for the 12 grader engines added in the audit-followup batch.

Each route follows the music_match / lab_titration pattern:
  1. validate run + game_type
  2. load engine, call grade_results / grade_result
  3. write `dimension_scores` onto the run state so the existing
     /report pipeline picks them up unchanged

Blueprint URL prefix: /api/run — final routes are
  POST /api/run/<run_id>/<engine-name>/complete
"""
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


# ==================== STEM LAB ENGINES ====================

@grader_bp.route("/<run_id>/pendulum-lab/complete", methods=["POST"])
def pendulum_lab_complete(run_id):
    from engines.pendulum_lab_engine import PendulumLabEngine
    return _grade(run_id, "pendulum_lab", PendulumLabEngine, "measurements")


@grader_bp.route("/<run_id>/optics-lab/complete", methods=["POST"])
def optics_lab_complete(run_id):
    from engines.optics_lab_engine import OpticsLabEngine
    return _grade(run_id, "optics_lab", OpticsLabEngine, "measurements")


@grader_bp.route("/<run_id>/circuit-debugger/complete", methods=["POST"])
def circuit_debugger_complete(run_id):
    from engines.circuit_debugger_engine import CircuitDebuggerEngine
    return _grade(run_id, "circuit_debugger", CircuitDebuggerEngine, "node_voltages")


@grader_bp.route("/<run_id>/genetics-cross/complete", methods=["POST"])
def genetics_cross_complete(run_id):
    from engines.genetics_cross_engine import GeneticsCrossEngine
    return _grade(run_id, "genetics_cross", GeneticsCrossEngine, "predictions")


@grader_bp.route("/<run_id>/stoichiometry-mixer/complete", methods=["POST"])
def stoichiometry_mixer_complete(run_id):
    from engines.stoichiometry_mixer_engine import StoichiometryMixerEngine
    return _grade(run_id, "stoichiometry_mixer", StoichiometryMixerEngine,
                  "added_b_moles", method_name="grade_results")


# ==================== SKILL-DRILL ENGINES ====================

@grader_bp.route("/<run_id>/mental-math/complete", methods=["POST"])
def mental_math_complete(run_id):
    from engines.mental_math_engine import MentalMathEngine
    return _grade(run_id, "mental_math", MentalMathEngine, "attempts")


@grader_bp.route("/<run_id>/typing-drill/complete", methods=["POST"])
def typing_drill_complete(run_id):
    from engines.typing_drill_engine import TypingDrillEngine
    return _grade(run_id, "typing_drill", TypingDrillEngine, "attempts")


@grader_bp.route("/<run_id>/boggle/complete", methods=["POST"])
def boggle_complete(run_id):
    from engines.boggle_engine import BoggleEngine
    return _grade(run_id, "boggle", BoggleEngine, "words")


@grader_bp.route("/<run_id>/mock-interview/complete", methods=["POST"])
def mock_interview_complete(run_id):
    from engines.mock_interview_engine import MockInterviewEngine
    # Mock interview optionally accepts an injected LLM callable; here we
    # pass None and let the engine attempt its lazy llm import + fall back
    # to heuristic if unavailable.
    return _grade(run_id, "mock_interview",
                  lambda game: MockInterviewEngine(game), "transcript")


# ==================== LOGIC PUZZLE ENGINES ====================

@grader_bp.route("/<run_id>/sudoku/complete", methods=["POST"])
def sudoku_complete(run_id):
    from engines.sudoku_engine import SudokuEngine
    return _grade(run_id, "sudoku", SudokuEngine, "submission")


@grader_bp.route("/<run_id>/logic-grid/complete", methods=["POST"])
def logic_grid_complete(run_id):
    from engines.logic_grid_engine import LogicGridEngine
    return _grade(run_id, "logic_grid", LogicGridEngine, "submission")


@grader_bp.route("/<run_id>/geometry-constructor/complete", methods=["POST"])
def geometry_constructor_complete(run_id):
    from engines.geometry_constructor_engine import GeometryConstructorEngine
    return _grade(run_id, "geometry_constructor", GeometryConstructorEngine, "points")
