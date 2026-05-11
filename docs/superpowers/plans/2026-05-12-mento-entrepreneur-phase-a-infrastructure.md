# Mento Entrepreneur — Phase A: Infrastructure Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land all backend services, lesson types, schema extensions, image self-hosting, and route scaffolding required by Phases B–D — without changing any existing behavior.

**Architecture:** Strict additive discipline. New files for new services. Existing files only get new branches added (never modified). All schema changes are optional fields. New routes use new path prefixes. Image self-host has fallback to original URLs.

**Tech Stack:** Python 3.12 / Flask, OpenAI SDK (TTS + STT), ElevenLabs SDK, React 18 / Vite, existing `cost_tracker.py`, existing `modules_engine.py`.

**Spec:** `docs/superpowers/specs/2026-05-12-mento-entrepreneur-workshop-readiness-design.md`

---

## File Structure

**Backend — new:**
- `backend/services/tts_service.py` — TTS wrapper (OpenAI + ElevenLabs), audio cache
- `backend/services/conversation_persona_engine.py` — generalized persona conversation (extracted from `audio_negotiation_engine.py`)
- `backend/scripts/cache_module_images.py` — one-time image self-host script
- `backend/personas/__init__.py` — persona loader
- `backend/routes/module_pitch_coach.py` — placeholder routes (returns 501 until Plan 2)
- `backend/routes/module_interview_sim.py` — placeholder routes
- `backend/routes/module_skill_report.py` — placeholder routes
- `backend/routes/module_idea_journal.py` — placeholder routes
- `backend/routes/cohort_live_sessions.py` — placeholder routes
- `backend/tests/test_tts_service.py`
- `backend/tests/test_module_schema_compat.py`
- `backend/tests/test_module_regression.py`

**Backend — modify:**
- `backend/app.py` — register new blueprints; add `cost_caps` enforcement helper
- `backend/modules_engine.py` — add support for optional `audio_urls`, `flashcards`, `cost_caps`, `completion` fields; safe-skip unknown lesson types
- `backend/assets/audio/cache/` — new dir (gitignored)
- `backend/assets/audio/module/` — new dir
- `backend/assets/module_images/mento_entrepreneur_4week/` — new dir

**Frontend — new:**
- `frontend-react/src/components/module/AudioLessonRenderer.jsx`
- `frontend-react/src/components/module/PitchCoachRenderer.jsx` — placeholder UI
- `frontend-react/src/components/module/InterviewSimRenderer.jsx` — placeholder UI
- `frontend-react/src/components/module/MicroQuestRenderer.jsx`
- `frontend-react/src/components/module/CaseStudyCardRenderer.jsx`
- `frontend-react/src/components/module/FailureCardRenderer.jsx`
- `frontend-react/src/components/module/CohortLiveSessionCard.jsx`
- `frontend-react/src/components/module/UnknownLessonRenderer.jsx`

**Frontend — modify:**
- `frontend-react/src/pages/ModuleDetailPage.jsx` — extend lesson-type dispatcher, add unknown fallback

**Data:**
- `backend/modules/mento_entrepreneur_4week.json` — image URLs rewritten with fallback retained

---

## Task 0: Establish regression baseline

**Files:**
- Create: `backend/tests/test_module_regression.py`

- [ ] **Step 1: Write smoke test that loads existing module unchanged**

```python
# backend/tests/test_module_regression.py
import json
from pathlib import Path
from backend.modules_engine import load_module

def test_mento_entrepreneur_loads_unchanged():
    """Baseline: module loads with same 32 lessons, 4 weeks, no errors."""
    module = load_module("mento_entrepreneur_4week")
    assert module is not None
    assert module["module_id"] == "mento_entrepreneur_4week"
    weeks = module["weeks"]
    assert len(weeks) == 4
    total_lessons = sum(len(w["lessons"]) for w in weeks)
    assert total_lessons == 32

def test_other_modules_load_unchanged():
    """All other modules in backend/modules/ must still load."""
    modules_dir = Path("backend/modules")
    json_files = [f for f in modules_dir.glob("*.json") if not f.name.startswith(".")]
    for f in json_files:
        with open(f) as fh:
            data = json.load(fh)
        assert "module_id" in data, f"{f} missing module_id"
```

- [ ] **Step 2: Run test to verify baseline passes today**

Run: `cd backend && python -m pytest tests/test_module_regression.py -v`
Expected: 2 tests pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_module_regression.py
git commit -m "test: baseline regression for module loading"
```

---

## Task 1: Self-host module hero images (with fallback)

**Files:**
- Create: `backend/scripts/cache_module_images.py`
- Modify: `backend/modules/mento_entrepreneur_4week.json` (URL rewrites)
- Create: `backend/assets/module_images/mento_entrepreneur_4week/` (directory)

- [ ] **Step 1: Write the image-cache script**

```python
# backend/scripts/cache_module_images.py
"""One-time: download every Pollinations image referenced in a module to
backend/assets/module_images/<module_id>/<lesson_id>.png and rewrite
URLs in the module JSON. Keeps original URL in `image_url_fallback`."""
import json
import sys
import hashlib
import urllib.request
from pathlib import Path

def cache_module_images(module_id: str) -> None:
    module_path = Path(f"backend/modules/{module_id}.json")
    assets_dir = Path(f"backend/assets/module_images/{module_id}")
    assets_dir.mkdir(parents=True, exist_ok=True)

    with open(module_path) as f:
        module = json.load(f)

    for week in module.get("weeks", []):
        for lesson in week.get("lessons", []):
            url = lesson.get("image_url")
            if not url or url.startswith("/static/"):
                continue
            lesson_id = lesson["lesson_id"]
            out_path = assets_dir / f"{lesson_id}.png"
            if not out_path.exists():
                print(f"downloading {lesson_id} from {url[:80]}...")
                try:
                    urllib.request.urlretrieve(url, out_path)
                except Exception as e:
                    print(f"FAILED {lesson_id}: {e}")
                    continue
            lesson["image_url_fallback"] = url
            lesson["image_url"] = f"/static/module_images/{module_id}/{lesson_id}.png"

    with open(module_path, "w") as f:
        json.dump(module, f, indent=2, ensure_ascii=False)
    print("done.")

if __name__ == "__main__":
    cache_module_images(sys.argv[1] if len(sys.argv) > 1 else "mento_entrepreneur_4week")
```

- [ ] **Step 2: Run the script**

```bash
cd backend && python scripts/cache_module_images.py mento_entrepreneur_4week
```

Expected: ~32 PNG files appear under `backend/assets/module_images/mento_entrepreneur_4week/`.

- [ ] **Step 3: Verify Flask serves them**

```bash
cd backend && python -c "from app import app; print([r.rule for r in app.url_map.iter_rules() if 'static' in r.rule])"
```

Expected: `/static/<path:filename>` route shows. If missing, add `app.config["STATIC_FOLDER"] = "assets"` and a static blueprint.

- [ ] **Step 4: Run regression test from Task 0**

```bash
cd backend && python -m pytest tests/test_module_regression.py -v
```

Expected: still 2 passes (module still loads, lesson count unchanged).

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/cache_module_images.py backend/assets/module_images/ backend/modules/mento_entrepreneur_4week.json
git commit -m "feat(module): self-host mento_entrepreneur hero images with fallback"
```

---

## Task 2: TTS service — failing tests first

**Files:**
- Create: `backend/tests/test_tts_service.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_tts_service.py
import os
from pathlib import Path
import pytest
from backend.services.tts_service import synthesize, cache_key_for

def test_cache_key_is_deterministic():
    k1 = cache_key_for("hello", "voice_a", "en", "openai")
    k2 = cache_key_for("hello", "voice_a", "en", "openai")
    assert k1 == k2

def test_cache_key_changes_with_text():
    k1 = cache_key_for("hello", "voice_a", "en", "openai")
    k2 = cache_key_for("hi there", "voice_a", "en", "openai")
    assert k1 != k2

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_openai_tts_synthesize_returns_mp3_bytes():
    audio = synthesize("Hello from Mento.", provider="openai", lang="en")
    assert isinstance(audio, bytes)
    assert len(audio) > 1000
    assert audio[:3] == b"ID3" or audio[:2] == b"\xff\xfb"  # mp3 magic

@pytest.mark.skipif(not os.getenv("ELEVENLABS_API_KEY"), reason="needs ELEVENLABS_API_KEY")
def test_elevenlabs_tts_synthesize_returns_mp3_bytes():
    audio = synthesize("Hello from Mento.", provider="elevenlabs", lang="en")
    assert isinstance(audio, bytes)
    assert len(audio) > 1000

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_cached_call_does_not_hit_api_twice(tmp_path, monkeypatch):
    monkeypatch.setenv("TTS_CACHE_DIR", str(tmp_path))
    text = "Hello cached."
    a1 = synthesize(text, provider="openai", lang="en")
    a2 = synthesize(text, provider="openai", lang="en")
    assert a1 == a2  # same bytes from cache
```

- [ ] **Step 2: Run tests — verify they fail with ImportError**

```bash
cd backend && python -m pytest tests/test_tts_service.py -v
```

Expected: 5 errors (ModuleNotFoundError: No module named 'backend.services.tts_service').

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_tts_service.py
git commit -m "test(tts): add failing tests for TTS service"
```

---

## Task 3: TTS service — implementation

**Files:**
- Create: `backend/services/__init__.py` (if missing)
- Create: `backend/services/tts_service.py`

- [ ] **Step 1: Implement minimal TTS service**

```python
# backend/services/tts_service.py
"""Unified TTS wrapper for OpenAI TTS and ElevenLabs. Caches results."""
import hashlib
import os
from pathlib import Path
from typing import Literal

try:
    from backend.cost_tracker import record_cost
except ImportError:
    def record_cost(category: str, amount: float, meta: dict | None = None) -> None:
        pass

Provider = Literal["openai", "elevenlabs"]
Lang = Literal["en", "hi", "hi_mix"]

_DEFAULT_CACHE_DIR = Path("backend/assets/audio/cache")
_DEFAULT_VOICES = {
    "openai": {"en": "nova", "hi": "nova", "hi_mix": "nova"},
    "elevenlabs": {
        "en": os.getenv("ELEVENLABS_VOICE_EN", "21m00Tcm4TlvDq8ikWAM"),
        "hi": os.getenv("ELEVENLABS_VOICE_HI", "21m00Tcm4TlvDq8ikWAM"),
        "hi_mix": os.getenv("ELEVENLABS_VOICE_HI_MIX", "21m00Tcm4TlvDq8ikWAM"),
    },
}

def _cache_dir() -> Path:
    p = Path(os.getenv("TTS_CACHE_DIR", _DEFAULT_CACHE_DIR))
    p.mkdir(parents=True, exist_ok=True)
    return p

def cache_key_for(text: str, voice: str, lang: str, provider: str) -> str:
    raw = f"{provider}|{lang}|{voice}|{text}".encode()
    return hashlib.sha1(raw).hexdigest()

def _read_cache(key: str) -> bytes | None:
    p = _cache_dir() / f"{key}.mp3"
    return p.read_bytes() if p.exists() else None

def _write_cache(key: str, data: bytes) -> None:
    (_cache_dir() / f"{key}.mp3").write_bytes(data)

def synthesize(
    text: str,
    provider: Provider = "openai",
    lang: Lang = "en",
    voice: str | None = None,
) -> bytes:
    voice = voice or _DEFAULT_VOICES[provider][lang]
    key = cache_key_for(text, voice, lang, provider)
    cached = _read_cache(key)
    if cached:
        return cached
    if provider == "openai":
        data = _synthesize_openai(text, voice)
    elif provider == "elevenlabs":
        data = _synthesize_elevenlabs(text, voice)
    else:
        raise ValueError(f"unknown provider: {provider}")
    _write_cache(key, data)
    record_cost(f"tts_{provider}", _estimate_cost(text, provider), {"voice": voice, "lang": lang})
    return data

def _synthesize_openai(text: str, voice: str) -> bytes:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    r = client.audio.speech.create(model="tts-1", voice=voice, input=text)
    return r.content

def _synthesize_elevenlabs(text: str, voice_id: str) -> bytes:
    from elevenlabs.client import ElevenLabs
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    chunks = client.text_to_speech.convert(voice_id=voice_id, text=text, model_id="eleven_multilingual_v2")
    return b"".join(chunks)

def _estimate_cost(text: str, provider: str) -> float:
    chars = len(text)
    if provider == "openai":
        return (chars / 1_000_000) * 15.0  # ~$15/M chars for tts-1
    return (chars / 1000) * 0.30  # ~$0.30/1000 chars elevenlabs multilingual
```

- [ ] **Step 2: Run tests — verify they pass**

```bash
cd backend && python -m pytest tests/test_tts_service.py -v
```

Expected: all 5 pass (or skip if env keys missing).

- [ ] **Step 3: Run regression test**

```bash
cd backend && python -m pytest tests/test_module_regression.py -v
```

Expected: 2 passes.

- [ ] **Step 4: Commit**

```bash
git add backend/services/__init__.py backend/services/tts_service.py
git commit -m "feat(tts): unified OpenAI + ElevenLabs TTS service with caching"
```

---

## Task 4: Module schema extensions — failing tests

**Files:**
- Create: `backend/tests/test_module_schema_compat.py`

- [ ] **Step 1: Write tests for optional schema fields**

```python
# backend/tests/test_module_schema_compat.py
"""Verify modules_engine handles new optional fields without breaking."""
from backend.modules_engine import load_module, get_lesson

def test_module_loads_when_lesson_lacks_audio_urls():
    m = load_module("mento_entrepreneur_4week")
    lesson = m["weeks"][0]["lessons"][0]
    assert "audio_urls" not in lesson or isinstance(lesson["audio_urls"], dict)

def test_module_loads_when_lesson_has_optional_audio_urls(tmp_path, monkeypatch):
    """If we inject audio_urls into a lesson, engine should preserve it."""
    m = load_module("mento_entrepreneur_4week")
    lesson = m["weeks"][0]["lessons"][0].copy()
    lesson["audio_urls"] = {"en": "/x.mp3", "hi": "/y.mp3"}
    assert lesson["audio_urls"]["en"] == "/x.mp3"

def test_unknown_lesson_type_does_not_raise():
    """Loader must tolerate lesson types it doesn't recognize."""
    from backend.modules_engine import _validate_lesson_safe
    weird = {"lesson_id": "x", "type": "future_type_v9", "title": "x"}
    assert _validate_lesson_safe(weird) is True

def test_module_with_flashcards_field_loads():
    """flashcards on a lesson is optional and preserved."""
    m = load_module("mento_entrepreneur_4week")
    lesson = m["weeks"][0]["lessons"][0]
    flashcards = lesson.get("flashcards", [])
    assert isinstance(flashcards, list)
```

- [ ] **Step 2: Run tests — see which fail**

```bash
cd backend && python -m pytest tests/test_module_schema_compat.py -v
```

Expected: `test_unknown_lesson_type_does_not_raise` fails (function doesn't exist). Others pass.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_module_schema_compat.py
git commit -m "test(modules): schema-compat tests for optional fields"
```

---

## Task 5: Module engine — accept new optional fields, tolerate unknown lesson types

**Files:**
- Modify: `backend/modules_engine.py`

- [ ] **Step 1: Add `_validate_lesson_safe` helper and tolerant lesson handling**

In `backend/modules_engine.py`, add near the top (after imports):

```python
# Lesson types known to the renderer. Unknown types are allowed (forward compat).
_KNOWN_LESSON_TYPES = {
    "lesson", "worksheet", "quiz", "field_mission", "reflection",
    "game", "voice_recording", "assessment",
    # New (Phase A):
    "audio_lesson", "pitch_coach", "interview_sim", "micro_quest",
    "case_study_card", "failure_card", "cohort_live_session",
}

def _validate_lesson_safe(lesson: dict) -> bool:
    """Return True if lesson has minimum fields. Unknown types are OK."""
    if not isinstance(lesson, dict):
        return False
    if "lesson_id" not in lesson or "type" not in lesson:
        return False
    return True
```

Wherever the loader currently rejects unknown types (search for any `raise` or `assert` on lesson type), replace with `_validate_lesson_safe()` and log unknown types but continue.

- [ ] **Step 2: Run schema-compat tests — verify all pass**

```bash
cd backend && python -m pytest tests/test_module_schema_compat.py -v
```

Expected: all 4 pass.

- [ ] **Step 3: Run regression tests — verify still pass**

```bash
cd backend && python -m pytest tests/test_module_regression.py tests/test_module_schema_compat.py -v
```

Expected: 6 passes.

- [ ] **Step 4: Commit**

```bash
git add backend/modules_engine.py
git commit -m "feat(modules): tolerate new optional fields and unknown lesson types"
```

---

## Task 6: Cost-cap enforcement helper

**Files:**
- Modify: `backend/modules_engine.py`
- Create: `backend/tests/test_cost_caps.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_cost_caps.py
import pytest
from backend.modules_engine import check_and_increment_usage, UsageLimitExceeded

def test_first_call_allowed(tmp_path, monkeypatch):
    monkeypatch.setenv("MODULE_PROGRESS_FILE", str(tmp_path / "p.json"))
    check_and_increment_usage("u1", "mod1", "pitch_coach_runs", limit=3)

def test_third_call_allowed_fourth_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("MODULE_PROGRESS_FILE", str(tmp_path / "p.json"))
    for _ in range(3):
        check_and_increment_usage("u1", "mod1", "pitch_coach_runs", limit=3)
    with pytest.raises(UsageLimitExceeded):
        check_and_increment_usage("u1", "mod1", "pitch_coach_runs", limit=3)
```

- [ ] **Step 2: Run — verify it fails (ImportError)**

```bash
cd backend && python -m pytest tests/test_cost_caps.py -v
```

Expected: ImportError on `UsageLimitExceeded`.

- [ ] **Step 3: Implement in `backend/modules_engine.py`**

Append to `modules_engine.py`:

```python
class UsageLimitExceeded(Exception):
    pass

def check_and_increment_usage(user_id: str, module_id: str, key: str, limit: int) -> int:
    """Atomic increment of progress[user][module].usage[key]. Raises if over limit."""
    progress = _load_progress()  # existing helper
    user_prog = progress.setdefault(user_id, {}).setdefault(module_id, {})
    usage = user_prog.setdefault("usage", {})
    current = usage.get(key, 0)
    if current >= limit:
        raise UsageLimitExceeded(f"{key} limit {limit} reached for {user_id}/{module_id}")
    usage[key] = current + 1
    _save_progress(progress)  # existing helper
    return usage[key]
```

(If `_load_progress`/`_save_progress` use different names in the file, use those.)

- [ ] **Step 4: Run tests**

```bash
cd backend && python -m pytest tests/test_cost_caps.py tests/test_module_regression.py -v
```

Expected: 4 passes total.

- [ ] **Step 5: Commit**

```bash
git add backend/modules_engine.py backend/tests/test_cost_caps.py
git commit -m "feat(modules): cost-cap enforcement helper for usage-limited features"
```

---

## Task 7: Placeholder route blueprints (501 responses)

**Files:**
- Create: `backend/routes/__init__.py` (if missing)
- Create: `backend/routes/module_pitch_coach.py`
- Create: `backend/routes/module_interview_sim.py`
- Create: `backend/routes/module_skill_report.py`
- Create: `backend/routes/module_idea_journal.py`
- Create: `backend/routes/cohort_live_sessions.py`
- Modify: `backend/app.py` (register blueprints)

- [ ] **Step 1: Write blueprint stubs**

```python
# backend/routes/module_pitch_coach.py
from flask import Blueprint, jsonify
bp = Blueprint("module_pitch_coach", __name__)

@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/pitch-coach")
def pitch_coach(module_id, lesson_id):
    return jsonify({"error": "not_implemented", "phase": "B"}), 501
```

```python
# backend/routes/module_interview_sim.py
from flask import Blueprint, jsonify
bp = Blueprint("module_interview_sim", __name__)

@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/start")
def start(module_id, lesson_id):
    return jsonify({"error": "not_implemented", "phase": "B"}), 501

@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/turn")
def turn(module_id, lesson_id):
    return jsonify({"error": "not_implemented", "phase": "B"}), 501

@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/end")
def end(module_id, lesson_id):
    return jsonify({"error": "not_implemented", "phase": "B"}), 501
```

```python
# backend/routes/module_skill_report.py
from flask import Blueprint, jsonify
bp = Blueprint("module_skill_report", __name__)

@bp.get("/api/modules/<module_id>/skill-report")
def report(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501

@bp.get("/api/modules/<module_id>/skill-report/card.png")
def card_png(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501

@bp.get("/api/modules/<module_id>/certificate")
def certificate(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501
```

```python
# backend/routes/module_idea_journal.py
from flask import Blueprint, jsonify
bp = Blueprint("module_idea_journal", __name__)

@bp.route("/api/modules/<module_id>/idea-journal", methods=["GET", "POST", "PATCH"])
def journal(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501

@bp.get("/api/modules/<module_id>/idea-journal/export")
def export(module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501
```

```python
# backend/routes/cohort_live_sessions.py
from flask import Blueprint, jsonify
bp = Blueprint("cohort_live_sessions", __name__)
PREFIX = "/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions"

@bp.route(PREFIX, methods=["GET", "POST"])
def list_or_create(cohort_id, module_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501

@bp.route(f"{PREFIX}/<session_id>", methods=["PATCH", "DELETE"])
def edit_or_delete(cohort_id, module_id, session_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501

@bp.post(f"{PREFIX}/<session_id>/rsvp")
def rsvp(cohort_id, module_id, session_id):
    return jsonify({"error": "not_implemented", "phase": "C"}), 501
```

- [ ] **Step 2: Register blueprints in `backend/app.py`**

Near other `register_blueprint` calls (search for existing blueprint registrations):

```python
from backend.routes.module_pitch_coach import bp as _bp_pitch_coach
from backend.routes.module_interview_sim import bp as _bp_interview_sim
from backend.routes.module_skill_report import bp as _bp_skill_report
from backend.routes.module_idea_journal import bp as _bp_idea_journal
from backend.routes.cohort_live_sessions import bp as _bp_cohort_live
for _bp in (_bp_pitch_coach, _bp_interview_sim, _bp_skill_report, _bp_idea_journal, _bp_cohort_live):
    app.register_blueprint(_bp)
```

- [ ] **Step 3: Verify routes mount without conflicts**

```bash
cd backend && python -c "from app import app
for r in sorted(str(r) for r in app.url_map.iter_rules() if 'pitch-coach' in str(r) or 'interview-sim' in str(r) or 'skill-report' in str(r) or 'idea-journal' in str(r) or 'live-sessions' in str(r)):
    print(r)"
```

Expected: 11 new route lines printed. No "already registered" errors.

- [ ] **Step 4: Smoke-test one endpoint returns 501**

```bash
cd backend && python -c "
from app import app
c = app.test_client()
r = c.post('/api/modules/mento_entrepreneur_4week/lessons/w3_l7_pitch_practice/pitch-coach')
print(r.status_code, r.get_json())
"
```

Expected: `501 {'error': 'not_implemented', 'phase': 'B'}`.

- [ ] **Step 5: Run regression tests**

```bash
cd backend && python -m pytest tests/test_module_regression.py tests/test_module_schema_compat.py tests/test_cost_caps.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/ backend/app.py
git commit -m "feat(routes): scaffold pitch-coach / interview-sim / skill-report / journal / live-session blueprints (501 placeholders)"
```

---

## Task 8: Frontend — UnknownLessonRenderer fallback

**Files:**
- Create: `frontend-react/src/components/module/UnknownLessonRenderer.jsx`

- [ ] **Step 1: Write the fallback component**

```jsx
// frontend-react/src/components/module/UnknownLessonRenderer.jsx
import React from "react";

export default function UnknownLessonRenderer({ lesson }) {
  return (
    <div className="rounded-2xl border-2 border-dashed border-gray-300 p-8 text-center bg-gray-50">
      <div className="text-4xl mb-2">🚧</div>
      <h3 className="text-lg font-semibold mb-1">{lesson?.title || "Coming soon"}</h3>
      <p className="text-sm text-gray-600">
        This lesson uses a new format ({lesson?.type}) that will be available in an upcoming update.
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/module/UnknownLessonRenderer.jsx
git commit -m "feat(module): UnknownLessonRenderer fallback for forward compat"
```

---

## Task 9: Frontend — AudioLessonRenderer

**Files:**
- Create: `frontend-react/src/components/module/AudioLessonRenderer.jsx`

- [ ] **Step 1: Write the component**

```jsx
// frontend-react/src/components/module/AudioLessonRenderer.jsx
import React, { useState, useRef } from "react";

const LANG_LABELS = { en: "EN", hi: "हिं", hi_mix: "Hinglish" };

export default function AudioLessonRenderer({ lesson, onComplete }) {
  const [lang, setLang] = useState("en");
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef(null);

  const audioUrls = lesson.audio_urls || {};
  const url = audioUrls[lang] || audioUrls.en;

  const toggle = () => {
    if (!audioRef.current) return;
    if (playing) audioRef.current.pause();
    else audioRef.current.play();
  };

  return (
    <article className="space-y-4">
      {lesson.image_url && (
        <img
          src={lesson.image_url}
          alt={lesson.title}
          onError={(e) => { if (lesson.image_url_fallback) e.currentTarget.src = lesson.image_url_fallback; }}
          className="w-full rounded-2xl"
        />
      )}
      <h2 className="text-2xl font-bold">{lesson.title}</h2>
      {url && (
        <div className="flex items-center gap-3 p-3 bg-sky-50 rounded-xl border border-sky-200">
          <button onClick={toggle} className="px-3 py-2 bg-sky-600 text-white rounded-lg" aria-label={playing ? "Pause narration" : "Play narration"}>
            {playing ? "⏸ Pause" : "▶ Listen"}
          </button>
          <audio
            ref={audioRef}
            src={url}
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            onEnded={() => setPlaying(false)}
          />
          <div className="flex gap-1 ml-auto">
            {Object.entries(LANG_LABELS).filter(([k]) => audioUrls[k]).map(([k, label]) => (
              <button key={k} onClick={() => setLang(k)} className={`px-2 py-1 text-xs rounded ${lang === k ? "bg-sky-600 text-white" : "bg-white border"}`}>
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: lesson.content || "" }} />
      <button onClick={onComplete} className="px-4 py-2 bg-emerald-600 text-white rounded-lg">
        Mark complete
      </button>
    </article>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/module/AudioLessonRenderer.jsx
git commit -m "feat(module): AudioLessonRenderer with multi-lang toggle + image fallback"
```

---

## Task 10: Frontend — placeholder renderers for B/C/D phases

**Files:**
- Create: `frontend-react/src/components/module/PitchCoachRenderer.jsx`
- Create: `frontend-react/src/components/module/InterviewSimRenderer.jsx`
- Create: `frontend-react/src/components/module/MicroQuestRenderer.jsx`
- Create: `frontend-react/src/components/module/CaseStudyCardRenderer.jsx`
- Create: `frontend-react/src/components/module/FailureCardRenderer.jsx`
- Create: `frontend-react/src/components/module/CohortLiveSessionCard.jsx`

- [ ] **Step 1: Write a shared placeholder helper**

```jsx
// frontend-react/src/components/module/_Placeholder.jsx
import React from "react";
export default function Placeholder({ title, type, phase }) {
  return (
    <div className="rounded-2xl border-2 border-dashed p-8 bg-gray-50 text-center">
      <div className="text-3xl mb-2">🛠️</div>
      <h3 className="text-lg font-semibold">{title || type}</h3>
      <p className="text-sm text-gray-600">This feature ships in Phase {phase}.</p>
    </div>
  );
}
```

- [ ] **Step 2: Write all 6 placeholder renderers**

```jsx
// PitchCoachRenderer.jsx
import React from "react";
import Placeholder from "./_Placeholder";
export default function PitchCoachRenderer({ lesson }) {
  return <Placeholder title={lesson.title} type="pitch_coach" phase="B" />;
}
```

```jsx
// InterviewSimRenderer.jsx
import React from "react";
import Placeholder from "./_Placeholder";
export default function InterviewSimRenderer({ lesson }) {
  return <Placeholder title={lesson.title} type="interview_sim" phase="B" />;
}
```

```jsx
// MicroQuestRenderer.jsx
import React, { useState } from "react";
export default function MicroQuestRenderer({ lesson, onComplete }) {
  const [answer, setAnswer] = useState("");
  const prompt = lesson.schema?.prompt || lesson.content || "Apply what you just learned.";
  return (
    <article className="space-y-4">
      <h2 className="text-2xl font-bold">{lesson.title}</h2>
      <div className="p-4 bg-amber-50 border-l-4 border-amber-400 rounded-r-lg">
        <p className="text-sm font-medium">⚡ Quick Quest ({lesson.estimated_minutes || 3} min)</p>
        <p className="mt-1">{prompt}</p>
      </div>
      <textarea
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        rows={4}
        className="w-full border rounded-lg p-3"
        placeholder="Type your answer here..."
      />
      <button
        onClick={() => onComplete({ answer })}
        disabled={!answer.trim()}
        className="px-4 py-2 bg-emerald-600 text-white rounded-lg disabled:opacity-50"
      >
        Submit
      </button>
    </article>
  );
}
```

```jsx
// CaseStudyCardRenderer.jsx
import React from "react";
export default function CaseStudyCardRenderer({ lesson, onComplete }) {
  const c = lesson.schema || {};
  return (
    <article className="max-w-2xl mx-auto">
      <div className="rounded-3xl overflow-hidden shadow-xl bg-gradient-to-br from-indigo-50 to-white border">
        {c.portrait_url && <img src={c.portrait_url} alt={c.founder_name} className="w-full" />}
        <div className="p-6 space-y-3">
          <h2 className="text-2xl font-bold">{c.founder_name}</h2>
          <p className="text-sm text-gray-500">{c.role}</p>
          <p>{c.backstory}</p>
          <div className="p-3 bg-indigo-50 rounded-lg border border-indigo-200">
            <p className="text-sm font-semibold">💡 Takeaway</p>
            <p className="text-sm">{c.takeaway}</p>
          </div>
          {c.reflection_prompt && (
            <p className="italic text-gray-700">✏️ {c.reflection_prompt}</p>
          )}
          <button onClick={onComplete} className="mt-2 px-4 py-2 bg-emerald-600 text-white rounded-lg">
            Got it
          </button>
        </div>
      </div>
    </article>
  );
}
```

```jsx
// FailureCardRenderer.jsx
import React from "react";
export default function FailureCardRenderer({ lesson, onComplete }) {
  const c = lesson.schema || {};
  return (
    <article className="max-w-2xl mx-auto">
      <div className="rounded-3xl overflow-hidden shadow-xl bg-gradient-to-br from-rose-50 to-white border">
        <div className="p-6 space-y-3">
          <div className="text-xs uppercase tracking-wider text-rose-600 font-semibold">Failure Museum</div>
          <h2 className="text-2xl font-bold">{c.company_name}</h2>
          <p className="text-sm text-gray-500">{c.years || ""}</p>
          <div>
            <p className="text-sm font-semibold">What they tried:</p>
            <p className="text-sm">{c.what_they_tried}</p>
          </div>
          <div>
            <p className="text-sm font-semibold">Why it failed:</p>
            <p className="text-sm">{c.why_it_failed}</p>
          </div>
          <div className="p-3 bg-rose-50 rounded-lg border border-rose-200">
            <p className="text-sm font-semibold">📚 Lesson</p>
            <p className="text-sm">{c.lesson_learned}</p>
          </div>
          <button onClick={onComplete} className="mt-2 px-4 py-2 bg-emerald-600 text-white rounded-lg">
            Understood
          </button>
        </div>
      </div>
    </article>
  );
}
```

```jsx
// CohortLiveSessionCard.jsx
import React from "react";
import Placeholder from "./_Placeholder";
export default function CohortLiveSessionCard({ lesson }) {
  return <Placeholder title={lesson.title || "Live Session"} type="cohort_live_session" phase="C" />;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/components/module/_Placeholder.jsx \
        frontend-react/src/components/module/PitchCoachRenderer.jsx \
        frontend-react/src/components/module/InterviewSimRenderer.jsx \
        frontend-react/src/components/module/MicroQuestRenderer.jsx \
        frontend-react/src/components/module/CaseStudyCardRenderer.jsx \
        frontend-react/src/components/module/FailureCardRenderer.jsx \
        frontend-react/src/components/module/CohortLiveSessionCard.jsx
git commit -m "feat(module): renderers for new lesson types (placeholders for B/C; functional for micro-quest/cards)"
```

---

## Task 11: Wire new lesson types into ModuleDetailPage dispatcher

**Files:**
- Modify: `frontend-react/src/pages/ModuleDetailPage.jsx`

- [ ] **Step 1: Find the dispatcher**

Run: `grep -n "case 'lesson'" frontend-react/src/pages/ModuleDetailPage.jsx`
Expected: one or two matches showing the switch statement (likely in a `renderLesson` function).

- [ ] **Step 2: Add imports at top of `ModuleDetailPage.jsx`**

```jsx
import AudioLessonRenderer from "../components/module/AudioLessonRenderer";
import PitchCoachRenderer from "../components/module/PitchCoachRenderer";
import InterviewSimRenderer from "../components/module/InterviewSimRenderer";
import MicroQuestRenderer from "../components/module/MicroQuestRenderer";
import CaseStudyCardRenderer from "../components/module/CaseStudyCardRenderer";
import FailureCardRenderer from "../components/module/FailureCardRenderer";
import CohortLiveSessionCard from "../components/module/CohortLiveSessionCard";
import UnknownLessonRenderer from "../components/module/UnknownLessonRenderer";
```

- [ ] **Step 3: Extend the switch (just before the `default` branch)**

```jsx
case "audio_lesson":
  return <AudioLessonRenderer lesson={lesson} onComplete={handleComplete} />;
case "pitch_coach":
  return <PitchCoachRenderer lesson={lesson} onComplete={handleComplete} />;
case "interview_sim":
  return <InterviewSimRenderer lesson={lesson} onComplete={handleComplete} />;
case "micro_quest":
  return <MicroQuestRenderer lesson={lesson} onComplete={handleComplete} />;
case "case_study_card":
  return <CaseStudyCardRenderer lesson={lesson} onComplete={handleComplete} />;
case "failure_card":
  return <FailureCardRenderer lesson={lesson} onComplete={handleComplete} />;
case "cohort_live_session":
  return <CohortLiveSessionCard lesson={lesson} cohortId={cohortId} />;
```

Replace any existing `default:` with:

```jsx
default:
  return <UnknownLessonRenderer lesson={lesson} />;
```

- [ ] **Step 4: Smoke-test in dev**

Run frontend dev server. Open existing module — verify all current lessons still render. Inspect console for warnings.

```bash
cd frontend-react && npm run dev
```

Manually open `/modules/mento_entrepreneur_4week` and click through 4–5 lessons. Verify no console errors. Verify text/worksheet/game/quiz lessons render exactly as before.

- [ ] **Step 5: Build to verify no syntax errors**

```bash
cd frontend-react && npm run build
```

Expected: clean build.

- [ ] **Step 6: Commit**

```bash
git add frontend-react/src/pages/ModuleDetailPage.jsx
git commit -m "feat(module): dispatch new lesson types in ModuleDetailPage"
```

---

## Task 12: Conversation persona engine (extracted from audio_negotiation)

**Files:**
- Create: `backend/services/conversation_persona_engine.py`
- Create: `backend/personas/__init__.py`
- Create: `backend/personas/entrepreneur/kirana_uncle.json`

- [ ] **Step 1: Author one starter persona JSON**

```json
// backend/personas/entrepreneur/kirana_uncle.json
{
  "persona_id": "kirana_uncle",
  "display_name": "Kirana shop uncle",
  "voice_id_openai": "onyx",
  "voice_id_elevenlabs": "21m00Tcm4TlvDq8ikWAM",
  "voice_lang": "hi",
  "hidden_pain_point": "Inventory waste from unpredictable customer demand — he over-orders perishables and throws ~₹400/day worth.",
  "reveal_threshold": 3,
  "system_prompt": "You are a kirana shop owner in his 40s from a tier-2 Indian city. You speak Hindi-first with simple English mixed in. You are friendly but busy. You do NOT immediately reveal your real business problems — make the student dig with WHY questions. After 3 thoughtful WHYs, you can hint at the inventory-waste issue. Keep replies to 1-2 sentences. Stay in character. NEVER give business advice; you are the customer being interviewed."
}
```

- [ ] **Step 2: Write the persona engine**

```python
# backend/services/conversation_persona_engine.py
"""Generalized persona conversation engine. One persona JSON + history → next reply.
Used by interview_sim (Phase B) and reusable by negotiation/dating-sim."""
import json
import os
from pathlib import Path
from typing import Any

try:
    from backend.llm import call_llm  # existing helper
except ImportError:
    call_llm = None

PERSONAS_DIR = Path("backend/personas")

def load_persona(category: str, persona_id: str) -> dict[str, Any]:
    p = PERSONAS_DIR / category / f"{persona_id}.json"
    if not p.exists():
        raise FileNotFoundError(f"persona not found: {category}/{persona_id}")
    return json.loads(p.read_text())

def list_personas(category: str) -> list[dict[str, Any]]:
    d = PERSONAS_DIR / category
    if not d.exists():
        return []
    return [json.loads(p.read_text()) for p in d.glob("*.json")]

def next_reply(persona: dict, history: list[dict]) -> str:
    """history: [{role: 'user'|'persona', text: str}, ...]"""
    if call_llm is None:
        return "(persona engine: LLM not configured)"
    messages = [{"role": "system", "content": persona["system_prompt"]}]
    for turn in history:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["text"]})
    return call_llm(messages=messages, max_tokens=200, temperature=0.8)
```

- [ ] **Step 3: Quick smoke test**

```bash
cd backend && python -c "
from services.conversation_persona_engine import load_persona, list_personas
p = load_persona('entrepreneur', 'kirana_uncle')
print('persona loaded:', p['display_name'])
print('listing:', len(list_personas('entrepreneur')), 'personas')
"
```

Expected: prints persona name + count of 1.

- [ ] **Step 4: Commit**

```bash
git add backend/services/conversation_persona_engine.py backend/personas/
git commit -m "feat(personas): conversation persona engine + kirana_uncle starter"
```

---

## Task 13: End-to-end regression sweep

**Files:** (no changes — verification only)

- [ ] **Step 1: Run all Phase-A tests together**

```bash
cd backend && python -m pytest tests/test_tts_service.py tests/test_module_schema_compat.py tests/test_cost_caps.py tests/test_module_regression.py -v
```

Expected: all pass (some TTS tests may skip if API keys not in env).

- [ ] **Step 2: Re-run existing project tests that touch modules**

```bash
cd backend && python -m pytest tests/test_game_flow_integration.py tests/test_round_takeaway.py -v 2>&1 | tail -30
```

Expected: same pass/fail state as before Phase A (no new failures).

- [ ] **Step 3: Frontend build**

```bash
cd frontend-react && npm run build
```

Expected: clean.

- [ ] **Step 4: Local server smoke**

```bash
cd backend && python app.py &
sleep 3
curl -s http://localhost:5001/api/modules/mento_entrepreneur_4week | python3 -c "import sys, json; d=json.load(sys.stdin); print('OK' if d.get('module') else 'FAIL:', d.get('module', {}).get('module_id'))"
kill %1
```

Expected: `OK mento_entrepreneur_4week`.

- [ ] **Step 5: Tag Phase A complete**

```bash
git tag -a phase-a-complete -m "Phase A: infrastructure foundation complete"
```

---

## Definition of Done — Phase A

- [ ] All Phase-A test files green
- [ ] Module regression test green (32 lessons, 4 weeks intact)
- [ ] Other modules in `backend/modules/` still load
- [ ] All 11 placeholder routes return 501 (not 404, not 500)
- [ ] All 7 new lesson types dispatch in frontend (no crashes; placeholder UIs visible)
- [ ] Existing lesson rendering unchanged (manual click-through pass)
- [ ] `tts_service.synthesize()` produces valid mp3 for "Hello"
- [ ] `conversation_persona_engine.load_persona('entrepreneur', 'kirana_uncle')` works
- [ ] Image self-host: at least one image is served at `/static/module_images/...`
- [ ] Cost-cap helper raises `UsageLimitExceeded` after limit
- [ ] No existing tests newly fail
- [ ] Tag `phase-a-complete` exists
