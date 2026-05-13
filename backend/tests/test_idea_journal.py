import os
import tempfile
import pytest


@pytest.fixture
def tmp_storage(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("MENTO_DATA_DIR", d)
        yield d


def test_append_and_list(tmp_storage):
    from importlib import reload
    import backend.idea_journal as ij
    reload(ij)
    ij.append_entry("u1", "mento_entrepreneur_4week", {
        "lesson_id": "w1_l1_intro",
        "lesson_title": "What is Entrepreneurship?",
        "content": "Solving a problem people care about.",
        "type": "worksheet",
    })
    entries = ij.list_entries("u1", "mento_entrepreneur_4week")
    assert len(entries) == 1
    assert entries[0]["lesson_id"] == "w1_l1_intro"
    assert "entry_id" in entries[0] and "timestamp" in entries[0]


def test_edit_and_star(tmp_storage):
    from importlib import reload
    import backend.idea_journal as ij
    reload(ij)
    e = ij.append_entry("u1", "m1", {"content": "first", "type": "free_form"})
    ij.edit_entry("u1", "m1", e["entry_id"], {"content": "second"})
    ij.star_entry("u1", "m1", e["entry_id"], True)
    entries = ij.list_entries("u1", "m1")
    assert entries[0]["content"] == "second"
    assert entries[0]["starred"] is True
    # Edit history retained:
    assert len(entries[0]["history"]) == 1
    assert entries[0]["history"][0]["content"] == "first"
