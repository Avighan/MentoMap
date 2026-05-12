"""Phase C — Task 11: parent-shareable PNG card endpoint."""
import uuid

import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from app import app, limiter
    app.config["TESTING"] = True
    try:
        limiter.reset()
    except Exception:
        pass
    return app.test_client()


def _auth(client):
    username = f"sc_{uuid.uuid4().hex[:8]}"
    password = "Mento@2026"
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    body = r.get_json() or {}
    token = body.get("token")
    if not token:
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        body = r.get_json() or {}
        token = body.get("token")
    assert token, f"failed to obtain auth token: status={r.status_code} body={body!r}"
    return {"Authorization": f"Bearer {token}"}


def test_card_returns_png(client):
    h = _auth(client)
    r = client.get(
        "/api/modules/mento_entrepreneur_4week/skill-report/card.png",
        headers=h,
    )
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "image/png"
    assert r.data[:8] == b"\x89PNG\r\n\x1a\n"
    # 1080x1080 — first IHDR chunk holds width/height (offsets 16..24)
    width = int.from_bytes(r.data[16:20], "big")
    height = int.from_bytes(r.data[20:24], "big")
    assert width == 1080 and height == 1080
