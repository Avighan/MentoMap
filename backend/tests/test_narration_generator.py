"""Failing tests for the narration batch generator (TDD red phase).

The implementation in scripts/generate_module_narration.py does not exist yet —
this test file should fail to import.
"""
from scripts.generate_module_narration import build_script  # noqa: F401


def test_build_script_uses_title_and_content():
    lesson = {"lesson_id": "w1_l1", "title": "Welcome", "content": "<p>Hello world.</p>"}
    s = build_script(lesson, lang="en")
    assert "Welcome" in s
    assert "Hello world" in s
    assert "<p>" not in s  # html stripped


def test_build_script_hi_mix_returns_nonempty():
    lesson = {"lesson_id": "w1_l1", "title": "Welcome", "content": "Hello."}
    s = build_script(lesson, lang="hi_mix")
    # Should at least return a non-empty string even without LLM configured.
    assert len(s) > 0
