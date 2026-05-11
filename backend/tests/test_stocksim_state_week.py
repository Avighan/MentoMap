"""Tests for /api/run/<id>/stocksim/state week-format enrichment fields.

Covers the ``day``, ``today_pnl``, and ``pending_earnings`` keys added by
the week-format enrichment block in the stocksim_state route.
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
# Auth helpers — mirrors test_stocksim_routes.py exactly
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
# Week-format run fixture — points at stock-market-simulator (week-mode game)
# ---------------------------------------------------------------------------

@pytest.fixture
def week_run():
    """Create a run pointing at stock-market-simulator, start the session, and yield run_id."""
    run_id = "test-week-stocksim-run-001"
    run_data = {
        "run_id": run_id,
        "user_id": "test-user-1",
        "game_id": "stock-market-simulator",
        # 'game' key is loaded from disk by the route via get_game_or_400 — not needed inline.
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

def test_week_state_day_on_fresh_run(client, week_run):
    """Fresh run (current_tick=0) must return day.id == 'mon' and day.of == 5."""
    # Start session
    start_resp = client.post(f"/api/run/{week_run}/stocksim/start", json={},
                             headers=_auth_headers())
    assert start_resp.status_code == 200, start_resp.get_data(as_text=True)

    # Pin started_at_ms to now so lazy-tick advance stays at tick 0.
    run = storage.get_run(week_run)
    run["stocksim"]["started_at_ms"] = int(time.time() * 1000)
    storage.update_run(week_run, run)

    resp = client.get(f"/api/run/{week_run}/stocksim/state",
                      headers=_auth_headers())
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()

    assert "day" in body, f"'day' key missing from response: {list(body.keys())}"
    assert body["day"]["id"] == "mon"
    assert body["day"]["of"] == 5


def test_week_state_pending_earnings_non_empty_and_has_required_keys(client, week_run):
    """pending_earnings must be a non-empty list with symbol/day/headline on a fresh run."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    run = storage.get_run(week_run)
    run["stocksim"]["started_at_ms"] = int(time.time() * 1000)
    storage.update_run(week_run, run)

    resp = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.get_json()

    assert "pending_earnings" in body, f"'pending_earnings' missing: {list(body.keys())}"
    pe = body["pending_earnings"]
    assert isinstance(pe, list)
    assert len(pe) > 0, "pending_earnings should be non-empty on a fresh run (TECHN is on tue)"

    for entry in pe:
        assert "symbol" in entry, f"Entry missing 'symbol': {entry}"
        assert "day" in entry, f"Entry missing 'day': {entry}"
        assert "headline" in entry, f"Entry missing 'headline': {entry}"


def test_week_state_today_pnl_has_required_keys(client, week_run):
    """today_pnl must be a dict with numeric realized/unrealized/total."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    run = storage.get_run(week_run)
    run["stocksim"]["started_at_ms"] = int(time.time() * 1000)
    storage.update_run(week_run, run)

    resp = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.get_json()

    assert "today_pnl" in body, f"'today_pnl' missing: {list(body.keys())}"
    tp = body["today_pnl"]
    assert isinstance(tp, dict)
    for key in ("realized", "unrealized", "total"):
        assert key in tp, f"today_pnl missing '{key}': {tp}"
        assert isinstance(tp[key], (int, float)), f"today_pnl['{key}'] is not numeric: {tp[key]}"


def test_week_state_day_advances_to_tue(client, week_run):
    """When state is pinned at tick 4 (start of Tuesday), day.id must be 'tue'."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    # The first day (mon) has 4 ticks, so tick=4 is the first tick of Tuesday.
    # Pin started_at_ms to now and manually set current_tick=4 so the lazy
    # advance does not move backward (target_tick is computed as elapsed_ticks
    # from started_at_ms — with interval_seconds=0 this is 0, but current_tick
    # is already >= 0, so we rely on the route not clamping DOWN).
    # We use the same technique as test_stocksim_routes.py: set started_at_ms
    # to a time far in the past so elapsed_ticks >> current_tick, but we also
    # set current_tick directly so the engine's advance_to_tick lands at tick 4.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    # Set tick_interval_seconds to 0 means infinite speed — elapsed_ticks will be
    # max(interval,1)=1ms per tick so we need a large elapsed ms.
    # Simpler: set current_tick to 4 directly and freeze the clock so advance won't
    # roll beyond it (set started_at_ms so that target_tick == 4).
    sim["current_tick"] = 4
    # Freeze the clock: started_at_ms = now, tick_interval_seconds effectively
    # means elapsed_ticks = 0 < current_tick=4, so `if target_tick > current_tick`
    # is False and the engine does not advance.
    sim["started_at_ms"] = int(time.time() * 1000)
    storage.update_run(week_run, run)

    resp = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.get_json()

    assert "day" in body
    assert body["day"]["id"] == "tue", f"Expected 'tue' but got: {body['day']}"
    assert "today_pnl" in body
    assert "pending_earnings" in body


def test_week_state_techn_in_pending_earnings_on_mon(client, week_run):
    """On Monday (tick=0), TECHN (which reports on tue) must appear in pending_earnings."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    run = storage.get_run(week_run)
    run["stocksim"]["started_at_ms"] = int(time.time() * 1000)
    storage.update_run(week_run, run)

    resp = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    body = resp.get_json()

    pe_symbols = {e["symbol"] for e in body.get("pending_earnings", [])}
    assert "TECHN" in pe_symbols, (
        f"TECHN should be pending on Monday (reports tue); got: {pe_symbols}"
    )
