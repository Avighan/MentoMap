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


def _register(client, role="student"):
    username = f"cls_{role}_{uuid.uuid4().hex[:8]}"
    password = "Mento@2026"
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "role": role},
    )
    body = r.get_json() or {}
    token = body.get("token")
    if not token:
        r = client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        body = r.get_json() or {}
        token = body.get("token")
    assert token, f"failed to obtain auth token: status={r.status_code} body={body!r}"
    return {"Authorization": f"Bearer {token}"}, username


def test_teacher_creates_and_student_rsvps(client):
    th, _ = _register(client, role="teacher")
    create = client.post(
        "/api/cohorts/c1/modules/mento_entrepreneur_4week/live-sessions",
        json={
            "week": 1, "title": "Founder cameo",
            "host_name": "Sridhar Vembu", "host_bio_short": "Founder, Zoho",
            "scheduled_at": "2030-06-15T18:00:00+05:30",
            "duration_min": 60, "meeting_url": "https://meet.google.com/abc",
        },
        headers=th,
    )
    assert create.status_code == 200, create.get_json()
    sid = create.get_json()["session_id"]

    sh, sname = _register(client, role="student")
    rsvp = client.post(
        f"/api/cohorts/c1/modules/mento_entrepreneur_4week/live-sessions/{sid}/rsvp",
        json={"attending": True}, headers=sh,
    )
    assert rsvp.status_code == 200, rsvp.get_json()
    assert len(rsvp.get_json()["rsvps"]) == 1


def test_student_cannot_create(client):
    sh, _ = _register(client, role="student")
    r = client.post(
        "/api/cohorts/c1/modules/mento_entrepreneur_4week/live-sessions",
        json={
            "week": 1, "title": "X", "host_name": "Y",
            "scheduled_at": "2030-06-15T18:00:00+05:30",
            "meeting_url": "https://m.example/x",
        },
        headers=sh,
    )
    assert r.status_code == 403


def test_list_returns_created(client):
    th, _ = _register(client, role="teacher")
    client.post(
        "/api/cohorts/c2/modules/mento_entrepreneur_4week/live-sessions",
        json={
            "week": 2, "title": "Y", "host_name": "Z",
            "scheduled_at": "2030-07-15T18:00:00+05:30",
            "meeting_url": "https://m.example/y",
        },
        headers=th,
    )
    r = client.get(
        "/api/cohorts/c2/modules/mento_entrepreneur_4week/live-sessions",
        headers=th,
    )
    assert r.status_code == 200
    sessions = r.get_json()["sessions"]
    assert len(sessions) == 1 and sessions[0]["title"] == "Y"
