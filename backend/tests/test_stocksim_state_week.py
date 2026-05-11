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

    # Mon has 4 ticks, so tick=4 is the first tick of Tue. Pin started_at_ms to
    # now so elapsed_ticks=0 < current_tick=4 → lazy-advance is a no-op.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    sim["current_tick"] = 4
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


# ---------------------------------------------------------------------------
# Coverage gap fills — code-quality review follow-up
# ---------------------------------------------------------------------------

@pytest.fixture
def non_week_run():
    """Run pointing at stock-market-day-trader (no calendar_mode='week')."""
    run_id = "test-nonweek-stocksim-run-001"
    run_data = {
        "run_id": run_id,
        "user_id": "test-user-1",
        "game_id": "stock-market-day-trader",
    }
    file_path = _write_run_to_disk(run_id, run_data)
    yield run_id
    storage.RUNS.pop(run_id, None)
    storage.RUNS_MTIME.pop(run_id, None)
    if os.path.exists(file_path):
        os.remove(file_path)


def test_non_week_run_omits_week_enrichment_keys(client, non_week_run):
    """When the underlying game has no calendar_mode='week', the response must
    NOT include day/today_pnl/pending_earnings (gating via current_day()→None)."""
    start_resp = client.post(f"/api/run/{non_week_run}/stocksim/start", json={},
                             headers=_auth_headers())
    assert start_resp.status_code == 200, start_resp.get_data(as_text=True)

    run = storage.get_run(non_week_run)
    run["stocksim"]["started_at_ms"] = int(time.time() * 1000)
    storage.update_run(non_week_run, run)

    resp = client.get(f"/api/run/{non_week_run}/stocksim/state", headers=_auth_headers())
    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()

    assert "day" not in body, f"'day' must be absent for non-week runs; got: {list(body.keys())}"
    assert "today_pnl" not in body, "'today_pnl' must be absent for non-week runs"
    assert "pending_earnings" not in body, "'pending_earnings' must be absent for non-week runs"


def test_pending_earnings_filters_past_earnings_days(client, week_run):
    """On Wednesday (tick=8), Mon/Tue earnings symbols (FMCGCORP, TECHN, PHARMAGS)
    must be FILTERED OUT of pending_earnings; only Wed-and-later remain."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    # Mon(4) + Tue(4) = 8 → tick 8 is the first tick of Wed.
    run = storage.get_run(week_run)
    sim = run["stocksim"]
    sim["current_tick"] = 8
    sim["started_at_ms"] = int(time.time() * 1000)  # freeze clock → no lazy-advance
    storage.update_run(week_run, run)

    resp = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    body = resp.get_json()
    assert body["day"]["id"] == "wed", f"Expected wed, got: {body['day']}"

    pe_symbols = {e["symbol"] for e in body.get("pending_earnings", [])}
    # Past (mon, tue) — must be filtered out.
    assert "FMCGCORP" not in pe_symbols, f"FMCGCORP (mon) should be filtered out on wed; got: {pe_symbols}"
    assert "TECHN" not in pe_symbols, f"TECHN (tue) should be filtered out on wed; got: {pe_symbols}"
    assert "PHARMAGS" not in pe_symbols, f"PHARMAGS (tue) should be filtered out on wed; got: {pe_symbols}"
    # Today/future (wed, thu, fri) — must remain.
    assert "RETAILK" in pe_symbols, f"RETAILK (wed) should still be pending on wed; got: {pe_symbols}"
    assert "GREENPWR" in pe_symbols, f"GREENPWR (fri) should still be pending on wed; got: {pe_symbols}"


def test_today_pnl_nonzero_with_real_holding_and_sell(client, week_run):
    """Seed a TECHN holding and a same-day sell trade; today_pnl realized/unrealized
    must reflect them rather than collapsing to zero."""
    client.post(f"/api/run/{week_run}/stocksim/start", json={}, headers=_auth_headers())

    run = storage.get_run(week_run)
    sim = run["stocksim"]
    # Land on Tue (tick=4). Tue day-open tick is 4. Place current_tick > day_start
    # so the held position is mark-to-marketed against a different tick than open.
    sim["current_tick"] = 6
    sim["started_at_ms"] = int(time.time() * 1000)  # freeze clock → no lazy-advance
    # Held position: 5 TECHN shares
    sim.setdefault("holdings", {})
    sim["holdings"]["TECHN"] = {"qty": 5, "avg_price": 1000.0}
    # Realized today: one sell at tick 5 (>= day_start_tick=4) for +123.45
    sim.setdefault("trade_log", [])
    sim["trade_log"].append({
        "tick": 5, "side": "sell", "symbol": "TECHN",
        "qty": 1, "price": 1010.0, "realized_pnl": 123.45,
    })
    storage.update_run(week_run, run)

    resp = client.get(f"/api/run/{week_run}/stocksim/state", headers=_auth_headers())
    body = resp.get_json()
    assert body["day"]["id"] == "tue"

    tp = body["today_pnl"]
    # Realized must include our seeded sell.
    assert tp["realized"] == pytest.approx(123.45), f"Expected realized 123.45, got: {tp['realized']}"
    # Unrealized is (cur_mid - day_open_mid) * qty. day_start_tick == current_tick
    # would yield 0; we set current_tick=6 vs day_start=4 to force a non-trivial walk.
    # We don't pin the exact value (depends on seeded RNG), but it must be finite
    # and total must equal realized + unrealized.
    assert isinstance(tp["unrealized"], (int, float))
    assert tp["total"] == pytest.approx(tp["realized"] + tp["unrealized"])
