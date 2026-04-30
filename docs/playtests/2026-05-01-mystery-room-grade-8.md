# Mystery Room — Substitute Teacher: Grade-8 Playtest Plan

**Date:** 2026-05-01
**Game:** `the-substitute-teacher` (game_type: `mystery_room`, grade: 8, target duration: 13–15 min)
**Feature flag:** `mystery_room_enabled` — must be enabled on the pilot org before sessions.

## Goals

1. Validate that 13–15 minutes is realistic for a Grade-8 student to reach an ending.
2. Identify hotspots that are too small / hard to find.
3. Watch hint-ladder usage: are students learning, or just clicking through?
4. Surface puzzle wording that's too adult or culturally off.
5. Measure ending distribution: do students discover the Whistleblower path organically?

## Recruitment

- 3–5 Grade-8 students (target 4).
- Mix of genders / English fluency levels.
- 30-minute slots: 5 min onboarding → 15 min play → 10 min interview.
- Recruit through pilot org or staff network.

## Setup

- Use `demo_student / Mento@2026` (or new test accounts on the pilot org).
- Tablet or laptop only — mobile is gated by the splash (Task 26).
- Verify the game loads at `https://simulations.mentomap.com/play/the-substitute-teacher` BEFORE the session.

## Observation Protocol

**Do not coach. Do not explain.** If a student is fully stuck for >2 minutes, gently say: "What would you do next?" and let them think.

For each player, record:

| Metric | Notes |
| --- | --- |
| Time-to-first-hotspot-click | Seconds from page load |
| Total session length | Seconds from page load to "play again" prompt |
| Rooms visited | staff_room only / both |
| Puzzles attempted | Count |
| Puzzles solved correctly first try | Count |
| Hint requests per puzzle | Tally with level (1/2/3) |
| Auto-prompts triggered | Count (the soft 120s nudge) |
| Evidence collected | Count (out of 9) |
| Synthesis attempted | Y/N + accuracy |
| Climax choice | compliant_bystander / cautious_investigator / quiet_protector / whistleblower |
| Reached ending? | Y/N |
| Boredom signals | Sigh, scroll, walk away, ask "is that it?" |
| "Want to play another?" | Y/N + verbal reaction |

## Post-Game Interview (5 questions, ~5 min)

1. "In one sentence, what was this game about?"
2. "Who do you think was right — Ms. Banerjee or the principal? Why?"
3. "Was anything confusing or boring? What part?"
4. "Did the hints help? Were they too obvious or not obvious enough?"
5. "If you played again, would you make a different choice? Which one?"

## Decision-Gate Metrics (post-pilot, after ≥20 plays)

These determine whether mystery_room becomes a permanent game type or stays a one-off pilot:

- **Completion rate ≥ 60%** (vs. story_branching baseline ~70%)
- **Median session 11–17 min** (target band: 13–15 ± 2)
- **Hint usage rate 30–60%** (low = puzzles too easy; high = friction)
- **Climax distribution: no ending exceeds 60%** (suggests genuine fork rather than railroad)
- **Replay rate ≥ 25%** (proxy: same user starts a 2nd run within 7 days)
- **NPS-style "want another" ≥ 60% yes**

## Iteration After Sessions

After all 4–5 sessions, the moderator should write a short patch list:

- **Top 2 friction points** identified across sessions.
- **Concrete fix** for each (e.g., "enlarge hotspot bbox for `desk_phone` from `[0.31, 0.55, 0.42, 0.66]` to `[0.28, 0.50, 0.46, 0.70]`").
- **Re-test with one fresh student** to verify the patches reduced friction without introducing new confusion.

## Common Predicted Friction Points

Based on plan review and content authoring:
- **Voicemail puzzle (p2_voicemails):** transcript text may be redundant if audio is good; if audio fails to load, transcripts must be the primary content. Verify audio plays.
- **Email-thread ordering puzzle (p3_email_thread):** ↑/↓ buttons may not be obvious — drag-and-drop would be more natural. v1 keeps simple buttons.
- **Folded-note interpretive puzzle (p6_folded_note):** some students may pick the "tear it up" option as a joke, not realising it's the ethically charged choice. Watch interview reactions.
- **Climax gating (Whistleblower locked):** the 🔒 with "Collect more evidence" message must be clearly visible; otherwise players get stuck thinking the game is broken.
- **No HUD trigger to OPEN climax:** the climax fires when player attempts to leave a fully-explored room. If they don't try to leave, they sit indefinitely. Watch for this; may need a "Make a decision" CTA.

## Output

Save observation notes here as the sessions complete. Update this file with:
- Session-by-session table
- Aggregate metrics
- Patch list
- Re-test result

Then commit:
```
git add docs/playtests/2026-05-01-mystery-room-grade-8.md
git commit -m "playtest(mystery): five Grade-8 sessions + patches"
```
