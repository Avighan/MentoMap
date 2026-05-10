"""Tests for POST /api/run/<run_id>/reflection — Task 12 of P0 plan."""
import pytest


@pytest.fixture
def client(monkeypatch):
    # Disable LLM real calls
    monkeypatch.setenv("MODEL_PROVIDER", "")
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def _seed_run(run_id="run_test_reflection"):
    """Insert a fake run via storage.update_run so get_run() can find it (mtime-cached)."""
    from storage import update_run
    run_data = {
        "run_id": run_id,
        "game_id": "test_game",
        "state": {},
        "game": {"focus_dimensions": ["empathy", "strategic_thinking"]},
        "reflections": [],
    }
    update_run(run_id, run_data)
    return run_id


def test_reflection_endpoint_attaches_signals(client, monkeypatch):
    monkeypatch.setattr("llm.grade_reflection_text", lambda t, dimension_focus=None: {
        "score": 70,
        "dim_signals": {"empathy": 6},
        "strengths": ["Considered the team"],
        "improvements": [],
    })
    run_id = _seed_run()
    rv = client.post(f"/api/run/{run_id}/reflection", json={
        "round_id": "round_1",
        "choice_id": "c_a",
        "rationale": "I prioritized the team over the deadline.",
    })
    assert rv.status_code == 200, rv.get_data(as_text=True)
    body = rv.get_json()
    assert body["score"] == 70
    assert body["dim_signals"]["empathy"] == 6


def test_reflection_endpoint_400_on_empty_rationale(client):
    run_id = _seed_run("run_empty_test")
    rv = client.post(f"/api/run/{run_id}/reflection", json={"rationale": "   "})
    assert rv.status_code == 400


def test_reflection_endpoint_404_on_missing_run(client):
    rv = client.post("/api/run/run_does_not_exist/reflection", json={"rationale": "x"})
    assert rv.status_code == 404


def test_reflection_persisted_to_run(client, monkeypatch):
    monkeypatch.setattr("llm.grade_reflection_text", lambda t, dimension_focus=None: {
        "score": 55, "dim_signals": {}, "strengths": [], "improvements": [],
    })
    run_id = _seed_run("run_persist_test")
    rv = client.post(f"/api/run/{run_id}/reflection", json={
        "round_id": "r1", "choice_id": "c1", "rationale": "Some reasoning here.",
    })
    assert rv.status_code == 200
    from storage import RUNS
    refls = RUNS[run_id].get("reflections", [])
    assert len(refls) == 1
    assert refls[0]["round_id"] == "r1"
    assert refls[0]["graded"]["score"] == 55
