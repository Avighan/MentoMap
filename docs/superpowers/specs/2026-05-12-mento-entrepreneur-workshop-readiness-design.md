# Mento Entrepreneur Workshop — Workshop-Readiness Design

**Module:** `mento_entrepreneur_4week`
**Date:** 2026-05-12
**Status:** Design (pre-implementation)
**Pilot scope:** Single live cohort (8–12 students), founder/team running the first run end-to-end.
**Primary commercial SKU:** "Mento Founder Lab" — 4-week live cohort at ₹2,499–₹3,999, using this module as the asynchronous backbone. The ₹100 standalone module is a secondary/upsell SKU. Implementation must support both shapes from day one.

---

## 1. Goal

Make `mento_entrepreneur_4week` production-ready for a real 4-week classroom workshop with Indian middle-school students (ages 10–14). "Ready" means:

1. Nothing in the module depends on a flaky external service.
2. Every lesson can be **heard** (EN + HI), not just read.
3. Students can practice the two highest-leverage entrepreneurial skills — *pitching* and *customer interviewing* — **by voice**, with AI feedback.
4. Every concept has an **Indian anchor** (founders, currency, regulations, failures).
5. The module ends with **proof of learning**: a certificate, a skill-delta report, and a student-authored "first pitch deck" PDF.
6. The module **supports a live-cohort delivery model** (scheduled live sessions, founder cameos, RSVP) without forcing it — same module serves async-only buyers too.
7. The module **produces shareable, viral artifacts** parents can post to WhatsApp / Instagram — the skill report card and pitch-deck PDF are growth assets.
8. Cost is bounded: a known ceiling per student per module.

This work is bundled into three thematic groups (1 = audio, 2 = Indian context, 3 = closing-the-loop) plus an infrastructure phase that unblocks them.

---

## 2. Audit summary (current state)

The module is structurally healthy. From the 2026-05-11 audit:

- 32 lessons, 6 games, 8 worksheets, 4 quizzes, 1 field mission, 1 reflection.
- All referenced game IDs and fallbacks exist.
- All worksheet/lesson types have working React renderers.
- Backend module engine, progress tracking, cohort assignment, and field-mission storage all work.

**Known risks this spec resolves:**

| Risk | Impact | Resolved by |
|---|---|---|
| All 32 hero images sourced from `image.pollinations.ai` | Module breaks if service is down | Phase A — self-host |
| Module advertises `hi` but no Hindi content exists | False promise; loss of trust | Phase B — narration generation |
| Quizzes are diagnostic-only; no completion proof | Workshop can't issue certificates | Phase C — certificate wiring |
| "Voice" is advertised in renderer but no module lesson uses it | Wasted infra; no real voice practice | Phase B — pitch coach + interview sim |
| No India-specific examples; all content is generic global | Cultural disconnect with target audience | Phase D — content layer |

---

## 3. Backend infrastructure changes (Phase A — prerequisite)

These land before any bundle. They are net-additive; no schema migrations, no breaking changes.

### 3.1 TTS service (`backend/services/tts_service.py`) — NEW

Wraps both OpenAI TTS (`tts-1` / `tts-1-hd`) and ElevenLabs (multilingual v2). Used for narration pre-generation and runtime pitch-coach voice replies.

```
tts_service.synthesize(
    text: str,
    voice: str = "mento_default",
    lang: Literal["en", "hi", "hi-mix"] = "en",
    provider: Literal["openai", "elevenlabs"] = "openai",  # default OpenAI for cost
    cache_key: str | None = None,
) -> bytes  # mp3
```

**Provider routing rules** (decided here so we don't re-litigate per feature):

- **Pre-generated narration** (one-time, 32 lessons × 2 langs = 64 files): **ElevenLabs** (quality matters for repeated listening; cost is one-time).
- **Pitch coach voice reply** (runtime, short, capped at 3/student/module): **OpenAI TTS** (cheap, fast, latency-sensitive).
- **Customer-interview persona responses** (runtime, conversational): **OpenAI TTS** with a per-persona voice ID.

**Caching:** SHA1 of `(text, voice, lang, provider)` → `backend/assets/audio/cache/<hash>.mp3`. Narration writes to `backend/assets/audio/module/<module_id>/<lesson_id>/<lang>.mp3` (stable paths so module JSON can reference them).

**Cost tracking:** Every synthesis call routed through existing `cost_tracker.py` with new categories `tts_openai` and `tts_elevenlabs`.

### 3.2 Self-host module hero images

One-time script `backend/scripts/cache_module_images.py`:
- Walk `backend/modules/mento_entrepreneur_4week.json`
- Download every `image_url` from `image.pollinations.ai`
- Save to `backend/assets/module_images/mento_entrepreneur_4week/<lesson_id>.png`
- Rewrite JSON `image_url` → `/static/module_images/mento_entrepreneur_4week/<lesson_id>.png`

Flask `/static` route already serves `backend/assets/` via existing static config.

### 3.3 Expand lesson-type dispatcher

`frontend-react/src/pages/ModuleDetailPage.jsx` adds 6 new lesson types:

| Type | Renderer | Purpose |
|---|---|---|
| `audio_lesson` | `AudioLessonRenderer` (extends existing lesson) | Lesson with mandatory audio track + transcript |
| `pitch_coach` | `PitchCoachRenderer` | Voice-in / voice-out 60-sec pitch practice |
| `interview_sim` | `InterviewSimRenderer` | Conversational customer-interview practice |
| `micro_quest` | `MicroQuestRenderer` | 2–3 min single-prompt apply-it-now task |
| `case_study_card` | `CaseStudyCardRenderer` | 60–90s founder story card |
| `failure_card` | `FailureCardRenderer` | 60s startup-failure card |
| `cohort_live_session` | `CohortLiveSessionCard` | Scheduled live session (Zoom/Meet) with founder, RSVP, recording link |

All renderers live in `frontend-react/src/components/module/`. Existing types continue to dispatch unchanged.

### 3.4 Module JSON schema additions

Lesson objects may now declare:

```json
{
  "audio_urls": {"en": "...", "hi": "...", "hi_mix": "..."},
  "flashcards": [{"q": "...", "a": "...", "skill_tag": "creativity"}]
}
```

Module-level additions:

```json
{
  "audio_voice_id": "mento_default_v1",
  "completion": {
    "certificate_id": "mento_entrepreneur_cert",
    "dimension_report": true
  },
  "cost_caps": {
    "pitch_coach_runs_per_user": 3,
    "interview_sim_turns_per_user": 15,
    "interview_sim_personas_per_user": 3
  }
}
```

### 3.5 Cost guardrails (decided)

| Feature | Cap (per student per module) | Enforcement |
|---|---|---|
| Pitch Coach runs | 3 | Reject route call with 429 + friendly message after 3 |
| Customer Interview turns | 15 turns total | Same |
| Customer Interview personas | 3 distinct personas | Same |
| TTS narration | 0 runtime cost (pre-generated) | N/A |
| TTS pitch-coach reply | ≤3 per student (matches pitch runs) | Tied to pitch coach cap |
| Daily-dispatch LLM | 0 (templated, not LLM-generated) | N/A |

Caps stored per-user in `backend/data/module_progress.json` under `progress[user][module].usage`. Existing `cost_tracker.py` records the underlying API spend.

**Estimated worst-case cost per student per module** (back-of-envelope):
- Pitch coach: 3 × (~5K input + 1K output Claude tokens + ~30s OpenAI TTS) ≈ ₹4–6
- Interview sim: 15 × (~3K input + 0.5K output + ~10s TTS) ≈ ₹6–10
- Narration: amortized to ₹0 per student (~₹250–500 one-time generation)
- **Total: ~₹15/student** worst case.

### 3.6 New backend routes (summary)

All scoped under `/api/modules/<module_id>/lessons/<lesson_id>/`:

| Route | Method | Purpose |
|---|---|---|
| `/pitch-coach` | POST | `multipart` audio → transcript + rubric + voice reply URL |
| `/interview-sim/start` | POST | `{persona_id}` → opens conversation |
| `/interview-sim/turn` | POST | `multipart` audio + `conv_id` → persona reply + voice URL |
| `/interview-sim/end` | POST | `{conv_id}` → transcript + "what you missed" note |
| `/skill-report` | GET | Module-level dimension aggregation |
| `/certificate` | GET | Issue/download certificate (200 once complete, 409 otherwise) |

Module-scoped:

| Route | Method | Purpose |
|---|---|---|
| `/api/modules/<id>/idea-journal` | GET/POST/PATCH | Read/append/edit idea-journal entries |
| `/api/modules/<id>/idea-journal/export` | GET | PDF export (reuses `certificate.py` PDF stack) |
| `/api/modules/<id>/skill-report/card.png` | GET | Server-rendered parent-shareable PNG card (used by WhatsApp share) |

Cohort-scoped:

| Route | Method | Purpose |
|---|---|---|
| `/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions` | GET | List scheduled live sessions for this cohort+module |
| `/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions` | POST | Create live session (teacher/admin) |
| `/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions/<session_id>` | PATCH/DELETE | Edit/cancel |
| `/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions/<session_id>/rsvp` | POST | Student RSVP toggle |

---

## 4. Bundle 1 — Make It Speak

**Goal:** Every lesson can be heard; every pitch and customer interview is a voice exercise.

### 4.1 Lesson narration (EN + HI + Hinglish)

- Build-time script `backend/scripts/generate_module_narration.py` reads module JSON, generates one MP3 per lesson per language via ElevenLabs, writes to stable path, updates `audio_urls`.
- **Voice:** one consistent ElevenLabs voice for Mento (TBD — pick from Indian-accented multilingual voices: `Aria` / `Domi` / `Antoni`-equivalent). One distinct voice per persona for interview sim.
- **Hinglish** generated by a Claude prompt that code-switches the lesson script ("Aaj hum baat karenge entrepreneurship ki. An entrepreneur is someone who…") → then synthesized in the same Mento voice.
- **Player UI:** sticky bottom audio bar in `ModuleDetailPage.jsx` (play/pause, scrubber, 1×/1.25×/1.5×, language toggle EN / हिं / Hinglish). Persists across lessons.
- **Accessibility:** transcript always visible (already is — narration is *additive*).

### 4.2 AI Pitch Coach

Replaces `w3_l7_pitch_practice` (currently embeds `g8-tedx-pitch` game). The game becomes optional / "advanced practice"; the new lesson is the core practice.

**Flow:**
1. Student sees pitch prompt + 60s timer + "Record" button.
2. Records via existing `VoiceLessonRenderer` capture component.
3. POST audio → `/pitch-coach` → backend pipeline:
   - Whisper STT (OpenAI) → transcript.
   - Claude scores on 5-axis rubric (Hook / Problem / Solution / Customer / Ask), each 0–10, plus one strength + one improvement per axis. JSON-structured output.
   - Claude drafts a 2–3 sentence voice reply ("Great hook. Try sharpening your ask — instead of 'we need help,' say 'I need 10 friends to test this by Friday.'")
   - OpenAI TTS → reply MP3.
4. UI shows: transcript, rubric bar chart (5 axes), strengths/improvements list, "Listen to Mento's feedback" button (plays MP3).
5. Student can re-record up to 3 times per module (cap).

**Persistence:** all attempts saved under `progress[user][module].lessons[lesson_id].pitch_attempts[]` so teachers and the final report can show progression.

**Dimension scoring contribution:** each pitch attempt contributes to `communication`, `strategic_thinking`, `creativity` deltas (reuses existing dimension scoring scaffolding).

### 4.3 AI Customer Interview Simulator

NEW lesson inserted as `w2_l3b_interview_sim` (between Five WHYs and the brainstorm worksheet — natural pedagogical fit).

**Personas (v1, 6 starter personas in `backend/personas/entrepreneur/`):**

| ID | Label | Voice profile | Hidden problem |
|---|---|---|---|
| `kirana_uncle` | Kirana-shop uncle | Hindi-leaning, 40s male | Inventory waste from unpredictable demand |
| `tiffin_auntie` | Tiffin-service auntie | Hindi, 50s female | Late payments from regular customers |
| `classmate_priya` | Classmate (12yo) | Hinglish, child voice | Loses pencils every week |
| `auto_driver` | Auto-rickshaw driver | Hindi, 30s male | Customers haggle even on meter |
| `working_parent` | Working parent | English, 40s female | Can't help kid with homework, too tired |
| `hostel_student` | College hostel student | Hinglish, 20s male | Tired of mess food, no easy alternative |

Each persona is a JSON file: `{display_name, voice_id, system_prompt, hidden_pain_point, reveal_threshold}`. System prompt instructs Claude to *resist* immediately revealing the real pain — student must dig with Five WHYs to surface it.

**Flow:**
1. Student picks a persona (max 3 personas per module).
2. `/interview-sim/start` opens a conversation (`conv_id`).
3. Student records each question (audio), backend transcribes → adds to history → Claude generates persona reply → TTS → returned as audio URL.
4. Cap: 15 turns total across the module.
5. `/interview-sim/end` returns:
   - Full transcript
   - "Five WHYs depth score" (how many layers did the student dig?)
   - "What you missed" note: a 2-sentence Claude critique pointing to the real pain point the student didn't surface (if they didn't).

**Re-use:** built on top of generalized `audio_negotiation_engine.py` refactored into `services/conversation_persona_engine.py` (negotiation becomes one consumer; customer-interview becomes another).

### 4.4 Hinglish narration toggle

Already covered in 4.1 — third option in the audio bar, generated from the EN script via Claude code-switch prompt, then ElevenLabs. No additional UI surface beyond the language toggle.

---

## 5. Bundle 2 — Make It Indian

**Goal:** Every concept has an Indian anchor; the module stays warm between sessions.

### 5.1 Eight Indian founder case-study cards (`case_study_card` lesson type)

60–90 seconds each. Each card has:
- One large founder portrait (self-hosted)
- 4-line backstory ("Sridhar grew up in a Tamil Nadu village…")
- One single takeaway ("Zoho proved you don't need to leave India to build a global tech company")
- One reflection prompt ("What's something you'd build *from* your hometown?")
- Optional audio narration (Bundle 1 pipeline)

**Inserted as bonus lessons** (don't disrupt week pacing): one per week + 4 in an "Indian Founders Gallery" sidebar entry.

Founders v1 list: Sridhar Vembu, Falguni Nayar, Ritesh Agarwal, Byju Raveendran, Kunal Shah, Ghazal Alagh, Bhavish Aggarwal, + one neighborhood example.

### 5.2 Six "Failure Museum" cards (`failure_card` lesson type)

Inserted as a single grouped lesson `w4_l0b_failure_museum` (before `w4_l1_failure_journey`). Cards: Stayzilla, Doodhwala, TinyOwl, Dazo, Askme.com, Housing.com. Each: 60s, what they tried / why they failed / one lesson.

### 5.3 Currency + scenarios localized to ₹

Edits-only (no new lesson types). Files touched:
- `w3_l2_who_pays` — examples become ₹10 chai vs ₹250 cafe coffee
- `w3_l3_customer_profile` — income ranges in ₹/month brackets
- `w3_l4_idea_scorecard` — market-size axis labeled in ₹ thousands/lakhs
- `w1_l9_warmup_game` (Idea Lab) — verify game already uses ₹; if not, file as game-level fix (out of module scope but adjacent).

### 5.4 Regulatory primer (Week 4 bonus track)

Three new `audio_lesson` entries grouped as `w4_bonus_regulatory`:
1. **Udyam basics** (3 min) — what is it, why a small business registers, how it helps
2. **GST in 3 minutes** — what GST is in plain language, what threshold matters for small businesses
3. **Why your business needs its own bank account** — separation of personal/business money

Optional / does not gate certificate.

### 5.5 Daily Mento dispatch (28 messages)

- One-time content authoring: 28 short tips/questions written for the 4-week run (some link back to a lesson, some are reflective).
- APScheduler job (`_run_scheduler` already exists) — new task `_run_module_daily_dispatch()` running at 18:00 IST daily, checks every user who started the module within last 28 days, picks the next unsent message, writes to `notifications.json` via existing notification API.
- Surfaces in existing `NotificationCenter.jsx` bell. No new UI.
- Opt-in toggle in `SettingsPage.jsx` ("Daily Mento workshop tips" — defaults ON during pilot).

---

## 6. Bundle 3 — Close the Loop

**Goal:** Students see what they're learning; the module ends with proof, not a checkmark.

### 6.1 Apply-it-now micro-quests (`micro_quest` lesson type)

Four new lessons (one per week), 2–3 min each, inserted after the week's key concept:

| ID | Week | Prompt |
|---|---|---|
| `w1_quest_one_complaint` | 1 | "In the next 3 minutes, ask one person near you one complaint. Type it." |
| `w2_quest_one_why` | 2 | "Pick one complaint from W1. Ask one 'WHY' about it now. Type the answer." |
| `w3_quest_one_customer` | 3 | "Find one real person who fits your customer profile. Take a photo or write their name." |
| `w4_quest_one_pitch` | 4 | "Say your 60-sec pitch out loud to one person now. Record their reaction in 1 line." |

Renderer: simple single-input form (text OR photo OR 10-sec voice). Autosaves to progress. Contributes to Idea Journal.

### 6.2 Spaced-repetition card seeding

- Each lesson optionally declares `flashcards: [...]`.
- Authoring target: ~20 cards across the module (5/week).
- On lesson completion, cards inject into the student's SR queue via `spaced_repetition.py` (already SM-2-based).
- No new UI — existing `/spaced-repetition` page renders them.
- Cards tagged with `module_id` so the SR page can filter "Cards from your Entrepreneurship Workshop."

### 6.3 Idea Journal

Persistent per-user notebook keyed by `(user_id, module_id)`.

**Auto-population:** every worksheet save AND every micro-quest submission appends an entry of `{lesson_id, lesson_title, content, timestamp, type}`.

**UI:** new sidebar entry "📒 My Idea Journal" in `ModuleDetailPage.jsx`. Click → side drawer listing all entries chronologically, grouped by week. Student can:
- Edit any entry
- Star favorites
- Add free-form entries any time

**Export:** "Download My Pitch Deck" button at module end → POST `/api/modules/<id>/idea-journal/export` → PDF via existing `certificate.py` PDF stack (extend with a deck template: cover page, problem, customer, solution, pitch transcript, journey timeline).

**Storage:** `backend/data/idea_journals/<user_id>__<module_id>.json`. Append-only with edit history retained (for teacher visibility).

### 6.4 Founder XP + streak in module hero

No new backend (already computed by existing infra). Render in `ModuleDetailPage.jsx`:
- Streak badge (🔥 N days)
- Module-specific XP earned this week
- 4 milestone badges across the top: 🌱 Idea Validator (W1), 🔍 Problem Detective (W2), 🎤 Pitch Builder (W3), 🚀 Founder (W4) — grey until earned, gold when earned.

Award logic: each week's quiz checkpoint + ≥80% lesson completion = earn that week's badge.

### 6.5 Certificate on completion

- `modules_engine.check_module_completion()` extended to return `{complete: bool, certificate_eligible: bool}`.
- New route `/api/modules/<id>/certificate` mints via existing `certificate.py` with `cert_type=mento_entrepreneur_cert`.
- UI: completion screen in `ModuleDetailPage` shows "🎓 Download your Certificate" button.
- Student name + completion date + cohort + skill highlights on the PDF.

### 6.6 Module skill report

- New route `/api/modules/<id>/skill-report` aggregates dimension scores from:
  - 6 embedded game completions (uses existing per-game dimension scores)
  - 4 quiz scores (mapped to relevant dimensions per quiz tag)
  - 1 pitch-coach final attempt (communication, creativity, strategic_thinking)
  - Interview-sim depth score (empathy, strategic_thinking)
- Reuses existing `_compute_*_dimension_scores` helpers.
- Returns `{dimensions: {empathy: 72, creativity: 84, ...}, deltas_from_baseline: {...}, highlights: [...], recommendations: [next-module-id, ...]}`.
- Renders at `/modules/:id/report` (route already exists, currently stub). Layout reuses `PostGameInsights.jsx` patterns.

**Parent-shareable artifact (growth asset):**

- Server-rendered PNG card via new route `/api/modules/<id>/skill-report/card.png`. Uses the same Pillow/ReportLab stack as `certificate.py`. Output: 1080×1080 (Instagram-square) PNG with:
  - Student first name + age + module title
  - Top 3 skills with values + small radar chart
  - One headline ("Aarav finished the Mento Founder Lab. He scored 84 on creativity.")
  - Mento branding + URL
  - Cohort name (if cohort context)
- **WhatsApp share button** on `/modules/:id/report` opens `https://wa.me/?text=<message>` with a short pre-filled caption + a public CDN URL of the PNG card. On mobile, uses Web Share API (`navigator.share`) for native sheet — falls back to WhatsApp URL on desktop.
- **Instagram / X share buttons** as secondary options (same PNG, different intent URLs).
- Card is cached for 24h; regenerates on next report change.
- Privacy: shareable card uses first-name only by default; full name requires explicit student/parent opt-in toggle.

### 6.7 Cohort Live Sessions (live-cohort SKU support)

Lets a cohort run the module as a guided 4-week live experience. Async students see this section as inert (no live sessions scheduled = no UI surface). Live-cohort students see scheduled sessions prominently.

**Data model** — new file `backend/data/cohort_live_sessions.json`:

```json
{
  "<cohort_id>__<module_id>": [
    {
      "session_id": "...",
      "week": 1,
      "title": "Founder Cameo: How I started Zoho",
      "host_name": "Sridhar Vembu",
      "host_bio_short": "Founder, Zoho. Built from a Tamil Nadu village.",
      "host_avatar_url": "...",
      "scheduled_at": "2026-06-15T18:00:00+05:30",
      "duration_min": 60,
      "meeting_url": "https://meet.google.com/...",
      "rsvps": ["user_id_1", "user_id_2"],
      "recording_url": null,
      "status": "scheduled"   // scheduled | live | recorded | cancelled
    }
  ]
}
```

**Renderer (`CohortLiveSessionCard`):**

- **Top-of-module banner** in `ModuleDetailPage.jsx` when the cohort has the next session within 7 days. Shows: host avatar, "Live this Saturday — Sridhar Vembu on Zoho's origin," countdown timer, RSVP toggle, "Add to Google Calendar" link, "Join" button (active 10 min before scheduled time).
- After the session ends and `recording_url` is set, the banner converts to a "Watch recording" card and gets pinned in the relevant week's sidebar.
- For async-only students (cohort has zero scheduled sessions), banner is hidden entirely — module looks identical to today.

**Admin/teacher UI** — new tab in `AdminDashboard.jsx` → COHORTS → `<cohort>` → "Live Sessions":
- Schedule new session (datetime picker, host info, meeting URL paste)
- See RSVPs per session
- Upload/paste recording URL after session
- Cancel session (notifies RSVPs via existing `notifications.json` pipeline)

**Notifications (uses existing infra):**
- 24h before session → "Your Mento live session starts tomorrow at 6 PM"
- 1h before → "Starting in 1 hour — join link inside"
- After recording uploaded → "Missed it? Watch the recording"

**Backend** — new file `backend/cohort_live_sessions.py`:
- CRUD operations, RSVP toggle, notification scheduling (APScheduler hooks)
- Reuses `_run_scheduler` already running for streak/dispatch jobs

**Not in scope:**
- We **do not** build a video conferencing tool. Teachers paste a Google Meet / Zoom link they created externally. Reliable, free, parents already know these tools.
- We **do not** auto-record. Teacher uploads/pastes recording URL post-session.
- No live chat / Q&A widget — uses the conferencing tool's native chat.

**Why this matters commercially:**
- Enables the ₹2,499–₹3,999 cohort SKU without a separate codebase.
- Founder-cameo sessions are a content asset: clips fuel social/influencer channels.
- RSVP data + attendance becomes a signal for the skill report ("attended 3 of 4 live sessions").

---

## 7. Sequencing

| Phase | Contents | Blocking? |
|---|---|---|
| **A — Infrastructure** | TTS service, image self-host, lesson types, JSON schema, cost caps, new routes scaffolded | Blocks all bundles |
| **B — Bundle 1 (audio)** | Narration generation, Pitch Coach, Interview Simulator, Hinglish | After A |
| **C — Bundle 3 (loop)** | Idea Journal, certificate, micro-quests, SR seeding, XP, skill report, parent-shareable PNG + WhatsApp share, cohort live sessions | After A; parallel-safe with B |
| **D — Bundle 2 (Indian)** | Case-study cards, failure museum, ₹ edits, regulatory primer, daily dispatch | Mostly content; can start after A, completes last |

Phases B/C/D can interleave once A is done; A is strictly sequential.

---

## 8. Pilot scope decisions (single live cohort)

The first cohort is one 8–12 student live cohort, founder/team running it directly. The following are explicitly **deferred** to v2:

- Multi-cohort self-serve onboarding for this module.
- Teacher UI to review every `interview_sim` transcript individually (teachers can read raw JSON via existing answers endpoint for v1).
- Mass cost-cap configuration per org (single set of caps embedded in module JSON for v1; orgs can override later).
- Multi-cohort leaderboards within the module (existing leaderboards remain at platform level).
- Auto-translation of *content* into HI for new content authored after v1 (we generate HI narration *and* translate existing strings for v1, but new content added later will require manual HI authoring until a translation pipeline is built).
- Built-in video conferencing — we use Google Meet / Zoom links pasted by host.
- Built-in payments / cohort sign-up flow — pilot uses external payment link (Razorpay) + manual cohort enrollment for first run.

**In scope for pilot:** everything in Phases A–D. The pilot must be able to (1) run 4 weeks live with founder cameos, (2) produce a certificate, (3) produce a skill report + WhatsApp-shareable card, (4) survive a home-WiFi-quality network (audio prefetched, no live calls required for narration), (5) cleanly support async-only buyers without showing empty live-session UI.

---

## 9. Out of scope

- Re-architecting other modules to use Bundle 1's audio pipeline (the TTS service is reusable but rolling it out elsewhere is a separate effort).
- Building a CMS for non-technical content authors to add founder cards (v1 = JSON edits committed to repo).
- AI generation of new lessons (designer-facing; covered by separate AIDesignStudio).
- Real-time multiplayer mechanics inside this module.
- Mobile app native shell (existing PWA + responsive web is sufficient for pilot).

---

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| ElevenLabs Hindi voice quality not great for kids | Test 3 candidate voices on a sample paragraph before bulk generation; user-test with 2 students before committing |
| Pitch-coach STT mishears Indian accents | Use Whisper `large-v3` (best multilingual); fall back to text-input mode if confidence low |
| Interview-sim persona breaks character / gives away pain point too fast | Strict system prompt + few-shot examples; QA each persona by hand before pilot |
| Audio files bloat module storage / bandwidth | Pre-generate at 64kbps mono mp3, lazy-load per lesson, total budget <50MB across module |
| Cost overrun in pilot | Caps enforced server-side; daily cost report from `cost_tracker.py`; circuit-breaker at 2× expected daily spend |
| Daily dispatch annoys students/parents | Opt-in; default ON for pilot cohort only, reassess after week 1; max 1/day, easy off switch |
| Hinglish code-switching reads as patronizing | Author manual review of 4 sample lessons before generating all 32; founder/Indian team review |

---

## 11. Success criteria (for the pilot)

1. ≥80% of pilot students complete all 4 weeks.
2. ≥60% use the Pitch Coach at least once.
3. ≥50% complete at least one Customer Interview Sim conversation.
4. Median skill-report shows positive delta on ≥3 of {creativity, strategic_thinking, empathy, resilience, communication}.
5. ≥70% of pilot students successfully download their certificate and Idea Journal PDF.
6. ≥60% RSVP attendance across the 4 live sessions.
7. ≥30% of completing students share their skill-report card to WhatsApp/Instagram (measured by share-intent click).
8. Cost per student per module ≤ ₹50 (worst case, including amortized fixed costs for a 10-student cohort).
9. Zero P0 outages caused by external service failures during the 4-week pilot.
10. Parent/Teacher NPS ≥ 7 / 10 at end of pilot.

---

## 12. Open items requiring decision before plan

None that block writing the implementation plan. The following are decisions that can be made *during* implementation (call them out then):

- Exact ElevenLabs voice IDs for Mento + 6 personas (taste decision, requires sampling).
- Exact Daily Dispatch copy (content authoring task).
- Founder card portrait sourcing (licensed stock vs. illustration; can start with illustrated cartoons matching module's existing visual style).
- Regulatory primer fact-checking (likely needs one pass from someone with CA / legal background; can default to clearly labeling as "general overview, not legal advice").
