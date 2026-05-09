# Stocksim v2 UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-skin both stock games to the warm-amber Mento simulation theme, add a 6-tab company drill-down, four NPC personas, persistent cash strip, position sizer, watchlist, mid-game mentor check-in, and an end-of-game trade autopsy — all behind the `stocksim_v2_ui` feature flag.

**Architecture:** Additive frontend orchestration. `StockMarketGame.jsx` becomes a ~400-line orchestrator. New components live in `frontend-react/src/components/game/renderers/stocksim/`. Backend additions are minimal: `last_reason` stamping on quotes, an image route, enriched trade log on completion, optional fundamentals/peers/about/briefing in game JSON. Server stays authoritative for ticks and prices.

**Tech Stack:** React 18 + Vite + framer-motion + react-i18next + Tailwind + inline style tokens (frontend); Flask + `engines/stocksim/*` + `story_image_service.py` (backend); Vitest + React Testing Library (frontend tests); pytest (backend tests).

**Spec:** `docs/superpowers/specs/2026-05-09-stocksim-v2-ui-design.md`

---

## File Structure

**New folder:** `frontend-react/src/components/game/renderers/stocksim/`

| File | Purpose |
|---|---|
| `theme.js` | Single source of warm-amber palette tokens. |
| `MarketBriefing.jsx` | Stock-specific 30-sec pre-game intro (replaces `OnboardingFlow`). |
| `PersistentStrip.jsx` | Sticky Cash · Holdings · Net Worth · P&L · Tick bar. |
| `StockCard.jsx` | Per-stock tile (extracted from `StockMarketGame.jsx`). Adds star, why-moving chip, lazy AI thumb. |
| `StockListFilters.jsx` | Filter chip row: All / Gainers / Losers / Mine / ⭐. |
| `CompanyDrillDown.jsx` | Modal shell that hosts the 6 tab files. |
| `tabs/ChartTab.jsx` | Larger chart with MA-20 + RSI overlay. |
| `tabs/FundamentalsTab.jsx` | Valuation / Profitability / Size / Quarterly / Ranges + Analyst NPC. |
| `tabs/TechnicalsTab.jsx` | RSI dial, support/resistance, MA crossover. |
| `tabs/NewsTab.jsx` | Per-stock news log + Journalist NPC lines. |
| `tabs/PeersTab.jsx` | 3-row sector comparison table. |
| `tabs/AboutTab.jsx` | AI hero image + business description + key people. |
| `OrderTicket.jsx` (extend) | Add live position sizer + Target/Stop chips + Broker NPC. |
| `NpcLayer.jsx` | Single mounted NPC dispatcher (Provider + `useNpc()` hook). |
| `MentorCheckIn.jsx` | One-shot mid-game banner. |
| `TradeAutopsy.jsx` | Recap-screen card. |
| `npcDialog.js` | Pure: persona/signal → i18n key + props. |
| `technicals.js` | Pure: RSI, MA, support/resistance, crossover. |
| `autopsy.js` | Pure: pickBestTrade, pickWorstTrade, lessons. |

**Touched files:**

- `frontend-react/src/components/game/renderers/StockMarketGame.jsx` (slim down to orchestrator, behind flag).
- `frontend-react/src/components/game/renderers/stocksim/{DepthLadder,EventOverlay,NewsTickerStrip,PortfolioPanel}.jsx` (re-skin only).
- `frontend-react/src/locales/{en,hi}.json` (new `stocksim.*` keys).
- `frontend-react/package.json` + `vitest.config.js` + `vite.config.js` (test setup).
- `backend/app.py` (new image route, ensure `last_reason` echoed on `/state`).
- `backend/engines/stocksim/events.py` (stamp `recent_reasons`).
- `backend/engines/stocksim/scoring.py` (emit `trade_log_enriched`).
- `backend/schemas.py` (extend `_validate_stock_market_minigame`).
- `backend/games/stock-market-day-trader.json`, `backend/games/stock-market-simulator.json` (add fundamentals/peers/about/briefing/image_prompt + per-event `reason`).
- `backend/tests/test_stocksim_engine.py`, `backend/tests/test_stocksim_routes.py` (extend).
- `frontend-react/test-stocksim-e2e.mjs` (extend smoke).

---

## Task 0: Test framework setup

**Files:**
- Modify: `frontend-react/package.json`
- Create: `frontend-react/vitest.config.js`
- Create: `frontend-react/src/tests/setup.js`

The existing `frontend-react/src/tests/stocksimPricing.test.js` already uses vitest syntax but `vitest` is not in `package.json`. Install it plus `@testing-library/react` so the rest of the plan can TDD components and pure modules.

- [ ] **Step 1: Add dev dependencies**

```bash
cd frontend-react && npm install --save-dev vitest@^2.1.4 @testing-library/react@^16.0.1 @testing-library/jest-dom@^6.5.0 jsdom@^25.0.1
```

Expected: `package.json` updates `devDependencies` and `package-lock.json` regenerates. No runtime install errors.

- [ ] **Step 2: Add `test` script**

In `frontend-react/package.json`, edit the `scripts` block:

```json
"scripts": {
  "dev": "vite",
  "build": "vite build",
  "lint": "eslint .",
  "preview": "vite preview",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

- [ ] **Step 3: Create `vitest.config.js`**

Create `frontend-react/vitest.config.js`:

```js
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: false,
    setupFiles: ['./src/tests/setup.js'],
    include: ['src/**/*.test.{js,jsx}'],
  },
});
```

- [ ] **Step 4: Create `setup.js`**

Create `frontend-react/src/tests/setup.js`:

```js
import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
});
```

Notes:
- Use the `/vitest` entry point of `@testing-library/jest-dom`, not the root entry. With `globals: false` (set in `vitest.config.js`), the root entry throws `ReferenceError: expect is not defined` because it expects a Jest-style global. The `/vitest` entry imports `expect` from vitest and calls `expect.extend(...)` itself.
- Explicitly register `afterEach(cleanup)`. RTL only auto-registers cleanup when vitest globals are enabled. With `globals: false` we must register it ourselves, otherwise tests with multiple `it()` blocks find duplicated DOM nodes from the prior render.

- [ ] **Step 5: Verify existing tests still run**

Run: `cd frontend-react && npm test`
Expected: `stocksimPricing.test.js` passes. Other `.test.js` files either pass or fail-with-actual-assertion (not framework-missing).

If any existing test fails, do not fix here — record the failures in the commit message and continue. They are out of scope.

- [ ] **Step 6: Commit**

```bash
git add frontend-react/package.json frontend-react/package-lock.json frontend-react/vitest.config.js frontend-react/src/tests/setup.js
git commit -m "chore(frontend): add vitest + @testing-library/react for stocksim v2 UI tests"
```

---

## Task 1: Theme tokens + re-skin existing stocksim files

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/theme.js`
- Test: `frontend-react/src/components/game/renderers/stocksim/theme.test.js`
- Modify: `frontend-react/src/components/game/renderers/stocksim/DepthLadder.jsx`
- Modify: `frontend-react/src/components/game/renderers/stocksim/EventOverlay.jsx`
- Modify: `frontend-react/src/components/game/renderers/stocksim/NewsTickerStrip.jsx`
- Modify: `frontend-react/src/components/game/renderers/stocksim/PortfolioPanel.jsx`

- [ ] **Step 1: Write the failing test**

Create `frontend-react/src/components/game/renderers/stocksim/theme.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { THEME, gainLossColor } from './theme';

describe('stocksim theme', () => {
  it('exposes the warm-amber palette tokens', () => {
    expect(THEME.bgPage).toBe('#FFF9EE');
    expect(THEME.bgTile).toBe('#FFF3DC');
    expect(THEME.borderTile).toBe('#F5E6C8');
    expect(THEME.textPrimary).toBe('#633806');
    expect(THEME.textMuted).toBe('#854F0B');
    expect(THEME.accentWarm).toBe('#B46B1E');
    expect(THEME.gain).toBe('#0F6E56');
    expect(THEME.loss).toBe('#A32D2D');
    expect(THEME.neutral).toBe('#633806');
  });

  it('gainLossColor returns gain for positive, loss for negative, neutral for zero', () => {
    expect(gainLossColor(1.5)).toBe(THEME.gain);
    expect(gainLossColor(-0.01)).toBe(THEME.loss);
    expect(gainLossColor(0)).toBe(THEME.neutral);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/theme.test.js`
Expected: FAIL — module `./theme` not found.

- [ ] **Step 3: Implement `theme.js`**

Create `frontend-react/src/components/game/renderers/stocksim/theme.js`:

```js
export const THEME = Object.freeze({
  bgPage: '#FFF9EE',
  bgTile: '#FFF3DC',
  borderTile: '#F5E6C8',
  textPrimary: '#633806',
  textMuted: '#854F0B',
  accentWarm: '#B46B1E',
  gain: '#0F6E56',
  loss: '#A32D2D',
  neutral: '#633806',
});

export function gainLossColor(value) {
  if (value > 0) return THEME.gain;
  if (value < 0) return THEME.loss;
  return THEME.neutral;
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/theme.test.js`
Expected: PASS, 2 tests.

- [ ] **Step 5: Re-skin `DepthLadder.jsx`**

Open `frontend-react/src/components/game/renderers/stocksim/DepthLadder.jsx`. Add at top:

```js
import { THEME } from './theme';
```

Replace any hard-coded blue/red palette (e.g. `#dbeafe`, `#ef4444`, `#10b981`, `#fef9c3`, `#1e40af`) with theme tokens:

- bid rows / "buy" green → `THEME.gain`
- ask rows / "sell" red → `THEME.loss`
- container background → `THEME.bgTile`
- container border → `THEME.borderTile`
- header / label text → `THEME.textMuted`
- body text → `THEME.textPrimary`

Use inline `style={{ ... }}` to stay consistent with the simulation pattern (see `frontend-react/src/components/game/sim/CashflowStrip.jsx` for the canonical example).

- [ ] **Step 6: Re-skin `EventOverlay.jsx`**

Same approach. Banner background `THEME.bgTile`, left accent border `3px solid ${THEME.accentWarm}`, headline color `THEME.textPrimary`, sub copy `THEME.textMuted`.

- [ ] **Step 7: Re-skin `NewsTickerStrip.jsx`**

Strip background `THEME.bgTile`, ticker text `THEME.textPrimary`, scroll-rail border `THEME.borderTile`, leading 📰 icon color `THEME.accentWarm`.

- [ ] **Step 8: Re-skin `PortfolioPanel.jsx`**

Card background `THEME.bgTile`, border `THEME.borderTile`, P&L numbers via `gainLossColor(value)`, label text `THEME.textMuted`.

- [ ] **Step 9: Manual sanity check**

Run: `cd frontend-react && npm run build`
Expected: build succeeds. (No new lint errors from `npm run lint`.)

- [ ] **Step 10: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/theme.js \
        frontend-react/src/components/game/renderers/stocksim/theme.test.js \
        frontend-react/src/components/game/renderers/stocksim/DepthLadder.jsx \
        frontend-react/src/components/game/renderers/stocksim/EventOverlay.jsx \
        frontend-react/src/components/game/renderers/stocksim/NewsTickerStrip.jsx \
        frontend-react/src/components/game/renderers/stocksim/PortfolioPanel.jsx
git commit -m "feat(stocksim): warm-amber theme tokens + reskin existing stocksim components"
```

---

## Task 2: PersistentStrip

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/PersistentStrip.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/PersistentStrip.test.jsx`

- [ ] **Step 1: Write the failing test**

Create `frontend-react/src/components/game/renderers/stocksim/PersistentStrip.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PersistentStrip from './PersistentStrip';

describe('PersistentStrip', () => {
  const baseProps = {
    cash: 98925,
    holdingsValue: 1075,
    netWorth: 100000,
    pnl: 0.25,
    currentTick: 4,
    tickCount: 22,
  };

  it('renders all 5 cells with formatted values', () => {
    render(<PersistentStrip {...baseProps} />);
    expect(screen.getByText(/CASH/i)).toBeInTheDocument();
    expect(screen.getByText(/₹98,925/)).toBeInTheDocument();
    expect(screen.getByText(/HOLDINGS/i)).toBeInTheDocument();
    expect(screen.getByText(/₹1,075/)).toBeInTheDocument();
    expect(screen.getByText(/NET WORTH/i)).toBeInTheDocument();
    expect(screen.getByText(/₹1,00,000/)).toBeInTheDocument();
    expect(screen.getByText(/4 \/ 22/)).toBeInTheDocument();
  });

  it('formats negative P&L with red color and minus sign', () => {
    render(<PersistentStrip {...baseProps} pnl={-247.5} />);
    const pnlEl = screen.getByTestId('persistent-pnl');
    expect(pnlEl.textContent).toMatch(/-₹247\.50/);
    expect(pnlEl).toHaveStyle({ color: '#A32D2D' });
  });

  it('formats positive P&L with green color and plus sign', () => {
    render(<PersistentStrip {...baseProps} pnl={123.45} />);
    const pnlEl = screen.getByTestId('persistent-pnl');
    expect(pnlEl.textContent).toMatch(/\+₹123\.45/);
    expect(pnlEl).toHaveStyle({ color: '#0F6E56' });
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/PersistentStrip.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `PersistentStrip.jsx`**

Create `frontend-react/src/components/game/renderers/stocksim/PersistentStrip.jsx`:

```jsx
import React from 'react';
import { THEME, gainLossColor } from './theme';

function formatINR(n) {
  // Indian-grouped rupee format. e.g. 100000 -> "1,00,000"
  const sign = n < 0 ? '-' : '';
  const abs = Math.abs(Math.round(n));
  const s = String(abs);
  if (s.length <= 3) return `${sign}₹${s}`;
  const last3 = s.slice(-3);
  const rest = s.slice(0, -3);
  const grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
  return `${sign}₹${grouped},${last3}`;
}

function formatPnl(n) {
  const sign = n > 0 ? '+' : n < 0 ? '-' : '';
  const fixed = Math.abs(n).toFixed(2);
  return `${sign}₹${fixed}`;
}

export default function PersistentStrip({ cash, holdingsValue, netWorth, pnl, currentTick, tickCount }) {
  const cellLabel = { fontSize: 9, color: THEME.textMuted, letterSpacing: 0.5, fontWeight: 600 };
  const cellValue = { fontSize: 14, fontWeight: 800, color: THEME.textPrimary };
  return (
    <div
      style={{
        background: '#fff',
        border: `1px solid ${THEME.borderTile}`,
        borderRadius: 10,
        padding: '8px 12px',
        display: 'flex',
        justifyContent: 'space-between',
        gap: 12,
      }}
    >
      <div>
        <div style={cellLabel}>CASH</div>
        <div style={{ ...cellValue, color: THEME.textMuted }}>{formatINR(cash)}</div>
      </div>
      <div>
        <div style={cellLabel}>HOLDINGS</div>
        <div style={cellValue}>{formatINR(holdingsValue)}</div>
      </div>
      <div>
        <div style={cellLabel}>NET WORTH</div>
        <div style={{ ...cellValue, color: THEME.gain }}>{formatINR(netWorth)}</div>
      </div>
      <div>
        <div style={cellLabel}>P&amp;L</div>
        <div data-testid="persistent-pnl" style={{ ...cellValue, color: gainLossColor(pnl) }}>{formatPnl(pnl)}</div>
      </div>
      <div>
        <div style={cellLabel}>TICK</div>
        <div style={cellValue}>{currentTick} / {tickCount}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/PersistentStrip.test.jsx`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/PersistentStrip.jsx \
        frontend-react/src/components/game/renderers/stocksim/PersistentStrip.test.jsx
git commit -m "feat(stocksim): add PersistentStrip component for cash/pnl/tick bar"
```

---

## Task 3: StockListFilters + watchlist state

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/StockListFilters.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/StockListFilters.test.jsx`

- [ ] **Step 1: Write the failing test**

Create `frontend-react/src/components/game/renderers/stocksim/StockListFilters.test.jsx`:

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StockListFilters from './StockListFilters';

describe('StockListFilters', () => {
  const counts = { all: 8, gainers: 3, losers: 2, mine: 1, starred: 2 };

  it('renders 5 filter chips with counts', () => {
    render(<StockListFilters mode="all" counts={counts} setMode={() => {}} />);
    expect(screen.getByText(/All/)).toBeInTheDocument();
    expect(screen.getByText(/Gainers/)).toBeInTheDocument();
    expect(screen.getByText(/Losers/)).toBeInTheDocument();
    expect(screen.getByText(/Mine/)).toBeInTheDocument();
    expect(screen.getByText(/⭐/)).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
  });

  it('marks the active chip', () => {
    render(<StockListFilters mode="gainers" counts={counts} setMode={() => {}} />);
    const chip = screen.getByTestId('filter-gainers');
    expect(chip).toHaveAttribute('data-active', 'true');
  });

  it('calls setMode when chip clicked', () => {
    const setMode = vi.fn();
    render(<StockListFilters mode="all" counts={counts} setMode={setMode} />);
    fireEvent.click(screen.getByTestId('filter-losers'));
    expect(setMode).toHaveBeenCalledWith('losers');
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/StockListFilters.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `StockListFilters.jsx`**

Create `frontend-react/src/components/game/renderers/stocksim/StockListFilters.jsx`:

```jsx
import React from 'react';
import { THEME } from './theme';

const MODES = [
  { id: 'all', label: 'All' },
  { id: 'gainers', label: 'Gainers' },
  { id: 'losers', label: 'Losers' },
  { id: 'mine', label: 'Mine' },
  { id: 'starred', label: '⭐' },
];

export default function StockListFilters({ mode, counts = {}, setMode }) {
  return (
    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
      {MODES.map((m) => {
        const active = mode === m.id;
        return (
          <button
            key={m.id}
            data-testid={`filter-${m.id}`}
            data-active={active ? 'true' : 'false'}
            onClick={() => setMode(m.id)}
            style={{
              background: active ? THEME.accentWarm : THEME.bgTile,
              color: active ? '#fff' : THEME.textPrimary,
              border: `1px solid ${THEME.borderTile}`,
              borderRadius: 14,
              padding: '4px 10px',
              fontSize: 11,
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span>{m.label}</span>
            <span style={{ opacity: 0.8, fontSize: 10 }}>{counts[m.id] ?? 0}</span>
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/StockListFilters.test.jsx`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/StockListFilters.jsx \
        frontend-react/src/components/game/renderers/stocksim/StockListFilters.test.jsx
git commit -m "feat(stocksim): add StockListFilters chip row"
```

---

## Task 4: npcDialog.js + NpcLayer (Broker + Journalist)

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/npcDialog.js`
- Test: `frontend-react/src/components/game/renderers/stocksim/npcDialog.test.js`
- Create: `frontend-react/src/components/game/renderers/stocksim/NpcLayer.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/NpcLayer.test.jsx`

- [ ] **Step 1: Write the failing test for `npcDialog`**

Create `frontend-react/src/components/game/renderers/stocksim/npcDialog.test.js`:

```js
import { describe, it, expect } from 'vitest';
import {
  analystVerdict,
  journalistFlavor,
  brokerOnTrade,
  mentorCheckIn,
} from './npcDialog';

describe('npcDialog', () => {
  it('analystVerdict flags stretched valuation when pe > sector_pe + 10%', () => {
    const out = analystVerdict({ pe: 28.4, sector_pe: 24.0, roe: 22.1, debt_equity: 0.12 });
    expect(out.key).toBe('stocksim.npc.analyst.stretched');
    expect(out.props.premiumPct).toBe(18);
  });

  it('analystVerdict flags cheap when pe < sector_pe - 10%', () => {
    const out = analystVerdict({ pe: 18, sector_pe: 24, roe: 19, debt_equity: 0.5 });
    expect(out.key).toBe('stocksim.npc.analyst.cheap');
  });

  it('analystVerdict returns fair when within band', () => {
    const out = analystVerdict({ pe: 24, sector_pe: 24, roe: 18, debt_equity: 0.4 });
    expect(out.key).toBe('stocksim.npc.analyst.fair');
  });

  it('journalistFlavor returns key with headline + reason', () => {
    const out = journalistFlavor({
      tick: 4,
      headline: 'TechVista wins ₹500Cr cloud contract',
      reason: 'Large new contract → revenue visibility lifts price',
    });
    expect(out.key).toBe('stocksim.npc.journalist.flavor');
    expect(out.props.tick).toBe(4);
    expect(out.props.reason).toMatch(/revenue visibility/);
  });

  it('brokerOnTrade warns when riskPct > 20', () => {
    const out = brokerOnTrade({ side: 'buy', symbol: 'TECHV', qty: 100, price: 215 }, 25);
    expect(out.key).toBe('stocksim.npc.broker.high_risk');
    expect(out.props.riskPct).toBe(25);
  });

  it('brokerOnTrade is silent when riskPct < 5', () => {
    const out = brokerOnTrade({ side: 'buy', symbol: 'TECHV', qty: 1, price: 215 }, 2);
    expect(out).toBeNull();
  });

  it('mentorCheckIn keys off concentration in single sector', () => {
    const state = {
      positions: { TECHV: 50, INFOS: 30 },
      stocks_by_sector: { TECHV: 'IT', INFOS: 'IT' },
    };
    const out = mentorCheckIn(state);
    expect(out.key).toBe('stocksim.npc.mentor.concentrated');
    expect(out.props.sector).toBe('IT');
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/npcDialog.test.js`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `npcDialog.js`**

Create `frontend-react/src/components/game/renderers/stocksim/npcDialog.js`:

```js
// Pure functions: NPC signal + data → { key, props } for i18n.
// Returning { key, props } lets the consumer call t(key, props).
// Returning null means "no line at this signal".

export function analystVerdict({ pe, sector_pe, roe, debt_equity }) {
  if (pe == null || sector_pe == null) {
    return { key: 'stocksim.npc.analyst.fair', props: {} };
  }
  const premiumPct = Math.round(((pe - sector_pe) / sector_pe) * 100);
  if (premiumPct >= 10) {
    return { key: 'stocksim.npc.analyst.stretched', props: { premiumPct, pe, sectorPe: sector_pe } };
  }
  if (premiumPct <= -10) {
    return { key: 'stocksim.npc.analyst.cheap', props: { discountPct: -premiumPct, pe, sectorPe: sector_pe } };
  }
  return { key: 'stocksim.npc.analyst.fair', props: { pe, sectorPe: sector_pe, roe, debtEquity: debt_equity } };
}

export function journalistFlavor(newsItem) {
  if (!newsItem) return null;
  return {
    key: 'stocksim.npc.journalist.flavor',
    props: {
      tick: newsItem.tick,
      headline: newsItem.headline,
      reason: newsItem.reason || '',
    },
  };
}

export function brokerOnTrade(order, riskPct) {
  if (riskPct == null) return null;
  if (riskPct >= 20) {
    return { key: 'stocksim.npc.broker.high_risk', props: { riskPct: Math.round(riskPct), symbol: order.symbol } };
  }
  if (riskPct >= 10) {
    return { key: 'stocksim.npc.broker.moderate', props: { riskPct: Math.round(riskPct), symbol: order.symbol } };
  }
  return null;
}

export function mentorCheckIn(state) {
  const positions = state?.positions || {};
  const sectors = state?.stocks_by_sector || {};
  const sectorTotals = {};
  let total = 0;
  for (const [sym, qty] of Object.entries(positions)) {
    const sec = sectors[sym] || 'Other';
    sectorTotals[sec] = (sectorTotals[sec] || 0) + Math.abs(qty);
    total += Math.abs(qty);
  }
  if (total === 0) {
    return { key: 'stocksim.npc.mentor.no_trades', props: {} };
  }
  const dominant = Object.entries(sectorTotals).sort((a, b) => b[1] - a[1])[0];
  if (dominant && dominant[1] / total >= 0.7) {
    return { key: 'stocksim.npc.mentor.concentrated', props: { sector: dominant[0], pct: Math.round((dominant[1] / total) * 100) } };
  }
  return { key: 'stocksim.npc.mentor.diversified', props: {} };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/npcDialog.test.js`
Expected: PASS, 7 tests.

- [ ] **Step 5: Write the failing test for `NpcLayer`**

Create `frontend-react/src/components/game/renderers/stocksim/NpcLayer.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { NpcLayerProvider, useNpc } from './NpcLayer';

function Probe() {
  const npc = useNpc();
  return (
    <div>
      <button onClick={() => npc.say('broker', { key: 'stocksim.npc.broker.high_risk', props: { riskPct: 30, symbol: 'TECHV' } })}>broker</button>
      <button onClick={() => npc.say('journalist', { key: 'stocksim.npc.journalist.flavor', props: { tick: 4, headline: 'h', reason: 'r' } })}>journalist</button>
    </div>
  );
}

describe('NpcLayer', () => {
  it('renders only one NPC chip at a time', () => {
    render(
      <NpcLayerProvider currentTick={1}>
        <Probe />
      </NpcLayerProvider>
    );
    act(() => { screen.getByText('broker').click(); });
    expect(screen.getAllByTestId('npc-chip').length).toBe(1);
    act(() => { screen.getByText('journalist').click(); });
    // newest wins: still one chip
    expect(screen.getAllByTestId('npc-chip').length).toBe(1);
  });

  it('honors broker cooldown (4 ticks)', () => {
    const { rerender } = render(
      <NpcLayerProvider currentTick={1}>
        <Probe />
      </NpcLayerProvider>
    );
    act(() => { screen.getByText('broker').click(); });
    expect(screen.queryByTestId('npc-chip')).not.toBeNull();

    // Advance ticks to 3 (still within 4-tick cooldown). New broker call should be suppressed.
    rerender(
      <NpcLayerProvider currentTick={3}>
        <Probe />
      </NpcLayerProvider>
    );
    act(() => { screen.getByText('broker').click(); });
    // Still showing earliest; not duplicated
    expect(screen.getAllByTestId('npc-chip').length).toBe(1);
  });
});
```

- [ ] **Step 6: Run to verify it fails**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/NpcLayer.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 7: Implement `NpcLayer.jsx`**

Create `frontend-react/src/components/game/renderers/stocksim/NpcLayer.jsx`:

```jsx
import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { THEME } from './theme';

const NpcContext = createContext(null);

const COOLDOWNS = {
  broker: 4,
  journalist: 0,
  analyst: 0,
  mentor: Infinity, // mentor handled separately (one-shot)
};

export function NpcLayerProvider({ currentTick = 0, children }) {
  const lastTickByPersona = useRef({});
  const [active, setActive] = useState(null);

  const say = useCallback((persona, payload) => {
    if (!payload) return;
    const last = lastTickByPersona.current[persona];
    const cooldown = COOLDOWNS[persona] ?? 0;
    if (last != null && currentTick - last < cooldown) return;
    lastTickByPersona.current[persona] = currentTick;
    setActive({ persona, payload, ts: Date.now() });
  }, [currentTick]);

  const dismiss = useCallback(() => setActive(null), []);

  const value = { say, dismiss, active };
  return (
    <NpcContext.Provider value={value}>
      {children}
      {active && <NpcChip persona={active.persona} payload={active.payload} onDismiss={dismiss} />}
    </NpcContext.Provider>
  );
}

export function useNpc() {
  const ctx = useContext(NpcContext);
  if (!ctx) throw new Error('useNpc must be used inside NpcLayerProvider');
  return ctx;
}

const PERSONA_ICON = { broker: '💼', journalist: '📰', analyst: '🤖', mentor: '🧭' };

function NpcChip({ persona, payload, onDismiss }) {
  const { t } = useTranslation();
  const text = t(payload.key, payload.props || {});
  return (
    <div
      data-testid="npc-chip"
      role="status"
      style={{
        position: 'fixed',
        bottom: 16,
        left: '50%',
        transform: 'translateX(-50%)',
        background: THEME.bgTile,
        border: `1px solid ${THEME.borderTile}`,
        borderLeft: `3px solid ${THEME.accentWarm}`,
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 12,
        color: THEME.textPrimary,
        maxWidth: 480,
        zIndex: 90,
        cursor: 'pointer',
        boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
      }}
      onClick={onDismiss}
    >
      <strong style={{ color: THEME.textMuted }}>{PERSONA_ICON[persona] || ''} {persona}:</strong> {text}
    </div>
  );
}
```

- [ ] **Step 8: Run the test to verify it passes**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/NpcLayer.test.jsx`
Expected: PASS, 2 tests.

- [ ] **Step 9: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/npcDialog.js \
        frontend-react/src/components/game/renderers/stocksim/npcDialog.test.js \
        frontend-react/src/components/game/renderers/stocksim/NpcLayer.jsx \
        frontend-react/src/components/game/renderers/stocksim/NpcLayer.test.jsx
git commit -m "feat(stocksim): NPC dispatcher (Broker + Journalist + Analyst + Mentor) with cooldowns"
```

---

## Task 5: Game JSON schema additions + 2 game JSON updates

**Files:**
- Modify: `backend/schemas.py`
- Test: `backend/tests/test_schemas.py`
- Modify: `backend/games/stock-market-day-trader.json`
- Modify: `backend/games/stock-market-simulator.json`

The spec adds these optional fields to `stock_market_config`:
- `briefing` (object): macro_tone, sector_mood, headline, sub.
- `stocks[i].fundamentals` (object): pe, pb, ev_ebitda, peg, eps_ttm, roe, roce, debt_equity, market_cap_cr, free_float_pct, promoter_pct, fii_pct, dii_pct, quarterly_revenue_cr (array of 4), fifty_two_week_high, fifty_two_week_low, div_yield_pct, beta, volume_x_avg, sector_pe.
- `stocks[i].peers` (array of 0..3): symbol, name, pe, growth_yoy, roe, market_cap_cr.
- `stocks[i].about` (object): description, key_people (array), founded, hq.
- `stocks[i].image_prompt` (string).
- `events[i].reason` (string).

All optional — backward-compatible.

**Validator contract (existing — confirmed in `backend/schemas.py:752` and `backend/tests/test_stocksim_bundles.py:18`):**
- Signature: `_validate_stock_market_minigame(g)` where `g` is the **full game bundle dict** with `g["game_id"]` and `g["minigame_config"]["stock_market_config"]`.
- Returns `None`. Raises `ValueError` on the first invalid field. Called from `_validate_minigame` at `backend/schemas.py:257`.
- Existing positive test pattern: `_validate(bundle)  # must not raise`.

Keep this contract. New validation paths must also `raise ValueError(...)`.

**Canonical events key:** `symbols`. Both `backend/games/stock-market-day-trader.json` and `backend/games/stock-market-simulator.json` use `symbols` (not `affected_symbols`). Test fixtures must use `symbols` to mirror production.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_schemas.py` (create the file if missing — top-of-file imports: `import pytest`; `import sys`; `from pathlib import Path`; `sys.path.insert(0, str(Path(__file__).resolve().parent.parent))`; `from schemas import _validate_stock_market_minigame`):

```python
def _wrap(cfg):
    """Wrap a stock_market_config in a full game bundle the validator expects."""
    return {
        "game_id": "test-stock-market",
        "minigame_config": {"subtype": "stock_market", "stock_market_config": cfg},
    }


def test_stock_market_v2_optional_fields_accepted():
    cfg = {
        "tick_interval_ms": 8000,
        "tick_count": 22,
        "starting_cash": 100000,
        "briefing": {
            "macro_tone": "RBI policy day. IT and banks in focus.",
            "sector_mood": {"IT": "positive", "Banking": "neutral"},
            "headline": "8 stocks. 22 ticks. Trade smart.",
            "sub": "Each tick = ~8 seconds.",
        },
        "stocks": [
            {
                "symbol": "TECHV", "name": "TechVista", "sector": "IT",
                "starting_price": 215, "volatility": 0.04,
                "fundamentals": {
                    "pe": 28.4, "sector_pe": 24.0, "roe": 22.1,
                    "debt_equity": 0.12, "market_cap_cr": 420000,
                    "quarterly_revenue_cr": [9400, 9820, 10250, 11140],
                },
                "peers": [{"symbol": "INFOS", "name": "InfoSwift", "pe": 24.0, "growth_yoy": 14, "roe": 25.0, "market_cap_cr": 720000}],
                "about": {"description": "Mid-cap IT services.", "key_people": [{"role": "CEO", "name": "R. Iyer"}], "founded": 1998, "hq": "Bengaluru"},
                "image_prompt": "modern server racks glowing blue",
            }
        ],
        "events": [{"id": "e1", "tick": 4, "headline": "h", "symbols": ["TECHV"], "reason": "Large contract", "impact": {"TECHV": 0.025}}],
    }
    _validate_stock_market_minigame(_wrap(cfg))  # must not raise


def test_stock_market_v2_rejects_quarterly_wrong_length():
    cfg = {
        "tick_interval_ms": 8000, "tick_count": 22, "starting_cash": 100000,
        "stocks": [{
            "symbol": "X", "name": "X", "sector": "X",
            "starting_price": 100, "volatility": 0.02,
            "fundamentals": {"quarterly_revenue_cr": [1, 2, 3]},
        }],
        "events": [],
    }
    with pytest.raises(ValueError, match="quarterly_revenue_cr"):
        _validate_stock_market_minigame(_wrap(cfg))


def test_stock_market_v2_legacy_config_still_valid():
    """A v1 config with no fundamentals/peers/about/briefing must still validate."""
    cfg = {
        "tick_interval_ms": 8000, "tick_count": 22, "starting_cash": 100000,
        "stocks": [{"symbol": "X", "name": "X", "sector": "X", "starting_price": 100, "volatility": 0.02}],
        "events": [{"id": "e1", "tick": 4, "headline": "h", "symbols": ["X"], "impact": {"X": 0.02}}],
    }
    _validate_stock_market_minigame(_wrap(cfg))  # must not raise
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `cd backend && python -m pytest tests/test_schemas.py::test_stock_market_v2_optional_fields_accepted tests/test_schemas.py::test_stock_market_v2_rejects_quarterly_wrong_length tests/test_schemas.py::test_stock_market_v2_legacy_config_still_valid -v`
Expected: `test_stock_market_v2_rejects_quarterly_wrong_length` FAILs (no ValueError raised — validator does not yet check `quarterly_revenue_cr`). The two positive tests may PASS already (unknown fields are silently accepted today); that's fine — they guard against regressions once Step 3 lands.

- [ ] **Step 3: Extend `_validate_stock_market_minigame`**

Open `backend/schemas.py:752-803`. The existing function uses `gid = g["game_id"]` and iterates `for i, s in enumerate(cfg["stocks"]):` — keep those names. Use `raise ValueError(...)` (matching the existing style); do NOT introduce an `errors` list.

Inside the per-stock loop (right after the existing volatility check at L780), add:

```python
        # v2 optional: fundamentals
        fund = s.get("fundamentals")
        if fund is not None:
            if not isinstance(fund, dict):
                raise ValueError(f"stock_market game {gid} stock[{i}]: 'fundamentals' must be an object")
            for num_field in (
                "pe", "pb", "ev_ebitda", "peg", "eps_ttm",
                "roe", "roce", "debt_equity",
                "market_cap_cr", "free_float_pct", "promoter_pct",
                "fii_pct", "dii_pct",
                "fifty_two_week_high", "fifty_two_week_low",
                "div_yield_pct", "beta", "volume_x_avg", "sector_pe",
            ):
                val = fund.get(num_field)
                if val is not None and (not isinstance(val, (int, float)) or isinstance(val, bool)):
                    raise ValueError(f"stock_market game {gid} stock[{i}]: 'fundamentals.{num_field}' must be numeric")
            qrev = fund.get("quarterly_revenue_cr")
            if qrev is not None:
                if not isinstance(qrev, list) or len(qrev) != 4:
                    raise ValueError(f"stock_market game {gid} stock[{i}]: 'fundamentals.quarterly_revenue_cr' must be a list of 4 numbers")
                if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in qrev):
                    raise ValueError(f"stock_market game {gid} stock[{i}]: 'fundamentals.quarterly_revenue_cr' entries must be numeric")

        # v2 optional: peers
        peers = s.get("peers")
        if peers is not None:
            if not isinstance(peers, list):
                raise ValueError(f"stock_market game {gid} stock[{i}]: 'peers' must be a list")
            if len(peers) > 3:
                raise ValueError(f"stock_market game {gid} stock[{i}]: 'peers' max length is 3")
            for pidx, peer in enumerate(peers):
                if not isinstance(peer, dict):
                    raise ValueError(f"stock_market game {gid} stock[{i}].peers[{pidx}] must be an object")
                for required in ("symbol", "name"):
                    if not isinstance(peer.get(required), str) or not peer.get(required):
                        raise ValueError(f"stock_market game {gid} stock[{i}].peers[{pidx}].{required} required string")
                for num_field in ("pe", "growth_yoy", "roe", "market_cap_cr"):
                    val = peer.get(num_field)
                    if val is not None and (not isinstance(val, (int, float)) or isinstance(val, bool)):
                        raise ValueError(f"stock_market game {gid} stock[{i}].peers[{pidx}].{num_field} must be numeric")

        # v2 optional: about
        about = s.get("about")
        if about is not None:
            if not isinstance(about, dict):
                raise ValueError(f"stock_market game {gid} stock[{i}]: 'about' must be an object")
            if about.get("description") is not None and not isinstance(about["description"], str):
                raise ValueError(f"stock_market game {gid} stock[{i}]: 'about.description' must be a string")
            kp = about.get("key_people")
            if kp is not None and not isinstance(kp, list):
                raise ValueError(f"stock_market game {gid} stock[{i}]: 'about.key_people' must be a list")

        # v2 optional: image_prompt
        ip = s.get("image_prompt")
        if ip is not None and not isinstance(ip, str):
            raise ValueError(f"stock_market game {gid} stock[{i}]: 'image_prompt' must be a string")
```

The existing event loop currently reads:
```python
for ev in cfg.get("events", []):
    for sym in ev.get("symbols", []):
        ...
```
Replace the loop header with `for ev_idx, ev in enumerate(cfg.get("events", [])):` (so we have an index), keep the existing `for sym in ev.get("symbols", []):` body unchanged, then at the end of each `ev` iteration add:

```python
        # v2 optional: events[i].reason
        reason = ev.get("reason")
        if reason is not None and not isinstance(reason, str):
            raise ValueError(f"stock_market game {gid}: events[{ev_idx}].reason must be a string")
```

After the per-stock loop and before the existing `dimensions_config` block, accept optional `briefing`:

```python
    briefing = cfg.get("briefing")
    if briefing is not None:
        if not isinstance(briefing, dict):
            raise ValueError(f"stock_market game {gid}: 'briefing' must be an object")
        for str_field in ("macro_tone", "headline", "sub"):
            v = briefing.get(str_field)
            if v is not None and not isinstance(v, str):
                raise ValueError(f"stock_market game {gid}: 'briefing.{str_field}' must be a string")
        sm = briefing.get("sector_mood")
        if sm is not None and not isinstance(sm, dict):
            raise ValueError(f"stock_market game {gid}: 'briefing.sector_mood' must be an object")
```

- [ ] **Step 4: Run schema tests**

Run: `cd backend && python -m pytest tests/test_schemas.py -v -k stock_market`
Expected: PASS, all stock_market tests including the 3 new ones.

- [ ] **Step 5: Update `backend/games/stock-market-day-trader.json`**

Open the file. Inside `minigame_config.stock_market_config`:

1. Add `briefing` block above `stocks`:

```json
"briefing": {
  "macro_tone": "RBI policy day. IT and banks in focus.",
  "sector_mood": {"IT": "positive", "Banking": "neutral", "Pharma": "neutral", "Auto": "negative"},
  "headline": "8 stocks. 22 ticks. Trade smart.",
  "sub": "Each tick = ~8 seconds. Watch news. Don't chase."
},
```

2. For each entry in `stocks`, add `fundamentals`, `peers`, `about`, `image_prompt`. Use the TECHV example in the spec as a template; populate plausible values per sector. Stay terse — one or two key_people max.

3. For each entry in `events`, add a `reason` string explaining the cause-effect.

- [ ] **Step 6: Update `backend/games/stock-market-simulator.json`**

Same fields. The two games may share copy where it makes sense; differences should already be encoded in tick_count / starting_cash / volatility.

- [ ] **Step 7: Validate both game files**

Run: `cd backend && python validate_all_games.py 2>&1 | grep -E "(stock-market|ERROR)"`
Expected: No ERROR lines for either stock game. PASS prints.

- [ ] **Step 8: Commit**

```bash
git add backend/schemas.py backend/tests/test_schemas.py \
        backend/games/stock-market-day-trader.json \
        backend/games/stock-market-simulator.json
git commit -m "feat(stocksim): extend schema with v2 fundamentals/peers/about/briefing/reason fields"
```

---

## Task 6: Backend last_reason propagation + /state echo

**Files:**
- Modify: `backend/engines/stocksim/events.py`
- Modify: `backend/app.py` (stocksim_state route)
- Test: `backend/tests/test_stocksim_engine.py` (NEW file — engine layer has no dedicated test today)
- Modify: `backend/tests/test_stocksim_routes.py`

The chip "Why is it moving?" requires the latest news/event reason to ride along on each quote for up to 2 ticks after the event.

**Pre-existing engine bugs we must fix in this task** (verified by reading `backend/engines/stocksim/events.py:1-58` and `backend/games/stock-market-day-trader.json:183-186`):

1. `news_at` only matches events whose `tick_pattern` starts with `every_` or `once_at_`. The production JSONs use `"tick": N` (a direct integer field), with no `tick_pattern`. So **events never fire today**. Task 6 must extend `news_at` to also match `ev.get("tick") == tick`.
2. `event_at` returns only events with `severity == "major"`. Production severities are `"info"` and `"warning"`. We do NOT change `event_at`'s contract — but the `recent_reasons` stamping must live in `news_at` so it fires for any matched event regardless of severity.
3. The run's stocksim state lives at `run["stocksim"]` (see `backend/app.py:26732` and `backend/tests/test_stocksim_routes.py:166`), NOT `run["state"]`. The route patch must use the correct key.
4. `stocksim_state` is GET-only and has no `force_tick` parameter. The route test must seed state directly via `storage.update_run` rather than passing a body.

- [ ] **Step 1: Write the failing engine test**

Create `backend/tests/test_stocksim_engine.py` (new file). Top-of-file imports:

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engines.stocksim.events import news_at, event_at
```

Then add three tests:

```python
def test_news_at_matches_direct_tick_field():
    """Production JSONs use {"tick": N}, not {"tick_pattern": "once_at_N"}. news_at must match both."""
    state = {}
    config = {"events": [{"id": "e1", "tick": 4, "headline": "h", "symbols": ["TECHV"],
                          "severity": "info", "reason": "Large contract"}]}
    out = news_at(state, 4, config)
    assert any(item["id"] == "e1" for item in out), "news_at should match events with bare 'tick' field"


def test_news_at_stamps_recent_reasons():
    """When an event with a reason matches, news_at must populate state['recent_reasons']."""
    state = {}
    config = {"events": [{"id": "e1", "tick": 4, "headline": "TechVista wins ₹500Cr",
                          "symbols": ["TECHV"], "severity": "info",
                          "reason": "Large contract → revenue"}]}
    news_at(state, 4, config)
    assert "TECHV" in state.get("recent_reasons", {})
    assert state["recent_reasons"]["TECHV"]["tick"] == 4
    assert "Large contract" in state["recent_reasons"]["TECHV"]["reason"]


def test_recent_reason_visible_within_two_ticks():
    """Reason should be readable for ticks 4, 5, 6, then expire at 7. Mirrors /state route logic."""
    state = {}
    config = {"events": [{"id": "e1", "tick": 4, "headline": "h", "symbols": ["TECHV"],
                          "severity": "info", "reason": "r"}]}
    news_at(state, 4, config)

    def visible_reason(state, tick, sym):
        rec = state.get("recent_reasons", {}).get(sym)
        if not rec:
            return None
        if tick - rec["tick"] <= 2:
            return rec["reason"]
        return None

    assert visible_reason(state, 4, "TECHV") == "r"
    assert visible_reason(state, 5, "TECHV") == "r"
    assert visible_reason(state, 6, "TECHV") == "r"
    assert visible_reason(state, 7, "TECHV") is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_stocksim_engine.py -v`
Expected: all three tests FAIL — `news_at` does not match bare-tick events, and never stamps `recent_reasons`.

- [ ] **Step 3: Extend `news_at` in `engines/stocksim/events.py`**

The current `news_at` (at `backend/engines/stocksim/events.py:13-45`) iterates `for ev in events:` and dispatches on `tick_pattern`. Add a third branch that matches the direct `tick` field, and stamp `recent_reasons` from a single helper at the point of match.

After the existing `pat = ev.get("tick_pattern", "")` line, add this block (replacing the existing `if pat.startswith(...)` chain). The full updated body of the loop should read:

```python
    for ev in events:
        matched = False
        pat = ev.get("tick_pattern", "")
        if pat.startswith("every_"):
            try:
                n = int(pat.split("_")[1])
                if n > 0 and tick > 0 and tick % n == 0:
                    matched = True
            except (ValueError, IndexError):
                pass
        elif pat.startswith("once_at_"):
            try:
                t = int(pat.split("_")[2])
                if tick == t:
                    matched = True
            except (ValueError, IndexError):
                pass
        else:
            # v2 canonical: bare {"tick": N}
            ev_tick = ev.get("tick")
            if isinstance(ev_tick, int) and ev_tick == tick:
                matched = True

        if not matched:
            continue

        out.append({
            "id": ev["id"],
            "headline": ev.get("headline", ""),
            "category": ev.get("category", "info"),
            "severity": ev.get("severity", "info"),
            "symbols": ev.get("symbols", []),
        })

        # v2: stamp recent_reasons for the why-moving chip (any severity, any matcher).
        reason = ev.get("reason") or ev.get("headline") or ""
        if reason:
            recent = state.setdefault("recent_reasons", {})
            for sym in (ev.get("symbols") or ev.get("affected_symbols") or []):
                recent[sym] = {"tick": tick, "reason": reason}
```

Do NOT touch `event_at` — it continues to filter for `severity == "major"`. Side effect propagates because `event_at` calls `news_at`.

- [ ] **Step 4: Run the engine tests**

Run: `cd backend && python -m pytest tests/test_stocksim_engine.py -v`
Expected: all three new tests PASS.

Also run the broader stocksim suite to confirm no regression:
Run: `cd backend && python -m pytest tests/test_stocksim_engine.py tests/test_stocksim_bundles.py tests/test_schemas.py -v`
Expected: all green.

- [ ] **Step 5: Echo `last_reason` in `/state` route**

Open `backend/app.py:26714-26783` (the `stocksim_state` route). Right after the `pnl = eng.compute_pnl(...)` line at `~26767` and before `active_event = ...`, insert:

```python
    # v2: surface "why is it moving?" reason for ≤2 ticks after the event.
    recent = state.get("recent_reasons") or {}
    for _sym, _q in quotes.items():
        _rec = recent.get(_sym)
        if _rec and (current_tick - _rec.get("tick", -999)) <= 2:
            _q["last_reason"] = _rec.get("reason", "")
```

`state` and `current_tick` are already in scope at that point (set at lines 26732 and 26756 respectively).

- [ ] **Step 6: Add a route test**

Append to `backend/tests/test_stocksim_routes.py` (the existing `client` and `stocksim_run` fixtures are already defined in the file — reuse them; do not introduce a new fixture):

```python
def test_state_echoes_last_reason_after_event(client, stocksim_run):
    """When recent_reasons is populated and current_tick is within 2 ticks, /state must echo last_reason."""
    # Start the session so /state returns 200.
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={},
                headers=_auth_headers())

    # Seed state directly: simulate an event having fired at tick 4, with the run now at tick 5.
    run = storage.get_run(stocksim_run)
    sim = run["stocksim"]
    sim["current_tick"] = 5
    sim["recent_reasons"] = {"TECHV": {"tick": 4, "reason": "Large contract → revenue"}}
    # Ensure the lazy-advance does NOT roll forward and clobber our seed:
    # set started_at_ms to "now" so elapsed_ticks ≈ 0, which is < current_tick = 5,
    # so the route's `if target_tick > current_tick` branch does not advance.
    sim["started_at_ms"] = int(time.time() * 1000)
    storage.update_run(stocksim_run, run)

    resp = client.get(f"/api/run/{stocksim_run}/stocksim/state",
                      headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.get_json()
    techv = (body.get("quotes") or {}).get("TECHV") or {}
    assert techv.get("last_reason") == "Large contract → revenue"


def test_state_drops_last_reason_after_three_ticks(client, stocksim_run):
    """When current_tick is >2 ticks past the recorded event tick, last_reason must NOT be echoed."""
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={},
                headers=_auth_headers())
    run = storage.get_run(stocksim_run)
    sim = run["stocksim"]
    sim["current_tick"] = 8  # 8 - 4 = 4 ticks past, well outside the 2-tick window
    sim["recent_reasons"] = {"TECHV": {"tick": 4, "reason": "Large contract"}}
    sim["started_at_ms"] = int(time.time() * 1000)
    storage.update_run(stocksim_run, run)

    resp = client.get(f"/api/run/{stocksim_run}/stocksim/state",
                      headers=_auth_headers())
    assert resp.status_code == 200
    body = resp.get_json()
    techv = (body.get("quotes") or {}).get("TECHV") or {}
    assert "last_reason" not in techv
```

- [ ] **Step 7: Run route tests**

Run: `cd backend && python -m pytest tests/test_stocksim_routes.py -v`
Expected: all stocksim route tests PASS, including the 2 new ones.

- [ ] **Step 8: Commit**

```bash
git add backend/engines/stocksim/events.py backend/app.py \
        backend/tests/test_stocksim_engine.py backend/tests/test_stocksim_routes.py
git commit -m "feat(stocksim): stamp event reason on quotes for 2-tick why-moving chip"
```

---

## Task 7: Backend stock image route

**Files:**
- Modify: `backend/app.py` (new route)
- Test: `backend/tests/test_stocksim_routes.py`

The route returns a cached DALL-E image URL (or 202 when generating). It mirrors the existing `/api/games/<game_id>/rounds/<round_id>/story-image` pattern at `backend/app.py:8333`.

- [ ] **Step 1: Write the failing route test**

Add to `backend/tests/test_stocksim_routes.py`:

```python
def test_stock_image_returns_url_when_cached(client, monkeypatch):
    """Second call to image route should return a cached URL."""
    from services import story_image_service

    calls = {"n": 0}
    def fake_generate(**kwargs):
        calls["n"] += 1
        return {"image_url": "/uploads/stocksim_techv.png", "cached": calls["n"] > 1}
    monkeypatch.setattr(story_image_service, "generate_story_image", fake_generate)

    r1 = client.get("/api/games/stock-market-day-trader/stock/TECHV/image")
    r2 = client.get("/api/games/stock-market-day-trader/stock/TECHV/image")
    assert r1.status_code in (200, 202)
    assert r2.status_code == 200
    assert r2.get_json()["image_url"].endswith(".png")


def test_stock_image_returns_404_for_unknown_symbol(client):
    r = client.get("/api/games/stock-market-day-trader/stock/NOPE/image")
    assert r.status_code == 404
```

**Note on monkeypatching:** the route MUST do `from services import story_image_service` then call `story_image_service.generate_story_image(...)` (module-attribute access) so `monkeypatch.setattr(story_image_service, "generate_story_image", ...)` actually intercepts the call. A `from services.story_image_service import generate_story_image` direct import inside the route would bind the original function and bypass the patch.

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_stocksim_routes.py::test_stock_image_returns_url_when_cached tests/test_stocksim_routes.py::test_stock_image_returns_404_for_unknown_symbol -v`
Expected: FAIL — route does not exist.

- [ ] **Step 3: Add the route in `backend/app.py`**

Near the existing `/api/games/<game_id>/rounds/<round_id>/story-image` route (~line 8333), add:

```python
@app.get("/api/games/<game_id>/stock/<symbol>/image")
def stocksim_stock_image(game_id, symbol):
    """Return cached AI hero image for a stock; 202 while generating; 404 if symbol unknown."""
    from game_storage import load_game
    from services import story_image_service

    bundle = load_game(game_id)
    if not bundle:
        return jsonify({"error": "Unknown game"}), 404
    cfg = (bundle.get("minigame_config") or {}).get("stock_market_config") or {}
    stock = next((s for s in cfg.get("stocks", []) if s.get("symbol") == symbol), None)
    if not stock:
        return jsonify({"error": "Unknown symbol"}), 404

    prompt = stock.get("image_prompt")
    if not prompt:
        return jsonify({"image_url": None, "fallback": True}), 200

    try:
        result = story_image_service.generate_story_image(
            game_id=f"stocksim_{game_id}",
            round_id=f"stock_{symbol}",
            image_prompt=prompt,
            scene_hint=f"{stock.get('name', symbol)} - {stock.get('sector', '')}",
            image_style="semi-realistic",
        )
        if not result or not result.get("image_url"):
            return jsonify({"status": "generating"}), 202
        return jsonify({"image_url": result["image_url"], "cached": result.get("cached", False)}), 200
    except Exception as exc:
        app.logger.warning("stock image generation failed for %s/%s: %s", game_id, symbol, exc)
        return jsonify({"image_url": None, "fallback": True}), 200
```

The bundle helper is `load_game(game_id)` from `game_storage` (this matches the existing `/api/games/<game_id>/rounds/<round_id>/story-image` route at `app.py:8336`). The service module import is `from services import story_image_service` (NOT `backend.services`) — `backend/` is the project root on the Python path, so the package is just `services`.

- [ ] **Step 4: Run route tests, then commit**

Run: `cd backend && python -m pytest tests/test_stocksim_routes.py -v`
Expected: PASS, all stocksim route tests.

```bash
git add backend/app.py backend/tests/test_stocksim_routes.py
git commit -m "feat(stocksim): GET /api/games/<id>/stock/<symbol>/image route with DALL-E cache"
```

---

## Task 8a: technicals.js (pure)

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/technicals.js`
- Test: `frontend-react/src/components/game/renderers/stocksim/technicals.test.js`

- [ ] **Step 1: Write the failing test**

Create `technicals.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { rsi, ma, supportResistance, crossover } from './technicals';

describe('technicals', () => {
  it('ma returns simple moving average over the last N closes', () => {
    expect(ma([1, 2, 3, 4, 5], 3)).toBeCloseTo(4); // (3+4+5)/3
    expect(ma([10], 3)).toBeNull();
  });

  it('rsi returns 100 for monotonic up series', () => {
    const series = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15];
    expect(rsi(series, 14)).toBeCloseTo(100, 0);
  });

  it('rsi returns 0 for monotonic down series', () => {
    const series = [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1];
    expect(rsi(series, 14)).toBeCloseTo(0, 0);
  });

  it('supportResistance returns min/max over lookback window', () => {
    const out = supportResistance([10, 12, 8, 11, 14, 9, 13], 5);
    expect(out.support).toBe(8);
    expect(out.resistance).toBe(14);
  });

  it('crossover detects bullish/bearish/none', () => {
    expect(crossover([5, 6, 7], [4, 5, 6])).toBe('bullish'); // short above long, increasing
    expect(crossover([5, 5, 5], [6, 6, 6])).toBe('bearish');
    expect(crossover([5, 5], [5, 5])).toBe('none');
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/technicals.test.js`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `technicals.js`**

```js
export function ma(prices, period) {
  if (!Array.isArray(prices) || prices.length < period) return null;
  const slice = prices.slice(-period);
  const sum = slice.reduce((a, b) => a + b, 0);
  return sum / period;
}

export function rsi(prices, period = 14) {
  if (!Array.isArray(prices) || prices.length <= period) return null;
  let gains = 0, losses = 0;
  for (let i = 1; i <= period; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff >= 0) gains += diff; else losses -= diff;
  }
  let avgGain = gains / period;
  let avgLoss = losses / period;
  for (let i = period + 1; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
  }
  if (avgLoss === 0) return 100;
  if (avgGain === 0) return 0;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

export function supportResistance(prices, lookback = 10) {
  if (!Array.isArray(prices) || prices.length === 0) return { support: null, resistance: null };
  const slice = prices.slice(-lookback);
  return { support: Math.min(...slice), resistance: Math.max(...slice) };
}

export function crossover(maShort, maLong) {
  if (!Array.isArray(maShort) || !Array.isArray(maLong)) return 'none';
  if (maShort.length === 0 || maLong.length === 0) return 'none';
  const lastShort = maShort[maShort.length - 1];
  const lastLong = maLong[maLong.length - 1];
  if (lastShort > lastLong) return 'bullish';
  if (lastShort < lastLong) return 'bearish';
  return 'none';
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/technicals.test.js`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/technicals.js \
        frontend-react/src/components/game/renderers/stocksim/technicals.test.js
git commit -m "feat(stocksim): pure technicals (RSI/MA/support-resistance/crossover)"
```

---

## Task 8b: Six tab components

**Files (all under `frontend-react/src/components/game/renderers/stocksim/tabs/`):**
- `ChartTab.jsx` · `FundamentalsTab.jsx` · `TechnicalsTab.jsx` · `NewsTab.jsx` · `PeersTab.jsx` · `AboutTab.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/tabs/tabs.test.jsx`

Each tab is a small presentational component. They share the warm-amber theme; their job is to render data, not fetch it.

- [ ] **Step 1: Write the smoke test for all 6 tabs**

Create `tabs/tabs.test.jsx`:

```jsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../../../i18n'; // Adjust path if i18n is elsewhere
import ChartTab from './ChartTab';
import FundamentalsTab from './FundamentalsTab';
import TechnicalsTab from './TechnicalsTab';
import NewsTab from './NewsTab';
import PeersTab from './PeersTab';
import AboutTab from './AboutTab';

const wrap = (ui) => <I18nextProvider i18n={i18n}>{ui}</I18nextProvider>;

describe('Drill-down tabs render with empty/minimal data', () => {
  it('ChartTab renders with empty priceHistory', () => {
    expect(() => render(wrap(<ChartTab priceHistory={[]} indicators={{}} />))).not.toThrow();
  });
  it('FundamentalsTab renders with no fundamentals', () => {
    expect(() => render(wrap(<FundamentalsTab fundamentals={null} />))).not.toThrow();
  });
  it('TechnicalsTab renders with empty priceHistory', () => {
    expect(() => render(wrap(<TechnicalsTab priceHistory={[]} stockCfg={{ symbol: 'X' }} />))).not.toThrow();
  });
  it('NewsTab renders with empty news', () => {
    expect(() => render(wrap(<NewsTab news={[]} symbol="X" currentTick={0} />))).not.toThrow();
  });
  it('PeersTab renders with no peers', () => {
    expect(() => render(wrap(<PeersTab peers={[]} stockCfg={{ symbol: 'X', fundamentals: {} }} />))).not.toThrow();
  });
  it('AboutTab renders with no about block', () => {
    expect(() => render(wrap(<AboutTab about={null} imageUrl={null} />))).not.toThrow();
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/tabs/tabs.test.jsx`
Expected: FAIL — modules not found.

- [ ] **Step 3: Implement `ChartTab.jsx`**

```jsx
import React from 'react';
import { THEME } from '../theme';
import { ma } from '../technicals';

export default function ChartTab({ priceHistory = [], indicators = {} }) {
  const closes = priceHistory.map(p => p.mid ?? p);
  const ma20 = ma(closes, 20);
  if (closes.length === 0) {
    return <div style={{ color: THEME.textMuted, padding: 12, fontSize: 12 }}>No price data yet.</div>;
  }
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const span = Math.max(max - min, 0.01);
  const points = closes.map((c, i) => {
    const x = (i / Math.max(closes.length - 1, 1)) * 400;
    const y = 90 - ((c - min) / span) * 80;
    return `${x},${y}`;
  }).join(' ');
  return (
    <div style={{ background: THEME.bgTile, borderRadius: 8, padding: 8 }}>
      <div style={{ height: 100, position: 'relative' }}>
        <svg viewBox="0 0 400 100" preserveAspectRatio="none" style={{ width: '100%', height: '100%' }}>
          {ma20 != null && (
            <line x1="0" y1={90 - ((ma20 - min) / span) * 80} x2="400"
                  y2={90 - ((ma20 - min) / span) * 80}
                  stroke={THEME.accentWarm} strokeDasharray="3,3" strokeWidth="0.5" />
          )}
          <polyline points={points} stroke={THEME.gain} strokeWidth="2" fill="none" />
        </svg>
      </div>
      <div style={{ fontSize: 10, color: THEME.textMuted, marginTop: 4 }}>
        MA-20: {ma20 != null ? ma20.toFixed(2) : '—'} · RSI: {indicators.rsi != null ? indicators.rsi.toFixed(0) : '—'}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Implement `FundamentalsTab.jsx`**

```jsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { THEME } from '../theme';
import { analystVerdict } from '../npcDialog';

function Cell({ label, value, color }) {
  return (
    <div style={{ background: THEME.bgTile, borderRadius: 6, padding: 6 }}>
      <div style={{ fontSize: 9, color: THEME.textMuted, fontWeight: 600 }}>{label}</div>
      <div style={{ fontWeight: 700, color: color || THEME.textPrimary, fontSize: 12 }}>{value ?? '—'}</div>
    </div>
  );
}

export default function FundamentalsTab({ fundamentals }) {
  const { t } = useTranslation();
  const f = fundamentals || {};
  const verdict = analystVerdict({
    pe: f.pe, sector_pe: f.sector_pe, roe: f.roe, debt_equity: f.debt_equity,
  });
  const grid = { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 };
  const sectionLabel = { fontSize: 10, color: THEME.textMuted, fontWeight: 700, margin: '8px 0 4px' };

  return (
    <div>
      <div style={sectionLabel}>VALUATION</div>
      <div style={grid}>
        <Cell label="P/E" value={f.pe} />
        <Cell label="P/B" value={f.pb} />
        <Cell label="EV/EBITDA" value={f.ev_ebitda} />
        <Cell label="PEG" value={f.peg} />
      </div>
      <div style={sectionLabel}>PROFITABILITY &amp; HEALTH</div>
      <div style={grid}>
        <Cell label="EPS (TTM)" value={f.eps_ttm != null ? `₹${f.eps_ttm}` : '—'} />
        <Cell label="ROE" value={f.roe != null ? `${f.roe}%` : '—'} color={THEME.gain} />
        <Cell label="ROCE" value={f.roce != null ? `${f.roce}%` : '—'} color={THEME.gain} />
        <Cell label="DEBT/EQ" value={f.debt_equity} />
      </div>
      <div style={sectionLabel}>SIZE &amp; OWNERSHIP</div>
      <div style={grid}>
        <Cell label="MARKET CAP" value={f.market_cap_cr != null ? `₹${(f.market_cap_cr / 100000).toFixed(1)}L Cr` : '—'} />
        <Cell label="FREE FLOAT" value={f.free_float_pct != null ? `${f.free_float_pct}%` : '—'} />
        <Cell label="PROMOTER" value={f.promoter_pct != null ? `${f.promoter_pct}%` : '—'} />
        <Cell label="FII / DII" value={(f.fii_pct != null && f.dii_pct != null) ? `${f.fii_pct}% / ${f.dii_pct}%` : '—'} />
      </div>
      {Array.isArray(f.quarterly_revenue_cr) && f.quarterly_revenue_cr.length === 4 && (
        <>
          <div style={sectionLabel}>QUARTERLY REVENUE (₹ Cr)</div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'flex-end', height: 60, background: THEME.bgTile, borderRadius: 6, padding: 6 }}>
            {f.quarterly_revenue_cr.map((q, i) => {
              const max = Math.max(...f.quarterly_revenue_cr);
              const h = (q / max) * 48;
              const rising = i > 0 && q >= f.quarterly_revenue_cr[i - 1];
              return (
                <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                  <div style={{ background: rising ? THEME.gain : THEME.textMuted, width: 18, height: h, borderRadius: '3px 3px 0 0' }} />
                  <div style={{ fontSize: 9, color: THEME.textMuted }}>Q{i + 1} · {q}</div>
                </div>
              );
            })}
          </div>
        </>
      )}
      <div style={sectionLabel}>RANGES &amp; SIGNALS</div>
      <div style={grid}>
        <Cell label="52W RANGE" value={(f.fifty_two_week_low != null && f.fifty_two_week_high != null) ? `${f.fifty_two_week_low} — ${f.fifty_two_week_high}` : '—'} />
        <Cell label="DIV YIELD" value={f.div_yield_pct != null ? `${f.div_yield_pct}%` : '—'} />
        <Cell label="BETA" value={f.beta} />
        <Cell label="VOLUME (T)" value={f.volume_x_avg != null ? `${f.volume_x_avg}× avg` : '—'} />
      </div>
      <div style={{ background: '#FEF3C7', borderRadius: 6, padding: 8, marginTop: 8, borderLeft: `3px solid ${THEME.accentWarm}` }}>
        <div style={{ fontSize: 9, color: THEME.textMuted, fontWeight: 700 }}>🤖 ANALYST</div>
        <div style={{ fontSize: 11, color: THEME.textPrimary }}>{t(verdict.key, verdict.props)}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Implement `TechnicalsTab.jsx`**

```jsx
import React from 'react';
import { THEME } from '../theme';
import { rsi, ma, supportResistance, crossover } from '../technicals';

export default function TechnicalsTab({ priceHistory = [], stockCfg }) {
  const closes = priceHistory.map(p => p.mid ?? p);
  const rsiVal = rsi(closes, 14);
  const ma20 = ma(closes, 20);
  const ma50 = ma(closes, 50);
  const sr = supportResistance(closes, 10);
  const cross = crossover(
    closes.length >= 21 ? closes.slice(-3).map((_, i, a) => ma(closes.slice(0, closes.length - 2 + i), 20)) : [],
    closes.length >= 51 ? closes.slice(-3).map((_, i, a) => ma(closes.slice(0, closes.length - 2 + i), 50)) : []
  );
  const cell = { background: THEME.bgTile, borderRadius: 6, padding: 6 };
  const label = { fontSize: 9, color: THEME.textMuted, fontWeight: 600 };
  const val = { fontWeight: 700, fontSize: 12, color: THEME.textPrimary };
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
      <div style={cell}><div style={label}>RSI (14)</div><div style={val}>{rsiVal != null ? rsiVal.toFixed(0) : '—'}</div></div>
      <div style={cell}><div style={label}>MA-20 / MA-50</div><div style={val}>{ma20?.toFixed(2) ?? '—'} / {ma50?.toFixed(2) ?? '—'}</div></div>
      <div style={cell}><div style={label}>SUPPORT</div><div style={val}>{sr.support?.toFixed?.(2) ?? '—'}</div></div>
      <div style={cell}><div style={label}>RESISTANCE</div><div style={val}>{sr.resistance?.toFixed?.(2) ?? '—'}</div></div>
      <div style={{ ...cell, gridColumn: 'span 2' }}>
        <div style={label}>CROSSOVER</div><div style={val}>{cross}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Implement `NewsTab.jsx`**

```jsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { THEME } from '../theme';
import { journalistFlavor } from '../npcDialog';

export default function NewsTab({ news = [], symbol, currentTick = 0 }) {
  const { t } = useTranslation();
  const items = (news || []).filter(n => {
    const syms = n.affected_symbols || n.symbols || [];
    return Array.isArray(syms) && syms.includes(symbol);
  });
  if (items.length === 0) {
    return <div style={{ color: THEME.textMuted, padding: 12, fontSize: 12 }}>No news yet for {symbol}.</div>;
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {items.map((n, i) => {
        const flav = journalistFlavor(n);
        return (
          <div key={i} style={{ background: THEME.bgTile, borderLeft: `3px solid ${THEME.accentWarm}`, borderRadius: 6, padding: 8 }}>
            <div style={{ fontSize: 9, color: THEME.textMuted }}>Tick {n.tick}{n.tick > currentTick ? ' (upcoming)' : ''}</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: THEME.textPrimary }}>{n.headline}</div>
            {flav && (
              <div style={{ fontSize: 11, color: THEME.textMuted, marginTop: 4 }}>📰 {t(flav.key, flav.props)}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 7: Implement `PeersTab.jsx`**

```jsx
import React from 'react';
import { THEME } from '../theme';

export default function PeersTab({ peers = [], stockCfg }) {
  const f = stockCfg?.fundamentals || {};
  const meRow = {
    symbol: stockCfg?.symbol, name: stockCfg?.name,
    pe: f.pe, growth_yoy: null, roe: f.roe, market_cap_cr: f.market_cap_cr,
  };
  const rows = [meRow, ...(peers || [])];
  const cell = { padding: '6px 8px', fontSize: 11, color: THEME.textPrimary, borderBottom: `1px solid ${THEME.borderTile}` };
  const head = { ...cell, fontWeight: 700, color: THEME.textMuted, fontSize: 10 };
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', background: THEME.bgTile, borderRadius: 6, overflow: 'hidden' }}>
      <thead>
        <tr><th style={head}>NAME</th><th style={head}>P/E</th><th style={head}>GROWTH</th><th style={head}>ROE</th><th style={head}>CAP</th></tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} style={i === 0 ? { background: '#FEF3C7' } : null}>
            <td style={cell}>{r.name || r.symbol}{i === 0 ? ' (this)' : ''}</td>
            <td style={cell}>{r.pe ?? '—'}</td>
            <td style={cell}>{r.growth_yoy != null ? `${r.growth_yoy}%` : '—'}</td>
            <td style={cell}>{r.roe != null ? `${r.roe}%` : '—'}</td>
            <td style={cell}>{r.market_cap_cr != null ? `₹${(r.market_cap_cr / 100000).toFixed(1)}L Cr` : '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 8: Implement `AboutTab.jsx`**

```jsx
import React from 'react';
import { THEME } from '../theme';

export default function AboutTab({ about, imageUrl }) {
  const a = about || {};
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{
        height: 140, borderRadius: 8, background: imageUrl ? `url(${imageUrl}) center/cover` : `linear-gradient(135deg, ${THEME.accentWarm}, ${THEME.textMuted})`,
      }} />
      {a.description && (
        <div style={{ fontSize: 12, color: THEME.textPrimary }}>{a.description}</div>
      )}
      {(a.founded || a.hq) && (
        <div style={{ fontSize: 11, color: THEME.textMuted }}>
          {a.founded && <>Founded {a.founded}</>}{a.founded && a.hq && ' · '}{a.hq && <>HQ {a.hq}</>}
        </div>
      )}
      {Array.isArray(a.key_people) && a.key_people.length > 0 && (
        <ul style={{ margin: 0, paddingLeft: 18, fontSize: 11, color: THEME.textPrimary }}>
          {a.key_people.map((p, i) => <li key={i}>{p.role}: {p.name}</li>)}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 9: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/tabs/tabs.test.jsx`
Expected: PASS, 6 tests.

- [ ] **Step 10: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/tabs/
git commit -m "feat(stocksim): six drill-down tab components (Chart/Fundamentals/Technicals/News/Peers/About)"
```

---

## Task 8c: CompanyDrillDown shell

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/CompanyDrillDown.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/CompanyDrillDown.test.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../../i18n';
import CompanyDrillDown from './CompanyDrillDown';

const stock = {
  symbol: 'TECHV', name: 'TechVista', sector: 'IT',
  fundamentals: { pe: 28.4, sector_pe: 24, roe: 22, debt_equity: 0.12 },
  peers: [], about: { description: 'd' }, image_prompt: 'p',
};
const quote = { mid: 215, bid: 214.95, ask: 215.05, volume: 100 };

const wrap = (ui) => <I18nextProvider i18n={i18n}>{ui}</I18nextProvider>;

describe('CompanyDrillDown', () => {
  it('renders with Chart tab active by default', () => {
    render(wrap(<CompanyDrillDown stock={stock} quote={quote} priceHistory={[{ mid: 210 }, { mid: 215 }]} news={[]} imageUrl={null} onClose={() => {}} />));
    expect(screen.getByTestId('drilldown-tab-chart')).toHaveAttribute('data-active', 'true');
  });

  it('switches to Fundamentals when clicked', () => {
    render(wrap(<CompanyDrillDown stock={stock} quote={quote} priceHistory={[]} news={[]} imageUrl={null} onClose={() => {}} />));
    fireEvent.click(screen.getByTestId('drilldown-tab-fundamentals'));
    expect(screen.getByTestId('drilldown-tab-fundamentals')).toHaveAttribute('data-active', 'true');
    expect(screen.getByText(/VALUATION/)).toBeInTheDocument();
  });

  it('calls onClose when backdrop clicked', () => {
    const onClose = vi.fn();
    render(wrap(<CompanyDrillDown stock={stock} quote={quote} priceHistory={[]} news={[]} imageUrl={null} onClose={onClose} />));
    fireEvent.click(screen.getByTestId('drilldown-backdrop'));
    expect(onClose).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/CompanyDrillDown.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `CompanyDrillDown.jsx`**

```jsx
import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { THEME, gainLossColor } from './theme';
import ChartTab from './tabs/ChartTab';
import FundamentalsTab from './tabs/FundamentalsTab';
import TechnicalsTab from './tabs/TechnicalsTab';
import NewsTab from './tabs/NewsTab';
import PeersTab from './tabs/PeersTab';
import AboutTab from './tabs/AboutTab';
import { analystVerdict } from './npcDialog';

const TABS = [
  { id: 'chart', label: 'Chart' },
  { id: 'fundamentals', label: 'Fundamentals' },
  { id: 'technicals', label: 'Technicals' },
  { id: 'news', label: 'News' },
  { id: 'peers', label: 'Peers' },
  { id: 'about', label: 'About' },
];

export default function CompanyDrillDown({
  stock, quote, position, priceHistory = [], news = [], imageUrl, currentTick = 0,
  onClose, onTrade,
}) {
  const { t } = useTranslation();
  const [tab, setTab] = useState('chart');

  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose?.(); }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const verdict = analystVerdict({
    pe: stock?.fundamentals?.pe,
    sector_pe: stock?.fundamentals?.sector_pe,
    roe: stock?.fundamentals?.roe,
    debt_equity: stock?.fundamentals?.debt_equity,
  });
  const change = quote?.last_change_pct ?? 0;

  return (
    <div
      data-testid="drilldown-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(60,40,10,0.4)',
        zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12, padding: 12, maxWidth: 600, width: '100%',
          maxHeight: '90vh', overflowY: 'auto', border: `1px solid ${THEME.borderTile}`,
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
          <div style={{
            width: 80, height: 80, borderRadius: 10,
            background: imageUrl ? `url(${imageUrl}) center/cover` : `linear-gradient(135deg, ${THEME.accentWarm}, ${THEME.textMuted})`,
            flex: '0 0 auto',
          }} />
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontWeight: 800, fontSize: 14, color: THEME.textPrimary }}>{stock?.name} ({stock?.symbol})</div>
                <div style={{ color: THEME.textMuted, fontSize: 11 }}>{stock?.sector}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontWeight: 800, fontSize: 14, color: gainLossColor(change) }}>₹{quote?.mid?.toFixed(2) ?? '—'}</div>
                <div style={{ color: gainLossColor(change), fontSize: 10 }}>{change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%</div>
              </div>
            </div>
            <div style={{ marginTop: 6, fontSize: 11, color: THEME.textPrimary }}>
              🤖 <strong>Analyst:</strong> {t(verdict.key, verdict.props)}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 4, borderBottom: `2px solid ${THEME.borderTile}`, marginBottom: 8 }}>
          {TABS.map(tb => (
            <button
              key={tb.id}
              data-testid={`drilldown-tab-${tb.id}`}
              data-active={tab === tb.id ? 'true' : 'false'}
              onClick={() => setTab(tb.id)}
              style={{
                padding: '4px 10px', border: 'none', cursor: 'pointer',
                background: tab === tb.id ? THEME.bgTile : 'transparent',
                color: tab === tb.id ? THEME.textPrimary : THEME.textMuted,
                fontWeight: tab === tb.id ? 700 : 500,
                borderRadius: '6px 6px 0 0', fontSize: 11,
              }}
            >{tb.label}</button>
          ))}
        </div>

        {/* Body */}
        {tab === 'chart' && <ChartTab priceHistory={priceHistory} indicators={{ rsi: quote?.rsi }} />}
        {tab === 'fundamentals' && <FundamentalsTab fundamentals={stock?.fundamentals} />}
        {tab === 'technicals' && <TechnicalsTab priceHistory={priceHistory} stockCfg={stock} />}
        {tab === 'news' && <NewsTab news={news} symbol={stock?.symbol} currentTick={currentTick} />}
        {tab === 'peers' && <PeersTab peers={stock?.peers} stockCfg={stock} />}
        {tab === 'about' && <AboutTab about={stock?.about} imageUrl={imageUrl} />}

        {/* Trade footer */}
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', background: THEME.bgTile, borderRadius: 8, padding: 8, marginTop: 10 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 9, color: THEME.textMuted }}>YOU OWN</div>
            <div style={{ fontWeight: 700, fontSize: 12, color: THEME.textPrimary }}>
              {position?.qty ? `${position.qty} shares · cost ₹${position.cost_basis?.toFixed?.(2) ?? '—'}` : '—'}
            </div>
          </div>
          <button onClick={() => onTrade?.('buy', { symbol: stock.symbol })} style={{ background: THEME.gain, color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 18, fontWeight: 700, fontSize: 11, cursor: 'pointer' }}>Buy</button>
          <button onClick={() => onTrade?.('sell', { symbol: stock.symbol })} style={{ background: THEME.loss, color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 18, fontWeight: 700, fontSize: 11, cursor: 'pointer' }}>Sell</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/CompanyDrillDown.test.jsx`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/CompanyDrillDown.jsx \
        frontend-react/src/components/game/renderers/stocksim/CompanyDrillDown.test.jsx
git commit -m "feat(stocksim): CompanyDrillDown modal shell wiring 6 tabs + Analyst NPC header"
```

---

## Task 9: OrderTicket upgrade — position sizer + Target/Stop chips

**Files:**
- Modify: `frontend-react/src/components/game/renderers/stocksim/OrderTicket.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/OrderTicket.test.jsx`

The existing `OrderTicket` already renders qty + buy/sell. We add:
1. A live "Position sizer" line under qty: total cost, % of cash, gain/loss at ±5%.
2. Two chips "Target +5% / Stop −3%" — toggling each attaches `target_pct`/`stop_pct` to the order payload.
3. Calls `useNpc().say('broker', brokerOnTrade(order, riskPct))` whenever order risk crosses thresholds.

- [ ] **Step 1: Read the existing component**

Open `frontend-react/src/components/game/renderers/stocksim/OrderTicket.jsx`. Note the existing prop shape and submit handler. Do NOT rename existing props.

- [ ] **Step 2: Write the failing test**

Create `frontend-react/src/components/game/renderers/stocksim/OrderTicket.test.jsx`:

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../../i18n';
import OrderTicket from './OrderTicket';
import { NpcLayerProvider } from './NpcLayer';

const wrap = (ui) => (
  <I18nextProvider i18n={i18n}>
    <NpcLayerProvider currentTick={0}>{ui}</NpcLayerProvider>
  </I18nextProvider>
);

describe('OrderTicket v2 additions', () => {
  it('shows position sizer line with total cost and risk %', () => {
    render(wrap(<OrderTicket symbol="TECHV" quote={{ ask: 215, bid: 214.95 }} cash={10000} onSubmit={() => {}} />));
    fireEvent.change(screen.getByTestId('order-qty'), { target: { value: '10' } });
    expect(screen.getByTestId('order-sizer').textContent).toMatch(/₹2,150/);
    expect(screen.getByTestId('order-sizer').textContent).toMatch(/21\.5%/);
  });

  it('toggles Target/Stop chips and includes them in submitted payload', () => {
    const onSubmit = vi.fn();
    render(wrap(<OrderTicket symbol="TECHV" quote={{ ask: 215, bid: 214.95 }} cash={10000} onSubmit={onSubmit} />));
    fireEvent.change(screen.getByTestId('order-qty'), { target: { value: '5' } });
    fireEvent.click(screen.getByTestId('chip-target'));
    fireEvent.click(screen.getByTestId('chip-stop'));
    fireEvent.click(screen.getByTestId('order-buy'));
    expect(onSubmit).toHaveBeenCalled();
    const payload = onSubmit.mock.calls[0][0];
    expect(payload.target_pct).toBe(5);
    expect(payload.stop_pct).toBe(-3);
  });
});
```

- [ ] **Step 3: Run, expect FAIL**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/OrderTicket.test.jsx`
Expected: FAIL — sizer/chips not present yet.

- [ ] **Step 4: Extend `OrderTicket.jsx`**

Inside the component, after existing state, add:

```jsx
import { useNpc } from './NpcLayer';
import { brokerOnTrade } from './npcDialog';
import { THEME } from './theme';

// inside component:
const [targetOn, setTargetOn] = useState(false);
const [stopOn, setStopOn] = useState(false);
const npc = useNpc();

const px = side === 'sell' ? (quote?.bid ?? 0) : (quote?.ask ?? 0);
const totalCost = (Number(qty) || 0) * px;
const riskPct = cash > 0 ? (totalCost / cash) * 100 : 0;
const fivePctMove = totalCost * 0.05;

function handleSubmit(submitSide) {
  const payload = {
    symbol, side: submitSide, qty: Number(qty) || 0,
    target_pct: targetOn ? 5 : null,
    stop_pct: stopOn ? -3 : null,
  };
  const line = brokerOnTrade(payload, riskPct);
  if (line) npc.say('broker', line);
  onSubmit?.(payload);
}
```

In JSX, after the qty input row, render:

```jsx
<div data-testid="order-sizer" style={{ fontSize: 10, color: THEME.textMuted, marginTop: 4 }}>
  @ qty={qty || 0} → ₹{totalCost.toLocaleString('en-IN')} ({riskPct.toFixed(1)}% of cash) ·
  +5% = +₹{fivePctMove.toFixed(2)} / −5% = −₹{fivePctMove.toFixed(2)}
</div>
<div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
  <button
    data-testid="chip-target"
    data-active={targetOn ? 'true' : 'false'}
    onClick={() => setTargetOn(v => !v)}
    style={{
      background: targetOn ? THEME.gain : THEME.bgTile,
      color: targetOn ? '#fff' : THEME.textPrimary,
      border: `1px solid ${THEME.borderTile}`, borderRadius: 12, padding: '2px 8px',
      fontSize: 10, cursor: 'pointer',
    }}
  >Target +5%</button>
  <button
    data-testid="chip-stop"
    data-active={stopOn ? 'true' : 'false'}
    onClick={() => setStopOn(v => !v)}
    style={{
      background: stopOn ? THEME.loss : THEME.bgTile,
      color: stopOn ? '#fff' : THEME.textPrimary,
      border: `1px solid ${THEME.borderTile}`, borderRadius: 12, padding: '2px 8px',
      fontSize: 10, cursor: 'pointer',
    }}
  >Stop −3%</button>
</div>
```

Wire the Buy button to `data-testid="order-buy"` calling `handleSubmit('buy')`. Mirror for Sell.

- [ ] **Step 5: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/OrderTicket.test.jsx`
Expected: PASS, 2 tests.

- [ ] **Step 6: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/OrderTicket.jsx \
        frontend-react/src/components/game/renderers/stocksim/OrderTicket.test.jsx
git commit -m "feat(stocksim): OrderTicket position sizer + Target/Stop chips + Broker NPC trigger"
```

---

## Task 10: MarketBriefing replaces OnboardingFlow for stock games

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/MarketBriefing.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/MarketBriefing.test.jsx`
- Modify: `frontend-react/src/components/game/renderers/StockMarketGame.jsx`

- [ ] **Step 1: Write the failing test**

Create `MarketBriefing.test.jsx`:

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MarketBriefing from './MarketBriefing';

describe('MarketBriefing', () => {
  const briefing = {
    macro_tone: 'RBI policy day. IT and banks in focus.',
    sector_mood: { IT: 'positive', Banking: 'neutral' },
    headline: '8 stocks. 22 ticks.',
    sub: 'Each tick = ~8 seconds.',
  };
  const stocks = [
    { symbol: 'TECHV', name: 'TechVista', sector: 'IT', starting_price: 215 },
    { symbol: 'BANKX', name: 'BankX', sector: 'Banking', starting_price: 320 },
  ];

  it('renders headline, sub, sector chips and stock peek', () => {
    render(<MarketBriefing briefing={briefing} stocks={stocks} onBegin={() => {}} />);
    expect(screen.getByText(briefing.headline)).toBeInTheDocument();
    expect(screen.getByText(briefing.sub)).toBeInTheDocument();
    expect(screen.getByText(/IT/)).toBeInTheDocument();
    expect(screen.getByText(/TECHV/)).toBeInTheDocument();
  });

  it('Begin button calls onBegin', () => {
    const onBegin = vi.fn();
    render(<MarketBriefing briefing={briefing} stocks={stocks} onBegin={onBegin} />);
    fireEvent.click(screen.getByRole('button', { name: /Begin/i }));
    expect(onBegin).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/MarketBriefing.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `MarketBriefing.jsx`**

```jsx
import React from 'react';
import { THEME } from './theme';

const MOOD_COLOR = { positive: THEME.gain, neutral: THEME.textMuted, negative: THEME.loss };

export default function MarketBriefing({ briefing, stocks = [], onBegin }) {
  const b = briefing || {};
  return (
    <div style={{
      background: THEME.bgPage, borderRadius: 12, padding: 24, maxWidth: 640, margin: '24px auto',
      border: `1px solid ${THEME.borderTile}`,
    }}>
      <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 700, letterSpacing: 1, marginBottom: 4 }}>
        📈 MARKET BRIEFING
      </div>
      <h2 style={{ margin: '0 0 6px', color: THEME.textPrimary, fontSize: 20 }}>{b.headline}</h2>
      <p style={{ margin: '0 0 14px', color: THEME.textMuted, fontSize: 13 }}>{b.sub}</p>

      {b.macro_tone && (
        <div style={{ background: THEME.bgTile, borderLeft: `3px solid ${THEME.accentWarm}`, padding: 10, borderRadius: 6, fontSize: 12, color: THEME.textPrimary, marginBottom: 12 }}>
          🌐 {b.macro_tone}
        </div>
      )}

      {b.sector_mood && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
          {Object.entries(b.sector_mood).map(([sec, mood]) => (
            <span key={sec} style={{
              background: THEME.bgTile, color: MOOD_COLOR[mood] || THEME.textPrimary,
              border: `1px solid ${THEME.borderTile}`, borderRadius: 14, padding: '2px 10px', fontSize: 11, fontWeight: 700,
            }}>{sec} · {mood}</span>
          ))}
        </div>
      )}

      <div style={{ fontSize: 10, color: THEME.textMuted, fontWeight: 700, marginBottom: 4 }}>STOCKS IN PLAY</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 6, marginBottom: 16 }}>
        {stocks.map(s => (
          <div key={s.symbol} style={{ background: THEME.bgTile, borderRadius: 6, padding: 6 }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: THEME.textPrimary }}>{s.symbol}</div>
            <div style={{ fontSize: 9, color: THEME.textMuted }}>{s.sector}</div>
            <div style={{ fontSize: 11, color: THEME.textPrimary }}>₹{s.starting_price}</div>
          </div>
        ))}
      </div>

      <button
        onClick={onBegin}
        style={{
          background: THEME.gain, color: '#fff', border: 'none', borderRadius: 18,
          padding: '10px 20px', fontSize: 14, fontWeight: 700, cursor: 'pointer',
        }}
      >Begin Trading →</button>
    </div>
  );
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/MarketBriefing.test.jsx`
Expected: PASS, 2 tests.

- [ ] **Step 5: Wire into `StockMarketGame.jsx` behind the flag**

Open `frontend-react/src/components/game/renderers/StockMarketGame.jsx`. At the top imports:

```jsx
import MarketBriefing from './stocksim/MarketBriefing';
import { useOrg } from '../../../contexts/OrgContext';
```

Inside the component, add a phase state:

```jsx
const { org } = useOrg() || {};
const v2Enabled = !!org?.flags?.stocksim_v2_ui;
const cfg = gameData?.minigame_config?.stock_market_config || {};
const briefing = cfg.briefing;
const [phase, setPhase] = useState(v2Enabled && briefing ? 'briefing' : 'playing');
```

Replace the existing `OnboardingFlow` mount block (currently around line 832) with:

```jsx
if (v2Enabled && phase === 'briefing') {
  return <MarketBriefing briefing={briefing} stocks={cfg.stocks || []} onBegin={() => setPhase('playing')} />;
}
// Legacy path:
if (!v2Enabled && /* existing onboarding condition */) {
  return <OnboardingFlow ... />;
}
```

(Leave the legacy `OnboardingFlow` import in place so the v1 path keeps working when the flag is off.)

- [ ] **Step 6: Lint + build sanity**

Run: `cd frontend-react && npm run lint && npm run build`
Expected: no new errors.

- [ ] **Step 7: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/MarketBriefing.jsx \
        frontend-react/src/components/game/renderers/stocksim/MarketBriefing.test.jsx \
        frontend-react/src/components/game/renderers/StockMarketGame.jsx
git commit -m "feat(stocksim): MarketBriefing replaces OnboardingFlow when stocksim_v2_ui flag is on"
```

---

## Task 11: MentorCheckIn (one-shot mid-game) + dimension counters

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/MentorCheckIn.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/MentorCheckIn.test.jsx`
- Modify: `frontend-react/src/components/game/renderers/StockMarketGame.jsx`

- [ ] **Step 1: Write the failing test**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from '../../../../i18n';
import MentorCheckIn from './MentorCheckIn';

const wrap = (ui) => <I18nextProvider i18n={i18n}>{ui}</I18nextProvider>;

describe('MentorCheckIn', () => {
  it('renders prompt + 3 reply chips when concentrated', () => {
    const state = { positions: { TECHV: 50, INFOS: 30 }, stocks_by_sector: { TECHV: 'IT', INFOS: 'IT' } };
    render(wrap(<MentorCheckIn state={state} onReply={() => {}} />));
    expect(screen.getAllByTestId(/mentor-reply-/).length).toBe(3);
  });

  it('reply calls onReply with choice id', () => {
    const onReply = vi.fn();
    const state = { positions: {}, stocks_by_sector: {} };
    render(wrap(<MentorCheckIn state={state} onReply={onReply} />));
    fireEvent.click(screen.getByTestId('mentor-reply-diversify'));
    expect(onReply).toHaveBeenCalledWith('diversify');
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/MentorCheckIn.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `MentorCheckIn.jsx`**

```jsx
import React from 'react';
import { useTranslation } from 'react-i18next';
import { THEME } from './theme';
import { mentorCheckIn } from './npcDialog';

const REPLIES = [
  { id: 'diversify', label: 'I should diversify', dim: { delayed_gratification: 5 } },
  { id: 'hold', label: 'Stay the course', dim: { resilience: 3 } },
  { id: 'take_profit', label: 'Take profit now', dim: { risk_tolerance: -5 } },
];

export default function MentorCheckIn({ state, onReply }) {
  const { t } = useTranslation();
  const line = mentorCheckIn(state);
  return (
    <div style={{
      background: '#FFF3DC', border: `1px solid ${THEME.borderTile}`, borderLeft: `4px solid ${THEME.accentWarm}`,
      borderRadius: 8, padding: 14, margin: '12px 0',
    }}>
      <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 700, marginBottom: 4 }}>🧭 MENTOR CHECK-IN</div>
      <div style={{ fontSize: 13, color: THEME.textPrimary, marginBottom: 10 }}>{t(line.key, line.props)}</div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {REPLIES.map(r => (
          <button
            key={r.id}
            data-testid={`mentor-reply-${r.id}`}
            onClick={() => onReply?.(r.id, r.dim)}
            style={{
              background: '#fff', border: `1px solid ${THEME.borderTile}`, borderRadius: 14,
              padding: '6px 12px', fontSize: 11, fontWeight: 700, color: THEME.textPrimary, cursor: 'pointer',
            }}
          >{r.label}</button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/MentorCheckIn.test.jsx`
Expected: PASS, 2 tests.

- [ ] **Step 5: Wire into `StockMarketGame.jsx`**

Inside the v2 orchestrator branch, add:

```jsx
const [mentorShown, setMentorShown] = useState(false);
const halfTick = Math.floor((cfg.tick_count || 0) / 2);
useEffect(() => {
  if (!mentorShown && state?.current_tick === halfTick) setMentorShown('open');
}, [state?.current_tick, halfTick, mentorShown]);

function handleMentorReply(choiceId, dim) {
  setMentorShown('done');
  // Persist to dimension_counters via existing /choice or telemetry endpoint:
  axios.post(`/api/run/${runId}/stocksim/mentor`, { choice: choiceId, dim_delta: dim }).catch(() => {});
}
```

Render `<MentorCheckIn ... />` when `mentorShown === 'open'`, between the persistent strip and the stock grid.

> If the `/api/run/<id>/stocksim/mentor` endpoint does not exist yet, leave the call commented with TODO and instead store the response in local state. Backend wiring is intentionally out of scope for this task — the dimension counter side-effect can be plumbed in a follow-up because telemetry already tracks reply choices.

- [ ] **Step 6: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/MentorCheckIn.jsx \
        frontend-react/src/components/game/renderers/stocksim/MentorCheckIn.test.jsx \
        frontend-react/src/components/game/renderers/StockMarketGame.jsx
git commit -m "feat(stocksim): one-shot Mentor check-in at mid-game with dimension-counter reply"
```

---

## Task 12: TradeAutopsy + autopsy.js + backend trade_log_enriched

**Files:**
- Create: `frontend-react/src/components/game/renderers/stocksim/autopsy.js`
- Test: `frontend-react/src/components/game/renderers/stocksim/autopsy.test.js`
- Create: `frontend-react/src/components/game/renderers/stocksim/TradeAutopsy.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/TradeAutopsy.test.jsx`
- Modify: `backend/engines/stocksim/scoring.py`
- Test: `backend/tests/test_stocksim_engine.py`
- Modify: `frontend-react/src/components/game/renderers/StockMarketGame.jsx`

- [ ] **Step 1: Write the failing test for autopsy.js**

Create `autopsy.test.js`:

```js
import { describe, it, expect } from 'vitest';
import { pickBestTrade, pickWorstTrade, whatWouldHaveBeenBetter } from './autopsy';

describe('autopsy', () => {
  const log = [
    { tick: 2, symbol: 'TECHV', side: 'buy', qty: 5, price: 200, realized_pnl: 0, news_at_tick: [] },
    { tick: 8, symbol: 'TECHV', side: 'sell', qty: 5, price: 220, realized_pnl: 100, news_at_tick: [{ headline: 'cloud win', reason: 'r' }] },
    { tick: 10, symbol: 'BANKX', side: 'buy', qty: 10, price: 300, realized_pnl: 0, news_at_tick: [] },
    { tick: 14, symbol: 'BANKX', side: 'sell', qty: 10, price: 280, realized_pnl: -200, news_at_tick: [] },
  ];

  it('pickBestTrade returns the highest realized P&L', () => {
    const best = pickBestTrade(log);
    expect(best.symbol).toBe('TECHV');
    expect(best.realized_pnl).toBe(100);
  });

  it('pickWorstTrade returns the lowest realized P&L', () => {
    const worst = pickWorstTrade(log);
    expect(worst.symbol).toBe('BANKX');
    expect(worst.realized_pnl).toBe(-200);
  });

  it('whatWouldHaveBeenBetter returns a lesson string keyed off side and outcome', () => {
    const lesson = whatWouldHaveBeenBetter({ symbol: 'BANKX', side: 'buy', realized_pnl: -200 }, []);
    expect(typeof lesson).toBe('string');
    expect(lesson.length).toBeGreaterThan(0);
  });

  it('returns null on empty log', () => {
    expect(pickBestTrade([])).toBeNull();
    expect(pickWorstTrade([])).toBeNull();
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/autopsy.test.js`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `autopsy.js`**

```js
export function pickBestTrade(log) {
  if (!Array.isArray(log) || log.length === 0) return null;
  const closed = log.filter(t => typeof t.realized_pnl === 'number');
  if (closed.length === 0) return null;
  return closed.reduce((a, b) => (a.realized_pnl >= b.realized_pnl ? a : b));
}

export function pickWorstTrade(log) {
  if (!Array.isArray(log) || log.length === 0) return null;
  const closed = log.filter(t => typeof t.realized_pnl === 'number');
  if (closed.length === 0) return null;
  return closed.reduce((a, b) => (a.realized_pnl <= b.realized_pnl ? a : b));
}

export function whatWouldHaveBeenBetter(trade, marketCtx = []) {
  if (!trade) return '';
  if (trade.realized_pnl > 0) {
    return `Locked in ₹${trade.realized_pnl} on ${trade.symbol}. Could you have held longer? Check the news.`;
  }
  if (trade.realized_pnl < 0) {
    if ((trade.news_at_tick || []).length === 0) {
      return `Lost ₹${Math.abs(trade.realized_pnl)} on ${trade.symbol} with no news catalyst — likely chased noise.`;
    }
    return `Lost ₹${Math.abs(trade.realized_pnl)} on ${trade.symbol}. The news was already priced in by the time you bought.`;
  }
  return `Even trade on ${trade.symbol}. No conviction either way.`;
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/autopsy.test.js`
Expected: PASS, 4 tests.

- [ ] **Step 5: Backend trade_log_enriched — write failing test**

Add to `backend/tests/test_stocksim_engine.py`:

```python
def test_finalize_run_emits_trade_log_enriched():
    from backend.engines.stocksim import scoring
    state = {
        "trade_log": [
            {"tick": 4, "symbol": "TECHV", "side": "buy", "qty": 5, "price": 215, "realized_pnl": 0},
            {"tick": 10, "symbol": "TECHV", "side": "sell", "qty": 5, "price": 225, "realized_pnl": 50},
        ],
        "quote_history": {
            "TECHV": {4: {"mid": 215}, 10: {"mid": 225}},
            "INFOS": {4: {"mid": 380}, 10: {"mid": 390}},
        },
    }
    config = {"news": [{"tick": 4, "affected_symbols": ["TECHV"], "headline": "h", "reason": "r"}],
              "stocks": [{"symbol": "TECHV", "peers": [{"symbol": "INFOS"}]}]}
    enriched = scoring.enrich_trade_log(state, config, config["news"])
    assert len(enriched) == 2
    assert enriched[0]["news_at_tick"][0]["reason"] == "r"
    assert "INFOS" in enriched[0]["peer_perf_at_tick"]
```

- [ ] **Step 6: Run, expect FAIL**

Run: `cd backend && python -m pytest tests/test_stocksim_engine.py::test_finalize_run_emits_trade_log_enriched -v`
Expected: FAIL — function does not exist.

- [ ] **Step 7: Implement `enrich_trade_log` in `backend/engines/stocksim/scoring.py`**

Add at module scope:

```python
def _peers_for(symbol, config):
    for s in config.get("stocks", []):
        if s.get("symbol") == symbol:
            return [p.get("symbol") for p in s.get("peers", []) if p.get("symbol")]
    return []


def enrich_trade_log(state, config, news):
    trade_log = state.get("trade_log", []) or []
    quote_history = state.get("quote_history", {}) or {}
    enriched = []
    for trade in trade_log:
        tick = trade.get("tick")
        if tick is None:
            continue
        ev_at_tick = [
            e for e in (news or [])
            if e.get("tick") is not None and e["tick"] <= tick <= e["tick"] + 3
            and trade.get("symbol") in (e.get("affected_symbols") or e.get("symbols") or [])
        ]
        peer_perf = {}
        for psym in _peers_for(trade.get("symbol"), config):
            qh = quote_history.get(psym, {})
            if tick in qh:
                peer_perf[psym] = qh[tick].get("mid")
        enriched.append({**trade, "news_at_tick": ev_at_tick, "peer_perf_at_tick": peer_perf})
    return enriched
```

In the existing `finalize_run(state, config, run)` (or its frontend-facing equivalent), include `trade_log_enriched` in the returned dict:

```python
    out["trade_log_enriched"] = enrich_trade_log(state, config, config.get("news") or config.get("events") or [])
```

- [ ] **Step 8: Run, expect PASS**

Run: `cd backend && python -m pytest tests/test_stocksim_engine.py -v`
Expected: PASS — including new test.

- [ ] **Step 9: Write failing test for `TradeAutopsy.jsx`**

```jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import TradeAutopsy from './TradeAutopsy';

describe('TradeAutopsy', () => {
  it('renders empty-state when no trades', () => {
    render(<TradeAutopsy final={{ trade_log_enriched: [] }} />);
    expect(screen.getByText(/No trades/i)).toBeInTheDocument();
  });

  it('renders best and worst with lesson lines', () => {
    const final = { trade_log_enriched: [
      { tick: 2, symbol: 'TECHV', side: 'sell', realized_pnl: 100, news_at_tick: [] },
      { tick: 6, symbol: 'BANKX', side: 'sell', realized_pnl: -200, news_at_tick: [] },
    ]};
    render(<TradeAutopsy final={final} />);
    expect(screen.getByTestId('autopsy-best').textContent).toMatch(/TECHV/);
    expect(screen.getByTestId('autopsy-worst').textContent).toMatch(/BANKX/);
  });
});
```

- [ ] **Step 10: Run, expect FAIL**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/TradeAutopsy.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 11: Implement `TradeAutopsy.jsx`**

```jsx
import React from 'react';
import { THEME, gainLossColor } from './theme';
import { pickBestTrade, pickWorstTrade, whatWouldHaveBeenBetter } from './autopsy';

function TradeRow({ trade, label, testId }) {
  if (!trade) return null;
  return (
    <div data-testid={testId} style={{ background: THEME.bgTile, borderRadius: 8, padding: 10, marginBottom: 8 }}>
      <div style={{ fontSize: 10, color: THEME.textMuted, fontWeight: 700 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 800, color: THEME.textPrimary }}>
        {trade.symbol} · {trade.side} · tick {trade.tick}
      </div>
      <div style={{ fontSize: 12, color: gainLossColor(trade.realized_pnl), fontWeight: 700 }}>
        ₹{trade.realized_pnl}
      </div>
      <div style={{ fontSize: 11, color: THEME.textMuted, marginTop: 4 }}>
        {whatWouldHaveBeenBetter(trade, trade.news_at_tick || [])}
      </div>
    </div>
  );
}

export default function TradeAutopsy({ final }) {
  const log = final?.trade_log_enriched || [];
  const best = pickBestTrade(log);
  const worst = pickWorstTrade(log);
  if (!best && !worst) {
    return <div style={{ padding: 12, color: THEME.textMuted, fontSize: 12 }}>No trades to autopsy.</div>;
  }
  return (
    <div style={{ background: '#fff', border: `1px solid ${THEME.borderTile}`, borderRadius: 12, padding: 14, margin: '12px 0' }}>
      <div style={{ fontSize: 11, color: THEME.textMuted, fontWeight: 700, marginBottom: 8 }}>🔬 TRADE AUTOPSY</div>
      <TradeRow trade={best} label="BEST TRADE" testId="autopsy-best" />
      <TradeRow trade={worst} label="WORST TRADE" testId="autopsy-worst" />
    </div>
  );
}
```

- [ ] **Step 12: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/TradeAutopsy.test.jsx`
Expected: PASS, 2 tests.

- [ ] **Step 13: Wire into `StockMarketGame.jsx`**

In the v2 orchestrator branch, when `state.completed` is true, render `<TradeAutopsy final={finalResult} />` BEFORE the existing `<PostGameInsights ... />` block. `finalResult` is what `/api/run/<id>/stocksim/complete` returns.

- [ ] **Step 14: Commit**

```bash
git add frontend-react/src/components/game/renderers/stocksim/autopsy.js \
        frontend-react/src/components/game/renderers/stocksim/autopsy.test.js \
        frontend-react/src/components/game/renderers/stocksim/TradeAutopsy.jsx \
        frontend-react/src/components/game/renderers/stocksim/TradeAutopsy.test.jsx \
        frontend-react/src/components/game/renderers/StockMarketGame.jsx \
        backend/engines/stocksim/scoring.py \
        backend/tests/test_stocksim_engine.py
git commit -m "feat(stocksim): TradeAutopsy + enrich_trade_log on finalize"
```

---

## Task 13: i18n keys + StockCard upgrade + orchestrator wire-up + flag flip prep

**Files:**
- Modify: `frontend-react/src/locales/en.json`
- Modify: `frontend-react/src/locales/hi.json`
- Create: `frontend-react/src/components/game/renderers/stocksim/StockCard.jsx`
- Test: `frontend-react/src/components/game/renderers/stocksim/StockCard.test.jsx`
- Modify: `frontend-react/src/components/game/renderers/StockMarketGame.jsx`
- Modify: `frontend-react/test-stocksim-e2e.mjs`

- [ ] **Step 1: Add i18n keys**

Open `frontend-react/src/locales/en.json` and add (under existing top-level structure; merge keys, do not replace the file):

```json
"stocksim": {
  "npc": {
    "analyst": {
      "stretched": "Quality looks good but P/E is {{premiumPct}}% above sector ({{pe}} vs {{sectorPe}}).",
      "cheap": "Trades {{discountPct}}% below sector P/E. Could be a value setup.",
      "fair": "Valuation in line with sector. Quality matters more here."
    },
    "journalist": {
      "flavor": "Tick {{tick}} · {{headline}} — {{reason}}"
    },
    "broker": {
      "high_risk": "Heads up — {{riskPct}}% of cash on {{symbol}}. That's a big single bet.",
      "moderate": "{{riskPct}}% on {{symbol}}. Sized fine."
    },
    "mentor": {
      "concentrated": "{{pct}}% of your book is in {{sector}}. Concentration risk worth thinking about.",
      "diversified": "Nice spread across sectors. Keep watching the laggards.",
      "no_trades": "Halfway through and no trades yet. What's holding you back?"
    }
  }
},
```

Open `frontend-react/src/locales/hi.json` and add the matching keys (Hindi):

```json
"stocksim": {
  "npc": {
    "analyst": {
      "stretched": "क्वालिटी अच्छी है लेकिन P/E सेक्टर से {{premiumPct}}% ऊपर है ({{pe}} बनाम {{sectorPe}}).",
      "cheap": "सेक्टर P/E से {{discountPct}}% नीचे ट्रेड कर रहा है। वैल्यू सेटअप हो सकता है।",
      "fair": "वैल्यूएशन सेक्टर के अनुरूप है। क्वालिटी ज़्यादा मायने रखती है।"
    },
    "journalist": {
      "flavor": "टिक {{tick}} · {{headline}} — {{reason}}"
    },
    "broker": {
      "high_risk": "ध्यान दें — {{symbol}} पर आपके कैश का {{riskPct}}%। बड़ा सिंगल बेट है।",
      "moderate": "{{symbol}} पर {{riskPct}}%। साइज़ ठीक है।"
    },
    "mentor": {
      "concentrated": "आपकी {{pct}}% बुक {{sector}} में है। कंसेंट्रेशन रिस्क पर सोचें।",
      "diversified": "सेक्टरों में अच्छी डाइवर्सिफिकेशन। पिछड़ रहे लोगों पर भी नज़र रखें।",
      "no_trades": "आधा खेल हो गया लेकिन कोई ट्रेड नहीं। क्या रोक रहा है?"
    }
  }
},
```

- [ ] **Step 2: Write failing test for `StockCard`**

```jsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StockCard from './StockCard';

const stock = { symbol: 'TECHV', name: 'TechVista', sector: 'IT' };

describe('StockCard', () => {
  it('shows star toggle and calls onStar', () => {
    const onStar = vi.fn();
    render(<StockCard stock={stock} quote={{ mid: 215 }} onOpen={() => {}} onStar={onStar} />);
    fireEvent.click(screen.getByTestId('star-TECHV'));
    expect(onStar).toHaveBeenCalledWith('TECHV');
  });

  it('shows "Why moving?" chip when last_reason set', () => {
    render(<StockCard stock={stock} quote={{ mid: 215, last_reason: 'big contract' }} onOpen={() => {}} onStar={() => {}} />);
    expect(screen.getByTestId('why-chip-TECHV').textContent).toMatch(/big contract/);
  });

  it('clicking card calls onOpen', () => {
    const onOpen = vi.fn();
    render(<StockCard stock={stock} quote={{ mid: 215 }} onOpen={onOpen} onStar={() => {}} />);
    fireEvent.click(screen.getByTestId('card-TECHV'));
    expect(onOpen).toHaveBeenCalledWith('TECHV');
  });
});
```

- [ ] **Step 3: Run, expect FAIL**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/StockCard.test.jsx`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement `StockCard.jsx`**

```jsx
import React from 'react';
import { THEME, gainLossColor } from './theme';

export default function StockCard({ stock, quote = {}, position, starred, imageUrl, onOpen, onStar }) {
  const { symbol, name, sector } = stock;
  const change = quote.last_change_pct ?? 0;
  return (
    <div
      data-testid={`card-${symbol}`}
      onClick={() => onOpen?.(symbol)}
      style={{
        background: '#fff', border: `1px solid ${THEME.borderTile}`, borderRadius: 8,
        padding: 8, cursor: 'pointer', position: 'relative',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontWeight: 800, fontSize: 13, color: THEME.textPrimary }}>{symbol}</div>
          <div style={{ fontSize: 9, color: THEME.textMuted }}>{sector}</div>
        </div>
        <button
          data-testid={`star-${symbol}`}
          onClick={(e) => { e.stopPropagation(); onStar?.(symbol); }}
          aria-label={starred ? 'unstar' : 'star'}
          style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontSize: 14, color: starred ? THEME.accentWarm : THEME.textMuted }}
        >{starred ? '★' : '☆'}</button>
      </div>

      {imageUrl && (
        <div style={{ height: 36, borderRadius: 4, marginTop: 4, background: `url(${imageUrl}) center/cover` }} />
      )}

      <div style={{ marginTop: 6, fontSize: 12, fontWeight: 700, color: gainLossColor(change) }}>
        ₹{quote.mid?.toFixed(2) ?? '—'} {change ? (change >= 0 ? '▲' : '▼') : ''}
      </div>

      {quote.last_reason && (
        <div
          data-testid={`why-chip-${symbol}`}
          style={{
            marginTop: 6, fontSize: 9, color: THEME.textMuted,
            background: THEME.bgTile, borderLeft: `2px solid ${THEME.accentWarm}`,
            padding: '2px 6px', borderRadius: 4,
          }}
        >Why? {quote.last_reason}</div>
      )}

      {position?.qty > 0 && (
        <div style={{ marginTop: 4, fontSize: 9, color: THEME.gain }}>You own {position.qty}</div>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Run, expect PASS**

Run: `cd frontend-react && npx vitest run src/components/game/renderers/stocksim/StockCard.test.jsx`
Expected: PASS, 3 tests.

- [ ] **Step 6: Wire orchestrator (`StockMarketGame.jsx`) — final v2 path**

Inside the v2 (`v2Enabled === true`) branch of `StockMarketGame.jsx`, replace any inline stock-card markup with the new orchestration:

```jsx
import PersistentStrip from './stocksim/PersistentStrip';
import StockListFilters from './stocksim/StockListFilters';
import StockCard from './stocksim/StockCard';
import CompanyDrillDown from './stocksim/CompanyDrillDown';
import TradeAutopsy from './stocksim/TradeAutopsy';
import { NpcLayerProvider } from './stocksim/NpcLayer';
// ... + MarketBriefing + MentorCheckIn already imported

// inside render, when phase === 'playing':
return (
  <NpcLayerProvider currentTick={state.current_tick || 0}>
    <PersistentStrip
      cash={state.cash} holdingsValue={state.holdings_value || 0}
      netWorth={state.net_worth || state.cash}
      pnl={pnl?.total_pnl ?? 0}
      currentTick={state.current_tick || 0} tickCount={cfg.tick_count || 22}
    />
    <StockListFilters mode={filter} setMode={setFilter} counts={counts} />
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8, margin: '8px 0' }}>
      {filteredStocks.map(s => (
        <StockCard
          key={s.symbol} stock={s}
          quote={quotes?.[s.symbol] || {}}
          position={positions?.[s.symbol]}
          starred={starred.has(s.symbol)}
          imageUrl={imageUrls[s.symbol]}
          onOpen={setOpenSymbol}
          onStar={(sym) => setStarred(prev => {
            const next = new Set(prev);
            next.has(sym) ? next.delete(sym) : next.add(sym);
            return next;
          })}
        />
      ))}
    </div>
    {/* Existing NewsTickerStrip + OrderTicket below, re-skinned in Task 1 */}
    {openSymbol && (
      <CompanyDrillDown
        stock={cfg.stocks.find(s => s.symbol === openSymbol)}
        quote={quotes?.[openSymbol] || {}}
        position={positions?.[openSymbol]}
        priceHistory={priceHistory[openSymbol] || []}
        news={cfg.events || cfg.news || []}
        imageUrl={imageUrls[openSymbol]}
        currentTick={state.current_tick || 0}
        onClose={() => setOpenSymbol(null)}
        onTrade={(side, payload) => {
          setOrderState({ ...payload, side });
          setOpenSymbol(null);
        }}
      />
    )}
    {mentorShown === 'open' && <MentorCheckIn state={state} onReply={handleMentorReply} />}
    {state.completed && <TradeAutopsy final={finalResult} />}
  </NpcLayerProvider>
);
```

`filteredStocks`, `counts`, `imageUrls`, `priceHistory` are derived from existing `state`/`cfg`/`quotes`. Compute `imageUrls` lazily on drill-down open (one fetch per symbol, cached in state).

- [ ] **Step 7: Extend `test-stocksim-e2e.mjs` smoke**

Open `frontend-react/test-stocksim-e2e.mjs`. After existing assertions, add:

```js
// v2 assertions
const stateBody = await fetchState();
const symKeys = Object.keys(stateBody.quotes || {});
if (symKeys.length === 0) throw new Error('no quotes in /state');
// At least one quote should have tick metadata; last_reason may or may not exist depending on tick.
// If we have advanced past an event tick, we expect at least one last_reason in the run.

const completeBody = await fetchComplete();
if (!Array.isArray(completeBody.trade_log_enriched)) {
  throw new Error('trade_log_enriched missing on /complete');
}
console.log('v2 smoke OK — trade_log_enriched length:', completeBody.trade_log_enriched.length);
```

- [ ] **Step 8: Run frontend tests once more**

Run: `cd frontend-react && npm test`
Expected: all stocksim tests PASS.

- [ ] **Step 9: Run backend tests**

Run: `cd backend && python -m pytest tests/test_stocksim_engine.py tests/test_stocksim_routes.py tests/test_schemas.py -v`
Expected: all PASS.

- [ ] **Step 10: Commit**

```bash
git add frontend-react/src/locales/en.json frontend-react/src/locales/hi.json \
        frontend-react/src/components/game/renderers/stocksim/StockCard.jsx \
        frontend-react/src/components/game/renderers/stocksim/StockCard.test.jsx \
        frontend-react/src/components/game/renderers/StockMarketGame.jsx \
        frontend-react/test-stocksim-e2e.mjs
git commit -m "feat(stocksim): StockCard + orchestrator wire-up + i18n keys + e2e smoke v2 assertions"
```

- [ ] **Step 11: Flag flip prep (manual, post-deploy)**

After all tasks above are merged and deployed to staging:

```bash
# Enable for staging org only
sshpass -p 'qwertY@1432o' ssh -o StrictHostKeyChecking=no root@206.189.143.244 \
  "cd /var/www/mentoapp/backend && python -c \"
import json
p = 'data/organizations.json'
d = json.load(open(p))
for org in d:
    if org['slug'] == 'staging':
        org.setdefault('flags', {})['stocksim_v2_ui'] = True
json.dump(d, open(p, 'w'), indent=2)
print('flag set on staging')
\""
sshpass -p 'qwertY@1432o' ssh -o StrictHostKeyChecking=no root@206.189.143.244 'systemctl restart mentoapp-backend'
```

After 1 week of clean staging soak (no Sentry regressions, e2e smoke green nightly), flip to default-on by editing `backend/organizations.py` to set `stocksim_v2_ui` default `True` in the org-flag schema.

---

## Self-review notes

Spec coverage check:
- §Theme tokens → Task 1.
- §MarketBriefing → Task 10.
- §PersistentStrip → Task 2.
- §StockCard + watchlist + why-moving chip → Tasks 13 + 6.
- §StockListFilters → Task 3.
- §CompanyDrillDown + 6 tabs → Tasks 8a/8b/8c.
- §OrderTicket extension → Task 9.
- §NpcLayer + npcDialog → Task 4.
- §MentorCheckIn → Task 11.
- §TradeAutopsy + autopsy.js + trade_log_enriched → Task 12.
- §Game JSON additions + schema → Task 5.
- §Backend last_reason + /state echo → Task 6.
- §Image route → Task 7.
- §i18n keys + e2e + flag flip → Task 13.
- §Test framework prerequisite → Task 0.

All decompositions from the spec are covered. Each task is bite-sized (10 sub-steps max) and ends in a commit. Type and prop names are consistent across tasks (e.g. `quote.last_reason` in Tasks 6 → 8c → 13; `trade_log_enriched` in Tasks 12 → 13 e2e).




