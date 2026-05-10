# HBR + CapSim Parity Uplift — 5 Multi-Tab Executive Simulations

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the 5 multi-tab framework simulations to **HBR Business Publishing parity** in shape and depth, with selective **CapSim-tier features** (real audited financial statements that recompute every round, reactive competitor AI, multi-period scorecard) — at the 35–45 minute runtime envelope these games occupy.

**Architecture:** The heavy lifting is already done. `backend/engines/finance_engine.py` (562L) computes real P&L / balance sheet / cash flow. `engines/market_engine.py`, `org_engine.py`, `corporate_board_engine.py`, `project_management_engine.py`, `intrapreneur_engine.py`, `compliance_engine.py`, `crisis_engine.py`, `decision_engine.py`, `stochastic_engine.py`, `market_actors_engine.py` (140-282L each) all expose `build_*_payload(state, game)` entry points. The gap is **JSON authorship**: the existing 5 game JSONs declare subsystem _config_ blocks but their per-round `choices.exec_effects` rarely apply real numerical deltas to the finance state, so the multi-tab UI shows static scaffolding instead of live numbers.

**Tech Stack:** Python 3.11+, Flask, pytest, existing `engines/*.py`, existing `backend/core/rounds.py` for choice processing.

**Parent plan:** `2026-05-02-mentoapp-roadmap-master.md` (this is a P5 sim-depth deliverable hoisted to be executed alongside P0).

---

## Honest scope framing

**What HBR sims look like (target):** 30–60 min runtime; 4–6 rounds; **5–8 sub-decisions per round** (sliders/dials, not categorical A/B/C); finance/operations state recomputes between rounds; competitor AI reacts; final weighted scorecard with benchmark percentile; debrief covers each decision with expert commentary. Examples: *Project Management Simulation: Scope, Resources, Schedule v3* (Kasser); *Finance Simulation: Capital Budgeting* (Ruback); *Negotiation Simulation: The Office Move* (Sebenius); *Everest* (leadership).

**What CapSim is (different category — won't fully reach):** 8 rounds × 100+ decision variables × 5 parallel competing firm AIs × full audited statements × 6–10 hour runtime over a semester. We can borrow CapSim _features_ (real audited financial statements every round, multi-firm competitor model, full Capstone Courier-style industry report) without trying to match its scope. **A 35-min sim will never be a CapSim, by design.**

**What we're committing to:**
- ✅ Match HBR shape and depth fully — sub-decisions per round, real-number recompute, scorecard, debrief
- ✅ Borrow CapSim's audited financial statements feature (P&L + Balance Sheet + Cash Flow visible each round)
- ✅ Borrow CapSim's reactive multi-firm competitor model (3 firms, not 5, scaled for runtime)
- ✅ Borrow CapSim's industry report ("Atlas Industry Pulse") shown between rounds
- ❌ Do NOT match CapSim's 8-round / 100-var / 10-hour runtime — a separate "Capstone Mode" sub-product would be required

---

## What's already in place vs gap

### Engine layer (READY — minimal work needed)
| Engine | Lines | Real compute | Gap |
|---|---|---|---|
| finance_engine | 562 | `compute_pnl`, `compute_balance_sheet`, `compute_cash_flow_statement` (lines 175, 235, 299), `_synth_pnl_from_state` fallback | Needs per-round delta application + multi-period buffer |
| market_engine | 254 | TAM/SAM/SOM, funnel, channels | Needs reactive competitor moves |
| org_engine | 218 | Span of control, headcount, culture | Done |
| corporate_board_engine | 207 | Member alignment, vote tally | Done |
| project_management_engine | 282 | Tasks, resources, RAID, Gantt | Done |
| intrapreneur_engine | 261 | Sponsor support, political capital | Done |
| compliance_engine | 141 | Risk register, audit findings | Done |
| crisis_engine | 160 | Severity, time pressure | Done |
| decision_engine | 169 | RCM-style decision quality | Done |
| stochastic_engine | 266 | Calibrated RNG, Monte Carlo | Done |
| market_actors_engine | 242 | Multi-actor sim | Needs to be wired into competitors loop |

**Engines are 80% ready.** Most work is in JSON authorship + a few engine extensions.

### JSON authorship layer (GAP — 70% of effort)

Per game, current state and gap:

#### `cfo_quarterly_close` (40 min, 6 rounds)
- ✅ Real finance primitives (`starting_cash: $42M`, ARR, burn, GM%, CAC, churn, NRR, cap table)
- ❌ Per-round choices don't apply deltas to finance state — only `decision_record` and `board_alignment`
- ❌ Each round has 3 choices with no sub-decisions
- ❌ No P&L/BS/CF visible to player between rounds
- ❌ No competitor pricing pressure round-to-round

**HBR analogue:** *Finance Simulation: Capital Budgeting* (Ruback) + *Quarterly Close: Strategic Decision Making*.

#### `series_a_founders_journey` (45 min, 6 rounds)
- ✅ 11 subsystems: TAM/SAM/SOM, board, market funnel, finance, org, crisis
- ❌ Choices don't drive finance/market/org deltas — same issue
- ❌ 4 choices per round but they're narrative, not decision-variable

**HBR analogue:** *Strategic Management* family of HBR sims; closest: *Founder–CEO Decision Sim*.

#### `project_management_mastery` (35 min, 6 rounds)
- ✅ Has real PM state (`tasks`, `resources`, `raid`, sprint length, target_end_day) — closest to HBR's PM Sim v3
- ❌ Choices apply `project_advance_day` and `project_task` but lack scope/resources/schedule **sliders** that HBR PM sim has
- ❌ No earned value (EV/PV/AC) reporting

**HBR analogue:** *Project Management Simulation: Scope, Resources, Schedule v3* (Kasser, Lapré). **This is the closest HBR fit — easiest first uplift.**

#### `new_bu_launch` (35 min, 6 rounds)
- ✅ Intrapreneur + finance + stakeholders + frameworks
- ❌ Same gap: narrative choices, not decision-variable choices

**HBR analogue:** *Innovation: Bridging the Idea–Execution Gap* + *New Venture Strategy*.

#### `skunkworks_atlas_corp` (35 min, 6 rounds)
- ✅ Sponsor + compliance + intrapreneur
- ❌ Same gap

**HBR analogue:** No exact HBR sim. Closest: HBS *3M Optical Systems* case-as-sim. We can author original.

---

## Architecture for the uplift

Each round transitions from "narrative choice" to **"decision panel"** — a multi-control sub-decision UI that maps to engine deltas:

```
ROUND N:
  scenario (existing)
  decision_panel:                       ← NEW
    controls:
      - pricing_lever:   slider 0–100 (% over cost)
      - marketing_spend: slider $0–$5M
      - hiring_pace:     dial 0–10 hires
      - r_and_d_alloc:   slider 0–40 % of budget
    expert_pick: {pricing: 12, marketing: 2.5M, hiring: 5, rd: 25}
    deltas_function: "apply_round_n_deltas"   ← engine-side
  competitor_moves:                     ← NEW (reactive AI)
    - reads player's decision_panel
    - 3 competitor firms make their own moves
    - mutates market_share, price_pressure
  industry_report:                      ← NEW (post-round)
    - "Atlas Industry Pulse Q{N}"
    - shows: market share, ROI, NPS, segment growth
  expert_debrief:                       ← NEW (each round)
    - 100-200 word commentary
    - "Why expert_pick was the strong move"
END:
  scorecard (5 weighted dimensions, percentile bands)
  meta_debrief (existing — already in JSON)
```

This shape is **HBR-equivalent** at the round level. Multi-period audited statements + reactive competitors are the **CapSim-borrow**.

### New backend additions

| Path | Action | Purpose |
|---|---|---|
| `backend/engines/decision_panel_engine.py` | NEW (~200L) | Apply slider/dial deltas to state per round; validate against ranges; compute drift from expert_pick |
| `backend/engines/industry_report_engine.py` | NEW (~150L) | Render between-round industry pulse: market share, KPIs, competitor positioning |
| `backend/engines/competitor_ai_engine.py` | NEW (~250L) | 3 reactive firm AIs (each has strategy persona); mutate market state in response to player |
| `backend/engines/scorecard_engine.py` | NEW (~150L) | Final weighted scorecard with benchmark percentile (uses `industry_benchmarks.json`) |
| `backend/engines/finance_engine.py` | EXTEND (+~80L) | Add `roll_forward_period(state, deltas)` for per-round audited statement update |
| `backend/engines/project_management_engine.py` | EXTEND (+~60L) | Add EV/PV/AC earned value reporting |
| `backend/core/rounds.py` | MODIFY | Process `decision_panel.controls` → call `apply_round_deltas` → call `competitor_ai.tick()` → return updated payload with `industry_report` block |

### Frontend additions

| Path | Action |
|---|---|
| `frontend-react/src/components/game/exec/DecisionPanel.jsx` | NEW — sliders/dials/inputs per round |
| `frontend-react/src/components/game/exec/IndustryReport.jsx` | NEW — between-round Atlas Industry Pulse modal |
| `frontend-react/src/components/game/exec/CompetitorBoard.jsx` | NEW — shows 3 competitor firms' moves |
| `frontend-react/src/components/game/exec/Scorecard.jsx` | NEW — final weighted scorecard with bands |
| `frontend-react/src/components/game/exec/ExpertDebrief.jsx` | NEW — per-round 100–200 word commentary |
| `frontend-react/src/components/game/exec/ExecutivePanel.jsx` | MODIFY — render new tabs (Decision, Industry, Competitors, Scorecard) |

---

## Phased rollout

**Phase A — Engine plumbing (5 days):**
- Build `decision_panel_engine`, `industry_report_engine`, `competitor_ai_engine`, `scorecard_engine`
- Extend `finance_engine.roll_forward_period`
- Extend `project_management_engine` for EV/PV/AC
- Wire `core/rounds.py` to call new engines

**Phase B — Frontend tabs (3 days):**
- Build `DecisionPanel`, `IndustryReport`, `CompetitorBoard`, `Scorecard`, `ExpertDebrief`
- Wire into `ExecutivePanel`

**Phase C — Pilot game (3 days): `project_management_mastery`**
- Closest HBR analogue → easiest authoring lift
- 6 rounds × 5 sub-decisions × earned-value reporting × 3 competitor firms × scorecard
- This becomes the proof-of-pattern reference

**Phase D — Replicate to other 4 games (8 days, 2 days each):**
- `cfo_quarterly_close` — finance-heavy decision panels (pricing, working capital, R&D allocation)
- `series_a_founders_journey` — fundraise, team, market, board
- `new_bu_launch` — intrapreneur sliders (sponsor capital, runway, hiring)
- `skunkworks_atlas_corp` — innovation R&D allocation

**Phase E — Acceptance (2 days):**
- Playtest each game end-to-end
- Verify scorecard bands map to industry benchmarks
- Snapshot test for behavior regression
- Deploy to production

**Total: 21 working days for 1 backend + 1 frontend developer.**

---

## Sequencing decision

This plan is a **separate workstream from P0** (scoring honesty). They share no critical-path files — P0 modifies `_compute_*_dimension_scores` and `dimension_utils.py`; uplift modifies engines + JSONs + new frontend tabs.

**Recommendation:** Run them in parallel. P0 finishes in ~5 more days (Tasks 5–23, mostly mechanical wiring); uplift takes 21 days. Total elapsed: ~21 days with 2-track work.

If single-track: do P0 first (5 days), then uplift (21 days). 26 days total.

---

## Self-review

- ✅ Spec coverage: all 5 games addressed; engine layer audited; gap quantified
- ✅ No placeholders: each phase has concrete file lists and durations
- ✅ Type consistency: `decision_panel.controls`, `apply_round_deltas`, `roll_forward_period` named consistently throughout
- ⚠️ Open question for user: confirm "HBR parity + CapSim-borrow" is the right scope target (not "full CapSim parity" which requires 5–10× the work for a different product class)
- ⚠️ Open question for user: parallel with P0, or serial (P0 first)?

---

## Execution handoff

Plan complete. Two options:

1. **Pilot-first** (recommended): I implement Phase A + B + C (pilot game = `project_management_mastery`) end-to-end as a proof-of-pattern, ship it, get user sign-off, then replicate to the other 4. Risk: low. Time-to-first-deployment: 11 days.

2. **All-in**: I implement all 5 phases sequentially. Risk: higher (no early validation). Time: 21 days.

Awaiting user confirmation.
