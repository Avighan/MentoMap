"""Integration tests for /api/run/<id>/stocksim/* routes."""
import json
import os
import time
import pytest
import jwt
from app import app as flask_app
import storage
from auth import JWT_SECRET


def _make_token(user_id: str = "test-user-1", role: str = "student") -> str:
    """Generate a valid JWT for the given user_id / role using the app's JWT_SECRET."""
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
    """Write a run dict to the storage directory so storage.get_run can find it."""
    from datetime import datetime
    run_data = dict(run_data)
    run_data.setdefault("last_accessed", datetime.now().isoformat())
    file_path = os.path.join(storage.STORAGE_DIR, f"{run_id}.json")
    with open(file_path, "w") as f:
        json.dump(run_data, f)
    return file_path


@pytest.fixture
def stocksim_run():
    """Create a stocksim run in storage and return its id."""
    run_id = "test-stocksim-run-001"
    run_data = {
        "run_id": run_id,
        "user_id": "test-user-1",
        "game_id": "stock-market-day-trader",
        "game": {
            "game_id": "stock-market-day-trader",
            "game_type": "minigame",
            "minigame_config": {
                "subtype": "stock_market",
                "stock_market_config": {
                    "tick_count": 22,
                    "tick_interval_seconds": 8,
                    "starting_capital": 100000,
                    "realism_tier": 2,
                    "stocks": [
                        {"symbol": "TECHV", "name": "TechVeda", "sector": "IT",
                         "starting_price": 1200, "volatility": 0.025, "beta": 1.2},
                    ],
                    "sectors": ["IT"], "events": [],
                    "charges": {"brokerage_per_trade": 20, "stt_buy_pct": 0.001,
                                "stt_sell_pct": 0.001, "exchange_pct": 0.0000345,
                                "gst_pct": 0.18},
                    "dimensions_config": {"risk_tolerance": {"weight": 1.0}},
                },
            },
        },
    }
    file_path = _write_run_to_disk(run_id, run_data)
    yield run_id
    # Cleanup
    storage.RUNS.pop(run_id, None)
    storage.RUNS_MTIME.pop(run_id, None)
    if os.path.exists(file_path):
        os.remove(file_path)


def test_stocksim_start_creates_session(client, stocksim_run):
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/start",
                       json={"profile": "day_trader"},
                       headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.get_json()
    assert "seed" in data
    assert "opening_state" in data
    assert data["opening_state"]["cash"] == 100000
    assert data["opening_state"]["holdings"] == {}


def test_stocksim_start_404_when_run_missing(client):
    resp = client.post("/api/run/no-such-run/stocksim/start", json={},
                       headers=_auth_headers())
    assert resp.status_code == 404


def test_stocksim_start_400_when_not_stock_market(client):
    run_id = "wrong-type-run"
    run_data = {
        "run_id": run_id,
        "user_id": "test-user-1",
        "game_id": "x",
        "game": {"game_type": "rounds"},
    }
    file_path = _write_run_to_disk(run_id, run_data)
    try:
        resp = client.post(f"/api/run/{run_id}/stocksim/start", json={},
                           headers=_auth_headers())
        assert resp.status_code == 400
    finally:
        storage.RUNS.pop(run_id, None)
        storage.RUNS_MTIME.pop(run_id, None)
        if os.path.exists(file_path):
            os.remove(file_path)


def test_stocksim_start_409_when_already_started(client, stocksim_run):
    r1 = client.post(f"/api/run/{stocksim_run}/stocksim/start", json={},
                     headers=_auth_headers())
    assert r1.status_code == 200
    r2 = client.post(f"/api/run/{stocksim_run}/stocksim/start", json={},
                     headers=_auth_headers())
    assert r2.status_code == 409


def test_stocksim_start_response_includes_meta(client, stocksim_run):
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/start", json={},
                       headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["tick_schedule_meta"]["tick_count"] == 22
    assert data["tick_schedule_meta"]["tick_interval_seconds"] == 8
    assert data["opening_state"]["current_tick"] == 0
    assert data["market_calendar"]["shorting_enabled"] is False
