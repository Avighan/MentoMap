import json
import uuid

import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth_headers(client):
    # Register a fresh user per test to avoid reliance on seeded fixtures.
    username = f"ij_user_{uuid.uuid4().hex[:8]}"
    password = "Mento@2026"
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    if r.status_code in (200, 201):
        token = r.get_json()["token"]
    else:
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        token = r.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_journal_post_and_get(client):
    h = _auth_headers(client)
    r = client.post(
        "/api/modules/mento_entrepreneur_4week/idea-journal",
        json={"content": "First idea", "type": "free_form"},
        headers=h,
    )
    assert r.status_code == 200
    eid = r.get_json()["entry_id"]

    r2 = client.get("/api/modules/mento_entrepreneur_4week/idea-journal", headers=h)
    assert r2.status_code == 200
    assert any(e["entry_id"] == eid for e in r2.get_json()["entries"])


def test_journal_patch_star(client):
    h = _auth_headers(client)
    r = client.post(
        "/api/modules/mento_entrepreneur_4week/idea-journal",
        json={"content": "Idea A", "type": "free_form"},
        headers=h,
    )
    eid = r.get_json()["entry_id"]
    r2 = client.patch(
        f"/api/modules/mento_entrepreneur_4week/idea-journal/{eid}",
        json={"starred": True, "content": "Idea A (edited)"},
        headers=h,
    )
    assert r2.status_code == 200
    body = r2.get_json()
    assert body["starred"] is True
    assert body["content"] == "Idea A (edited)"
