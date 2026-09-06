# Simulok → MentoMap Migration Plan

Status: draft, for review before Phase 1 starts.
Scope: move Simulok's simulation catalog and classroom/backend functionality into
MentoMap's schema, engines, and Flask backend. This document does not cover the
Simulok marketing website (`simulok.in`) or the standalone double-click demo
distribution model — those are separate decisions, noted under Open Questions.

---

## 1. Why migrate

Simulok today is a single 28,000-line client-side HTML file with two bolted-on
Google Apps Script services (contact form, classroom sessions). That design has
four structural ceilings that were identified during review and that MentoMap's
existing architecture already solves:

| Gap in Simulok | MentoMap's existing answer |
|---|---|
| Scores are computed client-side and self-reported; a student can forge a result | `grader_bp` + server-side `/api/run/*` lifecycle |
| Auth is a client-side label swap, no real accounts | JWT auth, RBAC (student/teacher/admin/trainer/school_admin), OTP reset |
| Classroom backend supports exactly one open session, globally, no concept of "class" | `organizations.py`, `cohort_live_sessions.py` already model cohorts/orgs |
| No automated tests anywhere | pytest (`conftest.py`, `tests/`) + Vitest already in place |

Migrating is therefore not a lateral move — it inherits a materially stronger
foundation for anything beyond a single-class pilot.

---

## 2. Game-by-game mapping

Simulok's ~40 games fall into four architectural tiers. Each maps to an existing
or lightly-extended MentoMap engine.

### Tier A — Discrete branching-choice sims (no new engine needed)
Covers the 20 `SIM_LIBRARY` titles plus the simpler legacy sims. MentoMap's own
game library already contains dozens of games in this exact shape (rounds →
choices → effects → weighted score), so this is a JSON-authoring task against
MentoMap's existing schema, not new engine code.

- Dealcraft, Brand Wars, Founders' Forge, Blue Ocean Sprint, Capital Storm
- Fraction Market, Probability Carnival, Lab Protocol, Eco-Balance, Forces-Play
- Pharma Batch Release, Pharma Med Affairs, Auto Launch, Auto Dealer, FMCG Promo
- InvoGrid, IndAS Peak, KaveriCIRP, TPlex, SutraCode
- Lemonade Stand, Summer Money Challenge, The Great Indian Bazaar
- DashMart, NimbooWala, DesiEats, ThreadCraft, Bullwhip Effect (currently external standalone files)
- CyberSafe, Decision Room, Zenith Appliances (currently orphaned/unlisted files)

**Work per game:** author a MentoMap game JSON (`game_id`, `rounds[].choices[].effects`,
`initial_state`, `dimension_scoring_weights`, `learning_objectives`), port the
`feedback`/`learning` teaching text as-is, map Simulok's 5-KPI score categories
onto MentoMap's dimension-scoring block.

### Tier B — Stateful settlement math (small custom module)
**The Mumbai Manufacturer.** Its period-close engine (demand fulfillment,
bullwhip-index drift, holding cost, stockout penalty, bank-debt interest) is
real computed logic, not a flat effects table — port `resolveMumbaiSettlement()`
into a new sibling module next to `engines/finance_engine.py` rather than trying
to flatten it into static JSON effects.

### Tier C — Continuous-lever / market-simulation sims (map to existing specialized engines)
**HelioGrid, MacroEcon, Zara, Zara-new, SoleForce.** These already use continuous
levers (price, discounts, allocation %) and a competitor model, not discrete
choices — a strong match for MentoMap's:
- `decision_panel_engine.py` (sliders/dials vs. an expert benchmark, drift scoring)
- `competitor_ai_engine.py` (Simulok's rival logic is a few lines of inline drift
  math; MentoMap's dedicated engine is a genuine upgrade here)
- `finance_engine.py` / `stock_market_engine.py` for P&L and market-clearing math

### Tier D — Bespoke multiplayer engine (new engine required)
**K2 — The Savage Mountain.** Hot-seat, 5 asymmetric roles, private briefs,
shared votes. No existing MentoMap engine (chess, escape-room, decision-panel,
mock-interview, etc.) covers asymmetric-role local multiplayer — this needs a
new engine (proposed: `expedition_engine.py`), built the same way it was
originally built in Simulok: as one bespoke module, not a schema extension.

---

## 3. Classroom/backend cutover

Replace both Simulok Apps Script services with MentoMap's existing backend
surface — this is largely a matter of pointing the frontend at routes that
already exist, not writing new backend from scratch:

| Simulok (Apps Script) | Replaced by (MentoMap) |
|---|---|
| `contact-form.gs` | Not in scope — marketing site concern, stays as-is or migrates separately |
| `classroom-session.gs` login (plaintext Roster tab) | `/api/auth/*` (JWT, RBAC) |
| `classroom-session.gs` open/close session (one global session) | `/api/run/*` session lifecycle, scoped per cohort via `organizations.py` / `cohort_live_sessions.py` |
| Client-computed, self-reported `complete_run` | `grader_bp` — score computed/verified server-side from the logged round history |
| Manual dashboard (`classroom/dashboard.html`, client-JS gated) | Existing teacher-facing routes (`/api/teacher/*`) — replace bespoke dashboard with MentoMap's, or keep the UI and swap its data source |

This directly closes the two concrete risks flagged earlier: the forgeable
client-reported grade, and the single-global-session limit that blocks running
more than one class/section at a time.

---

## 4. Phased plan

**Phase 0 — Foundations**
- Create migration branch in MentoMap (this document lives here).
- Confirm MentoMap's JSON schema fields precisely (game_id, rounds, choices,
  effects, dimension_scoring_weights) against 2-3 of Simulok's existing games.
- Pick pilot set: one Tier A game (Dealcraft), the Tier B game (Mumbai), one
  Tier C game (HelioGrid) — one of each archetype.

**Phase 1 — Pilot port**
- Port the 3 pilot games. Validate scoring parity against Simulok's existing
  grade tables (same choices → same grade/letter, not necessarily identical
  point totals).
- Smoke-test through MentoMap's `/api/run/*` lifecycle end-to-end.

**Phase 2 — Bulk port (Tier A)**
- Mechanical: author the remaining ~24 Tier A games as JSON. This is the bulk
  of the content work and is parallelizable across authors once the Phase 1
  schema is validated.

**Phase 3 — Custom engines (Tier B + D)**
- Build Mumbai's settlement module.
- Build K2's hot-seat engine.

**Phase 4 — Classroom cutover**
- Point classroom auth/session/scoring at MentoMap's existing routes.
- Retire `classroom-session.gs` once parity is confirmed; keep the Google Sheet
  read-only as a historical record during transition.

**Phase 5 — Content/IP review**
- Carry forward the earlier finding that K2/HelioGrid/MacroEcon are structural
  analogues of named HBS simulations (Everest V3, Managing Segments and
  Customers, Econland respectively) — this property is unchanged by the
  platform migration and should get a real legal review before wider release,
  independent of this technical work.

---

## 5. Risks and open questions

- **IP risk travels with the content, not the platform.** Moving K2/HelioGrid/
  MacroEcon into MentoMap does not change whether their structure is too close
  to their HBS analogues — that needs its own answer, not a side effect of this
  plan.
- **MentoMap's storage is file/JSON-based, not a full SQL database.** Verify it
  actually scales to a real MBA-college pilot's concurrent load (Phase 0)
  before treating the classroom cutover as a solved problem.
- **This is real authoring work, not a copy-paste.** ~40 games' worth of JSON
  plus scoring-weight tuning is the actual cost of this migration; engine
  compatibility removes the *architectural* blocker, not the labor.
- **Decide the fate of `simulok.in` and the standalone demo separately.** This
  plan is silent on whether the marketing site and the "double-click index.html"
  sales-demo distribution continue in parallel, get retired, or get pointed at
  MentoMap once it's live — that's a product decision, not a technical one.
