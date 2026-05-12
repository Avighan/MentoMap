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


def test_build_script_handles_dict_content():
    """Real mento_entrepreneur_4week lessons store content as a dict."""
    lesson = {
        "lesson_id": "w1_l1_intro",
        "title": "Welcome to the Workshop",
        "content": {
            "intro": "Hi, I'm Mento.",
            "key_takeaway": "Stay curious.",
            "mento_says": "Over 28 lessons we'll build a pitch.",
            "cards": [
                {"icon": "🌱", "title": "Week 1", "body": "Discover the entrepreneur."},
                {"icon": "🔍", "title": "Week 2", "body": "Fall in love with the problem."},
            ],
            "question": "What problem did you notice today?",
            "image_url": "/static/img.png",  # must be ignored
        },
    }
    s = build_script(lesson, lang="en")
    assert "Welcome to the Workshop" in s
    assert "Hi, I'm Mento" in s
    assert "Discover the entrepreneur" in s
    assert "Stay curious" in s
    assert "/static/img.png" not in s  # image_url filtered out


def test_build_script_handles_missing_content():
    lesson = {"lesson_id": "x", "title": "Title Only"}
    s = build_script(lesson, lang="en")
    assert s == "Title Only"
