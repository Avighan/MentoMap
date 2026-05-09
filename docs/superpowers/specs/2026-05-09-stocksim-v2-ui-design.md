# Stocksim v2 UI — Design Spec

**Date:** 2026-05-09
**Branch:** `audit-followups` (or new `stocksim-v2-ui`)
**Builds on:** `2026-05-08-realtime-stock-market-sim-design.md` (Phase B shipped)
**Status:** Approved by user, ready for implementation plan

---

## Goal

Make the two stock games (`stock-market-day-trader`, `stock-market-simulator`) less confusing and more engaging without losing the live-tick trader feel. Borrow the Mento simulation visual theme so the games stop feeling like a separate product. Add per-stock fundamentals/technicals/news drill-down, four NPCs, and an end-of-game trade autopsy.

## Architecture

The Tier-2 dense layout stays — the user explicitly chose density over consolidation. The redesign is **additive**: warm-amber re-skin, a click-through company drill-down modal with 6 tabs, four NPC personas voiced contextually, a persistent cash/PnL strip, an upgraded order ticket with risk sizing, plus 8 layered features (watchlist, filters, "why moving" chips, mid-game mentor check-in, market briefing intro, trade autopsy).

`StockMarketGame.jsx` becomes a thin orchestrator (~400 lines). All new pieces are single-purpose files in `frontend-react/src/components/game/renderers/stocksim/`. Server stays authoritative for prices, fills, ticks, scoring (already shipped Phase B). New backend additions are small and additive: per-stock metadata in game JSON, an image route, enriched trade log on `/complete`, and reason stamping on quotes.

## Tech Stack

- **Frontend:** React + Vite, framer-motion (existing), Tailwind utility classes + inline `style` for theme tokens (existing pattern).
- **Backend:** Flask `app.py` route additions, `engines/stocksim/*` extensions, `story_image_service.py` (DALL-E pipeline already used by simulation games).
- **i18n:** `react-i18next`, `locales/en.json` + `locales/hi.json`.
- **Testing:** Vitest + React Testing Library on the frontend; pytest on backend stocksim engine; `test-stocksim-e2e.mjs` for production smoke.

---

## Scope

### In scope

- Visual re-skin of `StockMarketGame.jsx` to the warm-amber Mento simulation theme.
- Replace `OnboardingFlow` for stock games with a stock-specific `MarketBriefing`.
- Per-stock click-through to a 6-tab drill-down modal.
- AI hero image per company via cached DALL-E call.
- 4 NPC personas (Analyst · Journalist · Broker · Mentor).
- Persistent strip: Cash · Holdings · Net Worth · P&L · Tick.
- Order-ticket upgrade: live position sizer + Target/Stop quick chips.
- Watchlist star + 4 quick filters.
- "Why is it moving?" chip on cards on >1% tick moves.
- Mid-game Mentor check-in at tick = floor(0.5 × tick_count).
- End-game Trade Autopsy on the recap screen.
- Backward-compatible JSON schema additions; both games migrate together.

### Out of scope

- Layout reflow into tabs/zones (user kept current density).
- Backend tick engine changes (server already authoritative).
- New game types or game-engine subtypes.
- Branching/dating-sim mechanics.

---

## Theme tokens

Two visual primitives carry family resemblance with the simulation games:

| Token | Value | Use |
|---|---|---|
| `bg.page` | `#FFF9EE` | Main page background |
| `bg.tile` | `#FFF3DC` | Cards, tile fills |
| `border.tile` | `#F5E6C8` | Tile borders, dividers |
| `text.primary` | `#633806` | Body text |
| `text.muted` | `#854F0B` | Secondary, labels |
| `accent.warm` | `#B46B1E` | Banners, highlights, dashed lines |
| `numeric.gain` | `#0F6E56` | Positive numbers, BUY button |
| `numeric.loss` | `#A32D2D` | Negative numbers, SELL button |
| `numeric.neutral` | `#633806` | Zero / neutral state |

These are codified in `frontend-react/src/components/game/renderers/stocksim/theme.js` and consumed by every new sub-component. Existing simulation files (`CashflowStrip.jsx`, `SimulationRenderer.jsx`) already use the same palette; this just makes it explicit.

---

## Components

Each component is one file with one responsibility. Props-driven, no shared mutable state. New folder structure:

```
frontend-react/src/components/game/renderers/stocksim/
├── theme.js                 (NEW)  warm-amber palette tokens
├── MarketBriefing.jsx       (NEW)  pre-game intro
├── PersistentStrip.jsx      (NEW)  cash/pnl/tick bar
├── StockCard.jsx            (NEW)  extracted from StockMarketGame.jsx
├── StockListFilters.jsx     (NEW)  All/Gainers/Losers/Mine/⭐
├── CompanyDrillDown.jsx     (NEW)  6-tab modal shell
├── tabs/ChartTab.jsx        (NEW)
├── tabs/FundamentalsTab.jsx (NEW)
├── tabs/TechnicalsTab.jsx   (NEW)
├── tabs/NewsTab.jsx         (NEW)
├── tabs/PeersTab.jsx        (NEW)
├── tabs/AboutTab.jsx        (NEW)
├── OrderTicket.jsx          (EXTEND) add position sizer + Target/Stop chips
├── DepthLadder.jsx          (existing — re-skin only)
├── NewsTickerStrip.jsx      (existing — re-skin only)
├── PortfolioPanel.jsx       (existing — re-skin only)
├── EventOverlay.jsx         (existing — re-skin only)
├── NpcLayer.jsx             (NEW)  single mounted NPC dispatcher
├── MentorCheckIn.jsx        (NEW)  mid-game banner
├── TradeAutopsy.jsx         (NEW)  recap-screen card
├── npcDialog.js             (NEW)  pure function library
├── technicals.js            (NEW)  pure RSI/MA/support-resistance
└── autopsy.js               (NEW)  pure best/worst-trade picker
```

### Component contracts

| Component | Job | Inputs | Output / event |
|---|---|---|---|
| `MarketBriefing` | 30-sec pre-game intro: macro tone, sector mood, 8 stocks at a glance, "Begin" CTA. Replaces `OnboardingFlow` for stock games only. | `briefing` block from `stock_market_config` | `onBegin()` callback |
| `PersistentStrip` | Sticky bar (top on desktop, bottom on mobile): Cash · Holdings · Net Worth · P&L · Tick `n/N`. | `pnl`, `state.cash`, `state.current_tick`, `tick_count` | none |
| `StockCard` | Compact card per stock. Adds: ⭐ watchlist toggle, "Why moving?" chip when `quote.last_reason` is set, AI image thumbnail (lazy-loaded). Click opens drill-down. | `stock`, `quote`, `position`, `starred`, `imageUrl` | `onOpen(symbol)`, `onStar(symbol)` |
| `StockListFilters` | Chip row at top of stock grid: All · Gainers · Losers · Mine · ⭐. | `mode`, `counts` | `setMode(mode)` |
| `CompanyDrillDown` | Modal shell hosting the 6 tab panels. Lazy-fetches AI hero image on open. Closes on backdrop click / Esc. **Does not pause the server tick clock.** Modal contents repoll every `tick_interval_ms`. | `symbol`, `stock`, `quote`, `fundamentals`, `technicals`, `news`, `peers`, `about`, `position`, `imageUrl` | `onClose()`, `onTrade(side, payload)` |
| `tabs/ChartTab` | Larger chart with MA-20 dashed overlay + RSI label. Re-uses `priceFromSeed` for between-poll smoothing. | `priceHistory[]`, `indicators` | none |
| `tabs/FundamentalsTab` | Sections: Valuation (P/E, P/B, EV/EBITDA, PEG) · Profitability (EPS, ROE, ROCE, Debt/Eq) · Size & Ownership (cap, free float, promoter, FII/DII) · 4-quarter revenue bar trend · Ranges & Signals (52w, div yield, beta, volume × avg). Footer: Analyst NPC verdict. | `fundamentals` | none |
| `tabs/TechnicalsTab` | RSI dial · Support/Resistance lines · MA-20 / MA-50 crossover state · Volume × avg. All derived client-side from `priceHistory` via `technicals.js`. | `priceHistory[]`, `stockCfg` | none |
| `tabs/NewsTab` | Per-stock news log (filtered from game-wide `news[]` by `affected_symbols`). Each item: timestamp · headline · Journalist NPC line. | `news[]`, `currentTick` | none |
| `tabs/PeersTab` | Mini comparison table: this stock + 2 sector peers. Columns: P/E, growth_yoy, ROE, market cap. | `peers[]` | none |
| `tabs/AboutTab` | AI hero image (large) + business description + key people. | `about`, `imageUrl` | none |
| `OrderTicket` (extend) | Existing component. Add: live "Position sizer" line under qty input ("@ qty=10 → ₹2,150 risked, 2.1% of cash. +5% = +₹107.50, −5% = −₹107.50"). Add 2 chip buttons "Target +5% / Stop −3%" that pre-attach OCO orders to the buy. Broker NPC line under chips when target/stop active. | `quote`, `cash`, payload state | `onSubmit(payload)` |
| `NpcLayer` | Single mounted component holding NPC dispatch logic + cooldowns. Provides React context: `npc.say(persona, key, props)`. Renders inline chips (Broker/Journalist/Analyst) or banner (Mentor). | `state`, recent trades, recent news, current tick | imperative `say()` |
| `MentorCheckIn` | Banner that opens once at tick = floor(0.5 × tick_count). 1 question, 3 reply chips (e.g., "Diversify", "Keep concentrated", "Take profit"). Records reply to `state.dimension_counters` (delayed_gratification ± 5, risk_tolerance ± 5). | `state`, `tick` | `onReply(choiceId)` |
| `TradeAutopsy` | Recap-screen card. Walks through best trade, worst trade, "what would have been better" using `trade_log_enriched`. Renders BEFORE `PostGameInsights`. | `final.trade_log_enriched`, `final.news` | none |
| `npcDialog.js` | Pure function library. Maps `(persona, signal) → text`. Functions: `analystVerdict(fundamentals)`, `journalistFlavor(newsItem)`, `brokerOnTrade(order, riskPct)`, `mentorCheckIn(state)`. Deterministic, testable, no I/O. All strings via `t()` keys. | data | string or `{key, props}` for i18n |
| `technicals.js` | Pure: `rsi(prices, period=14)`, `ma(prices, period)`, `supportResistance(prices, lookback=10)`, `crossover(maShort, maLong)`. | `prices[]` | numeric/string outputs |
| `autopsy.js` | Pure: `pickBestTrade(log)`, `pickWorstTrade(log)`, `whatWouldHaveBeenBetter(trade, marketCtx)`. | `trade_log_enriched`, `news` | `{best, worst, lessons[]}` |

### NPC voice rules

- **One NPC visible at a time, max.** Enforced in `NpcLayer`.
- **Broker:** trade nudges. Cooldown 4 ticks between nudges. Triggered on big position-size warnings, repeat trades in same symbol, target/stop suggestions.
- **Analyst:** fundamentals verdict. Visible only inside `CompanyDrillDown` (Fundamentals tab footer + top header line).
- **Journalist:** news flavor. Visible only on news items in `NewsTab` and on the global news ticker strip.
- **Mentor:** mid-game check-in. Exactly once per game at `tick = floor(tick_count / 2)`. Bigger banner; pauses no game state.

---

## Data flow

### Per tick (every `tick_interval_ms`)

```
client → GET /api/run/<id>/stocksim/state
server: lazy advance to wall-clock tick, return:
  {
    state, pnl, halted_symbols, event,
    quotes: { [symbol]: { mid, bid, ask, volume, last_reason? } },
    tick_count
  }

PersistentStrip reads (state, pnl, current_tick, tick_count)
StockCard[symbol] reads (stock, quotes[symbol], position[symbol], starred[symbol])
  if quotes[symbol].last_reason → render "Why moving?" chip
NpcLayer subscribes to:
  - quote tick deltas (Broker on big moves)
  - new event (Journalist on news)
  - tick == tick_count/2 (Mentor exactly once)
  - trade fill (Broker on position size)
```

### On stock card click

```
open CompanyDrillDown(symbol)
  fetch GET /api/games/<game_id>/stock/<symbol>/image
    → { image_url } (cached) | 202 generating | fallback to sector-color tile
  Tabs read:
    Chart        → priceHistory + indicators (computed in technicals.js)
    Fundamentals → stock_market_config.stocks[i].fundamentals (static)
    Technicals   → derived from priceHistory via technicals.js
    News         → news[].filter(n => n.affected_symbols.includes(symbol))
    Peers        → stock_market_config.stocks[i].peers[] (static)
    About        → stock_market_config.stocks[i].about (static)
  NPC verdicts (Analyst, Journalist) come from npcDialog.js
```

### On `/complete`

```
client → POST /api/run/<id>/stocksim/complete
server: scoring.finalize_run() emits:
  {
    pnl, dimensions, recap_messages,
    trade_log_enriched: [
      { tick, symbol, qty, price, side,
        news_at_tick: [...], peer_perf_at_tick: {...} }
    ]
  }

TradeAutopsy renders best/worst trade picks (autopsy.js, pure client)
PostGameInsights renders below
```

---

## Backend changes (additive)

### 1. Game JSON additions

`backend/games/stock-market-day-trader.json` and `stock-market-simulator.json` extend `minigame_config.stock_market_config`:

```json
{
  "briefing": {
    "macro_tone": "RBI policy day. IT &amp; banks in focus.",
    "sector_mood": { "IT": "positive", "Banking": "neutral", "..." : "..." },
    "headline": "8 stocks. 22 ticks. Trade smart.",
    "sub": "Each tick = ~8 seconds. Watch news. Don't chase."
  },
  "stocks": [
    {
      "symbol": "TECHV",
      "name": "TechVista",
      "sector": "IT",
      "starting_price": 215,
      "volatility": 0.04,
      "fundamentals": {
        "pe": 28.4, "pb": 5.6, "ev_ebitda": 19.2, "peg": 1.4,
        "eps_ttm": 7.58, "roe": 22.1, "roce": 25.4, "debt_equity": 0.12,
        "market_cap_cr": 420000, "free_float_pct": 42, "promoter_pct": 58,
        "fii_pct": 22, "dii_pct": 12,
        "quarterly_revenue_cr": [9400, 9820, 10250, 11140],
        "fifty_two_week_high": 232.10, "fifty_two_week_low": 178.40,
        "div_yield_pct": 1.2, "beta": 1.18, "volume_x_avg": 2.4,
        "sector_pe": 24.0
      },
      "peers": [
        { "symbol": "INFOS", "name": "InfoSwift", "pe": 24.0, "growth_yoy": 14, "roe": 25.0, "market_cap_cr": 720000 },
        { "symbol": "WIPCO", "name": "WipCo", "pe": 21.5, "growth_yoy": 9, "roe": 18.0, "market_cap_cr": 280000 }
      ],
      "about": {
        "description": "Mid-cap IT services firm focused on cloud + AI integration for enterprise clients.",
        "key_people": [{ "role": "CEO", "name": "R. Iyer" }],
        "founded": 1998, "hq": "Bengaluru"
      },
      "image_prompt": "modern server racks glowing blue, neon city skyline behind, semi-realistic editorial illustration"
    }
  ],
  "events": [
    {
      "tick": 4,
      "headline": "TechVista wins ₹500Cr govt cloud contract",
      "affected_symbols": ["TECHV"],
      "reason": "Large new contract → revenue visibility lifts price",
      "impact": { "TECHV": +0.025 }
    }
  ]
}
```

### 2. `engines/stocksim/events.py`

When `event_at(state, tick)` returns an event, stamp `state["recent_reasons"][symbol] = {tick, reason}` for each affected symbol. `/state` route reads this and includes it in `quotes[sym].last_reason` if `tick - last_reason.tick <= 2` (chip auto-fades after 2 ticks).

### 3. `engines/stocksim/scoring.py`

In `finalize_run(state, config, run)`, walk `state["trade_log"]` and emit `trade_log_enriched`:

```python
def enrich_trade_log(state, config, news):
    enriched = []
    for trade in state["trade_log"]:
        tick = trade["tick"]
        ev_at_tick = [e for e in news if e["tick"] <= tick <= e["tick"] + 3]
        enriched.append({
            **trade,
            "news_at_tick": ev_at_tick,
            "peer_perf_at_tick": {p: state["quote_history"][p][tick]["mid"]
                                  for p in config_peers_for(trade["symbol"], config)},
        })
    return enriched
```

Best/worst trade picking stays client-side (`autopsy.js`).

### 4. `backend/app.py`

New route:

```
GET /api/games/<game_id>/stock/<symbol>/image
  → { image_url } if cached
  → 202 { status: "generating" } if currently being generated
  → falls back to sector-color tile if 2 retries fail
  Implementation: story_image_service.get_or_generate(
      prompt=stock.image_prompt,
      style="semi-realistic",
      cache_key=f"stocksim:{game_id}:{symbol}",
  )
```

### 5. `backend/schemas.py`

Extend `stock_market_config` JSON schema with the new fields. All additions optional → backward-compatible. Validator: missing `fundamentals` → empty object; missing `peers` → `[]`; missing `image_prompt` → fallback sector tile only.

---

## Frontend orchestration

`StockMarketGame.jsx` shrinks from ~846 lines to ~400. New shape:

```jsx
// pseudocode
function StockMarketGame({ gameData, runId, ... }) {
  const [phase, setPhase] = useState('briefing'); // briefing | playing | mentor | complete
  const [openSymbol, setOpenSymbol] = useState(null);
  const [filter, setFilter] = useState('all');
  const [starred, setStarred] = useState(new Set());
  const { state, quotes, pnl, ... } = useStocksimPolling(runId);

  if (phase === 'briefing') {
    return <MarketBriefing briefing={cfg.briefing} onBegin={() => setPhase('playing')} />;
  }

  return (
    <NpcLayerProvider state={state} quotes={quotes} ... >
      <PersistentStrip pnl={pnl} state={state} tickCount={cfg.tick_count} />
      <StockListFilters mode={filter} setMode={setFilter} counts={...} />
      <div className="grid">
        {filteredStocks.map(s => (
          <StockCard
            key={s.symbol} stock={s} quote={quotes[s.symbol]}
            position={positions[s.symbol]} starred={starred.has(s.symbol)}
            onOpen={setOpenSymbol} onStar={toggleStar}
          />
        ))}
      </div>
      <NewsTickerStrip news={cfg.news_strip} />
      <OrderTicket ... />
      {openSymbol && (
        <CompanyDrillDown
          symbol={openSymbol} stock={...} fundamentals={...}
          peers={...} about={...} imageUrl={imageUrls[openSymbol]}
          onClose={() => setOpenSymbol(null)}
        />
      )}
      {phase === 'mentor' && (
        <MentorCheckIn state={state} onReply={handleMentorReply} />
      )}
      {state.completed && (
        <>
          <TradeAutopsy final={finalResult} />
          <PostGameInsights ... />
        </>
      )}
    </NpcLayerProvider>
  );
}
```

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| DALL-E generation latency on first open | Lazy fetch; modal renders with shimmer placeholder; falls back to sector-color tile after 2 retries. Pre-warm during MarketBriefing for 2 most-mentioned stocks. |
| Game JSON bloat (~6KB per game) | Acceptable. Validated by `validate_all_games.py`. |
| NPC chatter overwhelming the screen | Single-NPC-on-screen rule + cooldowns enforced in `NpcLayer`. Mentor exactly once. Broker max 1 per 4 ticks. |
| Drill-down modal blocks live ticks | Modal does NOT pause tick clock (server-authoritative). Quotes inside modal also poll. Timer continues. |
| Hindi i18n for NPC lines | All NPC strings live in `locales/{en,hi}.json` keyed `stocksim.npc.<persona>.<key>`. No hard-coded English. |
| Two stock games getting out of sync | Both share renderer + `stock_market_config` schema; differences are config-only (Tier-1 vs Tier-2 already a flag). |
| Existing telemetry stash conflict | Telemetry stash is unrelated to UI files; rebases cleanly. |

---

## Testing strategy

### Pure functions (vitest)

- `npcDialog.js`: deterministic output for fixed inputs (analyst verdict map, broker risk thresholds).
- `technicals.js`: RSI/MA/support-resistance match reference fixture (small input arrays with hand-computed expected values).
- `autopsy.js`: best/worst trade picker on synthetic `trade_log_enriched`.

### Component (vitest + React Testing Library)

- `MarketBriefing` — renders briefing copy, "Begin" calls `onBegin`.
- `CompanyDrillDown` tabs — each tab renders its sections without crashing on empty data.
- `TradeAutopsy` — renders best+worst with synthetic input; renders empty-state when no trades.
- `PersistentStrip` — formats negative numbers and tick counts correctly.
- `NpcLayer` — only one NPC visible; cooldowns honored across simulated ticks.
- `MentorCheckIn` — fires exactly once at tick = `floor(tick_count/2)`.

### Backend (pytest)

- `test_stocksim_engine.py` extended: `last_reason` propagates to quotes for 2 ticks after event; missing `affected_symbols` falls back gracefully; `trade_log_enriched` emitted on `finalize_run`.
- `test_app_stocksim.py` (new): `/api/games/<id>/stock/<sym>/image` returns cached URL on 2nd call; 202 on first call if async; 404 on unknown symbol.

### E2E (`test-stocksim-e2e.mjs`)

- Add assertion: `/state` includes `quotes[sym].last_reason` after an event tick (when scripted).
- Add assertion: `/complete` returns `trade_log_enriched`.
- Existing assertions preserved.

---

## Rollout

Single feature flag `stocksim_v2_ui` (org-level, follows the `mystery_room_enabled` pattern). Defaults off → opt in for staging org → flip default-on after one week of staging soak with no regressions.

When the flag is off, `StockMarketGame.jsx` falls through to the existing v1 layout. When on, mounts the new orchestrator. Both paths share the same backend; there is no v1/v2 server divergence.

---

## Decomposition (preview for the implementation plan)

The plan that follows this spec will break this into ~10 tasks, roughly:

1. Theme tokens + re-skin existing files (no new components yet).
2. `PersistentStrip` + glue into existing `StockMarketGame.jsx`.
3. `StockListFilters` + watchlist state + glue.
4. `npcDialog.js` + `NpcLayer` (Broker + Journalist signals first).
5. Game JSON schema additions + 2 game JSON updates + `schemas.py` + validator pass.
6. Backend `last_reason` propagation + `/state` echo + tests.
7. Backend image route + `story_image_service` integration + tests.
8. `CompanyDrillDown` shell + 6 tab files (Chart, Fundamentals, Technicals, News, Peers, About).
9. `OrderTicket` upgrade (position sizer + Target/Stop chips) + Broker NPC integration.
10. `MarketBriefing` + replace `OnboardingFlow` for stock games.
11. `MentorCheckIn` + dimension counter side-effects.
12. `TradeAutopsy` + `autopsy.js` + backend `trade_log_enriched` + recap glue.
13. i18n keys (en + hi) + final integration test + flag flip prep.

Final task is a code-review pass + production deploy via the same workflow as Phase B.

---

## Open questions / deferred decisions

None. Every decision called out in the brainstorm was answered:

- Layout: keep current density (user choice).
- Theme: warm-amber Mento simulation (matches `CashflowStrip`/`SimulationRenderer`).
- Drill-down: modal, 6 tabs (user accepted modal over full-page).
- Add-ons: all 8 included.
- NPCs: 4 personas with cooldown rules.
- Images: lazy DALL-E with sector-tile fallback.
- Telemetry stash: unrelated, rebases clean.
- Rollout: flag-gated, staging soak before default-on.
