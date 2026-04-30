# Baseline Assessment & Profile Setup Design

**Date:** 2026-03-12
**Status:** Draft
**Scope:** Registration profile collection, persona-aware baseline selection, result storage, and game gating

---

## Problem

1. Registration only collects username/password/role — age, persona, goal, and institution are gathered in a separate post-signup flow (PersonaFlow) that users can bypass entirely.
2. Without profile data at registration, the baseline game selector (`/api/profile/baseline-game`) always falls back to the generic variant instead of the persona- and age-appropriate one.
3. `baseline_complete` is never enforced — users can skip the baseline and play any game immediately.
4. Skipped baseline assessment leaves the profile with no dimension scores, breaking recommendations and leaderboard accuracy.

---

## Goals

- Collect age, persona type, goal, and institution during registration (required, not optional).
- Immediately select the correct baseline game variant using that profile data.
- Gate all games behind baseline completion — one mandatory assessment per user lifetime.
- Show baseline results via post-game screen + SkillProfileReveal before the user enters the app.
- Nudge skippers with a persistent banner until they complete the baseline.

---

## Scope: Student role only

Baseline gating applies to `role === "student"` only. Teachers, HR users, school admins, and trainers are sent to their dashboards directly after registration and are not subject to baseline requirements. The `lock_reason: "baseline_required"` annotation and skip nudge banner only fire for authenticated student users.

---

## Architecture

### Data Flow

```text
Register (Step 1: username/password/role)
  → JWT stored → ProfileSetupStep rendered inline (Step 2)
  → PATCH /api/profile/setup {age, persona, institution}
  → returns {ok, baseline_game_id, baseline_title}
  → /onboarding
      → baseline_complete: false → show baseline game screen
      → user plays baseline game → /play/<baseline_game_id>
      → GamePlayPage: report API returns just_completed_baseline: true
      → navigate to /onboarding (will land on profile_reveal step)
      → SkillProfileReveal (shows baseline_scores snapshot) → mark onboarding_complete → /discover
```

### Skipped Baseline Flow

```text
/onboarding baseline screen → "Skip — I'll do this before my first game"
  → sets baseline_skipped: true ONLY (onboarding_complete stays false)
  → /discover
  → sticky amber banner: "🎯 Complete your baseline to start playing"
  → game cards show 🎯 lock overlay (lock_reason: baseline_required)
  → clicking locked game or banner → /onboarding (baseline step shown again)
```

---

## Backend Changes

### New endpoint: `PATCH /api/profile/setup`

- **Auth:** Required (JWT)
- **Body:** `{age: int, persona: {type: str, goal: str}, institution: str}`
- **Validation:** age 10–100; persona.type in `[student, professional, assessor, trainer]`
- **Action:** Saves `profile.age`, `profile.persona`, `profile.institution`, sets `profile_setup_complete: True`
- **Returns:** `{ok: true, baseline_game_id: str, baseline_title: str}` — runs same selection logic as `/api/profile/baseline-game`
- The existing `PATCH /api/profile/persona` endpoint is aliased to this endpoint (both routes registered) so existing clients do not break. The alias accepts the old body shape `{persona, goal}` as a partial update — missing `age` and `institution` fields are left unchanged on the profile, and `profile_setup_complete` is only set to `True` when all required fields (`age`, `persona`, `institution`) are present in the body.

### Updated: `POST /api/run/<id>/report`

**Baseline detection:** Replace the existing hardcoded `game_id == BASELINE_GAME_ID` check (currently uses constant `"baseline-assessment"`) with `game.get("is_baseline") == True`. All four persona-specific baseline game JSONs already have `"is_baseline": true` in their JSON.

**Atomic baseline completion:** Combine `store_baseline_scores()` and `update_profile(baseline_complete=True)` into a single `update_profile()` call:

```python
update_profile(user_id, {
    "baseline_complete": True,
    "baseline_scores": dimension_scores_snapshot,
    "baseline_completed_at": now_iso(),
    "baseline_skipped": False,
})
```

This eliminates the race condition where `store_baseline_scores` succeeds but the `baseline_complete` flag write fails.

**Response addition:** When baseline is just completed, add `just_completed_baseline: true` as a top-level key:

```python
result["just_completed_baseline"] = True
```

### Updated: `GET /api/games`

For authenticated student users where `profile.get("baseline_complete") == False AND profile.get("profile_setup_complete") == True`:

This covers both skippers (`baseline_skipped: true`) and silent abandoners (completed setup but never played the baseline). The condition requires `profile_setup_complete` so that brand-new accounts that fail mid-registration (before setup completes) do not have all games locked with no explanation.

- Append `"lock_reason": "baseline_required"` to every non-baseline game entry (skip games where `g.get("is_baseline")`)
- This is additive — the existing `locked` field (from unlock_rules) is unaffected. A game can have both `locked: true` (level gate) AND `lock_reason: "baseline_required"`. Frontend checks `lock_reason` first.
- Profile is already loaded inside the games list loop (lines 1563–1578 in app.py) — read `baseline_complete` and `baseline_skipped` from it there
- Skip annotation entirely for demo accounts (`username.startswith("demo_")`)

### Updated: `_ensure_profile()`

New default fields added:

```python
"institution": "",
"profile_setup_complete": False,
"baseline_complete": False,   # explicit default ensures gate condition fires correctly for new accounts
```

Note: `profile_setup_complete: False` and `baseline_complete: False` are co-dependent guards in the game-gate condition — both must default to `False` so that accounts mid-registration (setup incomplete) are not shown a locked game list with no explanation.

---

## Frontend Changes

### `LoginPage.jsx` — 2-step registration (students only)

- Step 1: username + password + role (unchanged for all roles)
- After successful `/api/auth/register` **for student role only**, render `<ProfileSetupStep>` in-place (same page, progress indicator "Step 2 of 2")
- Non-student roles (teacher, HR, admin) continue to redirect to their dashboards as today
- `ProfileSetupStep` fields (all required):

  | Field | UI | Notes |
  | --- | --- | --- |
  | Age | Number input, min 10 | |
  | Persona | 4-button grid | Labels: Student / Professional / HR / Trainer; API values: `student` / `professional` / `assessor` / `trainer` |
  | Goal | 4 radio options | Dynamic per persona, same options as current PersonaFlow |
  | Institution | Text input | Placeholder: "School or company name" |

- On submit: `PATCH /api/profile/setup` → store `baseline_game_id` from response → navigate to `/onboarding`
- **Failure handling:** If `PATCH /api/profile/setup` fails, show inline error "Couldn't save your profile — try again". User stays on step 2. Retrying the PATCH is safe (idempotent).
- Removes existing "save persona to localStorage + redirect" pattern

### `OnboardingPage.jsx` — simplified

- Remove `step === 'persona'` / PersonaFlow rendering entirely
- Fallback for old accounts or failed setup: if profile loads and `profile_setup_complete: false` → render `<ProfileSetupStep>` inline (same component, standalone mode) before proceeding
- **`handleBaselineSkip` fix:** Change to `updateProfile({ baseline_skipped: true })` only — do NOT set `onboarding_complete: true`. This ensures `/onboarding` still shows the baseline step on re-entry.
- Baseline step and SkillProfileReveal step otherwise unchanged

### `GamePlayPage.jsx` — post-baseline redirect

- After report API call, check top-level `response.data.just_completed_baseline === true`
- If true: skip normal post-game flow, navigate to `/onboarding` (will land on `profile_reveal` step since `baseline_complete` is now true but `onboarding_complete` is still false)

### `SkillProfileReveal` — show baseline snapshot

- Pass `profile?.baseline_scores` (not `dimension_scores`) to `SkillProfileReveal` from `OnboardingPage`
- `baseline_scores` is the immutable starting snapshot; `dimension_scores` is cumulative and may differ
- Update prop at `OnboardingPage.jsx` line 146: `scores={profile?.baseline_scores || profile?.dimension_scores || {}}`

### `GameListPage.jsx` / `GameDiscoveryPage.jsx` — baseline gate

- If any game in the list has `lock_reason === "baseline_required"`:
  - Show sticky amber banner at top: "🎯 Complete your baseline assessment to unlock all games" with CTA → `/onboarding`
- Game cards with `lock_reason === "baseline_required"`:
  - Show `🎯` icon overlay
  - Play button replaced with "Complete baseline first"
  - Clicking card or button navigates to `/onboarding`

### `StudentHomePage.jsx` — skip nudge

- If `profile.baseline_skipped && !profile.baseline_complete`:
  - Show persistent amber banner (same style as streak-at-risk): "🎯 Complete your baseline to start playing" → `/onboarding`
  - Banner disappears when `baseline_complete` becomes true

### `PersonaFlow.jsx` — retired

- Remove all imports of `PersonaFlow` (currently in `App.jsx` PersonaTrigger and `OnboardingPage.jsx`)
- File deleted after confirming no remaining imports

---

## Profile Fields Summary

| Field | Type | Set By | Purpose |
| --- | --- | --- | --- |
| `age` | int | PATCH /api/profile/setup | Baseline variant selection |
| `persona.type` | str | PATCH /api/profile/setup | Baseline variant + recommendations |
| `persona.goal` | str | PATCH /api/profile/setup | Recommendation personalisation |
| `institution` | str | PATCH /api/profile/setup | Analytics / cohort grouping |
| `profile_setup_complete` | bool | PATCH /api/profile/setup | Fallback gate for old accounts |
| `baseline_complete` | bool | report endpoint (atomic write) | Unlocks all games |
| `baseline_skipped` | bool | skip action | Activates baseline_required lock |
| `baseline_scores` | dict | report endpoint (atomic write) | Immutable starting skill snapshot |
| `baseline_completed_at` | str | report endpoint (atomic write) | Audit / analytics |
| `onboarding_complete` | bool | SkillProfileReveal confirm only | Stops /onboarding redirect loop |

---

## Baseline Game Selection Logic (unchanged)

| Persona / Age | Game ID |
| --- | --- |
| professional / assessor / trainer OR age ≥ 26 | `baseline-professional-v1` |
| student OR age 18–25 | `baseline-young-adult-v1` |
| student OR age < 18 | `baseline-teen-v1` |
| fallback | `soft-skills-baseline-v1` |

Detection: `game.get("is_baseline") == True` — all four variants have this flag in their JSON.

---

## Demo Accounts

Users with usernames starting `demo_` skip onboarding, baseline, and all gates entirely (already implemented in `OnboardingPage.jsx` and `StudentHomePage.jsx`). The `lock_reason: "baseline_required"` annotation in `/api/games` must also be skipped for demo accounts.

---

## Out of Scope

- Retaking the baseline (separate feature)
- Admin override of `baseline_complete`
- Email verification during registration
- Baseline gating for non-student roles
