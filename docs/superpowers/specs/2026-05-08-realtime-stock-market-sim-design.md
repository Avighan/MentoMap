# Real-Time Stock Market Simulator — Design Spec

**Date:** 2026-05-08
**Status:** Approved
**Author:** Claude (brainstorming session with @amajumder)

## Goal

Build a real-time, server-authoritative stock market simulator (game_type=`minigame`, subtype=`stock_market`) that delivers a Zerodha/Groww-feel trading experience inside Mento. ~3-minute day-trader sprint by default, configurable to longer formats (investor-month, quarter-campaign) later. Tier 2 realism today (bid-ask spread, limit/SL/SIP, T+1 settlement, brokerage+STT, circuit breakers, FII/DII flow, India VIX) with Tier 3 hooks (options/futures/margin) reserved for a follow-up.

The simulator must align with existing Mento UI/UX — Mento color palette (#FFD166/#2D3047), Tailwind + Framer Motion, `rounded-2xl` cards, theme parity with `the-treaty` and recent narrative games — and feed the standard Mento dimension-score pipeline (PostGameInsights, skills leaderboard, report cards).

## Non-Goals (v1)

- Multiplayer / cohort live trading floors (out of scope; cohort leaderboards happen "for free" later via `/api/leaderboard/skills`).
- Options, futures, margin trading (Tier 3, deferred).
- Short-selling (defer; rejection path included).
- Real market data feed (deterministic seed-driven simulation only).
- Coaching after every trade (single end-of-session debrief instead).

## Architecture

**One Flask engine + thin server endpoints + extended existing renderer.** Per-session sandbox state lives in `RUNS` (existing pattern). Deterministic seed drives all randomness. Client owns visual playback only; server owns truth.

```
┌──────────────────────────────────────────────────────────────────┐
│  Frontend (StockMarketGame.jsx — extended)                       │
│   • Renders ticker tape, watchlist, depth ladder, P&L panel      │
│   • setInterval(tickInterval) → advances tick_index locally       │
│   • On trade: POST /trade, receives fill, updates UI              │
│   • End of last tick: POST /complete, gets dim scores + recap    │
└─────────────────┬────────────────────────────────────────────────┘
                  │ HTTPS (axios via apiClient)
┌─────────────────▼────────────────────────────────────────────────┐
│  Flask app.py routes                                             │
│   POST /api/run/<id>/stocksim/start    → seed + opening state    │
│   GET  /api/run/<id>/stocksim/state    → resume after reload     │
│   POST /api/run/<id>/stocksim/trade    → validate + fill         │
│   POST /api/run/<id>/stocksim/cancel   → cancel pending order    │
│   POST /api/run/<id>/stocksim/complete → final P&L + scoring     │
└─────────────────┬────────────────────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────────────────────┐
│  backend/engines/stock_market_engine.py (NEW)                    │
│   StockMarketEngine — pure functions, no I/O.                    │
│   Deterministic from (config, seed). Submodule split for clarity.│
└──────────────────────────────────────────────────────────────────┘
```

### Key Principles

- **Per-session sandbox** — `RUNS[run_id]['stocksim']` holds the entire session state (seed, holdings, cash, order book, dimension counters). No cross-session leakage.
- **Deterministic from seed** — `price_at(seed, symbol, tick)` is a pure function. Server can replay any tick on demand without storing the full timeline server-side; only seed + trades log persist.
- **Hybrid tick authority** — server returns deterministic seeded schedule at session start; client plays back at tick rate; trades POST to server for portfolio update + scoring; server can re-derive any tick from seed for audit/replay.
- **Reuse existing infra** — RUNS storage (multi-worker safe via `update_run`), `_PUBLIC_GAME_TYPES` whitelist, `_DISCOVER_WHITELIST`, `record_outcome`, `_compute_*_dimension_scores` pattern, `MiniGameRenderer` routing.
- **Tier-3 extension hook** — `place_order` switches on `order.type`. Today: `market | limit | stop_loss | sip`. Tomorrow: `option_buy | future_long` cases drop in without touching anything else.

## Components

### Backend

**1. `backend/engines/stock_market_engine.py` (NEW, ~600 lines)**
Pure logic. No Flask, no I/O. Resolves missing import in `test_all_19_new_engines.py:26`.

```python
class StockMarketEngine:
    def __init__(self, config: dict)             # validates config
    def validate(self) -> dict                   # → {valid, errors, warnings}
    def start_session(seed: int, profile: str)   # → SessionState
    def price_at(state, symbol, tick) -> Quote   # public; reads seed from state
    def _price_from_seed(seed, symbol, tick, cfg) -> Quote  # internal, pure
    def news_at(state, tick) -> list[NewsItem]
    def event_at(state, tick) -> Event | None    # circuit, halt, FII flow
    def place_order(state, order) -> Fill | Reject
    def cancel_order(state, order_id) -> bool
    def advance_to_tick(state, tick) -> dict     # SIPs, SL, settlement
    def compute_pnl(state) -> dict
    def score_dimensions(state) -> dict
    def replay(seed, config, trade_log) -> dict  # audit
```

State is a plain dict (JSON-serializable for RUNS).

**2. `backend/engines/stocksim/` submodule**
- `pricing.py` — `price_at`, Box-Muller-from-seed, momentum, volatility regimes, India VIX hook
- `orders.py` — order validation, matching, partial fills, T+1 settlement queue
- `events.py` — news + event scheduler (deterministic; circuit breakers, FII/DII flow)
- `charges.py` — brokerage, STT, exchange fees, GST (Tier 2)
- `scoring.py` — dimension scoring, financial_literacy tag

Why split: keeps each file focused; lets us add `options.py`, `futures.py` for Tier 3 without bloating one file.

**3. `backend/app.py` — 5 new routes (~180 lines added)**
- `POST /api/run/<id>/stocksim/start` — initialize session, return seed + initial state
- `GET  /api/run/<id>/stocksim/state` — resume after page reload
- `POST /api/run/<id>/stocksim/trade` — `{tick, symbol, side, qty, order_type, limit_price?, stop_price?}`
- `POST /api/run/<id>/stocksim/cancel` — cancel pending limit/SL order
- `POST /api/run/<id>/stocksim/complete` — finalize, compute dims, call `record_outcome`

All routes use `update_run` for persistence and reject if `state['completed']` (409, mirrors existing pattern).

**4. `backend/schemas.py` — `stock_market_v2` config validator**
Validates new game JSON shape: `tick_count`, `tick_interval_seconds`, `stocks[]`, `sectors[]`, `events[]`, `dimensions_config`, `realism_tier`. Raises `BundleValidationError` at startup if invalid.

### Frontend

**5. `frontend-react/src/components/game/renderers/StockMarketGame.jsx` — extended**
Existing file is real-time-capable. Changes:
- Replace local `randomNormal` price walk with **server-provided seed + local `price_at`** (JS port of `pricing.py`, parity-tested). Server stays authoritative.
- Add **OrderTicket modal** — qty, type (Market/Limit/SL/SIP), preview charges, confirm
- Add **DepthLadder** mini-component — 5-level bid/ask
- Add **NewsTickerStrip** — horizontal scrolling chips (matches existing `dynamic_news` pattern)
- Add **PortfolioPanel** — holdings table with LTP, P&L, % change
- Add **EventOverlay** — circuit/halt/dividend toast (reuses `TileEventOverlay` styling)
- Charts stay SVG-based (existing `PriceChart`) — no chart library dep

UI/UX theme: Mento palette (#FFD166, #2D3047), Framer Motion entrances, Tailwind, `rounded-2xl` cards.

**6. Game JSONs**
- `backend/games/stock-market-day-trader.json` (NEW) — day-trader sprint preset (~3 min, 22 ticks, 8s interval, ₹1L starting capital, 8 stocks)
- `backend/games/stock-market-simulator.json` (extend existing) — add `realism_tier: 2`, `tick_authority: hybrid`, `dimensions_config`

Both whitelisted in `_DISCOVER_WHITELIST`. Both `visible: true`. Internal `game_id` matches filename slug (per `feedback_rounds_to_negotiation_conversion` memory).

## Data Flow

### Session start
```
Client (StockMarketGame mount)
  └─ POST /api/run/<id>/stocksim/start  body: { profile: "day_trader" }

Server
  ├─ load run → validate game_type==minigame, subtype==stock_market
  ├─ seed = hash(run_id + user_id + ts) → int
  ├─ state = engine.start_session(seed, profile)
  │     · cash: 100000 (₹1L)
  │     · holdings: {}, pending_orders: [], settlement_queue: []
  │     · trade_log: [], current_tick: 0
  │     · realized_pnl: 0, dimension_counters: {…}
  ├─ update_run(id, {stocksim: state})
  └─ return { seed, opening_state, tick_schedule_meta, market_calendar }
```

### Each tick (client-driven)
```
Client setInterval (every tick_interval_seconds)
  ├─ tick_index += 1
  ├─ for each stock: locally compute price_at(seed, symbol, tick) → animate ticker
  ├─ render news_at(seed, tick) → NewsTickerStrip
  ├─ render event_at(seed, tick) → EventOverlay if any
  └─ no network call unless trade or tick_index === tick_count
```

Client's `price_at` is a deterministic JS port of server's. Tests assert parity.

### Trade
```
Client OrderTicket → confirm
  └─ POST /api/run/<id>/stocksim/trade
       body: { tick, symbol, side, qty, order_type, limit_price?, stop_price? }

Server
  ├─ load run, reject if completed (409)
  ├─ reject if tick > current_authoritative_tick + 1 (anti-cheat)
  ├─ engine.advance_to_tick(state, tick)        # lazy sweep of pending orders
  ├─ quote = engine.price_at(state, symbol, tick)
  ├─ fill_or_reject = engine.place_order(state, order, quote)
  │     · market: fills at ask (buy) / bid (sell); spread + brokerage + STT applied
  │     · limit: queued in pending_orders
  │     · stop_loss: queued, triggers when price crosses stop
  │     · sip: queued daily fixed-amount buy
  │     · check circuit_breaker, funds, holdings, T+1 settlement
  │     · update cash, holdings, settlement_queue
  │     · append to trade_log
  │     · update dimension_counters
  ├─ update_run(id, {stocksim: state})
  └─ return { status: "filled"|"queued"|"rejected", fill, charges, new_cash, new_holdings }
```

### Pending order trigger (lazy sweep)
Server's `place_order` and `complete` both call `engine.advance_to_tick(state, latest_tick)` first, firing any pending limits/SL/SIPs that should have triggered between last touch and now. Client simulates pending triggers visually for feel; server reconciles authoritatively.

### Session complete
```
Client (after tick_index === tick_count)
  └─ POST /api/run/<id>/stocksim/complete

Server
  ├─ engine.advance_to_tick(state, tick_count)   # final sweep
  ├─ engine.settle_pending(state)                # close T+1, MTM open positions
  ├─ pnl = engine.compute_pnl(state)
  ├─ dims = engine.score_dimensions(state)
  │     · risk_tolerance, delayed_gratification, strategic_thinking, financial_literacy
  ├─ record_outcome(user_id, game_id, dims, …)
  ├─ award_xp(user_id, …)
  ├─ persist final state, mark completed=true
  └─ return { pnl, dims, trade_log, recap_messages, top_moves, missed_opportunities }
```

### Cancel pending order
```
POST /api/run/<id>/stocksim/cancel  body: {order_id}
  → removes from pending_orders, returns updated state
```

**Trust boundary recap:** client can lie about anything visual. Every fill, charge, and dimension counter is recomputed server-side from `(seed, trade_log)`. Replay/audit = re-run engine over persisted trade_log; equality check confirms integrity.

**Network budget per session:** 1 start + N trades (typical 5–15) + 0–N cancels + 1 complete = under 20 round-trips for a 3-min session.

## Error Handling

### Server-side rejections (4xx with structured body)

| Code | Reason | Client behavior |
|------|--------|-----------------|
| 400 `INVALID_ORDER` | qty ≤ 0, missing limit_price for limit | Toast: "Order invalid — check quantity/price" |
| 400 `INVALID_TICK` | tick > current+1 OR < last seen | Toast: "Tick out of sync, refreshing…" → re-sync |
| 402 `INSUFFICIENT_FUNDS` | buy cost + charges > cash | Toast: "Need ₹X more — reduce qty or sell first" |
| 402 `INSUFFICIENT_HOLDINGS` | sell qty > holdings (no shorting v1) | Toast: "You only hold X shares" |
| 403 `MARKET_HALTED` | symbol hit upper/lower circuit | Banner: "⛔ TECHV halted (upper circuit)" |
| 403 `SETTLEMENT_PENDING` | sell shares bought today (T+1) | Toast: "Bought today, sellable tomorrow (T+1)" |
| 409 `SESSION_COMPLETED` | trade after complete | Redirect to recap |
| 409 `STALE_RUN` | RUNS evicted | Toast: "Session expired — start fresh" |
| 422 `BUNDLE_INVALID` | game JSON failed validate_bundle | 502 at startup (existing) |
| 429 `RATE_LIMIT` | > 30 trades/sec from one client | Toast: "Slow down" |
| 500 `ENGINE_ERROR` | unexpected exception | Logged; toast; session continues from last persisted state |

All rejections return `{error_code, message, recoverable: bool}`. Client never crashes the session.

### Client-side resilience

- **Network drop mid-tick**: client keeps animating from cached schedule. Trade attempts queue locally; on reconnect, POST with original `tick`. Server validates (rejects if too stale, expected). UI shows "📡 reconnecting…".
- **Tab backgrounded**: `setInterval` throttles. On `visibilitychange` resume, fast-forward visually; trades during gap aren't possible (no input fires when hidden).
- **Page reload mid-session**: client GETs `/api/run/<id>/stocksim/state` → resumes from current_tick, holdings, cash. Trade log is server-truth.
- **Server restart mid-session**: RUNS in-memory cap is 500 (per existing infra). If evicted → `STALE_RUN`. v1 accepts this (matches existing app behavior).

### Engine guards

- **Determinism guard**: internal `_price_from_seed(seed, symbol, tick, cfg)` is purely functional. Pinned-value test locks `_price_from_seed(42, "TECHV", 10, default_cfg)` forever. Public `price_at(state, …)` is a thin wrapper.
- **NaN/inf guard**: prices floored at ₹0.01, capped at 10× starting price. Volume floored at 0.
- **Charge sanity guard**: total charges per trade ≤ 5% of trade value. `EngineConfigError` at session start otherwise.
- **Dimension counter clamp**: counters in [-100, 100] before normalization to dimension scores 0-100.

### Audit / replay

Every session persists `{seed, config_hash, trade_log}`. `engine.replay(seed, config, trade_log)` recomputes final P&L + dimensions. v1 ships as `backend/scripts/stocksim_audit.py`, not UI.

### Bundle validation at startup

`validate_bundle` extended to check stock_market config when `subtype == "stock_market"`:
- `tick_count >= 1`
- each stock has `symbol`, `name`, `sector`, `starting_price > 0`, `volatility ∈ [0, 1]`
- `events[]` reference real symbols/sectors
- `dimensions_config` uses known dimension keys

Failure → `BundleValidationError` → gunicorn 502 (matches `feedback_new_game_type_checklist`).

## Testing

### Unit — `backend/tests/test_stock_market_engine.py` (NEW, ~25 tests)

**Determinism**
- `test_price_at_is_deterministic`
- `test_price_from_seed_pinned_values` — golden-value `_price_from_seed(42, "TECHV", 10, default_cfg) == <fixed>`
- `test_news_at_pinned_values`
- `test_event_at_circuit_breaker_fires_on_known_seed`

**Pricing**
- `test_price_floors_at_minimum`
- `test_price_caps_at_10x`
- `test_bid_ask_spread_widens_on_high_volatility`
- `test_momentum_persists_short_term`

**Order matching**
- `test_market_buy_fills_at_ask`
- `test_market_sell_fills_at_bid`
- `test_limit_buy_below_ask_queues`
- `test_limit_buy_above_ask_fills_immediately`
- `test_stop_loss_triggers_on_cross`
- `test_sip_executes_on_scheduled_tick`
- `test_insufficient_funds_rejected`
- `test_t1_settlement_blocks_same_day_sell`
- `test_t1_settlement_allows_next_day_sell`
- `test_circuit_breaker_blocks_orders`

**Charges**
- `test_charges_breakdown`
- `test_charges_capped_at_5pct`

**Scoring**
- `test_dimension_risk_tolerance_scales_with_position_size`
- `test_dimension_delayed_gratification_rewards_holding`
- `test_dimension_strategic_thinking_rewards_diversification`
- `test_dimension_financial_literacy_tracks_correct_order_types`

**Replay**
- `test_replay_reproduces_pnl`

### Schema — `backend/tests/test_schemas.py` (extend)
- `test_stock_market_v2_valid_bundle_passes`
- `test_stock_market_v2_missing_tick_count_raises`
- `test_stock_market_v2_event_references_unknown_symbol_raises`
- `test_stock_market_v2_invalid_dimension_key_raises`

### Integration — `backend/tests/test_stocksim_routes.py` (NEW, ~8 tests)

Flask test client, real RUNS (in-memory), no HTTP server.

- `test_full_session_happy_path`
- `test_trade_in_future_tick_rejected`
- `test_trade_after_complete_rejected`
- `test_session_resume_after_simulated_reload`
- `test_concurrent_trades_serialize`
- `test_pending_limit_triggers_on_advance`
- `test_record_outcome_called_on_complete`
- `test_dimension_scores_match_engine_directly`

### Frontend — `frontend-react/src/tests/StockMarketGame.test.jsx` (NEW, ~6 tests)

Vitest + RTL.

- `renders_ticker_and_portfolio_on_mount`
- `setInterval_advances_tick` (fake timers)
- `client_price_at_matches_server` — load `backend/tests/fixtures/stocksim_seed_42.json`; client `priceFromSeed(42, "TECHV", 10, defaultCfg)` matches server's pinned values
- `order_ticket_submits_with_correct_payload`
- `circuit_breaker_overlay_renders_on_event`
- `complete_navigates_to_postgame`

### Game JSON validation — `backend/tests/test_game_jsons.py` (extend)
- `test_stock_market_simulator_validates`
- `test_stock_market_day_trader_validates`
- `test_both_in_discover_whitelist_for_students`

### E2E smoke — `frontend-react/test-stocksim-e2e.mjs` (NEW)
Playwright-style, follows existing pattern (`test-deep.mjs`). One full happy-path session against local dev. Run on demand.

### Coverage targets
- Engine module: **100% line coverage**
- Routes: every error code path hit at least once
- Renderer: smoke + critical interactions

### Test fixtures
- `backend/tests/fixtures/stocksim_seed_42.json` — pinned prices for seed 42, ticks 0–22, all 8 stocks. Source of truth for client/server parity tests.
- Generated by `backend/scripts/generate_stocksim_fixtures.py` (committed alongside).

### Manual verification (post-deploy)
1. `curl https://simulations.mentomap.com/api/games | grep stock-market-day-trader` → present, `visible: true`
2. Login as `demo_student` → game appears, not locked
3. Play full session → trades execute, P&L updates, recap shows dimensions
4. `journalctl -u mentoapp-backend -n 100` → no errors

## Configuration: Day-Trader Profile (default v1)

```jsonc
{
  "tick_count": 22,
  "tick_interval_seconds": 8,
  "starting_capital": 100000,
  "realism_tier": 2,
  "tick_authority": "hybrid",
  "settlement": "T+1",
  "shorting_enabled": false,
  "circuit_breaker_pct": [5, 10, 20],
  "charges": {
    "brokerage_per_trade": 20,
    "stt_buy_pct": 0.001,
    "stt_sell_pct": 0.001,
    "exchange_pct": 0.0000345,
    "gst_pct": 0.18
  },
  "dimensions_config": {
    "risk_tolerance": { "weight": 1.0 },
    "delayed_gratification": { "weight": 1.0 },
    "strategic_thinking": { "weight": 1.0 },
    "financial_literacy": { "weight": 1.0, "is_tag": true }
  }
}
```

Future profiles (`investor_month`, `quarter_campaign`) override `tick_count`, `tick_interval_seconds`, `settlement`, etc., without engine changes.

## Open Questions / Future Work

- **Tier 3 (deferred):** options chain, futures, margin, F&O strategy templates. Engine extension hook is in `place_order` switch; new submodules `options.py`, `futures.py`.
- **Multiplayer trading floor (deferred):** would use `multiplayer_engine.py` pattern with shared seed across cohort.
- **Real market data feed (deferred):** out of scope; deterministic simulation only for v1.
- **Cohort leaderboards:** ride existing `/api/leaderboard/skills` once dimensions emit.

## Acceptance Criteria

- [ ] `from engines.stock_market_engine import StockMarketEngine` works (resolves `test_all_19_new_engines.py:26`).
- [ ] All ~25 engine unit tests pass.
- [ ] All 8 route integration tests pass.
- [ ] All 6 frontend tests pass.
- [ ] Both game JSONs (`stock-market-day-trader.json`, `stock-market-simulator.json`) validate at startup.
- [ ] Both appear in `/api/games` for `demo_student`.
- [ ] One full happy-path session emits `risk_tolerance`, `delayed_gratification`, `strategic_thinking`, `financial_literacy` dimension scores into `record_outcome`.
- [ ] Replay script (`backend/scripts/stocksim_audit.py`) reproduces a stored session's P&L exactly.
- [ ] No regressions in existing tests.
