"""Phase C — Task 9: module skill report aggregation."""
import uuid

import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth(client):
    username = f"skr_{uuid.uuid4().hex[:8]}"
    password = "Mento@2026"
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    if r.status_code in (200, 201):
        token = r.get_json()["token"]
    else:
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        token = r.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_skill_report_shape(client):
    h = _auth(client)
    r = client.get("/api/modules/mento_entrepreneur_4week/skill-report", headers=h)
    assert r.status_code == 200
    body = r.get_json()
    assert "dimensions" in body
    assert "highlights" in body
    assert "recommendations" in body
    # Even with zero plays, dimensions must include all core dimensions
    assert set(body["dimensions"].keys()) >= {
        "strategic_thinking", "creativity", "empathy", "communication", "resilience",
    }
