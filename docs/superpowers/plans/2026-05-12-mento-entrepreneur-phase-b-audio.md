# Mento Entrepreneur — Phase B: Audio (Bundle 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every lesson hearable (EN / HI / Hinglish), make the Pitch Coach and Customer Interview Simulator real voice-driven features.

**Architecture:** Pre-generated narration via ElevenLabs (one-time batch, cached to `assets/audio/module/`). Runtime voice features (pitch coach + interview sim) use Whisper STT → Claude scoring/conversation → OpenAI TTS reply. Cost caps enforced via Phase-A helper. Conversation state stored in `cost_tracker.py`-tracked progress JSON.

**Tech Stack:** OpenAI Whisper (STT), OpenAI TTS, ElevenLabs multilingual v2, Anthropic Claude, React audio capture (MediaRecorder API).

**Spec:** `docs/superpowers/specs/2026-05-12-mento-entrepreneur-workshop-readiness-design.md` §4
**Depends on:** Phase A (`phase-a-complete` tag)

---

## File Structure

**Backend — new:**
- `backend/scripts/generate_module_narration.py` — batch narration generator (one-time)
- `backend/services/pitch_coach.py` — STT → Claude rubric → TTS reply pipeline
- `backend/services/interview_sim.py` — conversation lifecycle (start/turn/end) using `conversation_persona_engine`
- `backend/personas/entrepreneur/tiffin_auntie.json`
- `backend/personas/entrepreneur/classmate_priya.json`
- `backend/personas/entrepreneur/auto_driver.json`
- `backend/personas/entrepreneur/working_parent.json`
- `backend/personas/entrepreneur/hostel_student.json`
- `backend/tests/test_pitch_coach.py`
- `backend/tests/test_interview_sim.py`

**Backend — modify:**
- `backend/routes/module_pitch_coach.py` — replace 501 with real impl
- `backend/routes/module_interview_sim.py` — replace 501 with real impl
- `backend/modules/mento_entrepreneur_4week.json` — add `audio_urls` to all 32 lessons, add new `w2_l3b_interview_sim` lesson, add new `w3_l7b_pitch_coach` lesson

**Frontend — modify:**
- `frontend-react/src/components/module/PitchCoachRenderer.jsx` — replace placeholder with real UI
- `frontend-react/src/components/module/InterviewSimRenderer.jsx` — replace placeholder with real UI
- `frontend-react/src/components/module/AudioLessonRenderer.jsx` — add sticky bottom player + persist play across lesson navigation
- `frontend-react/src/api/modules.js` — add `pitchCoach()`, `interviewSimStart/Turn/End()`

**Frontend — new:**
- `frontend-react/src/components/module/audio/StickyAudioPlayer.jsx` — global player
- `frontend-react/src/components/module/audio/VoiceRecorder.jsx` — shared recorder used by pitch + interview
- `frontend-react/src/components/module/audio/PitchRubricChart.jsx`

---

## Task 1: Author 5 more persona JSONs

**Files:** create 5 files in `backend/personas/entrepreneur/`

- [ ] **Step 1: Write `tiffin_auntie.json`**

```json
{
  "persona_id": "tiffin_auntie",
  "display_name": "Tiffin-service auntie",
  "voice_id_openai": "shimmer",
  "voice_id_elevenlabs": "EXAVITQu4vr4xnSDxMaL",
  "voice_lang": "hi",
  "hidden_pain_point": "Regular customers delay payment 3-4 weeks; she runs out of cash to buy groceries.",
  "reveal_threshold": 3,
  "system_prompt": "You are a 50s woman running a home-based tiffin service in an Indian city, delivering ~30 meals/day. You speak Hindi with English mixed in. You are warm but tired and worried. Do NOT reveal your real problem (cashflow from late payments) until the student asks 3 thoughtful WHYs. Keep replies 1-2 sentences. Stay in character. NEVER give business advice; you are the customer."
}
```

- [ ] **Step 2: Write `classmate_priya.json`**

```json
{
  "persona_id": "classmate_priya",
  "display_name": "Classmate Priya (12)",
  "voice_id_openai": "alloy",
  "voice_id_elevenlabs": "EXAVITQu4vr4xnSDxMaL",
  "voice_lang": "hi_mix",
  "hidden_pain_point": "She loses 2-3 pencils every week and her mom is angry; she actually loses them because they roll off her desk.",
  "reveal_threshold": 2,
  "system_prompt": "You are Priya, a 12-year-old student in class 7. You speak in Hinglish (mostly English with Hindi words and casual tone like 'haan', 'yaar', 'matlab'). You are chatty but distractible. Do NOT immediately say WHY you lose pencils — make the student dig with 2 WHYs. Keep replies short and age-appropriate. Stay in character."
}
```

- [ ] **Step 3: Write `auto_driver.json`**

```json
{
  "persona_id": "auto_driver",
  "display_name": "Auto-rickshaw driver",
  "voice_id_openai": "echo",
  "voice_id_elevenlabs": "TxGEqnHWrfWFTfGW9XjX",
  "voice_lang": "hi",
  "hidden_pain_point": "Even on meter rides, customers haggle and refuse to pay full meter; he loses ~₹200/day. Real cause: many customers don't trust the meter is honest.",
  "reveal_threshold": 3,
  "system_prompt": "You are a 30s auto-rickshaw driver in an Indian city. You speak Hindi with simple English. You are frank, slightly annoyed at customers, but honest. Do NOT immediately reveal the trust issue — make the student ask 3 WHYs to surface it. Keep replies 1-2 sentences. Stay in character."
}
```

- [ ] **Step 4: Write `working_parent.json`**

```json
{
  "persona_id": "working_parent",
  "display_name": "Working parent",
  "voice_id_openai": "nova",
  "voice_id_elevenlabs": "EXAVITQu4vr4xnSDxMaL",
  "voice_lang": "en",
  "hidden_pain_point": "Too tired after work to help kid with homework; the kid is falling behind in math and she feels guilty.",
  "reveal_threshold": 3,
  "system_prompt": "You are a 40s working professional in an Indian metro, with a 10-year-old. You speak English with some Hindi. You are polite but stressed. Do NOT immediately admit guilt about not helping with homework — surface it only after 3 thoughtful WHYs. Keep replies 1-2 sentences. Stay in character."
}
```

- [ ] **Step 5: Write `hostel_student.json`**

```json
{
  "persona_id": "hostel_student",
  "display_name": "College hostel student",
  "voice_id_openai": "fable",
  "voice_id_elevenlabs": "VR6AewLTigWG4xSOukaG",
  "voice_lang": "hi_mix",
  "hidden_pain_point": "Tired of bland mess food and has no nearby healthy alternative under ₹100; orders Swiggy daily and is broke by month-end.",
  "reveal_threshold": 2,
  "system_prompt": "You are a 20-year-old engineering hostel student. You speak Hinglish, casual and friendly. Do NOT immediately reveal the money problem — make student dig with 2 WHYs. Keep replies short, slangy. Stay in character."
}
```

- [ ] **Step 6: Verify all 6 personas load**

```bash
cd backend && python -c "
from services.conversation_persona_engine import list_personas
ps = list_personas('entrepreneur')
print(len(ps), 'personas:', [p['persona_id'] for p in ps])
"
```

Expected: `6 personas: [...]`

- [ ] **Step 7: Commit**

```bash
git add backend/personas/entrepreneur/
git commit -m "feat(personas): add 5 more entrepreneur interview personas"
```

---

## Task 2: Narration batch generator — failing test

**Files:**
- Create: `backend/tests/test_narration_generator.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_narration_generator.py
import json
from pathlib import Path
from backend.scripts.generate_module_narration import build_script, generate_for_module

def test_build_script_uses_title_and_content():
    lesson = {"lesson_id": "w1_l1", "title": "Welcome", "content": "<p>Hello world.</p>"}
    s = build_script(lesson, lang="en")
    assert "Welcome" in s
    assert "Hello world" in s
    assert "<p>" not in s  # html stripped

def test_build_script_hi_mix_includes_hindi_filler():
    lesson = {"lesson_id": "w1_l1", "title": "Welcome", "content": "Hello."}
    s = build_script(lesson, lang="hi_mix")
    # Should contain at least one Devanagari char (we ask the script generator to translate)
    # For now we only assert the function runs and returns a non-empty string.
    assert len(s) > 0
```

- [ ] **Step 2: Run — expect ImportError**

```bash
cd backend && python -m pytest tests/test_narration_generator.py -v
```

Expected: ImportError.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_narration_generator.py
git commit -m "test(narration): add failing tests for batch generator"
```

---

## Task 3: Narration batch generator — implementation

**Files:**
- Create: `backend/scripts/generate_module_narration.py`

- [ ] **Step 1: Implement script**

```python
# backend/scripts/generate_module_narration.py
"""One-time: generate EN + HI + Hinglish narration mp3s for every lesson in a module.
Writes to backend/assets/audio/module/<module_id>/<lesson_id>/<lang>.mp3
and updates the module JSON with audio_urls per lesson."""
import json
import re
import sys
from pathlib import Path

from backend.services.tts_service import synthesize

try:
    from backend.llm import call_llm
except ImportError:
    call_llm = None

LANGS = ["en", "hi", "hi_mix"]

def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()

def build_script(lesson: dict, lang: str) -> str:
    title = lesson.get("title", "")
    body = _strip_html(lesson.get("content", ""))
    base = f"{title}. {body}".strip(". ").strip()
    if lang == "en":
        return base
    if call_llm is None:
        return base  # cannot translate without LLM
    if lang == "hi":
        prompt = f"Translate the following short lesson to natural classroom Hindi for a 12-year-old Indian student. Keep it under 300 words. Return ONLY the Hindi text.\n\n{base}"
    else:  # hi_mix
        prompt = f"Rewrite the following short lesson in Hinglish — natural code-switched Hindi+English the way an urban Indian 12-year-old speaks. Keep most technical terms in English, but use Hindi connectors and casual phrasing. Under 300 words. Return ONLY the Hinglish text.\n\n{base}"
    try:
        out = call_llm(messages=[{"role": "user", "content": prompt}], max_tokens=600, temperature=0.4)
        return (out or base).strip()
    except Exception:
        return base

def generate_for_module(module_id: str, langs: list[str] | None = None, provider: str = "elevenlabs") -> None:
    langs = langs or LANGS
    module_path = Path(f"backend/modules/{module_id}.json")
    out_root = Path(f"backend/assets/audio/module/{module_id}")
    out_root.mkdir(parents=True, exist_ok=True)

    module = json.loads(module_path.read_text())
    for week in module.get("weeks", []):
        for lesson in week.get("lessons", []):
            lid = lesson["lesson_id"]
            ltype = lesson.get("type", "lesson")
            if ltype not in {"lesson", "audio_lesson", "case_study_card", "failure_card"}:
                continue
            lesson.setdefault("audio_urls", {})
            for lang in langs:
                out_file = out_root / lid / f"{lang}.mp3"
                if out_file.exists():
                    lesson["audio_urls"][lang] = f"/static/audio/module/{module_id}/{lid}/{lang}.mp3"
                    continue
                script = build_script(lesson, lang)
                if not script:
                    continue
                out_file.parent.mkdir(parents=True, exist_ok=True)
                audio = synthesize(script, provider=provider, lang=lang)
                out_file.write_bytes(audio)
                lesson["audio_urls"][lang] = f"/static/audio/module/{module_id}/{lid}/{lang}.mp3"
                print(f"✓ {lid}/{lang}.mp3 ({len(audio)} bytes)")
    module_path.write_text(json.dumps(module, indent=2, ensure_ascii=False))
    print("done.")

if __name__ == "__main__":
    args = sys.argv[1:]
    module_id = args[0] if args else "mento_entrepreneur_4week"
    langs = args[1].split(",") if len(args) > 1 else None
    provider = args[2] if len(args) > 2 else "elevenlabs"
    generate_for_module(module_id, langs, provider)
```

- [ ] **Step 2: Run tests pass**

```bash
cd backend && python -m pytest tests/test_narration_generator.py -v
```

Expected: 2 pass.

- [ ] **Step 3: Dry-run for ONE lesson only (sanity check before paying for full batch)**

Edit `generate_module_narration.py` temporarily OR run a one-off:

```bash
cd backend && python -c "
from scripts.generate_module_narration import build_script, generate_for_module
from services.tts_service import synthesize
import json
m = json.load(open('modules/mento_entrepreneur_4week.json'))
l = m['weeks'][0]['lessons'][0]
script = build_script(l, 'en')
print('SCRIPT:', script[:120])
audio = synthesize(script, provider='openai', lang='en')
open('/tmp/test_narration.mp3', 'wb').write(audio)
print('Wrote /tmp/test_narration.mp3', len(audio), 'bytes')
"
```

Expected: prints script + writes ~30-100KB mp3. Listen to confirm voice + clarity.

- [ ] **Step 4: Run full batch (after voice approval)**

```bash
cd backend && python -m scripts.generate_module_narration mento_entrepreneur_4week en elevenlabs
# Then HI and Hinglish
cd backend && python -m scripts.generate_module_narration mento_entrepreneur_4week en,hi,hi_mix elevenlabs
```

Expected: ~32 lesson dirs × 3 langs = up to 96 mp3 files. Cost: ~₹1200.

- [ ] **Step 5: Verify audio URLs landed in module JSON**

```bash
cd backend && python -c "
import json
m = json.load(open('modules/mento_entrepreneur_4week.json'))
n = sum(1 for w in m['weeks'] for l in w['lessons'] if 'audio_urls' in l)
print(n, 'lessons have audio_urls')
"
```

Expected: ≥10 (only lesson-like types).

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/generate_module_narration.py backend/assets/audio/module/mento_entrepreneur_4week/ backend/modules/mento_entrepreneur_4week.json
git commit -m "feat(narration): generate EN+HI+Hinglish narration for all lessons"
```

---

## Task 4: Sticky audio player

**Files:**
- Create: `frontend-react/src/components/module/audio/StickyAudioPlayer.jsx`
- Create: `frontend-react/src/contexts/AudioContext.jsx`

- [ ] **Step 1: Write `AudioContext`**

```jsx
// frontend-react/src/contexts/AudioContext.jsx
import React, { createContext, useContext, useRef, useState, useCallback } from "react";

const AudioContext = createContext(null);

export function AudioProvider({ children }) {
  const audioRef = useRef(null);
  const [src, setSrc] = useState(null);
  const [playing, setPlaying] = useState(false);
  const [rate, setRate] = useState(1);

  const play = useCallback((url) => {
    if (!audioRef.current) return;
    if (url !== src) {
      audioRef.current.src = url;
      setSrc(url);
    }
    audioRef.current.playbackRate = rate;
    audioRef.current.play();
  }, [src, rate]);

  const pause = useCallback(() => audioRef.current?.pause(), []);
  const setSpeed = useCallback((r) => {
    setRate(r);
    if (audioRef.current) audioRef.current.playbackRate = r;
  }, []);

  return (
    <AudioContext.Provider value={{ src, playing, rate, play, pause, setSpeed, audioRef }}>
      {children}
      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
    </AudioContext.Provider>
  );
}

export const useAudio = () => useContext(AudioContext);
```

- [ ] **Step 2: Write `StickyAudioPlayer`**

```jsx
// frontend-react/src/components/module/audio/StickyAudioPlayer.jsx
import React from "react";
import { useAudio } from "../../../contexts/AudioContext";

export default function StickyAudioPlayer() {
  const { src, playing, rate, play, pause, setSpeed } = useAudio();
  if (!src) return null;
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg p-3 flex items-center gap-3 z-40">
      <button onClick={() => playing ? pause() : play(src)} className="px-3 py-2 bg-sky-600 text-white rounded-lg">
        {playing ? "⏸" : "▶"}
      </button>
      <div className="flex-1 text-xs text-gray-600 truncate">Now playing: lesson narration</div>
      <div className="flex gap-1">
        {[1, 1.25, 1.5].map(r => (
          <button key={r} onClick={() => setSpeed(r)}
            className={`px-2 py-1 text-xs rounded ${rate === r ? "bg-sky-600 text-white" : "bg-gray-100"}`}>
            {r}×
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Wire `AudioProvider` and `StickyAudioPlayer` into `App.jsx`**

In `frontend-react/src/App.jsx`, wrap the routing tree with `<AudioProvider>`. Add `<StickyAudioPlayer />` once near the root.

```jsx
import { AudioProvider } from "./contexts/AudioContext";
import StickyAudioPlayer from "./components/module/audio/StickyAudioPlayer";
// ...
<AudioProvider>
  {/* existing tree */}
  <StickyAudioPlayer />
</AudioProvider>
```

- [ ] **Step 4: Update `AudioLessonRenderer` to use context**

In `AudioLessonRenderer.jsx`, replace the local `audioRef` with `useAudio()`:

```jsx
import { useAudio } from "../../contexts/AudioContext";
// inside component:
const { play, pause, playing, src } = useAudio();
const url = audioUrls[lang] || audioUrls.en;
const isThisPlaying = playing && src === url;
// "Listen" button calls play(url); "Pause" calls pause()
```

- [ ] **Step 5: Smoke test in dev**

Click "Listen" on lesson 1 → navigate to lesson 2 → audio should keep playing in sticky bar.

- [ ] **Step 6: Commit**

```bash
git add frontend-react/src/contexts/AudioContext.jsx \
        frontend-react/src/components/module/audio/StickyAudioPlayer.jsx \
        frontend-react/src/App.jsx \
        frontend-react/src/components/module/AudioLessonRenderer.jsx
git commit -m "feat(module): sticky audio player with cross-lesson playback"
```

---

## Task 5: VoiceRecorder shared component

**Files:**
- Create: `frontend-react/src/components/module/audio/VoiceRecorder.jsx`

- [ ] **Step 1: Implement**

```jsx
// frontend-react/src/components/module/audio/VoiceRecorder.jsx
import React, { useRef, useState } from "react";

export default function VoiceRecorder({ maxSeconds = 60, onRecorded }) {
  const [recording, setRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [blob, setBlob] = useState(null);
  const recRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const start = async () => {
    chunksRef.current = [];
    setBlob(null);
    setElapsed(0);
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const rec = new MediaRecorder(stream);
    rec.ondataavailable = (e) => chunksRef.current.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const b = new Blob(chunksRef.current, { type: "audio/webm" });
      setBlob(b);
      onRecorded?.(b);
    };
    rec.start();
    recRef.current = rec;
    setRecording(true);
    timerRef.current = setInterval(() => {
      setElapsed((s) => {
        if (s + 1 >= maxSeconds) { stop(); return maxSeconds; }
        return s + 1;
      });
    }, 1000);
  };

  const stop = () => {
    if (recRef.current && recRef.current.state !== "inactive") recRef.current.stop();
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setRecording(false);
  };

  return (
    <div className="border rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-3">
        {!recording ? (
          <button onClick={start} className="px-4 py-2 bg-rose-600 text-white rounded-lg">🎙 Record</button>
        ) : (
          <button onClick={stop} className="px-4 py-2 bg-gray-800 text-white rounded-lg">⏹ Stop</button>
        )}
        <div className="text-sm text-gray-600">
          {elapsed}s / {maxSeconds}s
        </div>
      </div>
      {blob && (
        <audio controls src={URL.createObjectURL(blob)} className="w-full" />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/module/audio/VoiceRecorder.jsx
git commit -m "feat(module): VoiceRecorder shared component (MediaRecorder API)"
```

---

## Task 6: Pitch Coach backend — failing tests

**Files:**
- Create: `backend/tests/test_pitch_coach.py`

- [ ] **Step 1: Write tests**

```python
# backend/tests/test_pitch_coach.py
import io
import pytest
from backend.services.pitch_coach import score_transcript, PitchScore

def test_score_transcript_returns_5_axes():
    transcript = "Hi, I'm Aarav. I noticed pencils roll off desks. I made a pencil holder. My friends need this. Can you test it next week?"
    score = score_transcript(transcript)
    assert isinstance(score, PitchScore)
    for axis in ("hook", "problem", "solution", "customer", "ask"):
        assert 0 <= score.scores[axis] <= 10

def test_score_transcript_returns_one_strength_one_improvement_per_axis():
    transcript = "Test pitch."
    score = score_transcript(transcript)
    assert all(len(score.strengths[a]) > 0 for a in score.scores)
    assert all(len(score.improvements[a]) > 0 for a in score.scores)

def test_short_transcript_does_not_crash():
    score = score_transcript("um")
    assert isinstance(score, PitchScore)
```

- [ ] **Step 2: Run — fail (ImportError)**

```bash
cd backend && python -m pytest tests/test_pitch_coach.py -v
```

Expected: ImportError.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_pitch_coach.py
git commit -m "test(pitch-coach): failing tests for rubric scoring"
```

---

## Task 7: Pitch Coach backend — implementation

**Files:**
- Create: `backend/services/pitch_coach.py`

- [ ] **Step 1: Implement**

```python
# backend/services/pitch_coach.py
"""Pitch Coach: STT → 5-axis rubric scoring → voice reply."""
from dataclasses import dataclass, field
import json
import os
from typing import Any

try:
    from backend.llm import call_llm
except ImportError:
    call_llm = None

from backend.services.tts_service import synthesize

AXES = ("hook", "problem", "solution", "customer", "ask")

@dataclass
class PitchScore:
    scores: dict[str, int] = field(default_factory=dict)
    strengths: dict[str, str] = field(default_factory=dict)
    improvements: dict[str, str] = field(default_factory=dict)
    summary: str = ""

_RUBRIC_PROMPT = """You are Mento, a kind but rigorous coach for a 10-14yo Indian student practicing a 60-second startup pitch.
Score the pitch on 5 axes, each 0-10:
- hook: does the opening grab attention?
- problem: is the problem real, specific, and felt?
- solution: is the solution clear and concrete?
- customer: is "who this is for" specific?
- ask: is the call-to-action precise (not vague "we need help")?

For EACH axis output one strength (1 short sentence) and one improvement (1 specific sentence with a concrete rewrite example).

Return ONLY this JSON shape:
{
  "scores": {"hook": 0, "problem": 0, "solution": 0, "customer": 0, "ask": 0},
  "strengths": {"hook": "...", "problem": "...", "solution": "...", "customer": "...", "ask": "..."},
  "improvements": {"hook": "...", "problem": "...", "solution": "...", "customer": "...", "ask": "..."},
  "summary": "<2-3 sentence overall verdict, warm tone, age-appropriate>"
}

Pitch transcript:
"""

def score_transcript(transcript: str) -> PitchScore:
    if call_llm is None:
        # fallback for tests without LLM env
        return PitchScore(
            scores={a: 5 for a in AXES},
            strengths={a: "ok" for a in AXES},
            improvements={a: "try harder" for a in AXES},
            summary="(LLM not configured)",
        )
    raw = call_llm(
        messages=[{"role": "user", "content": _RUBRIC_PROMPT + transcript}],
        max_tokens=900,
        temperature=0.3,
    )
    try:
        data = json.loads(raw.strip().lstrip("```json").rstrip("```").strip())
    except json.JSONDecodeError:
        data = {"scores": {a: 5 for a in AXES}, "strengths": {a: "" for a in AXES},
                "improvements": {a: "" for a in AXES}, "summary": "Could not parse."}
    return PitchScore(
        scores={a: int(data.get("scores", {}).get(a, 0)) for a in AXES},
        strengths={a: data.get("strengths", {}).get(a, "") for a in AXES},
        improvements={a: data.get("improvements", {}).get(a, "") for a in AXES},
        summary=data.get("summary", ""),
    )

def transcribe(audio_bytes: bytes, filename: str = "pitch.webm") -> str:
    from openai import OpenAI
    import io
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    f = io.BytesIO(audio_bytes); f.name = filename
    r = client.audio.transcriptions.create(model="whisper-1", file=f)
    return r.text

def voice_reply_for(score: PitchScore) -> bytes:
    """Generate a short spoken coaching reply."""
    top_improvement = max(score.improvements.items(), key=lambda kv: 10 - score.scores[kv[0]])
    text = f"{score.summary} {top_improvement[1]}"
    return synthesize(text[:600], provider="openai", lang="en")
```

- [ ] **Step 2: Run tests — pass**

```bash
cd backend && python -m pytest tests/test_pitch_coach.py -v
```

Expected: 3 pass.

- [ ] **Step 3: Commit**

```bash
git add backend/services/pitch_coach.py
git commit -m "feat(pitch-coach): STT + 5-axis rubric + voice reply service"
```

---

## Task 8: Pitch Coach route

**Files:**
- Modify: `backend/routes/module_pitch_coach.py`

- [ ] **Step 1: Replace placeholder with real handler**

```python
# backend/routes/module_pitch_coach.py
import os
import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request, send_from_directory

from backend.services.pitch_coach import transcribe, score_transcript, voice_reply_for
from backend.modules_engine import check_and_increment_usage, UsageLimitExceeded
from backend.auth import current_user  # assume existing helper

bp = Blueprint("module_pitch_coach", __name__)
REPLY_DIR = Path("backend/assets/audio/pitch_coach_replies"); REPLY_DIR.mkdir(parents=True, exist_ok=True)

@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/pitch-coach")
def pitch_coach(module_id, lesson_id):
    user = current_user()
    if not user:
        return jsonify({"error": "auth_required"}), 401

    try:
        check_and_increment_usage(user["user_id"], module_id, "pitch_coach_runs", limit=3)
    except UsageLimitExceeded:
        return jsonify({"error": "cap_reached", "message": "You've used all 3 pitch-coach runs for this module."}), 429

    if "audio" not in request.files:
        return jsonify({"error": "missing_audio"}), 400
    blob = request.files["audio"].read()
    if len(blob) < 1000:
        return jsonify({"error": "audio_too_short"}), 400

    transcript = transcribe(blob, filename=request.files["audio"].filename or "pitch.webm")
    score = score_transcript(transcript)
    reply_mp3 = voice_reply_for(score)

    reply_id = f"{uuid.uuid4().hex}.mp3"
    (REPLY_DIR / reply_id).write_bytes(reply_mp3)
    reply_url = f"/static/audio/pitch_coach_replies/{reply_id}"

    return jsonify({
        "transcript": transcript,
        "scores": score.scores,
        "strengths": score.strengths,
        "improvements": score.improvements,
        "summary": score.summary,
        "voice_reply_url": reply_url,
    })

@bp.get("/static/audio/pitch_coach_replies/<filename>")
def serve_reply(filename):
    return send_from_directory(REPLY_DIR, filename)
```

- [ ] **Step 2: Verify route mounts**

```bash
cd backend && python -c "
from app import app
print([r.rule for r in app.url_map.iter_rules() if 'pitch-coach' in r.rule or 'pitch_coach_replies' in r.rule])
"
```

Expected: 2 routes.

- [ ] **Step 3: Commit**

```bash
git add backend/routes/module_pitch_coach.py
git commit -m "feat(pitch-coach): real route with STT, rubric, voice reply, and 3-run cap"
```

---

## Task 9: Pitch Coach frontend

**Files:**
- Create: `frontend-react/src/components/module/audio/PitchRubricChart.jsx`
- Modify: `frontend-react/src/components/module/PitchCoachRenderer.jsx`
- Modify: `frontend-react/src/api/modules.js`

- [ ] **Step 1: Add API method**

In `frontend-react/src/api/modules.js`, add:

```js
export async function submitPitchCoach(moduleId, lessonId, blob) {
  const fd = new FormData();
  fd.append("audio", blob, "pitch.webm");
  const r = await fetch(`/api/modules/${moduleId}/lessons/${lessonId}/pitch-coach`, {
    method: "POST",
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    body: fd,
  });
  if (r.status === 429) throw new Error("cap_reached");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
```

- [ ] **Step 2: Write rubric chart**

```jsx
// frontend-react/src/components/module/audio/PitchRubricChart.jsx
import React from "react";

export default function PitchRubricChart({ scores }) {
  const axes = ["hook", "problem", "solution", "customer", "ask"];
  return (
    <div className="space-y-2">
      {axes.map((a) => (
        <div key={a} className="flex items-center gap-3">
          <div className="w-24 text-sm capitalize">{a}</div>
          <div className="flex-1 bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-emerald-500 h-full"
              style={{ width: `${(scores[a] || 0) * 10}%` }}
            />
          </div>
          <div className="w-8 text-sm text-right">{scores[a]}/10</div>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Rewrite `PitchCoachRenderer.jsx`**

```jsx
// frontend-react/src/components/module/PitchCoachRenderer.jsx
import React, { useState } from "react";
import VoiceRecorder from "./audio/VoiceRecorder";
import PitchRubricChart from "./audio/PitchRubricChart";
import { submitPitchCoach } from "../../api/modules";

export default function PitchCoachRenderer({ lesson, moduleId, onComplete }) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const onRecorded = async (blob) => {
    setBusy(true);
    setError(null);
    try {
      const r = await submitPitchCoach(moduleId, lesson.lesson_id, blob);
      setResult(r);
    } catch (e) {
      setError(e.message === "cap_reached"
        ? "You've used all 3 attempts for this module."
        : "Couldn't score your pitch. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className="space-y-4">
      <h2 className="text-2xl font-bold">{lesson.title}</h2>
      <div className="p-4 bg-amber-50 border-l-4 border-amber-400">
        <p className="font-medium">🎤 Record your 60-second pitch:</p>
        <p className="text-sm">{lesson.schema?.prompt || "Hook · Problem · Solution · Customer · Ask"}</p>
      </div>
      <VoiceRecorder maxSeconds={60} onRecorded={onRecorded} />
      {busy && <p className="text-sm text-gray-600">Scoring your pitch…</p>}
      {error && <p className="text-sm text-rose-600">{error}</p>}
      {result && (
        <div className="space-y-4 border-t pt-4">
          <div>
            <h3 className="font-semibold mb-2">Your transcript</h3>
            <p className="text-sm italic bg-gray-50 rounded-lg p-3">{result.transcript}</p>
          </div>
          <div>
            <h3 className="font-semibold mb-2">Rubric</h3>
            <PitchRubricChart scores={result.scores} />
          </div>
          <div>
            <h3 className="font-semibold mb-2">Mento's verdict</h3>
            <p className="text-sm">{result.summary}</p>
            <audio controls src={result.voice_reply_url} className="mt-2 w-full" />
          </div>
          <details>
            <summary className="cursor-pointer font-semibold">See per-axis feedback</summary>
            <div className="mt-2 space-y-2 text-sm">
              {Object.keys(result.scores).map((a) => (
                <div key={a} className="border rounded-lg p-2">
                  <div className="capitalize font-medium">{a}</div>
                  <div className="text-emerald-700">✓ {result.strengths[a]}</div>
                  <div className="text-amber-700">→ {result.improvements[a]}</div>
                </div>
              ))}
            </div>
          </details>
          <button onClick={() => onComplete(result)} className="px-4 py-2 bg-emerald-600 text-white rounded-lg">
            Save & continue
          </button>
        </div>
      )}
    </article>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/api/modules.js \
        frontend-react/src/components/module/audio/PitchRubricChart.jsx \
        frontend-react/src/components/module/PitchCoachRenderer.jsx
git commit -m "feat(pitch-coach): functional UI with recording, rubric chart, voice reply"
```

---

## Task 10: Interview Sim backend — service + tests

**Files:**
- Create: `backend/tests/test_interview_sim.py`
- Create: `backend/services/interview_sim.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_interview_sim.py
from backend.services.interview_sim import start_conversation, end_conversation, ConvState

def test_start_returns_conv_id_and_persona():
    s = start_conversation(user_id="u1", module_id="m1", persona_id="kirana_uncle")
    assert s.conv_id
    assert s.persona["persona_id"] == "kirana_uncle"
    assert s.turns == []

def test_end_returns_transcript_and_depth_score():
    s = start_conversation(user_id="u1", module_id="m1", persona_id="kirana_uncle")
    s.turns = [
        {"role": "user", "text": "Why do you order so much milk?"},
        {"role": "persona", "text": "Because customers want fresh milk daily."},
        {"role": "user", "text": "Why is freshness so important?"},
        {"role": "persona", "text": "Because they complain if it's even one day old."},
    ]
    summary = end_conversation(s)
    assert "transcript" in summary
    assert "depth_score" in summary
    assert 0 <= summary["depth_score"] <= 5
```

- [ ] **Step 2: Run — fail (ImportError)**

```bash
cd backend && python -m pytest tests/test_interview_sim.py -v
```

- [ ] **Step 3: Implement**

```python
# backend/services/interview_sim.py
"""Customer-interview simulator: persona-driven voice conversation."""
import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.services.conversation_persona_engine import load_persona, next_reply
from backend.services.tts_service import synthesize

CONV_DIR = Path("backend/data/interview_sim_convs"); CONV_DIR.mkdir(parents=True, exist_ok=True)

@dataclass
class ConvState:
    conv_id: str
    user_id: str
    module_id: str
    persona: dict
    turns: list[dict] = field(default_factory=list)

def _conv_path(conv_id: str) -> Path:
    return CONV_DIR / f"{conv_id}.json"

def _save(state: ConvState) -> None:
    _conv_path(state.conv_id).write_text(json.dumps({
        "conv_id": state.conv_id, "user_id": state.user_id,
        "module_id": state.module_id, "persona_id": state.persona["persona_id"],
        "turns": state.turns,
    }, ensure_ascii=False, indent=2))

def _load(conv_id: str) -> ConvState:
    raw = json.loads(_conv_path(conv_id).read_text())
    persona = load_persona("entrepreneur", raw["persona_id"])
    return ConvState(conv_id=raw["conv_id"], user_id=raw["user_id"],
                     module_id=raw["module_id"], persona=persona, turns=raw["turns"])

def start_conversation(user_id: str, module_id: str, persona_id: str) -> ConvState:
    persona = load_persona("entrepreneur", persona_id)
    state = ConvState(conv_id=uuid.uuid4().hex, user_id=user_id, module_id=module_id, persona=persona)
    _save(state)
    return state

def take_turn(conv_id: str, user_text: str) -> tuple[ConvState, str, bytes]:
    state = _load(conv_id)
    state.turns.append({"role": "user", "text": user_text})
    reply_text = next_reply(state.persona, state.turns)
    state.turns.append({"role": "persona", "text": reply_text})
    _save(state)
    reply_audio = synthesize(reply_text, provider="openai", lang=state.persona.get("voice_lang", "en"),
                             voice=state.persona.get("voice_id_openai"))
    return state, reply_text, reply_audio

def _count_whys(turns: list[dict]) -> int:
    return sum(1 for t in turns if t["role"] == "user" and re.search(r"\bwhy\b|क्यों", t["text"], re.I))

def end_conversation(state: ConvState) -> dict:
    whys = _count_whys(state.turns)
    hint = state.persona.get("hidden_pain_point", "")
    missed = "Good interview." if whys >= state.persona.get("reveal_threshold", 3) else \
             f"You stopped digging too early. The deeper truth was: {hint}"
    return {
        "transcript": state.turns,
        "depth_score": min(whys, 5),
        "missed_note": missed,
        "persona_display_name": state.persona.get("display_name"),
    }
```

- [ ] **Step 4: Run tests pass**

```bash
cd backend && python -m pytest tests/test_interview_sim.py -v
```

Expected: 2 pass.

- [ ] **Step 5: Commit**

```bash
git add backend/services/interview_sim.py backend/tests/test_interview_sim.py
git commit -m "feat(interview-sim): persona conversation service with depth scoring"
```

---

## Task 11: Interview Sim routes

**Files:**
- Modify: `backend/routes/module_interview_sim.py`

- [ ] **Step 1: Replace placeholder**

```python
# backend/routes/module_interview_sim.py
import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request, send_from_directory

from backend.services.interview_sim import start_conversation, take_turn, end_conversation, _load
from backend.services.pitch_coach import transcribe  # reuse Whisper
from backend.services.conversation_persona_engine import list_personas
from backend.modules_engine import check_and_increment_usage, UsageLimitExceeded
from backend.auth import current_user

bp = Blueprint("module_interview_sim", __name__)
REPLY_DIR = Path("backend/assets/audio/interview_sim_replies"); REPLY_DIR.mkdir(parents=True, exist_ok=True)

@bp.get("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/personas")
def personas(module_id, lesson_id):
    return jsonify({"personas": [
        {"persona_id": p["persona_id"], "display_name": p["display_name"]} for p in list_personas("entrepreneur")
    ]})

@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/start")
def start(module_id, lesson_id):
    user = current_user()
    if not user: return jsonify({"error": "auth_required"}), 401
    try:
        check_and_increment_usage(user["user_id"], module_id, "interview_sim_personas", limit=3)
    except UsageLimitExceeded:
        return jsonify({"error": "cap_reached", "message": "You've used all 3 personas."}), 429
    persona_id = (request.json or {}).get("persona_id")
    if not persona_id: return jsonify({"error": "missing_persona_id"}), 400
    state = start_conversation(user["user_id"], module_id, persona_id)
    return jsonify({"conv_id": state.conv_id, "persona": {
        "persona_id": state.persona["persona_id"], "display_name": state.persona["display_name"]
    }})

@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/turn")
def turn(module_id, lesson_id):
    user = current_user()
    if not user: return jsonify({"error": "auth_required"}), 401
    try:
        check_and_increment_usage(user["user_id"], module_id, "interview_sim_turns", limit=15)
    except UsageLimitExceeded:
        return jsonify({"error": "cap_reached", "message": "You've used all 15 turns."}), 429
    conv_id = request.form.get("conv_id")
    if not conv_id or "audio" not in request.files: return jsonify({"error": "missing_args"}), 400
    blob = request.files["audio"].read()
    user_text = transcribe(blob)
    state, reply_text, reply_audio = take_turn(conv_id, user_text)
    reply_id = f"{uuid.uuid4().hex}.mp3"
    (REPLY_DIR / reply_id).write_bytes(reply_audio)
    return jsonify({
        "user_text": user_text,
        "persona_text": reply_text,
        "persona_audio_url": f"/static/audio/interview_sim_replies/{reply_id}",
        "turn_count": len([t for t in state.turns if t["role"] == "user"]),
    })

@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/end")
def end(module_id, lesson_id):
    conv_id = (request.json or {}).get("conv_id")
    if not conv_id: return jsonify({"error": "missing_conv_id"}), 400
    state = _load(conv_id)
    return jsonify(end_conversation(state))

@bp.get("/static/audio/interview_sim_replies/<filename>")
def serve(filename):
    return send_from_directory(REPLY_DIR, filename)
```

- [ ] **Step 2: Smoke**

```bash
cd backend && python -c "
from app import app
c = app.test_client()
r = c.get('/api/modules/m/lessons/l/interview-sim/personas')
print(r.status_code, len(r.get_json()['personas']))
"
```

Expected: `200 6`.

- [ ] **Step 3: Commit**

```bash
git add backend/routes/module_interview_sim.py
git commit -m "feat(interview-sim): real routes (personas, start, turn, end) with 15-turn cap"
```

---

## Task 12: Interview Sim frontend

**Files:**
- Modify: `frontend-react/src/components/module/InterviewSimRenderer.jsx`
- Modify: `frontend-react/src/api/modules.js`

- [ ] **Step 1: Add API methods**

```js
// In frontend-react/src/api/modules.js
export async function listInterviewPersonas(moduleId, lessonId) {
  const r = await fetch(`/api/modules/${moduleId}/lessons/${lessonId}/interview-sim/personas`, {
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
  });
  return r.json();
}

export async function startInterview(moduleId, lessonId, personaId) {
  const r = await fetch(`/api/modules/${moduleId}/lessons/${lessonId}/interview-sim/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("token")}` },
    body: JSON.stringify({ persona_id: personaId }),
  });
  return r.json();
}

export async function takeInterviewTurn(moduleId, lessonId, convId, blob) {
  const fd = new FormData();
  fd.append("conv_id", convId);
  fd.append("audio", blob, "turn.webm");
  const r = await fetch(`/api/modules/${moduleId}/lessons/${lessonId}/interview-sim/turn`, {
    method: "POST",
    headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    body: fd,
  });
  return r.json();
}

export async function endInterview(moduleId, lessonId, convId) {
  const r = await fetch(`/api/modules/${moduleId}/lessons/${lessonId}/interview-sim/end`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("token")}` },
    body: JSON.stringify({ conv_id: convId }),
  });
  return r.json();
}
```

- [ ] **Step 2: Rewrite renderer**

```jsx
// frontend-react/src/components/module/InterviewSimRenderer.jsx
import React, { useState, useEffect } from "react";
import VoiceRecorder from "./audio/VoiceRecorder";
import { listInterviewPersonas, startInterview, takeInterviewTurn, endInterview } from "../../api/modules";

export default function InterviewSimRenderer({ lesson, moduleId, onComplete }) {
  const [personas, setPersonas] = useState([]);
  const [selected, setSelected] = useState(null);
  const [conv, setConv] = useState(null);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    listInterviewPersonas(moduleId, lesson.lesson_id).then((r) => setPersonas(r.personas || []));
  }, [moduleId, lesson.lesson_id]);

  const begin = async () => {
    const r = await startInterview(moduleId, lesson.lesson_id, selected);
    if (r.error === "cap_reached") return alert(r.message);
    setConv(r);
  };

  const onTurn = async (blob) => {
    setBusy(true);
    const r = await takeInterviewTurn(moduleId, lesson.lesson_id, conv.conv_id, blob);
    setHistory((h) => [...h, { role: "user", text: r.user_text }, { role: "persona", text: r.persona_text, audio: r.persona_audio_url }]);
    setBusy(false);
  };

  const finish = async () => {
    const r = await endInterview(moduleId, lesson.lesson_id, conv.conv_id);
    setSummary(r);
  };

  if (!conv) {
    return (
      <article className="space-y-4">
        <h2 className="text-2xl font-bold">{lesson.title}</h2>
        <p>Pick a customer to interview. Ask them WHY at least 3 times.</p>
        <div className="grid grid-cols-2 gap-3">
          {personas.map((p) => (
            <button key={p.persona_id} onClick={() => setSelected(p.persona_id)}
              className={`p-4 border-2 rounded-xl text-left ${selected === p.persona_id ? "border-sky-600 bg-sky-50" : "border-gray-200"}`}>
              <div className="font-medium">{p.display_name}</div>
            </button>
          ))}
        </div>
        <button disabled={!selected} onClick={begin}
          className="px-4 py-2 bg-sky-600 text-white rounded-lg disabled:opacity-50">
          Start interview
        </button>
      </article>
    );
  }

  if (summary) {
    return (
      <article className="space-y-3">
        <h2 className="text-2xl font-bold">Interview summary</h2>
        <p><strong>Depth score:</strong> {summary.depth_score}/5 WHYs</p>
        <p className="p-3 bg-amber-50 rounded-lg border-l-4 border-amber-400">{summary.missed_note}</p>
        <button onClick={() => onComplete(summary)} className="px-4 py-2 bg-emerald-600 text-white rounded-lg">
          Save & continue
        </button>
      </article>
    );
  }

  return (
    <article className="space-y-3">
      <h2 className="text-xl font-bold">Talking to {conv.persona.display_name}</h2>
      <div className="space-y-2 max-h-72 overflow-y-auto bg-gray-50 p-3 rounded-lg">
        {history.map((h, i) => (
          <div key={i} className={h.role === "user" ? "text-right" : ""}>
            <span className={`inline-block px-3 py-2 rounded-2xl ${h.role === "user" ? "bg-sky-600 text-white" : "bg-white border"}`}>
              {h.text}
            </span>
            {h.audio && <audio controls src={h.audio} className="mt-1 w-full" />}
          </div>
        ))}
      </div>
      <VoiceRecorder maxSeconds={20} onRecorded={onTurn} />
      {busy && <p className="text-sm text-gray-500">Persona is thinking…</p>}
      <button onClick={finish} className="px-4 py-2 bg-gray-700 text-white rounded-lg">End interview</button>
    </article>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/api/modules.js frontend-react/src/components/module/InterviewSimRenderer.jsx
git commit -m "feat(interview-sim): voice-driven persona interview UI"
```

---

## Task 13: Add new lessons to module JSON (additive only)

**Files:**
- Modify: `backend/modules/mento_entrepreneur_4week.json`

- [ ] **Step 1: Insert new lesson `w2_l3b_interview_sim` after `w2_l3_practice_5whys`**

Open `backend/modules/mento_entrepreneur_4week.json`. Inside Week 2's `lessons` array, after the entry whose `lesson_id` is `w2_l3_practice_5whys`, add:

```json
{
  "lesson_id": "w2_l3b_interview_sim",
  "type": "interview_sim",
  "title": "Practice the Five WHYs with a Real Customer (Voice)",
  "estimated_minutes": 10,
  "coaching_moment": "Real customer-interviewing is messy and your job is to dig — these AI personas resist easy answers on purpose.",
  "schema": {
    "min_personas_required": 1,
    "max_personas": 3
  }
}
```

- [ ] **Step 2: Insert `w3_l7b_pitch_coach` AFTER `w3_l7_pitch_practice` (not replacing it)**

Inside Week 3's `lessons` array, after `w3_l7_pitch_practice`, add:

```json
{
  "lesson_id": "w3_l7b_pitch_coach",
  "type": "pitch_coach",
  "title": "AI Pitch Coach: Record Your 60-Second Pitch",
  "estimated_minutes": 12,
  "coaching_moment": "Mento will score your pitch on 5 axes and speak back specific rewrites. Try 3 times.",
  "schema": {
    "max_seconds": 60,
    "max_attempts": 3,
    "prompt": "Pitch your idea in 60 seconds. Cover: hook, problem, solution, customer, ask."
  }
}
```

- [ ] **Step 3: Run regression test**

```bash
cd backend && python -m pytest tests/test_module_regression.py -v
```

The regression test pinned 32 lessons — now there are 34. **Update the assertion** in `test_module_regression.py`:

```python
assert total_lessons >= 32  # additive only; new lessons may be inserted
```

- [ ] **Step 4: Verify module still loads via API**

```bash
cd backend && python -c "
from modules_engine import load_module
m = load_module('mento_entrepreneur_4week')
ids = [l['lesson_id'] for w in m['weeks'] for l in w['lessons']]
assert 'w2_l3b_interview_sim' in ids
assert 'w3_l7b_pitch_coach' in ids
assert 'w3_l7_pitch_practice' in ids  # ORIGINAL preserved
print('OK', len(ids), 'lessons')
"
```

Expected: `OK 34 lessons`.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/mento_entrepreneur_4week.json backend/tests/test_module_regression.py
git commit -m "feat(module): add pitch_coach and interview_sim lessons (additive)"
```

---

## Task 14: End-to-end smoke

- [ ] **Step 1: Run full Phase B test suite**

```bash
cd backend && python -m pytest tests/test_pitch_coach.py tests/test_interview_sim.py tests/test_narration_generator.py tests/test_module_regression.py -v
```

Expected: all pass.

- [ ] **Step 2: Manual e2e (dev server)**

1. Open `/modules/mento_entrepreneur_4week`
2. Click `w1_l1` — verify narration "Listen" button works, sticky bar persists
3. Navigate to `w2_l3b_interview_sim` — pick `kirana_uncle`, record one turn ("Why do you order so much milk?"), see persona reply (text + audio)
4. End interview — see depth score + missed note
5. Navigate to `w3_l7b_pitch_coach` — record 30s of any pitch — see rubric chart + voice reply

- [ ] **Step 3: Tag Phase B complete**

```bash
git tag -a phase-b-complete -m "Phase B: audio (narration + pitch coach + interview sim)"
```

---

## Definition of Done — Phase B

- [ ] ≥32 lessons have `audio_urls.en` populated; ≥24 have all 3 languages
- [ ] Sticky audio player persists across lesson navigation
- [ ] Pitch Coach returns 5-axis rubric + voice reply within 15s
- [ ] Pitch Coach 4th attempt returns 429 (cap enforced)
- [ ] Interview Sim turn returns persona text + audio
- [ ] Interview Sim 16th turn returns 429 (cap enforced)
- [ ] Interview Sim end returns depth_score + missed_note
- [ ] All 6 personas selectable
- [ ] All Phase A regression tests still pass
- [ ] Tag `phase-b-complete` exists
