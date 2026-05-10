# MentoApp Simulation & Modules Roadmap — Master Execution Plan

> **For agentic workers:** This is a **master roadmap**, not a bite-sized task plan. Each phase has a separate detailed plan written just-in-time (see "Plan of Plans" at the bottom). To execute a specific phase, use that phase's plan with `superpowers:executing-plans` or `superpowers:subagent-driven-development`.

**Goal:** Bring MentoApp to commercial-sim parity (Capsim/HBP/Capitalism Lab) on simulation depth, fix the soft-skill scoring credibility gap, and graduate the modules system from breadth to depth — without breaking the live app.

**Out of scope for this roadmap:** No pricing-tier UI, no per-tier feature gating, no commercial-tier rollout. The audit's T0–T5 framing (in §19) is historical context, not a deliverable. Org-level feature flags exist for rollout discipline only, not for pricing.

**Source spec:** `MentoApp_Simulation_Audit_and_Roadmap.pdf` (2026-05-02, 30 pages, §§1–20).

**Architecture approach:** All new mechanics implemented as generic, JSON-driven, deterministic engines that emit structured tick-results. UI extends existing `SimulationRenderer` via a widget registry that consumes `tick_result.ui_hints`. Scoring shifts from ~90% authored to ~50/50 authored+behavioral with confidence intervals. Every breaking change is gated behind a per-game feature flag.

**Tech Stack:** Python (Flask, app.py, engines/), React (Vite, Tailwind, Framer Motion), JSON game configs, JSON player profile store with file locks, Anthropic Claude (claude-sonnet-4-6) for LLM grading.

**Total scope:** ~3,500–4,500 LOC engines + ~50 engineer-days modules + 6–8 sim widgets + scoring correction pass. ~38 calendar weeks for a 2-backend + 1-frontend team.

---

## Reality Check vs. Audit

The audit was largely accurate but the following items materially change the plan. These corrections come from a verification pass against `backend/` and `frontend-react/` (see verification report dated 2026-05-02).

| Audit claim | Verified reality | Plan impact |
|---|---|---|
| `finance_engine.py` rewrite is high-risk because cap-table is wired into existing games | **Orphan engine.** No game JSON references it. cap_table is computed in isolation. | P1 risk drops from HIGH to LOW. No feature flag needed for v2 — there is no v1 to preserve. CFO-quarterly-close uses ad-hoc P&L in app.py, not the engine. |
| `behavioral_analytics.py` exists but is "wired only to wellbeing path" | **25+ signals exist** including `analyze_session_behavior`, `record_dimension_snapshot`, `compute_growth_rate`, `get_growth_curves`. Plus `dimension_utils.adjust_scores_for_timing()` already implements one timing-based behavioral adjustment. | P0 is **wiring**, not building. Reduces P0 LOC by ~60%. |
| Modules composite formula is `0.6·quiz_avg + 0.4·pct_complete` | **No composite formula exists.** Modules use only `percent_complete = required_done / required_total`. Quiz scores are stored per-lesson but never aggregated. | M1 is "introduce a composite," not "fix one." Adds an additive endpoint, no migration needed. |
| `MentoScoreBreakdown.jsx` shows the same dimensions as `PostGameInsights.jsx` | **Different taxonomies.** PostGameInsights shows 14 dims (6 SEL + 8 exec). MentoScoreBreakdown shows 7 aggregate dims (resource_optimization, decision_quality, etc.). | Latent inconsistency. P0 must reconcile the two views or scope explicitly which is canonical. |
| `dimension_rubrics.json` doesn't exist | **Exists.** 135 lines, 8 exec dimensions, 4-tier anchors, signals_to_look_for arrays. | M2 rubric grading has the rubric pre-built. Lift drops to wiring + LLM call. |
| ~50 engines exist, "most are scaffolds" | **95 engines exist.** ~24 wired into app.py, ~71 orphan. Some Tier 2/3 engines (logistics, market_actors, market_engine) are orphan, not load-bearing. | New engines won't conflict with most "existing" ones; orphans become starting material to copy/refactor from, not constraints. |
| 11 worksheet types | **11 confirmed:** complaint_collector, three_tests, five_whys, brainstorm, customer_profile, idea_scorecard, pitch_builder, pledge, reflection, simple_form, budget_table | M11 (worksheet vocab expansion) starts from accurate inventory. |

**Net effect:** ~30% of the audit's stated work is already partly done; ~10% is mis-described and needs different work; ~60% is accurate. The total bounded estimate (3,500–4,500 LOC) is roughly correct, but the **shape** shifts toward wiring and integration rather than greenfield.

---

## Cross-Cutting Architecture Decisions

These apply to every phase and must be in place before P1 starts.

### CCA-1: Engine Contract (per audit §11)

Every new or rewritten engine must satisfy:
1. **JSON-driven config** — no hardcoded gameplay numbers; use `formula_engine.py` for computed values.
2. **Deterministic given a seed** — `(seed, tick_index, state) → state'` must be reproducible.
3. **Structured tick-result** — every engine call returns:
   ```python
   {
     'state_delta': {...},        # Diff to apply to state
     'kpis': {...},               # KPI values for display
     'events': [...],             # Discrete events
     'narrative': str,            # Round narrative copy
     'ui_hints': {                # Hints for renderer
       'flash': [str],            # KPI keys to flash
       'chart_focus': str,        # Which chart to highlight
       'show': [str],             # Which optional widgets to render
     }
   }
   ```
4. **Composable, not coupled** — engines never call each other directly. A new `engines/orchestrator.py` sequences them per game type.

### CCA-2: Feature Flag Discipline

| Change type | Flag mechanism |
|---|---|
| New engine | Per-game JSON: `engines: ["revenue_v1"]` or absence |
| Scoring formula change | `score_v2_enabled: bool` in org config; shadow scoring writes both `score_v1` and `score_v2` to player profile |
| New worksheet type | Type appears in TYPE_MAP only; old games unaffected |
| Renderer widget | `ui_hints.show: ["FinancialStatementsTab"]` in game JSON; renderer renders only what's declared |
| Modules composite score | `module.score_version: 2` in module JSON; v1 modules use `percent_complete` only |

### CCA-3: Snapshot Regression Suite (must exist before P1)

Before P1 begins, capture end-of-game KPI snapshots for these games as the regression baseline:
- `cfo-quarterly-close.json`
- `lemonade-empire-enhanced.json`
- `founders-gambit.json`
- `series-a-founders-journey.json`
- `project-management-mastery.json`
- `the-startup-decision.json`
- `climate-champions.json`
- `city-mayor.json`

Snapshot file: `backend/tests/snapshots/<game_id>_v1.json` containing final dimension_scores, kpis, total_score, completion_rate. P1 changes must keep these stable for any game that doesn't opt into `engines: ["finance_v2"]`.

### CCA-4: Shadow Scoring Window

When P0 ships the new scoring blend, the API returns BOTH `score_v1` and `score_v2` in the run report for **2 weeks minimum**. Frontend renders v1 with a "📊 New scoring coming Aug 1" badge showing v2 in a tooltip. After 2 weeks of reviewing leaderboard reorders, flip default. Keep v1 readable for ≥6 months for cohort comparability.

### CCA-5: i18n Discipline

Every new user-facing string lands in `frontend-react/src/locales/en.json` and `hi.json` simultaneously. No hardcoded English strings in JSX.

### CCA-6: Org Theming Discipline

Every new widget reads CSS vars from `OrgContext`. No hardcoded colors. New CSS files live in `frontend-react/src/styles/sim-widgets/`.

### CCA-7: Mobile-First Discipline

Every new widget has `compact` and `expanded` modes. Compact mode renders ≤320px wide. Expanded mode renders ≤1280px. Switch breakpoint: 768px.

---

## Phase-by-Phase Plan

Each phase has: theme, deliverables, UI/UX changes (in-phase vs deferred), exit criteria, dependencies. Estimated calendar is for a 2-backend + 1-frontend team.

---

### Phase P0 — Stabilize & Score Honesty (3 weeks)

**Theme:** Make the score honest before adding capability. Replace ~90% authored scoring with a 50/50 blend. Surface confidence intervals. Wire dormant behavioral signals.

**Backend deliverables:**
1. Wire `analyze_session_behavior()` output into `_compute_rounds_dimension_scores`, `_compute_story_dimension_scores`, `_compute_strategy_dimension_scores` in `backend/app.py`.
2. Replace fixed tag-bonus formulas with: `score = 0.5·clip(authored, 0..100) + 0.5·clip(behavioral, 0..100)`.
3. Add bootstrap CI computation in `backend/engines/dimension_utils.py::compute_dimension_ci()` (B=1000, alpha=0.10).
4. Per-game-type Z-score normalization before leaderboard write (`_save_strategy_leaderboard`, `api_skill_leaderboard`).
5. Infer `risk_level` from delta volatility when designer didn't tag (in `dimension_utils`).
6. Bulk-edit script: strip `delayed_gratification` skill_tags from timed_challenge games; add `adaptability` instead. Run `validate_all_games.py` after.
7. Add reflection-input scoring channel: when `ReflectionPrompt` submits, run LLM grade → emit `dim_signal` → blend into score.
8. Change leaderboard ordering to use CI lower bound, not point estimate (`leaderboard_rank = ci_low`).

**M-track deliverables (run in parallel):**
- **M1:** Modules composite score endpoint (`GET /api/modules/<id>/report-v2`) emitting `quiz_avg, rubric_avg, reflection_depth, anchored_game_dim_avg, time_on_task` + per-dim delta.
- **M2:** LLM-graded worksheets (textarea-heavy types: `reflection`, `pitch_builder`, `customer_profile`, `idea_scorecard`). Cache by content hash. Persist in `progress["rubrics"]`.
- **M5:** Add `lesson.quiz.bank[]` schema with `difficulty + skill_tags`. Engine selects via simple Rasch theta on retake. Backward compat: `lesson.quiz.questions` still works.
- **M6:** Wire `ContentModerator.moderate_text()` to `add_field_mission_entry`; block on toxicity/PII; flag borderline for teacher review.

**UI/UX in P0 (must ship together):**
- `PostGameInsights.jsx`: methodology banner ("📊 Score now reflects how you played, not just what you chose"); CI band visualization on each dimension bar (lower line = ci_low, upper line = ci_high, point = mean).
- `MentoScoreBreakdown.jsx`: reconcile taxonomy with PostGameInsights — pick one canonical 14-dim set OR document the two as separate views with explanation tooltips.
- `LeaderboardPage.jsx`: rank tooltip explaining "Ranked by lower bound of confidence interval (we're conservative when uncertain)."
- `ReflectionPrompt.jsx`: capture rationale → POST to `/api/run/<id>/reflection` → score-channel feedback toast.
- New worksheet result panel `frontend-react/src/components/module/WorksheetRubricResult.jsx`: shows {score 0–100, strengths[], improvements[], dim_signals}.
- `ModuleReportPage.jsx`: render new composite (5 channels with mini-bars), per-dim trajectory mini-chart, "What changed" diff vs v1.

**UI/UX deferred to later phases:** All sim widgets (P3), parent module tab (M9 in T2), live-class (M10 in T4).

**Exit criteria:**
- Test-retest variance per replay drops > 30% on a 50-run benchmark (run `lemonade_empire_v1` 50 times with the same fixed seed; v1 vs v2 variance).
- Leaderboard reorders post-flip (visible in admin analytics).
- All 12 timed_challenge games pass `validate_all_games.py` after the bulk edit.
- Snapshot regression suite (CCA-3) passes — no game scores shift > 5 percentile points unless explicitly opted into v2.

**Detailed plan:** `docs/superpowers/plans/2026-05-02-p0-stabilize-and-score-honesty.md` (write next; bite-sized TDD tasks).

---

### Phase P1 — Financial Core (8 weeks)

**Theme:** Build the financial engines that don't exist today. Wire them into one pilot game (cfo-quarterly-close-v2) before broad adoption.

**Backend deliverables:**
1. `backend/engines/revenue_engine.py` (NEW, 300–400 LOC): ARR/MRR, expansion, churn, cohort retention, NRR; segment-aware.
2. `backend/engines/cogs_engine.py` (NEW, 250–350 LOC): per-unit cost, yield loss, capacity utilization, supplier discount tiers.
3. `backend/engines/working_capital_engine.py` (NEW, 300–400 LOC): DSO/DPO/inventory days, cash cycle.
4. `backend/engines/finance_engine.py` (REWRITE, 600–800 LOC): real P&L, double-entry BS, indirect cash flow, tax, debt schedule. Keeps existing `compute_cap_table()` API for back-compat.
5. `backend/engines/orchestrator.py` (NEW, 200–300 LOC): sequences engines per game per CCA-1. Replaces ad-hoc tick wiring.
6. `logistics_engine.py` → COGS bridge: convert orphan `logistics_engine.py` into a wired adapter that propagates inventory into COGS and cash flow.
7. New game: `backend/games/cfo-quarterly-close-v2.json` declaring `engines: ["finance_v2", "revenue_v1", "cogs_v1", "working_capital_v1"]`.

**M-track deliverables:**
- **M3:** Adaptive sequencing (`progression: 'adaptive'` mode in module schema). Reuses `adaptive_engine.py` + `coaching_bandit.py`.
- **M4:** Spaced review wired to module lessons (1-min micro-quiz; surfaced on HomePage banner).

**UI/UX in P1 (minimal):**
- `cfo-quarterly-close-v2` game uses existing `SimulationRenderer` — engines emit standard tick-result, renderer ignores fields it doesn't know about. **No new widgets needed in P1.**
- `HomePage.jsx`: spaced-review banner now also points to module-lesson reviews (currently game-only).
- `ModulesPage.jsx`: badge `🧭 Adaptive` next to modules with adaptive progression.

**Exit criteria:**
- A 6-quarter run of `cfo-quarterly-close-v2` produces P&L, BS, CF that reconcile to within 1¢.
- Runway (months) is computed and accurate.
- Snapshot regression suite (CCA-3) still passes for all v1 games.
- `engines/orchestrator.py` is the single entry point for tick processing in v2 games.

**Detailed plan:** Written when P0 completes (decisions made in P0 about CI computation and tick-result schema feed P1).

---

### Phase P2 — Market Dynamics (8 weeks)

**Theme:** Replace probabilistic competitor moves with state-aware AI. Wire churn, demand forecast, product lifecycle.

**Backend deliverables:**
1. `backend/engines/competitive_ai_engine.py` (NEW, 400–500 LOC): state-aware decisions, memory, delayed reactions, coalition behavior.
2. `backend/engines/churn_engine.py` (NEW, 150–200 LOC): segment survival curves, quality/NPS/price modifiers.
3. `backend/engines/demand_forecast_engine.py` (NEW, 200–300 LOC): exponential smoothing + seasonal index + CI bands.
4. `backend/engines/product_lifecycle_engine.py` (NEW, 300–400 LOC): R&D→beta→GA pipeline, cannibalization, decline curves.
5. Per-segment elasticity in `market_engine.py`: replace single global elasticity with `{SMB: -2.0, Mid: -1.4, Enterprise: -0.8}` (configurable per game).

**M-track deliverables:**
- **M7:** Cross-module skill trajectory aggregation. Surfaced in `SkillPortfolioPage.jsx` as "Module skill graph."
- **M8:** Teacher pacing dashboard. New endpoint `/api/cohorts/<id>/modules/<id>/pacing`. New page `TeacherCohortPacingPage.jsx`.
- **M11:** Worksheet vocabulary expansion — 7 new types (drag_rank, decision_matrix, kanban, mind_map, voice_diary, peer_review, video_reflection). ~150 LOC React + JSON schema each.

**UI/UX in P2 (minimal — widgets land in P3):**
- `SkillPortfolioPage.jsx`: new "Module Skill Graph" tab.
- `TeacherCohortPacingPage.jsx`: NEW page with cohort progress curve, at-risk list, suggested intervention CTAs.
- 7 new worksheet renderers in `frontend-react/src/components/module/worksheets/`.

**UI/UX freeze gate at end of P2:** The `ui_hints` schema for all P3 widgets must be frozen by end of P2. Storybook stubs with synthetic tick-results must exist before P3 starts.

**Exit criteria:**
- AI competitors provably react to player moves (compare 50 runs with vs. without competitive AI; market share variance > 30%).
- ARR equation is decomposable: `ARR_t = ARR_{t-1} + new + expansion - churn`, all four computable.
- Forecast endpoint returns `{point, ci_low, ci_high}`.
- All 7 new worksheet types render in Storybook.

**Detailed plan:** Written when P1 completes.

---

### Phase P3 — Renderer Expansion (6 weeks, parallel with P2 final 4 weeks)

**Theme:** Eight new sim widgets driven by `tick_result.ui_hints.show`. Single registry, mobile-first, theme-aware.

**Frontend deliverables:**

| # | Widget | File | Reads from |
|---|---|---|---|
| 1 | FinancialStatementsTab | `frontend-react/src/components/game/sim/FinancialStatementsTab.jsx` | `kpis.financials.{pnl, bs, cf}` |
| 2 | MarketShareDashboard | `frontend-react/src/components/game/sim/MarketShareDashboard.jsx` | `kpis.market_share_history` |
| 3 | DemandForecastPanel | `frontend-react/src/components/game/sim/DemandForecastPanel.jsx` | `kpis.forecast.{point, ci_low, ci_high}` |
| 4 | ProductLifecycleBoard | `frontend-react/src/components/game/sim/ProductLifecycleBoard.jsx` | `kpis.products[]` |
| 5 | CompetitorIntelTimeline | `frontend-react/src/components/game/sim/CompetitorIntelTimeline.jsx` | `events` filtered by `source=competitor` |
| 6 | WorkingCapitalDial | `frontend-react/src/components/game/sim/WorkingCapitalDial.jsx` | `kpis.working_capital` |
| 7 | ScenarioTornado | `frontend-react/src/components/game/sim/ScenarioTornado.jsx` | `kpis.scenario_sensitivity` |
| 8 | ExitReadinessScorecard | `frontend-react/src/components/game/sim/ExitReadinessScorecard.jsx` | `kpis.exit_readiness` |

**Plus infrastructure:**
- `frontend-react/src/components/game/sim/SimWidgetRegistry.jsx` (NEW): maps widget ID → component, used by `SimulationRenderer` to render `ui_hints.show: [...]`.
- `frontend-react/src/components/game/sim/SimWidget.stories.jsx` (NEW): Storybook entries with synthetic tick-results for each widget.
- `frontend-react/src/styles/sim-widgets/` (NEW): per-widget CSS files using `OrgContext` CSS vars.

**Backend touch:**
- `backend/games/cfo-quarterly-close-v2.json`: add `ui_hints.show: ["FinancialStatementsTab", "WorkingCapitalDial", "MarketShareDashboard"]`.
- New game: `backend/games/capsim-foundation-v1.json` declaring all 8 widgets.

**Exit criteria:**
- Each widget renders purely from tick-result; no extra API calls.
- Storybook coverage 100%: each widget has compact + expanded + dark-mode + 2 example data states.
- All widgets pass mobile audit at 320, 768, 1024, 1280px.
- `capsim-foundation-v1` plays end-to-end with all 8 widgets active.

**Detailed plan:** Written when P2 completes (depends on `ui_hints` schema frozen at end of P2).

---

### Phase P4 — Differentiation Engines (6 weeks)

**Theme:** Tier 3 capabilities: scenario, exit, M&A, ESG, multi-region tax/FX.

**Backend deliverables:**
1. `backend/engines/scenario_engine.py` (NEW, 250–350 LOC): base/up/down + sensitivity tornado; Monte-Carlo banding.
2. `backend/engines/exit_engine.py` (NEW, 200–300 LOC): IPO, strategic sale, terminal value, exit-readiness scorecard.
3. `backend/engines/ma_engine.py` (NEW, 250–350 LOC): target valuation, synergy, integration cost & risk.
4. `backend/engines/esg_engine.py` (NEW, 150–250 LOC): carbon/labor/privacy; ESG rating impacts cost-of-capital.
5. `backend/engines/org_engine.py` (EXTEND, +200 LOC): turnover, ramp, sales-force quota & comp, retention bonus.
6. `backend/engines/finance_engine.py` (EXTEND, +150 LOC): statutory rate, NOL, FX, tariffs.

**M-track deliverables:**
- **M9:** Parent module visibility — `ParentDashboardPage.jsx` adds Modules tab; LLM-generated weekly family discussion prompts.
- **M10:** Live-class mode (lesson type `live_session`). Built on `multiplayer_engine` + WebSocket layer.
- **M12:** Module certificate pipeline (PDF generation via existing `certificate.py` + ReportLab; public verification page).

**UI/UX in P4:**
- New widgets ScenarioTornado and ExitReadinessScorecard activate in games.
- `ParentDashboardPage.jsx`: Modules tab.
- New `LiveClassroomPage.jsx`: shared timer, presence list, teacher-controlled advance.
- `ModuleCompletePage.jsx`: certificate download CTA + share link.
- New page `CertificateVerifyPage.jsx`: public, anti-fake hash check.

**Exit criteria:**
- End-to-end Capsim-equivalent game (`capsim-capstone-v1`) playable with 6-firm AI competition stable.
- Live-class session supports ≥30 concurrent students with shared timer drift < 500ms.
- Certificate PDF generates in < 3s; verification page renders in < 1s.

**Detailed plan:** Written when P3 completes.

---

### Phase P5 — Validation (6 weeks)

**Theme:** Earn the credibility claim. Pilot study, CFA/IRT, fairness audit. Close creativity & empathy content gaps.

**Deliverables:**
1. Pilot validity study, n≈150 students, 4 schools (`docs/research/pilot_2026Q3.md`).
2. CFA / IRT analysis after pilot (`scripts/psychometric_validation.py`).
3. Fairness audit by age, language, SES (`scripts/fairness_audit.py`).
4. **M13:** Accessibility track — TTS variant + dyslexia mode + alt-text required in module schema.
5. Content gap closure: build to ≥20 creativity games, ≥30 empathy games, ≥30 genuine delayed_gratification games.
6. Publish factor loadings; if ICC > 0.7, public methodology page goes live.

**UI/UX in P5:**
- `MethodologyPage.jsx`: replace current copy with audited + cited methodology.
- Settings: dyslexia-mode toggle, audio-first toggle.
- `ModulesPage.jsx`: 🔊 Audio variant badge on accessibility-ready modules.

**Exit criteria:**
- ICC > 0.70 across replays (test-retest reliability).
- Demographic gap < 1 SD across age, language, SES segments.
- ≥20 creativity / ≥30 empathy genuine-practice games shipped.
- Methodology page passes external academic review (≥1 reviewer).

**Detailed plan:** Written when P4 completes; pilot recruitment starts in P3.

---

## Module Tracks (Cross-Phase)

The 13 module tracks (M1–M13) are scheduled into phases above. Recap by phase:

| Phase | Tracks |
|---|---|
| P0 | M1 score depth, M2 rubric grading, M5 IRT item bank, M6 moderation |
| P1 | M3 adaptive sequencing, M4 spaced review |
| P2 | M7 cross-module skill, M8 teacher pacing, M11 worksheet vocab |
| P4 | M9 parent module, M10 live-class, M12 certificate |
| P5 | M13 accessibility |

Total module work: ~50 engineer-days, distributed across phases.

---

## Critical Path & Dependencies

```
P0 (3w) ──→ P1 (8w) ──→ P2 (8w) ──→ P4 (6w) ──→ P5 (6w)
                          └─→ P3 (6w, parallel from P2 wk 4) ──┘
```

**Hard dependencies:**
- P3 cannot start until tick-result schema is frozen at end of P2.
- P4 cannot start until P3 widgets are integrated into the renderer.
- P5 pilot recruitment starts during P3 so data is ready post-P4.
- M3 adaptive needs P0 dimension scoring stable.
- M9 parent module needs M1 composite report.
- M10 live-class needs M3 adaptive + multiplayer_engine WebSocket layer (build during P3).

**No-skip rule:** P0 cannot be skipped. Every later phase compounds on its scoring honesty. Skipping P0 means every claim downstream is undermined.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| Finance v2 rewrite breaks pilot game | Low (orphan engine) | Medium | Build alongside v1; opt-in per game JSON | Backend lead |
| P0 scoring blend changes leaderboard ordering, frustrates students | High | High | 2-week shadow scoring; both v1+v2 in API; methodology banner with explainer; honor v1 historical leaderboards | Frontend + Comms |
| Competitive AI proves too strong/weak | Medium | Medium | Difficulty knobs in JSON; calibrate via `automated_playtesting` before release | Backend lead |
| LLM grading cost balloons (M2, reflection-input scoring) | Medium | Medium | Cache by content hash (already standard pattern); per-org budget caps; downgrade to local model for low-stakes grading | Backend lead |
| Pilot validity study shows weak ICC (<0.5) | Medium | Low | Acceptable outcome; publish CIs honestly; iterate scoring blend; do not over-claim | Research lead |
| Rendering scope creeps; widgets diverge from tick-result schema | Medium | High | `SimWidgetRegistry` enforces contract; Storybook with synthetic tick-results gates merge | Frontend lead |
| Module composite (M1) angers teachers comparing v1→v2 percentages | Medium | Low | Show both for 2 weeks; "What changed" panel on report card | M-track lead |
| Live-class WebSocket layer destabilizes existing endpoints | Medium | High | Separate WebSocket service on different port; no shared connection pool with REST | Infra |
| ContentModerator (M6) blocks legitimate field-mission entries | Medium | Medium | "Borderline" path goes to teacher review, not auto-block; teacher can override | M-track lead |
| Bulk JSON edit (P0 step 6) corrupts a game | Low | High | Run `validate_all_games.py` after every batch; commit-by-commit; keep `.bak` files | Backend |

---

## Success Metrics (mirror audit §14)

| Metric | Today | Target after P5 |
|---|---|---|
| Capability matrix (Y / Partial / N) | 7 / 10 / 6 | 20 / 3 / 0 |
| Genuine soft-skill practice (mean across 8 dims) | 31% | ≥ 60% |
| Behavioral weight in dimension score | ≈ 10% | ≈ 50% |
| Test-retest ICC (pilot) | Not measured | ≥ 0.70 |
| Demographic fairness gap (SD) | Not measured | < 1.0 |
| Engine LOC (mechanics layer) | ≈ 6,800 | ≈ 11,000 |
| Generic engines (vs. game-specific) | Mostly generic, ad-hoc wiring | 100% generic with formal contract via orchestrator |
| Sim widgets in renderer | 5 | 13 |
| Games with reflection prompts | ≈ 18 | ≥ 80 |
| Modules with composite v2 score | 0 | 7 (all live) |

---

## UI/UX Summary — When Each Surface Changes

This is the consolidated answer to "what UI/UX changes when?":

| Surface | Phase | Change |
|---|---|---|
| `PostGameInsights.jsx` | P0 | Methodology banner, CI bands |
| `MentoScoreBreakdown.jsx` | P0 | Reconcile taxonomy with PostGameInsights |
| `LeaderboardPage.jsx` | P0 | Rank tooltip, "ranked by CI lower bound" |
| `ReflectionPrompt.jsx` | P0 | Capture rationale → score channel |
| New: `WorksheetRubricResult.jsx` | P0 | Rubric panel for textarea worksheets |
| `ModuleReportPage.jsx` | P0 | Composite v2 (5 channels) + per-dim trajectory |
| `HomePage.jsx` | P1 | Spaced-review banner extends to module lessons |
| `ModulesPage.jsx` | P1, P5 | 🧭 Adaptive badge (P1), 🔊 Audio badge (P5) |
| `SkillPortfolioPage.jsx` | P2 | Module Skill Graph tab |
| New: `TeacherCohortPacingPage.jsx` | P2 | Cohort progress curves, at-risk list |
| 7 new worksheet renderers | P2 | drag_rank, decision_matrix, kanban, mind_map, voice_diary, peer_review, video_reflection |
| 8 new sim widgets | P3 | FinancialStatementsTab, MarketShareDashboard, DemandForecastPanel, ProductLifecycleBoard, CompetitorIntelTimeline, WorkingCapitalDial, ScenarioTornado, ExitReadinessScorecard |
| `SimulationRenderer.jsx` | P3 | Wire widget registry; render from `ui_hints.show` |
| `ParentDashboardPage.jsx` | P4 | Modules tab |
| New: `LiveClassroomPage.jsx` | P4 | Shared timer, presence, teacher-controlled advance |
| `ModuleCompletePage.jsx` | P4 | Certificate download + share |
| New: `CertificateVerifyPage.jsx` | P4 | Public verification with hash check |
| `MethodologyPage.jsx` | P5 | Audited methodology copy |
| `SettingsPage.jsx` | P5 | Dyslexia mode, audio-first toggle |

**Critical insight:** Only P0, P3, P4 require coordinated frontend pushes. P1, P2, P5 are mostly backend with small UI deltas. The frontend engineer is therefore the bottleneck in P3 (6 dedicated weeks of widget work) and free for other work in P1, P2, P5.

---

## Plan of Plans

The master plan above is structural. Each phase needs a detailed implementation plan with bite-sized TDD tasks before that phase executes. Detailed plans are written **just-in-time** because decisions made in earlier phases reshape later ones (e.g., the exact CI computation chosen in P0 changes the tick-result schema used in P1+).

| Phase | Detailed plan path | Status | Written when |
|---|---|---|---|
| P0 | `docs/superpowers/plans/2026-05-02-p0-stabilize-and-score-honesty.md` | **Drafted alongside this master plan** | Now |
| P1 | `docs/superpowers/plans/<date>-p1-financial-core.md` | TBD | Last week of P0 |
| P2 | `docs/superpowers/plans/<date>-p2-market-dynamics.md` | TBD | Last week of P1 |
| P3 | `docs/superpowers/plans/<date>-p3-sim-renderer-widgets.md` | TBD | Mid-P2 (in parallel) |
| P4 | `docs/superpowers/plans/<date>-p4-differentiation.md` | TBD | Last week of P3 |
| P5 | `docs/superpowers/plans/<date>-p5-validation.md` | TBD | Last week of P4 |

---

## Open Questions to Resolve Before Starting P0

1. **MentoScoreBreakdown vs PostGameInsights taxonomy:** which is canonical? Must decide before P0 step 1 ships, otherwise the methodology banner will be inconsistent. **Recommendation:** PostGameInsights is canonical (richer, mapped to NEP/CASEL/Goleman). Refactor MentoScoreBreakdown in P0 to consume the same dimension data, but render a 7-aggregate "executive summary" view derived from the 14 dims.

2. **CI alpha:** 0.10 (90% CI) vs 0.05 (95% CI)? **Recommendation:** 0.10 — leaderboards reorder less violently and student variance is large.

3. **Reflection grading model:** Claude Sonnet 4.6 (current) or local fallback? **Recommendation:** Sonnet for production; local distillation later if cost spikes.

4. **Snapshot suite size:** 8 games (listed in CCA-3) or all 96? **Recommendation:** 8 representative games for CI; full sweep nightly via cron.

5. **Org-level rollout vs global rollout for v2 scoring:** flip per-org or globally after shadow period? **Recommendation:** per-org, default off; admins flip per cohort to control parent communications.

These should be resolved during the first 2 days of P0 before code starts.

---

**End of master plan.**
