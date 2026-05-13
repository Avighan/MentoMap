import pytest


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))


def test_crud_and_rsvp(env):
    from importlib import reload
    import cohort_live_sessions as cls
    reload(cls)
    s = cls.create_session(
        cohort_id="c1", module_id="mento_entrepreneur_4week",
        data={
            "week": 1, "title": "Founder cameo",
            "host_name": "Sridhar Vembu", "host_bio_short": "Founder, Zoho",
            "scheduled_at": "2026-06-15T18:00:00+05:30",
            "duration_min": 60, "meeting_url": "https://meet.google.com/abc",
        },
    )
    assert s["session_id"]
    sessions = cls.list_sessions("c1", "mento_entrepreneur_4week")
    assert len(sessions) == 1
    cls.toggle_rsvp("c1", "mento_entrepreneur_4week", s["session_id"], "u1", True)
    cls.toggle_rsvp("c1", "mento_entrepreneur_4week", s["session_id"], "u1", True)  # idempotent
    cls.toggle_rsvp("c1", "mento_entrepreneur_4week", s["session_id"], "u2", True)
    again = cls.list_sessions("c1", "mento_entrepreneur_4week")
    assert set(again[0]["rsvps"]) == {"u1", "u2"}
    cls.toggle_rsvp("c1", "mento_entrepreneur_4week", s["session_id"], "u1", False)
    again2 = cls.list_sessions("c1", "mento_entrepreneur_4week")
    assert again2[0]["rsvps"] == ["u2"]
