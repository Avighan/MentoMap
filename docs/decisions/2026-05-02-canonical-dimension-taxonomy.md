# P0 Pre-flight Decisions — 2026-05-02

Canonical resolutions for the three open architectural questions that block
any P0 code work. These were authorized before implementation began; this
document records them for traceability.

---

## Decision 1 — MentoScoreBreakdown Taxonomy (Pre-flight 1)

**Choice adopted:** (A) MentoScoreBreakdown becomes a derived view.

**Rationale:** PostGameInsights already surfaces 14 dimension labels that are
the closest-to-engine source of truth. Maintaining a parallel 7-bucket model
in MentoScoreBreakdown with different labels creates two competing score
surfaces that diverge silently. Making MentoScoreBreakdown a projection of
the 14 canonical dimensions collapses that gap without removing the 7-bucket
display players expect.

**Source of truth:** The 14 dimensions in
`frontend-react/src/components/game/PostGameInsights.jsx` (_DIM_LABELS) are
canonical. MentoScoreBreakdown's 7 buckets are a **derived projection** whose
mapping is defined in Task 19.

**Pricing-tier work is explicitly OUT of scope for P0.** No tier-gating,
paywall, or pricing UI changes are to be introduced as part of this plan.

**Implementation pointer:** Task 19 — reimplement
`frontend-react/src/components/game/MentoScoreBreakdown.jsx` as a derived
view that aggregates the 14 canonical dimensions into 7 display buckets.
Mapping spec is TBD in that task.

**Reversal cost:** LOW before Task 19 ships (only this doc changes). After
Task 19 ships: medium — requires unwiring the derived mapping and restoring
the old independent 7-bucket logic; no data migration needed.

---

## Decision 2 — CI Alpha (Pre-flight 2)

**Choice adopted:** alpha = 0.10 (90% confidence interval).

**Rationale:** The 14 dimension scores are noisy by design (3–10 rounds per
game). A 95% CI (alpha = 0.05) would produce intervals so wide they become
unactionable feedback for learners. 90% CI strikes the right balance between
statistical honesty and legibility. This can be tightened in a future round
once per-player sample sizes grow.

**Implementation pointer:** `backend/engines/dimension_utils.py` — the CI
computation function must use `alpha = 0.10`. A comment referencing this
decision has been added at the top of that file.

**Reversal cost:** LOW — changing alpha is a single constant. Any already-
stored interval values would be stale but are recalculated on demand; no
migration needed.

---

## Decision 3 — Rollout Granularity (Pre-flight 3)

**Choice adopted:** Per-org flag via `org.score_version: 2` in
`backend/data/organizations.json`.

**Rationale:** A single global flag would force all orgs onto the new scoring
at once, which is high-risk for schools already using the platform. Per-org
gating lets pilot orgs opt in while others stay on v1, consistent with the
existing `mystery_room_enabled` per-org flag pattern already in production.

**Implementation pointer:** `backend/data/organizations.json` — add
`"score_version": 2` to orgs that opt into P0 scoring. The score-serving
endpoint checks `org.score_version` (default `1`) and routes accordingly.
Schema change tracked in `backend/schemas.py`.

**Reversal cost:** MEDIUM — requires removing `score_version` from org
records and the routing logic in the score endpoint. No user-facing data is
lost; dimension raw scores are unchanged.

---

## Summary Table

| # | Question | Decision | Task |
|---|----------|----------|------|
| 1 | Score surface | MentoScoreBreakdown = derived view of 14 dims | Task 19 |
| 2 | CI alpha | 0.10 (90% CI) | dimension_utils.py |
| 3 | Rollout | Per-org `score_version: 2` | organizations.json + schemas.py |
