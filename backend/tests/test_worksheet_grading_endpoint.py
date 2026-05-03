"""Tests for worksheet rubric grading on /api/modules/<id>/lessons/<id>/complete — Task 15."""
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEXTAREA_TYPES = ("reflection", "pitch_builder", "customer_profile", "idea_scorecard")

FAKE_RUBRIC = {
    "score": 78,
    "strengths": ["Clear problem statement", "Good market insight"],
    "improvements": ["Add more data points"],
    "dim_signals": {"strategic_thinking": 5, "creativity": 3},
}

MODULE_ID = "test_ws_module"
LESSON_ID_SCORECARD = "w1_l1_idea_scorecard"
LESSON_ID_NON_TEXTAREA = "w1_l2_quiz"


def _make_module():
    """Minimal module fixture with two lessons: one textarea-heavy, one not."""
    return {
        "module_id": MODULE_ID,
        "title": "Test WS Module",
        "progression": "free",
        "weeks": [
            {
                "week_id": "w1",
                "number": 1,
                "title": "Week 1",
                "lessons": [
                    {
                        "lesson_id": LESSON_ID_SCORECARD,
                        "title": "Idea Scorecard",
                        "type": "worksheet",
                        "skill_tags": ["creativity"],
                        "schema": {
                            "type": "idea_scorecard",
                            "fields": [{"id": "problem", "label": "Problem"}],
                            "rubric": {
                                "version": "v1",
                                "anchors": {"novice": "vague", "capable": "clear", "strong": "specific"},
                                "signals": ["problem definition", "market insight"],
                            },
                        },
                    },
                    {
                        "lesson_id": LESSON_ID_NON_TEXTAREA,
                        "title": "Quiz",
                        "type": "quiz",
                        "pass_threshold": 0.6,
                        "schema": {"type": "quiz"},
                    },
                ],
            }
        ],
        "completion_award": {"xp": 100},
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch, tmp_path):
    """Bootstrap Flask test client with minimal env + module mock."""
    monkeypatch.setenv("MODEL_PROVIDER", "")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    import modules_engine
    # Redirect progress storage to a temp file so tests are isolated.
    monkeypatch.setattr(modules_engine, "PROGRESS_FILE", str(tmp_path / "module_progress.json"))

    # Inject our fake module by patching get_module so it doesn't require a file on disk.
    mod = _make_module()
    _orig_get_module = modules_engine.get_module

    def _fake_get_module(module_id):
        if module_id == MODULE_ID:
            return mod
        return _orig_get_module(module_id)

    monkeypatch.setattr(modules_engine, "get_module", _fake_get_module)

    from app import app as flask_app
    flask_app.config["TESTING"] = True

    # Inject a logged-in user via JWT.
    from auth import generate_token
    token = generate_token("u_ws_test", "ws_test_user", "student")

    with flask_app.test_client() as c:
        c._auth_token = token
        yield c


def _post_complete(client, module_id, lesson_id, body):
    token = client._auth_token
    return client.post(
        f"/api/modules/{module_id}/lessons/{lesson_id}/complete",
        json=body,
        headers={"Authorization": f"Bearer {token}"},
    )


# ---------------------------------------------------------------------------
# Test 1: rubric is returned when schema type is textarea-heavy (idea_scorecard)
# ---------------------------------------------------------------------------

def test_rubric_returned_for_textarea_schema(client, monkeypatch):
    """First completion of idea_scorecard lesson triggers grader and returns rubric."""
    monkeypatch.setattr("llm.grade_worksheet_freetext", lambda text, lesson, rubric: FAKE_RUBRIC)

    rv = _post_complete(client, MODULE_ID, LESSON_ID_SCORECARD, {
        "answers": {"problem": "Working parents struggle to find good tutoring."},
    })
    assert rv.status_code == 200, rv.get_data(as_text=True)
    body = rv.get_json()
    assert body["ok"] is True
    rubric = body.get("rubric")
    assert rubric is not None, f"Expected 'rubric' in response but got: {list(body.keys())}"
    assert rubric["score"] == 78
    assert "Clear problem statement" in rubric["strengths"]
    assert rubric["dim_signals"]["creativity"] == 3


# ---------------------------------------------------------------------------
# Test 2: rubric persisted in progress["rubrics"][lesson_id]
# ---------------------------------------------------------------------------

def test_rubric_persisted_in_progress(client, monkeypatch):
    """Rubric grading result is stored in prog['rubrics'][lesson_id]."""
    monkeypatch.setattr("llm.grade_worksheet_freetext", lambda text, lesson, rubric: FAKE_RUBRIC)

    rv = _post_complete(client, MODULE_ID, LESSON_ID_SCORECARD, {
        "answers": {"problem": "Farmers lack access to weather data."},
    })
    assert rv.status_code == 200
    body = rv.get_json()
    rubrics = (body.get("progress") or {}).get("rubrics") or {}
    assert LESSON_ID_SCORECARD in rubrics, (
        f"Expected progress.rubrics['{LESSON_ID_SCORECARD}'] but rubrics={rubrics}"
    )
    stored = rubrics[LESSON_ID_SCORECARD]
    assert stored["score"] == 78


# ---------------------------------------------------------------------------
# Test 3: no rubric when schema type is NOT in textarea-heavy list
# ---------------------------------------------------------------------------

def test_no_rubric_for_non_textarea_schema(client, monkeypatch):
    """Quiz lessons do not trigger the worksheet grader."""
    called = []
    monkeypatch.setattr("llm.grade_worksheet_freetext", lambda *a, **kw: called.append(1) or FAKE_RUBRIC)

    # Complete the quiz-type lesson (send passing score)
    rv = _post_complete(client, MODULE_ID, LESSON_ID_NON_TEXTAREA, {
        "answers": {"q1": "Paris"},
        "score": 8,
        "max_score": 10,
        "passed": True,
    })
    # Quiz passes or fails; either way, grader must NOT be called.
    assert len(called) == 0, "grade_worksheet_freetext should not be called for quiz lessons"
    if rv.status_code == 200:
        body = rv.get_json()
        assert body.get("rubric") is None


# ---------------------------------------------------------------------------
# Test 4: no second LLM call on re-completion (already_completed=True)
# ---------------------------------------------------------------------------

def test_no_second_grader_call_on_recompletion(client, monkeypatch):
    """Grader called exactly once; second submit does not call it again."""
    call_count = []
    monkeypatch.setattr(
        "llm.grade_worksheet_freetext",
        lambda text, lesson, rubric: call_count.append(1) or FAKE_RUBRIC,
    )

    payload = {"answers": {"problem": "Students need better feedback."}}

    # First submission → should grade
    rv1 = _post_complete(client, MODULE_ID, LESSON_ID_SCORECARD, payload)
    assert rv1.status_code == 200
    assert len(call_count) == 1

    # Second submission → already_completed; should NOT grade again
    rv2 = _post_complete(client, MODULE_ID, LESSON_ID_SCORECARD, payload)
    assert rv2.status_code == 200
    assert rv2.get_json().get("already_completed") is True
    assert len(call_count) == 1, (
        f"Grader called {len(call_count)} times but should only be called once"
    )


# ---------------------------------------------------------------------------
# Test 5: empty answers dict does not call grader
# ---------------------------------------------------------------------------

def test_empty_answers_skips_grader(client, monkeypatch):
    """Empty answers dict does not trigger grader (matches existing ai_feedback guard)."""
    called = []
    monkeypatch.setattr("llm.grade_worksheet_freetext", lambda *a, **kw: called.append(1) or FAKE_RUBRIC)

    rv = _post_complete(client, MODULE_ID, LESSON_ID_SCORECARD, {"answers": {}})
    assert rv.status_code == 200
    assert len(called) == 0
    body = rv.get_json()
    assert body.get("rubric") is None
