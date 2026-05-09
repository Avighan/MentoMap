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


def test_stocksim_state_returns_session(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={},
                headers=_auth_headers())
    resp = client.get(f"/api/run/{stocksim_run}/stocksim/state",
                      headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.get_json()
    assert "state" in data
    assert data["state"]["cash"] == 100000


def test_stocksim_state_404_when_no_session(client, stocksim_run):
    # No /start call
    resp = client.get(f"/api/run/{stocksim_run}/stocksim/state",
                      headers=_auth_headers())
    assert resp.status_code == 404


def test_stocksim_cancel_removes_pending_order(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={},
                headers=_auth_headers())
    # Inject a fake pending order via storage
    run = storage.get_run(stocksim_run)
    run["stocksim"]["pending_orders"] = [{
        "order_id": "lim-1", "type": "limit", "side": "buy",
        "symbol": "TECHV", "qty": 5, "limit_price": 100.0, "placed_tick": 1,
    }]
    storage.update_run(stocksim_run, run)
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/cancel",
                       json={"order_id": "lim-1"},
                       headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.get_json()["cancelled"] is True
    assert storage.get_run(stocksim_run)["stocksim"]["pending_orders"] == []


def test_stocksim_cancel_404_for_unknown_order(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={},
                headers=_auth_headers())
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/cancel",
                       json={"order_id": "nope"},
                       headers=_auth_headers())
    assert resp.status_code == 404


def test_stocksim_trade_market_buy_filled(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={}, headers=_auth_headers())
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 1, "symbol": "TECHV", "side": "buy",
        "qty": 5, "order_type": "market"
    }, headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "filled"
    assert data["fill"]["qty"] == 5
    assert "charges" in data
    state = storage.get_run(stocksim_run)["stocksim"]
    assert state["holdings"]["TECHV"]["qty"] == 5


def test_stocksim_trade_in_future_tick_rejected(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={}, headers=_auth_headers())
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 999, "symbol": "TECHV", "side": "buy",
        "qty": 1, "order_type": "market"
    }, headers=_auth_headers())
    assert resp.status_code == 400
    assert resp.get_json().get("error_code") == "INVALID_TICK"


def test_stocksim_trade_after_complete_rejected(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={}, headers=_auth_headers())
    client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={}, headers=_auth_headers())
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 1, "symbol": "TECHV", "side": "buy",
        "qty": 1, "order_type": "market"
    }, headers=_auth_headers())
    assert resp.status_code == 409
    assert resp.get_json().get("error_code") == "SESSION_COMPLETED"


def test_stocksim_complete_returns_pnl_and_dimensions(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={}, headers=_auth_headers())
    client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 1, "symbol": "TECHV", "side": "buy",
        "qty": 5, "order_type": "market"
    }, headers=_auth_headers())
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={}, headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.get_json()
    assert "pnl" in data
    assert "dimensions" in data
    assert "risk_tolerance" in data["dimensions"]
    assert storage.get_run(stocksim_run)["stocksim"]["completed"] is True


def test_stocksim_complete_idempotent(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={}, headers=_auth_headers())
    r1 = client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={}, headers=_auth_headers())
    r2 = client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={}, headers=_auth_headers())
    assert r1.status_code == 200
    assert r2.status_code in (200, 409)


def test_dimension_scores_match_engine_directly(client, stocksim_run):
    """Route output should match engine.score_dimensions() called directly."""
    from engines.stock_market_engine import StockMarketEngine
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={}, headers=_auth_headers())
    client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 1, "symbol": "TECHV", "side": "buy",
        "qty": 5, "order_type": "market"
    }, headers=_auth_headers())
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={}, headers=_auth_headers())
    route_dims = resp.get_json()["dimensions"]
    state = storage.get_run(stocksim_run)["stocksim"]
    sm_cfg = (storage.get_run(stocksim_run).get("game", {}).get("minigame_config") or {}).get("stock_market_config")
    eng = StockMarketEngine(sm_cfg)
    direct_dims = eng.score_dimensions(state)
    assert route_dims == direct_dims
