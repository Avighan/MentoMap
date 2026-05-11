"""Tests for POST /api/run/<id>/stocksim/phase (EOD pause/resume).

Validates the server-authoritative pause clock: when the frontend signals
"eod" or "weekend", the backend freezes current_tick advancement; when it
resumes ("playing"), the paused duration is added to paused_total_ms so the
elapsed-ticks math effectively skips that interval.
"""
import json
import os
import time
import pytest
import jwt
from app import app as flask_app
import storage
from auth import JWT_SECRET


# ---------------------------------------------------------------------------
# Auth helpers — mirrors test_stocksim_state_week.py
# ---------------------------------------------------------------------------

def _make_token(user_id: str = "test-user-1", role: str = "student") -> str:
    payload = {
        "user_id": user_id,
        "username": user_id,
        "role": role,
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _auth_headers(user_id: str = "test-user-1", role: str = "student") -> dict:
    return {"Authorization": f"Bearer {_make_token(user_id, role)}"}


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def _write_run_to_disk(run_id: str, run_data: dict):
    from datetime import datetime
    run_data = dict(run_data)
    run_data.setdefault("last_accessed", datetime.now().isoformat())
    file_path = os.path.join(storage.STORAGE_DIR, f"{run_id}.json")
    with open(file_path, "w") as f:
        json.dump(run_data, f)
    return file_path


# ---------------------------------------------------------------------------
# Run fixture — points at stock-market-simulator (week-mode game).
# ---------------------------------------------------------------------------

@pytest.fixture
def week_run():
    run_id = "test-pause-stocksim-run-001"
    run_data = {
        "run_id": run_id,
        "user_id": "test-user-1",
        "game_id": "stock-market-simulator",
    }
    file_path = _write_run_to_disk(run_id, run_data)
    yield run_id
    storage.RUNS.pop(run_id, None)
    storage.RUNS_MTIME.pop(run_id, None)
    if os.path.exists(file_path):
        os.remove(file_path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_phase_endpoint_rejects_invalid_phase(client, week_run):
    """An unknown phase string must yield 400 with error 'invalid_phase'."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    resp = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "garbage"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 400, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body.get("error") == "invalid_phase", body


def test_phase_endpoint_returns_404_for_unknown_run(client):
    """Posting against an unknown run_id must return 404 (not 500/400)."""
    resp = client.post(
        "/api/run/this-run-does-not-exist-xyz/stocksim/phase",
        json={"phase": "eod"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404, resp.get_data(as_text=True)


def test_phase_endpoint_eod_sets_paused_at_ms(client, week_run):
    """POST {phase:'eod'} must set paused_at_ms > 0 and phase=='eod' in state."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    resp = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "eod"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body.get("phase") == "eod"
    assert body.get("paused_at_ms", 0) > 0

    # Re-read the run from storage and verify persistence.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    assert sim.get("phase") == "eod"
    assert int(sim.get("paused_at_ms", 0)) > 0


def test_phase_endpoint_eod_is_idempotent(client, week_run):
    """Two consecutive eod calls must preserve the first paused_at_ms."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    r1 = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "eod"},
        headers=_auth_headers(),
    )
    assert r1.status_code == 200
    first_paused_at = r1.get_json().get("paused_at_ms", 0)
    assert first_paused_at > 0

    # Sleep so that wall-clock advances; if we re-stamped paused_at_ms,
    # the second call would return a strictly larger value.
    time.sleep(0.05)

    r2 = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "eod"},
        headers=_auth_headers(),
    )
    assert r2.status_code == 200
    second_paused_at = r2.get_json().get("paused_at_ms", 0)
    assert second_paused_at == first_paused_at, (
        f"paused_at_ms must not be re-stamped on repeated eod; "
        f"first={first_paused_at}, second={second_paused_at}"
    )


def test_phase_endpoint_resume_increments_paused_total_ms_and_clears_paused_at_ms(client, week_run):
    """Resuming 'playing' must add the paused duration to paused_total_ms and clear paused_at_ms."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    # 1) pause
    r1 = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "eod"},
        headers=_auth_headers(),
    )
    assert r1.status_code == 200
    paused_at = r1.get_json().get("paused_at_ms", 0)
    assert paused_at > 0

    # 2) wait so a measurable delta accrues
    time.sleep(0.05)

    # 3) resume
    r2 = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "playing"},
        headers=_auth_headers(),
    )
    assert r2.status_code == 200, r2.get_data(as_text=True)
    body = r2.get_json()
    assert body.get("phase") == "playing"
    assert body.get("paused_at_ms", -1) == 0, f"paused_at_ms must be cleared on resume: {body}"
    assert body.get("paused_total_ms", 0) > 0, (
        f"paused_total_ms should have accumulated the eod window: {body}"
    )

    # Verify on disk too.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    assert sim.get("phase") == "playing"
    assert int(sim.get("paused_at_ms", 0)) == 0
    assert int(sim.get("paused_total_ms", 0)) > 0


def test_paused_state_response_does_not_advance_current_tick(client, week_run):
    """While paused, /state must NOT advance current_tick and must echo phase/paused."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    # Pin started_at_ms ~25s in the past so without pause, with 8s tick_interval,
    # the lazy clock would advance to tick ~3. Then pause and verify it stops.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    now_ms = int(time.time() * 1000)
    sim["started_at_ms"] = now_ms - 25_000  # 25s ago → would be tick 3 at 8s/tick
    sim["current_tick"] = 0
    storage.update_run(week_run, run)

    # Pause immediately. The pause endpoint should freeze further advancement.
    pr = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "eod"},
        headers=_auth_headers(),
    )
    assert pr.status_code == 200

    # First /state call right after pause — capture current_tick. The invariant
    # under test: once paused, the in-flight `(now_ms - paused_at)` correction
    # in stocksim_state cancels the growing `(now_ms - started_at)` term, so
    # current_tick stays flat across repeated /state reads while paused.
    s1 = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    assert s1.status_code == 200
    body1 = s1.get_json()
    tick_at_pause = body1["state"]["current_tick"]
    assert body1.get("phase") == "eod"
    assert body1.get("paused") is True

    # Sleep > 1 tick interval (8s) — but we don't want a slow test, so use a
    # shorter sleep and verify the *relative* invariant: tick doesn't grow.
    time.sleep(0.5)

    s2 = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    assert s2.status_code == 200
    body2 = s2.get_json()
    assert body2["state"]["current_tick"] == tick_at_pause, (
        f"current_tick must not advance while paused: "
        f"was {tick_at_pause}, became {body2['state']['current_tick']}"
    )
    assert body2.get("phase") == "eod"
    assert body2.get("paused") is True


def test_state_includes_phase_default_playing(client, week_run):
    """On a fresh start (no phase stored), /state must default to phase='playing', paused=False."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    # Make sure no phase has been set.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    sim.pop("phase", None)
    sim.pop("paused_at_ms", None)
    sim["started_at_ms"] = int(time.time() * 1000)  # freeze clock
    storage.update_run(week_run, run)

    resp = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body.get("phase") == "playing", f"default phase must be 'playing': {body.get('phase')}"
    assert body.get("paused") is False, f"default paused must be False: {body.get('paused')}"


def test_phase_endpoint_resume_when_not_paused_is_noop(client, week_run):
    """POST {phase:'playing'} on a fresh run (never paused) must not mutate the
    counters; only `phase` updates. Documented no-op for resume-without-prior-pause."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    # Ensure no pause state exists.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    sim.pop("phase", None)
    sim["paused_at_ms"] = 0
    sim["paused_total_ms"] = 0
    storage.update_run(week_run, run)

    r = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "playing"},
        headers=_auth_headers(),
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body.get("phase") == "playing"
    assert body.get("paused_at_ms", -1) == 0, f"paused_at_ms must remain 0: {body}"
    assert body.get("paused_total_ms", -1) == 0, f"paused_total_ms must remain 0: {body}"

    # Verify on disk.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    assert sim.get("phase") == "playing"
    assert int(sim.get("paused_at_ms", 0)) == 0
    assert int(sim.get("paused_total_ms", 0)) == 0


def test_phase_endpoint_forbidden_for_other_user(client, week_run):
    """A non-owner without admin/teacher/school_admin role must get 403."""
    r = client.post(
        f"/api/run/{week_run}/stocksim/phase",
        json={"phase": "eod"},
        headers=_auth_headers(user_id="someone-else", role="student"),
    )
    assert r.status_code == 403, r.get_data(as_text=True)
    body = r.get_json() or {}
    assert "Not authorized" in (body.get("error") or "")
