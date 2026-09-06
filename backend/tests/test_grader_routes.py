"""HTTP-level characterization tests for routes/grader_routes.py.

The real `storage`/`game_storage` modules this blueprint depends on are not
present in this checkout (a pre-existing gap unrelated to the scoring-
registry refactor — `backend/app.py` itself cannot be imported here either).
So these tests stand up a minimal in-memory fake for both, register just
`grader_bp` on a bare Flask app, and drive it with the real test client.
This is also, notably, the only test coverage `grader_routes.py` has ever
had — there was no prior HTTP-level test for any of the 12 routes — so it
doubles as the regression guard for the dispatch-table refactor (each route
now resolves its engine via `_GRADER_REGISTRY` instead of a per-route
inline `from engines.X import Y`).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import types  # noqa: E402

import pytest  # noqa: E402


# ---- fake `storage` / `game_storage` modules, installed before the routes
#      module (which imports them at module scope) is ever imported ----

_RUNS = {}


def _fake_get_run(run_id):
    return _RUNS.get(run_id)


def _fake_update_run(run_id, run):
    _RUNS[run_id] = run


def _fake_load_game(game_id):
    return None


# These modules genuinely don't exist in this checkout (a pre-existing gap
# — `backend/app.py` can't be imported here either). We install throwaway
# stubs just long enough for `routes.grader_routes`'s module-level
# `from storage import get_run, update_run` (and `game_storage`) to bind
# names into ITS OWN namespace, then immediately remove the stubs from
# `sys.modules` again so later test files' `import storage` still see the
# same "genuinely missing" ModuleNotFoundError they saw before this file
# ran — otherwise every other test collected after this one in the same
# session would see our stub instead of the real absence.
_storage_was_missing = "storage" not in sys.modules
_game_storage_was_missing = "game_storage" not in sys.modules

if _storage_was_missing:
    _storage_stub = types.ModuleType("storage")
    _storage_stub.get_run = _fake_get_run
    _storage_stub.update_run = _fake_update_run
    sys.modules["storage"] = _storage_stub

if _game_storage_was_missing:
    _game_storage_stub = types.ModuleType("game_storage")
    _game_storage_stub.load_game = _fake_load_game
    sys.modules["game_storage"] = _game_storage_stub

from flask import Flask  # noqa: E402

from routes.grader_routes import grader_bp  # noqa: E402

if _storage_was_missing:
    del sys.modules["storage"]
if _game_storage_was_missing:
    del sys.modules["game_storage"]


@pytest.fixture
def client():
    _RUNS.clear()
    app = Flask(__name__)
    app.register_blueprint(grader_bp)
    app.testing = True
    return app.test_client()


def _seed_run(run_id: str, game: dict) -> None:
    _RUNS[run_id] = {"run_id": run_id, "game_id": "g1", "game": game, "state": {}, "log": []}


# ---- pendulum_lab (proximity_band via the registry) ----

def test_pendulum_lab_complete_success_shape(client):
    import math

    game = {
        "game_type": "pendulum_lab",
        "pendulum": {"true_g": 9.81, "scoring": {"tolerance_g": 0.3}},
    }
    _seed_run("run1", game)
    period = 2 * math.pi * math.sqrt(1.0 / 9.81)

    resp = client.post(
        "/api/run/run1/pendulum-lab/complete",
        json={"measurements": [{"length_m": 1.0, "period_s": period}]},
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    summary = body["summary"]
    assert summary["score"] == 100
    assert summary["band"] == "perfect"
    assert "dimension_scores" in summary

    # Run state was updated for the /report pipeline.
    assert _RUNS["run1"]["state"]["score"] == 100
    assert _RUNS["run1"]["state"]["completed"] is True


def test_pendulum_lab_wrong_game_type_400(client):
    _seed_run("run1", {"game_type": "optics_lab"})
    resp = client.post("/api/run/run1/pendulum-lab/complete", json={"measurements": []})
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "Wrong game type for this endpoint"
    assert body["expected"] == "pendulum_lab"
    assert body["actual"] == "optics_lab"


def test_pendulum_lab_missing_payload_key_400(client):
    _seed_run("run1", {"game_type": "pendulum_lab", "pendulum": {}})
    resp = client.post("/api/run/run1/pendulum-lab/complete", json={})
    assert resp.status_code == 400
    assert "Missing 'measurements'" in resp.get_json()["error"]


def test_run_not_found_404(client):
    resp = client.post("/api/run/nope/pendulum-lab/complete", json={"measurements": []})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "Run not found"


# ---- circuit_debugger (fraction_correct via the registry) ----

def test_circuit_debugger_complete_matches_direct_engine_call(client):
    from engines.circuit_debugger_engine import CircuitDebuggerEngine

    game = {"game_type": "circuit_debugger", "circuit": {"target_node_voltages": {"A": 5, "B": 0}}}
    _seed_run("run2", game)
    submission = {"node_voltages": {"A": 5.0, "B": 5.0}}

    resp = client.post("/api/run/run2/circuit-debugger/complete", json=submission)
    assert resp.status_code == 200
    summary = resp.get_json()["summary"]

    direct = CircuitDebuggerEngine(game).grade_results(submission["node_voltages"])
    assert summary == direct


# ---- sudoku (penalized_fraction via the registry) ----

def test_sudoku_complete_matches_direct_engine_call(client):
    from engines.sudoku_engine import SudokuEngine

    solution = [[1] * 9 for _ in range(9)]
    game = {"game_type": "sudoku", "solution": solution, "hint_penalty": 5}
    _seed_run("run3", game)
    submission = {"submission": {"grid": solution, "hints_used": 3}}

    resp = client.post("/api/run/run3/sudoku/complete", json=submission)
    assert resp.status_code == 200
    summary = resp.get_json()["summary"]

    direct = SudokuEngine(game).grade_results(submission["submission"])
    assert summary == direct


# ---- mental_math (speed_accuracy_factor via the registry) ----

def test_mental_math_complete_matches_direct_engine_call(client):
    from engines.mental_math_engine import MentalMathEngine

    game = {
        "game_type": "mental_math",
        "problems": [{"id": "p1", "answer": 4}, {"id": "p2", "answer": 9}],
        "time_target_s": 5.0,
    }
    _seed_run("run4", game)
    attempts = [
        {"id": "p1", "answer": 4, "elapsed_s": 5},
        {"id": "p2", "answer": 9, "elapsed_s": 5},
    ]

    resp = client.post("/api/run/run4/mental-math/complete", json={"attempts": attempts})
    assert resp.status_code == 200
    summary = resp.get_json()["summary"]

    direct = MentalMathEngine(game).grade_results(attempts)
    assert summary == direct


# ---- every route responds under its expected engine dispatch ----

@pytest.mark.parametrize("slug,game_type,payload_key,payload", [
    ("pendulum-lab", "pendulum_lab", "measurements", []),
    ("optics-lab", "optics_lab", "measurements", []),
    ("circuit-debugger", "circuit_debugger", "node_voltages", {}),
    ("genetics-cross", "genetics_cross", "predictions", {}),
    ("stoichiometry-mixer", "stoichiometry_mixer", "added_b_moles", 0),
    ("mental-math", "mental_math", "attempts", []),
    ("typing-drill", "typing_drill", "attempts", []),
    ("boggle", "boggle", "words", []),
    ("mock-interview", "mock_interview", "transcript", []),
    ("sudoku", "sudoku", "submission", {}),
    ("logic-grid", "logic_grid", "submission", []),
    ("geometry-constructor", "geometry_constructor", "points", {}),
])
def test_every_grader_route_dispatches_to_its_engine(client, slug, game_type, payload_key, payload):
    game = {"game_type": game_type}
    _seed_run("runX", game)
    resp = client.post(f"/api/run/runX/{slug}/complete", json={payload_key: payload})
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
