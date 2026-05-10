# P0 — Stabilize & Score Honesty Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace ~90% authored dimension scoring with a 50/50 authored+behavioral blend, surface confidence intervals, wire dormant behavioral signals, ship 4 must-have module fixes (M1 composite, M2 rubric, M5 IRT bank, M6 moderation), and the must-ship UI for all of the above. Three weeks for a 2-backend + 1-frontend team.

**Architecture:** Behavioral signals already computed in `backend/engines/behavioral_analytics.py` (analyze_session_behavior + 25 signals) get blended into existing dimension scoring functions in `backend/app.py` via a single new helper in `backend/engines/dimension_utils.py`. Bootstrap CI computed inline. v1 scores preserved alongside v2 in API responses for 2-week shadow window. Module composite is a new endpoint, not a replacement.

**Tech Stack:** Python 3.11+, Flask, pytest, React 18, Vite, Tailwind, Anthropic Claude (claude-sonnet-4-6 via existing `backend/llm.py`).

**Parent plan:** `2026-05-02-mentoapp-roadmap-master.md`

---

## File Structure

### Backend files

| Path | Action | Purpose |
|---|---|---|
| `backend/engines/dimension_utils.py` | EXTEND | Add `compute_dimension_ci()`, `blend_authored_behavioral()`, `infer_risk_level_from_volatility()`, `zscore_normalize_for_leaderboard()` |
| `backend/app.py` | MODIFY | `_compute_rounds_dimension_scores`, `_compute_story_dimension_scores`, `_compute_strategy_dimension_scores` — wire behavioral blend; emit `score_v1` + `score_v2` + `ci_low` + `ci_high`. New endpoint `/api/run/<id>/reflection`. Leaderboard writers use ci_low. |
| `backend/llm.py` | EXTEND | Add `grade_reflection_text(text, dimension_focus)` → `{score, dim_signals, strengths, improvements}` |
| `backend/llm.py` | EXTEND | Add `grade_worksheet_freetext(text, lesson, rubric)` → `{score, strengths, improvements, dim_signals}` |
| `backend/modules_engine.py` | EXTEND | Add `compute_module_composite_v2(prog, module)` → 5-channel composite. Add `select_quiz_questions_irt(lesson, prog)` → bank-aware question selection. Field-mission moderation hook. |
| `backend/app.py` | MODIFY | New endpoint `GET /api/modules/<id>/report-v2`. Modify `submit_worksheet` to call rubric grading on textarea types. Modify `add_field_mission_entry` route to call moderator. |
| `backend/scripts/strip_dg_from_timed_quizzes.py` | NEW | Bulk-edit timed_challenge games: strip `delayed_gratification` skill_tags, add `adaptability` |
| `backend/tests/snapshots/` | NEW DIR | Regression snapshots for 8 reference games |
| `backend/tests/test_dimension_blend.py` | NEW | Tests for blend, CI, normalization |
| `backend/tests/test_modules_v2.py` | NEW | Tests for composite, IRT bank selection, moderation |
| `backend/tests/test_reflection_scoring.py` | NEW | Tests for reflection-input scoring channel |

### Frontend files

| Path | Action | Purpose |
|---|---|---|
| `frontend-react/src/components/game/PostGameInsights.jsx` | MODIFY | Methodology banner, CI bands on each dimension bar |
| `frontend-react/src/components/game/MentoScoreBreakdown.jsx` | MODIFY | Refactor to consume canonical 14-dim data; render 7-aggregate executive summary derived from those |
| `frontend-react/src/pages/LeaderboardPage.jsx` | MODIFY | Rank tooltip; "Ranked by lower bound of confidence interval" copy |
| `frontend-react/src/components/game/ReflectionPrompt.jsx` | MODIFY | POST rationale to `/api/run/<id>/reflection`; show toast with dim_signals |
| `frontend-react/src/components/module/WorksheetRubricResult.jsx` | NEW | Rubric panel: score, strengths, improvements, dim_signals |
| `frontend-react/src/components/module/worksheets/index.jsx` | MODIFY | Render `WorksheetRubricResult` after submit for textarea-heavy types |
| `frontend-react/src/pages/ModuleReportPage.jsx` | MODIFY | Render new composite v2 (5 channels with mini-bars), per-dim trajectory mini-chart |
| `frontend-react/src/api/profile.js` | MODIFY | Add `getModuleReportV2(moduleId)`, `submitReflection(runId, payload)`, `submitWorksheetForGrading(...)` |
| `frontend-react/src/locales/en.json` | MODIFY | Add P0 strings |
| `frontend-react/src/locales/hi.json` | MODIFY | Hindi translations |

### Bulk-edit & migration

| Path | Action |
|---|---|
| `backend/scripts/strip_dg_from_timed_quizzes.py` | NEW; idempotent; writes `.bak` files; runs `validate_all_games.py` after |
| `backend/scripts/snapshot_v1_baseline.py` | NEW; runs 8 reference games to fixed seed; writes `backend/tests/snapshots/<game_id>_v1.json` |

---

## Pre-flight: Resolve open questions

Settle these in the first 2 days. They block code changes.

- [ ] **Pre-flight 1: Decide MentoScoreBreakdown taxonomy**

  Choose one of:
  - (A) MentoScoreBreakdown becomes a derived view: 7 aggregate buckets computed from the 14 PostGameInsights dimensions
  - (B) MentoScoreBreakdown is deprecated; remove from GameOverScreen

  **Default if undecided:** (A). Document choice in `docs/decisions/2026-05-02-canonical-dimension-taxonomy.md`.

- [ ] **Pre-flight 2: Decide CI alpha**

  Choose 0.10 (90% CI, more stable leaderboard) or 0.05 (95% CI, more conservative).

  **Default:** 0.10. Document in `backend/engines/dimension_utils.py` docstring.

- [ ] **Pre-flight 3: Decide rollout granularity**

  Per-org flag (each org admin flips) vs global flag (single switch).

  **Default:** per-org via `org.score_version: 2` in `backend/data/organizations.json`.

- [ ] **Pre-flight 4: Commit pre-flight decisions**

  ```bash
  git add docs/decisions/
  git commit -m "decision: P0 pre-flight — taxonomy, CI alpha, rollout granularity"
  ```

---

## Day 1 — Snapshot baseline (Task 1)

### Task 1: Capture v1 regression snapshots

**Files:**
- Create: `backend/scripts/snapshot_v1_baseline.py`
- Create: `backend/tests/snapshots/.gitkeep`
- Create: `backend/tests/test_snapshot_regression.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_snapshot_regression.py`:
```python
import json
import os
import pytest

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
REFERENCE_GAMES = [
    "cfo-quarterly-close",
    "lemonade-empire-enhanced",
    "founders-gambit",
    "series-a-founders-journey",
    "project-management-mastery",
    "the-startup-decision",
    "climate-champions",
    "city-mayor",
]


@pytest.mark.parametrize("game_id", REFERENCE_GAMES)
def test_snapshot_exists(game_id):
    path = os.path.join(SNAPSHOT_DIR, f"{game_id}_v1.json")
    assert os.path.exists(path), f"Missing baseline snapshot: {path}"
    with open(path) as f:
        snap = json.load(f)
    assert "final_dimension_scores" in snap
    assert "kpis" in snap
    assert "total_score" in snap
    assert "completion_rate" in snap
    assert "seed" in snap
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_snapshot_regression.py -v
```
Expected: 8 FAILs ("Missing baseline snapshot").

- [ ] **Step 3: Implement snapshot generator**

`backend/scripts/snapshot_v1_baseline.py`:
```python
"""Generate v1 baseline snapshots for regression testing.

Runs 8 reference games to a fixed seed and saves end-of-game state.
P0+ changes must keep these stable for any game NOT opted into v2.
"""
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import _compute_rounds_dimension_scores, _compute_story_dimension_scores, _compute_strategy_dimension_scores
from storage import load_game

REFERENCE_GAMES = [
    "cfo-quarterly-close",
    "lemonade-empire-enhanced",
    "founders-gambit",
    "series-a-founders-journey",
    "project-management-mastery",
    "the-startup-decision",
    "climate-champions",
    "city-mayor",
]

SEED = 42


def simulate_game(game_id):
    """Run the game with fixed seed, choosing first option each round.
    Returns end-of-game state for snapshotting.
    """
    game = load_game(game_id)
    if game is None:
        return None
    state = {
        "user_id": "snapshot_user",
        "game_id": game_id,
        "seed": SEED,
        "choice_history": [],
        "resource_trajectory": [],
        "round_index": 0,
    }
    rounds = game.get("rounds", []) or game.get("scenes", [])
    for r in rounds:
        choices = r.get("choices", [])
        if not choices:
            continue
        chosen = choices[0]
        state["choice_history"].append({
            "round_id": r.get("id") or r.get("round_id"),
            "choice_id": chosen.get("id"),
            "skill_tags": chosen.get("skill_tags", []),
            "deltas": chosen.get("deltas", {}),
            "risk_level": chosen.get("risk_level"),
            "decision_time_ms": 5000,
        })
        deltas = chosen.get("deltas", {})
        prev = state["resource_trajectory"][-1] if state["resource_trajectory"] else {}
        next_r = {**prev, **{k: prev.get(k, 0) + v for k, v in deltas.items() if isinstance(v, (int, float))}}
        state["resource_trajectory"].append(next_r)
        state["round_index"] += 1

    game_type = game.get("game_type", "rounds")
    if game_type == "story_branching":
        scores = _compute_story_dimension_scores(state, ending_type="standard")
    elif game_type in ("chess_strategy", "strategy_grid"):
        scores = _compute_strategy_dimension_scores(state)
    else:
        scores = _compute_rounds_dimension_scores(state, game)

    final_kpis = state["resource_trajectory"][-1] if state["resource_trajectory"] else {}
    return {
        "game_id": game_id,
        "seed": SEED,
        "completion_rate": 1.0,
        "total_score": sum(v for v in final_kpis.values() if isinstance(v, (int, float))),
        "final_dimension_scores": scores,
        "kpis": final_kpis,
        "round_count": len(state["choice_history"]),
    }


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "snapshots")
    os.makedirs(out_dir, exist_ok=True)
    for game_id in REFERENCE_GAMES:
        result = simulate_game(game_id)
        if result is None:
            print(f"SKIP: {game_id} not found")
            continue
        path = os.path.join(out_dir, f"{game_id}_v1.json")
        with open(path, "w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        print(f"WROTE: {path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run snapshot generator**

```bash
cd backend && python scripts/snapshot_v1_baseline.py
```
Expected: `WROTE: tests/snapshots/<game_id>_v1.json` × 8.

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && pytest tests/test_snapshot_regression.py -v
```
Expected: 8 PASSes.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/snapshot_v1_baseline.py backend/tests/test_snapshot_regression.py backend/tests/snapshots/
git commit -m "test: capture v1 regression snapshots for 8 reference games"
```

---

## Day 2-4 — Behavioral blend foundation (Tasks 2–4)

### Task 2: Add behavioral signal aggregator

**Files:**
- Modify: `backend/engines/dimension_utils.py`
- Test: `backend/tests/test_dimension_blend.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_dimension_blend.py`:
```python
import pytest
from backend.engines.dimension_utils import aggregate_behavioral_signals


def test_aggregate_behavioral_signals_returns_dict_per_dimension():
    state = {
        "choice_history": [
            {"decision_time_ms": 8000, "deltas": {"money": 10}, "risk_level": "low"},
            {"decision_time_ms": 7500, "deltas": {"money": -5}, "risk_level": "low"},
            {"decision_time_ms": 12000, "deltas": {"money": 20}, "risk_level": "high"},
        ],
        "resource_trajectory": [
            {"money": 100},
            {"money": 110},
            {"money": 105},
            {"money": 125},
        ],
    }
    out = aggregate_behavioral_signals(state)
    assert isinstance(out, dict)
    for dim in ("strategic_thinking", "risk_tolerance", "delayed_gratification",
                "adaptability", "resilience", "empathy"):
        assert dim in out
        assert 0 <= out[dim] <= 100, f"{dim} score out of bounds: {out[dim]}"


def test_aggregate_with_empty_history_returns_neutral():
    state = {"choice_history": [], "resource_trajectory": []}
    out = aggregate_behavioral_signals(state)
    for dim in ("strategic_thinking", "risk_tolerance"):
        assert out[dim] == 50  # neutral when no signal


def test_recovery_pattern_increases_resilience():
    state = {
        "choice_history": [{"decision_time_ms": 5000, "deltas": {"money": -50}, "risk_level": "low"}] * 5,
        "resource_trajectory": [
            {"money": 100}, {"money": 50}, {"money": 60}, {"money": 80}, {"money": 95},
        ],
    }
    out = aggregate_behavioral_signals(state)
    assert out["resilience"] > 50, f"Expected resilience > 50 with recovery pattern, got {out['resilience']}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/test_dimension_blend.py::test_aggregate_behavioral_signals_returns_dict_per_dimension -v
```
Expected: FAIL with `ImportError: cannot import name 'aggregate_behavioral_signals'`.

- [ ] **Step 3: Implement `aggregate_behavioral_signals`**

Append to `backend/engines/dimension_utils.py`:
```python
from backend.engines.behavioral_analytics import (
    compute_timing_stats,
    detect_risk_averse_streak,
    detect_recovery_pattern,
    detect_consistency_pattern,
    score_consistency,
    score_recovery_ability,
    score_risk_seeking,
    score_grit,
)


def aggregate_behavioral_signals(state):
    """Roll behavioral signals from behavioral_analytics into per-dimension 0-100 scores.

    Returns a dict with keys matching STANDARD_DIMENSIONS.
    Returns 50 (neutral) for any dimension with insufficient signal.
    """
    history = state.get("choice_history", []) or []
    trajectory = state.get("resource_trajectory", []) or []
    if not history:
        return {d: 50 for d in (
            "strategic_thinking", "risk_tolerance", "delayed_gratification",
            "adaptability", "resilience", "empathy"
        )}

    timing = compute_timing_stats(history)
    consistency = score_consistency(history, trajectory)
    recovery = score_recovery_ability(trajectory)
    risk_seek = score_risk_seeking(history, trajectory)
    grit = score_grit(trajectory, history)

    mean_ms = timing.get("mean_ms", 5000)
    deliberation_score = max(0, min(100, ((mean_ms - 2000) / 80)))

    return {
        "strategic_thinking": int(0.6 * consistency + 0.4 * deliberation_score),
        "risk_tolerance": int(risk_seek),
        "delayed_gratification": int(deliberation_score),
        "adaptability": int(0.5 * consistency + 0.5 * recovery),
        "resilience": int(0.7 * recovery + 0.3 * grit),
        "empathy": 50,
    }
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd backend && pytest tests/test_dimension_blend.py -v
```
Expected: 3 PASSes.

- [ ] **Step 5: Commit**

```bash
git add backend/engines/dimension_utils.py backend/tests/test_dimension_blend.py
git commit -m "feat(scoring): aggregate behavioral signals into per-dimension scores"
```

---

### Task 3: Add bootstrap confidence interval helper

**Files:**
- Modify: `backend/engines/dimension_utils.py`
- Modify: `backend/tests/test_dimension_blend.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_dimension_blend.py`:
```python
from backend.engines.dimension_utils import compute_dimension_ci


def test_compute_dimension_ci_returns_low_high():
    samples = [60, 62, 58, 65, 61, 59, 63, 60, 62, 58]
    ci_low, ci_high = compute_dimension_ci(samples, alpha=0.10, B=200)
    assert ci_low < ci_high
    assert 50 < ci_low < 60
    assert 60 < ci_high < 70


def test_compute_dimension_ci_handles_single_sample():
    ci_low, ci_high = compute_dimension_ci([75], alpha=0.10, B=200)
    assert ci_low == ci_high == 75


def test_compute_dimension_ci_clips_to_0_100():
    ci_low, ci_high = compute_dimension_ci([95, 99, 100, 98, 97], alpha=0.10, B=200)
    assert ci_high <= 100
    assert ci_low >= 0
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && pytest tests/test_dimension_blend.py::test_compute_dimension_ci_returns_low_high -v
```
Expected: FAIL ImportError.

- [ ] **Step 3: Implement `compute_dimension_ci`**

Append to `backend/engines/dimension_utils.py`:
```python
import random


def compute_dimension_ci(samples, alpha=0.10, B=1000):
    """Bootstrap CI for a list of dimension scores (one per round or per sub-event).
    Returns (ci_low, ci_high) clipped to [0, 100].
    alpha=0.10 → 90% CI by default.
    """
    if not samples:
        return (50, 50)
    if len(samples) == 1:
        v = max(0, min(100, samples[0]))
        return (v, v)
    means = []
    n = len(samples)
    for _ in range(B):
        resample = [samples[random.randint(0, n - 1)] for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()
    lo_idx = int((alpha / 2) * B)
    hi_idx = int((1 - alpha / 2) * B) - 1
    return (max(0, min(100, means[lo_idx])), max(0, min(100, means[hi_idx])))
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_dimension_blend.py -v
```
Expected: 6 PASSes.

- [ ] **Step 5: Commit**

```bash
git add backend/engines/dimension_utils.py backend/tests/test_dimension_blend.py
git commit -m "feat(scoring): bootstrap confidence interval for dimension scores"
```

---

### Task 4: Implement scoring blend (50/50 authored + behavioral)

**Files:**
- Modify: `backend/engines/dimension_utils.py`
- Modify: `backend/tests/test_dimension_blend.py`

- [ ] **Step 1: Write failing tests**

Append to `backend/tests/test_dimension_blend.py`:
```python
from backend.engines.dimension_utils import blend_authored_behavioral


def test_blend_50_50():
    authored = {"strategic_thinking": 80, "empathy": 60}
    behavioral = {"strategic_thinking": 40, "empathy": 80}
    out = blend_authored_behavioral(authored, behavioral, w_authored=0.5, w_behavioral=0.5)
    assert out["strategic_thinking"] == 60
    assert out["empathy"] == 70


def test_blend_clips_to_0_100():
    authored = {"strategic_thinking": 120}
    behavioral = {"strategic_thinking": -20}
    out = blend_authored_behavioral(authored, behavioral, 0.5, 0.5)
    assert 0 <= out["strategic_thinking"] <= 100


def test_blend_uses_authored_when_behavioral_missing():
    out = blend_authored_behavioral({"empathy": 70}, {}, 0.5, 0.5)
    assert out["empathy"] == 70


def test_blend_returns_only_authored_keys():
    out = blend_authored_behavioral({"strategic_thinking": 50}, {"empathy": 80}, 0.5, 0.5)
    assert "empathy" not in out
    assert "strategic_thinking" in out
```

- [ ] **Step 2: Verify failure**

```bash
cd backend && pytest tests/test_dimension_blend.py::test_blend_50_50 -v
```
Expected: FAIL ImportError.

- [ ] **Step 3: Implement `blend_authored_behavioral`**

Append to `backend/engines/dimension_utils.py`:
```python
def blend_authored_behavioral(authored, behavioral, w_authored=0.5, w_behavioral=0.5):
    """Blend authored (tag-based) and behavioral scores per dimension.

    For dimensions present in `authored` but missing from `behavioral`,
    return the authored value unchanged (preserves back-compat).
    """
    out = {}
    for dim, a_score in (authored or {}).items():
        a = max(0, min(100, a_score))
        if dim in (behavioral or {}):
            b = max(0, min(100, behavioral[dim]))
            out[dim] = int(w_authored * a + w_behavioral * b)
        else:
            out[dim] = int(a)
    return out
```

- [ ] **Step 4: Run all tests**

```bash
cd backend && pytest tests/test_dimension_blend.py -v
```
Expected: 10 PASSes.

- [ ] **Step 5: Commit**

```bash
git add backend/engines/dimension_utils.py backend/tests/test_dimension_blend.py
git commit -m "feat(scoring): blend authored and behavioral dimension scores"
```

---

## Day 5–6 — Wire blend into app.py scoring functions (Tasks 5–7)

### Task 5: Wire blend into `_compute_rounds_dimension_scores`

**Files:**
- Modify: `backend/app.py:20333-20417`
- Test: `backend/tests/test_dimension_blend.py`

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_dimension_blend.py`:
```python
from backend.app import _compute_rounds_dimension_scores


def test_rounds_scores_emit_v1_v2_and_ci():
    state = {
        "choice_history": [
            {"decision_time_ms": 8000, "skill_tags": ["empathy"],
             "deltas": {"money": 10}, "risk_level": "low"}
        ] * 5,
        "resource_trajectory": [{"money": v} for v in [100, 110, 115, 125, 140, 150]],
        "completion_rate": 1.0,
    }
    out = _compute_rounds_dimension_scores(state)
    assert "score_v1" in out
    assert "score_v2" in out
    assert "ci" in out
    for dim in out["score_v1"]:
        assert 0 <= out["score_v1"][dim] <= 100
        assert 0 <= out["score_v2"][dim] <= 100
        assert dim in out["ci"]
        ci = out["ci"][dim]
        assert "low" in ci and "high" in ci
        assert ci["low"] <= ci["high"]
```

- [ ] **Step 2: Verify failure**

```bash
cd backend && pytest tests/test_dimension_blend.py::test_rounds_scores_emit_v1_v2_and_ci -v
```
Expected: FAIL — current function returns flat dict.

- [ ] **Step 3: Modify `_compute_rounds_dimension_scores`**

Read current implementation in `backend/app.py:20333-20417`. Wrap the existing return value as `score_v1`. Compute `score_v2 = blend_authored_behavioral(score_v1, aggregate_behavioral_signals(state))`. Compute `ci` per dimension by bootstrapping over rounds.

```python
# At top of app.py imports section:
from backend.engines.dimension_utils import (
    aggregate_behavioral_signals,
    blend_authored_behavioral,
    compute_dimension_ci,
)

# Modify _compute_rounds_dimension_scores:
def _compute_rounds_dimension_scores(state, game=None):
    # ... existing tag-counting + base+bonus formulas remain ...
    # Save original return as `authored`:
    authored = {
        "strategic_thinking": min(100, 35 + tag_counts.get("strategic_thinking", 0) * 7
                                  + int(completion_rate * 25)),
        "risk_tolerance": _existing_risk_calc(...),
        # ... all existing dims ...
    }

    behavioral = aggregate_behavioral_signals(state)
    blended = blend_authored_behavioral(authored, behavioral, w_authored=0.5, w_behavioral=0.5)

    # Per-dimension bootstrap CI from per-round score samples
    per_round_samples = _build_per_round_dimension_samples(state, authored)
    ci = {dim: dict(zip(("low", "high"), compute_dimension_ci(per_round_samples.get(dim, [blended[dim]]))))
          for dim in blended}

    return {
        "score_v1": authored,
        "score_v2": blended,
        "ci": ci,
    }


def _build_per_round_dimension_samples(state, final_authored):
    """For each dimension, generate a per-round score sample by re-computing
    authored partial through round k. Used as bootstrap input for CI.
    """
    history = state.get("choice_history", []) or []
    samples = {dim: [] for dim in final_authored}
    for k in range(1, len(history) + 1):
        partial_state = {**state, "choice_history": history[:k]}
        partial = _compute_rounds_dimension_scores_authored_only(partial_state)
        for dim, v in partial.items():
            samples[dim].append(v)
    return samples


def _compute_rounds_dimension_scores_authored_only(state, game=None):
    """Authored-only scoring (extracted from old function body).
    Used internally to produce per-round samples for CI bootstrap.
    """
    # ... extract the authored-formula body from old _compute_rounds_dimension_scores ...
```

- [ ] **Step 4: Update all callers of `_compute_rounds_dimension_scores`**

Find every call site. Each currently expects flat dict; now gets `{score_v1, score_v2, ci}`. Add `_canonical_scores(result, org_score_version)` adapter:
```python
def _canonical_scores(result, score_version=1):
    """Pick which score version to surface to caller (back-compat shim)."""
    if not isinstance(result, dict) or "score_v1" not in result:
        return result
    return result["score_v1"] if score_version == 1 else result["score_v2"]
```

- [ ] **Step 5: Run dimension test**

```bash
cd backend && pytest tests/test_dimension_blend.py::test_rounds_scores_emit_v1_v2_and_ci -v
```
Expected: PASS.

- [ ] **Step 6: Run snapshot regression**

```bash
cd backend && python scripts/snapshot_v1_baseline.py
cd backend && pytest tests/test_snapshot_regression.py -v
```
Expected: PASS — `score_v1` matches the original snapshots since the authored-only formula is unchanged.

- [ ] **Step 7: Commit**

```bash
git add backend/app.py backend/tests/test_dimension_blend.py
git commit -m "feat(scoring): emit score_v1, score_v2, and CI from rounds scoring"
```

---

### Task 6: Wire blend into `_compute_story_dimension_scores`

**Files:**
- Modify: `backend/app.py:20438-20498`
- Test: `backend/tests/test_dimension_blend.py`

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_dimension_blend.py`:
```python
from backend.app import _compute_story_dimension_scores


def test_story_scores_emit_v1_v2_and_ci():
    state = {
        "choice_history": [
            {"skill_tags": ["empathy", "ethical_reasoning"], "delta": +5,
             "decision_time_ms": 9000, "risk_level": "low"},
            {"skill_tags": ["adaptability"], "delta": -2,
             "decision_time_ms": 6000, "risk_level": "medium"},
            {"skill_tags": ["empathy"], "delta": +3,
             "decision_time_ms": 8500, "risk_level": "low"},
        ],
        "resource_trajectory": [],  # story_branching has no resource trajectory
    }
    out = _compute_story_dimension_scores(state, ending_type="growth")
    assert "score_v1" in out
    assert "score_v2" in out
    assert "ci" in out
    for dim in out["score_v1"]:
        assert 0 <= out["score_v1"][dim] <= 100
        assert 0 <= out["score_v2"][dim] <= 100
        ci = out["ci"][dim]
        assert ci["low"] <= ci["high"]


def test_story_scores_v1_unchanged_for_empty_behavioral():
    """When choice_history has no timing data, behavioral is neutral and v2 ≈ v1."""
    state = {"choice_history": [{"skill_tags": ["empathy"], "delta": +5}], "resource_trajectory": []}
    out = _compute_story_dimension_scores(state, ending_type="standard")
    # With one choice and no timing, behavioral defaults to 50; blend = 0.5*authored + 0.5*50
    for dim in out["score_v1"]:
        v1 = out["score_v1"][dim]
        v2 = out["score_v2"][dim]
        expected_v2 = int(0.5 * v1 + 0.5 * 50)
        assert abs(v2 - expected_v2) <= 2, f"{dim}: v2={v2} vs expected {expected_v2}"
```

- [ ] **Step 2: Verify failure**

```bash
cd backend && pytest tests/test_dimension_blend.py::test_story_scores_emit_v1_v2_and_ci -v
```
Expected: FAIL — current function returns flat dict.

- [ ] **Step 3: Modify `_compute_story_dimension_scores`**

Read existing implementation at `backend/app.py:20438-20498`. Apply same wrapping pattern as Task 5:

```python
def _compute_story_dimension_scores(state_or_log, ending_type="standard"):
    # Existing function body becomes _compute_story_dimension_scores_authored_only.
    # Wrapper version:
    authored = _compute_story_dimension_scores_authored_only(state_or_log, ending_type=ending_type)

    # Build state shape that aggregate_behavioral_signals understands
    if isinstance(state_or_log, list):
        state = {"choice_history": state_or_log, "resource_trajectory": []}
    else:
        state = state_or_log

    behavioral = aggregate_behavioral_signals(state)
    blended = blend_authored_behavioral(authored, behavioral, w_authored=0.5, w_behavioral=0.5)

    # Per-round samples for bootstrap CI
    history = state.get("choice_history", []) if isinstance(state, dict) else state_or_log
    samples = {dim: [] for dim in authored}
    for k in range(1, len(history) + 1):
        partial = _compute_story_dimension_scores_authored_only(
            history[:k] if isinstance(state_or_log, list)
            else {**state, "choice_history": history[:k]},
            ending_type=ending_type,
        )
        for dim, v in partial.items():
            samples[dim].append(v)
    ci = {dim: dict(zip(("low", "high"),
                        compute_dimension_ci(samples.get(dim, [blended[dim]]))))
          for dim in blended}

    return {"score_v1": authored, "score_v2": blended, "ci": ci}


def _compute_story_dimension_scores_authored_only(state_or_log, ending_type="standard"):
    """Authored-only story scoring (extracted from old function body).
    Original 60 lines of skill_tag counting + ending bonus mapping go here unchanged.
    """
    # ... extract original body verbatim ...
```

- [ ] **Step 4: Update callers** — same pattern as Task 5; use `_canonical_scores` adapter.

- [ ] **Step 5: Run dimension + snapshot tests**

```bash
cd backend && pytest tests/test_dimension_blend.py -v
cd backend && pytest tests/test_snapshot_regression.py -v
```
Expected: all PASS (story-branching games' `score_v1` unchanged).

- [ ] **Step 6: Commit**

```bash
git add backend/app.py backend/tests/test_dimension_blend.py
git commit -m "feat(scoring): emit score_v1/v2/ci from story_branching scoring"
```

---

### Task 7: Wire blend into `_compute_strategy_dimension_scores`

**Files:**
- Modify: `backend/app.py:20420-20435`
- Test: `backend/tests/test_dimension_blend.py`

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_dimension_blend.py`:
```python
from backend.app import _compute_strategy_dimension_scores


def test_strategy_scores_emit_v1_v2_and_ci():
    state = {
        "moves_made": 24,
        "final_score": 1450,
        "resources": {"territory": 18, "captures": 4, "blunders": 2},
        "choice_history": [
            {"decision_time_ms": 7500, "deltas": {"territory": +1}, "risk_level": "low"},
        ] * 24,
        "resource_trajectory": [{"territory": i} for i in range(25)],
    }
    out = _compute_strategy_dimension_scores(state)
    assert "score_v1" in out
    assert "score_v2" in out
    assert "ci" in out
    for dim in ("strategic_thinking", "risk_tolerance", "delayed_gratification",
                "adaptability", "resilience", "empathy"):
        assert dim in out["score_v1"]
        assert 0 <= out["score_v2"][dim] <= 100
        assert out["ci"][dim]["low"] <= out["ci"][dim]["high"]
```

- [ ] **Step 2: Verify failure**

```bash
cd backend && pytest tests/test_dimension_blend.py::test_strategy_scores_emit_v1_v2_and_ci -v
```
Expected: FAIL.

- [ ] **Step 3: Modify `_compute_strategy_dimension_scores`**

Read existing implementation at `backend/app.py:20420-20435` (16 lines). Apply same wrapping pattern:

```python
def _compute_strategy_dimension_scores(state):
    authored = _compute_strategy_dimension_scores_authored_only(state)
    behavioral = aggregate_behavioral_signals(state)
    blended = blend_authored_behavioral(authored, behavioral, 0.5, 0.5)

    # For strategy games, samples come from move-level dimension snapshots
    history = state.get("choice_history", []) or []
    samples = {dim: [] for dim in authored}
    for k in range(1, len(history) + 1):
        partial_state = {**state, "choice_history": history[:k],
                         "resource_trajectory": state.get("resource_trajectory", [])[:k+1]}
        partial = _compute_strategy_dimension_scores_authored_only(partial_state)
        for dim, v in partial.items():
            samples[dim].append(v)
    ci = {dim: dict(zip(("low", "high"),
                        compute_dimension_ci(samples.get(dim, [blended[dim]]))))
          for dim in blended}

    return {"score_v1": authored, "score_v2": blended, "ci": ci}


def _compute_strategy_dimension_scores_authored_only(state):
    """Authored-only strategy scoring (extracted from old function body verbatim)."""
    # ... extract original body ...
```

- [ ] **Step 4: Update callers** with `_canonical_scores` adapter.

- [ ] **Step 5: Run dimension + snapshot tests**

```bash
cd backend && pytest tests/test_dimension_blend.py -v
cd backend && pytest tests/test_snapshot_regression.py -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app.py backend/tests/test_dimension_blend.py
git commit -m "feat(scoring): emit score_v1/v2/ci from strategy scoring"
```

---

## Day 7–8 — Z-score normalization + leaderboard CI ranking (Tasks 8–9)

### Task 8: Z-score normalization for leaderboard

**Files:**
- Modify: `backend/engines/dimension_utils.py`
- Modify: `backend/app.py` (leaderboard writers)
- Test: `backend/tests/test_dimension_blend.py`

- [ ] **Step 1: Write failing test**

```python
from backend.engines.dimension_utils import zscore_normalize_for_leaderboard


def test_zscore_normalize_uses_game_type_distribution():
    raw = {"strategic_thinking": 75}
    population_stats = {"strategic_thinking": {"mean": 60, "std": 10}}
    out = zscore_normalize_for_leaderboard(raw, population_stats)
    # z = (75-60)/10 = 1.5, mapped to 0..100 with mean 50, sd 15: 50 + 1.5*15 = 72.5
    assert 70 <= out["strategic_thinking"] <= 75


def test_zscore_handles_missing_population_stats():
    out = zscore_normalize_for_leaderboard({"strategic_thinking": 75}, {})
    assert out["strategic_thinking"] == 75
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement**

```python
def zscore_normalize_for_leaderboard(raw_scores, population_stats):
    """Convert raw 0-100 to game-type-normalized 0-100.
    Maps z to (50 + 15*z) and clips to [0, 100].
    """
    out = {}
    for dim, v in (raw_scores or {}).items():
        stats = (population_stats or {}).get(dim) or {}
        mean = stats.get("mean")
        std = stats.get("std")
        if mean is None or std is None or std == 0:
            out[dim] = v
            continue
        z = (v - mean) / std
        out[dim] = max(0, min(100, int(50 + 15 * z)))
    return out
```

- [ ] **Step 4: Wire into `_save_strategy_leaderboard`, `_submit_strategy_leaderboard`, `_save_chess_leaderboard`** to call `zscore_normalize_for_leaderboard` with cached per-game-type population stats from `backend/data/leaderboard_pop_stats.json`.

- [ ] **Step 5: Add a daily cron job to recompute population stats** in the existing `_run_scheduler()` block in app.py.

- [ ] **Step 6: Run tests**

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(scoring): per-game-type Z-score normalization on leaderboard write"
```

---

### Task 9: Leaderboard ranks by CI lower bound

**Files:**
- Modify: `backend/app.py` (leaderboard writers and readers)
- Test: `backend/tests/test_dimension_blend.py`

- [ ] **Step 1: Test that leaderboard entries store ci_low** — extend the leaderboard write tests.

- [ ] **Step 2: Modify each `_save_*_leaderboard`** to write `{score, score_v2, ci_low, ci_high, ranked_by: "ci_low"}` instead of just `score`.

- [ ] **Step 3: Modify `api_get_leaderboard`, `api_skill_leaderboard`** sort by `ci_low DESC`, fall back to `score DESC` for legacy entries without ci_low.

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(leaderboard): rank by CI lower bound for new entries; back-compat for legacy"
```

---

## Day 9 — Bulk-edit timed quiz games (Task 10)

### Task 10: Strip `delayed_gratification` from timed_challenge games

**Files:**
- Create: `backend/scripts/strip_dg_from_timed_quizzes.py`
- Modify: ~12 timed_challenge JSONs in `backend/games/`
- Test: `backend/tests/test_game_json_validation.py` (existing — uses `validate_all_games.py`)

- [ ] **Step 1: List affected games**

```bash
cd backend && python -c "
import json, os, glob
for p in sorted(glob.glob('games/*.json')):
    if '.bak' in p: continue
    try:
        g = json.load(open(p))
    except: continue
    if g.get('game_type') == 'timed_challenge':
        print(p)
"
```
Expected: ~12 paths.

- [ ] **Step 2: Write the migration script**

`backend/scripts/strip_dg_from_timed_quizzes.py`:
```python
"""Strip delayed_gratification skill_tags from timed_challenge games; add adaptability.

Reasoning: timed quizzes test the OPPOSITE of delayed gratification (speed over
deliberation). The audit (§9 step 6) flags this as a tag-mechanic mismatch.

Idempotent. Writes .bak before mutation.
"""
import json
import os
import shutil
import sys
import glob

GAMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "games")


def strip_dg_in_obj(obj):
    """Recursively walk obj; replace 'delayed_gratification' with 'adaptability' in skill_tags arrays."""
    changed = False
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "skill_tags" and isinstance(v, list):
                if "delayed_gratification" in v:
                    obj[k] = [t if t != "delayed_gratification" else "adaptability" for t in v]
                    changed = True
            else:
                if strip_dg_in_obj(v):
                    changed = True
    elif isinstance(obj, list):
        for item in obj:
            if strip_dg_in_obj(item):
                changed = True
    return changed


def main():
    paths = sorted(glob.glob(os.path.join(GAMES_DIR, "*.json")))
    affected = []
    for p in paths:
        if ".bak" in p or ".retrofit.bak" in p:
            continue
        try:
            with open(p) as f:
                game = json.load(f)
        except Exception as e:
            print(f"SKIP {p}: {e}")
            continue
        if game.get("game_type") != "timed_challenge":
            continue
        if not strip_dg_in_obj(game):
            print(f"clean: {os.path.basename(p)}")
            continue
        bak = p + ".pre_dg_strip.bak"
        if not os.path.exists(bak):
            shutil.copy2(p, bak)
        with open(p, "w") as f:
            json.dump(game, f, indent=2, ensure_ascii=False)
        affected.append(p)
        print(f"updated: {os.path.basename(p)}")
    print(f"\nTotal updated: {len(affected)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the script**

```bash
cd backend && python scripts/strip_dg_from_timed_quizzes.py
```

- [ ] **Step 4: Validate all games**

```bash
cd backend && python validate_all_games.py
```
Expected: all PASS, no JSON errors.

- [ ] **Step 5: Spot-check a converted game**

```bash
cd backend && python -c "
import json
g = json.load(open('games/math-speed-challenge.json'))
import re
text = json.dumps(g)
assert 'delayed_gratification' not in text, 'still present!'
print('OK: delayed_gratification stripped')
"
```

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/strip_dg_from_timed_quizzes.py backend/games/*.json backend/games/*.pre_dg_strip.bak
git commit -m "fix(content): strip delayed_gratification skill_tags from timed_challenge games"
```

---

## Day 10–11 — Reflection-input scoring channel (Tasks 11–12)

### Task 11: Reflection LLM grader

**Files:**
- Modify: `backend/llm.py`
- Test: `backend/tests/test_reflection_scoring.py`

- [ ] **Step 1: Write failing test**

`backend/tests/test_reflection_scoring.py`:
```python
import pytest
from backend.llm import grade_reflection_text


def test_grade_reflection_returns_expected_shape(monkeypatch):
    def fake_call(*args, **kwargs):
        return {
            "score": 72,
            "dim_signals": {"empathy": 8, "strategic_thinking": 4},
            "strengths": ["Considered the other side's perspective"],
            "improvements": ["Could quantify the trade-off"],
        }
    monkeypatch.setattr("backend.llm._call_llm_json", fake_call)
    out = grade_reflection_text(
        "I chose this because the team felt overwhelmed and I wanted to give them space.",
        dimension_focus=["empathy", "strategic_thinking"],
    )
    assert out["score"] == 72
    assert out["dim_signals"]["empathy"] == 8


def test_grade_reflection_falls_back_on_empty(monkeypatch):
    out = grade_reflection_text("", dimension_focus=["empathy"])
    assert out["score"] == 0
    assert out["dim_signals"] == {}
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement**

Append to `backend/llm.py`:
```python
def grade_reflection_text(text, dimension_focus=None):
    """Grade a player's reflection rationale on quality of reasoning + dimension signals.

    Returns:
      {
        "score": int 0-100,
        "dim_signals": dict[dimension, int -10..+10],  # delta to add to authored
        "strengths": list[str],
        "improvements": list[str],
      }
    Returns zero-result for empty input.
    """
    text = (text or "").strip()
    if not text:
        return {"score": 0, "dim_signals": {}, "strengths": [], "improvements": []}
    if len(text) < 10:
        return {"score": 30, "dim_signals": {}, "strengths": [], "improvements": ["Add more detail"]}
    focus = ", ".join(dimension_focus or ["empathy", "strategic_thinking"])
    sys_prompt = (
        f"You are an educational psychologist scoring a student's reflection on a recent in-game choice. "
        f"Focus dimensions: {focus}. "
        f"Return JSON with fields: score (0-100), dim_signals (object mapping each focus dimension "
        f"to an integer -10..+10 indicating how strongly the reflection demonstrates that dimension), "
        f"strengths (array of short strings), improvements (array of short strings). "
        f"Be calibrated: 50 = generic, 70 = thoughtful, 85 = exceptionally insightful."
    )
    return _call_llm_json(sys_prompt, text)
```

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(scoring): LLM-based reflection text grader"
```

---

### Task 12: Reflection scoring endpoint + frontend wiring

**Files:**
- Modify: `backend/app.py` (new endpoint)
- Modify: `frontend-react/src/components/game/ReflectionPrompt.jsx`
- Modify: `frontend-react/src/api/profile.js` (new `submitReflection`)
- Test: `backend/tests/test_reflection_scoring.py`

- [ ] **Step 1: Write failing route test**

```python
def test_reflection_endpoint_attaches_signals(client, monkeypatch):
    monkeypatch.setattr("backend.llm.grade_reflection_text", lambda t, dimension_focus=None: {
        "score": 70, "dim_signals": {"empathy": 6}, "strengths": [], "improvements": []
    })
    rv = client.post("/api/run/run_test/reflection", json={
        "round_id": "round_1",
        "choice_id": "c_a",
        "rationale": "I prioritized the team over the deadline.",
    })
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["dim_signals"]["empathy"] == 6
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement endpoint**

```python
@app.route("/api/run/<run_id>/reflection", methods=["POST"])
@require_auth
def api_submit_reflection(run_id):
    payload = request.get_json(silent=True) or {}
    rationale = (payload.get("rationale") or "").strip()
    if not rationale:
        return jsonify({"error": "rationale_required"}), 400
    run = RUNS.get(run_id)
    if not run:
        return jsonify({"error": "run_not_found"}), 404
    focus = payload.get("dimension_focus") or run.get("game", {}).get("focus_dimensions") or ["empathy", "strategic_thinking"]
    graded = grade_reflection_text(rationale, dimension_focus=focus)
    reflections = run.setdefault("reflections", [])
    reflections.append({
        "round_id": payload.get("round_id"),
        "choice_id": payload.get("choice_id"),
        "rationale": rationale,
        "graded": graded,
        "ts": int(time.time()),
    })
    save_run(run)
    return jsonify({"ok": True, "score": graded["score"], "dim_signals": graded["dim_signals"]})
```

- [ ] **Step 4: Modify `aggregate_behavioral_signals`** to add reflection-signal contributions to the behavioral score.

- [ ] **Step 5: Modify `ReflectionPrompt.jsx`**

```jsx
// Inside component, after existing onSubmit:
const handleSubmit = async () => {
  if (!rationale.trim()) return;
  setSubmitting(true);
  try {
    const result = await submitReflection(runId, {
      round_id: roundId, choice_id: choiceId, rationale,
    });
    setFeedback(result);  // {score, dim_signals}
    setShowToast(true);
    setTimeout(onClose, 3500);
  } catch (e) {
    console.error("reflection submit failed", e);
    onClose();
  } finally {
    setSubmitting(false);
  }
};
```

Render `feedback` as a small toast: `"Empathy +6 · You showed perspective-taking."`

- [ ] **Step 6: Add `submitReflection` to `frontend-react/src/api/profile.js`**

```js
export async function submitReflection(runId, payload) {
  const r = await client.post(`/api/run/${runId}/reflection`, payload);
  return r.data;
}
```

- [ ] **Step 7: Add i18n keys**

`frontend-react/src/locales/en.json`:
```json
"reflection": {
  "feedback_title": "Reflection captured",
  "feedback_dim_delta": "{{dim}} {{sign}}{{delta}}"
}
```

- [ ] **Step 8: Run tests**

- [ ] **Step 9: Commit**

```bash
git commit -m "feat(reflection): submit rationale → LLM grade → score channel + frontend toast"
```

---

## Day 12 — Module composite v2 (Task 13)

### Task 13: Modules report v2 endpoint

**Files:**
- Modify: `backend/modules_engine.py`
- Modify: `backend/app.py` (new endpoint)
- Test: `backend/tests/test_modules_v2.py`

- [ ] **Step 1: Write failing test**

```python
def test_module_report_v2_returns_5_channels(client, sample_module_progress):
    rv = client.get(f"/api/modules/mento_entrepreneur_4week/report-v2")
    body = rv.get_json()
    assert "composite" in body
    assert "channels" in body["composite"]
    for ch in ("quiz_avg", "rubric_avg", "reflection_depth", "anchored_game_dim_avg", "time_on_task"):
        assert ch in body["composite"]["channels"]
    assert "per_dim_delta" in body["composite"]
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement `compute_module_composite_v2` in `modules_engine.py`**

```python
def compute_module_composite_v2(prog, module):
    """5-channel composite: quiz_avg, rubric_avg, reflection_depth, anchored_game_dim_avg, time_on_task.
    Plus per-dimension delta from start of module to now.
    """
    channels = {
        "quiz_avg": _avg_quiz_score(prog),
        "rubric_avg": _avg_rubric_score(prog),
        "reflection_depth": _avg_reflection_depth(prog),
        "anchored_game_dim_avg": _avg_anchored_game_dim(prog),
        "time_on_task": _normalize_time_on_task(prog, module),
    }
    weights = {"quiz_avg": 0.25, "rubric_avg": 0.20, "reflection_depth": 0.15,
               "anchored_game_dim_avg": 0.30, "time_on_task": 0.10}
    composite_score = sum(channels[k] * weights[k] for k in channels if channels[k] is not None)
    per_dim_delta = _compute_dim_delta(prog)
    return {
        "score": int(composite_score),
        "channels": channels,
        "weights": weights,
        "per_dim_delta": per_dim_delta,
    }
```

- [ ] **Step 4: Implement endpoint in app.py**

- [ ] **Step 5: Run tests**

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(modules): composite v2 report with 5 channels + per-dim delta"
```

---

## Day 13–14 — Worksheet rubric grading (M2) (Tasks 14–15)

### Task 14: Worksheet LLM grader

**Files:**
- Modify: `backend/llm.py`
- Test: `backend/tests/test_modules_v2.py`

- [ ] **Step 1: Write failing test**

Append to `backend/tests/test_modules_v2.py`:
```python
import pytest
from backend.llm import grade_worksheet_freetext


def test_grade_worksheet_returns_expected_shape(monkeypatch):
    def fake_call(*args, **kwargs):
        return {
            "score": 78,
            "strengths": ["Clear customer profile", "Specific metrics"],
            "improvements": ["Validate willingness to pay"],
            "dim_signals": {"creativity": 5, "commercial_acumen": 6},
        }
    monkeypatch.setattr("backend.llm._call_llm_json", fake_call)
    rubric = {
        "anchors": {
            "novice": "Vague problem statement",
            "capable": "Specific user, specific pain",
            "strong": "Specific user + specific pain + measurable size",
            "exec": "All of strong, plus differentiated wedge",
        },
        "signals": ["mentions specific user", "quantifies pain"],
    }
    out = grade_worksheet_freetext(
        text="Working parents struggle to find affordable after-school tutoring; market is ~$2B.",
        lesson={"id": "lesson_idea_scorecard", "type": "idea_scorecard"},
        rubric=rubric,
    )
    assert out["score"] == 78
    assert "Validate willingness to pay" in out["improvements"]


def test_grade_worksheet_caches_by_content_hash(monkeypatch):
    call_count = {"n": 0}
    def fake_call(*args, **kwargs):
        call_count["n"] += 1
        return {"score": 70, "strengths": [], "improvements": [], "dim_signals": {}}
    monkeypatch.setattr("backend.llm._call_llm_json", fake_call)
    rubric = {"anchors": {}, "signals": []}
    grade_worksheet_freetext("same text", {"id": "L1", "type": "reflection"}, rubric)
    grade_worksheet_freetext("same text", {"id": "L1", "type": "reflection"}, rubric)
    assert call_count["n"] == 1, "Second identical call should hit cache"


def test_grade_worksheet_handles_empty_text():
    out = grade_worksheet_freetext("", {"id": "L1", "type": "reflection"}, {"anchors": {}, "signals": []})
    assert out["score"] == 0
    assert out["dim_signals"] == {}
```

- [ ] **Step 2: Verify failure**

```bash
cd backend && pytest tests/test_modules_v2.py::test_grade_worksheet_returns_expected_shape -v
```
Expected: FAIL ImportError.

- [ ] **Step 3: Implement `grade_worksheet_freetext`**

Append to `backend/llm.py`:
```python
import hashlib

_WORKSHEET_GRADE_CACHE = {}  # {sha256 → graded_dict}; capped at 2000 entries
_WORKSHEET_CACHE_MAX = 2000


def grade_worksheet_freetext(text, lesson, rubric):
    """Grade a free-text worksheet response against a rubric.

    Returns:
      {
        "score": int 0-100,
        "strengths": list[str],
        "improvements": list[str],
        "dim_signals": dict[dimension, int -10..+10],
      }
    Cached by SHA256(text + lesson_id + rubric_version).
    Returns zero-result for empty text.
    """
    text = (text or "").strip()
    if not text:
        return {"score": 0, "strengths": [], "improvements": [], "dim_signals": {}}
    rubric_version = (rubric or {}).get("version", "v1")
    lesson_id = (lesson or {}).get("id", "unknown")
    key_str = f"{text}|{lesson_id}|{rubric_version}"
    cache_key = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
    if cache_key in _WORKSHEET_GRADE_CACHE:
        return _WORKSHEET_GRADE_CACHE[cache_key]

    anchors = (rubric or {}).get("anchors", {}) or {}
    signals = (rubric or {}).get("signals", []) or []
    sys_prompt = (
        "You are an educational assessor scoring a student's free-text worksheet response.\n"
        f"Lesson type: {(lesson or {}).get('type', 'unknown')}.\n"
        f"Rubric anchors: {anchors}\n"
        f"Signals to look for: {signals}\n"
        "Return JSON with: score (0-100, calibrated to anchors), "
        "strengths (array of short phrases citing what the student did well), "
        "improvements (array of short phrases for next iteration), "
        "dim_signals (object mapping dimension names to integer -10..+10)."
    )
    result = _call_llm_json(sys_prompt, text)

    # Cap cache size with simple FIFO eviction
    if len(_WORKSHEET_GRADE_CACHE) >= _WORKSHEET_CACHE_MAX:
        first_key = next(iter(_WORKSHEET_GRADE_CACHE))
        _WORKSHEET_GRADE_CACHE.pop(first_key)
    _WORKSHEET_GRADE_CACHE[cache_key] = result
    return result
```

- [ ] **Step 4: Run tests**

```bash
cd backend && pytest tests/test_modules_v2.py::test_grade_worksheet_returns_expected_shape \
                       tests/test_modules_v2.py::test_grade_worksheet_caches_by_content_hash \
                       tests/test_modules_v2.py::test_grade_worksheet_handles_empty_text -v
```
Expected: 3 PASSes.

- [ ] **Step 5: Commit**

```bash
git add backend/llm.py backend/tests/test_modules_v2.py
git commit -m "feat(modules): LLM worksheet rubric grader with content-hash cache"
```

---

### Task 15: Wire grader into `submit_worksheet` + frontend rubric panel

**Files:**
- Modify: `backend/modules_engine.py::save_worksheet` and the corresponding route in `app.py`
- Create: `frontend-react/src/components/module/WorksheetRubricResult.jsx`
- Modify: `frontend-react/src/components/module/worksheets/index.jsx`
- Modify: `frontend-react/src/api/modules.js`
- i18n keys

- [ ] **Step 1: Test** — submit worksheet → expect `rubric` field in response for textarea-heavy types.

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Modify `save_worksheet`** to call `grade_worksheet_freetext` for textarea types (`reflection`, `pitch_builder`, `customer_profile`, `idea_scorecard`). Persist in `prog["rubrics"][lesson_id]`.

- [ ] **Step 4: Build `WorksheetRubricResult.jsx`**

```jsx
import React from 'react';
import { useTranslation } from 'react-i18next';

export default function WorksheetRubricResult({ rubric }) {
  const { t } = useTranslation();
  if (!rubric) return null;
  return (
    <div className="mt-4 p-4 rounded-lg border" style={{borderColor:'var(--primary)'}}>
      <div className="flex items-center gap-3 mb-3">
        <div className="text-3xl font-bold" style={{color:'var(--primary)'}}>{rubric.score}</div>
        <div className="text-sm text-gray-600">{t('worksheet.rubric_score')}</div>
      </div>
      {rubric.strengths?.length > 0 && (
        <div className="mb-3">
          <div className="font-semibold text-green-700 text-sm mb-1">✓ {t('worksheet.strengths')}</div>
          <ul className="list-disc list-inside text-sm">
            {rubric.strengths.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}
      {rubric.improvements?.length > 0 && (
        <div className="mb-3">
          <div className="font-semibold text-amber-700 text-sm mb-1">↗ {t('worksheet.improvements')}</div>
          <ul className="list-disc list-inside text-sm">
            {rubric.improvements.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}
      {Object.keys(rubric.dim_signals || {}).length > 0 && (
        <div className="flex gap-2 flex-wrap text-xs">
          {Object.entries(rubric.dim_signals).map(([dim, delta]) => (
            <span key={dim} className="px-2 py-1 rounded bg-blue-50 text-blue-700">
              {dim} {delta >= 0 ? '+' : ''}{delta}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Render in worksheet container** — after submit, pass `rubric` prop down.

- [ ] **Step 6: i18n keys**

- [ ] **Step 7: Run tests**

- [ ] **Step 8: Commit**

```bash
git commit -m "feat(modules): worksheet rubric panel + grading on submit"
```

---

## Day 15 — IRT quiz bank (M5) (Task 16)

### Task 16: Quiz item bank with Rasch theta selection

**Files:**
- Modify: `backend/modules_engine.py`
- Schema doc: `docs/modules-quiz-bank.md`
- Test: `backend/tests/test_modules_v2.py`

- [ ] **Step 1: Write failing test** — given a lesson with `quiz.bank` of 12 items at varied difficulty and a player's prior `theta`, verify `select_quiz_questions_irt` returns N items closest to theta (one-parameter Rasch).

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Implement**

```python
def select_quiz_questions_irt(lesson, prog, n=5):
    """Select N questions from lesson.quiz.bank at difficulty closest to player's theta.
    Falls back to legacy lesson.quiz.questions if no bank.
    """
    quiz = lesson.get("quiz", {}) or {}
    bank = quiz.get("bank") or []
    if not bank:
        return quiz.get("questions", [])[:n]
    theta = prog.get("quiz_theta", {}).get(lesson.get("id"), 0.0)
    bank_sorted = sorted(bank, key=lambda q: abs(q.get("difficulty", 0.0) - theta))
    seen_ids = set(prog.get("quiz_seen_ids", {}).get(lesson.get("id"), []))
    fresh = [q for q in bank_sorted if q.get("id") not in seen_ids][:n]
    if len(fresh) < n:
        fresh += [q for q in bank_sorted if q.get("id") in seen_ids][: n - len(fresh)]
    return fresh


def update_quiz_theta(prog, lesson_id, items_correct, items_total):
    """Naive Rasch theta update: shift by 0.5 per question above/below 50% correct."""
    if items_total == 0:
        return prog
    pct = items_correct / items_total
    delta = (pct - 0.5) * 1.0  # ±0.5 per question over 50%
    th = prog.setdefault("quiz_theta", {})
    th[lesson_id] = max(-3.0, min(3.0, th.get(lesson_id, 0.0) + delta))
    return prog
```

- [ ] **Step 4: Wire into quiz attempt route**

- [ ] **Step 5: Document schema** in `docs/modules-quiz-bank.md`:
```markdown
## Quiz item bank

Add `quiz.bank` to a lesson:
{
  "quiz": {
    "bank": [
      {"id": "q1", "difficulty": -1.0, "skill_tags": ["resilience"], "prompt": "...", "options": ["..."], "correct": 0},
      ...
    ],
    "n_questions_per_attempt": 5
  }
}
```

- [ ] **Step 6: Run tests**

- [ ] **Step 7: Commit**

```bash
git commit -m "feat(modules): IRT-based quiz item bank with Rasch theta selection"
```

---

## Day 16 — Field mission moderation (M6) (Task 17)

### Task 17: Wire ContentModerator to add_field_mission_entry

**Files:**
- Modify: `backend/modules_engine.py::add_field_mission_entry`
- Modify: `backend/app.py` (route)
- Test: `backend/tests/test_modules_v2.py`

- [ ] **Step 1: Write failing test**

```python
def test_field_mission_blocks_toxic_text(monkeypatch):
    monkeypatch.setattr("backend.ai.content_moderator.ContentModerator.moderate_text",
                        lambda self, text: {"flagged": True, "categories": ["toxicity"], "score": 0.92})
    out = add_field_mission_entry("u1", "mod1", "lesson1", {"text": "hateful content here"})
    assert out["status"] == "blocked"
    assert "moderation_score" in out


def test_field_mission_borderline_flags_for_teacher_review(monkeypatch):
    monkeypatch.setattr("backend.ai.content_moderator.ContentModerator.moderate_text",
                        lambda self, text: {"flagged": False, "categories": [], "score": 0.55})
    out = add_field_mission_entry("u1", "mod1", "lesson1", {"text": "edgy borderline"})
    assert out["status"] == "needs_review"
```

- [ ] **Step 2: Verify failure**

- [ ] **Step 3: Add `moderate_text` method to `ContentModerator`** if not already present; wrap existing pipeline.

- [ ] **Step 4: Modify `add_field_mission_entry`**

```python
from backend.ai.content_moderator import ContentModerator
_MODERATOR = ContentModerator()


def add_field_mission_entry(user_id, module_id, lesson_id, entry):
    text = entry.get("text", "")
    if text:
        result = _MODERATOR.moderate_text(text)
        score = result.get("score", 0)
        if result.get("flagged") or score >= 0.85:
            return {"status": "blocked", "moderation_score": score, "categories": result.get("categories", [])}
        if 0.5 <= score < 0.85:
            entry["moderation_status"] = "needs_review"
        else:
            entry["moderation_status"] = "ok"
        entry["moderation_score"] = score
    # ... existing append logic ...
```

- [ ] **Step 5: Run tests**

- [ ] **Step 6: Commit**

```bash
git commit -m "feat(modules): wire content moderation to field-mission entries"
```

---

## Day 17–18 — Frontend: methodology banner, CI bands, taxonomy reconcile (Tasks 18–20)

### Task 18: Methodology banner + CI bands in PostGameInsights

**Files:**
- Modify: `frontend-react/src/components/game/PostGameInsights.jsx:208`+
- Modify: `frontend-react/src/locales/en.json`, `hi.json`
- Test: visual via Storybook (or manual smoke test)

- [ ] **Step 1: Add CI band rendering**

Inside the dimension-bar render block:
```jsx
{dimScore.ci && (
  <div className="relative h-1 mt-1">
    <div className="absolute h-full bg-gray-200" style={{width: '100%'}} />
    <div className="absolute h-full bg-blue-300"
         style={{
           left: `${dimScore.ci.low}%`,
           width: `${dimScore.ci.high - dimScore.ci.low}%`
         }} />
  </div>
)}
<div className="text-xs text-gray-500 mt-1">
  {t('insights.ci_label', { low: dimScore.ci.low, high: dimScore.ci.high })}
</div>
```

- [ ] **Step 2: Add methodology banner**

Above the dimension list:
```jsx
<div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 flex items-start gap-2">
  <span>📊</span>
  <div className="flex-1 text-sm">
    <strong>{t('insights.methodology_banner.title')}</strong>{' '}
    <span>{t('insights.methodology_banner.body')}</span>{' '}
    <a href="/methodology" className="text-blue-700 underline">{t('insights.methodology_banner.link')}</a>
  </div>
</div>
```

- [ ] **Step 3: i18n keys**

```json
"insights": {
  "methodology_banner": {
    "title": "Score now reflects how you played, not just what you chose.",
    "body": "We added timing, recovery, and consistency signals.",
    "link": "Learn how"
  },
  "ci_label": "{{low}}–{{high}} (90% confidence)"
}
```

- [ ] **Step 4: Smoke test in browser**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(insights): methodology banner and CI bands on dimension scores"
```

---

### Task 19: Reconcile MentoScoreBreakdown taxonomy

**Files:**
- Modify: `frontend-react/src/components/game/MentoScoreBreakdown.jsx`

- [ ] **Step 1: Choose path per Pre-flight 1**

If (A): refactor to derive 7 aggregate buckets from the 14 PostGameInsights dimensions.
If (B): remove from `GameOverScreen.jsx`.

- [ ] **Step 2: Implement chosen path**

For (A), add a derivation map:
```jsx
const AGGREGATE_FROM_DIMS = {
  resource_optimization: ['capital_allocation', 'commercial_acumen'],
  decision_quality: ['decision_quality', 'strategic_thinking'],
  achievement_progress: ['delayed_gratification', 'resilience'],
  competitive_performance: ['risk_tolerance', 'narrative_persuasion'],
  learning_engagement: ['adaptability', 'creativity'],
  speed_efficiency: ['decision_quality'],  // mean decision_time inverse
  risk_management: ['risk_tolerance', 'governance_judgment'],
};

function deriveAggregates(dimensionScores) {
  const out = {};
  for (const [aggKey, srcDims] of Object.entries(AGGREGATE_FROM_DIMS)) {
    const vals = srcDims.map(d => dimensionScores[d]).filter(v => v != null);
    out[aggKey] = vals.length ? Math.round(vals.reduce((a,b)=>a+b,0)/vals.length) : null;
  }
  return out;
}
```

- [ ] **Step 3: Visual smoke test**

- [ ] **Step 4: Commit**

```bash
git commit -m "fix(scoring): reconcile MentoScoreBreakdown taxonomy with PostGameInsights"
```

---

### Task 20: Leaderboard CI tooltip + ReflectionPrompt feedback toast

Already covered in tasks 12 + 9 frontend pieces. Final UI pass to verify:

- [ ] **Step 1: Verify LeaderboardPage tooltip**

- [ ] **Step 2: Verify ReflectionPrompt toast renders dim_signals**

- [ ] **Step 3: Mobile audit — both surfaces at 320px**

- [ ] **Step 4: Commit any fixes**

```bash
git commit -m "polish(insights): leaderboard tooltip + reflection toast mobile audit"
```

---

## Day 19 — Module Report v2 UI (Task 21)

### Task 21: ModuleReportPage v2 rendering

**Files:**
- Modify: `frontend-react/src/pages/ModuleReportPage.jsx`
- Modify: `frontend-react/src/api/modules.js`
- i18n keys

- [ ] **Step 1: Add `getModuleReportV2(moduleId)` to api/modules.js**

- [ ] **Step 2: Render 5-channel composite** with mini-bars (one per channel) and the per-dim delta as a small "since you started" chart.

```jsx
{report.composite && (
  <section className="bg-white rounded-2xl shadow-sm p-6 mt-6">
    <h2 className="text-xl font-bold mb-4">{t('module.composite.title')}</h2>
    <div className="text-5xl font-bold mb-1" style={{color: 'var(--primary)'}}>{report.composite.score}</div>
    <div className="text-sm text-gray-500 mb-4">{t('module.composite.subtitle')}</div>
    <div className="space-y-2">
      {Object.entries(report.composite.channels).map(([key, val]) => (
        <ChannelBar key={key} label={t(`module.composite.${key}`)} value={val} weight={report.composite.weights[key]} />
      ))}
    </div>
    <DimDeltaChart deltas={report.composite.per_dim_delta} />
  </section>
)}
```

- [ ] **Step 3: Add `What changed` panel** comparing v1 score (percent_complete) to v2 composite.

- [ ] **Step 4: i18n keys, smoke test**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(modules): module report v2 page with composite + per-dim trajectory"
```

---

## Day 20 — Shadow scoring window + admin flag (Task 22)

### Task 22: Wire org-level v2 flag

**Files:**
- Modify: `backend/data/organizations.json` schema
- Modify: `backend/app.py` — `_canonical_scores` reads `org.score_version`
- Modify: `frontend-react/src/components/admin/OrgsSection.jsx` — add toggle

- [ ] **Step 1: Add `score_version` field to org schema** (default 1)

- [ ] **Step 2: Modify run report endpoint** to return v1 by default; flip to v2 when `org.score_version == 2`. ALWAYS include both in response so frontend can show methodology preview.

- [ ] **Step 3: Add admin toggle** in `OrgsSection.jsx`: "Use v2 scoring (with confidence intervals + behavioral signals)" — default off.

- [ ] **Step 4: Smoke test**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat(scoring): per-org score_version toggle for shadow rollout"
```

---

## Day 21 — Final integration test pass + deploy

### Task 23: Full P0 acceptance suite

- [ ] **Step 1: Run all unit + integration tests**

```bash
cd backend && pytest -v
```

- [ ] **Step 2: Run snapshot regression**

```bash
cd backend && pytest tests/test_snapshot_regression.py -v
```
Expected: PASS — `score_v1` unchanged.

- [ ] **Step 3: Manual end-to-end smoke**

Play through `lemonade-empire-enhanced` to completion. Verify:
- Methodology banner appears
- CI bands render on each dimension
- ReflectionPrompt captures rationale and toast shows dim_signal delta
- LeaderboardPage rank tooltip appears
- A worksheet in `mento_entrepreneur_4week` (e.g., the pitch_builder lesson) shows rubric panel after submit
- Module report page shows v2 composite with 5 channels
- Field mission with toxic text is blocked
- Quiz retake serves different questions when `quiz.bank` declared

- [ ] **Step 4: Deploy to staging**

```bash
sshpass -p 'qwertY@1432o' rsync -avz -e 'ssh -o StrictHostKeyChecking=no' \
  backend/app.py backend/engines/dimension_utils.py backend/engines/behavioral_analytics.py \
  backend/llm.py backend/modules_engine.py backend/scripts/ backend/tests/ backend/games/ \
  root@206.189.143.244:/var/www/mentoapp/backend/
```

```bash
sshpass -p 'qwertY@1432o' ssh -o StrictHostKeyChecking=no root@206.189.143.244 \
  'systemctl restart mentoapp-backend'
```

Build and upload frontend:
```bash
cd frontend-react && npm run build
sshpass -p 'qwertY@1432o' ssh -o StrictHostKeyChecking=no root@206.189.143.244 \
  'rm -rf /var/www/mentoapp/frontend/assets/'
sshpass -p 'qwertY@1432o' rsync -avz -e 'ssh -o StrictHostKeyChecking=no' \
  frontend-react/dist/ root@206.189.143.244:/var/www/mentoapp/frontend/
```

- [ ] **Step 5: Verify health on production**

```bash
curl -s http://206.189.143.244:5001/api/games | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'OK: {len(d[\"games\"])} games')"
```

- [ ] **Step 6: Enable v2 for one pilot org only**

Set `score_version: 2` for one demo org in production `organizations.json`. Leave all others at v1. Watch for 1 week.

- [ ] **Step 7: Final commit + tag**

```bash
git commit --allow-empty -m "release: P0 stabilize-and-score-honesty complete"
git tag p0-complete
```

---

## Exit Criteria Summary

P0 is done when ALL of the following hold:

1. ✅ All unit tests pass: `pytest backend/tests/`
2. ✅ Snapshot regression: 8 reference games' `score_v1` matches captured baselines
3. ✅ One pilot org runs `score_version: 2` for ≥7 days without regression incidents
4. ✅ A 50-run benchmark of `lemonade_empire_v1` shows test-retest variance reduced > 30% under v2 vs v1
5. ✅ All P0 frontend surfaces (methodology banner, CI bands, rubric panel, module v2 report, leaderboard tooltip) render correctly at 320, 768, 1024, 1280px
6. ✅ All P0 frontend strings present in `en.json` and `hi.json`
7. ✅ Field-mission moderation blocks high-toxicity inputs in production
8. ✅ M2 worksheet rubric grading produces feedback for `reflection`, `pitch_builder`, `customer_profile`, `idea_scorecard` worksheets
9. ✅ M5 IRT bank serves different questions on retake when `quiz.bank` declared

When all 9 hold, write `2026-XX-XX-p1-financial-core.md` (using master plan §P1) and start P1.

---

**End of P0 detailed plan.**
