import pytest


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    yield


def test_seed_flashcards(env):
    from importlib import reload
    import spaced_repetition as sr
    reload(sr)
    sr.schedule_flashcard(
        user_id="u1",
        module_id="mento_entrepreneur_4week",
        lesson_id="w1_l1_intro",
        card={
            "q": "Define entrepreneurship",
            "a": "Solving a real problem people care about",
            "skill_tag": "creativity",
        },
    )
    # Existing get_due_reviews works for game reviews; for flashcards we use list:
    cards = sr.list_module_flashcards("u1", "mento_entrepreneur_4week")
    assert len(cards) == 1
    assert cards[0]["q"].startswith("Define")
