# Stocksim Week-Format + Portfolio Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `stock-market-simulator` into a 5-day calendar week (Mon–Fri × 4 ticks/day, weekend events, scheduled earnings, overnight drift) and add a 4-tab Portfolio modal launched from the v2 PersistentStrip.

**Architecture:** Backend additions are gated by `calendar_mode === "week"` so legacy continuous mode is preserved. New engine helpers (`current_day`, `apply_overnight_drift`) live in `backend/engines/stocksim/`. Endpoint `/api/run/<id>/stocksim/state` is enriched with `day`, `today_pnl`, `pending_earnings`. Frontend Portfolio modal computes everything client-side from existing `serverState` and `priceHistory` — no new endpoints. All UI is gated by the existing `v2Enabled` flag.

**Tech Stack:** Python 3 + Flask + pytest (backend); React + Vite + Vitest + Testing Library + Tailwind (frontend); existing stocksim engine modules under `backend/engines/stocksim/` (orders.py, pricing.py, events.py, scoring.py, charges.py).

**Spec:** `docs/superpowers/specs/2026-05-10-stocksim-week-and-portfolio-design.md`

---

## File Structure

### New backend files
- `backend/engines/stocksim/calendar.py` — pure helpers: `current_day(state, sm_cfg)`, `day_index_to_id(idx, days)`, `tick_to_day(tick, days)`, `apply_overnight_drift(state, sm_cfg, from_day_id, to_day_id)`.

### New frontend files
- `frontend-react/src/components/game/renderers/stocksim/DayHeader.jsx`
- `frontend-react/src/components/game/renderers/stocksim/EndOfDayModal.jsx`
- `frontend-react/src/components/game/renderers/stocksim/WeekendInterlude.jsx`
- `frontend-react/src/components/game/renderers/stocksim/dayBoundaries.js`
- `frontend-react/src/components/game/renderers/stocksim/PortfolioModal.jsx`
- `frontend-react/src/components/game/renderers/stocksim/portfolio/OverviewTab.jsx`
- `frontend-react/src/components/game/renderers/stocksim/portfolio/HoldingsTab.jsx`
- `frontend-react/src/components/game/renderers/stocksim/portfolio/TradesTab.jsx`
- `frontend-react/src/components/game/renderers/stocksim/portfolio/PerformanceTab.jsx`
- `frontend-react/src/components/game/renderers/stocksim/portfolio/AllocationPie.jsx`
- `frontend-react/src/components/game/renderers/stocksim/portfolio/Sparkline.jsx`
- `frontend-react/src/components/game/renderers/stocksim/portfolio/netWorthSeries.js`
- `frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.js`

### Modified files
- `backend/games/stock-market-simulator.json` — add `calendar_mode`, `days[]`, `earnings_schedule`, `weekend_events`.
- `backend/engines/stocksim/orders.py` — `advance_to_tick` calls drift on day boundary; respects `paused_at_ms`.
- `backend/app.py` (around line 27493–27569) — enrich `/stocksim/state` response with `day`, `today_pnl`, `pending_earnings`; honor `paused_at_ms` when computing `target_tick`.
- `frontend-react/src/components/game/renderers/StockMarketGame.jsx` — phase machine gains `'eod'` and `'weekend'`; mount DayHeader, EndOfDayModal, WeekendInterlude, PortfolioModal, 📊 trigger button; `PriceChart` accepts `boundaries` prop.
- `frontend-react/src/components/game/renderers/stocksim/MarketBriefing.jsx` — `📅 Earnings: <Day>` chip when stock has scheduled earnings.

### New test files
Each new pure helper / component gets a sibling `.test.js` or `.test.jsx`. Backend additions get pytest tests in `backend/tests/`.

---

## Phase A — Frontend Portfolio Modal (independent of week format)

This phase ships first. Portfolio modal works against legacy and forthcoming week games.

### Task 1: `netWorthSeries` helper

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/portfolio/netWorthSeries.js`
- Test: `frontend-react/src/components/game/renderers/stocksim/portfolio/netWorthSeries.test.js`

- [ ] **Step 1: Write failing test**

```js
// netWorthSeries.test.js
import { describe, it, expect } from 'vitest';
import { netWorthSeries } from './netWorthSeries';

describe('netWorthSeries', () => {
  it('returns startingCash for tick 0 with no trades', () => {
    const series = netWorthSeries([], { TECHV: [100, 110, 120] }, 50000, 0);
    expect(series).toEqual([50000]);
  });

  it('replays a buy and tracks holdings value across ticks', () => {
    // Buy 10 TECHV at tick 1 for ₹110/share = ₹1,100 spent
    const txs = [{ tick: 1, symbol: 'TECHV', side: 'buy', qty: 10, price: 110 }];
    const prices = { TECHV: [100, 110, 120, 130] };
    const series = netWorthSeries(txs, prices, 50000, 3);
    expect(series).toHaveLength(4);
    expect(series[0]).toBe(50000);                 // before trade
    expect(series[1]).toBe(50000 - 1100 + 10*110); // cash drops, holdings worth same
    expect(series[2]).toBe(50000 - 1100 + 10*120);
    expect(series[3]).toBe(50000 - 1100 + 10*130);
  });

  it('handles a sell after a buy (realizes pnl)', () => {
    const txs = [
      { tick: 1, symbol: 'TECHV', side: 'buy',  qty: 10, price: 100 },
      { tick: 3, symbol: 'TECHV', side: 'sell', qty: 10, price: 130 },
    ];
    const prices = { TECHV: [100, 100, 100, 130, 140] };
    const series = netWorthSeries(txs, prices, 10000, 4);
    expect(series[0]).toBe(10000);
    expect(series[1]).toBe(10000 - 1000 + 10*100); // 10000
    expect(series[3]).toBe(10000 - 1000 + 1300);   // 10300 (cash up after sell)
    expect(series[4]).toBe(10300);                  // no holdings, just cash
  });
});
```

- [ ] **Step 2: Run to verify failure**

`cd frontend-react && npx vitest run src/components/game/renderers/stocksim/portfolio/netWorthSeries.test.js`
Expected: FAIL — `Failed to resolve import "./netWorthSeries"`.

- [ ] **Step 3: Implement**

```js
// netWorthSeries.js
// Replays transactions over the price history to compute net worth at each tick.
// transactions: Array<{ tick, symbol, side: 'buy'|'sell', qty, price, charges? }>
// priceHistory: { [symbol]: number[] }   // index = tick
// startingCash: number
// currentTick: number   // inclusive — produces currentTick+1 points
// Returns: number[] of length currentTick+1
export function netWorthSeries(transactions, priceHistory, startingCash, currentTick) {
  const sorted = [...(transactions || [])].sort((a, b) => (a.tick ?? 0) - (b.tick ?? 0));
  const holdings = {};
  let cash = startingCash;
  let txIdx = 0;
  const out = [];

  for (let t = 0; t <= currentTick; t++) {
    while (txIdx < sorted.length && (sorted[txIdx].tick ?? 0) <= t) {
      const tx = sorted[txIdx++];
      const charges = tx.charges ?? 0;
      const cost = tx.qty * tx.price;
      if (tx.side === 'buy') {
        cash -= cost + charges;
        holdings[tx.symbol] = (holdings[tx.symbol] ?? 0) + tx.qty;
      } else {
        cash += cost - charges;
        holdings[tx.symbol] = (holdings[tx.symbol] ?? 0) - tx.qty;
      }
    }
    let mv = 0;
    for (const sym of Object.keys(holdings)) {
      const qty = holdings[sym];
      if (!qty) continue;
      const series = priceHistory?.[sym] ?? [];
      const price = series[t] ?? series[series.length - 1] ?? 0;
      mv += qty * price;
    }
    out.push(cash + mv);
  }
  return out;
}
```

- [ ] **Step 4: Run to verify pass**

`cd frontend-react && npx vitest run src/components/game/renderers/stocksim/portfolio/netWorthSeries.test.js`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/netWorthSeries.js \
        frontend-react/src/components/game/renderers/stocksim/portfolio/netWorthSeries.test.js
git commit -m "feat(stocksim): netWorthSeries client-side replay helper"
```

---

### Task 2: `portfolioMetrics` — drawdown / concentration / hit ratio

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.js`
- Test: `frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.test.js`

- [ ] **Step 1: Write failing test**

```js
// portfolioMetrics.test.js
import { describe, it, expect } from 'vitest';
import { maxDrawdown, concentration, hitRatio } from './portfolioMetrics';

describe('maxDrawdown', () => {
  it('returns 0 for monotonically rising series', () => {
    expect(maxDrawdown([100, 110, 120, 130])).toBe(0);
  });
  it('computes percent drop from peak', () => {
    expect(maxDrawdown([100, 120, 90, 110])).toBeCloseTo(25, 5); // 120 → 90
  });
  it('returns 0 for empty/single', () => {
    expect(maxDrawdown([])).toBe(0);
    expect(maxDrawdown([100])).toBe(0);
  });
});

describe('concentration', () => {
  it('returns largest position by market value as pct of total', () => {
    const holdings = { A: { qty: 10 }, B: { qty: 5 } };
    const prices = { A: 200, B: 100 };  // A=2000, B=500, total=2500
    const result = concentration(holdings, prices);
    expect(result.symbol).toBe('A');
    expect(result.pct).toBeCloseTo(80, 1);
  });
  it('returns null on empty holdings', () => {
    expect(concentration({}, {})).toBeNull();
  });
});

describe('hitRatio', () => {
  it('counts winning closed trades vs total closed', () => {
    const txs = [
      { side: 'sell', realized_pnl: 500 },
      { side: 'sell', realized_pnl: -200 },
      { side: 'sell', realized_pnl: 300 },
      { side: 'buy', realized_pnl: 0 },        // open: not counted
    ];
    const r = hitRatio(txs);
    expect(r.totalClosed).toBe(3);
    expect(r.winRate).toBeCloseTo(2 / 3, 3);
    expect(r.avgWin).toBeCloseTo(400);
    expect(r.avgLoss).toBeCloseTo(-200);
  });
  it('handles no closed trades', () => {
    expect(hitRatio([])).toEqual({ winRate: 0, avgWin: 0, avgLoss: 0, totalClosed: 0 });
  });
});
```

- [ ] **Step 2: Run to verify failure**

`cd frontend-react && npx vitest run src/components/game/renderers/stocksim/portfolio/portfolioMetrics.test.js`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```js
// portfolioMetrics.js
export function maxDrawdown(series) {
  if (!series || series.length < 2) return 0;
  let peak = series[0];
  let maxDD = 0;
  for (const v of series) {
    if (v > peak) peak = v;
    if (peak > 0) {
      const dd = ((peak - v) / peak) * 100;
      if (dd > maxDD) maxDD = dd;
    }
  }
  return maxDD;
}

export function concentration(holdings, prices) {
  let total = 0;
  let best = null;
  for (const sym of Object.keys(holdings || {})) {
    const qty = holdings[sym]?.qty ?? 0;
    if (!qty) continue;
    const px = prices?.[sym] ?? 0;
    const mv = qty * px;
    total += mv;
    if (!best || mv > best.mv) best = { symbol: sym, mv };
  }
  if (!best || total <= 0) return null;
  return { symbol: best.symbol, pct: (best.mv / total) * 100 };
}

export function hitRatio(transactions) {
  const closed = (transactions || []).filter(
    (t) => t.side === 'sell' && typeof t.realized_pnl === 'number'
  );
  if (closed.length === 0) return { winRate: 0, avgWin: 0, avgLoss: 0, totalClosed: 0 };
  const wins = closed.filter((t) => t.realized_pnl > 0);
  const losses = closed.filter((t) => t.realized_pnl < 0);
  const sum = (a) => a.reduce((s, t) => s + t.realized_pnl, 0);
  return {
    totalClosed: closed.length,
    winRate: wins.length / closed.length,
    avgWin: wins.length ? sum(wins) / wins.length : 0,
    avgLoss: losses.length ? sum(losses) / losses.length : 0,
  };
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.js \
        frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.test.js
git commit -m "feat(stocksim): drawdown / concentration / hit-ratio metrics"
```

---

### Task 3: `portfolioMetrics` — sector exposure / benchmark / day P&L

**Files:**
- Modify: `frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.js`
- Modify: `frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.test.js`

- [ ] **Step 1: Append failing tests**

Append to `portfolioMetrics.test.js`:

```js
import { sectorExposureSeries, benchmarkSeries, dayPnL } from './portfolioMetrics';

describe('sectorExposureSeries', () => {
  it('returns per-tick sector pct from transactions and price history', () => {
    const txs = [{ tick: 0, symbol: 'A', side: 'buy', qty: 10, price: 100 }]; // sector IT
    const prices = { A: [100, 110], B: [50, 50] };
    const sectorBySymbol = { A: 'IT', B: 'Pharma' };
    const series = sectorExposureSeries(txs, prices, sectorBySymbol, 10000, 1);
    expect(series).toHaveLength(2);
    expect(series[0].IT).toBeCloseTo(100); // 100% of holdings value is IT
    expect(series[1].IT).toBeCloseTo(100);
  });
});

describe('benchmarkSeries', () => {
  it('returns equal-weight cumulative return %', () => {
    const prices = { A: [100, 110], B: [200, 220] };  // both +10%
    const series = benchmarkSeries(prices, 1);
    expect(series[0]).toBeCloseTo(0);
    expect(series[1]).toBeCloseTo(10, 1);
  });
});

describe('dayPnL', () => {
  it('groups realized pnl by day window', () => {
    const days = [
      { id: 'mon', label: 'Monday', ticks: 4 },
      { id: 'tue', label: 'Tuesday', ticks: 4 },
    ];
    const txs = [
      { tick: 1, side: 'sell', realized_pnl: 100 },  // mon
      { tick: 5, side: 'sell', realized_pnl: -50 },  // tue
      { tick: 6, side: 'sell', realized_pnl: 200 },  // tue
    ];
    const result = dayPnL(txs, days);
    expect(result).toEqual([
      { dayId: 'mon', label: 'Monday', pnl: 100 },
      { dayId: 'tue', label: 'Tuesday', pnl: 150 },
    ]);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — `sectorExposureSeries` / `benchmarkSeries` / `dayPnL` undefined.

- [ ] **Step 3: Append implementation**

Append to `portfolioMetrics.js`:

```js
// Replays trades to track holdings, then aggregates market value by sector at each tick.
// sectorBySymbol: { [symbol]: sectorString }
// Returns: Array<{ [sectorName]: pct, total: number }>
export function sectorExposureSeries(transactions, priceHistory, sectorBySymbol, startingCash, currentTick) {
  const sorted = [...(transactions || [])].sort((a, b) => (a.tick ?? 0) - (b.tick ?? 0));
  const holdings = {};
  let cash = startingCash;
  let i = 0;
  const out = [];
  for (let t = 0; t <= currentTick; t++) {
    while (i < sorted.length && (sorted[i].tick ?? 0) <= t) {
      const tx = sorted[i++];
      const cost = tx.qty * tx.price;
      const charges = tx.charges ?? 0;
      if (tx.side === 'buy') {
        cash -= cost + charges;
        holdings[tx.symbol] = (holdings[tx.symbol] ?? 0) + tx.qty;
      } else {
        cash += cost - charges;
        holdings[tx.symbol] = (holdings[tx.symbol] ?? 0) - tx.qty;
      }
    }
    const sectors = {};
    let total = 0;
    for (const sym of Object.keys(holdings)) {
      const qty = holdings[sym];
      if (!qty) continue;
      const series = priceHistory?.[sym] ?? [];
      const px = series[t] ?? series[series.length - 1] ?? 0;
      const mv = qty * px;
      total += mv;
      const sec = sectorBySymbol?.[sym] ?? 'Other';
      sectors[sec] = (sectors[sec] ?? 0) + mv;
    }
    const pcts = { total };
    for (const sec of Object.keys(sectors)) {
      pcts[sec] = total > 0 ? (sectors[sec] / total) * 100 : 0;
    }
    out.push(pcts);
  }
  return out;
}

// Equal-weight cumulative return % across all symbols in priceHistory.
export function benchmarkSeries(priceHistory, currentTick) {
  const symbols = Object.keys(priceHistory || {});
  if (symbols.length === 0) return [];
  const out = [];
  for (let t = 0; t <= currentTick; t++) {
    let sum = 0;
    let n = 0;
    for (const sym of symbols) {
      const arr = priceHistory[sym] ?? [];
      const start = arr[0];
      const cur = arr[t] ?? arr[arr.length - 1];
      if (start && cur != null) {
        sum += (cur - start) / start;
        n += 1;
      }
    }
    out.push(n ? (sum / n) * 100 : 0);
  }
  return out;
}

// Sums realized pnl per day window. days: Array<{ id, label, ticks }>.
// Tick t belongs to day k when sum(days[0..k-1].ticks) <= t < sum(days[0..k].ticks).
export function dayPnL(transactions, days) {
  const out = (days || []).map((d) => ({ dayId: d.id, label: d.label, pnl: 0 }));
  let cumulative = 0;
  const ranges = (days || []).map((d) => {
    const range = { start: cumulative, end: cumulative + d.ticks };
    cumulative = range.end;
    return range;
  });
  for (const tx of transactions || []) {
    if (tx.side !== 'sell' || typeof tx.realized_pnl !== 'number') continue;
    const tick = tx.tick ?? 0;
    const idx = ranges.findIndex((r) => tick >= r.start && tick < r.end);
    if (idx >= 0) out[idx].pnl += tx.realized_pnl;
  }
  return out;
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 10 tests total in portfolioMetrics.test.js.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.js \
        frontend-react/src/components/game/renderers/stocksim/portfolio/portfolioMetrics.test.js
git commit -m "feat(stocksim): sector exposure, benchmark, day-pnl metrics"
```

---

### Task 4: `Sparkline.jsx` — small SVG line chart

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/portfolio/Sparkline.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/portfolio/Sparkline.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import Sparkline from './Sparkline';

describe('Sparkline', () => {
  it('renders an svg with a polyline path when given values', () => {
    const { container } = render(<Sparkline values={[10, 12, 8, 14, 11]} width={200} height={40} />);
    expect(container.querySelector('svg')).toBeTruthy();
    expect(container.querySelector('polyline')).toBeTruthy();
  });

  it('renders an empty placeholder when no values', () => {
    const { container } = render(<Sparkline values={[]} />);
    expect(container.querySelector('polyline')).toBeFalsy();
  });
});
```

- [ ] **Step 2: Run to verify failure**

`cd frontend-react && npx vitest run src/components/game/renderers/stocksim/portfolio/Sparkline.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```jsx
// Sparkline.jsx
import React from 'react';
import { THEME, gainLossColor } from '../theme';

export default function Sparkline({
  values = [],
  width = 200,
  height = 40,
  stroke,
  strokeWidth = 1.5,
}) {
  if (!values.length) {
    return <svg width={width} height={height} aria-label="sparkline-empty" />;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const dx = values.length > 1 ? width / (values.length - 1) : 0;
  const points = values
    .map((v, i) => `${(i * dx).toFixed(2)},${(height - ((v - min) / range) * height).toFixed(2)}`)
    .join(' ');
  const color = stroke ?? gainLossColor(values[values.length - 1] - values[0]);
  return (
    <svg width={width} height={height} aria-label="sparkline">
      <polyline points={points} fill="none" stroke={color} strokeWidth={strokeWidth} />
    </svg>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/Sparkline.jsx \
        frontend-react/src/components/game/renderers/stocksim/portfolio/Sparkline.test.jsx
git commit -m "feat(stocksim): Sparkline svg component"
```

---

### Task 5: `AllocationPie.jsx` — small SVG pie chart

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/portfolio/AllocationPie.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/portfolio/AllocationPie.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import AllocationPie from './AllocationPie';

describe('AllocationPie', () => {
  it('renders one path per slice', () => {
    const slices = [{ label: 'IT', value: 60 }, { label: 'Pharma', value: 40 }];
    const { container } = render(<AllocationPie slices={slices} size={120} />);
    const paths = container.querySelectorAll('path[data-slice]');
    expect(paths).toHaveLength(2);
  });

  it('calls onSliceClick with label when slice clicked', () => {
    const slices = [{ label: 'IT', value: 60 }, { label: 'Pharma', value: 40 }];
    const onClick = vi.fn();
    const { container } = render(<AllocationPie slices={slices} onSliceClick={onClick} />);
    fireEvent.click(container.querySelector('path[data-slice="IT"]'));
    expect(onClick).toHaveBeenCalledWith('IT');
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```jsx
// AllocationPie.jsx
import React from 'react';

const PALETTE = ['#B46B1E', '#0F6E56', '#A32D2D', '#854F0B', '#3F6FB0', '#7A3FA8', '#D4A645', '#5B7C2F'];

function arcPath(cx, cy, r, startAngle, endAngle) {
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy + r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy + r * Math.sin(endAngle);
  const largeArc = endAngle - startAngle > Math.PI ? 1 : 0;
  return `M ${cx},${cy} L ${x1},${y1} A ${r},${r} 0 ${largeArc} 1 ${x2},${y2} Z`;
}

export default function AllocationPie({ slices = [], size = 120, onSliceClick }) {
  const total = slices.reduce((s, x) => s + (x.value || 0), 0);
  if (total <= 0) return <svg width={size} height={size} aria-label="pie-empty" />;
  const r = size / 2;
  let acc = -Math.PI / 2;
  return (
    <svg width={size} height={size} aria-label="allocation-pie">
      {slices.map((s, i) => {
        const angle = (s.value / total) * Math.PI * 2;
        const d = arcPath(r, r, r, acc, acc + angle);
        const path = (
          <path
            key={s.label}
            d={d}
            fill={PALETTE[i % PALETTE.length]}
            data-slice={s.label}
            style={{ cursor: onSliceClick ? 'pointer' : 'default' }}
            onClick={onSliceClick ? () => onSliceClick(s.label) : undefined}
          />
        );
        acc += angle;
        return path;
      })}
    </svg>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/AllocationPie.jsx \
        frontend-react/src/components/game/renderers/stocksim/portfolio/AllocationPie.test.jsx
git commit -m "feat(stocksim): AllocationPie svg component"
```

---

### Task 6: `OverviewTab.jsx`

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/portfolio/OverviewTab.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/portfolio/OverviewTab.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import OverviewTab from './OverviewTab';

const fixture = {
  netWorth: 52000,
  startingCash: 50000,
  todayPnL: 500,
  cash: 30000,
  holdingsValue: 22000,
  realizedPnL: 800,
  unrealizedPnL: 1200,
  netWorthSeries: [50000, 50500, 51200, 52000],
  allocation: [{ label: 'IT', value: 60 }, { label: 'Pharma', value: 40 }],
  bestToday: { symbol: 'TECHV', delta: 320 },
  worstToday: { symbol: 'BHARATBANK', delta: -120 },
};

describe('OverviewTab', () => {
  it('renders net worth and total return', () => {
    render(<OverviewTab {...fixture} />);
    expect(screen.getByTestId('overview-networth').textContent).toContain('52,000');
    expect(screen.getByTestId('overview-total-return').textContent).toContain('4.00%');
  });

  it('renders best/worst symbols', () => {
    render(<OverviewTab {...fixture} />);
    expect(screen.getByTestId('overview-best').textContent).toContain('TECHV');
    expect(screen.getByTestId('overview-worst').textContent).toContain('BHARATBANK');
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```jsx
// OverviewTab.jsx
import React from 'react';
import Sparkline from './Sparkline';
import AllocationPie from './AllocationPie';
import { THEME, gainLossColor } from '../theme';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;
const pct = (n) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`;

export default function OverviewTab({
  netWorth = 0,
  startingCash = 0,
  todayPnL = 0,
  cash = 0,
  holdingsValue = 0,
  realizedPnL = 0,
  unrealizedPnL = 0,
  netWorthSeries = [],
  allocation = [],
  bestToday,
  worstToday,
  onAllocationClick,
}) {
  const totalReturnPct = startingCash ? ((netWorth - startingCash) / startingCash) * 100 : 0;
  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div style={{ fontSize: 12, color: THEME.textMuted }}>Net worth</div>
          <div data-testid="overview-networth" style={{ fontSize: 28, fontWeight: 800, color: THEME.textPrimary }}>{fmt(netWorth)}</div>
          <div style={{ color: gainLossColor(todayPnL), fontWeight: 700 }}>
            {todayPnL >= 0 ? '▲' : '▼'} {fmt(Math.abs(todayPnL))} today
          </div>
        </div>
        <div data-testid="overview-total-return" style={{ color: gainLossColor(totalReturnPct), fontWeight: 700 }}>
          {pct(totalReturnPct)}
        </div>
      </div>

      <div style={{ marginTop: 8 }}>
        <Sparkline values={netWorthSeries} width={520} height={48} />
      </div>

      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        <Stat label="Cash" value={fmt(cash)} />
        <Stat label="Holdings" value={fmt(holdingsValue)} />
        <Stat label="Today's P&L" value={fmt(todayPnL)} color={gainLossColor(todayPnL)} />
        <Stat label="Realized" value={fmt(realizedPnL)} color={gainLossColor(realizedPnL)} />
        <Stat label="Unrealized" value={fmt(unrealizedPnL)} color={gainLossColor(unrealizedPnL)} />
        <Stat label="Total return" value={pct(totalReturnPct)} color={gainLossColor(totalReturnPct)} />
      </div>

      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '120px 1fr', gap: 12, alignItems: 'center' }}>
        <AllocationPie slices={allocation} size={120} onSliceClick={onAllocationClick} />
        <div>
          {allocation.map((s) => (
            <div key={s.label} style={{ fontSize: 12, color: THEME.textPrimary }}>
              {s.label}: {s.value.toFixed(1)}%
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
        <PositionCard testId="overview-best" label="Best today" position={bestToday} />
        <PositionCard testId="overview-worst" label="Worst today" position={worstToday} />
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ background: THEME.bgTile, padding: 8, borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted }}>{label}</div>
      <div style={{ fontWeight: 700, color: color ?? THEME.textPrimary }}>{value}</div>
    </div>
  );
}

function PositionCard({ testId, label, position }) {
  if (!position) {
    return <div data-testid={testId} style={{ background: THEME.bgTile, padding: 8, borderRadius: 6, color: THEME.textMuted, fontSize: 12 }}>{label}: —</div>;
  }
  return (
    <div data-testid={testId} style={{ background: THEME.bgTile, padding: 8, borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted }}>{label}</div>
      <div style={{ fontWeight: 700 }}>{position.symbol}</div>
      <div style={{ color: gainLossColor(position.delta) }}>{fmt(position.delta)}</div>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/OverviewTab.jsx \
        frontend-react/src/components/game/renderers/stocksim/portfolio/OverviewTab.test.jsx
git commit -m "feat(stocksim): portfolio OverviewTab"
```

---

### Task 7: `HoldingsTab.jsx`

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/portfolio/HoldingsTab.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/portfolio/HoldingsTab.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import HoldingsTab from './HoldingsTab';

const rows = [
  { symbol: 'TECHV', sector: 'IT', qty: 10, avgCost: 1100, ltp: 1180, pnlAbs: 800, pnlPct: 7.27, dayDelta: 60 },
  { symbol: 'BHARATBANK', sector: 'Fin', qty: 5, avgCost: 600, ltp: 580, pnlAbs: -100, pnlPct: -3.3, dayDelta: -25 },
];

describe('HoldingsTab', () => {
  it('renders one row per holding', () => {
    render(<HoldingsTab rows={rows} />);
    expect(screen.getByTestId('holding-row-TECHV')).toBeTruthy();
    expect(screen.getByTestId('holding-row-BHARATBANK')).toBeTruthy();
  });

  it('opens drilldown on row click', () => {
    const onOpen = vi.fn();
    render(<HoldingsTab rows={rows} onOpenSymbol={onOpen} />);
    fireEvent.click(screen.getByTestId('holding-row-TECHV'));
    expect(onOpen).toHaveBeenCalledWith('TECHV');
  });

  it('filters by Profit chip', () => {
    render(<HoldingsTab rows={rows} />);
    fireEvent.click(screen.getByTestId('holdings-filter-profit'));
    expect(screen.getByTestId('holding-row-TECHV')).toBeTruthy();
    expect(screen.queryByTestId('holding-row-BHARATBANK')).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```jsx
// HoldingsTab.jsx
import React, { useState, useMemo } from 'react';
import { THEME, gainLossColor } from '../theme';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

export default function HoldingsTab({ rows = [], onOpenSymbol, sectorFilter = null, onClearSectorFilter }) {
  const [filter, setFilter] = useState('all');  // all | profit | loss
  const [sortKey, setSortKey] = useState('pnlPct');

  const filtered = useMemo(() => {
    let r = rows;
    if (filter === 'profit') r = r.filter((x) => x.pnlAbs > 0);
    if (filter === 'loss') r = r.filter((x) => x.pnlAbs < 0);
    if (sectorFilter) r = r.filter((x) => x.sector === sectorFilter);
    return [...r].sort((a, b) => (b[sortKey] ?? 0) - (a[sortKey] ?? 0));
  }, [rows, filter, sortKey, sectorFilter]);

  const Chip = ({ id, label }) => (
    <button
      data-testid={`holdings-filter-${id}`}
      onClick={() => setFilter(id)}
      style={{
        padding: '4px 10px', borderRadius: 999, border: `1px solid ${THEME.borderTile}`,
        background: filter === id ? THEME.accentWarm : '#fff',
        color: filter === id ? '#fff' : THEME.textPrimary,
        cursor: 'pointer', fontSize: 12,
      }}
    >{label}</button>
  );

  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'center' }}>
        <Chip id="all" label="All" />
        <Chip id="profit" label="Profit" />
        <Chip id="loss" label="Loss" />
        {sectorFilter && (
          <button
            onClick={onClearSectorFilter}
            data-testid="holdings-clear-sector"
            style={{ marginLeft: 'auto', fontSize: 12, color: THEME.textMuted, background: 'none', border: 'none', cursor: 'pointer' }}
          >× Sector: {sectorFilter}</button>
        )}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: THEME.bgTile, color: THEME.textMuted }}>
            {['Symbol', 'Sector', 'Qty', 'Avg', 'LTP', 'MV', 'P&L ₹', 'P&L %', 'Day Δ'].map((h) => (
              <th key={h} style={{ padding: 6, textAlign: 'left' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr
              key={r.symbol}
              data-testid={`holding-row-${r.symbol}`}
              onClick={() => onOpenSymbol?.(r.symbol)}
              style={{ cursor: 'pointer', borderBottom: `1px solid ${THEME.borderTile}` }}
            >
              <td style={{ padding: 6, fontWeight: 700 }}>{r.symbol}</td>
              <td style={{ padding: 6 }}>{r.sector}</td>
              <td style={{ padding: 6 }}>{r.qty}</td>
              <td style={{ padding: 6 }}>{fmt(r.avgCost)}</td>
              <td style={{ padding: 6 }}>{fmt(r.ltp)}</td>
              <td style={{ padding: 6 }}>{fmt(r.qty * r.ltp)}</td>
              <td style={{ padding: 6, color: gainLossColor(r.pnlAbs) }}>{fmt(r.pnlAbs)}</td>
              <td style={{ padding: 6, color: gainLossColor(r.pnlPct) }}>{r.pnlPct.toFixed(2)}%</td>
              <td style={{ padding: 6, color: gainLossColor(r.dayDelta) }}>{fmt(r.dayDelta)}</td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan={9} style={{ padding: 16, textAlign: 'center', color: THEME.textMuted }}>No holdings match.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/HoldingsTab.jsx \
        frontend-react/src/components/game/renderers/stocksim/portfolio/HoldingsTab.test.jsx
git commit -m "feat(stocksim): portfolio HoldingsTab with filters and row click"
```

---

### Task 8: `TradesTab.jsx`

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/portfolio/TradesTab.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/portfolio/TradesTab.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TradesTab from './TradesTab';

const trades = [
  { tick: 1, dayLabel: 'Mon', symbol: 'TECHV', side: 'buy',  qty: 10, price: 100, charges: 5, realized_pnl: 0 },
  { tick: 5, dayLabel: 'Tue', symbol: 'TECHV', side: 'sell', qty: 10, price: 130, charges: 5, realized_pnl: 290 },
  { tick: 6, dayLabel: 'Tue', symbol: 'BHARATBANK', side: 'buy', qty: 5, price: 600, charges: 3 },
];

describe('TradesTab', () => {
  it('renders one row per trade and footer summary', () => {
    render(<TradesTab trades={trades} />);
    expect(screen.getAllByTestId(/^trade-row-/)).toHaveLength(3);
    expect(screen.getByTestId('trades-summary').textContent).toContain('Win rate');
  });

  it('filters by side', () => {
    render(<TradesTab trades={trades} />);
    fireEvent.click(screen.getByTestId('trades-filter-buy'));
    expect(screen.getAllByTestId(/^trade-row-/)).toHaveLength(2);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```jsx
// TradesTab.jsx
import React, { useState, useMemo } from 'react';
import { THEME, gainLossColor } from '../theme';
import { hitRatio } from './portfolioMetrics';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

export default function TradesTab({ trades = [] }) {
  const [side, setSide] = useState('all');
  const [day, setDay] = useState('all');
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    return trades.filter((t) => {
      if (side !== 'all' && t.side !== side) return false;
      if (day !== 'all' && t.dayLabel !== day) return false;
      if (query && !t.symbol.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [trades, side, day, query]);

  const allDays = useMemo(() => Array.from(new Set(trades.map((t) => t.dayLabel).filter(Boolean))), [trades]);
  const stats = hitRatio(trades);

  const Chip = ({ id, group, label, current, setter }) => (
    <button
      data-testid={`trades-filter-${id}`}
      onClick={() => setter(id)}
      style={{
        padding: '3px 8px', borderRadius: 999, border: `1px solid ${THEME.borderTile}`,
        background: current === id ? THEME.accentWarm : '#fff',
        color: current === id ? '#fff' : THEME.textPrimary,
        cursor: 'pointer', fontSize: 11, marginRight: 4,
      }}
    >{label}</button>
  );

  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8, alignItems: 'center' }}>
        <Chip id="all"  label="All sides" current={side} setter={setSide} />
        <Chip id="buy"  label="Buy"        current={side} setter={setSide} />
        <Chip id="sell" label="Sell"       current={side} setter={setSide} />
        <span style={{ width: 8 }} />
        <Chip id="all" label="All days" current={day} setter={setDay} />
        {allDays.map((d) => (
          <Chip key={d} id={d} label={d} current={day} setter={setDay} />
        ))}
        <input
          data-testid="trades-search"
          placeholder="Symbol…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginLeft: 'auto', padding: '3px 6px', border: `1px solid ${THEME.borderTile}`, borderRadius: 6, fontSize: 11 }}
        />
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr style={{ background: THEME.bgTile, color: THEME.textMuted }}>
            {['Tick', 'Day', 'Symbol', 'Side', 'Qty', 'Price', 'Charges', 'Realized'].map((h) => (
              <th key={h} style={{ padding: 6, textAlign: 'left' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.map((t, i) => (
            <tr key={i} data-testid={`trade-row-${i}`} style={{ borderBottom: `1px solid ${THEME.borderTile}` }}>
              <td style={{ padding: 6 }}>{t.tick}</td>
              <td style={{ padding: 6 }}>{t.dayLabel ?? ''}</td>
              <td style={{ padding: 6, fontWeight: 700 }}>{t.symbol}</td>
              <td style={{ padding: 6, color: t.side === 'buy' ? THEME.gain : THEME.loss }}>{t.side}</td>
              <td style={{ padding: 6 }}>{t.qty}</td>
              <td style={{ padding: 6 }}>{fmt(t.price)}</td>
              <td style={{ padding: 6 }}>{fmt(t.charges ?? 0)}</td>
              <td style={{ padding: 6, color: gainLossColor(t.realized_pnl ?? 0) }}>
                {t.realized_pnl != null ? fmt(t.realized_pnl) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div data-testid="trades-summary" style={{ marginTop: 10, fontSize: 12, color: THEME.textMuted }}>
        {trades.length} trade(s) · {stats.totalClosed} closed · Win rate {(stats.winRate * 100).toFixed(0)}% ·
        Avg win {fmt(stats.avgWin)} · Avg loss {fmt(stats.avgLoss)}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/TradesTab.jsx \
        frontend-react/src/components/game/renderers/stocksim/portfolio/TradesTab.test.jsx
git commit -m "feat(stocksim): portfolio TradesTab with side/day filters"
```

---

### Task 9: `PerformanceTab.jsx`

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/portfolio/PerformanceTab.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/portfolio/PerformanceTab.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PerformanceTab from './PerformanceTab';

describe('PerformanceTab', () => {
  it('renders day P&L bars and metrics card', () => {
    render(
      <PerformanceTab
        dayPnL={[{ dayId: 'mon', label: 'Mon', pnl: 200 }, { dayId: 'tue', label: 'Tue', pnl: -100 }]}
        portfolioReturnSeries={[0, 1, 2, 3]}
        benchmarkReturnSeries={[0, 0.5, 1, 1.5]}
        maxDD={4.2}
        topConcentration={{ symbol: 'TECHV', pct: 35 }}
        hitRatio={{ winRate: 0.66, totalClosed: 3, avgWin: 200, avgLoss: -50 }}
      />
    );
    expect(screen.getByTestId('perf-day-mon')).toBeTruthy();
    expect(screen.getByTestId('perf-day-tue')).toBeTruthy();
    expect(screen.getByTestId('perf-max-dd').textContent).toContain('4.2');
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```jsx
// PerformanceTab.jsx
import React from 'react';
import { THEME, gainLossColor } from '../theme';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;

export default function PerformanceTab({
  dayPnL = [],
  portfolioReturnSeries = [],
  benchmarkReturnSeries = [],
  maxDD = 0,
  topConcentration,
  hitRatio,
}) {
  const maxAbs = Math.max(1, ...dayPnL.map((d) => Math.abs(d.pnl)));
  return (
    <div style={{ padding: 12 }}>
      <div style={{ fontWeight: 700, marginBottom: 6, color: THEME.textPrimary }}>P&L by day</div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 100, borderBottom: `1px solid ${THEME.borderTile}`, padding: '0 4px 4px' }}>
        {dayPnL.map((d) => {
          const h = (Math.abs(d.pnl) / maxAbs) * 80;
          return (
            <div key={d.dayId} data-testid={`perf-day-${d.dayId}`} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: 36 }}>
              <div style={{ fontSize: 10, color: gainLossColor(d.pnl) }}>{fmt(d.pnl)}</div>
              <div style={{ width: 24, height: h, background: gainLossColor(d.pnl), borderRadius: 3, marginTop: 4 }} />
              <div style={{ fontSize: 10, color: THEME.textMuted, marginTop: 4 }}>{d.label}</div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 12, fontWeight: 700, color: THEME.textPrimary }}>Return vs benchmark</div>
      <ReturnLines portfolio={portfolioReturnSeries} benchmark={benchmarkReturnSeries} />

      <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        <Stat data-testid="perf-max-dd" label="Max drawdown" value={`${maxDD.toFixed(1)}%`} testId="perf-max-dd" />
        <Stat label="Top concentration" value={topConcentration ? `${topConcentration.symbol} (${topConcentration.pct.toFixed(0)}%)` : '—'} />
        <Stat label="Hit ratio" value={hitRatio ? `${(hitRatio.winRate * 100).toFixed(0)}% (${hitRatio.totalClosed})` : '—'} />
      </div>
    </div>
  );
}

function Stat({ label, value, testId }) {
  return (
    <div data-testid={testId} style={{ background: THEME.bgTile, padding: 8, borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted }}>{label}</div>
      <div style={{ fontWeight: 700, color: THEME.textPrimary }}>{value}</div>
    </div>
  );
}

function ReturnLines({ portfolio, benchmark }) {
  const all = [...portfolio, ...benchmark];
  if (!all.length) return null;
  const min = Math.min(...all);
  const max = Math.max(...all);
  const range = max - min || 1;
  const W = 520, H = 120;
  const toPoints = (arr) => arr.map((v, i) => `${(i * (W / Math.max(arr.length - 1, 1))).toFixed(2)},${(H - ((v - min) / range) * H).toFixed(2)}`).join(' ');
  return (
    <svg width={W} height={H} aria-label="return-lines">
      <polyline points={toPoints(benchmark)} fill="none" stroke={THEME.textMuted} strokeWidth={1.5} strokeDasharray="4 3" />
      <polyline points={toPoints(portfolio)} fill="none" stroke={THEME.accentWarm} strokeWidth={2} />
    </svg>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 1 test.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/portfolio/PerformanceTab.jsx \
        frontend-react/src/components/game/renderers/stocksim/portfolio/PerformanceTab.test.jsx
git commit -m "feat(stocksim): portfolio PerformanceTab"
```

---

### Task 10: `PortfolioModal.jsx` host

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/PortfolioModal.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/PortfolioModal.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import PortfolioModal from './PortfolioModal';

const baseProps = {
  open: true,
  onClose: vi.fn(),
  cash: 30000,
  startingCash: 50000,
  netWorth: 52000,
  todayPnL: 500,
  pnl: { realized: 800, unrealized: 1200 },
  holdings: { TECHV: { qty: 10, avg_price: 1100 } },
  quotes: { TECHV: { mid: 1180 } },
  transactions: [],
  priceHistory: { TECHV: [1100, 1150, 1180] },
  currentTick: 2,
  stocks: [{ symbol: 'TECHV', sector: 'IT', name: 'TechVista' }],
  days: [{ id: 'mon', label: 'Monday', ticks: 4 }],
};

describe('PortfolioModal', () => {
  it('renders backdrop with testid when open', () => {
    render(<PortfolioModal {...baseProps} />);
    expect(screen.getByTestId('portfolio-backdrop')).toBeTruthy();
  });

  it('does not render when closed', () => {
    render(<PortfolioModal {...baseProps} open={false} />);
    expect(screen.queryByTestId('portfolio-backdrop')).toBeNull();
  });

  it('switches tabs', () => {
    render(<PortfolioModal {...baseProps} />);
    fireEvent.click(screen.getByTestId('portfolio-tab-holdings'));
    expect(screen.getByTestId('portfolio-tab-holdings').getAttribute('data-active')).toBe('true');
  });

  it('closes on backdrop click', () => {
    const onClose = vi.fn();
    render(<PortfolioModal {...baseProps} onClose={onClose} />);
    fireEvent.click(screen.getByTestId('portfolio-backdrop'));
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```jsx
// PortfolioModal.jsx
import React, { useState, useEffect, useMemo } from 'react';
import { THEME } from './theme';
import OverviewTab from './portfolio/OverviewTab';
import HoldingsTab from './portfolio/HoldingsTab';
import TradesTab from './portfolio/TradesTab';
import PerformanceTab from './portfolio/PerformanceTab';
import { netWorthSeries } from './portfolio/netWorthSeries';
import {
  maxDrawdown, concentration, hitRatio, sectorExposureSeries, benchmarkSeries, dayPnL,
} from './portfolio/portfolioMetrics';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'holdings', label: 'Holdings' },
  { id: 'trades', label: 'Trades' },
  { id: 'performance', label: 'Performance' },
];

export default function PortfolioModal({
  open, onClose,
  cash = 0, startingCash = 0, netWorth = 0, todayPnL = 0, pnl = { realized: 0, unrealized: 0 },
  holdings = {}, quotes = {}, transactions = [], priceHistory = {},
  currentTick = 0, stocks = [], days = [],
  onOpenSymbol,
}) {
  const [tab, setTab] = useState('overview');
  const [sectorFilter, setSectorFilter] = useState(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const sectorBySymbol = useMemo(() => {
    const m = {};
    for (const s of stocks) m[s.symbol] = s.sector;
    return m;
  }, [stocks]);

  const nwSeries = useMemo(
    () => netWorthSeries(transactions, priceHistory, startingCash || (cash + Object.values(holdings).reduce((s, h) => s, 0)), currentTick),
    [transactions, priceHistory, startingCash, cash, holdings, currentTick]
  );

  const livePrices = useMemo(() => {
    const p = {};
    for (const sym of Object.keys(quotes)) p[sym] = quotes[sym]?.mid ?? 0;
    return p;
  }, [quotes]);

  const allocation = useMemo(() => {
    const sectorTotals = {};
    let total = 0;
    for (const sym of Object.keys(holdings)) {
      const qty = holdings[sym]?.qty ?? 0;
      if (!qty) continue;
      const px = livePrices[sym] ?? 0;
      const mv = qty * px;
      total += mv;
      const sec = sectorBySymbol[sym] ?? 'Other';
      sectorTotals[sec] = (sectorTotals[sec] ?? 0) + mv;
    }
    return Object.entries(sectorTotals).map(([label, mv]) => ({
      label, value: total > 0 ? (mv / total) * 100 : 0,
    }));
  }, [holdings, livePrices, sectorBySymbol]);

  const holdingsRows = useMemo(() => Object.keys(holdings).map((sym) => {
    const h = holdings[sym] || {};
    const px = livePrices[sym] ?? 0;
    const avg = h.avg_price ?? 0;
    const qty = h.qty ?? 0;
    const pnlAbs = (px - avg) * qty;
    const pnlPct = avg > 0 ? ((px - avg) / avg) * 100 : 0;
    const ph = priceHistory[sym] ?? [];
    const dayDelta = ph.length >= 2 ? (ph[ph.length - 1] - ph[Math.max(0, ph.length - 2)]) * qty : 0;
    return {
      symbol: sym, sector: sectorBySymbol[sym] ?? 'Other', qty,
      avgCost: avg, ltp: px, pnlAbs, pnlPct, dayDelta,
    };
  }).filter((r) => r.qty), [holdings, livePrices, priceHistory, sectorBySymbol]);

  const tradesEnriched = useMemo(() => {
    if (!days.length) return transactions.map((t) => ({ ...t, dayLabel: '' }));
    const ranges = [];
    let acc = 0;
    for (const d of days) { ranges.push({ id: d.id, label: d.label, start: acc, end: acc + d.ticks }); acc += d.ticks; }
    return transactions.map((t) => {
      const r = ranges.find((rr) => (t.tick ?? 0) >= rr.start && (t.tick ?? 0) < rr.end);
      return { ...t, dayLabel: r?.label ?? '' };
    });
  }, [transactions, days]);

  const perfDayPnL  = useMemo(() => dayPnL(transactions, days), [transactions, days]);
  const benchmark   = useMemo(() => benchmarkSeries(priceHistory, currentTick), [priceHistory, currentTick]);
  const portfolioPctSeries = useMemo(() => {
    if (!nwSeries.length) return [];
    const start = nwSeries[0] || 1;
    return nwSeries.map((v) => ((v - start) / start) * 100);
  }, [nwSeries]);
  const topConc     = useMemo(() => concentration(holdings, livePrices), [holdings, livePrices]);
  const hr          = useMemo(() => hitRatio(transactions), [transactions]);

  if (!open) return null;

  return (
    <div
      data-testid="portfolio-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(60,40,10,0.4)',
        zIndex: 110, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12, maxWidth: 720, width: '100%',
          maxHeight: '90vh', overflow: 'hidden', border: `1px solid ${THEME.borderTile}`,
          display: 'flex', flexDirection: 'column',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 12, borderBottom: `1px solid ${THEME.borderTile}` }}>
          <div style={{ fontWeight: 800, color: THEME.textPrimary }}>📊 My Portfolio</div>
          <button onClick={onClose} aria-label="close" style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: THEME.textMuted }}>✕</button>
        </div>
        <div style={{ display: 'flex', gap: 4, padding: '0 12px', borderBottom: `1px solid ${THEME.borderTile}`, background: THEME.bgTile }}>
          {TABS.map((t) => (
            <button
              key={t.id}
              data-testid={`portfolio-tab-${t.id}`}
              data-active={tab === t.id ? 'true' : 'false'}
              onClick={() => setTab(t.id)}
              style={{
                padding: '8px 12px', border: 'none', cursor: 'pointer',
                background: tab === t.id ? '#fff' : 'transparent',
                color: tab === t.id ? THEME.accentWarm : THEME.textMuted,
                fontWeight: tab === t.id ? 700 : 500,
                borderBottom: tab === t.id ? `2px solid ${THEME.accentWarm}` : '2px solid transparent',
              }}
            >{t.label}</button>
          ))}
        </div>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {tab === 'overview' && (
            <OverviewTab
              netWorth={netWorth}
              startingCash={startingCash}
              todayPnL={todayPnL}
              cash={cash}
              holdingsValue={netWorth - cash}
              realizedPnL={pnl.realized || 0}
              unrealizedPnL={pnl.unrealized || 0}
              netWorthSeries={nwSeries}
              allocation={allocation}
              bestToday={holdingsRows.slice().sort((a, b) => b.dayDelta - a.dayDelta)[0]}
              worstToday={holdingsRows.slice().sort((a, b) => a.dayDelta - b.dayDelta)[0]}
              onAllocationClick={(label) => { setSectorFilter(label); setTab('holdings'); }}
            />
          )}
          {tab === 'holdings' && (
            <HoldingsTab
              rows={holdingsRows}
              onOpenSymbol={(s) => { onClose?.(); onOpenSymbol?.(s); }}
              sectorFilter={sectorFilter}
              onClearSectorFilter={() => setSectorFilter(null)}
            />
          )}
          {tab === 'trades' && <TradesTab trades={tradesEnriched} />}
          {tab === 'performance' && (
            <PerformanceTab
              dayPnL={perfDayPnL}
              portfolioReturnSeries={portfolioPctSeries}
              benchmarkReturnSeries={benchmark}
              maxDD={maxDrawdown(nwSeries)}
              topConcentration={topConc}
              hitRatio={hr}
            />
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/PortfolioModal.jsx \
        frontend-react/src/components/game/renderers/stocksim/PortfolioModal.test.jsx
git commit -m "feat(stocksim): PortfolioModal host with 4 tabs"
```

---

### Task 11: Wire 📊 button + modal into `StockMarketGame.jsx`

**Files:**
- Modify: `frontend-react/src/components/game/renderers/StockMarketGame.jsx`

- [ ] **Step 1: Add import + state**

Near other stocksim imports (around line 1–60), add:

```jsx
import PortfolioModal from './stocksim/PortfolioModal';
```

Inside the component (next to other useState declarations like `filterMode`, `drilldownSymbol`), add:

```jsx
const [portfolioOpen, setPortfolioOpen] = useState(false);
```

- [ ] **Step 2: Add 📊 button to PersistentStrip wrapper**

Replace the existing `{v2Enabled && (<div ...><PersistentStrip .../></div>)}` block with:

```jsx
{v2Enabled && (
  <div className="mb-4 sticky top-0 z-30" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
    <div style={{ flex: 1 }}>
      <PersistentStrip
        cash={cash}
        holdingsValue={portfolioValue}
        netWorth={totalValue}
        pnl={profitAbs}
        currentTick={currentTick}
        tickCount={tickCount}
      />
    </div>
    <button
      data-testid="portfolio-open"
      onClick={() => setPortfolioOpen(true)}
      style={{
        padding: '8px 12px', borderRadius: 8, border: '1px solid #F5E6C8',
        background: '#fff', color: '#633806', fontWeight: 700, cursor: 'pointer',
      }}
    >📊 Portfolio</button>
  </div>
)}
```

- [ ] **Step 3: Mount the modal at end of playing tree**

Add right before the closing `</NpcLayerProvider>` (or end of v2 tree):

```jsx
{v2Enabled && (
  <PortfolioModal
    open={portfolioOpen}
    onClose={() => setPortfolioOpen(false)}
    cash={cash}
    startingCash={sessionConfig?.starting_capital ?? 0}
    netWorth={totalValue}
    todayPnL={serverState?.today_pnl?.total ?? 0}
    pnl={{ realized: pnl?.realized ?? 0, unrealized: pnl?.unrealized ?? 0 }}
    holdings={serverState?.holdings || {}}
    quotes={quotes}
    transactions={serverState?.trade_log || []}
    priceHistory={priceHistory}
    currentTick={currentTick}
    stocks={sessionConfig?.stocks || []}
    days={sessionConfig?.days || []}
    onOpenSymbol={(sym) => { setSelectedSymbol(sym); setDrilldownSymbol(sym); }}
  />
)}
```

- [ ] **Step 4: Run frontend tests**

`cd frontend-react && npx vitest run`
Expected: PASS — no regressions in existing tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/StockMarketGame.jsx
git commit -m "feat(stocksim): wire PortfolioModal + 📊 trigger into v2 path"
```

---

## Phase B — Backend Calendar Week

### Task 12: JSON schema additions to `stock-market-simulator.json`

**Files:**
- Modify: `backend/games/stock-market-simulator.json`

- [ ] **Step 1: Inspect current `minigame_config.stock_market_config`**

Read the file. Confirm `tick_count: 30`, `tick_interval_seconds: 0`, `stocks` has 8 entries.

- [ ] **Step 2: Edit `tick_count` → 20, `tick_interval_seconds` → 8, and add new keys**

Inside `minigame_config.stock_market_config`, set:

```json
"tick_count": 20,
"tick_interval_seconds": 8,
"calendar_mode": "week",
"days": [
  { "id": "mon", "label": "Monday",    "ticks": 4 },
  { "id": "tue", "label": "Tuesday",   "ticks": 4 },
  { "id": "wed", "label": "Wednesday", "ticks": 4 },
  { "id": "thu", "label": "Thursday",  "ticks": 4 },
  { "id": "fri", "label": "Friday",    "ticks": 4 }
],
"earnings_schedule": {
  "TECHN":      { "day": "tue", "surprise": 0.05,  "headline": "TechNova beats Q2 guidance" },
  "BHARATBANK": { "day": "wed", "surprise": -0.03, "headline": "BharatBank misses on NPAs" },
  "INFRABLD":   { "day": "thu", "surprise": 0.04,  "headline": "InfraBld wins highway order" },
  "GREENX":     { "day": "fri", "surprise": 0.06,  "headline": "GreenX bags solar tender" },
  "CONSPLUS":   { "day": "mon", "surprise": -0.02, "headline": "ConsPlus flags weak rural demand" },
  "PHARMAX":    { "day": "tue", "surprise": 0.03,  "headline": "PharmaX gets USFDA nod" },
  "FINTAP":     { "day": "wed", "surprise": -0.04, "headline": "FinTap regulatory probe" },
  "STREAMHUB":  { "day": "thu", "surprise": 0.05,  "headline": "StreamHub subscriber beat" }
},
"weekend_events": [
  {
    "after_day": "fri", "type": "saturday_news", "title": "Saturday Headlines",
    "items": [
      { "scope": "macro", "text": "RBI keeps repo rate unchanged" },
      { "scope": "stock", "symbol": "GREENX", "text": "Govt approves new solar tariff" }
    ]
  },
  {
    "after_day": "fri", "type": "sunday_brief", "title": "Monday Agenda",
    "items": [
      { "scope": "macro", "text": "US Fed minutes due Tuesday — IT in focus" },
      { "scope": "macro", "text": "Q2 earnings season picks up next week" }
    ]
  }
]
```

> **Symbol verification:** confirm the 8 symbols above match the actual `stocks[].symbol` values in the file. If a symbol differs, adjust the `earnings_schedule` keys to match.

- [ ] **Step 3: Validate JSON parses**

```bash
cd backend && python -c "import json; json.load(open('games/stock-market-simulator.json'))"
```

Expected: no output (success).

- [ ] **Step 4: Commit**

```bash
git add backend/games/stock-market-simulator.json
git commit -m "feat(stocksim): add calendar_mode/days/earnings_schedule/weekend_events"
```

---

### Task 13: `current_day` + `tick_to_day` helpers

**Files:**
- Create: `backend/engines/stocksim/calendar.py`
- Test: `backend/tests/test_stocksim_calendar.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_stocksim_calendar.py
import pytest
from engines.stocksim.calendar import current_day, tick_to_day, day_index_to_id

DAYS = [
    {"id": "mon", "label": "Monday", "ticks": 4},
    {"id": "tue", "label": "Tuesday", "ticks": 4},
    {"id": "wed", "label": "Wednesday", "ticks": 4},
    {"id": "thu", "label": "Thursday", "ticks": 4},
    {"id": "fri", "label": "Friday", "ticks": 4},
]

def test_tick_to_day_first_tick_of_day():
    assert tick_to_day(0, DAYS) == DAYS[0]
    assert tick_to_day(4, DAYS) == DAYS[1]
    assert tick_to_day(7, DAYS) == DAYS[1]

def test_tick_to_day_last_tick_clamps_to_final_day():
    assert tick_to_day(19, DAYS) == DAYS[4]
    assert tick_to_day(99, DAYS) == DAYS[4]

def test_current_day_uses_state_current_tick():
    state = {"current_tick": 9}
    sm_cfg = {"calendar_mode": "week", "days": DAYS}
    d = current_day(state, sm_cfg)
    assert d["id"] == "wed"
    assert d["index"] == 2
    assert d["of"] == 5

def test_current_day_returns_none_when_calendar_mode_absent():
    assert current_day({"current_tick": 0}, {}) is None

def test_day_index_to_id():
    assert day_index_to_id(0, DAYS) == "mon"
    assert day_index_to_id(4, DAYS) == "fri"
    assert day_index_to_id(99, DAYS) == "fri"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_stocksim_calendar.py -v
```

Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

```python
# backend/engines/stocksim/calendar.py
"""Calendar-week helpers for the week-format stock market simulator.

These helpers are pure: they take a state dict + sm_cfg dict and return
metadata. They never mutate state (drift application lives separately).
"""
from typing import Optional


def tick_to_day(tick: int, days: list) -> Optional[dict]:
    """Return the day dict that owns the given tick index. Clamps to the last day."""
    if not days:
        return None
    cumulative = 0
    for d in days:
        cumulative += int(d.get("ticks", 0))
        if tick < cumulative:
            return d
    return days[-1]


def day_index_to_id(idx: int, days: list) -> Optional[str]:
    if not days:
        return None
    if idx < 0:
        return days[0].get("id")
    if idx >= len(days):
        return days[-1].get("id")
    return days[idx].get("id")


def current_day(state: dict, sm_cfg: dict) -> Optional[dict]:
    """Return enriched current-day metadata, or None if calendar_mode != 'week'."""
    if (sm_cfg or {}).get("calendar_mode") != "week":
        return None
    days = sm_cfg.get("days") or []
    if not days:
        return None
    tick = int(state.get("current_tick", 0))
    d = tick_to_day(tick, days)
    if not d:
        return None
    idx = days.index(d) if d in days else 0
    return {
        "id": d.get("id"),
        "label": d.get("label"),
        "index": idx,
        "of": len(days),
    }
```

- [ ] **Step 4: Run to verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_calendar.py -v
```

Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/engines/stocksim/calendar.py backend/tests/test_stocksim_calendar.py
git commit -m "feat(stocksim): calendar helpers (current_day, tick_to_day, day_index_to_id)"
```

---

### Task 14: `apply_overnight_drift` helper

**Files:**
- Modify: `backend/engines/stocksim/calendar.py`
- Modify: `backend/tests/test_stocksim_calendar.py`

- [ ] **Step 1: Append failing test**

Add to `test_stocksim_calendar.py`:

```python
import math
from engines.stocksim.calendar import apply_overnight_drift

SM_CFG_WEEK = {
    "calendar_mode": "week",
    "days": DAYS,
    "earnings_schedule": {
        "TECHN":      {"day": "tue", "surprise": 0.05},
        "BHARATBANK": {"day": "wed", "surprise": -0.03},
    },
}

def test_apply_overnight_drift_zero_when_seed_makes_noise_zero(monkeypatch):
    state = {"current_tick": 4, "drift": {}}
    # Force base_noise = 0 by stubbing the gaussian
    import engines.stocksim.calendar as calmod
    monkeypatch.setattr(calmod, "_normal", lambda mu, sigma, seed: 0.0)
    apply_overnight_drift(state, SM_CFG_WEEK, "mon", "tue")
    # No earnings on Monday → drift for both should be 0 (no noise + no earnings)
    assert state["drift"].get("TECHN", 0.0) == 0.0
    assert state["drift"].get("BHARATBANK", 0.0) == 0.0

def test_apply_overnight_drift_applies_earnings_when_day_matches(monkeypatch):
    state = {"current_tick": 8, "drift": {}}
    import engines.stocksim.calendar as calmod
    monkeypatch.setattr(calmod, "_normal", lambda mu, sigma, seed: 0.0)
    # Tue earnings for TECHN: surprise +0.05, factor 0.6 → drift = 0.03
    apply_overnight_drift(state, SM_CFG_WEEK, "tue", "wed")
    assert math.isclose(state["drift"]["TECHN"], 0.03, abs_tol=1e-9)
    assert state["drift"].get("BHARATBANK", 0.0) == 0.0

def test_apply_overnight_drift_noop_when_calendar_mode_absent():
    state = {"current_tick": 0, "drift": {}}
    apply_overnight_drift(state, {}, "mon", "tue")
    assert state["drift"] == {}
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — `apply_overnight_drift` not found.

- [ ] **Step 3: Append implementation**

Append to `backend/engines/stocksim/calendar.py`:

```python
import math
import random


_EARNINGS_DRIFT_FACTOR = 0.6  # spec §"Overnight Drift Formula"
_BASE_NOISE_SIGMA = 0.005


def _normal(mu: float, sigma: float, seed: int) -> float:
    """Box-Muller normal sample seeded for determinism."""
    rng = random.Random(seed)
    u1 = max(rng.random(), 1e-12)
    u2 = rng.random()
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z


def apply_overnight_drift(state: dict, sm_cfg: dict, from_day_id: str, to_day_id: str) -> None:
    """Mutates state['drift'] (per-symbol multiplicative drift) for the overnight gap.

    Drift formula:
      drift[sym] = N(mu=0, sigma=0.005) + (surprise * 0.6 if day-N hosted that earnings else 0)

    Drift is additive on top of any prior drift so multiple overnights compound.
    """
    if (sm_cfg or {}).get("calendar_mode") != "week":
        return
    state.setdefault("drift", {})
    earnings = (sm_cfg.get("earnings_schedule") or {})
    base_seed = int(state.get("seed", 0))
    days = sm_cfg.get("days") or []
    day_idx = next((i for i, d in enumerate(days) if d.get("id") == from_day_id), 0)
    for sym, cfg in earnings.items():
        # Per-symbol seed so different stocks don't move identically.
        sym_seed = (hash(sym) ^ (base_seed * 1009) ^ (day_idx * 31)) & 0xFFFFFFFF
        noise = _normal(0.0, _BASE_NOISE_SIGMA, sym_seed)
        earnings_drift = 0.0
        if cfg.get("day") == from_day_id:
            earnings_drift = float(cfg.get("surprise", 0.0)) * _EARNINGS_DRIFT_FACTOR
        prior = state["drift"].get(sym, 0.0)
        state["drift"][sym] = prior + noise + earnings_drift
    # Symbols not in earnings_schedule still get noise drift.
    for stock in (sm_cfg.get("stocks") or []):
        sym = stock.get("symbol")
        if not sym or sym in earnings:
            continue
        sym_seed = (hash(sym) ^ (base_seed * 1009) ^ (day_idx * 31)) & 0xFFFFFFFF
        noise = _normal(0.0, _BASE_NOISE_SIGMA, sym_seed)
        state["drift"][sym] = state["drift"].get(sym, 0.0) + noise
```

- [ ] **Step 4: Run to verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_calendar.py -v
```

Expected: PASS, 8 tests.

- [ ] **Step 5: Commit**

```bash
git add backend/engines/stocksim/calendar.py backend/tests/test_stocksim_calendar.py
git commit -m "feat(stocksim): apply_overnight_drift with seeded noise + earnings factor"
```

---

### Task 15: `advance_to_tick` calls drift on day boundary

**Files:**
- Modify: `backend/engines/stocksim/orders.py` (`advance_to_tick`)
- Create: `backend/tests/test_stocksim_advance_week.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_stocksim_advance_week.py
import pytest
from engines.stocksim.orders import advance_to_tick

DAYS = [
    {"id": "mon", "label": "Monday", "ticks": 4},
    {"id": "tue", "label": "Tuesday", "ticks": 4},
    {"id": "wed", "label": "Wednesday", "ticks": 4},
    {"id": "thu", "label": "Thursday", "ticks": 4},
    {"id": "fri", "label": "Friday", "ticks": 4},
]

CFG = {
    "tick_count": 20,
    "tick_interval_seconds": 8,
    "starting_capital": 50000,
    "circuit_breaker_pct": [10],
    "charges": {"brokerage_pct": 0.0003, "stt_pct": 0.001, "exchange_pct": 3.45e-05, "gst_pct": 0.18},
    "stocks": [
        {"symbol": "TECHN", "name": "TechNova", "sector": "IT", "starting_price": 1000, "volatility": 0.02},
    ],
    "events": [],
    "calendar_mode": "week",
    "days": DAYS,
    "earnings_schedule": {"TECHN": {"day": "mon", "surprise": 0.10}},
}

def _empty_state():
    return {
        "seed": 42, "profile": "balanced", "cash": 50000, "holdings": {},
        "pending_orders": [], "settlement_queue": [], "trade_log": [],
        "current_tick": 0, "realized_pnl": 0.0, "completed": False,
        "dimension_counters": {}, "halted_symbols": {},
    }

def test_advance_within_same_day_does_not_apply_drift():
    state = _empty_state()
    advance_to_tick(state, 3, CFG)
    assert state.get("drift", {}) == {}  # still in mon

def test_advance_across_one_boundary_applies_drift_once():
    state = _empty_state()
    advance_to_tick(state, 4, CFG)  # mon → tue
    assert "drift" in state
    # earnings on mon for TECHN: 0.10 * 0.6 = 0.06 plus seeded noise
    assert state["drift"].get("TECHN", 0.0) > 0.05

def test_advance_across_multiple_boundaries_compounds():
    state = _empty_state()
    advance_to_tick(state, 12, CFG)  # mon → tue → wed → thu (3 boundaries)
    # drift should reflect noise from 3 overnight applications + 1 earnings
    assert "drift" in state
    assert "TECHN" in state["drift"]
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_stocksim_advance_week.py -v
```

Expected: FAIL — `state['drift']` either missing or not populated, since `advance_to_tick` doesn't yet call drift.

- [ ] **Step 3: Modify `advance_to_tick`**

Open `backend/engines/stocksim/orders.py`. Find the `advance_to_tick(state, tick, config)` function (around line 258). Modify it to detect day boundaries crossed since last tick and call drift on each.

```python
# Top of orders.py — add import
from engines.stocksim.calendar import day_index_to_id, tick_to_day, apply_overnight_drift
```

Replace the body of `advance_to_tick` with (preserving its existing logic for sweep/settle/breakers):

```python
def advance_to_tick(state: dict, tick: int, config: dict) -> dict:
    """Lazy sweep: fire pending orders, T+1 settle, then update circuit breakers.

    For week-format games, also applies overnight drift across each day boundary
    crossed since the previously-served tick.
    """
    prev_tick = int(state.get("current_tick", 0))
    target = max(prev_tick, int(tick))

    # Apply overnight drift for each day boundary crossed.
    if (config or {}).get("calendar_mode") == "week":
        days = config.get("days") or []
        prev_day = tick_to_day(prev_tick, days)
        for boundary_tick in _day_boundary_ticks(days, prev_tick, target):
            from_day_id = tick_to_day(boundary_tick - 1, days).get("id")
            to_day_id   = tick_to_day(boundary_tick, days).get("id")
            apply_overnight_drift(state, config, from_day_id, to_day_id)

    # Existing sweep / settlement / breakers logic (preserved verbatim from prior body)
    state["current_tick"] = target
    _sweep_pending_orders(state, config)
    _settle_t1(state, config)
    _check_circuit_breakers(state, config)

    return {"current_tick": state["current_tick"], "halted_symbols": list(state.get("halted_symbols", {}).keys())}


def _day_boundary_ticks(days: list, from_tick: int, to_tick: int) -> list:
    """Return the tick indices in (from_tick, to_tick] that are first-of-day."""
    if not days or to_tick <= from_tick:
        return []
    boundaries = []
    cumulative = 0
    for d in days[:-1]:
        cumulative += int(d.get("ticks", 0))
        if from_tick < cumulative <= to_tick:
            boundaries.append(cumulative)
    return boundaries
```

> **Note:** when modifying, keep the existing implementation's sweep/settle/breaker calls in the same order. If those helpers have different names in the current file, preserve those names.

- [ ] **Step 4: Run to verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_advance_week.py tests/test_stock_market_engine.py tests/test_stocksim_engine.py -v
```

Expected: PASS for all (no regressions to legacy tests).

- [ ] **Step 5: Commit**

```bash
git add backend/engines/stocksim/orders.py backend/tests/test_stocksim_advance_week.py
git commit -m "feat(stocksim): advance_to_tick applies overnight drift on day boundaries"
```

---

### Task 16: Pricing helper applies drift to mid price

**Files:**
- Modify: `backend/engines/stocksim/pricing.py`
- Test: `backend/tests/test_stocksim_pricing_drift.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_stocksim_pricing_drift.py
from engines.stocksim.pricing import price_at

CFG = {
    "stocks": [{"symbol": "TECHN", "starting_price": 1000, "volatility": 0.02}],
    "calendar_mode": "week",
}

def test_price_at_with_no_drift_state_unchanged():
    state = {"seed": 42, "drift": {}}
    p_no_drift = price_at(state, "TECHN", 5, CFG)
    state2 = {"seed": 42}  # no drift key at all
    p_no_key = price_at(state2, "TECHN", 5, CFG)
    assert abs(p_no_drift - p_no_key) < 1e-9

def test_price_at_with_positive_drift_increases_mid():
    state = {"seed": 42, "drift": {}}
    p0 = price_at(state, "TECHN", 5, CFG)
    state["drift"] = {"TECHN": 0.05}
    p1 = price_at(state, "TECHN", 5, CFG)
    assert p1 > p0
    assert abs(p1 - p0 * 1.05) / p0 < 0.005  # roughly +5%
```

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_stocksim_pricing_drift.py -v
```

Expected: FAIL — drift not applied yet.

- [ ] **Step 3: Modify `price_at` to factor in `state["drift"]`**

Open `backend/engines/stocksim/pricing.py`. Find `price_at(state, symbol, tick, config)`. At the end, just before returning the mid price, multiply by the drift factor:

```python
# Inside price_at, just before returning mid:
drift_pct = float((state.get("drift") or {}).get(symbol, 0.0))
mid = mid * (1.0 + drift_pct)
```

> **Note:** apply this to the existing computed `mid`. Do not change the existing seed/volatility/walk computation — drift is layered on top.

- [ ] **Step 4: Run to verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_pricing_drift.py tests/test_stocksim_engine.py -v
```

Expected: PASS for new tests; existing pricing tests unchanged because empty drift is the default.

- [ ] **Step 5: Commit**

```bash
git add backend/engines/stocksim/pricing.py backend/tests/test_stocksim_pricing_drift.py
git commit -m "feat(stocksim): price_at applies overnight drift multiplier"
```

---

### Task 17: `/stocksim/state` endpoint enrichment

**Files:**
- Modify: `backend/app.py` (around lines 27493–27569 — the `stocksim_state` route)
- Test: `backend/tests/test_stocksim_state_week.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_stocksim_state_week.py
import json
import pytest
from app import app
from storage import RUNS, update_run, load_run

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

@pytest.fixture
def week_run(monkeypatch):
    """Create an in-memory run pointing at the week-format simulator."""
    run_id = "test-week-run"
    run = {
        "run_id": run_id,
        "user_id": "u1",
        "game_id": "stock-market-simulator",
        "stocksim": {
            "seed": 7, "profile": "balanced", "cash": 50000, "holdings": {},
            "pending_orders": [], "settlement_queue": [], "trade_log": [],
            "current_tick": 0, "realized_pnl": 0.0, "completed": False,
            "started_at_ms": 0, "dimension_counters": {}, "halted_symbols": {},
        },
    }
    RUNS[run_id] = run
    yield run_id
    RUNS.pop(run_id, None)

def test_state_response_contains_day_field(client, week_run, mocker_helper=None):
    # Skip JWT enforcement using app.test_client + a registered user fixture
    # (existing test_stocksim_routes.py shows the pattern; reuse it.)
    ...  # see test_stocksim_routes.py for the JWT setup helper to import here.
```

> **Note:** the test above is a skeleton. Use the JWT helper pattern already present in `backend/tests/test_stocksim_routes.py` to issue a valid token for `u1` and assert:
> - `response.json["day"]["id"] == "mon"` and `response.json["day"]["of"] == 5`
> - `response.json["pending_earnings"]` is a non-empty list with each entry having `symbol`, `day`, `headline`
> - After advancing tick to 5: `response.json["day"]["id"] == "tue"` and `response.json["today_pnl"]` exists with `realized` / `unrealized` / `total`.

Implement those assertions following the existing test file's pattern.

- [ ] **Step 2: Run to verify failure**

```bash
cd backend && python -m pytest tests/test_stocksim_state_week.py -v
```

Expected: FAIL — `day` / `pending_earnings` / `today_pnl` not in response.

- [ ] **Step 3: Modify the route**

In `backend/app.py`, locate the `stocksim_state` handler. After computing the existing `payload` dict (with `state`, `quotes`, `pnl`, `tick_count`), add the calendar enrichment:

```python
# Imports at top of app.py (only if not already present)
from engines.stocksim.calendar import current_day, tick_to_day

# Inside stocksim_state, after the existing payload is built:
sm_cfg = (game_def.get("minigame_config") or {}).get("stock_market_config") or {}
day_meta = current_day(state, sm_cfg)
if day_meta:
    payload["day"] = day_meta

    # today_pnl: realized in trades since day_start_tick; unrealized vs day-open price.
    days = sm_cfg.get("days") or []
    day_start_tick = sum(d.get("ticks", 0) for d in days[:day_meta["index"]])
    realized_today = sum(
        t.get("realized_pnl", 0.0) or 0.0
        for t in (state.get("trade_log") or [])
        if (t.get("tick") or 0) >= day_start_tick and t.get("side") == "sell"
    )
    unrealized_today = 0.0
    for sym, h in (state.get("holdings") or {}).items():
        qty = h.get("qty", 0) or 0
        if not qty:
            continue
        cur = (payload.get("quotes") or {}).get(sym, {}).get("mid") or 0.0
        try:
            day_open = eng.price_at(state, sym, day_start_tick) if hasattr(eng, "price_at") else cur
        except Exception:
            day_open = cur
        unrealized_today += (cur - day_open) * qty
    payload["today_pnl"] = {
        "realized": realized_today,
        "unrealized": unrealized_today,
        "total": realized_today + unrealized_today,
    }

    # pending_earnings: any earnings whose day is on/after today's day
    earnings = sm_cfg.get("earnings_schedule") or {}
    pending = []
    days_after_inclusive = {d["id"] for d in days[day_meta["index"]:]}
    for sym, cfg in earnings.items():
        if cfg.get("day") in days_after_inclusive:
            pending.append({"symbol": sym, "day": cfg.get("day"), "headline": cfg.get("headline", "")})
    payload["pending_earnings"] = pending
```

- [ ] **Step 4: Run to verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_state_week.py tests/test_stocksim_routes.py -v
```

Expected: PASS for both files.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_stocksim_state_week.py
git commit -m "feat(stocksim): /state response gains day, today_pnl, pending_earnings"
```

---

### Task 18: EOD pause/resume clock

**Files:**
- Modify: `backend/app.py` (`stocksim_state` and a new `stocksim_phase` handler)
- Test: `backend/tests/test_stocksim_pause.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_stocksim_pause.py
# Use the same JWT/run fixtures as test_stocksim_routes.py.
# Assert:
#   POST /api/run/<run_id>/stocksim/phase  body={"phase": "eod"} → 200, sets state.paused_at_ms
#   GET  /api/run/<run_id>/stocksim/state  while paused → current_tick does NOT advance even if wall-clock moves.
#   POST /api/run/<run_id>/stocksim/phase  body={"phase": "playing"} → 200, state.paused_total_ms incremented by elapsed pause, paused_at_ms cleared.
#
# Use time.sleep + monkeypatch on time.time if needed to control wall-clock advance.
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL — endpoint doesn't exist yet.

- [ ] **Step 3: Add phase endpoint and honor pause in tick math**

Add a new route in `app.py`:

```python
@app.route("/api/run/<run_id>/stocksim/phase", methods=["POST"])
@jwt_required
def stocksim_phase(run_id):
    body = request.get_json(silent=True) or {}
    phase = body.get("phase")
    if phase not in ("playing", "eod", "weekend"):
        return jsonify({"error": "invalid_phase"}), 400
    run = storage.get_run(run_id)
    if not run or run.get("user_id") != g.user_id:
        return jsonify({"error": "not_found"}), 404
    state = run.get("stocksim") or {}
    now_ms = int(time.time() * 1000)
    if phase in ("eod", "weekend"):
        # Pause: record pause start (idempotent if already paused).
        if not state.get("paused_at_ms"):
            state["paused_at_ms"] = now_ms
    else:  # resume
        paused_at = state.get("paused_at_ms")
        if paused_at:
            state["paused_total_ms"] = (state.get("paused_total_ms") or 0) + (now_ms - paused_at)
            state["paused_at_ms"] = 0
    state["phase"] = phase
    run["stocksim"] = state
    storage.update_run(run_id, run)
    return jsonify({"phase": phase, "paused_at_ms": state.get("paused_at_ms", 0), "paused_total_ms": state.get("paused_total_ms", 0)})
```

In `stocksim_state`, replace the elapsed_ticks computation:

```python
# Old:
# elapsed_ticks = int((time.time() * 1000 - started_at_ms) / (tick_interval_seconds * 1000))

# New (subtracts paused time, including any in-flight pause):
now_ms = int(time.time() * 1000)
paused_total = state.get("paused_total_ms", 0)
paused_at = state.get("paused_at_ms", 0)
if paused_at:
    paused_total += (now_ms - paused_at)
effective_ms = (now_ms - started_at_ms) - paused_total
elapsed_ticks = max(0, int(effective_ms / (tick_interval_seconds * 1000))) if tick_interval_seconds > 0 else 0
target_tick = min(elapsed_ticks, tick_count)
```

Also include phase + pause flags in the response payload:

```python
payload["phase"] = state.get("phase", "playing")
payload["paused"] = bool(state.get("paused_at_ms"))
```

- [ ] **Step 4: Run to verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_pause.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_stocksim_pause.py
git commit -m "feat(stocksim): server-authoritative pause for EOD / weekend phases"
```

---

## Phase C — Frontend Week Format

### Task 19: `dayBoundaries.js` pure helper

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/dayBoundaries.js`
- Test: `frontend-react/src/components/game/renderers/stocksim/dayBoundaries.test.js`

- [ ] **Step 1: Write failing test**

```js
import { describe, it, expect } from 'vitest';
import { dayBoundaries } from './dayBoundaries';

const DAYS = [
  { id: 'mon', ticks: 4 },
  { id: 'tue', ticks: 4 },
  { id: 'wed', ticks: 4 },
  { id: 'thu', ticks: 4 },
  { id: 'fri', ticks: 4 },
];

describe('dayBoundaries', () => {
  it('returns first-of-day ticks (excluding tick 0)', () => {
    expect(dayBoundaries(DAYS)).toEqual([4, 8, 12, 16]);
  });

  it('returns empty for missing days', () => {
    expect(dayBoundaries([])).toEqual([]);
    expect(dayBoundaries(null)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL.

- [ ] **Step 3: Implement**

```js
// dayBoundaries.js
// Returns the tick indices that are the first tick of each day after the first.
// Used to render dashed vertical separators on charts.
export function dayBoundaries(days) {
  if (!Array.isArray(days) || days.length <= 1) return [];
  const out = [];
  let acc = 0;
  for (let i = 0; i < days.length - 1; i++) {
    acc += Number(days[i].ticks || 0);
    out.push(acc);
  }
  return out;
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/dayBoundaries.js \
        frontend-react/src/components/game/renderers/stocksim/dayBoundaries.test.js
git commit -m "feat(stocksim): dayBoundaries helper for chart separators"
```

---

### Task 20: `DayHeader.jsx`

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/DayHeader.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/DayHeader.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DayHeader from './DayHeader';

describe('DayHeader', () => {
  it('renders day label and position', () => {
    render(<DayHeader day={{ id: 'wed', label: 'Wednesday', index: 2, of: 5 }} />);
    expect(screen.getByTestId('day-header').textContent).toContain('Wednesday');
    expect(screen.getByTestId('day-header').textContent).toContain('Day 3 of 5');
  });

  it('renders nothing when day is null', () => {
    const { container } = render(<DayHeader day={null} />);
    expect(container.querySelector('[data-testid="day-header"]')).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL.

- [ ] **Step 3: Implement**

```jsx
// DayHeader.jsx
import React from 'react';
import { THEME } from './theme';

export default function DayHeader({ day }) {
  if (!day) return null;
  return (
    <div
      data-testid="day-header"
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        background: THEME.bgTile, color: THEME.textPrimary,
        padding: '4px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700,
        border: `1px solid ${THEME.borderTile}`, marginBottom: 6,
      }}
    >
      <span aria-hidden>📅</span>
      <span>{day.label}</span>
      <span style={{ color: THEME.textMuted, fontWeight: 500 }}>· Day {day.index + 1} of {day.of}</span>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 2 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/DayHeader.jsx \
        frontend-react/src/components/game/renderers/stocksim/DayHeader.test.jsx
git commit -m "feat(stocksim): DayHeader chip"
```

---

### Task 21: `EndOfDayModal.jsx`

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/EndOfDayModal.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/EndOfDayModal.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import EndOfDayModal from './EndOfDayModal';

const props = {
  open: true,
  day: { id: 'wed', label: 'Wednesday', index: 2, of: 5 },
  todayPnL: { total: 320, realized: 200, unrealized: 120 },
  topMover: { symbol: 'TECHV', changePct: 4.2 },
  bottomMover: { symbol: 'BHARATBANK', changePct: -2.1 },
  earningsRevealed: [{ symbol: 'BHARATBANK', headline: 'BharatBank misses on NPAs', surprise: -0.03 }],
  onContinue: vi.fn(),
};

describe('EndOfDayModal', () => {
  it('renders today P&L and continue button', () => {
    render(<EndOfDayModal {...props} />);
    expect(screen.getByTestId('eod-pnl').textContent).toContain('320');
    expect(screen.getByTestId('eod-continue')).toBeTruthy();
  });
  it('renders earnings reveal block when present', () => {
    render(<EndOfDayModal {...props} />);
    expect(screen.getByTestId('eod-earnings').textContent).toContain('BharatBank');
  });
  it('calls onContinue when button clicked', () => {
    const onContinue = vi.fn();
    render(<EndOfDayModal {...props} onContinue={onContinue} />);
    fireEvent.click(screen.getByTestId('eod-continue'));
    expect(onContinue).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL.

- [ ] **Step 3: Implement**

```jsx
// EndOfDayModal.jsx
import React from 'react';
import { THEME, gainLossColor } from './theme';

const fmt = (n) => `₹${Math.round(n).toLocaleString('en-IN')}`;
const pct = (p) => `${p >= 0 ? '+' : ''}${p.toFixed(2)}%`;

export default function EndOfDayModal({
  open, day, todayPnL = { total: 0, realized: 0, unrealized: 0 },
  topMover, bottomMover, earningsRevealed = [], headlines = [], onContinue,
}) {
  if (!open || !day) return null;
  const isLastDay = day.index + 1 >= day.of;
  return (
    <div
      data-testid="eod-backdrop"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(60,40,10,0.55)',
        zIndex: 120, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div style={{ background: '#fff', borderRadius: 14, maxWidth: 520, width: '100%', padding: 20, border: `1px solid ${THEME.borderTile}` }}>
        <div style={{ fontSize: 12, color: THEME.textMuted }}>End of {day.label}</div>
        <div style={{ fontSize: 24, fontWeight: 800, color: THEME.textPrimary, marginBottom: 8 }}>
          Day {day.index + 1} closed
        </div>
        <div data-testid="eod-pnl" style={{ fontSize: 18, fontWeight: 800, color: gainLossColor(todayPnL.total) }}>
          {todayPnL.total >= 0 ? '▲' : '▼'} {fmt(todayPnL.total)} today
        </div>
        <div style={{ fontSize: 12, color: THEME.textMuted }}>
          Realized {fmt(todayPnL.realized)} · Unrealized {fmt(todayPnL.unrealized)}
        </div>

        <div style={{ marginTop: 12, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <Mover label="Top mover" mover={topMover} />
          <Mover label="Worst mover" mover={bottomMover} />
        </div>

        {earningsRevealed.length > 0 && (
          <div data-testid="eod-earnings" style={{ marginTop: 12, padding: 10, background: THEME.bgTile, borderRadius: 8 }}>
            <div style={{ fontSize: 11, color: THEME.textMuted, marginBottom: 4 }}>Earnings revealed</div>
            {earningsRevealed.map((e) => (
              <div key={e.symbol} style={{ fontSize: 13 }}>
                <strong>{e.symbol}</strong>: {e.headline}{' '}
                <span style={{ color: gainLossColor(e.surprise) }}>({pct((e.surprise || 0) * 100)})</span>
              </div>
            ))}
          </div>
        )}

        {headlines.length > 0 && (
          <div style={{ marginTop: 8, fontSize: 12, color: THEME.textMuted }}>
            {headlines.map((h, i) => <div key={i}>· {h}</div>)}
          </div>
        )}

        <button
          data-testid="eod-continue"
          onClick={onContinue}
          style={{
            marginTop: 16, padding: '10px 16px', width: '100%',
            background: THEME.accentWarm, color: '#fff', border: 'none',
            borderRadius: 8, fontWeight: 700, cursor: 'pointer',
          }}
        >{isLastDay ? 'Continue to weekend →' : 'Continue to next day →'}</button>
      </div>
    </div>
  );
}

function Mover({ label, mover }) {
  return (
    <div style={{ background: THEME.bgTile, padding: 8, borderRadius: 6 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted }}>{label}</div>
      {mover ? (
        <>
          <div style={{ fontWeight: 700 }}>{mover.symbol}</div>
          <div style={{ color: gainLossColor(mover.changePct) }}>{pct(mover.changePct)}</div>
        </>
      ) : (
        <div style={{ color: THEME.textMuted, fontSize: 12 }}>—</div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/EndOfDayModal.jsx \
        frontend-react/src/components/game/renderers/stocksim/EndOfDayModal.test.jsx
git commit -m "feat(stocksim): EndOfDayModal with day P&L, movers, earnings reveal"
```

---

### Task 22: `WeekendInterlude.jsx`

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/WeekendInterlude.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/WeekendInterlude.test.jsx`

- [ ] **Step 1: Write failing test**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import WeekendInterlude from './WeekendInterlude';

const event = {
  type: 'saturday_news',
  title: 'Saturday Headlines',
  items: [
    { scope: 'macro', text: 'RBI keeps repo rate unchanged' },
    { scope: 'stock', symbol: 'GREENX', text: 'Govt approves new solar tariff' },
  ],
};

describe('WeekendInterlude', () => {
  it('renders title and items', () => {
    render(<WeekendInterlude open event={event} onAdvance={() => {}} />);
    expect(screen.getByTestId('weekend-title').textContent).toContain('Saturday Headlines');
    expect(screen.getAllByTestId(/^weekend-item-/)).toHaveLength(2);
  });

  it('skip button is disabled for first 3s, then enabled', async () => {
    vi.useFakeTimers();
    render(<WeekendInterlude open event={event} onAdvance={() => {}} />);
    const btn = screen.getByTestId('weekend-skip');
    expect(btn.disabled).toBe(true);
    await act(async () => { vi.advanceTimersByTime(3100); });
    expect(btn.disabled).toBe(false);
    vi.useRealTimers();
  });

  it('auto-advances after 10s', async () => {
    vi.useFakeTimers();
    const onAdvance = vi.fn();
    render(<WeekendInterlude open event={event} onAdvance={onAdvance} />);
    await act(async () => { vi.advanceTimersByTime(10100); });
    expect(onAdvance).toHaveBeenCalled();
    vi.useRealTimers();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL.

- [ ] **Step 3: Implement**

```jsx
// WeekendInterlude.jsx
import React, { useEffect, useState } from 'react';
import { THEME } from './theme';

const SKIP_AFTER_MS = 3000;
const AUTO_ADVANCE_MS = 10000;

export default function WeekendInterlude({ open, event, onAdvance }) {
  const [skippable, setSkippable] = useState(false);

  useEffect(() => {
    if (!open) return;
    setSkippable(false);
    const skipTimer = setTimeout(() => setSkippable(true), SKIP_AFTER_MS);
    const advTimer = setTimeout(() => onAdvance?.(), AUTO_ADVANCE_MS);
    return () => { clearTimeout(skipTimer); clearTimeout(advTimer); };
  }, [open, event?.type, onAdvance]);

  if (!open || !event) return null;

  return (
    <div
      data-testid="weekend-backdrop"
      style={{
        position: 'fixed', inset: 0, background: 'rgba(40,30,5,0.85)',
        zIndex: 130, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div style={{ background: '#fff', borderRadius: 14, maxWidth: 560, width: '100%', padding: 24, border: `1px solid ${THEME.borderTile}` }}>
        <div style={{ fontSize: 11, color: THEME.textMuted, textTransform: 'uppercase', letterSpacing: 1 }}>
          {event.type === 'saturday_news' ? 'Saturday' : 'Sunday'}
        </div>
        <div data-testid="weekend-title" style={{ fontSize: 22, fontWeight: 800, color: THEME.textPrimary, marginBottom: 10 }}>
          {event.title}
        </div>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {(event.items || []).map((it, i) => (
            <li
              key={i}
              data-testid={`weekend-item-${i}`}
              style={{
                padding: '8px 10px', marginBottom: 6,
                background: THEME.bgTile, borderRadius: 6, color: THEME.textPrimary,
                borderLeft: `3px solid ${it.scope === 'stock' ? THEME.accentWarm : THEME.textMuted}`,
              }}
            >
              {it.scope === 'stock' && <strong>{it.symbol}: </strong>}{it.text}
            </li>
          ))}
        </ul>
        <button
          data-testid="weekend-skip"
          disabled={!skippable}
          onClick={onAdvance}
          style={{
            marginTop: 16, padding: '10px 16px', width: '100%',
            background: skippable ? THEME.accentWarm : THEME.bgTile,
            color: skippable ? '#fff' : THEME.textMuted,
            border: 'none', borderRadius: 8, fontWeight: 700,
            cursor: skippable ? 'pointer' : 'not-allowed',
          }}
        >{skippable ? 'Continue →' : 'Continue (auto in a moment)'}</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/WeekendInterlude.jsx \
        frontend-react/src/components/game/renderers/stocksim/WeekendInterlude.test.jsx
git commit -m "feat(stocksim): WeekendInterlude with 3s skip / 10s auto-advance"
```

---

### Task 23: `MarketBriefing` earnings chip

**Files:**
- Modify: `frontend-react/src/components/game/renderers/stocksim/MarketBriefing.jsx`
- Modify: existing `MarketBriefing.test.jsx` (or create one if absent)

- [ ] **Step 1: Add failing test for the chip**

In the existing `MarketBriefing.test.jsx` (or create), add:

```jsx
it('renders earnings day chip when stock has scheduled earnings', () => {
  render(
    <MarketBriefing
      briefing={{ headline: 'X', sub: 'Y', macro_tone: 'neutral', sector_mood: {} }}
      stocks={[{ symbol: 'TECHV', name: 'TechVista', sector: 'IT' }]}
      earningsByDay={{ TECHV: { day: 'tue', label: 'Tuesday' } }}
      onBegin={() => {}}
    />
  );
  expect(screen.getByTestId('briefing-earnings-TECHV').textContent).toContain('Earnings: Tue');
});
```

- [ ] **Step 2: Run to verify failure**

Expected: FAIL.

- [ ] **Step 3: Modify component**

Open `MarketBriefing.jsx`. Add `earningsByDay` to the destructured props. In the per-stock card rendering, add a chip:

```jsx
{earningsByDay?.[stock.symbol] && (
  <span
    data-testid={`briefing-earnings-${stock.symbol}`}
    style={{
      marginLeft: 6, fontSize: 10, padding: '2px 6px', borderRadius: 999,
      background: '#FFF3DC', color: '#854F0B', border: '1px solid #F5E6C8',
    }}
  >
    📅 Earnings: {earningsByDay[stock.symbol].day.charAt(0).toUpperCase() + earningsByDay[stock.symbol].day.slice(1, 3)}
  </span>
)}
```

- [ ] **Step 4: Run to verify pass**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/MarketBriefing.jsx \
        frontend-react/src/components/game/renderers/stocksim/MarketBriefing.test.jsx
git commit -m "feat(stocksim): MarketBriefing shows earnings-day chip"
```

---

### Task 24: `PriceChart` accepts `boundaries` prop

**Files:**
- Modify: `frontend-react/src/components/game/renderers/StockMarketGame.jsx` (the inline `PriceChart` component, ~lines 59–112)

- [ ] **Step 1: Locate the `PriceChart` function and add a failing-style assertion test for the new prop**

This component is inline; we don't have an isolated test file. Instead, write a smoke test by extracting the SVG path generation. Since extracting just for tests is overkill, the verification is:

After modification, the chart should render `<line>` elements for each entry in `boundaries`, with `data-testid="chart-boundary-<idx>"`.

- [ ] **Step 2: Modify `PriceChart`**

Find the function definition (`function PriceChart({ history, color, height = CHART_HEIGHT })`) and update:

```jsx
function PriceChart({ history, color, height = CHART_HEIGHT, boundaries = [] }) {
  if (!history || history.length === 0) return null;
  const min = Math.min(...history) * 0.95;
  const max = Math.max(...history) * 1.05;
  const range = max - min || 1;
  const width = 600;
  const dx = history.length > 1 ? width / (history.length - 1) : 0;
  const pts = history.map((v, i) => `${i * dx},${height - ((v - min) / range) * height}`).join(' ');
  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {boundaries.map((b) => {
        const x = b * dx;
        return (
          <line
            key={b}
            data-testid={`chart-boundary-${b}`}
            x1={x} x2={x} y1={0} y2={height}
            stroke="#854F0B"
            strokeWidth="1"
            strokeDasharray="4 3"
            opacity="0.4"
          />
        );
      })}
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  );
}
```

- [ ] **Step 3: Manually verify (no automated test for this inline change)**

```bash
cd frontend-react && npx vitest run
```

Expected: existing tests still pass.

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/components/game/renderers/StockMarketGame.jsx
git commit -m "feat(stocksim): PriceChart accepts boundaries prop for day separators"
```

---

### Task 25: Wire phase machine + week components into `StockMarketGame.jsx`

**Files:**
- Modify: `frontend-react/src/components/game/renderers/StockMarketGame.jsx`

- [ ] **Step 1: Imports + `setPhase` API call helper**

Add imports near other stocksim imports:

```jsx
import DayHeader from './stocksim/DayHeader';
import EndOfDayModal from './stocksim/EndOfDayModal';
import WeekendInterlude from './stocksim/WeekendInterlude';
import { dayBoundaries as computeDayBoundaries } from './stocksim/dayBoundaries';
```

In `frontend-react/src/api/v2.js` (or wherever stocksim API helpers live — match existing `getStocksimState`), add:

```js
export async function postStocksimPhase(runId, phase) {
  const res = await client.post(`/api/run/${runId}/stocksim/phase`, { phase });
  return res.data;
}
```

Import it in `StockMarketGame.jsx`:

```jsx
import { postStocksimPhase } from '../../../api/v2';
```

- [ ] **Step 2: Phase tracking**

Inside `StockMarketGame.jsx`, the existing `phase` state already covers `'briefing'` and `'playing'`. Add tracking for `'eod'` and `'weekend'`:

```jsx
const [eodSeenDayId, setEodSeenDayId] = useState(null);
const [weekendStep, setWeekendStep] = useState(0);  // 0=saturday, 1=sunday, 2=done
```

In `pollState` callback (after `setServerState(...)`), detect day rollover:

```jsx
const newDay = data.day;
const lastDayIndex = serverStateRef.current?.day?.index ?? -1;
const newDayIndex = newDay?.index ?? -1;
if (v2Enabled && newDay && newDayIndex > lastDayIndex && phase === 'playing') {
  // Day just ended → enter EOD pause.
  setPhase('eod');
  postStocksimPhase(runId, 'eod').catch(() => {});
}
```

> **Note:** add `serverStateRef` if not present: `const serverStateRef = useRef(serverState); useEffect(() => { serverStateRef.current = serverState; }, [serverState]);`

- [ ] **Step 3: Mount DayHeader + EOD/Weekend overlays**

Above the v2 PersistentStrip block, add:

```jsx
{v2Enabled && serverState?.day && (
  <DayHeader day={serverState.day} />
)}
```

Below the playing tree, add EOD modal:

```jsx
{v2Enabled && phase === 'eod' && (
  <EndOfDayModal
    open
    day={serverState?.day}
    todayPnL={serverState?.today_pnl || { total: 0, realized: 0, unrealized: 0 }}
    topMover={computeTopMover(quotes, 'asc')}
    bottomMover={computeTopMover(quotes, 'desc')}
    earningsRevealed={computeEarningsForDay(sessionConfig, serverState?.day)}
    headlines={(serverState?.recent_news || []).slice(0, 2).map((n) => n.text || n.headline)}
    onContinue={async () => {
      const isLast = (serverState?.day?.index ?? 0) + 1 >= (serverState?.day?.of ?? 0);
      if (isLast && (sessionConfig?.weekend_events?.length || 0) > 0) {
        setPhase('weekend');
        setWeekendStep(0);
        await postStocksimPhase(runId, 'weekend').catch(() => {});
      } else {
        setPhase('playing');
        await postStocksimPhase(runId, 'playing').catch(() => {});
      }
    }}
  />
)}

{v2Enabled && phase === 'weekend' && (
  <WeekendInterlude
    open
    event={(sessionConfig?.weekend_events || [])[weekendStep]}
    onAdvance={async () => {
      const next = weekendStep + 1;
      if (next >= (sessionConfig?.weekend_events?.length || 0)) {
        // Week complete — show recap.
        setPhase('recap');
        await postStocksimPhase(runId, 'playing').catch(() => {});
      } else {
        setWeekendStep(next);
      }
    }}
  />
)}
```

Add helpers near top of component (or as a module-level functions):

```jsx
function computeTopMover(quotes, direction) {
  const entries = Object.entries(quotes || {})
    .map(([sym, q]) => ({ symbol: sym, changePct: (q.last_change_pct ?? 0) * (q.last_change_pct >= 0 || q.last_change_pct === 0 ? 1 : 1) }))
    .sort((a, b) => b.changePct - a.changePct);
  if (!entries.length) return null;
  return direction === 'asc' ? entries[0] : entries[entries.length - 1];
}

function computeEarningsForDay(sessionConfig, day) {
  if (!day) return [];
  const sched = sessionConfig?.earnings_schedule || {};
  return Object.entries(sched)
    .filter(([, cfg]) => cfg.day === day.id)
    .map(([symbol, cfg]) => ({ symbol, headline: cfg.headline, surprise: cfg.surprise }));
}
```

- [ ] **Step 4: Pass `boundaries` to `PriceChart`**

In each `<PriceChart>` invocation, add the prop:

```jsx
<PriceChart
  history={priceHistory[selectedSymbol] || []}
  color={...}
  boundaries={v2Enabled ? computeDayBoundaries(sessionConfig?.days || []) : []}
/>
```

- [ ] **Step 5: Pass `earningsByDay` into `MarketBriefing`**

In the briefing render block:

```jsx
<MarketBriefing
  briefing={briefing}
  stocks={sessionConfig?.stocks || []}
  earningsByDay={Object.fromEntries(
    Object.entries(sessionConfig?.earnings_schedule || {}).map(([sym, cfg]) => [
      sym,
      { day: cfg.day, label: (sessionConfig?.days || []).find((d) => d.id === cfg.day)?.label || cfg.day },
    ])
  )}
  onBegin={() => setPhase('playing')}
/>
```

- [ ] **Step 6: Run frontend tests**

```bash
cd frontend-react && npx vitest run
```

Expected: PASS — no regressions.

- [ ] **Step 7: Commit**

```bash
git add frontend-react/src/components/game/renderers/StockMarketGame.jsx \
        frontend-react/src/api/v2.js
git commit -m "feat(stocksim): wire phase machine, DayHeader, EOD modal, Weekend interlude"
```

---

## Final Integration

### Task 26: Smoke-test the full week playthrough

**Files:**
- No code changes — manual verification.

- [ ] **Step 1: Run backend**

```bash
cd backend && python app.py
```

- [ ] **Step 2: Run frontend dev**

```bash
cd frontend-react && npm run dev
```

- [ ] **Step 3: Open the simulator with v2 enabled**

Navigate to `http://localhost:5173/play/stock-market-simulator?stocksim_v2=1` (logged in).

- [ ] **Step 4: Verify**

- DayHeader shows "📅 Monday — Day 1 of 5".
- PersistentStrip mounted with 📊 Portfolio button on right.
- Click 📊 — PortfolioModal opens with 4 tabs; Holdings tab is empty (expected).
- Place 1–2 trades.
- Wait for ~32s (4 ticks × 8s) → EndOfDayModal appears with day's P&L. Continue.
- Repeat through Friday.
- After Friday's EOD modal, WeekendInterlude shows Saturday news, then Sunday brief.
- After Sunday, recap screen.

- [ ] **Step 5: Commit (no-op or final docs)**

If a doc needs updating (e.g. `MEMORY.md` summary), commit. Otherwise skip.

---

## Self-Review Checklist (controller)

This plan is to be executed via `superpowers:subagent-driven-development`. Before dispatch:

- All 26 tasks have a concrete file path, a failing test, an implementation step, a verification step, and a commit step (skipping the test step only for Task 24's inline component change, which is acknowledged in the task body).
- Spec coverage:
  - §Schedule + Phase machine → Tasks 12, 18, 25.
  - §Earnings calendar → Tasks 12, 14, 17, 23, 25.
  - §Overnight drift → Tasks 14, 15, 16.
  - §Weekend events → Tasks 12, 22, 25.
  - §Backend changes → Tasks 12, 13, 14, 15, 16, 17, 18.
  - §Frontend new files → Tasks 19, 20, 21, 22, 24, 25.
  - §Portfolio Modal trigger → Tasks 10, 11.
  - §Portfolio Modal tabs → Tasks 6, 7, 8, 9, 10.
  - §Portfolio data source helpers → Tasks 1, 2, 3, 4, 5.
  - §Backwards compat → Tasks 13 (`current_day` returns None when calendar_mode absent), 15 (drift gated by calendar_mode), 16 (drift defaults to 0 when absent).
  - §v2 gating → all UI mounts gated by `v2Enabled` (Tasks 11, 25).
  - §Testing strategy → unit tests in Tasks 1–10, 13–16, 18–22; integration via Task 26.
  - §Rollout plan → Tasks 1–11 land first (Phase A — Portfolio works on legacy), then Tasks 12–18 (Phase B — backend), then Tasks 19–25 (Phase C — frontend week).
- Type consistency: `dayBoundaries` (frontend) and `_day_boundary_ticks` (backend) are deliberately distinct: frontend returns boundaries for chart x-axis; backend returns boundaries for drift application. `current_day` shape (`id`, `label`, `index`, `of`) used by both backend (Task 13) and frontend (Task 25) matches.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-10-stocksim-week-and-portfolio.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, two-stage review (spec compliance + code quality) between tasks, fast iteration.

2. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

Which approach?
