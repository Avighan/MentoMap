import uuid
import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth(client):
    username = f"ij_pdf_{uuid.uuid4().hex[:8]}"
    password = "Mento@2026"
    r = client.post("/api/auth/register", json={"username": username, "password": password})
    if r.status_code in (200, 201):
        token = r.get_json()["token"]
    else:
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        token = r.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_pdf_export_returns_pdf_bytes(client):
    h = _auth(client)
    client.post(
        "/api/modules/mento_entrepreneur_4week/idea-journal",
        json={"content": "My pitch: a tiffin app for hostel students", "type": "free_form"},
        headers=h,
    )
    r = client.get("/api/modules/mento_entrepreneur_4week/idea-journal/export", headers=h)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/pdf")
    assert r.data[:4] == b"%PDF"
