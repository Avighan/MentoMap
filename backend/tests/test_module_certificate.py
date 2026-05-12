"""Phase C — Task 13: module certificate gating."""
import uuid

import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth(client):
    username = f"cert_{uuid.uuid4().hex[:8]}"
    password = "Mento@2026"
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    if r.status_code in (200, 201):
        token = r.get_json()["token"]
    else:
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        token = r.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_certificate_blocked_when_incomplete(client):
    h = _auth(client)
    r = client.get("/api/modules/mento_entrepreneur_4week/certificate", headers=h)
    assert r.status_code == 409  # not yet eligible
    body = r.get_json()
    assert body.get("certificate_eligible") is False
