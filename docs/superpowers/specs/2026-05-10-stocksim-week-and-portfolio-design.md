# Stocksim Week-Format + Portfolio Modal — Design Spec

**Date:** 2026-05-10
**Scope:** `stock-market-simulator` game only. `stock-market-day-trader` (3-min sprint) unchanged.
**Goal:** Convert the 22-tick continuous simulator into a 5-day calendar week with weekend events and scheduled earnings, and add a standalone 4-tab Portfolio modal launched from the PersistentStrip.

---

## Section 1 — Calendar Week Structure

### Schedule

| Phase                | Duration             | What happens                                              |
|----------------------|----------------------|-----------------------------------------------------------|
| Mon–Fri trading      | 4 ticks/day × 8s     | Live trading. Mentor check-in fires at mid-week.          |
| End-of-day modal     | User-paced           | Recap: today's P&L, top winner/loser, day's headlines.    |
| Overnight gap        | Computed at advance  | Price drift between Day-N close and Day-N+1 open.         |
| Saturday news flash  | 10s overlay          | 1 macro headline + 1 stock-specific story.                |
| Sunday pre-market    | 10s overlay          | "Tomorrow's agenda" — what to watch on Monday morning.    |
| Markets-closed pause | 3s between days      | Visual beat to make the day boundary feel real.           |

Total session ≈ 5 minutes (≈2.7 min trading at 20 ticks × 8s + day transitions + weekend overlays). Existing `tick_count` in JSON is replaced by `Σ days[].ticks` (= 20 ticks for the default 5×4 week). Backwards-compat: if `calendar_mode` is absent, engine falls back to legacy continuous mode.

### Earnings Calendar

Each of the 8 stocks has 1 scheduled earnings on a specific weekday, configured per game in JSON:

```json
"earnings_schedule": {
  "TECHV":     { "day": "tue", "surprise": "+5%",  "headline": "TechVista beats Q2 guidance" },
  "BHARATBANK":{ "day": "wed", "surprise": "-3%",  "headline": "BharatBank misses on NPAs" },
  "...":       { "day": "...", "surprise": "...", "headline": "..." }
}
```

- Earnings are revealed in the EndOfDayModal at the close of the scheduled day (not mid-day intraday).
- Overnight drift carries the surprise into next day's opening price; the post-earnings level is what users see when Day-N+1's first tick lands.
- Pre-announced in the briefing's "STOCKS IN PLAY" cards (small `📅 Earnings: Tue` chip) and again in the Sunday pre-market overlay.

### Overnight Drift Formula

Applied between trailing tick of Day-N and leading tick of Day-N+1:

```
drift = base_noise + earnings_drift
base_noise     = N(μ=0, σ=0.005)              # ~±0.5%
earnings_drift = surprise * 0.6 if Day-N hosted that stock's earnings, else 0
```

Drift is server-authoritative (computed in `StockMarketEngine.advance_to_tick`) and persists to state so polling clients see consistent prices.

### Weekend Events

```json
"weekend_events": [
  {
    "after_day": "fri",
    "type": "saturday_news",
    "title": "Saturday Headlines",
    "items": [
      { "scope": "macro",       "text": "RBI keeps repo rate unchanged" },
      { "scope": "stock", "symbol": "GREENX", "text": "Govt approves new solar tariff" }
    ]
  },
  {
    "after_day": "fri",
    "type": "sunday_brief",
    "title": "Monday Agenda",
    "items": [
      { "scope": "macro", "text": "US Fed minutes due Tuesday — IT in focus" }
    ]
  }
]
```

The week-format game has only one weekend (post-Friday). Mon–Fri have no weekend events. Frontend renders these as full-bleed overlays between Friday EndOfDayModal and Sunday→Monday transition. After the user dismisses Sunday brief, the game ends and goes to recap (since the spec is a single Mon–Fri week).

### Backend Changes

**File: `backend/games/stock-market-simulator.json`**
- Add `minigame_config.stock_market_config.calendar_mode: "week"`.
- Add `days: [{ id, label, ticks, weekend }]` array (5 entries).
- Add `earnings_schedule: { SYMBOL: { day, surprise, headline } }` for all 8 stocks.
- Add `weekend_events: [...]` array.
- Existing fields (`stocks`, `briefing`, `tick_interval_seconds`, `event_deck`) preserved.

**File: stocksim engine module owning `advance_to_tick`** (exact path located during plan-writing — likely `backend/engines/stock_market_engine.py` or `backend/engines/stocksim/pricing.py`)
- New helper `apply_overnight_drift(state, sm_cfg, from_day_id, to_day_id)`.
- `advance_to_tick` checks if the new tick crosses a day boundary; if so, applies drift to per-symbol price state.
- New helper `current_day(state, sm_cfg)` returns the day metadata for the tick currently being served.

**File: `backend/app.py`** — `stocksim_state` endpoint
- Response gains `day: { id: "wed", label: "Wednesday", index: 2, of: 5 }` and `today_pnl: { ... }` (computed from trades since 00:00 of current day).
- `pending_earnings: [{ symbol, day, headline }]` listing remaining unrevealed earnings.

### Frontend Changes

**New files:**

| File | Purpose |
|------|---------|
| `stocksim/DayHeader.jsx` | Sticky chip above PersistentStrip: "📅 Wednesday — Day 3 of 5". Re-renders on `state.day` change. |
| `stocksim/EndOfDayModal.jsx` | Modal: today's P&L, top winner/loser, headlines, earnings reveal if applicable, "Continue to Thursday →" button. |
| `stocksim/WeekendInterlude.jsx` | Full-bleed overlay for Sat news flash + Sun pre-market brief. Auto-advance after 10s OR manual "Continue". |
| `stocksim/dayBoundaries.js` | Pure helper: given `days[]` and `currentTick`, returns array of tick indices where day boundaries occur (for chart separator rendering). |

**Modified files:**

| File | Change |
|------|--------|
| `stocksim/MarketBriefing.jsx` | Show small `📅 Earnings: Tue` chip on stock cards that have earnings during the week. |
| `StockMarketGame.jsx` | Mount `<DayHeader>` above PersistentStrip. Phase machine gains `'eod'` (end-of-day modal) and `'weekend'` (interlude). Detect day transition via response.day.index change. Pass `dayBoundaries` into chart rendering. |
| `PriceChart` (existing inline component in StockMarketGame.jsx) | Accept `boundaries: number[]` prop, render dashed vertical lines at those indices. |

### Phase Machine

```
briefing → playing
playing → eod         (when current_tick reaches last tick of day)
eod     → playing     (next day, user clicks Continue)
eod     → weekend     (after Friday's eod, if weekend_events exist)
weekend → recap       (after Sunday brief, end of week)
playing → recap       (legacy fallback when calendar_mode absent)
```

### Out of Scope

- Multi-week scenarios (only Mon–Fri × 1).
- Earnings volatility calibration per sector.
- Half-day sessions, options expiry, ex-dividend dates.
- Pre-market / after-hours trading windows.

---

## Section 2 — Portfolio Modal

### Trigger

A `📊 Portfolio` button mounted to the **right edge of the PersistentStrip**. Always visible during `playing` phase. Clicking opens a full-screen modal (same backdrop pattern as `CompanyDrillDown`: fixed inset-0, click outside or Esc to close, `data-testid="portfolio-backdrop"`).

### Modal Layout

```
┌──────────────────────────────────────────────────┐
│ 📊 My Portfolio                          ✕       │  Header
├──────────────────────────────────────────────────┤
│ [Overview] [Holdings] [Trades] [Performance]     │  Tab nav
├──────────────────────────────────────────────────┤
│                                                  │
│   <ActiveTab />                                  │  Body
│                                                  │
└──────────────────────────────────────────────────┘
```

### Tab 1 — Overview

- Hero: large `Net Worth: ₹X` + delta chip (`▲ +₹Y today` / `▼ -₹Y today`).
- Net-worth sparkline across the entire session so far (200×40 inline SVG).
- 6-cell mini-grid: Cash · Holdings Value · Realized P&L · Unrealized P&L · Today's P&L · Total Return %.
- Allocation pie chart by sector (8 sectors max, slices labelled with %). Click a slice to filter Holdings tab to that sector.
- Best/Worst position today: two side-by-side cards (symbol, qty, today's ₹ delta).

### Tab 2 — Holdings

Sortable table, one row per non-zero holding:

| Symbol | Sector | Qty | Avg Cost | LTP | Mkt Value | P&L ₹ | P&L % | Day Δ |
|--------|--------|-----|----------|-----|-----------|-------|-------|-------|

- Default sort: P&L % desc.
- Filter chips: All / Profit / Loss / Sector dropdown.
- Click row → close Portfolio modal, set `selectedSymbol`, open `CompanyDrillDown` for that symbol.

### Tab 3 — Trades

Full log (no truncation), one row per fill:

| Time | Day | Symbol | Side | Qty | Price | Charges | Realized P&L |
|------|-----|--------|------|-----|-------|---------|--------------|

- Filter chips: Day (Mon/Tue/Wed/Thu/Fri) · Side (Buy/Sell) · Symbol search.
- Footer: total trades · win rate (% of closed trades with realized > 0) · avg win · avg loss.

### Tab 4 — Performance

- 5-bar chart: P&L per trading day (Mon..Fri).
- Stacked area: sector exposure (% of portfolio) over time.
- Metrics card: max drawdown · biggest position concentration % · hit ratio (closed trades).
- Compare-to-market line: portfolio cumulative return % vs. equal-weight index of all 8 stocks (benchmark = mean of stock cumulative returns).

### Data Source

100% client-side compute. No new backend endpoints.

**Inputs (already available in `StockMarketGame.jsx`):**
- `priceHistory: { [symbol]: number[] }` — mid prices per tick.
- `transactions: Array<{ tick, symbol, side, qty, price, charges?, realized_pnl? }>` — from `serverState.transactions`.
- `holdings: { [symbol]: { qty, avg_price } }` — current.
- `cash: number`, `currentTick: number`, `tickCount: number`.
- `sm_cfg.days` — for day-bar grouping.
- `sm_cfg.stocks` — for sector mapping.

**Pure helpers (new files):**

`stocksim/portfolio/netWorthSeries.js`
```
netWorthSeries(transactions, priceHistory, startingCash, currentTick) → number[]
  // walk ticks 0..currentTick, replay trades to track cash + qty per symbol,
  // compute net worth at each tick using priceHistory[sym][tick]
```

`stocksim/portfolio/portfolioMetrics.js`
```
maxDrawdown(series)             → number  (% from peak)
concentration(holdings, prices) → { symbol, pct }
hitRatio(transactions)          → { winRate, avgWin, avgLoss, totalClosed }
sectorExposureSeries(...)       → Array<{ tick, sector: pct }>
benchmarkSeries(priceHistory, currentTick) → number[]  (equal-weight cumulative return %)
dayPnL(transactions, days, priceHistory, holdings) → Array<{ dayId, label, pnl }>
```

All memoised via `useMemo` keyed on `(transactions.length, currentTick)`.

### Files

**New:**
- `stocksim/PortfolioModal.jsx` — host with tab state + Esc/backdrop close.
- `stocksim/portfolio/OverviewTab.jsx`
- `stocksim/portfolio/HoldingsTab.jsx`
- `stocksim/portfolio/TradesTab.jsx`
- `stocksim/portfolio/PerformanceTab.jsx`
- `stocksim/portfolio/netWorthSeries.js` (+ `.test.js`)
- `stocksim/portfolio/portfolioMetrics.js` (+ `.test.js`)
- `stocksim/portfolio/AllocationPie.jsx` — small SVG pie chart used by OverviewTab.
- `stocksim/portfolio/Sparkline.jsx` — small SVG line chart used by OverviewTab + PerformanceTab.

**Modified:**
- `StockMarketGame.jsx` — add `portfolioOpen` state, mount `<PortfolioModal>` when open, render `📊 Portfolio` button next to PersistentStrip.

### Out of Scope

- CSV export of trades.
- Multi-game portfolio aggregation.
- Tax-lot accounting (FIFO vs. LIFO toggle).
- Stress-test scenarios ("what if X stock dropped 20%?").
- Real-time animation of pie chart on rebalance.

---

## Cross-Cutting Concerns

### Backwards Compatibility

- Legacy games without `calendar_mode` continue to use existing tick-based engine path. New code branches on `sm_cfg.calendar_mode === "week"`.
- The Portfolio modal works for both week-format and legacy games (it doesn't depend on `days[]` — only enriches with day grouping when present).

### v2 Gating

All new UI is gated behind the existing `v2Enabled` flag (org `flags.stocksim_v2_ui` or `?stocksim_v2=1` query param). v1 users never see week structure or Portfolio modal.

### Testing

- **Unit:** `netWorthSeries.test.js`, `portfolioMetrics.test.js`, `dayBoundaries.test.js` — pure functions, fixture-driven.
- **Component:** `EndOfDayModal.test.jsx`, `WeekendInterlude.test.jsx`, `DayHeader.test.jsx`, `PortfolioModal.test.jsx`, each tab's `.test.jsx`.
- **Integration (e2e via existing playwright suite):** "open portfolio modal during play, switch tabs, verify net worth matches PersistentStrip", "advance through Mon→Fri, see EndOfDay modals, weekend overlay, recap".
- **Backend:** `test_stocksim_engine.py` — week mode advances ticks correctly, overnight drift applied, earnings revealed on the right day.

### Rollout Plan

1. Land backend (engine + endpoint changes) behind `calendar_mode` config check. No frontend wired yet → existing simulator continues to work.
2. Land frontend pure helpers + tab components with their tests.
3. Wire `PortfolioModal` button into `StockMarketGame.jsx`. Ship — Portfolio works on legacy and (forthcoming) week games.
4. Wire `DayHeader` + phase machine + `EndOfDayModal` + `WeekendInterlude`. Ship — week format goes live.
5. Update `stock-market-simulator.json` with `calendar_mode: "week"` + earnings + weekend events. Live game becomes week-format.
6. Optional: write a second week-format game (e.g. `stock-market-week-earnings-season`) using the same scaffolding.

### Risk & Open Questions

- **Risk:** Net-worth sparkline computed client-side may diverge from server's accounting if there's a rounding gap. Mitigation: validate against `serverState.pnl.total + cash` for the latest tick; if delta > ₹1 log a warning.
- **Open:** Should EndOfDayModal pause the wall-clock tick counter (so users can read it without ticks advancing)? Decision: **yes, pause** — set `state.paused_at_ms` server-side when phase transitions to `eod`, restore on Continue. Server tick clock subtracts paused time.
- **Open:** Should Saturday/Sunday overlays be skippable? Decision: **yes, skippable after 3s** to respect user time, but auto-advance after 10s if untouched.

---

## Sign-off

This spec covers the C+2 design the user approved. Implementation will be planned in a separate doc using the writing-plans skill.
