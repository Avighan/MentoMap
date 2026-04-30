# Learning Journey Redesign Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform MentoApp from a 135-game library into a structured learning journey with role-specific home screens, smart game curation (~15 visible at a time), daily challenges, meaningful level gates, and post-game hooks that drive next-session behaviour.

**Architecture:** Four role-specific home screen experiences (student / teacher / parent / hr) sit on top of a new backend layer: a daily challenge system, dimension-based next-game recommender, and game quality scorer. The 135 games remain in the catalogue but only ~15 surface at any time based on persona + dimension profile + level. Onboarding funnels first-time students through persona → baseline → skill profile → 3 curated recommendations before showing any other games.

**Tech Stack:** React + Tailwind + Framer Motion (frontend), Flask + JSON storage (backend), existing GameContext + player_profile.py + spaced_repetition.py infrastructure.

---

## Overview of Subsystems

This plan is split into 8 independent chunks. Each chunk is deployable on its own. Suggested execution order respects dependencies (backend before frontend consumers).

| Chunk | Subsystem | Backend / Frontend | Dependencies |
|---|---|---|---|
| 1 | Daily Challenge + Recommendations API | Backend | None |
| 2 | Level Gates + Progression System | Backend | None |
| 3 | Game Quality Scoring + Curation | Backend | None |
| 4 | Student Home Screen Redesign | Frontend | Chunks 1, 2, 3 |
| 5 | Role-Based Home Screens (Teacher / Parent / HR) | Frontend | None |
| 6 | First-Time Onboarding Flow | Frontend | Chunk 2, 3 |
| 7 | Game Discovery Redesign | Frontend | Chunks 1, 2, 3 |
| 8 | Post-Game Retention Improvements | Frontend + Backend | Chunk 1 |

---

## File Map

### New backend files / endpoints
| File | What it does |
|---|---|
| `backend/daily_challenge.py` | Deterministic daily game selection, teacher override, change-at-midnight |
| `backend/app.py` | +4 new endpoints (see Chunk 1, 2, 3 details) |
| `backend/data/game_quality.json` | Auto-generated quality scores per game (rounds ≥ 7, has dim scoring, not duplicate) |

### New frontend files
| File | What it does |
|---|---|
| `frontend-react/src/pages/StudentHomePage.jsx` | New student home: Continue / Today's Challenge / Weak Spot / Streak / Explore link |
| `frontend-react/src/pages/TeacherHomePage.jsx` | Teacher home: My Classes / Assign Challenge / Gradebook CTA |
| `frontend-react/src/pages/ParentHomePage.jsx` | Parent home: Child week summary / Skill trajectory / Weak spot |
| `frontend-react/src/pages/HRHomePage.jsx` | HR home: Candidate assessments table / Batch results |
| `frontend-react/src/components/home/DailyChallenge.jsx` | "Today's Challenge" card — single featured game, changes daily |
| `frontend-react/src/components/home/WeakSpotCard.jsx` | One targeted game based on lowest dimension |
| `frontend-react/src/components/home/ContinueCard.jsx` | Resume last game or next course item |
| `frontend-react/src/components/home/SkillSnapshotCard.jsx` | Mini radar / bar chart of current dim scores |
| `frontend-react/src/pages/OnboardingPage.jsx` | First-time flow: Persona → Baseline redirect → Profile reveal → 3 recommendations |
| `frontend-react/src/components/onboarding/SkillProfileReveal.jsx` | Post-baseline "here's what we found" display |
| `frontend-react/src/pages/GameDiscoveryPage.jsx` | Curated discovery: By Goal / By Time / By Level, max 12 shown |
| `frontend-react/src/api/journey.js` | API module: daily challenge, recommendations, quality, level info |

### Modified files
| File | What changes |
|---|---|
| `frontend-react/src/App.jsx` | Route home `/` by role to new role-specific pages; add `/onboarding` route |
| `frontend-react/src/pages/HomePage.jsx` | Becomes thin router: if first-time → `/onboarding`, else role-route |
| `frontend-react/src/pages/GameListPage.jsx` | Add "By Goal / By Time / By Level" filter modes; respect quality filter |
| `frontend-react/src/components/game/PostGameInsights.jsx` | Add "What to play next" card + "Challenge a friend" CTA |
| `backend/player_profile.py` | `is_first_time_user()` helper; `get_next_recommended_game()` |
| `backend/data/unlock_rules.json` | Level-gated game types: L1-3 foundational only, L4-6 simulations, L7+ AI Arena |

---

## Chunk 1 — Backend: Daily Challenge + Recommendations API

### What this builds
- `GET /api/daily-challenge` — returns one game, changes daily at midnight, same game for all users in same org, teacher-overridable
- `GET /api/recommendations/next` — returns 1-3 game recommendations based on weakest dimensions + persona + level
- `GET /api/recommendations/for-goal?goal=<leadership|negotiation|decisions>` — returns 8 curated games for a learning goal

### Task 1.1 — Create `backend/daily_challenge.py`

**Files:**
- Create: `backend/daily_challenge.py`

- [ ] **Step 1: Write the module**

```python
"""
Daily challenge selection.
One game per day, consistent for all users.
Teacher can override for their org on the day.
"""
import hashlib
import json
import os
from datetime import datetime

OVERRIDE_FILE = os.path.join(os.path.dirname(__file__), "data", "daily_challenge_overrides.json")

# Game types eligible for daily challenge (high engagement value)
ELIGIBLE_GAME_TYPES = {
    "rounds", "story_branching", "board", "ai_arena",
    "negotiation", "debate", "card_board", "trump_card",
}

def get_daily_challenge(games: dict, org_id: str = None, date_str: str = None) -> dict | None:
    """
    Return one game for today's daily challenge.

    Selection is deterministic per (date, org): same game shown to everyone in the
    same org on the same day. Changes at midnight UTC.

    Teacher override: if data/daily_challenge_overrides.json has an entry for
    {org_id or 'default'}::{date}, use that game_id instead.
    """
    today = date_str or datetime.utcnow().strftime("%Y-%m-%d")

    # Check teacher override first
    override_game_id = _get_override(org_id, today)
    if override_game_id and override_game_id in games:
        g = games[override_game_id].copy()
        g["is_override"] = True
        return g

    # Filter to eligible, quality games
    eligible = [
        g for g in games.values()
        if g.get("game_type") in ELIGIBLE_GAME_TYPES
        and g.get("dimension_scoring_weights")
        and len(g.get("rounds") or g.get("scenarios") or []) >= 5
    ]
    if not eligible:
        return None

    # Deterministic selection: hash(org_id + date) mod eligible count
    seed_str = f"{org_id or 'default'}::{today}"
    idx = int(hashlib.md5(seed_str.encode()).hexdigest(), 16) % len(eligible)
    chosen = eligible[idx].copy()
    chosen["is_daily_challenge"] = True
    chosen["challenge_date"] = today
    return chosen


def set_override(org_id: str, game_id: str, date_str: str = None):
    """Set a teacher override for today's (or a specific) daily challenge."""
    today = date_str or datetime.utcnow().strftime("%Y-%m-%d")
    data = _load_overrides()
    key = f"{org_id or 'default'}::{today}"
    data[key] = game_id
    _save_overrides(data)


def _get_override(org_id: str, today: str) -> str | None:
    data = _load_overrides()
    return data.get(f"{org_id or 'default'}::{today}") or data.get(f"default::{today}")


def _load_overrides() -> dict:
    try:
        with open(OVERRIDE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_overrides(data: dict):
    os.makedirs(os.path.dirname(OVERRIDE_FILE), exist_ok=True)
    with open(OVERRIDE_FILE, "w") as f:
        json.dump(data, f, indent=2)
```

- [ ] **Step 2: Add endpoints to `backend/app.py`**

Find the `/api/config` endpoint section and add after it:

```python
# ── Daily Challenge ──────────────────────────────────────────────────────────

@app.get("/api/daily-challenge")
def api_daily_challenge():
    """Return today's daily challenge game (same for all users in an org)."""
    load_bundle()
    import daily_challenge as _dc
    org_id = None
    try:
        token = get_token_from_request()
        payload = verify_token(token) if token else None
        org_id = payload.get("org_id") if payload else None
    except Exception:
        pass
    game = _dc.get_daily_challenge(GAMES, org_id=org_id)
    if not game:
        return jsonify({"challenge": None})
    return jsonify({"challenge": game})


@app.post("/api/teacher/daily-challenge/override")
@jwt_required
@role_required("teacher", "school_admin", "admin")
def api_set_daily_challenge_override():
    """Teacher sets today's daily challenge for their org."""
    body = request.get_json() or {}
    game_id = body.get("game_id")
    if not game_id:
        return jsonify({"error": "game_id required"}), 400
    load_bundle()
    if game_id not in GAMES:
        return jsonify({"error": "Game not found"}), 404
    import daily_challenge as _dc
    org_id = g.jwt_payload.get("org_id")
    _dc.set_override(org_id, game_id)
    return jsonify({"ok": True, "game_id": game_id})
```

- [ ] **Step 3: Add `GET /api/recommendations/next` endpoint**

```python
@app.get("/api/recommendations/next")
@jwt_required
def api_next_recommendation():
    """
    Return 1-3 game recommendations for the current user.
    Prioritises: (1) weakest dimension, (2) persona track, (3) current level.
    Excludes games the user has played in the last 7 days.
    """
    user_id = g.jwt_payload["user_id"]
    load_bundle()
    profile = player_profile.get_profile(user_id) or {}

    dim_scores = profile.get("dimension_scores", {})
    persona = profile.get("persona", {}).get("type", "student")
    level = profile.get("level", 1)
    recent_games = set(
        e.get("game_id") for e in profile.get("game_history", [])[-20:]
        if e.get("game_id")
    )

    # Determine weakest dimension (scored < 65 or unplayed)
    ALL_DIMS = ["strategic_thinking", "risk_tolerance", "delayed_gratification",
                "adaptability", "resilience", "empathy", "ethical_reasoning", "creativity"]
    weakest = min(ALL_DIMS, key=lambda d: dim_scores.get(d, 0))

    # Find games that target the weakest dimension and respect level gate
    unlocked_types = _get_unlocked_game_types_for_level(level)
    candidates = []
    for gid, game in GAMES.items():
        if gid in recent_games:
            continue
        if game.get("game_type") not in unlocked_types:
            continue
        dim_weights = game.get("dimension_scoring_weights", {})
        if dim_weights.get(weakest, 0) >= 0.25:
            candidates.append((gid, game, dim_weights.get(weakest, 0)))

    candidates.sort(key=lambda x: -x[2])
    recs = []
    for gid, game, _ in candidates[:3]:
        recs.append({
            "game_id": gid,
            "title": game.get("title", gid),
            "description": game.get("description", ""),
            "game_type": game.get("game_type"),
            "estimated_duration_minutes": game.get("estimated_duration_minutes", 15),
            "reason": f"Targets your weakest skill: {weakest.replace('_', ' ')}",
            "target_dimension": weakest,
        })

    return jsonify({"recommendations": recs, "weakest_dimension": weakest})


def _get_unlocked_game_types_for_level(level: int) -> set:
    """Level gate: what game types are accessible at this level."""
    base = {"rounds", "story_branching", "minigame", "quiz", "wellbeing_survey"}
    if level >= 4:
        base |= {"board", "card", "card_board", "trump_card", "strategy_grid", "puzzle_match"}
    if level >= 6:
        base |= {"strategy", "chess_strategy", "go_territory", "reversi", "tower_defense"}
    if level >= 7:
        base |= {"ai_arena", "negotiation", "debate"}
    return base
```

- [ ] **Step 4: Add `GET /api/recommendations/for-goal` endpoint**

```python
# Goal → dimension mapping
_GOAL_DIMENSIONS = {
    "leadership":    ["strategic_thinking", "adaptability", "resilience"],
    "negotiation":   ["empathy", "strategic_thinking", "risk_tolerance"],
    "decisions":     ["delayed_gratification", "risk_tolerance", "ethical_reasoning"],
    "empathy":       ["empathy", "ethical_reasoning"],
    "resilience":    ["resilience", "adaptability"],
    "creativity":    ["creativity", "adaptability"],
}

@app.get("/api/recommendations/for-goal")
def api_games_for_goal():
    """Return up to 12 games for a learning goal (by goal slug)."""
    goal = request.args.get("goal", "leadership")
    dims = _GOAL_DIMENSIONS.get(goal, ["strategic_thinking"])
    load_bundle()

    scored = []
    for gid, game in GAMES.items():
        weights = game.get("dimension_scoring_weights", {})
        relevance = sum(weights.get(d, 0) for d in dims)
        if relevance > 0:
            scored.append((gid, game, relevance))

    scored.sort(key=lambda x: -x[2])
    results = []
    for gid, game, rel in scored[:12]:
        results.append({
            "game_id": gid,
            "title": game.get("title", gid),
            "description": game.get("description", ""),
            "game_type": game.get("game_type"),
            "estimated_duration_minutes": game.get("estimated_duration_minutes", 15),
            "relevance_score": round(rel, 2),
            "cognitive_framework": game.get("cognitive_framework", {}),
        })

    return jsonify({"games": results, "goal": goal, "dimensions": dims})
```

- [ ] **Step 5: Create `frontend-react/src/api/journey.js`**

```javascript
import { apiFetch } from './crud';

export const getDailyChallenge = () =>
  apiFetch('/api/daily-challenge').then(r => r.challenge);

export const getNextRecommendations = () =>
  apiFetch('/api/recommendations/next').then(r => r.recommendations || []);

export const getGamesForGoal = (goal) =>
  apiFetch(`/api/recommendations/for-goal?goal=${goal}`).then(r => r.games || []);

export const setDailyChallengeOverride = (game_id) =>
  apiFetch('/api/teacher/daily-challenge/override', {
    method: 'POST',
    body: JSON.stringify({ game_id }),
  });
```

- [ ] **Step 6: Verify**

```bash
# Start backend, then:
curl http://localhost:5001/api/daily-challenge
# → {"challenge": {"game_id": "...", "title": "...", "is_daily_challenge": true}}

curl -H "Authorization: Bearer <student_token>" http://localhost:5001/api/recommendations/next
# → {"recommendations": [...], "weakest_dimension": "empathy"}

curl http://localhost:5001/api/recommendations/for-goal?goal=negotiation
# → {"games": [...12 items...], "goal": "negotiation"}
```

- [ ] **Step 7: Commit**

```bash
git add backend/daily_challenge.py backend/app.py frontend-react/src/api/journey.js
git commit -m "feat: add daily challenge + smart recommendations API"
```

---

## Chunk 2 — Backend: Level Gates + Progression System

### What this builds
- `unlock_rules.json` updated so levels map to game type access (L1-3 foundational, L4-6 simulation, L7+ AI Arena)
- `GET /api/profile/level-info` returns current level, next unlock, games_to_unlock
- Teacher override: teacher can grant early access to a student or cohort

### Task 2.1 — Update `backend/data/unlock_rules.json`

- [ ] **Step 1: Restructure unlock rules**

The current unlock_rules.json has individual game unlocks. Add a `level_gates` section that gates by game_type, not just game_id. This is additive — existing per-game rules still work.

```json
{
  "level_gates": {
    "1": {
      "unlocked_types": ["rounds", "story_branching", "minigame", "quiz", "wellbeing_survey"],
      "label": "Foundation",
      "description": "Scenario decisions, story choices, knowledge quizzes"
    },
    "4": {
      "unlocked_types": ["board", "card", "card_board", "trump_card", "strategy_grid", "puzzle_match"],
      "label": "Simulation",
      "description": "Board games, card mechanics, strategy grids"
    },
    "6": {
      "unlocked_types": ["strategy", "chess_strategy", "go_territory", "reversi", "tower_defense"],
      "label": "Strategy",
      "description": "Abstract strategy and long-horizon planning"
    },
    "7": {
      "unlocked_types": ["ai_arena", "negotiation", "debate"],
      "label": "AI Arena",
      "description": "Live AI opponents — negotiation, debate, and competitive scenarios"
    }
  }
}
```

### Task 2.2 — Add `GET /api/profile/level-info` endpoint

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Add endpoint**

```python
@app.get("/api/profile/level-info")
@jwt_required
def api_level_info():
    """Return current level, what's unlocked, and what unlocks next."""
    user_id = g.jwt_payload["user_id"]
    profile = player_profile.get_profile(user_id) or {}
    level = profile.get("level", 1)
    xp = profile.get("xp", 0)

    # Load level gates from unlock_rules
    try:
        with open("data/unlock_rules.json") as f:
            rules = json.load(f)
        gates = rules.get("level_gates", {})
    except Exception:
        gates = {}

    # Current unlocked types
    unlocked_types = set()
    for gate_level_str, gate_data in gates.items():
        if level >= int(gate_level_str):
            unlocked_types.update(gate_data.get("unlocked_types", []))

    # Next gate
    next_gate = None
    for gate_level_str, gate_data in sorted(gates.items(), key=lambda x: int(x[0])):
        if int(gate_level_str) > level:
            next_gate = {"level": int(gate_level_str), **gate_data}
            break

    # XP to next level
    import math
    next_level = level + 1
    xp_for_next = (next_level ** 2) * 50  # matches level formula sqrt(xp/50)
    xp_needed = max(0, xp_for_next - xp)

    return jsonify({
        "level": level,
        "xp": xp,
        "xp_to_next_level": xp_needed,
        "unlocked_types": list(unlocked_types),
        "next_unlock": next_gate,
    })
```

### Task 2.3 — Teacher cohort-level override

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: Add teacher early-unlock endpoint**

```python
@app.post("/api/teacher/grant-access")
@jwt_required
@role_required("teacher", "school_admin", "admin")
def api_teacher_grant_access():
    """
    Grant a student (or all students in a cohort) early access to a game type.
    Body: {student_id?: str, cohort_id?: str, game_type: str}
    """
    body = request.get_json() or {}
    game_type = body.get("game_type")
    if not game_type:
        return jsonify({"error": "game_type required"}), 400

    target_user_ids = []
    if body.get("student_id"):
        target_user_ids = [body["student_id"]]
    elif body.get("cohort_id"):
        cohort = _get_cohort(body["cohort_id"])
        target_user_ids = cohort.get("student_ids", []) if cohort else []

    if not target_user_ids:
        return jsonify({"error": "student_id or cohort_id required"}), 400

    updated = 0
    for uid in target_user_ids:
        p = player_profile.get_profile(uid)
        if p is not None:
            early_access = p.get("teacher_early_access", [])
            if game_type not in early_access:
                early_access.append(game_type)
            player_profile.update_profile(uid, {"teacher_early_access": early_access})
            updated += 1

    return jsonify({"ok": True, "updated": updated, "game_type": game_type})
```

- [ ] **Step 2: Wire teacher_early_access into `check_unlocks()` in `player_profile.py`**

In `check_unlocks()`, add early access types from profile to unlocked_types:

```python
# Teacher early access overrides
early_access = profile.get("teacher_early_access", [])
for gt in early_access:
    unlocked_types.add(gt)
```

- [ ] **Step 3: Commit**

```bash
git add backend/data/unlock_rules.json backend/app.py backend/player_profile.py
git commit -m "feat: level-gated game types (L1 foundational, L4 simulation, L7 AI Arena)"
```

---

## Chunk 3 — Backend: Game Quality Scoring + Curation

### What this builds
- Auto-generated `game_quality.json` — each game gets a quality score (0-100) and a `curated: true/false` flag
- `GET /api/games` enriched with `quality_score` and `curated` fields
- Games with `curated: false` are hidden from the default library view (still accessible by direct URL)
- Criteria: has dimension_scoring_weights (25pts), rounds ≥ 7 or type is minigame/board (25pts), unique content (25pts), has coaching_moment (25pts)

### Task 3.1 — Create quality scoring script

**Files:**
- Create: `backend/scripts/score_game_quality.py`

- [ ] **Step 1: Write the script**

```python
"""
Score all games for quality and write to data/game_quality.json.
Run: python scripts/score_game_quality.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

GAMES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "games")
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "game_quality.json")

# Game types that count as having "rounds" even if stored differently
RICH_TYPES = {"board", "ai_arena", "negotiation", "debate", "story_branching",
              "card_board", "trump_card", "chess_strategy", "go_territory",
              "reversi", "tower_defense", "puzzle_match", "strategy_grid"}


def score_game(game: dict) -> dict:
    score = 0
    reasons = []

    # 1. Has dimension scoring weights (25 pts)
    if game.get("dimension_scoring_weights"):
        score += 25
        reasons.append("has dimension scoring")

    # 2. Sufficient rounds / rich game type (25 pts)
    round_count = len(game.get("rounds") or game.get("scenarios") or
                      game.get("chapters") or [])
    gt = game.get("game_type", "")
    if round_count >= 7 or gt in RICH_TYPES:
        score += 25
        reasons.append(f"rich content ({round_count} rounds or type '{gt}')")

    # 3. Has coaching moments (25 pts)
    has_coaching = (
        game.get("coaching_moment") or
        any(r.get("coaching_moment") for r in (game.get("rounds") or []))
    )
    if has_coaching:
        score += 25
        reasons.append("has coaching moments")

    # 4. Unique content — not a duplicate title pattern (25 pts)
    title = (game.get("title") or "").lower()
    duplicate_signals = ["test", "demo", "copy of", "untitled", "placeholder"]
    if not any(s in title for s in duplicate_signals):
        score += 25
        reasons.append("unique title")

    curated = score >= 75  # Needs 3/4 criteria to be curated
    return {"score": score, "curated": curated, "reasons": reasons}


def main():
    results = {}
    for fname in os.listdir(GAMES_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(GAMES_DIR, fname)
        try:
            with open(path) as f:
                game = json.load(f)
            game_id = game.get("game_id", fname.replace(".json", ""))
            results[game_id] = score_game(game)
        except Exception as e:
            print(f"SKIP {fname}: {e}")

    curated_count = sum(1 for v in results.values() if v["curated"])
    print(f"Scored {len(results)} games. Curated: {curated_count}.")

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Written to {OUTPUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the script and check output**

```bash
cd backend && python scripts/score_game_quality.py
# Expected: "Scored 135 games. Curated: ~70-90."
cat data/game_quality.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for v in d.values() if v['curated']), 'curated')"
```

- [ ] **Step 3: Load quality scores into `/api/games` response**

In `backend/app.py`, in the `games_list()` function, load `game_quality.json` once at startup and include `quality_score` + `curated` fields:

```python
# Near top of app.py (after GAMES global):
_GAME_QUALITY: dict = {}

def _load_game_quality():
    global _GAME_QUALITY
    try:
        with open(os.path.join(os.path.dirname(__file__), "data", "game_quality.json")) as f:
            _GAME_QUALITY = json.load(f)
    except Exception:
        _GAME_QUALITY = {}

# Call at startup (alongside load_bundle()):
_load_game_quality()
```

In the `/api/games` response dict per game, add:
```python
"quality_score": _GAME_QUALITY.get(g["game_id"], {}).get("score", 50),
"curated": _GAME_QUALITY.get(g["game_id"], {}).get("curated", True),
```

- [ ] **Step 4: Commit**

```bash
git add backend/scripts/score_game_quality.py backend/data/game_quality.json backend/app.py
git commit -m "feat: game quality scoring — curated flag for game curation"
```

---

## Chunk 4 — Frontend: Student Home Screen Redesign

### What this builds
A new `StudentHomePage.jsx` with 5 sections:
1. **Continue** — resume in-progress game or next course item
2. **Today's Challenge** — one daily game, teacher-overridable, with a countdown to midnight refresh
3. **Your Weak Spot** — one targeted recommendation with explanation
4. **Streak + XP** — compact, not dominant
5. **Explore more** — link to `GameDiscoveryPage`

Replaces the current `/` home for students.

### Task 4.1 — `DailyChallenge.jsx` component

**Files:**
- Create: `frontend-react/src/components/home/DailyChallenge.jsx`

- [ ] **Step 1: Write the component**

```jsx
import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const GAME_TYPE_ICONS = {
  rounds: '🎭', board: '🎲', ai_arena: '🤖', story_branching: '📖',
  negotiation: '🤝', debate: '🎤', card_board: '🃏', default: '⚡',
};

export default function DailyChallenge({ game, loading }) {
  const nav = useNavigate();
  if (loading) return <div className="h-36 bg-gray-800 rounded-2xl animate-pulse" />;
  if (!game) return null;

  const icon = GAME_TYPE_ICONS[game.game_type] || GAME_TYPE_ICONS.default;
  const dims = Object.keys(game.dimension_scoring_weights || {}).slice(0, 2)
    .map(d => d.replace(/_/g, ' '));

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 p-5 cursor-pointer shadow-lg"
      onClick={() => nav(`/play/${game.game_id}`)}
    >
      <div className="absolute top-3 right-3 bg-white/20 text-white text-xs font-bold px-2 py-0.5 rounded-full">
        TODAY'S CHALLENGE
      </div>
      <div className="text-3xl mb-2">{icon}</div>
      <h3 className="text-white font-bold text-lg leading-tight">{game.title}</h3>
      <p className="text-amber-100 text-sm mt-1 line-clamp-2">{game.description}</p>
      {dims.length > 0 && (
        <div className="flex gap-2 mt-3">
          {dims.map(d => (
            <span key={d} className="bg-white/20 text-white text-xs px-2 py-0.5 rounded-full capitalize">{d}</span>
          ))}
        </div>
      )}
      <div className="mt-4 inline-flex items-center gap-1.5 bg-white text-orange-600 font-semibold text-sm px-4 py-2 rounded-xl">
        Play Now →
      </div>
    </motion.div>
  );
}
```

### Task 4.2 — `WeakSpotCard.jsx` component

**Files:**
- Create: `frontend-react/src/components/home/WeakSpotCard.jsx`

- [ ] **Step 1: Write the component**

```jsx
import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

const DIM_TIPS = {
  strategic_thinking: "You tend to react rather than plan ahead. This game will challenge that.",
  risk_tolerance: "You play it safe. This will push you into calculated risk territory.",
  delayed_gratification: "You go for quick wins. Try resisting the immediate reward here.",
  adaptability: "Change throws you off. This scenario forces rapid pivots.",
  resilience: "You fold under pressure. This game is designed to stress-test that.",
  empathy: "You underweigh others' perspectives. This forces you into someone else's shoes.",
  ethical_reasoning: "Ethical grey zones trip you up. Every choice here has a cost.",
  creativity: "You default to the conventional path. There's a better way — find it.",
};

export default function WeakSpotCard({ recommendation, loading }) {
  const nav = useNavigate();
  if (loading) return <div className="h-28 bg-gray-800 rounded-2xl animate-pulse" />;
  if (!recommendation) return null;

  const dim = recommendation.target_dimension || '';
  const tip = DIM_TIPS[dim] || recommendation.reason || '';

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl bg-gray-800 border border-gray-700 p-4 cursor-pointer hover:border-indigo-500 transition-colors"
      onClick={() => nav(`/play/${recommendation.game_id}`)}
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl mt-0.5">🎯</div>
        <div className="flex-1">
          <p className="text-gray-400 text-xs uppercase tracking-wide font-semibold mb-0.5">Your weak spot</p>
          <h4 className="text-white font-semibold">{recommendation.title}</h4>
          <p className="text-gray-400 text-sm mt-1">{tip}</p>
        </div>
        <div className="text-gray-500 text-lg mt-1">›</div>
      </div>
    </motion.div>
  );
}
```

### Task 4.3 — `ContinueCard.jsx` component

**Files:**
- Create: `frontend-react/src/components/home/ContinueCard.jsx`

- [ ] **Step 1: Write the component**

```jsx
import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';

export default function ContinueCard({ lastGame, activeCourse, loading }) {
  const nav = useNavigate();
  if (loading) return <div className="h-20 bg-gray-800 rounded-2xl animate-pulse" />;

  // Course takes priority over last game
  const target = activeCourse
    ? { label: 'Continue Course', title: activeCourse.title, sub: `${activeCourse.progress_pct}% complete`, path: `/courses/${activeCourse.course_id}`, icon: '📚' }
    : lastGame
    ? { label: 'Continue', title: lastGame.title, sub: `Round ${lastGame.last_round || 1}`, path: `/play/${lastGame.game_id}`, icon: '▶️' }
    : null;

  if (!target) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl bg-indigo-900/40 border border-indigo-500/30 p-4 flex items-center gap-4 cursor-pointer hover:border-indigo-400 transition-colors"
      onClick={() => nav(target.path)}
    >
      <span className="text-2xl">{target.icon}</span>
      <div className="flex-1 min-w-0">
        <p className="text-indigo-300 text-xs font-semibold uppercase tracking-wide">{target.label}</p>
        <p className="text-white font-semibold truncate">{target.title}</p>
        <p className="text-gray-400 text-xs">{target.sub}</p>
      </div>
      <div className="text-indigo-400 text-xl">›</div>
    </motion.div>
  );
}
```

### Task 4.4 — `StudentHomePage.jsx`

**Files:**
- Create: `frontend-react/src/pages/StudentHomePage.jsx`

- [ ] **Step 1: Write the page**

```jsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getDailyChallenge, getNextRecommendations } from '../api/journey';
import { getProfile } from '../api/profile';
import DailyChallenge from '../components/home/DailyChallenge';
import WeakSpotCard from '../components/home/WeakSpotCard';
import ContinueCard from '../components/home/ContinueCard';
import MobileBottomNav from '../components/ui/MobileBottomNav';

export default function StudentHomePage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [challenge, setChallenge] = useState(null);
  const [recs, setRecs] = useState([]);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getDailyChallenge().catch(() => null),
      getNextRecommendations().catch(() => []),
      getProfile().catch(() => null),
    ]).then(([ch, r, p]) => {
      setChallenge(ch);
      setRecs(r);
      setProfile(p);
      setLoading(false);
    });
  }, []);

  const lastGame = profile?.game_history?.slice(-1)[0] || null;
  const activeCourse = profile?.active_course || null;
  const streak = profile?.streak_days || 0;
  const level = profile?.level || 1;
  const firstName = user?.username?.split('_')[0] || 'there';

  return (
    <div className="min-h-screen bg-gray-950 pb-24">
      {/* Header */}
      <div className="px-5 pt-8 pb-2">
        <p className="text-gray-400 text-sm">Hey {firstName} 👋</p>
        <div className="flex items-center justify-between mt-1">
          <h1 className="text-white text-2xl font-bold">Your Journey</h1>
          <div className="flex items-center gap-3">
            {streak > 0 && (
              <div className="flex items-center gap-1 bg-orange-900/40 border border-orange-500/30 px-3 py-1.5 rounded-full">
                <span>🔥</span>
                <span className="text-orange-300 font-bold text-sm">{streak}</span>
              </div>
            )}
            <div className="flex items-center gap-1 bg-indigo-900/40 border border-indigo-500/30 px-3 py-1.5 rounded-full">
              <span className="text-indigo-300 font-bold text-sm">Lv {level}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="px-5 space-y-4 mt-4">
        {/* Continue */}
        <ContinueCard lastGame={lastGame} activeCourse={activeCourse} loading={loading} />

        {/* Today's Challenge */}
        <DailyChallenge game={challenge} loading={loading} />

        {/* Weak spot */}
        {recs[0] && <WeakSpotCard recommendation={recs[0]} loading={loading} />}

        {/* Additional recommendations */}
        {recs.slice(1, 3).length > 0 && (
          <div className="space-y-2">
            <p className="text-gray-400 text-xs uppercase tracking-wide font-semibold px-1">Also recommended</p>
            {recs.slice(1, 3).map(rec => (
              <div
                key={rec.game_id}
                className="flex items-center gap-3 bg-gray-800/60 rounded-xl p-3 cursor-pointer hover:bg-gray-800 transition-colors"
                onClick={() => nav(`/play/${rec.game_id}`)}
              >
                <span className="text-lg">🎮</span>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium truncate">{rec.title}</p>
                  <p className="text-gray-500 text-xs">{rec.estimated_duration_minutes || 15} min · {rec.reason}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Explore more */}
        <button
          onClick={() => nav('/discover')}
          className="w-full py-3 rounded-xl border border-gray-700 text-gray-400 text-sm font-medium hover:border-gray-500 hover:text-gray-200 transition-colors"
        >
          Explore all games →
        </button>
      </div>

      <MobileBottomNav />
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/pages/StudentHomePage.jsx \
        frontend-react/src/components/home/
git commit -m "feat: student home screen — continue/daily challenge/weak spot"
```

---

## Chunk 5 — Frontend: Role-Based Home Screens

### What this builds
Three additional home screen variants: `TeacherHomePage`, `ParentHomePage`, `HRHomePage`. The routing in `App.jsx` sends users to the right one based on `user.role`. Current `HomePage.jsx` becomes the student home.

### Task 5.1 — Teacher Home Screen

**Files:**
- Create: `frontend-react/src/pages/TeacherHomePage.jsx`

Key sections (wire to existing APIs):
- **My Classes** — `GET /api/teacher/cohorts` → list with student count + last activity
- **Today's Challenge** — same `DailyChallenge` component + override button
- **Quick actions** — Assign game, View gradebook, Wellbeing alerts badge
- **Set today's challenge** — teacher taps to override the daily challenge for their class

```jsx
// Core structure:
export default function TeacherHomePage() {
  // ...fetch cohorts, daily challenge, wellbeing alerts
  return (
    <div className="min-h-screen bg-gray-950 pb-20">
      <Header title="My Classes" />
      <div className="px-5 space-y-4 mt-4">
        <QuickActions actions={[
          { label: 'Assign Game', icon: '📤', path: '/games?assign=1' },
          { label: 'Gradebook', icon: '📊', path: '/teacher/gradebook' },
          { label: 'Wellbeing', icon: `🔔 ${alertCount || ''}`, path: '/teacher' },
        ]} />
        <CohortsList cohorts={cohorts} />
        <DailyChallengeTeacher challenge={challenge} onOverride={handleOverride} />
      </div>
    </div>
  );
}
```

### Task 5.2 — Parent Home Screen

**Files:**
- Create: `frontend-react/src/pages/ParentHomePage.jsx`

Key sections:
- **Child's week** — games played this week, streak, XP gained
- **Skill snapshot** — top 3 dimensions with week-on-week delta
- **Weak spot** — same recommendation the child sees ("Aryan's weakest area is risk tolerance — here's what we're recommending this week")
- **Course progress** — if enrolled in a course, show progress %

```jsx
export default function ParentHomePage() {
  // Fetch via existing /api/family/* endpoints
  // Show one child at a time with tabs for multiple children
  return (
    <div className="min-h-screen bg-gray-950 pb-20">
      <Header title="Your Child's Progress" />
      <ChildSelector children={children} selected={selectedChild} onSelect={setSelectedChild} />
      <div className="px-5 space-y-4 mt-4">
        <WeekSummaryCard child={selectedChild} />
        <SkillSnapshotCard scores={dimScores} deltas={weekDeltas} />
        <WeakSpotCard recommendation={childRec} />
        {activeCourse && <CourseProgressCard course={activeCourse} />}
      </div>
    </div>
  );
}
```

### Task 5.3 — HR Home Screen

**Files:**
- Create: `frontend-react/src/pages/HRHomePage.jsx`

Key sections:
- **Assessment batches** — table of active batches with candidate count + completion rate
- **Create new batch** — one-click CTA to `/assessment-manager`
- **Recent completions** — last 5 candidates who finished with quick score preview
- No streaks, no levels, no daily challenge

```jsx
export default function HRHomePage() {
  return (
    <div className="min-h-screen bg-gray-950 pb-20">
      <Header title="Assessment Manager" />
      <div className="px-5 space-y-4 mt-4">
        <CreateBatchCTA />
        <BatchesTable batches={batches} />
        <RecentCompletions completions={recentCompletions} />
      </div>
    </div>
  );
}
```

### Task 5.4 — Wire role routing in `App.jsx`

**Files:**
- Modify: `frontend-react/src/App.jsx`

- [ ] **Step 1: Update `RoleHome` component**

Replace the existing `RoleHome` switch with:
```jsx
function RoleHome() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" />;
  switch (user.role) {
    case 'student':    return <Navigate to="/home/student" />;
    case 'teacher':    return <Navigate to="/home/teacher" />;
    case 'parent':     return <Navigate to="/home/parent" />;
    case 'hr':         return <Navigate to="/home/hr" />;
    case 'admin':
    case 'school_admin': return <Navigate to="/admin" />;
    default:           return <Navigate to="/home/student" />;
  }
}
```

- [ ] **Step 2: Add routes**

```jsx
<Route path="/home/student"  element={<ProtectedRoute><StudentHomePage /></ProtectedRoute>} />
<Route path="/home/teacher"  element={<ProtectedRoute><TeacherHomePage /></ProtectedRoute>} />
<Route path="/home/parent"   element={<ProtectedRoute><ParentHomePage /></ProtectedRoute>} />
<Route path="/home/hr"       element={<ProtectedRoute><HRHomePage /></ProtectedRoute>} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/pages/TeacherHomePage.jsx \
        frontend-react/src/pages/ParentHomePage.jsx \
        frontend-react/src/pages/HRHomePage.jsx \
        frontend-react/src/App.jsx
git commit -m "feat: role-based home screens (teacher/parent/hr) + routing"
```

---

## Chunk 6 — Frontend: First-Time Onboarding Flow

### What this builds
A gated first-time onboarding flow for new students:
`PersonaQuiz` (existing, reused) → redirect to `/play/soft-skills-baseline-v1` → after baseline completes → `SkillProfileReveal` (new) → 3 curated recommendations → enter app

Trigger: `profile.onboarding_complete !== true` for students.

### Task 6.1 — `SkillProfileReveal.jsx` component

**Files:**
- Create: `frontend-react/src/components/onboarding/SkillProfileReveal.jsx`

- [ ] **Step 1: Write the component**

```jsx
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const DIM_LABELS = {
  strategic_thinking: 'Strategic Thinking', risk_tolerance: 'Risk Tolerance',
  delayed_gratification: 'Patience', adaptability: 'Adaptability',
  resilience: 'Resilience', empathy: 'Empathy',
};

export default function SkillProfileReveal({ scores, recommendations, onContinue }) {
  const [revealed, setRevealed] = useState(false);

  const sortedDims = Object.entries(scores)
    .filter(([, v]) => typeof v === 'number')
    .sort(([, a], [, b]) => b - a);

  const strongDim = sortedDims[0]?.[0];
  const weakDim = sortedDims[sortedDims.length - 1]?.[0];

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-5 py-10">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        className="max-w-sm w-full text-center">
        <div className="text-5xl mb-4">🧬</div>
        <h1 className="text-white text-2xl font-bold mb-2">Here's what we found</h1>
        <p className="text-gray-400 text-sm mb-8">
          Based on your baseline assessment
        </p>

        {/* Dimension bars */}
        <div className="space-y-3 text-left mb-8">
          {sortedDims.slice(0, 6).map(([dim, score], i) => (
            <motion.div key={dim} initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.12 }}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-300">{DIM_LABELS[dim] || dim}</span>
                <span className={score >= 60 ? 'text-emerald-400' : 'text-amber-400'}>
                  {score}
                </span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${score}%` }}
                  transition={{ duration: 0.8, delay: i * 0.12 + 0.3 }}
                  className={`h-2 rounded-full ${score >= 60 ? 'bg-emerald-400' : 'bg-amber-400'}`}
                />
              </div>
            </motion.div>
          ))}
        </div>

        {/* Insight line */}
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }}
          className="text-gray-300 text-sm bg-gray-800 rounded-xl p-4 mb-6">
          {strongDim && weakDim && (
            <>Your strongest skill is <strong className="text-emerald-400">{DIM_LABELS[strongDim]}</strong>.
            Your biggest growth opportunity is <strong className="text-amber-400">{DIM_LABELS[weakDim]}</strong>.</>
          )}
        </motion.p>

        {/* 3 game recommendations */}
        {!revealed ? (
          <motion.button
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5 }}
            onClick={() => setRevealed(true)}
            className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl transition-colors">
            See your personalised games →
          </motion.button>
        ) : (
          <AnimatePresence>
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              className="space-y-3 mb-4">
              {recommendations.map((rec, i) => (
                <motion.div key={rec.game_id} initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                  className="bg-gray-800 rounded-xl p-3 text-left">
                  <p className="text-white font-semibold text-sm">{rec.title}</p>
                  <p className="text-gray-400 text-xs mt-0.5">{rec.reason}</p>
                </motion.div>
              ))}
              <button onClick={onContinue}
                className="w-full py-3.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition-colors mt-2">
                Start my journey →
              </button>
            </motion.div>
          </AnimatePresence>
        )}
      </motion.div>
    </div>
  );
}
```

### Task 6.2 — `OnboardingPage.jsx`

**Files:**
- Create: `frontend-react/src/pages/OnboardingPage.jsx`

- [ ] **Step 1: Write the page**

```jsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getProfile, updateProfile } from '../api/profile';
import { getNextRecommendations } from '../api/journey';
import SkillProfileReveal from '../components/onboarding/SkillProfileReveal';
import PersonaFlow from '../components/game/PersonaFlow'; // existing component

// Steps: persona → baseline (redirects to game) → profile_reveal → done
export default function OnboardingPage() {
  const { user, updateAuth } = useAuth();
  const nav = useNavigate();
  const [step, setStep] = useState('loading');
  const [profile, setProfile] = useState(null);
  const [recs, setRecs] = useState([]);

  useEffect(() => {
    getProfile().then(p => {
      setProfile(p);
      if (!p?.persona?.type) {
        setStep('persona');
      } else if (!p?.baseline_complete) {
        setStep('baseline');
      } else if (!p?.onboarding_complete) {
        setStep('profile_reveal');
        getNextRecommendations().then(setRecs).catch(() => {});
      } else {
        nav('/', { replace: true }); // already onboarded
      }
    });
  }, []);

  const handlePersonaDone = async () => {
    setStep('baseline');
  };

  const handleBaselinePrompt = () => {
    nav(`/play/soft-skills-baseline-v1?onboarding=1`);
    // GamePlayPage will set baseline_complete on report and redirect back here
  };

  const handleOnboardingComplete = async () => {
    await updateProfile({ onboarding_complete: true });
    nav('/', { replace: true });
  };

  if (step === 'loading') return <div className="min-h-screen bg-gray-950 flex items-center justify-center"><div className="text-white">Loading…</div></div>;

  if (step === 'persona') return <PersonaFlow onComplete={handlePersonaDone} />;

  if (step === 'baseline') return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-5 text-center">
      <div className="text-5xl mb-4">🎯</div>
      <h1 className="text-white text-2xl font-bold mb-2">First, let's find your baseline</h1>
      <p className="text-gray-400 text-sm mb-8 max-w-xs">
        A quick 10-minute assessment to understand your current soft skill profile. We'll use this to personalise everything.
      </p>
      <button onClick={handleBaselinePrompt}
        className="px-8 py-3.5 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-xl transition-colors">
        Start Baseline Assessment →
      </button>
    </div>
  );

  if (step === 'profile_reveal') return (
    <SkillProfileReveal
      scores={profile?.dimension_scores || {}}
      recommendations={recs}
      onContinue={handleOnboardingComplete}
    />
  );

  return null;
}
```

### Task 6.3 — Gate first-time users

**Files:**
- Modify: `frontend-react/src/pages/StudentHomePage.jsx`

- [ ] **Step 1: Add onboarding redirect check**

In `StudentHomePage`, at top of `useEffect`:
```javascript
if (profile && !profile.onboarding_complete && user?.role === 'student') {
  nav('/onboarding', { replace: true });
  return;
}
```

- [ ] **Step 2: Add `/onboarding` route in `App.jsx`**

```jsx
<Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
```

- [ ] **Step 3: Backend — mark baseline_complete after report**

In `backend/app.py`, in the `/api/run/<id>/report` handler, after fetching the report:
```python
# Mark baseline complete if this was the baseline game
if game_id == BASELINE_GAME_ID:
    player_profile.update_profile(user_id, {"baseline_complete": True})
```

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/pages/OnboardingPage.jsx \
        frontend-react/src/components/onboarding/SkillProfileReveal.jsx \
        frontend-react/src/App.jsx backend/app.py
git commit -m "feat: first-time onboarding — persona → baseline → skill reveal → recommendations"
```

---

## Chunk 7 — Frontend: Game Discovery Redesign

### What this builds
A new `/discover` route replacing the 135-game flat grid. Three discovery modes:
1. **By Goal** — "I want to get better at…" → 8-12 curated games
2. **By Time** — "I have 5 / 15 / 30 mins" → filtered by `estimated_duration_minutes`
3. **By Level** — Beginner / Intermediate / Advanced

Max 12 games shown at a time. "Show more" pagination only. Quality filter active by default (hides `curated: false` games).

### Task 7.1 — `GameDiscoveryPage.jsx`

**Files:**
- Create: `frontend-react/src/pages/GameDiscoveryPage.jsx`

- [ ] **Step 1: Write the page**

```jsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getGamesForGoal } from '../api/journey';
import { games as getGames } from '../api/crud';
import GameCard from '../components/game/GameCard'; // existing

const GOALS = [
  { id: 'leadership',   label: 'Leadership',   icon: '👑', desc: 'Decision-making, delegation, resilience' },
  { id: 'negotiation',  label: 'Negotiation',  icon: '🤝', desc: 'Influence, empathy, strategic positioning' },
  { id: 'decisions',    label: 'Decisions',    icon: '⚡', desc: 'Risk, ethics, delayed gratification' },
  { id: 'empathy',      label: 'Empathy',      icon: '❤️', desc: 'Perspective-taking, emotional intelligence' },
  { id: 'resilience',   label: 'Resilience',   icon: '💪', desc: 'Handling failure, adaptability, grit' },
  { id: 'creativity',   label: 'Creativity',   icon: '✨', desc: 'Novel thinking, problem-solving' },
];

const TIME_FILTERS = [
  { label: '5 mins', max: 8 },
  { label: '15 mins', max: 18 },
  { label: '30 mins', max: 35 },
  { label: 'Any', max: 999 },
];

export default function GameDiscoveryPage() {
  const [mode, setMode] = useState('goal'); // 'goal' | 'time' | 'level'
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [timeFilter, setTimeFilter] = useState(TIME_FILTERS[3]);
  const [levelFilter, setLevelFilter] = useState('beginner'); // 'beginner' | 'intermediate' | 'advanced'
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(false);
  const nav = useNavigate();

  const LEVEL_TYPE_MAP = {
    beginner:     ['rounds', 'story_branching', 'minigame', 'quiz'],
    intermediate: ['board', 'card', 'card_board', 'trump_card', 'strategy_grid'],
    advanced:     ['ai_arena', 'negotiation', 'debate', 'chess_strategy', 'tower_defense'],
  };

  useEffect(() => {
    if (mode === 'goal' && selectedGoal) {
      setLoading(true);
      getGamesForGoal(selectedGoal.id)
        .then(g => { setGames(g.slice(0, 12)); setLoading(false); })
        .catch(() => setLoading(false));
    } else if (mode === 'time' || mode === 'level') {
      setLoading(true);
      getGames().then(({ games: allGames }) => {
        let filtered = allGames.filter(g => g.curated !== false);
        if (mode === 'time') {
          filtered = filtered.filter(g => (g.estimated_duration_minutes || 15) <= timeFilter.max);
        } else {
          const allowedTypes = LEVEL_TYPE_MAP[levelFilter] || [];
          filtered = filtered.filter(g => allowedTypes.includes(g.game_type));
        }
        setGames(filtered.slice(0, 12));
        setLoading(false);
      }).catch(() => setLoading(false));
    }
  }, [mode, selectedGoal, timeFilter, levelFilter]);

  return (
    <div className="min-h-screen bg-gray-950 pb-24">
      <div className="px-5 pt-8 pb-4">
        <h1 className="text-white text-2xl font-bold">Discover Games</h1>
        <p className="text-gray-400 text-sm mt-1">Find the right game for right now</p>
      </div>

      {/* Mode tabs */}
      <div className="flex gap-2 px-5 mb-4">
        {['goal', 'time', 'level'].map(m => (
          <button key={m} onClick={() => setMode(m)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
              mode === m ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}>
            {m === 'goal' ? '🎯 By Goal' : m === 'time' ? '⏱ By Time' : '📈 By Level'}
          </button>
        ))}
      </div>

      {/* Goal selector */}
      {mode === 'goal' && (
        <div className="px-5 grid grid-cols-2 gap-3 mb-5">
          {GOALS.map(goal => (
            <button key={goal.id} onClick={() => setSelectedGoal(goal)}
              className={`text-left p-3 rounded-xl border transition-all ${
                selectedGoal?.id === goal.id
                  ? 'border-indigo-500 bg-indigo-900/30'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-500'
              }`}>
              <div className="text-2xl mb-1">{goal.icon}</div>
              <div className="text-white text-sm font-semibold">{goal.label}</div>
              <div className="text-gray-400 text-xs mt-0.5">{goal.desc}</div>
            </button>
          ))}
        </div>
      )}

      {/* Time filter */}
      {mode === 'time' && (
        <div className="flex gap-2 px-5 mb-5">
          {TIME_FILTERS.map(tf => (
            <button key={tf.label} onClick={() => setTimeFilter(tf)}
              className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                timeFilter.label === tf.label ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}>
              {tf.label}
            </button>
          ))}
        </div>
      )}

      {/* Level filter */}
      {mode === 'level' && (
        <div className="flex gap-2 px-5 mb-5">
          {['beginner', 'intermediate', 'advanced'].map(l => (
            <button key={l} onClick={() => setLevelFilter(l)}
              className={`px-4 py-2 rounded-xl text-sm font-medium capitalize transition-colors ${
                levelFilter === l ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}>
              {l}
            </button>
          ))}
        </div>
      )}

      {/* Game grid — max 12 */}
      <div className="px-5">
        {loading ? (
          <div className="grid grid-cols-2 gap-3">
            {Array(6).fill(0).map((_, i) => (
              <div key={i} className="h-36 bg-gray-800 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : games.length > 0 ? (
          <div className="grid grid-cols-2 gap-3">
            {games.map(g => <GameCard key={g.game_id} game={g} />)}
          </div>
        ) : (
          mode !== 'goal' || selectedGoal ? (
            <p className="text-gray-500 text-center py-12">No games found for this filter</p>
          ) : (
            <p className="text-gray-500 text-center py-12">Pick a goal above to see curated games</p>
          )
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add `/discover` route in `App.jsx`**

```jsx
<Route path="/discover" element={<ProtectedRoute><GameDiscoveryPage /></ProtectedRoute>} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/pages/GameDiscoveryPage.jsx frontend-react/src/App.jsx
git commit -m "feat: game discovery — by goal/time/level, max 12 shown"
```

---

## Chunk 8 — Frontend + Backend: Post-Game Retention Improvements

### What this builds
Three additions to `PostGameInsights.jsx`:
1. **"What to play next"** — one specific game recommendation with the reason (weakest dimension)
2. **"Challenge a friend"** — social hook if the user has friends
3. **Clearer improvement number** — "You improved Empathy by +12 points" as the headline metric

Plus a backend change: the `/api/run/<id>/report` response includes `next_recommended_game`.

### Task 8.1 — Backend: include `next_recommended_game` in report

**Files:**
- Modify: `backend/app.py` (report endpoint)

- [ ] **Step 1: Add recommendation to report response**

In the `/api/run/<id>/report` handler, just before building the final response:

```python
# Next game recommendation
next_game_rec = None
try:
    _dim_scores = report_core.get("dimension_scores", {})
    if _dim_scores and user_payload:
        _uid = user_payload["user_id"]
        _profile = player_profile.get_profile(_uid) or {}
        _level = _profile.get("level", 1)
        _unlocked = _get_unlocked_game_types_for_level(_level)
        _recent = {e.get("game_id") for e in _profile.get("game_history", [])[-10:] if e.get("game_id")}
        _weakest = min(_dim_scores, key=lambda d: _dim_scores.get(d, 100))
        for gid, _g in GAMES.items():
            if gid in _recent or gid == game_id:
                continue
            if _g.get("game_type") not in _unlocked:
                continue
            if _g.get("dimension_scoring_weights", {}).get(_weakest, 0) >= 0.25:
                next_game_rec = {
                    "game_id": gid,
                    "title": _g.get("title", gid),
                    "reason": f"Your weakest area is {_weakest.replace('_', ' ')} — this game targets it directly.",
                }
                break
except Exception as _e:
    logger.debug(f"next_game_rec failed: {_e}")

# Add to response
report_core["next_recommended_game"] = next_game_rec
```

### Task 8.2 — Frontend: "What to play next" + "Challenge a friend"

**Files:**
- Modify: `frontend-react/src/components/game/PostGameInsights.jsx`

- [ ] **Step 1: Add "What to Play Next" section**

After the career suggestions section, add:

```jsx
{/* What to play next */}
{reportCore?.next_recommended_game && (
  <div className="mt-6 p-4 bg-indigo-900/30 border border-indigo-500/30 rounded-2xl">
    <p className="text-indigo-300 text-xs font-semibold uppercase tracking-wide mb-2">What to play next</p>
    <div className="flex items-center gap-3">
      <span className="text-2xl">🎯</span>
      <div className="flex-1">
        <p className="text-white font-semibold">{reportCore.next_recommended_game.title}</p>
        <p className="text-gray-400 text-sm">{reportCore.next_recommended_game.reason}</p>
      </div>
      <button
        onClick={() => navigate(`/play/${reportCore.next_recommended_game.game_id}`)}
        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl transition-colors whitespace-nowrap"
      >
        Play →
      </button>
    </div>
  </div>
)}

{/* Challenge a friend */}
{user?.role === 'student' && reportCore?.game_id && (
  <div className="mt-3 p-4 bg-gray-800/60 rounded-2xl flex items-center gap-3">
    <span className="text-xl">👥</span>
    <div className="flex-1">
      <p className="text-white text-sm font-semibold">Challenge a friend</p>
      <p className="text-gray-400 text-xs">Dare them to beat your score</p>
    </div>
    <button
      onClick={() => navigate(`/social?challenge=${reportCore.game_id}`)}
      className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs font-semibold rounded-lg transition-colors"
    >
      Send →
    </button>
  </div>
)}
```

- [ ] **Step 2: Make the top improvement metric more prominent**

At the top of `PostGameInsights`, find where the score is displayed and add a headline improvement line:

```jsx
{/* Headline improvement */}
{(() => {
  const scores = reportCore?.dimension_scores || {};
  const top = Object.entries(scores).sort(([,a],[,b]) => b - a)[0];
  if (!top) return null;
  const [dim, score] = top;
  const DIM_LABELS = { strategic_thinking: 'Strategic Thinking', risk_tolerance: 'Risk Tolerance',
    delayed_gratification: 'Patience', adaptability: 'Adaptability',
    resilience: 'Resilience', empathy: 'Empathy' };
  return (
    <div className="text-center py-4">
      <p className="text-gray-400 text-sm">Top skill this session</p>
      <p className="text-3xl font-black text-emerald-400 mt-1">{score}<span className="text-lg text-emerald-600">/100</span></p>
      <p className="text-gray-300 text-sm mt-0.5">{DIM_LABELS[dim] || dim}</p>
    </div>
  );
})()}
```

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/components/game/PostGameInsights.jsx backend/app.py
git commit -m "feat: post-game retention — next game rec + challenge friend + headline improvement"
```

---

## Deployment Sequence

- [ ] **1.** Run game quality scoring script on server: `python backend/scripts/score_game_quality.py`
- [ ] **2.** Upload backend files: `app.py`, `daily_challenge.py`, `player_profile.py`, `data/unlock_rules.json`, `data/game_quality.json`
- [ ] **3.** Restart backend: `systemctl restart mentoapp-backend`
- [ ] **4.** Verify: `curl /api/daily-challenge` → game returned; `curl /api/recommendations/next` → 3 games
- [ ] **5.** Run `npm run build` → upload dist/ → verify frontend loads
- [ ] **6.** Test student flow: new user → onboarding → baseline → profile reveal → recommendations
- [ ] **7.** Test teacher flow: login as teacher → TeacherHomePage loads → set daily challenge override
- [ ] **8.** Test HR flow: login as hr → HRHomePage loads with assessment batches
- [ ] **9.** Test parent flow: login as parent → child progress visible

---

## Verification Checklist

| Test | Expected |
|---|---|
| `GET /api/daily-challenge` | Returns one game, same game for same org+date |
| `GET /api/recommendations/next` (student token) | Returns ≤3 games targeting weakest dim |
| `GET /api/recommendations/for-goal?goal=negotiation` | Returns ≤12 games |
| `GET /api/profile/level-info` | Returns level, XP to next, unlocked types |
| Student first login | Redirects to `/onboarding` → persona → baseline → profile reveal |
| Student returning login | Goes to `/home/student` — shows Continue + Daily Challenge + Weak Spot |
| Teacher login | Goes to `/home/teacher` — shows My Classes + override button |
| Parent login | Goes to `/home/parent` — shows child progress |
| HR login | Goes to `/home/hr` — shows assessment batches |
| `/discover` | Shows goal/time/level modes, max 12 games each |
| Post-game | Shows "What to play next" card + "Challenge a friend" |
| Game quality | `curated: false` games hidden from discovery by default |
| Level 1 student | Cannot access ai_arena/negotiation/debate game cards |
| Level 7+ student | Can access all game types |
| Teacher grant-access | Student unlocked for game_type before level threshold |
