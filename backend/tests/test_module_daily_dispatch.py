# backend/tests/test_module_daily_dispatch.py
import json
import pytest


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    # Seed the dispatch bank in tmp data dir
    bank_dir = tmp_path / "module_daily_dispatch"
    bank_dir.mkdir()
    (bank_dir / "mento_entrepreneur_4week.json").write_text(json.dumps([
        {"day": 1, "title": "Welcome", "body": "Day 1."},
        {"day": 2, "title": "Day 2", "body": "Second tip."},
    ]))
    yield


def test_dispatch_picks_correct_day_for_user(env, monkeypatch):
    from importlib import reload
    import module_daily_dispatch as mdd
    reload(mdd)
    # User started the module 1 day ago → should receive message for day 2.
    msg = mdd.message_for_user_today(
        module_id="mento_entrepreneur_4week",
        started_at_iso="2026-05-10T08:00:00+05:30",
        today_iso="2026-05-11T18:00:00+05:30",
    )
    assert msg["day"] == 2
    # Out of range → None
    none = mdd.message_for_user_today(
        module_id="mento_entrepreneur_4week",
        started_at_iso="2026-05-10T08:00:00+05:30",
        today_iso="2026-06-30T18:00:00+05:30",
    )
    assert none is None
