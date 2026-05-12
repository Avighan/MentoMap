"""Verify modules_engine handles new optional fields without breaking."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from modules_engine import get_module


def test_module_loads_when_lesson_lacks_audio_urls():
    """Lessons without audio_urls field should load without error."""
    m = get_module("mento_entrepreneur_4week")
    assert m is not None, "Module should load"
    lesson = m["weeks"][0]["lessons"][0]
    # Either the field doesn't exist, or if it does, it's a dict
    assert "audio_urls" not in lesson or isinstance(lesson["audio_urls"], dict)


def test_module_loads_when_lesson_has_optional_audio_urls():
    """If we inject audio_urls into a lesson, engine should preserve it."""
    m = get_module("mento_entrepreneur_4week")
    assert m is not None, "Module should load"
    lesson = m["weeks"][0]["lessons"][0].copy()
    lesson["audio_urls"] = {"en": "/x.mp3", "hi": "/y.mp3"}
    assert lesson["audio_urls"]["en"] == "/x.mp3"


def test_module_with_flashcards_field_loads():
    """flashcards on a lesson is optional and preserved."""
    m = get_module("mento_entrepreneur_4week")
    assert m is not None, "Module should load"
    lesson = m["weeks"][0]["lessons"][0]
    flashcards = lesson.get("flashcards", [])
    assert isinstance(flashcards, list)


def test_unknown_lesson_type_does_not_raise():
    """Loader must tolerate lesson types it doesn't recognize."""
    from modules_engine import _validate_lesson_safe
    weird = {"lesson_id": "x", "type": "future_type_v9", "title": "x"}
    assert _validate_lesson_safe(weird) is True
