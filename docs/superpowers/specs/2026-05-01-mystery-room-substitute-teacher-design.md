# Mystery Room Pilot — "The Substitute Teacher" — Design Spec

**Date:** 2026-05-01
**Status:** Draft
**Scope:** New `mystery_room` game type + one pilot game ("The Substitute Teacher") for Grade 8

---

## 1. Overview

### Problem
MentoApp's 96 games today are uniformly turn-based or choice-driven. Multiple-choice scoring measures *what students say they would do*, not *what they do*. The weakest signal areas — resilience, creativity, and ethical reasoning — are precisely the dimensions hardest to capture with choice menus, because students learn quickly to pick the "right-sounding" answer.

### Solution
Introduce a new game type — `mystery_room` — that asks the player to **examine a 2D scene with mouse and keyboard**, pick up items, combine clues, and reach a moral climax based on what they discovered. Behavior is the assessment. The pilot is a single 13–15 minute game, "The Substitute Teacher", set in an empty staff room and classroom.

### Why this game first
- Grade 8 audience: school setting maximises relatability vs. corporate/startup framings.
- Strong cross-dimension signal (empathy, ethical reasoning, critical thinking, courage, resilience).
- Diegetic puzzles (read between the lines, interpret a child's drawing) measure judgement, not IQ.
- Reuses ~70% of existing engines (`inventory_management_engine`, `quest_engine`, `hint_engine`, `dimension_utils`, `accessibility_engine`).

### Decision gate
Before building game #2, this pilot must hit:
- Completion rate ≥ existing `story_branching` baseline (tracked via `game_starts.json`).
- Median session length 12–20 minutes.
- Hint distribution: most players use 1–2; few use 0 or all 3.
- Climax distribution: each gateable ending taken by ≥15% of qualifying players (no single-ending collapse).
- Self-reported "want to play another" ≥ 60%.

---

## 2. Premise & Narrative

### Setup
Your favorite teacher, Ms. Banerjee, has been suddenly transferred. She was beloved by her Grade 8 class but hadn't told anyone she was leaving. After school hours, during a school cultural event when adults are distracted, you slip into the empty staff room — and from there into Ms. Banerjee's classroom — to find out *why*.

What you piece together: a parent (not the school board) filed a complaint after Ms. Banerjee intervened in a private home matter to protect a student named **Aarav**. The principal, under pressure from the parent (who is a major school donor), transferred Ms. Banerjee rather than investigate. Aarav still attends the school. The truth has consequences for him, for Ms. Banerjee, and for you.

### Tone
Quiet, slightly melancholy, lived-in. Empty rooms with the feel of recent occupancy — a half-finished cup of chai, a chair pulled out, the air conditioner still humming. Not horror. Not comedic. The mood is *concern*.

### Cast (off-screen — no on-screen NPCs in v1)
- **Ms. Banerjee** — transferred teacher; her voice in voicemails and notebook margins.
- **Aarav** — Grade 8 student; his drawing and folded note are key clues.
- **Principal Sharma** — referenced in the complaint and a voicemail; the antagonist.
- **Aarav's parent** — the complainant; off-screen, named in the letter.
- **Mrs. Iyer** — a fellow teacher Ms. Banerjee trusted; potential ally.

---

## 3. Pedagogy

### Primary dimensions (5)
1. **Empathy** — drawing interpretation, voicemail tone, child's note.
2. **Ethical reasoning** — folded-note privacy fork, climax choice, evidence interpretation.
3. **Critical thinking** — email reconstruction, contradiction-spotting, evidence-board synthesis.
4. **Courage** — climax choice, willingness to act on incomplete evidence.
5. **Resilience** — recovery from dead-end clues, hint usage pattern, time-stuck behaviour.

### Light-touch dimensions (3)
6. **Strategic thinking** — order of puzzle pursuit (which space first, which clue first).
7. **Creativity** — non-obvious item combinations and drawing interpretation.
8. **Adaptability** — evidence-board re-arrangements after new info.

### Scoring model — Hybrid (Q4 = C)
- **Knowledge accuracy score (0–100):** correctness on factual puzzles 1–5. One free retry per factual puzzle (no hint-cost penalty). Used in assessment mode and reports.
- **Eight-dimension fingerprint:** weighted aggregation of `skill_tags` from every action across the session. Same path as the existing `_compute_story_dimension_scores()` in `app.py`. Includes ethical and exploratory micro-actions.
- **Outcome label** — one of: `Whistleblower`, `Quiet Protector`, `Cautious Investigator`, `Compliant Bystander`. Derived deterministically from climax choice + folded-note decision.

### Pedagogical framing
- **No ending is wrong.** Outcome is descriptive, not judgmental. The lesson lives in the dimension fingerprint, not the moral verdict on the player. This is non-negotiable; shaming the Compliant Bystander will train students to lie.
- The post-game debrief explicitly says which soft skill each ending exercised. ("Whistleblower endings exercise courage; Quiet Protector exercises empathy. Both are valid responses.")

---

## 4. Scenes & Navigation

### Two scenes
1. **Staff Room** — bureaucratic / institutional view. Holds the complaint letter, voicemails, email thread, transfer notice. Coffee mugs, staff lockers, a noticeboard.
2. **Ms. Banerjee's Classroom** — human / lived view. Holds the drawing, graded notebook, folded student note. Empty desks, a half-erased blackboard, a bookshelf.

### Movement
- A **corridor click-target** on the right edge of each scene transitions to the other.
- Inventory carries between scenes.
- No avatar character on screen — first-person POV, the camera is the player.
- No free movement within a scene; the camera is fixed, and the player examines hotspots laid over the background.

### Climax
- A modal — **"You hear footsteps. The Principal is back. Knock on her door?"** — fires when the player clicks the corridor *after* meeting the climax-trigger threshold (see §6).
- No third scene is rendered; the modal is the climax surface.

---

## 5. Puzzles (7 + climax)

All puzzles are diegetic / narrative-style. Each puzzle has 1–3 `skill_tags` driving fingerprint deltas; factual puzzles also have a correctness flag.

### Staff Room
1. **The Complaint Letter** — find it on the principal's pigeonhole, then click the signature. Player must select the correct claim: "signed by a parent" vs. "signed by the school board" vs. "anonymous".
   - Skills: critical_thinking, evidence-weighing.
   - Factual. Correct answer = parent.
2. **The Voicemails** — three 10s clips on the staff phone (TTS). Player picks which clip explains the transfer.
   - Skills: critical_thinking, empathy.
   - Factual. Correct answer = the third clip (Mrs. Iyer's worried voice).
3. **The Email Thread** — five printed emails on a desk, scattered. Drag into chronological order.
   - Skills: critical_thinking, strategic_thinking.
   - Factual. One correct sequence.

### Classroom
4. **The Student's Drawing** — found behind the bookshelf. Three interpretation options ("just a house", "a fight at home", "a memory of school"). Selection feeds the dimension fingerprint; no "wrong" answer.
   - Skills: empathy, creativity.
   - Diegetic / interpretive (not pass/fail).
5. **The Graded Notebook** — Ms. Banerjee's margin comments on Aarav's homework. Spot the line that contradicts the principal's complaint. Click the offending line.
   - Skills: critical_thinking, empathy.
   - Factual. One correct line.
6. **The Folded Note** — passed between two students, found on a desk. Two-option micro-fork: **read** or **leave folded**.
   - Skills: ethical_reasoning (privacy), curiosity vs. integrity.
   - Diegetic / interpretive. Reading reveals a clue but tags negative ethical_reasoning.

### Synthesis
7. **The Evidence Board** — modal. Player drags collected items into three buckets: "What the principal says", "What actually happened", "Doesn't fit anywhere". Three correct groupings, free retries.
   - Skills: critical_thinking, adaptability (rearrangements measured).
   - Factual. Required for top climax tier.

### Climax modal
- See §6.

### Pacing target
~90–120 seconds per puzzle; ~13–15 minutes total. Hint button always available (§7).

---

## 6. Climax & Endings

### Gating — C-mixed (Q5 = C-mixed)
| Tier | Trigger | Endings unlocked |
|---|---|---|
| Always | Reach the climax modal | Walk Away, Cautious Investigator |
| 4–5 items found | Sufficient context | + Quiet Protector |
| All 7 found + Evidence Board correctly synthesised | Full understanding | + Whistleblower |

### The four endings
Each is a 25–40 second epilogue: one DALL-E semi-realistic image + 3 short paragraphs of text. No game-over screen. No score reveal at this point — score and fingerprint reveal happen on the post-game debrief screen (§8).

| Ending | Trigger choice | Epilogue (gist) | Dimension deltas |
|---|---|---|---|
| **Whistleblower** | Confront the principal with the evidence board contents | Ms. Banerjee is reinstated after a board enquiry. You face social pushback at school. Aarav's parents thank you in private. | courage++, ethical_reasoning++, critical_thinking+, empathy+ |
| **Quiet Protector** | Slip a note to Mrs. Iyer naming Aarav (no confrontation) | Ms. Banerjee does not return, but Aarav gets quiet support from Mrs. Iyer. You sleep okay. | empathy++, ethical_reasoning+, resilience+, courage+ |
| **Cautious Investigator** | Tell a teacher generally; let adults handle it | Status quo holds. The teacher promises to "look into it." Maybe they will. | critical_thinking+, ethical_reasoning+, empathy+ (no courage delta) |
| **Compliant Bystander** | Walk away; leave everything as found | Nothing changes. You see Aarav crying at lunch the next day. | No positive deltas. No negative shaming. Honest reflection. |

### Outcome-label rule
- Climax = Confront → Whistleblower (requires top tier).
- Climax = Quiet help → Quiet Protector (requires mid tier).
- Climax = Talk to a teacher → Cautious Investigator.
- Climax = Walk away → Compliant Bystander.
- Folded-note decision (§5.6) modifies the fingerprint but does not change the label.

---

## 7. Hint Mechanic

### Policy — Hybrid (Q6 = C)
- **"🤔 I'm stuck" button** is always visible in the HUD. Three escalations on the *current focused puzzle*: nudge → pointer → solution.
- **Soft auto-prompt** at 120 seconds of puzzle inactivity. Mento mascot whispers "Need a hint?", dismissable. Fires at most once per puzzle. Configurable per game JSON (`hint_policy.auto_prompt_seconds`).
- **No score penalty** for hint usage in v1. Usage logged for analytics only.

### Implementation
- Reuse `backend/engines/hint_engine.py`. Add `HintLadder` config block to game JSON:
  ```json
  "hints": {
    "puzzle_1": ["Have you looked at all the pigeonholes?", "Try the principal's slot.", "Click the letter on top of the third pile."],
    ...
  }
  ```
- Frontend tracks idle time per puzzle in `MysteryRoomRenderer.jsx` state.

---

## 8. Post-game Debrief

Reuses existing `PostGameInsights.jsx` with a new optional slot **`MysteryRoomEpilogue`** rendered before the standard insights panel.

The epilogue panel shows:
1. **Outcome label** with a one-line description.
2. **Dimension fingerprint** (radar chart — uses existing `LiveSkillRadar`).
3. **Knowledge accuracy** — "You correctly identified 4 of 5 facts."
4. **What you missed** — list of clues not found, lightly spoiled, encouraging replay.
5. **Soft-skill named** — "This ending exercises courage. Players who choose this typically score higher in ethical_reasoning."
6. **Recommendation** — uses existing adaptive-recommendation API to suggest a follow-up game from the weakest dimension.

Replay is enabled. Past attempts and their outcome labels are persisted in the player profile for parent/teacher reports.

---

## 9. Backend Architecture

### New files
- `backend/engines/escape_room_engine.py` — orchestrator (~600–900 LOC). Public surface:
  - `EscapeRoomEngine.start(run_state, game_def)` — initialises rooms, hotspots, items, locks, evidence-board state.
  - `EscapeRoomEngine.handle_action(run_state, action)` — dispatches `examine`, `pickup`, `combine`, `use_on`, `submit_synthesis`, `climax_choose`. Returns updated state + skill_tag deltas for `dimension_utils`.
  - `EscapeRoomEngine.gating_status(run_state)` — returns which climax options are unlocked.
- `backend/games/the-substitute-teacher.json` — the single pilot game's content.

### Reused engines (no modification)
- `inventory_management_engine.py` — item pickup, slots, weight (weight disabled for v1).
- `quest_engine.py` — "find X" objectives.
- `hint_engine.py` — escalation ladder.
- `dimension_utils.py` — fingerprint aggregation.

### Game-type registration
Add `mystery_room` to the type dispatch in `app.py` alongside `card`, `board`, `simulation`, etc.

### Action verbs (reuse existing endpoint)
`POST /api/run/<id>/choice` with body:
```json
{ "action": "examine", "target": "hotspot:complaint_letter" }
{ "action": "pickup", "target": "item:staff_room_key" }
{ "action": "combine", "target": "item:keychain", "with": "item:classroom_door" }
{ "action": "submit_synthesis", "groupings": {...} }
{ "action": "climax_choose", "choice": "whistleblower" }
```
The backend returns the same shape it does today (state + score deltas + narrative bridge), with new fields:
- `evidence_collected[]`, `evidence_board_state`, `climax_unlocked[]`, `outcome_label` (final only).

### JSON schema additions
```json
{
  "id": "the-substitute-teacher",
  "type": "mystery_room",
  "grade": "8",
  "ai_image_config": { "image_style": "semi-realistic" },
  "rooms": [
    {
      "id": "staff_room",
      "background_image": "/uploads/mr_staff_room_v1.png",
      "hotspots": [
        { "id": "complaint_letter", "bbox": [0.42, 0.31, 0.52, 0.39], "puzzle_id": "p1" },
        ...
      ],
      "exits": [ { "to": "classroom", "bbox": [0.92, 0.40, 1.00, 0.72] } ]
    },
    { "id": "classroom", ... }
  ],
  "items": [
    { "id": "staff_room_key", "icon": "/uploads/mr_key.png", "combinable_with": ["classroom_door"] }
  ],
  "puzzles": [
    {
      "id": "p1",
      "type": "factual",
      "prompt": "Who signed this letter?",
      "options": ["a parent", "the school board", "anonymous"],
      "correct": 0,
      "skill_tags": ["critical_thinking", "evidence_weighing"]
    },
    {
      "id": "p6",
      "type": "ethical_micro",
      "prompt": "Read the folded note?",
      "options": ["Read it", "Leave it folded"],
      "skill_tags_per_option": [
        ["curiosity", "ethical_reasoning_negative"],
        ["ethical_reasoning_positive", "integrity"]
      ]
    }
  ],
  "evidence_board": {
    "buckets": ["principal_says", "actually_happened", "irrelevant"],
    "correct_groupings": { "complaint_letter": "principal_says", ... }
  },
  "climax": {
    "trigger": { "evidence_min": 0 },
    "options": [
      { "id": "whistleblower", "label": "Confront the principal", "gating": { "evidence_min": 7, "synthesis_correct": true } },
      { "id": "quiet_protector", "label": "Tell Mrs. Iyer privately", "gating": { "evidence_min": 4 } },
      { "id": "cautious_investigator", "label": "Talk to any teacher", "gating": null },
      { "id": "compliant_bystander", "label": "Walk away", "gating": null }
    ]
  },
  "hints": { "p1": [...], "p2": [...] },
  "hint_policy": { "auto_prompt_seconds": 120 },
  "epilogues": {
    "whistleblower": { "image": "...", "paragraphs": [...] },
    ...
  }
}
```

### Scoring path
- Factual puzzles: `_score_factual(puzzle_id, answer)` → updates `knowledge_score` and emits the puzzle's `skill_tags`.
- Ethical / interpretive puzzles: emit `skill_tags_per_option` of the chosen option.
- Climax: emits the climax option's `skill_tags`. Outcome label set on the run.
- All `skill_tags` are aggregated into the existing 8-dimension fingerprint via `dimension_utils.aggregate()`.

---

## 10. Frontend Architecture

### New files
- `frontend-react/src/components/game/renderers/MysteryRoomRenderer.jsx` (~1000 LOC).
- `frontend-react/src/components/game/mystery/HotspotLayer.jsx` — absolute-positioned bounding boxes over the background.
- `frontend-react/src/components/game/mystery/InventoryDrawer.jsx` — slide-up drawer (left side on desktop).
- `frontend-react/src/components/game/mystery/EvidenceBoardModal.jsx` — drag-and-drop synthesis UI.
- `frontend-react/src/components/game/mystery/ClimaxModal.jsx` — 4-option fork, with gated options visually disabled and tooltipped.
- `frontend-react/src/components/game/mystery/MysteryRoomEpilogue.jsx` — pre-`PostGameInsights` panel.

### Modified files
- `frontend-react/src/components/game/renderers/GameTypeRouter.jsx` — register `mystery_room` → `MysteryRoomRenderer`.
- `frontend-react/src/components/game/PostGameInsights.jsx` — accept optional `epilogueSlot` prop.

### Renderer responsibilities
- Render the active room's background image (`<img>` with `object-fit: contain`, anchored top-left, percent-based hotspot bboxes for resolution independence).
- Hotspot hover changes cursor and shows a subtle outline; click fires `examine`.
- Inventory drag onto a hotspot fires `use_on`.
- Inventory drag onto another inventory item fires `combine`.
- Top-left HUD: hint button, evidence-board access (locked until ≥3 items).
- Idle timer per puzzle for soft auto-prompt.
- Listens for `Tab`, `Enter`, `I`, `Esc` keys for accessibility navigation.

### Reused unchanged
`GlossaryPanel`, `MentoExplainPopover`, `ReflectionPrompt`, `LiveSkillRadar`, `NarrativeBridge`, `ChoiceExplanation`, `AchievementUnlock`.

### Routing
No new routes — game launches via existing `/play/:gameId` path. `GameTypeRouter` handles the dispatch.

---

## 11. Accessibility

- **Keyboard navigation:** Tab cycles hotspots in a defined order; Enter examines; `I` toggles inventory; `Esc` closes modals; arrow keys move within the inventory; Space activates buttons.
- **Screen reader:** every hotspot has an `aria-label`; the renderer exposes a hidden `<ul>` listing all hotspots in current scene; voicemails and audio have transcripts available on demand.
- **Contrast:** WCAG AA on all overlays; no text directly on the DALL-E backgrounds (always in modals or panels with solid backing).
- **Reduced motion:** respect `prefers-reduced-motion` for hotspot pulse animation and modal transitions.
- **No timer:** no time-based exclusion of any player.
- Reuses `engines/accessibility_engine.py` patterns established in existing renderers.

---

## 12. Assets

| Asset | Count | Source | Notes |
|---|---|---|---|
| Background images | 2 | DALL-E semi-realistic via `story_image_service.py` | Staff room, classroom. Pre-generated, hand-curated, cached. |
| Item icons | 7 | Hand-curated (consistent flat-vector style) | Key, keychain, voicemail icon, drawing, notebook, note, letter. |
| Voicemail audio | 3 | ElevenLabs / built-in TTS | ~10s each, ~30s total. Transcripts included. |
| Child's drawing | 1 | Hand-drawn or carefully prompted DALL-E | Must look child-authored (deliberate imperfection). |
| Epilogue images | 4 | DALL-E semi-realistic | One per ending. |
| **Total** | ~14 images + 3 audio | | All cached on first generation. |

Assets are committed under `frontend-react/public/uploads/mystery/the-substitute-teacher/` and referenced via stable URLs. No DALL-E calls at runtime in v1.

---

## 13. Scope Cuts (v1)

| Decision | v1 | Rationale |
|---|---|---|
| Timer | None. Untimed. | Conflicts with reflection. Add later if data shows session length is bad. |
| Mobile (phone) | Splash: "best on tablet/desktop". Game disabled on screen <768px. | Hotspot precision needs ≥10" screen. Touch v2. |
| Languages | English only | Quality of writing matters too much to translate before validation. Hindi via `i18n` in v2. |
| Save / resume | Single session. Quit = restart. | 15-min sessions; save adds complexity for negligible gain. |
| Auth | Login required. Demo account `demo_student/Mento@2026` works. | Matches all other games. |
| Image generation | Pre-generated, hand-curated. No runtime DALL-E. | Quality + cost predictability for the pilot. |
| Replay | Enabled. Past attempts logged in profile. | Encourages exploring other endings. |
| Multiplayer | Out of scope. | v2+. |
| AI Game Builder integration | Out of scope. | Hand-author the first; learn what good looks like before generation. |
| Procedural variants | Out of scope. | Validate format first. |
| Feature flag | `mystery_room_enabled` per-org and per-user override. **Default OFF.** | Standard pattern. Off until QA passes. |
| Analytics | Reuses `game_starts.json`, `choice_stats.json`. New event types: `examine`, `pickup`, `combine`, `synthesis_submit`, `climax_choose`, `hint_request`, `auto_prompt_dismiss`. | No new analytics infra. |

---

## 14. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Pure narrative puzzles feel like a reading exercise; engagement drops below `story_branching` | Medium | High | Heavy use of non-text clue media (drawing, voicemails, redacted email). Audio clips for mood. Diegetic puzzle 1 ("find the staff-room key") is intentionally tactile to set click-rhythm. |
| Authoring one good mystery is harder than authoring a 7-round story; first pass falls flat | Medium | High | Hand-author by a single writer with editorial review. Playtest with 3–5 Grade 8 students before release. Hint ladder smooths rough edges. |
| Climax distribution collapses to "Walk Away" (path of least resistance) | Medium | Medium | Make the "Walk Away" epilogue honest about its consequences (Aarav crying at lunch). Don't reward it but don't punish either. Track and iterate. |
| Mobile/phone players bounce off the splash screen and never return | Medium | Medium | Splash includes "Save for later" + email reminder. Track conversion. v2 priority. |
| Topic (teacher protecting student) is too sensitive for some schools | Low | Medium | Per-org feature flag; preview build to school admins before enabling for students. Avoid on-screen depiction of the home conflict. |
| Hint ladder over-helps; game becomes solvable without thinking | Low | Medium | Solution-tier hint (3rd click) requires deliberate confirmation modal: "Reveal solution? You'll learn more by trying first." |
| Accessibility: keyboard navigation incomplete on launch | Medium | High | Required for v1. Tested by a non-mouse playthrough before merge. |

---

## 15. Open Questions

None blocking — all design questions resolved during brainstorming. Implementation-level questions (component file boundaries, state shape, exact keyboard navigation order) will be settled in the implementation plan.

---

## 16. Out of Scope

- Multiplayer / co-op mystery rooms.
- AI-generated mystery rooms via the Game Builder.
- Procedurally randomised hotspots / item placement.
- A mystery-room *system* (multiple games, authoring tools, builder integration). This spec deliberately covers *one game and the engine for that one game*.
- Touch / mobile UX optimisation.
- Hindi or other localisations.
- VR / 3D rendering.
- Real-time multiplayer voice chat.
- Procedural narrative generation per playthrough.

---

## 17. Success Metrics — Decision Gate Before Game #2

Before authoring a second mystery-room game, validate:

| Metric | Threshold | Source |
|---|---|---|
| Completion rate (started → climax reached) | ≥ current `story_branching` baseline (compute from `game_starts.json` at launch time as the comparison anchor) | `game_starts.json` |
| Median session length | 12–20 minutes | Run timestamps |
| Hint usage distribution | Mode at 1–2 hints; <15% use 0; <15% use all | `hint_request` events |
| Climax distribution | Each gateable ending ≥15% of qualifying players | `climax_choose` events |
| Replay rate (within 7 days) | ≥20% | Session logs |
| Self-reported "want to play another?" | ≥60% | Post-game prompt |
| Knowledge accuracy mean | 60–80% (not too easy, not too hard) | Score logs |
| Accessibility: full keyboard playthrough | Verified pre-launch | QA |

If thresholds are not met, iterate on the pilot before authoring a second game. If they are met, decide between (a) a second hand-authored mystery game, (b) Game Builder integration, or (c) mobile/touch v2.

---

## 18. Implementation Sequencing (high level — full plan to follow via writing-plans skill)

1. Backend: `escape_room_engine.py` skeleton + game-type registration.
2. Backend: action verbs wired through `/api/run/<id>/choice`.
3. Backend: scoring path (factual + skill_tags + outcome label).
4. Frontend: `MysteryRoomRenderer` skeleton + hotspot layer + inventory.
5. Frontend: evidence-board modal + climax modal + epilogue.
6. Content: author `the-substitute-teacher.json` + assets.
7. Hint policy + soft auto-prompt + accessibility navigation.
8. Analytics events + feature flag.
9. Playtest with 3–5 Grade 8 students, iterate.
10. QA pass (full keyboard, screen reader, two browsers, two screen sizes).
11. Deploy behind feature flag, off by default. Enable for one pilot org first.
12. Measure against §17 thresholds.

Detailed implementation plan to follow via `superpowers:writing-plans`.
