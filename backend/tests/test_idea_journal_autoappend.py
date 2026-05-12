"""Phase C Task 3: save_worksheet auto-appends to the Idea Journal."""
import pytest


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    yield


def test_worksheet_save_auto_appends_journal_entry(env):
    from importlib import reload
    import idea_journal
    reload(idea_journal)
    import modules_engine
    reload(modules_engine)

    user_id = "u_autoappend_1"
    module_id = "mento_entrepreneur_4week"
    lesson_id = "w1_l1_intro"

    modules_engine.save_worksheet(user_id, module_id, lesson_id, {"q1": "Solve a real problem"})

    entries = idea_journal.list_entries(user_id, module_id)
    assert any(e.get("lesson_id") == lesson_id and e.get("type") == "worksheet" for e in entries), \
        f"Expected a worksheet entry auto-appended, got: {entries}"
