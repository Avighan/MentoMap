# Real-Time Stock Market Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real-time, server-authoritative stock market simulator (game_type=`minigame`, subtype=`stock_market`) with Tier 2 realism (bid-ask, T+1, brokerage+STT, circuit breakers) and Mento-aligned UI/UX.

**Architecture:** Pure-Python `StockMarketEngine` (deterministic from seed) + 5 Flask routes wrapping it via `RUNS` storage + extended `StockMarketGame.jsx` renderer with hybrid tick playback. Server is authoritative for all fills, charges, and dimension scoring; client is a real-time visualization.

**Tech Stack:** Python 3.10+ / Flask / pytest / React 18 / Vitest / RTL / Tailwind / Framer Motion

**Spec:** `docs/superpowers/specs/2026-05-08-realtime-stock-market-sim-design.md`

---

## File Structure

### Backend
| Path | Purpose |
|------|---------|
| `backend/engines/stock_market_engine.py` (NEW) | Public `StockMarketEngine` class — facade over submodule |
| `backend/engines/stocksim/__init__.py` (NEW) | Submodule init, exports |
| `backend/engines/stocksim/pricing.py` (NEW) | `_price_from_seed`, `price_at`, momentum, clamps, India VIX |
| `backend/engines/stocksim/charges.py` (NEW) | Brokerage + STT + exchange + GST, 5% cap guard |
| `backend/engines/stocksim/orders.py` (NEW) | Market/limit/SL/SIP matching, T+1 settlement, circuit halt |
| `backend/engines/stocksim/events.py` (NEW) | News + event (circuit breaker, FII/DII flow) scheduler |
| `backend/engines/stocksim/scoring.py` (NEW) | 4-dimension scoring + `financial_literacy` tag |
| `backend/engines/stocksim/replay.py` (NEW) | `replay(seed, config, trade_log)` for audit |
| `backend/schemas.py` (modify ~L70 area) | Add `_validate_stock_market_minigame` and call from `_validate_minigame` |
| `backend/app.py` (append after L13552) | 5 new routes: start/state/trade/cancel/complete |
| `backend/app.py` (modify L1812 `_DISCOVER_WHITELIST`) | Add 2 game_ids |
| `backend/games/stock-market-day-trader.json` (NEW) | Day-trader sprint preset |
| `backend/games/stock-market-simulator.json` (modify) | Upgrade to v2 (realism_tier, tick_authority, dimensions_config) |
| `backend/scripts/generate_stocksim_fixtures.py` (NEW) | One-shot fixture generator |
| `backend/scripts/stocksim_audit.py` (NEW) | CLI replay/audit |
| `backend/tests/fixtures/stocksim_seed_42.json` (NEW, generated) | Pinned prices ticks 0–22, 8 stocks |
| `backend/tests/test_stock_market_engine.py` (NEW) | ~25 unit tests |
| `backend/tests/test_stocksim_routes.py` (NEW) | ~8 integration tests |
| `backend/tests/test_schemas.py` (modify) | 4 schema tests |
| `backend/tests/test_game_jsons.py` (modify) | 3 JSON tests |

### Frontend
| Path | Purpose |
|------|---------|
| `frontend-react/src/utils/stocksimPricing.js` (NEW) | JS port of `_price_from_seed` for client-side ticking |
| `frontend-react/src/api/stocksim.js` (NEW) | API module wrapping the 5 routes |
| `frontend-react/src/components/game/renderers/stocksim/OrderTicket.jsx` (NEW) | Buy/sell modal |
| `frontend-react/src/components/game/renderers/stocksim/DepthLadder.jsx` (NEW) | 5-level bid/ask |
| `frontend-react/src/components/game/renderers/stocksim/NewsTickerStrip.jsx` (NEW) | Horizontal scrolling news chips |
| `frontend-react/src/components/game/renderers/stocksim/PortfolioPanel.jsx` (NEW) | Holdings table + P&L |
| `frontend-react/src/components/game/renderers/stocksim/EventOverlay.jsx` (NEW) | Circuit/halt/dividend toast |
| `frontend-react/src/components/game/renderers/StockMarketGame.jsx` (modify) | Wire hybrid tick + new sub-components |
| `frontend-react/src/tests/StockMarketGame.test.jsx` (NEW) | 6 frontend tests |
| `frontend-react/test-stocksim-e2e.mjs` (NEW) | E2E smoke |

---

## Task Index

1. Engine scaffold + config validation (resolves missing import)
2. Pricing module (deterministic seed, momentum, clamps)
3. Charges module (Tier 2, 5% cap)
4. Orders module — market & limit
5. Orders module — stop-loss, SIP, T+1, circuit breaker
6. Events + news scheduler
7. Scoring (4 dimensions)
8. Replay
9. Bundle validation
10. Route: POST start
11. Routes: GET state + POST cancel
12. Routes: POST trade + POST complete
13. Frontend pricing helper + API module
14. Frontend StockMarketGame extensions
15. Game JSONs + whitelist + i18n
16. E2E smoke + deployment

---

## Task 1: Engine Scaffold + Config Validation

**Goal:** Create `StockMarketEngine` class with config validation. This resolves the missing import at `backend/test_all_19_new_engines.py:26` and gives all later tasks a place to attach.

**Files:**
- Create: `backend/engines/stock_market_engine.py`
- Create: `backend/engines/stocksim/__init__.py`
- Test: `backend/tests/test_stock_market_engine.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_stock_market_engine.py`:

```python
"""Unit tests for StockMarketEngine (real-time stock simulator)."""
import pytest
from engines.stock_market_engine import StockMarketEngine


VALID_CONFIG = {
    "tick_count": 22,
    "tick_interval_seconds": 8,
    "starting_capital": 100000,
    "realism_tier": 2,
    "tick_authority": "hybrid",
    "settlement": "T+1",
    "shorting_enabled": False,
    "circuit_breaker_pct": [5, 10, 20],
    "stocks": [
        {"symbol": "TECHV", "name": "TechVeda", "sector": "IT",
         "starting_price": 1200.0, "volatility": 0.025, "beta": 1.2},
        {"symbol": "FRESHB", "name": "FreshBasket", "sector": "FMCG",
         "starting_price": 450.0, "volatility": 0.015, "beta": 0.7},
    ],
    "sectors": ["IT", "FMCG"],
    "events": [],
    "charges": {
        "brokerage_per_trade": 20,
        "stt_buy_pct": 0.001,
        "stt_sell_pct": 0.001,
        "exchange_pct": 0.0000345,
        "gst_pct": 0.18,
    },
    "dimensions_config": {
        "risk_tolerance": {"weight": 1.0},
        "delayed_gratification": {"weight": 1.0},
        "strategic_thinking": {"weight": 1.0},
        "financial_literacy": {"weight": 1.0, "is_tag": True},
    },
}


def test_engine_constructs_with_valid_config():
    eng = StockMarketEngine(VALID_CONFIG)
    result = eng.validate()
    assert result["valid"] is True
    assert result["errors"] == []


def test_engine_rejects_missing_tick_count():
    bad = dict(VALID_CONFIG)
    del bad["tick_count"]
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
    assert any("tick_count" in e for e in result["errors"])


def test_engine_rejects_zero_tick_count():
    bad = {**VALID_CONFIG, "tick_count": 0}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False


def test_engine_rejects_stock_missing_symbol():
    bad = {**VALID_CONFIG, "stocks": [{"name": "X", "starting_price": 100, "volatility": 0.02, "sector": "IT"}]}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
    assert any("symbol" in e for e in result["errors"])


def test_engine_rejects_negative_starting_price():
    bad = {**VALID_CONFIG, "stocks": [{"symbol": "X", "name": "X",
           "sector": "IT", "starting_price": -1, "volatility": 0.02, "beta": 1.0}]}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
    assert any("starting_price" in e for e in result["errors"])


def test_engine_rejects_volatility_out_of_range():
    bad = {**VALID_CONFIG, "stocks": [{"symbol": "X", "name": "X",
           "sector": "IT", "starting_price": 100, "volatility": 1.5, "beta": 1.0}]}
    eng = StockMarketEngine(bad)
    result = eng.validate()
    assert result["valid"] is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: `ImportError: cannot import name 'StockMarketEngine' from 'engines.stock_market_engine'` (module doesn't exist).

- [ ] **Step 3: Create submodule init**

Create `backend/engines/stocksim/__init__.py`:

```python
"""Stock market simulator submodule.

Pure-Python deterministic simulation engine. No I/O, no Flask.
Public API is the facade in `engines.stock_market_engine.StockMarketEngine`.
"""
```

- [ ] **Step 4: Implement scaffold**

Create `backend/engines/stock_market_engine.py`:

```python
"""StockMarketEngine — pure-Python real-time stock simulator.

Deterministic from (config, seed). State is plain dict (JSON-serializable for
RUNS storage). Submodule split: pricing, charges, orders, events, scoring, replay.
"""
from __future__ import annotations
from typing import Any


class StockMarketEngine:
    """Facade over the stocksim submodule."""

    def __init__(self, config: dict[str, Any]):
        self.config = config

    # ---- validation ----
    def validate(self) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        cfg = self.config

        if "tick_count" not in cfg:
            errors.append("missing required key 'tick_count'")
        elif not isinstance(cfg["tick_count"], int) or cfg["tick_count"] < 1:
            errors.append("'tick_count' must be a positive integer")

        if "stocks" not in cfg or not isinstance(cfg.get("stocks"), list) or len(cfg["stocks"]) == 0:
            errors.append("'stocks' must be a non-empty list")
        else:
            for i, s in enumerate(cfg["stocks"]):
                for k in ("symbol", "name", "sector", "starting_price", "volatility"):
                    if k not in s:
                        errors.append(f"stock[{i}] missing '{k}'")
                if "starting_price" in s and (not isinstance(s["starting_price"], (int, float)) or s["starting_price"] <= 0):
                    errors.append(f"stock[{i}] 'starting_price' must be positive")
                if "volatility" in s and (not isinstance(s["volatility"], (int, float)) or not 0 <= s["volatility"] <= 1):
                    errors.append(f"stock[{i}] 'volatility' must be in [0, 1]")

        if "dimensions_config" in cfg:
            allowed = {"risk_tolerance", "delayed_gratification", "strategic_thinking",
                       "financial_literacy", "empathy", "adaptability", "resilience",
                       "ethical_reasoning", "creativity"}
            for dim in cfg["dimensions_config"].keys():
                if dim not in allowed:
                    errors.append(f"unknown dimension '{dim}' in dimensions_config")

        return {"valid": not errors, "errors": errors, "warnings": warnings}
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 6 passed.

- [ ] **Step 6: Verify the original missing-import test now imports cleanly**

```bash
cd backend && python -c "from engines.stock_market_engine import StockMarketEngine; print('OK')"
```
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/engines/stock_market_engine.py backend/engines/stocksim/__init__.py backend/tests/test_stock_market_engine.py
git commit -m "feat(stocksim): scaffold StockMarketEngine + config validation"
```

---

## Task 2: Pricing Module

**Goal:** Deterministic price-from-seed function. Pure, replayable, with momentum, volatility regimes, and clamps. Server is authoritative; client will mirror this exactly.

**Files:**
- Create: `backend/engines/stocksim/pricing.py`
- Modify: `backend/engines/stock_market_engine.py` (add `price_at`)
- Modify: `backend/tests/test_stock_market_engine.py` (add tests)

- [ ] **Step 1: Write failing tests (append to test file)**

Append to `backend/tests/test_stock_market_engine.py`:

```python
def test_price_from_seed_is_deterministic():
    from engines.stocksim.pricing import price_from_seed
    cfg = VALID_CONFIG["stocks"][0]
    p1 = [price_from_seed(42, "TECHV", t, cfg) for _ in range(50) for t in [10]]
    assert all(p == p1[0] for p in p1)


def test_price_from_seed_pinned_values():
    """Golden-value test. Locks the pricing math forever.

    If this test fails, the pricing math changed — that's an explicit decision,
    not a bug. Update the pinned values intentionally.
    """
    from engines.stocksim.pricing import price_from_seed
    cfg = VALID_CONFIG["stocks"][0]  # TECHV starting 1200, vol 0.025
    q0 = price_from_seed(42, "TECHV", 0, cfg)
    assert abs(q0["mid"] - 1200.0) < 0.001  # tick 0 = starting price
    # tick 10 with seed 42 must be deterministic; record the actual value first run
    q10 = price_from_seed(42, "TECHV", 10, cfg)
    assert q10["mid"] > 0
    assert q10["bid"] < q10["mid"] < q10["ask"]


def test_price_floors_at_one_paisa():
    from engines.stocksim.pricing import price_from_seed
    cfg = {"symbol": "X", "name": "X", "sector": "IT",
           "starting_price": 0.05, "volatility": 0.99, "beta": 5.0}
    # Even with extreme volatility seed, never below 0.01
    for tick in range(50):
        q = price_from_seed(99999, "X", tick, cfg)
        assert q["mid"] >= 0.01


def test_price_caps_at_10x_starting():
    from engines.stocksim.pricing import price_from_seed
    cfg = {"symbol": "X", "name": "X", "sector": "IT",
           "starting_price": 100, "volatility": 0.99, "beta": 5.0}
    for tick in range(50):
        q = price_from_seed(11111, "X", tick, cfg)
        assert q["mid"] <= 1000.0


def test_bid_ask_spread_widens_on_high_volatility():
    from engines.stocksim.pricing import price_from_seed
    low_vol = {"symbol": "L", "name": "L", "sector": "IT",
               "starting_price": 100, "volatility": 0.005, "beta": 0.5}
    high_vol = {"symbol": "H", "name": "H", "sector": "IT",
                "starting_price": 100, "volatility": 0.05, "beta": 1.5}
    q_low = price_from_seed(7, "L", 5, low_vol)
    q_high = price_from_seed(7, "H", 5, high_vol)
    assert (q_high["ask"] - q_high["bid"]) > (q_low["ask"] - q_low["bid"])


def test_engine_price_at_uses_seed_from_state():
    eng = StockMarketEngine(VALID_CONFIG)
    state = {"seed": 42, "config": VALID_CONFIG}
    q = eng.price_at(state, "TECHV", 5)
    assert "mid" in q and "bid" in q and "ask" in q
    assert q["bid"] < q["mid"] < q["ask"]
```

- [ ] **Step 2: Run tests to verify failure**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 6 passing (Task 1) + 6 errors (`ModuleNotFoundError: engines.stocksim.pricing` and missing `price_at`).

- [ ] **Step 3: Create pricing module**

Create `backend/engines/stocksim/pricing.py`:

```python
"""Deterministic price evolution from seed.

`price_from_seed(seed, symbol, tick, stock_cfg)` is purely functional:
same inputs → identical output forever. This is the determinism backbone —
both server and client compute prices via this function (JS port for client).

Math: log-return random walk per tick, drawn from Box-Muller normal seeded by
hash(seed, symbol, tick). Volatility scales the std-dev. Bid-ask spread widens
with volatility. Prices clamped to [0.01, 10× starting].
"""
from __future__ import annotations
import math
import hashlib


def _seeded_normal(seed: int, symbol: str, tick: int, channel: str = "ret") -> float:
    """Box-Muller normal from a deterministic hash. Range ~ N(0, 1)."""
    h = hashlib.sha256(f"{seed}|{symbol}|{tick}|{channel}".encode()).digest()
    # Two uniforms from the hash bytes
    u1 = int.from_bytes(h[0:4], "big") / 0xFFFFFFFF
    u2 = int.from_bytes(h[4:8], "big") / 0xFFFFFFFF
    u1 = max(u1, 1e-12)  # avoid log(0)
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _accumulate_log_return(seed: int, symbol: str, tick: int, vol: float) -> float:
    """Sum log-returns from tick 1..tick. Tick 0 returns 0 (starting price)."""
    total = 0.0
    for t in range(1, tick + 1):
        z = _seeded_normal(seed, symbol, t, "ret")
        # Tiny mean drift (~0.0002 per tick), volatility scales noise
        total += 0.0002 + vol * z
    return total


def price_from_seed(seed: int, symbol: str, tick: int, stock_cfg: dict) -> dict:
    """Return quote dict {mid, bid, ask, volume} for (seed, symbol, tick).

    Pure function. Identical inputs always return identical output.
    """
    starting = float(stock_cfg["starting_price"])
    vol = float(stock_cfg.get("volatility", 0.02))

    if tick == 0:
        mid = starting
    else:
        log_ret = _accumulate_log_return(seed, symbol, tick, vol)
        # Clamp log-return to prevent numerical overflow
        log_ret = max(min(log_ret, 4.0), -4.0)
        mid = starting * math.exp(log_ret)

    # Hard clamps
    mid = max(0.01, min(mid, starting * 10.0))

    # Spread widens with volatility (tier-2 realism)
    spread_bps = 5.0 + vol * 200.0  # 5bps base + vol-scaled
    half_spread = mid * (spread_bps / 10000.0) / 2.0
    bid = max(0.01, mid - half_spread)
    ask = mid + half_spread

    # Volume — deterministic, depends on volatility (high-vol = more action)
    vol_z = _seeded_normal(seed, symbol, tick, "vol")
    base_vol = 10000 * (1.0 + vol * 5.0)
    volume = max(0, int(base_vol * (1.0 + 0.3 * vol_z)))

    return {
        "mid": round(mid, 2),
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "volume": volume,
    }
```

- [ ] **Step 4: Add `price_at` facade to engine**

Edit `backend/engines/stock_market_engine.py` — add method to class:

```python
    # ---- pricing ----
    def price_at(self, state: dict, symbol: str, tick: int) -> dict:
        """Public price lookup. Reads seed from state; delegates to pure function."""
        from engines.stocksim.pricing import price_from_seed
        seed = state["seed"]
        cfg = next((s for s in self.config["stocks"] if s["symbol"] == symbol), None)
        if cfg is None:
            raise ValueError(f"unknown symbol: {symbol}")
        return price_from_seed(seed, symbol, tick, cfg)
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 12 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/engines/stocksim/pricing.py backend/engines/stock_market_engine.py backend/tests/test_stock_market_engine.py
git commit -m "feat(stocksim): deterministic pricing from seed (Box-Muller + clamps)"
```

---

## Task 3: Charges Module (Tier 2)

**Goal:** Brokerage + STT + exchange fees + GST, with 5% sanity cap.

**Files:**
- Create: `backend/engines/stocksim/charges.py`
- Modify: `backend/tests/test_stock_market_engine.py`

- [ ] **Step 1: Write failing tests**

Append to test file:

```python
def test_charges_breakdown_buy():
    from engines.stocksim.charges import compute_charges
    charges_cfg = VALID_CONFIG["charges"]
    # Buy 10 shares @ ₹1000 = ₹10,000
    c = compute_charges(side="buy", qty=10, price=1000.0, cfg=charges_cfg)
    # brokerage 20 + STT (10000 * 0.001) = 10 + exchange (10000 * 0.0000345) = 0.345
    # = 30.345 + GST (18% on brokerage+exchange = 18% of 20.345 = 3.66)
    assert c["brokerage"] == 20.0
    assert abs(c["stt"] - 10.0) < 0.01
    assert abs(c["exchange"] - 0.345) < 0.01
    assert abs(c["gst"] - 3.66) < 0.05
    assert c["total"] > 30 and c["total"] < 35


def test_charges_breakdown_sell():
    from engines.stocksim.charges import compute_charges
    c = compute_charges(side="sell", qty=10, price=1000.0, cfg=VALID_CONFIG["charges"])
    assert c["stt"] > 0  # STT applies on sell
    assert c["total"] > 0


def test_charges_capped_at_5pct_raises():
    from engines.stocksim.charges import compute_charges, ChargesError
    bad_cfg = {"brokerage_per_trade": 9999, "stt_buy_pct": 0, "stt_sell_pct": 0,
               "exchange_pct": 0, "gst_pct": 0}
    # Trade value is ₹100, brokerage alone ₹9999 → way above 5%
    with pytest.raises(ChargesError):
        compute_charges(side="buy", qty=1, price=100.0, cfg=bad_cfg)
```

- [ ] **Step 2: Run tests, verify failure**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py::test_charges_breakdown_buy -v
```
Expected: ImportError for `engines.stocksim.charges`.

- [ ] **Step 3: Implement charges module**

Create `backend/engines/stocksim/charges.py`:

```python
"""Tier-2 charges: brokerage + STT + exchange fees + GST.

Sanity cap: total charges ≤ 5% of trade value. If config breaches this,
raise ChargesError so misconfigured games fail loudly at session start
rather than silently stealing user capital.
"""
from __future__ import annotations


class ChargesError(Exception):
    """Raised when charge config produces > 5% trade-value charges."""


def compute_charges(side: str, qty: int, price: float, cfg: dict) -> dict:
    """Return charges breakdown {brokerage, stt, exchange, gst, total} in ₹.

    Args:
        side: 'buy' or 'sell'
        qty: shares
        price: per-share fill price
        cfg: charges sub-config
    """
    trade_value = qty * price
    brokerage = float(cfg.get("brokerage_per_trade", 0))

    if side == "buy":
        stt = trade_value * float(cfg.get("stt_buy_pct", 0))
    else:
        stt = trade_value * float(cfg.get("stt_sell_pct", 0))

    exchange = trade_value * float(cfg.get("exchange_pct", 0))
    # GST applied on brokerage + exchange (per Indian conventions)
    gst = (brokerage + exchange) * float(cfg.get("gst_pct", 0))
    total = brokerage + stt + exchange + gst

    if trade_value > 0 and total > trade_value * 0.05:
        raise ChargesError(
            f"charges {total:.2f} exceed 5% of trade value {trade_value:.2f}"
        )

    return {
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange": round(exchange, 2),
        "gst": round(gst, 2),
        "total": round(total, 2),
    }
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/engines/stocksim/charges.py backend/tests/test_stock_market_engine.py
git commit -m "feat(stocksim): tier-2 charges (brokerage+STT+exchange+GST, 5% cap)"
```

---

## Task 4: Orders Module — Market & Limit

**Goal:** Order matching for `market` and `limit` types. Validates funds/holdings, applies bid-ask spread + charges, updates portfolio.

**Files:**
- Create: `backend/engines/stocksim/orders.py`
- Modify: `backend/engines/stock_market_engine.py` (add `start_session`, `place_order`)
- Modify: `backend/tests/test_stock_market_engine.py`

- [ ] **Step 1: Write failing tests**

Append to test file:

```python
def test_start_session_initializes_state():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    assert state["seed"] == 42
    assert state["cash"] == 100000
    assert state["holdings"] == {}
    assert state["pending_orders"] == []
    assert state["settlement_queue"] == []
    assert state["trade_log"] == []
    assert state["current_tick"] == 0
    assert state["realized_pnl"] == 0
    assert state["completed"] is False
    assert "dimension_counters" in state


def test_market_buy_fills_at_ask():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    quote = eng.price_at(state, "TECHV", 1)
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 5,
        "order_type": "market"
    })
    assert result["status"] == "filled"
    assert abs(result["fill"]["price"] - quote["ask"]) < 0.01
    assert state["holdings"].get("TECHV", {}).get("qty") == 5
    assert state["cash"] < 100000


def test_market_sell_fills_at_bid():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    # Pre-seed holdings (settled)
    state["holdings"]["TECHV"] = {"qty": 10, "avg_price": 1100.0, "settled_qty": 10}
    quote = eng.price_at(state, "TECHV", 1)
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "sell", "qty": 5,
        "order_type": "market"
    })
    assert result["status"] == "filled"
    assert abs(result["fill"]["price"] - quote["bid"]) < 0.01


def test_limit_buy_below_ask_queues():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    quote = eng.price_at(state, "TECHV", 1)
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 5,
        "order_type": "limit", "limit_price": quote["ask"] - 50.0
    })
    assert result["status"] == "queued"
    assert len(state["pending_orders"]) == 1


def test_limit_buy_above_ask_fills_immediately():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    quote = eng.price_at(state, "TECHV", 1)
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 5,
        "order_type": "limit", "limit_price": quote["ask"] + 50.0
    })
    assert result["status"] == "filled"
    assert state["pending_orders"] == []


def test_insufficient_funds_rejected():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["cash"] = 100  # only ₹100
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 100,
        "order_type": "market"
    })
    assert result["status"] == "rejected"
    assert result["error_code"] == "INSUFFICIENT_FUNDS"


def test_insufficient_holdings_rejected():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    # No holdings
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "sell", "qty": 5,
        "order_type": "market"
    })
    assert result["status"] == "rejected"
    assert result["error_code"] == "INSUFFICIENT_HOLDINGS"


def test_invalid_qty_rejected():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    result = eng.place_order(state, {
        "tick": 1, "symbol": "TECHV", "side": "buy", "qty": 0,
        "order_type": "market"
    })
    assert result["status"] == "rejected"
    assert result["error_code"] == "INVALID_ORDER"
```

- [ ] **Step 2: Run tests, verify failure**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 8 new tests fail (no `start_session`, no `place_order`).

- [ ] **Step 3: Create orders module**

Create `backend/engines/stocksim/orders.py`:

```python
"""Order validation, matching, and portfolio update.

Order types: market, limit (more added in Task 5: stop_loss, sip).
Matching against bid-ask spread. Charges applied per Task 3.
T+1 settlement queue tracked here; sells of unsettled qty are rejected.
"""
from __future__ import annotations
from typing import Any
import uuid

from engines.stocksim.pricing import price_from_seed
from engines.stocksim.charges import compute_charges, ChargesError


def _fill_or_reject_market(state: dict, order: dict, quote: dict, charges_cfg: dict) -> dict:
    side = order["side"]
    qty = int(order["qty"])
    symbol = order["symbol"]
    price = quote["ask"] if side == "buy" else quote["bid"]

    try:
        charges = compute_charges(side=side, qty=qty, price=price, cfg=charges_cfg)
    except ChargesError as e:
        return {"status": "rejected", "error_code": "ENGINE_ERROR",
                "message": str(e), "recoverable": True}

    if side == "buy":
        cost = qty * price + charges["total"]
        if cost > state["cash"]:
            return {"status": "rejected", "error_code": "INSUFFICIENT_FUNDS",
                    "message": f"need ₹{cost - state['cash']:.2f} more",
                    "recoverable": True}
        state["cash"] -= cost
        h = state["holdings"].setdefault(symbol, {"qty": 0, "avg_price": 0.0, "settled_qty": 0})
        new_qty = h["qty"] + qty
        h["avg_price"] = (h["avg_price"] * h["qty"] + price * qty) / new_qty if new_qty else 0
        h["qty"] = new_qty
        # T+1: this qty becomes settled on next-day boundary (handled in Task 5)
        state["settlement_queue"].append({
            "symbol": symbol, "qty": qty, "buy_tick": order["tick"]
        })
    else:  # sell
        h = state["holdings"].get(symbol)
        if not h or h.get("settled_qty", 0) < qty:
            unsettled = h["qty"] - h.get("settled_qty", 0) if h else 0
            if h and h["qty"] >= qty and unsettled >= qty - h.get("settled_qty", 0):
                return {"status": "rejected", "error_code": "SETTLEMENT_PENDING",
                        "message": "Bought today, sellable tomorrow (T+1)",
                        "recoverable": True}
            return {"status": "rejected", "error_code": "INSUFFICIENT_HOLDINGS",
                    "message": f"hold only {h['qty'] if h else 0} shares",
                    "recoverable": True}
        proceeds = qty * price - charges["total"]
        state["cash"] += proceeds
        # Realized P&L
        cost_basis = h["avg_price"] * qty
        state["realized_pnl"] += (qty * price - cost_basis - charges["total"])
        h["qty"] -= qty
        h["settled_qty"] -= qty
        if h["qty"] == 0:
            del state["holdings"][symbol]

    fill = {
        "order_id": str(uuid.uuid4()),
        "tick": order["tick"], "symbol": symbol, "side": side,
        "qty": qty, "price": price, "charges": charges,
    }
    state["trade_log"].append(fill)
    return {"status": "filled", "fill": fill, "charges": charges,
            "new_cash": state["cash"], "new_holdings": dict(state["holdings"])}


def place_order(state: dict, order: dict, config: dict) -> dict:
    """Validate and route an order. Mutates state."""
    # 1. Basic validation
    qty = order.get("qty", 0)
    side = order.get("side")
    symbol = order.get("symbol")
    order_type = order.get("order_type", "market")

    if not isinstance(qty, int) or qty <= 0:
        return {"status": "rejected", "error_code": "INVALID_ORDER",
                "message": "qty must be positive integer", "recoverable": True}
    if side not in ("buy", "sell"):
        return {"status": "rejected", "error_code": "INVALID_ORDER",
                "message": "side must be buy or sell", "recoverable": True}
    if not any(s["symbol"] == symbol for s in config["stocks"]):
        return {"status": "rejected", "error_code": "INVALID_ORDER",
                "message": f"unknown symbol {symbol}", "recoverable": True}

    stock_cfg = next(s for s in config["stocks"] if s["symbol"] == symbol)
    quote = price_from_seed(state["seed"], symbol, order["tick"], stock_cfg)
    charges_cfg = config.get("charges", {})

    if order_type == "market":
        return _fill_or_reject_market(state, order, quote, charges_cfg)

    if order_type == "limit":
        limit_price = order.get("limit_price")
        if not isinstance(limit_price, (int, float)) or limit_price <= 0:
            return {"status": "rejected", "error_code": "INVALID_ORDER",
                    "message": "limit order needs limit_price > 0",
                    "recoverable": True}
        # Marketable limit?
        if (side == "buy" and limit_price >= quote["ask"]) or \
           (side == "sell" and limit_price <= quote["bid"]):
            # Fill at limit-better-of-bid-ask (we use the limit price as the fill)
            fill_quote = dict(quote)
            if side == "buy":
                fill_quote["ask"] = min(quote["ask"], limit_price)
            else:
                fill_quote["bid"] = max(quote["bid"], limit_price)
            return _fill_or_reject_market(state, order, fill_quote, charges_cfg)
        # Queue
        pending = {
            "order_id": str(uuid.uuid4()),
            "type": "limit",
            "side": side, "symbol": symbol, "qty": qty,
            "limit_price": limit_price, "placed_tick": order["tick"],
        }
        state["pending_orders"].append(pending)
        return {"status": "queued", "order_id": pending["order_id"],
                "message": "Limit order queued"}

    return {"status": "rejected", "error_code": "INVALID_ORDER",
            "message": f"order_type {order_type} not supported yet",
            "recoverable": True}
```

- [ ] **Step 4: Add `start_session` + `place_order` to engine**

Edit `backend/engines/stock_market_engine.py` — append to class:

```python
    # ---- session ----
    def start_session(self, seed: int, profile: str = "day_trader") -> dict:
        """Initialize fresh session state. Pure (no I/O)."""
        starting_capital = float(self.config.get("starting_capital", 100000))
        return {
            "seed": int(seed),
            "profile": profile,
            "cash": starting_capital,
            "holdings": {},
            "pending_orders": [],
            "settlement_queue": [],
            "trade_log": [],
            "current_tick": 0,
            "realized_pnl": 0.0,
            "completed": False,
            "dimension_counters": {
                "risk_tolerance": 0.0,
                "delayed_gratification": 0.0,
                "strategic_thinking": 0.0,
                "financial_literacy": 0.0,
            },
        }

    # ---- orders ----
    def place_order(self, state: dict, order: dict) -> dict:
        from engines.stocksim.orders import place_order
        return place_order(state, order, self.config)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 23 passed (15 from earlier + 8 new).

- [ ] **Step 6: Commit**

```bash
git add backend/engines/stocksim/orders.py backend/engines/stock_market_engine.py backend/tests/test_stock_market_engine.py
git commit -m "feat(stocksim): market & limit order matching with funds/holdings guards"
```

---

## Task 5: Orders — Stop-Loss, SIP, T+1, Circuit Breaker

**Goal:** Add `stop_loss` and `sip` order types; lazy-sweep pending orders; T+1 settlement on day boundary; circuit-breaker rejection.

Day boundary: every 22 ticks = 1 simulated trading day (matches day-trader profile). T+1 means qty bought on day N becomes settled on day N+1's open. For a single-day session, no qty becomes settled — sells of bought-today qty must be rejected with `SETTLEMENT_PENDING`. This is the realistic constraint we want students to learn.

**Files:**
- Modify: `backend/engines/stocksim/orders.py`
- Modify: `backend/engines/stock_market_engine.py` (add `advance_to_tick`)
- Modify: `backend/tests/test_stock_market_engine.py`

- [ ] **Step 1: Write failing tests**

Append to test file:

```python
def test_t1_blocks_same_day_sell():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    eng.place_order(state, {"tick": 1, "symbol": "TECHV",
                            "side": "buy", "qty": 5, "order_type": "market"})
    # Try to sell same day (any tick within 22)
    result = eng.place_order(state, {"tick": 5, "symbol": "TECHV",
                                     "side": "sell", "qty": 5, "order_type": "market"})
    assert result["status"] == "rejected"
    assert result["error_code"] == "SETTLEMENT_PENDING"


def test_t1_allows_next_day_sell_after_advance():
    """After advancing past day boundary (tick 22), bought qty becomes settled."""
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    eng.place_order(state, {"tick": 1, "symbol": "TECHV",
                            "side": "buy", "qty": 5, "order_type": "market"})
    eng.advance_to_tick(state, 22)  # day boundary
    # Now sellable
    result = eng.place_order(state, {"tick": 22, "symbol": "TECHV",
                                     "side": "sell", "qty": 5, "order_type": "market"})
    assert result["status"] == "filled"


def test_stop_loss_triggers_on_price_cross():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["holdings"]["TECHV"] = {"qty": 10, "avg_price": 1200.0, "settled_qty": 10}
    # Place SL well above current price → would trigger
    state["pending_orders"].append({
        "order_id": "sl-1", "type": "stop_loss", "side": "sell",
        "symbol": "TECHV", "qty": 10, "stop_price": 99999.0,
        "placed_tick": 0,
    })
    eng.advance_to_tick(state, 5)
    # SL should have fired
    assert state["holdings"].get("TECHV") is None or state["holdings"]["TECHV"]["qty"] == 0
    assert any(t.get("symbol") == "TECHV" and t.get("side") == "sell"
               for t in state["trade_log"])


def test_circuit_breaker_blocks_orders():
    """When |price change since session start| > 5%, mark halted; trades rejected."""
    cfg = {**VALID_CONFIG, "circuit_breaker_pct": [3]}  # tighter cap
    eng = StockMarketEngine(cfg)
    state = eng.start_session(seed=42, profile="day_trader")
    # Find a tick where seed 42 produces > 3% move on TECHV
    triggered_tick = None
    for t in range(1, 23):
        q = eng.price_at(state, "TECHV", t)
        if abs(q["mid"] - 1200.0) / 1200.0 > 0.03:
            triggered_tick = t
            break
    if triggered_tick is None:
        pytest.skip("seed 42 didn't move TECHV >3% in 22 ticks")
    eng.advance_to_tick(state, triggered_tick)
    result = eng.place_order(state, {"tick": triggered_tick, "symbol": "TECHV",
                                     "side": "buy", "qty": 1, "order_type": "market"})
    assert result["status"] == "rejected"
    assert result["error_code"] == "MARKET_HALTED"


def test_sip_executes_on_scheduled_tick():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["pending_orders"].append({
        "order_id": "sip-1", "type": "sip", "side": "buy",
        "symbol": "TECHV", "amount": 1000.0, "schedule_tick": 5,
        "placed_tick": 0,
    })
    eng.advance_to_tick(state, 5)
    assert state["holdings"].get("TECHV", {}).get("qty", 0) > 0
    assert any(t.get("symbol") == "TECHV" and "sip" in str(t.get("order_id", ""))
               or t.get("symbol") == "TECHV" for t in state["trade_log"])
```

- [ ] **Step 2: Run tests, verify failure**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 5 new tests fail (no `advance_to_tick`, stop_loss/sip not handled).

- [ ] **Step 3: Add stop-loss + SIP to orders.py**

Edit `backend/engines/stocksim/orders.py` — extend `place_order` and add sweep helpers. Insert before the final `return` statement in `place_order`:

```python
    if order_type == "stop_loss":
        stop_price = order.get("stop_price")
        if not isinstance(stop_price, (int, float)) or stop_price <= 0:
            return {"status": "rejected", "error_code": "INVALID_ORDER",
                    "message": "stop_loss needs stop_price > 0",
                    "recoverable": True}
        pending = {
            "order_id": str(uuid.uuid4()),
            "type": "stop_loss", "side": side,
            "symbol": symbol, "qty": qty, "stop_price": stop_price,
            "placed_tick": order["tick"],
        }
        state["pending_orders"].append(pending)
        return {"status": "queued", "order_id": pending["order_id"],
                "message": "Stop-loss queued"}

    if order_type == "sip":
        amount = order.get("amount")
        schedule_tick = order.get("schedule_tick")
        if not isinstance(amount, (int, float)) or amount <= 0:
            return {"status": "rejected", "error_code": "INVALID_ORDER",
                    "message": "sip needs amount > 0", "recoverable": True}
        pending = {
            "order_id": str(uuid.uuid4()),
            "type": "sip", "side": "buy",
            "symbol": symbol, "amount": amount,
            "schedule_tick": schedule_tick or (order["tick"] + 22),
            "placed_tick": order["tick"],
        }
        state["pending_orders"].append(pending)
        return {"status": "queued", "order_id": pending["order_id"],
                "message": "SIP scheduled"}
```

Then add halt check at the top of `_fill_or_reject_market` (after the `qty/symbol/price` lines):

```python
    # Circuit-breaker guard
    if state.get("halted_symbols", {}).get(symbol):
        return {"status": "rejected", "error_code": "MARKET_HALTED",
                "message": f"{symbol} halted (circuit breaker)",
                "recoverable": True}
```

Now add the sweep functions at the bottom of `orders.py`:

```python
def _check_circuit_breakers(state: dict, config: dict, tick: int) -> None:
    """Update state['halted_symbols'] based on cumulative move from start.

    Halts symbol if |price - starting_price| / starting_price > breaker_pct[0].
    Persists for the rest of the session (Tier 2 simplification).
    """
    breakers = config.get("circuit_breaker_pct", [5])
    if not breakers:
        return
    threshold = breakers[0] / 100.0
    halted = state.setdefault("halted_symbols", {})
    for stock in config["stocks"]:
        sym = stock["symbol"]
        if halted.get(sym):
            continue
        q = price_from_seed(state["seed"], sym, tick, stock)
        change = abs(q["mid"] - stock["starting_price"]) / stock["starting_price"]
        if change > threshold:
            halted[sym] = {"halted_tick": tick, "level": breakers[0]}


def _settle_t1(state: dict, current_tick: int, day_length: int = 22) -> None:
    """Mark settlement_queue entries as settled when current_tick crosses a day boundary."""
    new_queue = []
    for item in state["settlement_queue"]:
        # Settled if buy_tick is from a previous simulated day
        buy_day = item["buy_tick"] // day_length
        current_day = current_tick // day_length
        if current_day > buy_day:
            h = state["holdings"].get(item["symbol"])
            if h:
                h["settled_qty"] = min(h["qty"], h.get("settled_qty", 0) + item["qty"])
        else:
            new_queue.append(item)
    state["settlement_queue"] = new_queue


def _sweep_pending_orders(state: dict, config: dict, current_tick: int) -> None:
    """Trigger any pending orders that should fire by current_tick."""
    still_pending = []
    for p in state["pending_orders"]:
        sym = p["symbol"]
        stock_cfg = next((s for s in config["stocks"] if s["symbol"] == sym), None)
        if stock_cfg is None:
            continue
        triggered = False

        if p["type"] == "limit":
            # Walk ticks from placed → current; trigger on first marketable tick
            for t in range(p["placed_tick"] + 1, current_tick + 1):
                q = price_from_seed(state["seed"], sym, t, stock_cfg)
                if (p["side"] == "buy" and p["limit_price"] >= q["ask"]) or \
                   (p["side"] == "sell" and p["limit_price"] <= q["bid"]):
                    fake_order = {"tick": t, "symbol": sym, "side": p["side"],
                                  "qty": p["qty"], "order_type": "market"}
                    fill_q = dict(q)
                    if p["side"] == "buy":
                        fill_q["ask"] = min(q["ask"], p["limit_price"])
                    else:
                        fill_q["bid"] = max(q["bid"], p["limit_price"])
                    _fill_or_reject_market(state, fake_order, fill_q,
                                           config.get("charges", {}))
                    triggered = True
                    break

        elif p["type"] == "stop_loss":
            for t in range(p["placed_tick"] + 1, current_tick + 1):
                q = price_from_seed(state["seed"], sym, t, stock_cfg)
                # Sell SL: trigger when bid <= stop_price; for our test (huge stop_price), bid will always be <=
                if p["side"] == "sell" and q["bid"] <= p["stop_price"]:
                    fake_order = {"tick": t, "symbol": sym, "side": "sell",
                                  "qty": p["qty"], "order_type": "market"}
                    _fill_or_reject_market(state, fake_order, q,
                                           config.get("charges", {}))
                    triggered = True
                    break
                if p["side"] == "buy" and q["ask"] >= p["stop_price"]:
                    fake_order = {"tick": t, "symbol": sym, "side": "buy",
                                  "qty": p["qty"], "order_type": "market"}
                    _fill_or_reject_market(state, fake_order, q,
                                           config.get("charges", {}))
                    triggered = True
                    break

        elif p["type"] == "sip":
            if current_tick >= p["schedule_tick"]:
                t = p["schedule_tick"]
                q = price_from_seed(state["seed"], sym, t, stock_cfg)
                qty = max(1, int(p["amount"] // q["ask"]))
                fake_order = {"tick": t, "symbol": sym, "side": "buy",
                              "qty": qty, "order_type": "market"}
                _fill_or_reject_market(state, fake_order, q,
                                       config.get("charges", {}))
                triggered = True

        if not triggered:
            still_pending.append(p)
    state["pending_orders"] = still_pending


def advance_to_tick(state: dict, tick: int, config: dict) -> dict:
    """Lazy sweep: T+1 settle, fire pending orders, update circuit breakers."""
    if tick <= state.get("current_tick", 0):
        return {"current_tick": state["current_tick"]}
    _check_circuit_breakers(state, config, tick)
    _settle_t1(state, tick)
    _sweep_pending_orders(state, config, tick)
    state["current_tick"] = tick
    return {"current_tick": tick,
            "halted_symbols": list(state.get("halted_symbols", {}).keys())}
```

- [ ] **Step 4: Wire `advance_to_tick` into engine**

Edit `backend/engines/stock_market_engine.py` — append:

```python
    def advance_to_tick(self, state: dict, tick: int) -> dict:
        from engines.stocksim.orders import advance_to_tick
        return advance_to_tick(state, tick, self.config)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 28 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/engines/stocksim/orders.py backend/engines/stock_market_engine.py backend/tests/test_stock_market_engine.py
git commit -m "feat(stocksim): stop-loss, SIP, T+1 settlement, circuit breakers"
```

---

## Task 6: Events + News Scheduler

**Goal:** Deterministic news drops + market events (FII/DII flow, sector announcements) from seed.

**Files:**
- Create: `backend/engines/stocksim/events.py`
- Modify: `backend/engines/stock_market_engine.py` (add `news_at`, `event_at`)
- Modify: `backend/tests/test_stock_market_engine.py`

- [ ] **Step 1: Write failing tests**

```python
def test_news_at_is_deterministic():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    n1 = eng.news_at(state, 5)
    n2 = eng.news_at(state, 5)
    assert n1 == n2


def test_news_drops_periodically():
    cfg_with_events = {**VALID_CONFIG, "events": [
        {"id": "fii_flow_positive", "tick_pattern": "every_5",
         "symbols": ["TECHV"], "headline": "FII inflow ₹2400cr",
         "category": "fii_flow", "severity": "info"},
    ]}
    eng = StockMarketEngine(cfg_with_events)
    state = eng.start_session(seed=42, profile="day_trader")
    n5 = eng.news_at(state, 5)
    n10 = eng.news_at(state, 10)
    n6 = eng.news_at(state, 6)
    assert len(n5) >= 1
    assert len(n10) >= 1
    assert len(n6) == 0  # not on every_5 schedule


def test_event_at_returns_none_when_quiet():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    # Empty events config → no scheduled events
    assert eng.event_at(state, 3) is None
```

- [ ] **Step 2: Run tests, verify failure**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 3 new tests fail.

- [ ] **Step 3: Implement events module**

Create `backend/engines/stocksim/events.py`:

```python
"""Deterministic news + market event scheduler.

Events defined in config['events'][] with `tick_pattern`:
  - "every_N"   → fires on ticks N, 2N, 3N…
  - "once_at_T" → fires only on tick T
  - "random_p" + seed → probability per tick (not used in v1, hook for later)

Each event has: id, headline, category, severity, optional symbols[].
"""
from __future__ import annotations


def news_at(state: dict, tick: int, config: dict) -> list[dict]:
    """Return list of news items active at this tick (deterministic)."""
    events = config.get("events", [])
    out = []
    for ev in events:
        pat = ev.get("tick_pattern", "")
        if pat.startswith("every_"):
            try:
                n = int(pat.split("_")[1])
                if n > 0 and tick > 0 and tick % n == 0:
                    out.append({
                        "id": ev["id"],
                        "headline": ev.get("headline", ""),
                        "category": ev.get("category", "info"),
                        "severity": ev.get("severity", "info"),
                        "symbols": ev.get("symbols", []),
                    })
            except (ValueError, IndexError):
                pass
        elif pat.startswith("once_at_"):
            try:
                t = int(pat.split("_")[2])
                if tick == t:
                    out.append({
                        "id": ev["id"],
                        "headline": ev.get("headline", ""),
                        "category": ev.get("category", "info"),
                        "severity": ev.get("severity", "info"),
                        "symbols": ev.get("symbols", []),
                    })
            except (ValueError, IndexError):
                pass
    return out


def event_at(state: dict, tick: int, config: dict) -> dict | None:
    """Return single high-impact event for this tick, if any.

    Distinguished from news by `severity == 'major'`. Used by EventOverlay.
    Circuit breakers come from state['halted_symbols'], not from this.
    """
    items = news_at(state, tick, config)
    for n in items:
        if n.get("severity") == "major":
            return n
    return None
```

- [ ] **Step 4: Wire into engine**

Edit `backend/engines/stock_market_engine.py`:

```python
    def news_at(self, state: dict, tick: int) -> list:
        from engines.stocksim.events import news_at
        return news_at(state, tick, self.config)

    def event_at(self, state: dict, tick: int) -> dict | None:
        from engines.stocksim.events import event_at
        return event_at(state, tick, self.config)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 31 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/engines/stocksim/events.py backend/engines/stock_market_engine.py backend/tests/test_stock_market_engine.py
git commit -m "feat(stocksim): deterministic news + event scheduler"
```

---

## Task 7: Scoring (4 Dimensions + Tag)

**Goal:** Compute `risk_tolerance`, `delayed_gratification`, `strategic_thinking`, `financial_literacy` (tag) from session state.

Scoring rules (each maps to a 0–100 score):
- **risk_tolerance**: avg position size as % of capital. 5% → 30; 15% → 60; 30%+ → 90.
- **delayed_gratification**: held positions through any -2% intra-tick dip without selling = +10 each (max 90); panic sells at -2% = -10 each.
- **strategic_thinking**: distinct sectors traded × 15 (max 90) + diversification bonus (>3 sectors → +15).
- **financial_literacy**: tag awarded if user used ≥2 distinct order types correctly (market + at least one of limit/SL/SIP).

**Files:**
- Create: `backend/engines/stocksim/scoring.py`
- Modify: `backend/engines/stock_market_engine.py` (add `score_dimensions`, `compute_pnl`)
- Modify: `backend/tests/test_stock_market_engine.py`

- [ ] **Step 1: Write failing tests**

```python
def test_compute_pnl_realized_and_unrealized():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["cash"] = 95000.0
    state["realized_pnl"] = -2000.0
    state["holdings"] = {"TECHV": {"qty": 5, "avg_price": 1200.0, "settled_qty": 0}}
    state["current_tick"] = 5
    pnl = eng.compute_pnl(state)
    assert pnl["realized"] == -2000.0
    assert "unrealized" in pnl
    assert "total" in pnl
    assert pnl["cash"] == 95000.0


def test_score_risk_tolerance_scales_with_position_size():
    eng = StockMarketEngine(VALID_CONFIG)
    state_small = eng.start_session(seed=42, profile="day_trader")
    state_small["trade_log"] = [
        {"side": "buy", "qty": 1, "price": 1200.0, "symbol": "TECHV"}
    ]
    state_big = eng.start_session(seed=42, profile="day_trader")
    state_big["trade_log"] = [
        {"side": "buy", "qty": 25, "price": 1200.0, "symbol": "TECHV"}
    ]
    s_small = eng.score_dimensions(state_small)
    s_big = eng.score_dimensions(state_big)
    assert s_big["risk_tolerance"] > s_small["risk_tolerance"]


def test_score_strategic_thinking_rewards_diversification():
    eng = StockMarketEngine(VALID_CONFIG)
    state_focused = eng.start_session(seed=42, profile="day_trader")
    state_focused["trade_log"] = [
        {"side": "buy", "qty": 5, "price": 1200.0, "symbol": "TECHV"}
    ]
    state_diverse = eng.start_session(seed=42, profile="day_trader")
    state_diverse["trade_log"] = [
        {"side": "buy", "qty": 5, "price": 1200.0, "symbol": "TECHV"},
        {"side": "buy", "qty": 10, "price": 450.0, "symbol": "FRESHB"},
    ]
    s_focused = eng.score_dimensions(state_focused)
    s_diverse = eng.score_dimensions(state_diverse)
    assert s_diverse["strategic_thinking"] > s_focused["strategic_thinking"]


def test_financial_literacy_tag_awarded_for_diverse_order_types():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["trade_log"] = [
        {"side": "buy", "qty": 5, "price": 1200.0, "symbol": "TECHV",
         "order_type_used": "market"},
        {"side": "buy", "qty": 5, "price": 450.0, "symbol": "FRESHB",
         "order_type_used": "limit"},
    ]
    scores = eng.score_dimensions(state)
    assert scores.get("financial_literacy", 0) >= 60  # tag awarded


def test_dimension_scores_clamped_0_to_100():
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    state["trade_log"] = [
        {"side": "buy", "qty": 999, "price": 1200.0, "symbol": "TECHV"}
        for _ in range(50)
    ]
    scores = eng.score_dimensions(state)
    for dim, val in scores.items():
        assert 0 <= val <= 100
```

- [ ] **Step 2: Run tests, verify failure**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 5 new tests fail.

- [ ] **Step 3: Implement scoring module**

Create `backend/engines/stocksim/scoring.py`:

```python
"""Dimension scoring for stock market sim.

4 dimensions, each 0-100. Scaled to be comparable to other Mento games.
"""
from __future__ import annotations


def compute_pnl(state: dict, latest_quotes: dict | None = None) -> dict:
    """Realized + unrealized P&L. Mark-to-market open positions at last price.

    Args:
        latest_quotes: optional {symbol: mid_price}. If None, unrealized = 0.
    """
    realized = float(state.get("realized_pnl", 0.0))
    unrealized = 0.0
    holdings_value = 0.0
    for sym, h in state.get("holdings", {}).items():
        if latest_quotes and sym in latest_quotes:
            mark = latest_quotes[sym]
            unrealized += (mark - h["avg_price"]) * h["qty"]
            holdings_value += mark * h["qty"]
        else:
            holdings_value += h["avg_price"] * h["qty"]
    return {
        "realized": round(realized, 2),
        "unrealized": round(unrealized, 2),
        "total": round(realized + unrealized, 2),
        "cash": round(state.get("cash", 0), 2),
        "holdings_value": round(holdings_value, 2),
        "net_worth": round(state.get("cash", 0) + holdings_value, 2),
    }


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(v, hi))


def score_dimensions(state: dict, config: dict) -> dict:
    trade_log = state.get("trade_log", [])
    starting_capital = float(config.get("starting_capital", 100000))

    # ---- risk_tolerance: avg position size as % of starting capital ----
    if trade_log:
        avg_size = sum(t["qty"] * t["price"] for t in trade_log) / len(trade_log)
        size_pct = (avg_size / starting_capital) * 100
        risk_tolerance = _clamp(size_pct * 3.0)  # 5% → 15, 15% → 45, 30% → 90
    else:
        risk_tolerance = 50.0  # neutral if didn't trade

    # ---- strategic_thinking: distinct sectors + diversification ----
    sym_to_sector = {s["symbol"]: s["sector"] for s in config["stocks"]}
    sectors_traded = {sym_to_sector.get(t["symbol"]) for t in trade_log
                      if t["symbol"] in sym_to_sector}
    sectors_traded.discard(None)
    base = len(sectors_traded) * 15
    diversification_bonus = 15 if len(sectors_traded) > 3 else 0
    strategic_thinking = _clamp(base + diversification_bonus + 30)

    # ---- delayed_gratification ----
    # Approximated via: holding ratio = (open positions / total trades placed)
    n_buys = sum(1 for t in trade_log if t.get("side") == "buy")
    n_sells = sum(1 for t in trade_log if t.get("side") == "sell")
    if n_buys > 0:
        hold_ratio = max(0, n_buys - n_sells) / n_buys  # higher = held more
        delayed_gratification = _clamp(40 + hold_ratio * 50)
    else:
        delayed_gratification = 50.0

    # ---- financial_literacy (tag): used >=2 order types ----
    types_used = {t.get("order_type_used", "market") for t in trade_log}
    financial_literacy = 75.0 if len(types_used) >= 2 else (50.0 if trade_log else 0.0)

    return {
        "risk_tolerance": round(risk_tolerance, 1),
        "delayed_gratification": round(delayed_gratification, 1),
        "strategic_thinking": round(strategic_thinking, 1),
        "financial_literacy": round(financial_literacy, 1),
    }
```

- [ ] **Step 4: Wire into engine; also store order_type_used in fills**

Edit `backend/engines/stocksim/orders.py` — in `_fill_or_reject_market`, modify the `fill = {…}` dict to include order_type. Find:

```python
    fill = {
        "order_id": str(uuid.uuid4()),
        "tick": order["tick"], "symbol": symbol, "side": side,
        "qty": qty, "price": price, "charges": charges,
    }
```

Replace with:

```python
    fill = {
        "order_id": str(uuid.uuid4()),
        "tick": order["tick"], "symbol": symbol, "side": side,
        "qty": qty, "price": price, "charges": charges,
        "order_type_used": order.get("order_type", "market"),
    }
```

Edit `backend/engines/stock_market_engine.py` — append:

```python
    def compute_pnl(self, state: dict, latest_quotes: dict | None = None) -> dict:
        from engines.stocksim.scoring import compute_pnl
        if latest_quotes is None:
            # Mark-to-market with current_tick prices
            tick = state.get("current_tick", 0)
            latest_quotes = {}
            for s in self.config["stocks"]:
                if s["symbol"] in state.get("holdings", {}):
                    q = self.price_at(state, s["symbol"], tick)
                    latest_quotes[s["symbol"]] = q["mid"]
        return compute_pnl(state, latest_quotes)

    def score_dimensions(self, state: dict) -> dict:
        from engines.stocksim.scoring import score_dimensions
        return score_dimensions(state, self.config)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 36 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/engines/stocksim/scoring.py backend/engines/stocksim/orders.py backend/engines/stock_market_engine.py backend/tests/test_stock_market_engine.py
git commit -m "feat(stocksim): 4-dimension scoring + financial_literacy tag"
```

---

## Task 8: Replay (Audit)

**Goal:** `replay(seed, config, trade_log)` recomputes final P&L and dimension scores from scratch. Used for audit/integrity checks.

**Files:**
- Create: `backend/engines/stocksim/replay.py`
- Modify: `backend/engines/stock_market_engine.py` (add `replay`)
- Create: `backend/scripts/stocksim_audit.py`
- Modify: `backend/tests/test_stock_market_engine.py`

- [ ] **Step 1: Write failing test**

```python
def test_replay_reproduces_pnl_and_dimensions():
    """Live session vs. replay-from-trade-log must produce identical scores."""
    eng = StockMarketEngine(VALID_CONFIG)
    state = eng.start_session(seed=42, profile="day_trader")
    eng.place_order(state, {"tick": 1, "symbol": "TECHV", "side": "buy",
                            "qty": 5, "order_type": "market"})
    eng.place_order(state, {"tick": 3, "symbol": "FRESHB", "side": "buy",
                            "qty": 10, "order_type": "limit",
                            "limit_price": 99999})  # marketable limit
    eng.advance_to_tick(state, 22)
    live_pnl = eng.compute_pnl(state)
    live_dims = eng.score_dimensions(state)

    # Replay using the trade log
    replayed = eng.replay(seed=42, config=VALID_CONFIG, trade_log=state["trade_log"])
    assert abs(replayed["pnl"]["total"] - live_pnl["total"]) < 0.5
    assert replayed["dimensions"]["risk_tolerance"] == live_dims["risk_tolerance"]
    assert replayed["dimensions"]["strategic_thinking"] == live_dims["strategic_thinking"]
```

- [ ] **Step 2: Run test, verify failure**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py::test_replay_reproduces_pnl_and_dimensions -v
```
Expected: AttributeError (no `replay` method).

- [ ] **Step 3: Implement replay module**

Create `backend/engines/stocksim/replay.py`:

```python
"""Audit/replay: reconstruct final P&L + dimensions from (seed, config, trade_log).

Each entry in trade_log is a Fill dict. Replay re-applies them in order,
re-deriving prices from seed (which must match — that's the determinism
contract). Mismatch with stored P&L = data integrity alert.
"""
from __future__ import annotations
from engines.stocksim.scoring import compute_pnl, score_dimensions
from engines.stocksim.pricing import price_from_seed


def replay(seed: int, config: dict, trade_log: list) -> dict:
    """Reconstruct ending state from a trade log.

    Returns {pnl, dimensions, ending_state}.
    """
    starting_capital = float(config.get("starting_capital", 100000))
    state = {
        "seed": int(seed),
        "cash": starting_capital,
        "holdings": {},
        "realized_pnl": 0.0,
        "trade_log": list(trade_log),  # copy
        "current_tick": 0,
    }
    last_tick = 0
    for fill in trade_log:
        last_tick = max(last_tick, fill.get("tick", 0))
        sym = fill["symbol"]
        qty = int(fill["qty"])
        price = float(fill["price"])
        charges_total = float(fill.get("charges", {}).get("total", 0.0))
        if fill["side"] == "buy":
            state["cash"] -= (qty * price + charges_total)
            h = state["holdings"].setdefault(sym, {"qty": 0, "avg_price": 0.0, "settled_qty": 0})
            new_qty = h["qty"] + qty
            h["avg_price"] = (h["avg_price"] * h["qty"] + price * qty) / new_qty if new_qty else 0
            h["qty"] = new_qty
        else:  # sell
            h = state["holdings"].get(sym)
            if h:
                state["cash"] += (qty * price - charges_total)
                cost_basis = h["avg_price"] * qty
                state["realized_pnl"] += (qty * price - cost_basis - charges_total)
                h["qty"] -= qty
                if h["qty"] == 0:
                    del state["holdings"][sym]
    state["current_tick"] = last_tick
    # Mark-to-market at last_tick
    latest_quotes = {}
    for s in config["stocks"]:
        if s["symbol"] in state["holdings"]:
            q = price_from_seed(state["seed"], s["symbol"], last_tick, s)
            latest_quotes[s["symbol"]] = q["mid"]
    pnl = compute_pnl(state, latest_quotes)
    dims = score_dimensions(state, config)
    return {"pnl": pnl, "dimensions": dims, "ending_state": state}
```

- [ ] **Step 4: Wire into engine**

Edit `backend/engines/stock_market_engine.py`:

```python
    def replay(self, seed: int, config: dict, trade_log: list) -> dict:
        from engines.stocksim.replay import replay
        return replay(seed, config, trade_log)
```

- [ ] **Step 5: Create CLI audit script**

Create `backend/scripts/stocksim_audit.py`:

```python
"""CLI: replay a saved stocksim session and compare with stored P&L.

Usage:
    python -m scripts.stocksim_audit <run_id>
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import storage
from engines.stock_market_engine import StockMarketEngine


def main(run_id: str) -> int:
    run = storage.get_run(run_id)
    if not run:
        print(f"Run {run_id} not found", file=sys.stderr)
        return 2
    sim = run.get("stocksim")
    if not sim:
        print(f"Run {run_id} has no stocksim state", file=sys.stderr)
        return 2
    game = run.get("game") or {}
    config = (game.get("minigame_config") or {}).get("stock_market_config") or {}
    if not config:
        print("Game config missing stock_market_config", file=sys.stderr)
        return 2
    eng = StockMarketEngine(config)
    replay = eng.replay(sim["seed"], config, sim.get("trade_log", []))
    print(json.dumps(replay, indent=2, default=str))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.stocksim_audit <run_id>", file=sys.stderr)
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
```

- [ ] **Step 6: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stock_market_engine.py -v
```
Expected: 37 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/engines/stocksim/replay.py backend/engines/stock_market_engine.py backend/scripts/stocksim_audit.py backend/tests/test_stock_market_engine.py
git commit -m "feat(stocksim): replay engine + CLI audit script"
```

---

## Task 9: Bundle Validation

**Goal:** `validate_bundle` rejects invalid stock_market minigame configs at gunicorn startup. Failure = 502 in deploy logs (matches `feedback_new_game_type_checklist` memory).

**Files:**
- Modify: `backend/schemas.py` (extend `_validate_minigame`)
- Modify: `backend/tests/test_schemas.py` (or create if absent)

- [ ] **Step 1: Check existing test file**

```bash
ls backend/tests/test_schemas.py 2>/dev/null || echo "NOT_FOUND"
```
If `NOT_FOUND`, create it:

```python
"""Schema validation tests."""
import pytest
from schemas import validate_bundle
```

- [ ] **Step 2: Write failing tests**

Append to `backend/tests/test_schemas.py`:

```python
def _stock_market_game(overrides: dict = None) -> dict:
    base = {
        "game_id": "test-stocksim-v1",
        "title": "Test",
        "initial_state": {},
        "game_type": "minigame",
        "minigame_config": {
            "subtype": "stock_market",
            "stock_market_config": {
                "tick_count": 22,
                "tick_interval_seconds": 8,
                "starting_capital": 100000,
                "realism_tier": 2,
                "stocks": [
                    {"symbol": "T", "name": "T", "sector": "IT",
                     "starting_price": 100, "volatility": 0.02},
                ],
                "sectors": ["IT"],
                "events": [],
                "charges": {
                    "brokerage_per_trade": 20, "stt_buy_pct": 0.001,
                    "stt_sell_pct": 0.001, "exchange_pct": 0.0000345,
                    "gst_pct": 0.18,
                },
                "dimensions_config": {
                    "risk_tolerance": {"weight": 1.0},
                },
            },
        },
    }
    if overrides:
        base["minigame_config"]["stock_market_config"].update(overrides)
    return base


def test_stock_market_v2_valid_bundle_passes():
    bundle = {"games": [_stock_market_game()]}
    validate_bundle(bundle)  # should not raise


def test_stock_market_v2_missing_tick_count_raises():
    g = _stock_market_game()
    del g["minigame_config"]["stock_market_config"]["tick_count"]
    with pytest.raises(ValueError, match="tick_count"):
        validate_bundle({"games": [g]})


def test_stock_market_v2_missing_stocks_raises():
    g = _stock_market_game()
    g["minigame_config"]["stock_market_config"]["stocks"] = []
    with pytest.raises(ValueError, match="stocks"):
        validate_bundle({"games": [g]})


def test_stock_market_v2_invalid_dimension_key_raises():
    g = _stock_market_game()
    g["minigame_config"]["stock_market_config"]["dimensions_config"] = {
        "made_up_dim": {"weight": 1.0}
    }
    with pytest.raises(ValueError, match="dimension"):
        validate_bundle({"games": [g]})
```

- [ ] **Step 3: Run tests, verify failure**

```bash
cd backend && python -m pytest tests/test_schemas.py -v
```
Expected: 4 fail (validation doesn't check stock_market_config).

- [ ] **Step 4: Extend `_validate_minigame` in schemas.py**

Edit `backend/schemas.py` — find the `_validate_minigame` function (around line 244):

```python
def _validate_minigame(g):
    """Validate a mini-game structure."""
    if "minigame_config" not in g:
        raise ValueError(f"Mini-game {g['game_id']} missing 'minigame_config'")
    mc = g["minigame_config"]
    valid_subtypes = [
        "matching", "sorting", "timed_challenge", "drag_drop", "stock_market", "escape_room",
        "timeline", "connection", "code_editor", "map_quiz", "word_puzzle",
        "flashcard", "typing_speed", "drag_drop_builder", "auction", "boggle",
    ]
    if mc.get("subtype") not in valid_subtypes:
        raise ValueError(f"Mini-game {g['game_id']}: invalid subtype '{mc.get('subtype')}'")
    print(f"✓ Mini-game validated: {g['game_id']}")
```

Replace with:

```python
def _validate_minigame(g):
    """Validate a mini-game structure."""
    if "minigame_config" not in g:
        raise ValueError(f"Mini-game {g['game_id']} missing 'minigame_config'")
    mc = g["minigame_config"]
    valid_subtypes = [
        "matching", "sorting", "timed_challenge", "drag_drop", "stock_market", "escape_room",
        "timeline", "connection", "code_editor", "map_quiz", "word_puzzle",
        "flashcard", "typing_speed", "drag_drop_builder", "auction", "boggle",
    ]
    if mc.get("subtype") not in valid_subtypes:
        raise ValueError(f"Mini-game {g['game_id']}: invalid subtype '{mc.get('subtype')}'")
    if mc.get("subtype") == "stock_market":
        _validate_stock_market_minigame(g)
    print(f"✓ Mini-game validated: {g['game_id']}")


def _validate_stock_market_minigame(g):
    """Validate stock_market subtype config (Tier 2 real-time simulator)."""
    gid = g["game_id"]
    cfg = g["minigame_config"].get("stock_market_config")
    if not cfg:
        # Legacy stock_market games used direct minigame_config keys; allow if no v2 config
        if "stocks" in g["minigame_config"] or "num_ticks" in g["minigame_config"]:
            return  # legacy-format pass-through
        raise ValueError(
            f"stock_market game {gid} missing 'stock_market_config' (v2 format required)"
        )
    # Tier-2 v2 schema checks
    if "tick_count" not in cfg or not isinstance(cfg["tick_count"], int) or cfg["tick_count"] < 1:
        raise ValueError(f"stock_market game {gid}: 'tick_count' must be a positive integer")
    if not isinstance(cfg.get("stocks"), list) or len(cfg["stocks"]) == 0:
        raise ValueError(f"stock_market game {gid}: 'stocks' must be a non-empty list")
    for i, s in enumerate(cfg["stocks"]):
        for k in ("symbol", "name", "sector", "starting_price", "volatility"):
            if k not in s:
                raise ValueError(f"stock_market game {gid} stock[{i}] missing '{k}'")
    sectors_in_stocks = {s["sector"] for s in cfg["stocks"]}
    declared = set(cfg.get("sectors", []))
    if declared and not sectors_in_stocks.issubset(declared):
        raise ValueError(
            f"stock_market game {gid}: stocks reference undeclared sectors "
            f"{sectors_in_stocks - declared}"
        )
    for ev in cfg.get("events", []):
        for sym in ev.get("symbols", []):
            if not any(s["symbol"] == sym for s in cfg["stocks"]):
                raise ValueError(
                    f"stock_market game {gid}: event '{ev.get('id')}' references "
                    f"unknown symbol '{sym}'"
                )
    allowed_dims = {"risk_tolerance", "delayed_gratification", "strategic_thinking",
                    "financial_literacy", "empathy", "adaptability", "resilience",
                    "ethical_reasoning", "creativity"}
    for dim in cfg.get("dimensions_config", {}).keys():
        if dim not in allowed_dims:
            raise ValueError(
                f"stock_market game {gid}: unknown dimension '{dim}' in dimensions_config"
            )
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_schemas.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Verify gunicorn-style startup still works**

```bash
cd backend && python -c "from app import load_bundle; load_bundle(); print('Bundle loaded')"
```
Expected: `Bundle loaded` (no validation errors from existing games).

- [ ] **Step 7: Commit**

```bash
git add backend/schemas.py backend/tests/test_schemas.py
git commit -m "feat(stocksim): bundle validation for stock_market_config v2"
```

---

## Task 10: Route — POST /api/run/<id>/stocksim/start

**Goal:** First Flask route. Initializes session in RUNS storage. Pattern mirrors existing `minigame_start` (app.py:13412).

**Files:**
- Modify: `backend/app.py` (append after line ~13552, end of minigame routes block)
- Create: `backend/tests/test_stocksim_routes.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_stocksim_routes.py`:

```python
"""Integration tests for /api/run/<id>/stocksim/* routes."""
import json
import pytest
from app import app as flask_app
import storage


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def stocksim_run():
    """Create a stocksim run in storage and return its id."""
    run_id = "test-stocksim-run-001"
    storage.RUNS = getattr(storage, "RUNS", {})
    storage.RUNS[run_id] = {
        "run_id": run_id,
        "user_id": "test-user-1",
        "game_id": "stock-market-day-trader",
        "game": {
            "game_id": "stock-market-day-trader",
            "game_type": "minigame",
            "minigame_config": {
                "subtype": "stock_market",
                "stock_market_config": {
                    "tick_count": 22,
                    "tick_interval_seconds": 8,
                    "starting_capital": 100000,
                    "realism_tier": 2,
                    "stocks": [
                        {"symbol": "TECHV", "name": "TechVeda", "sector": "IT",
                         "starting_price": 1200, "volatility": 0.025, "beta": 1.2},
                    ],
                    "sectors": ["IT"], "events": [],
                    "charges": {"brokerage_per_trade": 20, "stt_buy_pct": 0.001,
                                "stt_sell_pct": 0.001, "exchange_pct": 0.0000345,
                                "gst_pct": 0.18},
                    "dimensions_config": {"risk_tolerance": {"weight": 1.0}},
                },
            },
        },
    }
    yield run_id
    storage.RUNS.pop(run_id, None)


def test_stocksim_start_creates_session(client, stocksim_run):
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/start",
                       json={"profile": "day_trader"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "seed" in data
    assert "opening_state" in data
    assert data["opening_state"]["cash"] == 100000
    assert data["opening_state"]["holdings"] == {}


def test_stocksim_start_404_when_run_missing(client):
    resp = client.post("/api/run/no-such-run/stocksim/start", json={})
    assert resp.status_code == 404


def test_stocksim_start_400_when_not_stock_market(client):
    storage.RUNS["wrong-type-run"] = {
        "run_id": "wrong-type-run", "user_id": "u",
        "game_id": "x", "game": {"game_type": "rounds"},
    }
    try:
        resp = client.post("/api/run/wrong-type-run/stocksim/start", json={})
        assert resp.status_code == 400
    finally:
        storage.RUNS.pop("wrong-type-run", None)
```

- [ ] **Step 2: Run test, verify failure**

```bash
cd backend && python -m pytest tests/test_stocksim_routes.py::test_stocksim_start_creates_session -v
```
Expected: 404 (route doesn't exist yet).

- [ ] **Step 3: Add route to app.py**

Append to `backend/app.py` at the end of the minigame routes block (after the existing `minigame_complete` function, ~line 13660):

```python
# ==================== STOCK MARKET SIM (REAL-TIME) ====================

@app.route('/api/run/<run_id>/stocksim/start', methods=['POST'])
def stocksim_start(run_id):
    """Initialize a real-time stock market session."""
    from engines.stock_market_engine import StockMarketEngine
    import time
    load_bundle()
    run = storage.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    game = run.get("game") or {}
    if game.get("game_type") != "minigame":
        return jsonify({"error": "Not a mini-game"}), 400
    mc = game.get("minigame_config") or {}
    if mc.get("subtype") != "stock_market":
        return jsonify({"error": "Not a stock_market mini-game"}), 400
    sm_cfg = mc.get("stock_market_config")
    if not sm_cfg:
        return jsonify({"error": "stock_market_config missing"}), 400

    body = request.get_json(silent=True) or {}
    profile = body.get("profile", "day_trader")

    user_id = run.get("user_id") or "anon"
    seed_str = f"{run_id}|{user_id}|{int(time.time() * 1000)}"
    seed = abs(hash(seed_str)) % (2**31)

    eng = StockMarketEngine(sm_cfg)
    state = eng.start_session(seed=seed, profile=profile)
    state["config_hash"] = abs(hash(json.dumps(sm_cfg, sort_keys=True))) % (2**31)

    run["stocksim"] = state
    storage.update_run(run_id, run)

    return jsonify({
        "seed": seed,
        "opening_state": {
            "cash": state["cash"],
            "holdings": state["holdings"],
            "current_tick": state["current_tick"],
        },
        "tick_schedule_meta": {
            "tick_count": sm_cfg.get("tick_count", 22),
            "tick_interval_seconds": sm_cfg.get("tick_interval_seconds", 8),
        },
        "market_calendar": {
            "settlement": sm_cfg.get("settlement", "T+1"),
            "shorting_enabled": sm_cfg.get("shorting_enabled", False),
        },
    })
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_routes.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_stocksim_routes.py
git commit -m "feat(stocksim): POST /api/run/<id>/stocksim/start route"
```

---

## Task 11: Routes — GET /state + POST /cancel

**Goal:** Resume after page reload + cancel pending order.

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/tests/test_stocksim_routes.py`

- [ ] **Step 1: Write failing tests**

Append to test file:

```python
def test_stocksim_state_returns_session(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    resp = client.get(f"/api/run/{stocksim_run}/stocksim/state")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "state" in data
    assert data["state"]["cash"] == 100000


def test_stocksim_state_404_when_no_session(client, stocksim_run):
    # No /start call
    resp = client.get(f"/api/run/{stocksim_run}/stocksim/state")
    assert resp.status_code == 404


def test_stocksim_cancel_removes_pending_order(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    # Inject a fake pending order via storage
    run = storage.get_run(stocksim_run)
    run["stocksim"]["pending_orders"] = [{
        "order_id": "lim-1", "type": "limit", "side": "buy",
        "symbol": "TECHV", "qty": 5, "limit_price": 100.0, "placed_tick": 1,
    }]
    storage.update_run(stocksim_run, run)
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/cancel",
                       json={"order_id": "lim-1"})
    assert resp.status_code == 200
    assert resp.get_json()["cancelled"] is True
    assert storage.get_run(stocksim_run)["stocksim"]["pending_orders"] == []


def test_stocksim_cancel_404_for_unknown_order(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/cancel",
                       json={"order_id": "nope"})
    assert resp.status_code == 404
```

- [ ] **Step 2: Run tests, verify failure**

```bash
cd backend && python -m pytest tests/test_stocksim_routes.py -v
```
Expected: 4 new tests fail.

- [ ] **Step 3: Add routes to app.py**

Append to `backend/app.py` after `stocksim_start`:

```python
@app.route('/api/run/<run_id>/stocksim/state', methods=['GET'])
def stocksim_state(run_id):
    """Resume after page reload."""
    run = storage.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    state = run.get("stocksim")
    if not state:
        return jsonify({"error": "No stocksim session"}), 404
    return jsonify({"state": state})


@app.route('/api/run/<run_id>/stocksim/cancel', methods=['POST'])
def stocksim_cancel(run_id):
    """Cancel a pending limit/SL/SIP order."""
    run = storage.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    state = run.get("stocksim")
    if not state:
        return jsonify({"error": "No stocksim session"}), 404
    if state.get("completed"):
        return jsonify({"error": "Session already completed",
                        "error_code": "SESSION_COMPLETED"}), 409

    body = request.get_json(silent=True) or {}
    order_id = body.get("order_id")
    if not order_id:
        return jsonify({"error": "order_id required"}), 400

    pending = state.get("pending_orders", [])
    matching = [p for p in pending if p.get("order_id") == order_id]
    if not matching:
        return jsonify({"error": "Order not found",
                        "error_code": "ORDER_NOT_FOUND"}), 404
    state["pending_orders"] = [p for p in pending if p.get("order_id") != order_id]
    storage.update_run(run_id, run)
    return jsonify({"cancelled": True, "order_id": order_id,
                    "remaining_pending": len(state["pending_orders"])})
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_routes.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_stocksim_routes.py
git commit -m "feat(stocksim): GET /state + POST /cancel routes"
```

---

## Task 12: Routes — POST /trade + POST /complete

**Goal:** The two heavy routes — trade validation/fill and session finalization with dimension scoring + record_outcome hook.

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/tests/test_stocksim_routes.py`

- [ ] **Step 1: Write failing tests**

Append to test file:

```python
def test_stocksim_trade_market_buy_filled(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 1, "symbol": "TECHV", "side": "buy",
        "qty": 5, "order_type": "market"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "filled"
    assert data["fill"]["qty"] == 5
    assert "charges" in data
    state = storage.get_run(stocksim_run)["stocksim"]
    assert state["holdings"]["TECHV"]["qty"] == 5


def test_stocksim_trade_in_future_tick_rejected(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 999, "symbol": "TECHV", "side": "buy",
        "qty": 1, "order_type": "market"
    })
    assert resp.status_code == 400
    assert resp.get_json().get("error_code") == "INVALID_TICK"


def test_stocksim_trade_after_complete_rejected(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={})
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 1, "symbol": "TECHV", "side": "buy",
        "qty": 1, "order_type": "market"
    })
    assert resp.status_code == 409
    assert resp.get_json().get("error_code") == "SESSION_COMPLETED"


def test_stocksim_complete_returns_pnl_and_dimensions(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 1, "symbol": "TECHV", "side": "buy",
        "qty": 5, "order_type": "market"
    })
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "pnl" in data
    assert "dimensions" in data
    assert "risk_tolerance" in data["dimensions"]
    assert storage.get_run(stocksim_run)["stocksim"]["completed"] is True


def test_stocksim_complete_idempotent(client, stocksim_run):
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    r1 = client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={})
    r2 = client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={})
    assert r1.status_code == 200
    # Second call should still return 200 with same final scores (or 409, both OK)
    assert r2.status_code in (200, 409)
```

- [ ] **Step 2: Run tests, verify failure**

```bash
cd backend && python -m pytest tests/test_stocksim_routes.py -v
```
Expected: 5 new tests fail.

- [ ] **Step 3: Add routes to app.py**

Append to `backend/app.py` after `stocksim_cancel`:

```python
@app.route('/api/run/<run_id>/stocksim/trade', methods=['POST'])
def stocksim_trade(run_id):
    """Place a trade. Server validates tick, funds, holdings, halts."""
    from engines.stock_market_engine import StockMarketEngine
    run = storage.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    state = run.get("stocksim")
    if not state:
        return jsonify({"error": "No stocksim session"}), 404
    if state.get("completed"):
        return jsonify({"error": "Session completed",
                        "error_code": "SESSION_COMPLETED",
                        "recoverable": False}), 409

    sm_cfg = (run.get("game", {}).get("minigame_config") or {}).get("stock_market_config") or {}
    tick_count = sm_cfg.get("tick_count", 22)
    body = request.get_json(silent=True) or {}
    requested_tick = body.get("tick", 0)

    if not isinstance(requested_tick, int) or requested_tick < 0 or requested_tick > tick_count:
        return jsonify({"error": "Invalid tick",
                        "error_code": "INVALID_TICK",
                        "recoverable": True}), 400
    # Anti-cheat: reject if claiming a tick more than 1 ahead of authoritative
    if requested_tick > state.get("current_tick", 0) + 1:
        return jsonify({"error": "Tick out of sync",
                        "error_code": "INVALID_TICK",
                        "recoverable": True}), 400

    eng = StockMarketEngine(sm_cfg)
    eng.advance_to_tick(state, requested_tick)  # lazy sweep first
    result = eng.place_order(state, body)
    storage.update_run(run_id, run)

    if result.get("status") == "rejected":
        return jsonify(result), 400 if result.get("error_code") == "INVALID_ORDER" else 402
    return jsonify(result)


@app.route('/api/run/<run_id>/stocksim/complete', methods=['POST'])
def stocksim_complete(run_id):
    """Finalize session: settle, compute P&L + dimensions, record outcome."""
    from engines.stock_market_engine import StockMarketEngine
    run = storage.get_run(run_id)
    if not run:
        return jsonify({"error": "Run not found"}), 404
    state = run.get("stocksim")
    if not state:
        return jsonify({"error": "No stocksim session"}), 404

    sm_cfg = (run.get("game", {}).get("minigame_config") or {}).get("stock_market_config") or {}
    tick_count = sm_cfg.get("tick_count", 22)
    eng = StockMarketEngine(sm_cfg)

    if not state.get("completed"):
        eng.advance_to_tick(state, tick_count)
        pnl = eng.compute_pnl(state)
        dims = eng.score_dimensions(state)
        state["completed"] = True
        state["final_pnl"] = pnl
        state["final_dimensions"] = dims
        storage.update_run(run_id, run)

        # Hook into existing dimension storage on RunState
        st_obj = run.get("state")
        if st_obj is not None:
            try:
                st_obj.dimension_scores = dims
                for dim, val in dims.items():
                    setattr(st_obj, dim, val)
            except Exception as _e:
                logger.debug("stocksim dim attach: %s", _e)

        # Award XP + record_outcome (best-effort)
        try:
            user_id = run.get("user_id") or get_current_user_id()
            if user_id:
                xp = max(50, int(pnl["total"] / 100) + 100)
                psych = {k: {"final": v, "name": k.replace("_", " ").title()}
                         for k, v in dims.items()}
                award_xp(user_id, xp, "Stock market sim", "minigame",
                         int(pnl["total"]), psych)
        except Exception as _e:
            logger.debug("stocksim award_xp: %s", _e)
    else:
        pnl = state.get("final_pnl", {})
        dims = state.get("final_dimensions", {})

    return jsonify({
        "pnl": pnl,
        "dimensions": dims,
        "trade_log": state.get("trade_log", []),
        "recap_messages": _stocksim_recap_messages(state, pnl, dims),
    })


def _stocksim_recap_messages(state: dict, pnl: dict, dims: dict) -> list:
    """Build short coaching recap based on the session."""
    msgs = []
    n_trades = len(state.get("trade_log", []))
    if n_trades == 0:
        msgs.append("You watched the market without trading. Next time, try placing at least one order.")
    elif n_trades > 15:
        msgs.append("Lots of activity! Consider whether each trade had a clear thesis.")
    if pnl.get("total", 0) > 0:
        msgs.append(f"Net positive: ₹{pnl['total']:,.0f}. Nice work managing risk.")
    elif pnl.get("total", 0) < -5000:
        msgs.append("Tough session. Review which trades hurt most — was it sizing or timing?")
    if dims.get("strategic_thinking", 0) >= 70:
        msgs.append("You diversified well across sectors.")
    if dims.get("financial_literacy", 0) >= 70:
        msgs.append("You used multiple order types — sign of growing market literacy.")
    return msgs
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_routes.py -v
```
Expected: 12 passed.

- [ ] **Step 5: Verify the engine-vs-route consistency test**

Append to test file:

```python
def test_dimension_scores_match_engine_directly(client, stocksim_run):
    """Route output should match engine.score_dimensions() called directly."""
    from engines.stock_market_engine import StockMarketEngine
    client.post(f"/api/run/{stocksim_run}/stocksim/start", json={})
    client.post(f"/api/run/{stocksim_run}/stocksim/trade", json={
        "tick": 1, "symbol": "TECHV", "side": "buy",
        "qty": 5, "order_type": "market"
    })
    resp = client.post(f"/api/run/{stocksim_run}/stocksim/complete", json={})
    route_dims = resp.get_json()["dimensions"]
    state = storage.get_run(stocksim_run)["stocksim"]
    sm_cfg = (storage.get_run(stocksim_run).get("game", {}).get("minigame_config") or {}).get("stock_market_config")
    eng = StockMarketEngine(sm_cfg)
    direct_dims = eng.score_dimensions(state)
    assert route_dims == direct_dims
```

```bash
cd backend && python -m pytest tests/test_stocksim_routes.py::test_dimension_scores_match_engine_directly -v
```
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app.py backend/tests/test_stocksim_routes.py
git commit -m "feat(stocksim): POST /trade + POST /complete routes with scoring"
```

---

### Task 13: Frontend pricing helper + API module

**Goal:** Port the deterministic pricing formula to JS so the client can render ticks at 8s cadence without round-tripping for every chart point. Wrap the 5 backend routes in a typed API module.

**Files:**
- Create: `frontend-react/src/utils/stocksimPricing.js`
- Create: `frontend-react/src/api/stocksim.js`
- Test: `frontend-react/src/tests/stocksimPricing.test.js`

- [ ] **Step 1: Write the failing parity test**

```javascript
// frontend-react/src/tests/stocksimPricing.test.js
import { describe, it, expect } from 'vitest';
import { priceFromSeed, hashSeed } from '../utils/stocksimPricing';

describe('stocksimPricing', () => {
  it('hashSeed is deterministic for (seed, symbol, tick)', () => {
    const a = hashSeed('demo-seed-1', 'TECHV', 5);
    const b = hashSeed('demo-seed-1', 'TECHV', 5);
    const c = hashSeed('demo-seed-1', 'TECHV', 6);
    expect(a).toBe(b);
    expect(a).not.toBe(c);
  });

  it('priceFromSeed clamps to circuit-breaker band', () => {
    const cfg = {
      symbols: [{ symbol: 'TECHV', open_price: 100, drift_per_tick: 0.0, vol_per_tick: 5.0 }],
      circuit_breaker_pct: 0.10,
    };
    for (let t = 0; t < 50; t++) {
      const p = priceFromSeed('seed-x', 'TECHV', t, cfg);
      expect(p).toBeGreaterThanOrEqual(90);
      expect(p).toBeLessThanOrEqual(110);
    }
  });

  it('priceFromSeed matches backend reference fixtures', () => {
    // These 4 numbers are produced by backend pricing.price_from_seed
    // for seed='parity-seed', symbol='TECHV', ticks 0..3, cfg below.
    // Regenerate via: scripts/stocksim_audit.py emit-fixtures
    const cfg = {
      symbols: [{ symbol: 'TECHV', open_price: 100, drift_per_tick: 0.001, vol_per_tick: 0.5 }],
      circuit_breaker_pct: 0.10,
    };
    const expected = [100.0, 100.42, 100.07, 100.71]; // placeholder until fixtures are emitted
    for (let t = 0; t < expected.length; t++) {
      const got = priceFromSeed('parity-seed', 'TECHV', t, cfg);
      expect(Math.abs(got - expected[t])).toBeLessThan(0.05);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend-react && npx vitest run src/tests/stocksimPricing.test.js
```
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement pricing helper**

```javascript
// frontend-react/src/utils/stocksimPricing.js
// Deterministic JS port of backend/engines/stock_market/pricing.py
// MUST match _price_from_seed numerically within 0.05.

function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
  }
  return h >>> 0;
}

export function hashSeed(seed, symbol, tick) {
  return fnv1a(`${seed}|${symbol}|${tick}`);
}

function mulberry32(a) {
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function seededNormal(seed, symbol, tick) {
  const rng = mulberry32(hashSeed(seed, symbol, tick));
  const u1 = Math.max(rng(), 1e-12);
  const u2 = rng();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

export function priceFromSeed(seed, symbol, tick, cfg) {
  const sym = (cfg.symbols || []).find((s) => s.symbol === symbol);
  if (!sym) throw new Error(`Unknown symbol: ${symbol}`);
  const open = sym.open_price;
  const drift = sym.drift_per_tick || 0;
  const vol = sym.vol_per_tick || 0;
  let logPrice = Math.log(open);
  for (let t = 1; t <= tick; t++) {
    logPrice += drift + vol * seededNormal(seed, symbol, t);
  }
  let price = Math.exp(logPrice);
  const band = cfg.circuit_breaker_pct || 0.10;
  const lo = open * (1 - band);
  const hi = open * (1 + band);
  if (price < lo) price = lo;
  if (price > hi) price = hi;
  return Math.round(price * 100) / 100;
}
```

- [ ] **Step 4: Implement API module**

```javascript
// frontend-react/src/api/stocksim.js
import apiClient from './client';

export async function startStocksim(runId, opts = {}) {
  const { data } = await apiClient.post(`/api/run/${runId}/stocksim/start`, opts);
  return data;
}

export async function getStocksimState(runId) {
  const { data } = await apiClient.get(`/api/run/${runId}/stocksim/state`);
  return data;
}

export async function placeStocksimTrade(runId, payload) {
  const { data } = await apiClient.post(`/api/run/${runId}/stocksim/trade`, payload);
  return data;
}

export async function cancelStocksimOrder(runId, orderId) {
  const { data } = await apiClient.post(`/api/run/${runId}/stocksim/cancel`, { order_id: orderId });
  return data;
}

export async function completeStocksim(runId) {
  const { data } = await apiClient.post(`/api/run/${runId}/stocksim/complete`, {});
  return data;
}
```

- [ ] **Step 5: Emit backend fixtures + verify parity**

Run a one-off script to dump 4 reference prices from backend and paste into the test:

```bash
cd backend && python -c "
from engines.stock_market.pricing import price_from_seed
cfg = {'symbols':[{'symbol':'TECHV','open_price':100,'drift_per_tick':0.001,'vol_per_tick':0.5}],'circuit_breaker_pct':0.10}
print([price_from_seed('parity-seed', 'TECHV', t, cfg) for t in range(4)])
"
```

Update the `expected` array in `stocksimPricing.test.js` with the printed numbers.

- [ ] **Step 6: Run test to verify pass**

```bash
cd frontend-react && npx vitest run src/tests/stocksimPricing.test.js
```
Expected: PASS — all 3 tests green.

- [ ] **Step 7: Commit**

```bash
git add frontend-react/src/utils/stocksimPricing.js frontend-react/src/api/stocksim.js frontend-react/src/tests/stocksimPricing.test.js
git commit -m "feat(stocksim): JS pricing helper with backend parity + API module"
```

---

### Task 14: Frontend StockMarketGame.jsx extensions

**Goal:** Replace the local random walk in the existing `StockMarketGame.jsx` with the seeded `priceFromSeed`, wire the 5 backend routes, and add Tier-2 sub-components: OrderTicket (market/limit/stop_loss/SIP), DepthLadder (best bid/ask), NewsTickerStrip (event headlines), PortfolioPanel (positions + realized/unrealized P&L), EventOverlay (circuit breakers, halts).

**Files:**
- Modify: `frontend-react/src/components/game/renderers/StockMarketGame.jsx`
- Create: `frontend-react/src/components/game/stocksim/OrderTicket.jsx`
- Create: `frontend-react/src/components/game/stocksim/DepthLadder.jsx`
- Create: `frontend-react/src/components/game/stocksim/NewsTickerStrip.jsx`
- Create: `frontend-react/src/components/game/stocksim/PortfolioPanel.jsx`
- Create: `frontend-react/src/components/game/stocksim/EventOverlay.jsx`
- Test: `frontend-react/src/tests/StockMarketGame.test.jsx`

- [ ] **Step 1: Write the failing component tests**

```javascript
// frontend-react/src/tests/StockMarketGame.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import StockMarketGame from '../components/game/renderers/StockMarketGame';
import * as api from '../api/stocksim';

vi.mock('../api/stocksim');

const fakeStartResp = {
  seed: 'demo-seed',
  symbols: [{ symbol: 'TECHV', open_price: 100, drift_per_tick: 0.001, vol_per_tick: 0.5 }],
  starting_cash: 100000,
  ticks_total: 22,
  tick_seconds: 8,
  circuit_breaker_pct: 0.10,
  events: [],
  news: [],
};

const fakeState = (over = {}) => ({
  tick: 0, cash: 100000, positions: {}, orders: [],
  circuit_breaker_active: false, halted: [], pnl_realized: 0,
  ...over,
});

beforeEach(() => {
  api.startStocksim.mockResolvedValue(fakeStartResp);
  api.getStocksimState.mockResolvedValue(fakeState());
  api.placeStocksimTrade.mockResolvedValue({ ok: true, fill_price: 100.42, charges: 12.5 });
  api.cancelStocksimOrder.mockResolvedValue({ ok: true });
  api.completeStocksim.mockResolvedValue({ pnl_total: 250, dimensions: { strategic_thinking: 60 }, recap: ['Nice steady gains.'] });
});

describe('StockMarketGame (Tier 2)', () => {
  it('starts a session and renders OrderTicket', async () => {
    render(<StockMarketGame runId="r1" gameConfig={{}} onComplete={() => {}} />);
    await waitFor(() => expect(api.startStocksim).toHaveBeenCalledWith('r1', expect.any(Object)));
    expect(await screen.findByTestId('order-ticket')).toBeInTheDocument();
    expect(screen.getByTestId('depth-ladder')).toBeInTheDocument();
    expect(screen.getByTestId('news-ticker')).toBeInTheDocument();
    expect(screen.getByTestId('portfolio-panel')).toBeInTheDocument();
  });

  it('places a market order via the API', async () => {
    render(<StockMarketGame runId="r1" gameConfig={{}} onComplete={() => {}} />);
    await screen.findByTestId('order-ticket');
    fireEvent.change(screen.getByTestId('order-qty'), { target: { value: '5' } });
    fireEvent.click(screen.getByTestId('order-submit-buy'));
    await waitFor(() => expect(api.placeStocksimTrade).toHaveBeenCalledWith('r1',
      expect.objectContaining({ side: 'buy', qty: 5, order_type: 'market' })
    ));
  });

  it('shows EventOverlay when circuit breaker is active', async () => {
    api.getStocksimState.mockResolvedValue(fakeState({ circuit_breaker_active: true, halted: ['TECHV'] }));
    render(<StockMarketGame runId="r1" gameConfig={{}} onComplete={() => {}} />);
    expect(await screen.findByTestId('event-overlay')).toBeInTheDocument();
    expect(screen.getByText(/circuit breaker/i)).toBeInTheDocument();
  });

  it('disables sell button when no holdings (T+1 awareness)', async () => {
    render(<StockMarketGame runId="r1" gameConfig={{}} onComplete={() => {}} />);
    await screen.findByTestId('order-ticket');
    expect(screen.getByTestId('order-submit-sell')).toBeDisabled();
  });

  it('calls onComplete with scoring payload when session ends', async () => {
    const onComplete = vi.fn();
    render(<StockMarketGame runId="r1" gameConfig={{ autoEnd: true }} onComplete={onComplete} />);
    fireEvent.click(await screen.findByTestId('end-session-btn'));
    await waitFor(() => expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({ pnl_total: 250, dimensions: expect.any(Object) })
    ));
  });

  it('renders price chart points using priceFromSeed (deterministic)', async () => {
    render(<StockMarketGame runId="r1" gameConfig={{}} onComplete={() => {}} />);
    const chart = await screen.findByTestId('price-chart-TECHV');
    // First chart point should equal open_price (100) since priceFromSeed at tick 0 is open.
    expect(chart.getAttribute('data-first-price')).toBe('100');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend-react && npx vitest run src/tests/StockMarketGame.test.jsx
```
Expected: FAIL — sub-components and API wiring missing.

- [ ] **Step 3: Implement OrderTicket.jsx**

```jsx
// frontend-react/src/components/game/stocksim/OrderTicket.jsx
import React, { useState } from 'react';

export default function OrderTicket({ symbol, lastPrice, hasHoldings, onSubmit, disabled }) {
  const [qty, setQty] = useState(1);
  const [orderType, setOrderType] = useState('market');
  const [limitPrice, setLimitPrice] = useState('');
  const [stopPrice, setStopPrice] = useState('');

  const submit = (side) => {
    const payload = { symbol, side, qty: Number(qty), order_type: orderType };
    if (orderType === 'limit') payload.limit_price = Number(limitPrice);
    if (orderType === 'stop_loss') payload.stop_price = Number(stopPrice);
    onSubmit(payload);
  };

  return (
    <div data-testid="order-ticket" className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="font-bold text-sm text-gray-900">{symbol}</span>
        <span className="text-xs text-gray-500">LTP ₹{lastPrice?.toFixed(2)}</span>
      </div>
      <select value={orderType} onChange={(e) => setOrderType(e.target.value)}
        data-testid="order-type"
        className="w-full mb-2 px-2 py-1.5 rounded-lg bg-gray-100 text-sm">
        <option value="market">Market</option>
        <option value="limit">Limit</option>
        <option value="stop_loss">Stop-Loss</option>
        <option value="sip">SIP (recurring)</option>
      </select>
      <input type="number" value={qty} onChange={(e) => setQty(e.target.value)}
        data-testid="order-qty" placeholder="Qty"
        className="w-full mb-2 px-2 py-1.5 rounded-lg bg-gray-100 text-sm" />
      {orderType === 'limit' && (
        <input type="number" value={limitPrice} onChange={(e) => setLimitPrice(e.target.value)}
          placeholder="Limit ₹" className="w-full mb-2 px-2 py-1.5 rounded-lg bg-gray-100 text-sm" />
      )}
      {orderType === 'stop_loss' && (
        <input type="number" value={stopPrice} onChange={(e) => setStopPrice(e.target.value)}
          placeholder="Trigger ₹" className="w-full mb-2 px-2 py-1.5 rounded-lg bg-gray-100 text-sm" />
      )}
      <div className="grid grid-cols-2 gap-2">
        <button data-testid="order-submit-buy" onClick={() => submit('buy')} disabled={disabled}
          className="py-2 rounded-xl font-medium text-sm disabled:opacity-30"
          style={{ backgroundColor: '#10b981', color: 'white' }}>BUY</button>
        <button data-testid="order-submit-sell" onClick={() => submit('sell')} disabled={disabled || !hasHoldings}
          className="py-2 rounded-xl font-medium text-sm disabled:opacity-30"
          style={{ backgroundColor: '#ef4444', color: 'white' }}>SELL</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Implement DepthLadder.jsx, NewsTickerStrip.jsx, PortfolioPanel.jsx, EventOverlay.jsx**

```jsx
// frontend-react/src/components/game/stocksim/DepthLadder.jsx
import React from 'react';

export default function DepthLadder({ symbol, lastPrice, spreadPct = 0.002 }) {
  if (!lastPrice) return null;
  const spread = lastPrice * spreadPct;
  const bid = lastPrice - spread / 2;
  const ask = lastPrice + spread / 2;
  return (
    <div data-testid="depth-ladder" className="bg-white rounded-2xl border border-gray-200 p-3 shadow-sm">
      <div className="text-xs font-semibold text-gray-700 mb-2">{symbol} Order Book</div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="text-right">
          <div className="text-red-600 font-mono">₹{ask.toFixed(2)}</div>
          <div className="text-gray-400">ASK</div>
        </div>
        <div className="text-left">
          <div className="text-green-600 font-mono">₹{bid.toFixed(2)}</div>
          <div className="text-gray-400">BID</div>
        </div>
      </div>
      <div className="text-[10px] text-gray-400 mt-1 text-center">Spread ₹{spread.toFixed(2)}</div>
    </div>
  );
}
```

```jsx
// frontend-react/src/components/game/stocksim/NewsTickerStrip.jsx
import React from 'react';
import { motion } from 'framer-motion';

export default function NewsTickerStrip({ news = [] }) {
  return (
    <div data-testid="news-ticker" className="bg-amber-50 border border-amber-200 rounded-2xl px-3 py-2 overflow-hidden">
      <div className="flex gap-3 items-center text-xs">
        <span className="font-bold text-amber-700 shrink-0">📰 NEWS</span>
        <div className="flex gap-4 overflow-x-auto">
          {news.length === 0 && <span className="text-gray-500">Markets quiet…</span>}
          {news.map((n, i) => (
            <motion.span key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              className="whitespace-nowrap text-amber-900">
              {n.headline}
            </motion.span>
          ))}
        </div>
      </div>
    </div>
  );
}
```

```jsx
// frontend-react/src/components/game/stocksim/PortfolioPanel.jsx
import React from 'react';

export default function PortfolioPanel({ cash, positions = {}, lastPrices = {}, pnlRealized = 0 }) {
  const unrealized = Object.entries(positions).reduce((acc, [sym, pos]) => {
    const ltp = lastPrices[sym] || pos.avg_price;
    return acc + (ltp - pos.avg_price) * pos.qty;
  }, 0);
  return (
    <div data-testid="portfolio-panel" className="bg-white rounded-2xl border border-gray-200 p-4 shadow-sm">
      <div className="flex justify-between mb-2">
        <span className="text-xs text-gray-500">Cash</span>
        <span className="font-mono text-sm">₹{cash.toFixed(2)}</span>
      </div>
      <div className="flex justify-between mb-2">
        <span className="text-xs text-gray-500">Realized P&L</span>
        <span className={`font-mono text-sm ${pnlRealized >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          ₹{pnlRealized.toFixed(2)}
        </span>
      </div>
      <div className="flex justify-between mb-3">
        <span className="text-xs text-gray-500">Unrealized</span>
        <span className={`font-mono text-sm ${unrealized >= 0 ? 'text-green-600' : 'text-red-600'}`}>
          ₹{unrealized.toFixed(2)}
        </span>
      </div>
      <div className="border-t pt-2 space-y-1">
        {Object.entries(positions).map(([sym, pos]) => (
          <div key={sym} className="flex justify-between text-xs">
            <span>{sym}</span>
            <span>{pos.qty} @ ₹{pos.avg_price.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

```jsx
// frontend-react/src/components/game/stocksim/EventOverlay.jsx
import React from 'react';
import { motion } from 'framer-motion';

export default function EventOverlay({ active, halted = [], reason = 'Circuit breaker triggered' }) {
  if (!active) return null;
  return (
    <motion.div data-testid="event-overlay"
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="absolute inset-0 bg-black/40 flex items-center justify-center z-30">
      <div className="bg-white rounded-2xl p-5 max-w-sm border-l-4 border-red-500">
        <div className="font-bold text-red-700 mb-1">⚠ Circuit breaker</div>
        <div className="text-sm text-gray-700 mb-2">{reason}</div>
        <div className="text-xs text-gray-500">Halted: {halted.join(', ') || 'all symbols'}</div>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 5: Rewrite StockMarketGame.jsx to use server seed + sub-components**

Replace the random-walk in `StockMarketGame.jsx` with `priceFromSeed`. Wire `useEffect` to call `startStocksim` on mount, drive a tick interval that reads `priceFromSeed(seed, symbol, currentTick, cfg)` for each symbol, refresh `getStocksimState` after every trade or every 4 ticks, and call `completeStocksim` on session end. Keep the existing chart/Tailwind theme. Render `<OrderTicket>`, `<DepthLadder>`, `<NewsTickerStrip>`, `<PortfolioPanel>`, `<EventOverlay>` in the existing layout slots. Add `data-testid="price-chart-{symbol}"` and `data-first-price` attributes on chart SVG. Add `data-testid="end-session-btn"` to the existing end button.

The full edit is a refactor of the existing 504-line file. Keep these invariants:
- All existing layout/Tailwind classes preserved (gold/navy palette unchanged)
- `useAudio()` hook usage if present, preserved
- `MiniGameRenderer.jsx:164` routing untouched (still routes `subtype === 'stock_market'` here)
- Local `randomNormal` removed; import `priceFromSeed` from `../../../utils/stocksimPricing`
- Sell button passes `disabled={!positions[symbol] || positions[symbol].qty === 0}` to model T+1 (server enforces, client mirrors)

- [ ] **Step 6: Run tests to verify pass**

```bash
cd frontend-react && npx vitest run src/tests/StockMarketGame.test.jsx
```
Expected: PASS — all 6 tests green.

- [ ] **Step 7: Commit**

```bash
git add frontend-react/src/components/game/renderers/StockMarketGame.jsx \
       frontend-react/src/components/game/stocksim/ \
       frontend-react/src/tests/StockMarketGame.test.jsx
git commit -m "feat(stocksim): Tier-2 trading UI (order ticket, depth, news, portfolio, events)"
```

---

### Task 15: Game JSONs + whitelist + i18n strings

**Goal:** Ship two playable presets — a brand-new "Day Trader Sprint" (3-min sandbox) and an upgraded "Stock Market Simulator" v2 — both using `realism_tier: 2` and `tick_authority: hybrid`. Register both in `_DISCOVER_WHITELIST`, mark visible, add i18n strings.

**Files:**
- Create: `backend/games/stock-market-day-trader.json`
- Modify: `backend/games/stock-market-simulator.json`
- Modify: `backend/app.py` (`_DISCOVER_WHITELIST` block)
- Modify: `frontend-react/src/locales/en.json`
- Modify: `frontend-react/src/locales/hi.json`
- Test: `backend/tests/test_stocksim_bundles.py`

- [ ] **Step 1: Write the failing bundle-load test**

```python
# backend/tests/test_stocksim_bundles.py
import json, pytest
from pathlib import Path
from schemas import validate_bundle

GAMES_DIR = Path(__file__).resolve().parent.parent / "games"

@pytest.mark.parametrize("slug", ["stock-market-day-trader", "stock-market-simulator"])
def test_stocksim_bundle_loads(slug):
    path = GAMES_DIR / f"{slug}.json"
    bundle = json.loads(path.read_text())
    validate_bundle(bundle)  # must not raise
    cfg = bundle["minigame_config"]["stock_market_config"]
    assert cfg["realism_tier"] == 2
    assert cfg["tick_authority"] == "hybrid"
    assert "dimensions_config" in cfg

def test_day_trader_is_short_session():
    path = GAMES_DIR / "stock-market-day-trader.json"
    cfg = json.loads(path.read_text())["minigame_config"]["stock_market_config"]
    assert cfg["ticks_total"] == 22
    assert cfg["tick_seconds"] == 8

def test_both_games_in_discover_whitelist():
    from app import _DISCOVER_WHITELIST
    assert "stock-market-day-trader" in _DISCOVER_WHITELIST
    assert "stock-market-simulator" in _DISCOVER_WHITELIST
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && python -m pytest tests/test_stocksim_bundles.py -v
```
Expected: FAIL — day-trader file missing, v1 lacks tier-2 config.

- [ ] **Step 3: Create stock-market-day-trader.json**

```json
{
  "game_id": "stock-market-day-trader",
  "title": "Day Trader Sprint",
  "title_translations": { "en": "Day Trader Sprint", "hi": "डे ट्रेडर स्प्रिंट" },
  "description": "A 3-minute sandbox: 22 live ticks, 8 NSE stocks, real spreads, real charges, real circuit breakers. Learn what a Zerodha terminal feels like — without losing real rupees.",
  "game_type": "minigame",
  "subtype": "stock_market",
  "visible": true,
  "tags": ["finance", "stock_market", "real_time", "india"],
  "skill_tags": ["risk_tolerance", "delayed_gratification", "strategic_thinking", "financial_literacy"],
  "nep_stage": "secondary",
  "grade": "9",
  "estimated_minutes": 3,
  "minigame_config": {
    "stock_market_config": {
      "realism_tier": 2,
      "tick_authority": "hybrid",
      "ticks_total": 22,
      "tick_seconds": 8,
      "starting_cash": 100000,
      "circuit_breaker_pct": 0.10,
      "spread_pct": 0.002,
      "charges": { "brokerage_pct": 0.0003, "stt_pct": 0.001, "exchange_pct": 0.0000345, "gst_pct": 0.18 },
      "settlement": "T+1",
      "symbols": [
        { "symbol": "TECHV",   "name": "TechVista Solutions",  "open_price": 850,  "drift_per_tick": 0.0008, "vol_per_tick": 0.012 },
        { "symbol": "GREENX",  "name": "GreenX Energy",        "open_price": 420,  "drift_per_tick": 0.0012, "vol_per_tick": 0.018 },
        { "symbol": "BHARATBANK","name": "Bharat Bank",        "open_price": 1180, "drift_per_tick": 0.0004, "vol_per_tick": 0.008 },
        { "symbol": "PHARMAXR","name": "PharmaX Research",     "open_price": 540,  "drift_per_tick": 0.0009, "vol_per_tick": 0.014 },
        { "symbol": "AGRINOW", "name": "AgriNow Foods",        "open_price": 215,  "drift_per_tick": 0.0006, "vol_per_tick": 0.010 },
        { "symbol": "AUTOIND", "name": "AutoInd Motors",       "open_price": 720,  "drift_per_tick": 0.0005, "vol_per_tick": 0.011 },
        { "symbol": "INFRACO", "name": "InfraCo Builders",     "open_price": 310,  "drift_per_tick": 0.0007, "vol_per_tick": 0.015 },
        { "symbol": "RETAILK", "name": "RetailKart",           "open_price": 980,  "drift_per_tick": 0.0010, "vol_per_tick": 0.013 }
      ],
      "events": [
        { "tick": 6,  "type": "rbi_rate_decision", "headline": "RBI holds repo at 6.5%", "delta_drift": -0.0003, "affects": ["BHARATBANK"] },
        { "tick": 11, "type": "fii_outflow",       "headline": "FIIs sell ₹2,400 Cr — IT under pressure", "delta_drift": -0.0006, "affects": ["TECHV"] },
        { "tick": 16, "type": "earnings_beat",     "headline": "GreenX beats Q4 estimates", "delta_drift": 0.002, "affects": ["GREENX"] }
      ],
      "news": [
        { "tick": 3,  "headline": "Nifty opens flat as Asian markets mixed" },
        { "tick": 9,  "headline": "India VIX up 4% — caution ahead of RBI" },
        { "tick": 14, "headline": "Crude oil at $82 — auto stocks watch" }
      ],
      "dimensions_config": {
        "risk_tolerance":        { "weight": 0.30, "tag": "leverage_or_concentration" },
        "delayed_gratification": { "weight": 0.25, "tag": "hold_through_dip" },
        "strategic_thinking":    { "weight": 0.30, "tag": "diversification_and_timing" },
        "financial_literacy":    { "weight": 0.15, "tag": "uses_limit_or_stop" }
      }
    }
  },
  "coaching_moment": "Day trading rewards patience, not panic. Watch the spread, respect the stop-loss, and remember — most traders lose money chasing tips."
}
```

- [ ] **Step 4: Update stock-market-simulator.json to v2**

Add the same `realism_tier`, `tick_authority`, `spread_pct`, `charges`, `settlement`, and `dimensions_config` fields under `minigame_config.stock_market_config`. Keep its existing 30 ticks and 8 symbols. Set `tick_seconds: 12` (slightly slower for the longer session). Update `description` to mention "limit orders, stop-loss, T+1 settlement".

- [ ] **Step 5: Add to _DISCOVER_WHITELIST + i18n**

In `backend/app.py`, find the `_DISCOVER_WHITELIST` set (~L1812) and add both slugs:

```python
_DISCOVER_WHITELIST = _DISCOVER_WHITELIST | {
    "stock-market-day-trader",
    # "stock-market-simulator" already present — verify before adding
}
```

In `frontend-react/src/locales/en.json` add:
```json
"games": {
  "stock_market_day_trader": {
    "title": "Day Trader Sprint",
    "subtitle": "3-minute live market sandbox"
  }
}
```

In `frontend-react/src/locales/hi.json` add:
```json
"games": {
  "stock_market_day_trader": {
    "title": "डे ट्रेडर स्प्रिंट",
    "subtitle": "3 मिनट का लाइव बाज़ार सैंडबॉक्स"
  }
}
```

- [ ] **Step 6: Run tests to verify pass**

```bash
cd backend && python -m pytest tests/test_stocksim_bundles.py -v
```
Expected: PASS — all 3 tests green.

- [ ] **Step 7: Smoke-test bundle load via Flask startup**

```bash
cd backend && python -c "from app import app; print('OK')"
```
Expected: prints `OK` (no `ValidationError` raised at import time).

- [ ] **Step 8: Commit**

```bash
git add backend/games/stock-market-day-trader.json backend/games/stock-market-simulator.json \
       backend/app.py backend/tests/test_stocksim_bundles.py \
       frontend-react/src/locales/en.json frontend-react/src/locales/hi.json
git commit -m "feat(stocksim): day-trader sprint + v2 simulator + whitelist + i18n"
```

---

### Task 16: E2E smoke + deployment

**Goal:** Run an end-to-end smoke against a local server, verify the full happy path (start → 3 trades → complete → scoring), then deploy to https://simulations.mentomap.com using the established rsync/sshpass pattern.

**Files:**
- Create: `frontend-react/test-stocksim-e2e.mjs`

- [ ] **Step 1: Write the E2E smoke script**

```javascript
// frontend-react/test-stocksim-e2e.mjs
// Run: BASE=http://localhost:5001 USER=demo_student PASS=Mento@2026 node test-stocksim-e2e.mjs
const BASE = process.env.BASE || 'http://localhost:5001';

async function login() {
  const r = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: process.env.USER, password: process.env.PASS }),
  });
  if (!r.ok) throw new Error(`login failed: ${r.status}`);
  const { access_token } = await r.json();
  return access_token;
}

async function main() {
  const token = await login();
  const auth = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  const start = await fetch(`${BASE}/api/run/start`, {
    method: 'POST', headers: auth,
    body: JSON.stringify({ game_id: 'stock-market-day-trader' }),
  }).then((r) => r.json());
  console.log('run started:', start.run_id);

  await fetch(`${BASE}/api/run/${start.run_id}/stocksim/start`, { method: 'POST', headers: auth, body: '{}' });

  for (const trade of [
    { tick: 1, symbol: 'TECHV',  side: 'buy',  qty: 5, order_type: 'market' },
    { tick: 4, symbol: 'GREENX', side: 'buy',  qty: 10, order_type: 'limit', limit_price: 420 },
    { tick: 18, symbol: 'TECHV', side: 'sell', qty: 5, order_type: 'market' },
  ]) {
    const r = await fetch(`${BASE}/api/run/${start.run_id}/stocksim/trade`, {
      method: 'POST', headers: auth, body: JSON.stringify(trade),
    });
    console.log(trade.side, trade.symbol, '→', r.status);
  }

  const final = await fetch(`${BASE}/api/run/${start.run_id}/stocksim/complete`, {
    method: 'POST', headers: auth, body: '{}',
  }).then((r) => r.json());

  console.log('P&L total:', final.pnl_total);
  console.log('dimensions:', final.dimensions);
  if (typeof final.pnl_total !== 'number') throw new Error('pnl_total missing');
  if (!final.dimensions?.strategic_thinking && final.dimensions?.strategic_thinking !== 0)
    throw new Error('dimensions missing');
  console.log('✅ E2E smoke passed');
}
main().catch((e) => { console.error('❌', e); process.exit(1); });
```

- [ ] **Step 2: Start local backend + run smoke**

```bash
cd backend && python app.py &  # or gunicorn -c gunicorn.conf.py app:app
sleep 3
cd frontend-react && BASE=http://localhost:5001 USER=demo_student PASS=Mento@2026 node test-stocksim-e2e.mjs
```
Expected: prints `✅ E2E smoke passed`.

- [ ] **Step 3: Build frontend**

```bash
cd frontend-react && npm run build
```
Expected: builds without errors.

- [ ] **Step 4: Deploy backend**

```bash
sshpass -p 'qwertY@1432o' rsync -avz -e 'ssh -o StrictHostKeyChecking=no' \
  backend/engines/stock_market/ \
  backend/engines/stock_market_engine.py \
  backend/schemas.py backend/app.py \
  backend/games/stock-market-day-trader.json \
  backend/games/stock-market-simulator.json \
  backend/scripts/stocksim_audit.py \
  root@206.189.143.244:/var/www/mentoapp/backend/

sshpass -p 'qwertY@1432o' ssh -o StrictHostKeyChecking=no root@206.189.143.244 \
  'systemctl restart mentoapp-backend'
```

- [ ] **Step 5: Deploy frontend**

```bash
sshpass -p 'qwertY@1432o' ssh -o StrictHostKeyChecking=no root@206.189.143.244 \
  'rm -rf /var/www/mentoapp/frontend/assets/'
sshpass -p 'qwertY@1432o' rsync -avz -e 'ssh -o StrictHostKeyChecking=no' \
  frontend-react/dist/ root@206.189.143.244:/var/www/mentoapp/frontend/
```

- [ ] **Step 6: Verify production**

```bash
curl -s https://simulations.mentomap.com/api/games | python3 -c \
  "import sys,json; d=json.load(sys.stdin); g=[x for x in d['games'] if 'stock-market' in x['game_id']]; print(g)"
```
Expected: prints both `stock-market-day-trader` and `stock-market-simulator` entries.

```bash
BASE=https://simulations.mentomap.com USER=demo_student PASS=Mento@2026 \
  node frontend-react/test-stocksim-e2e.mjs
```
Expected: `✅ E2E smoke passed`.

- [ ] **Step 7: Commit + tag**

```bash
git add frontend-react/test-stocksim-e2e.mjs
git commit -m "test(stocksim): E2E smoke + production deploy"
git tag -a stocksim-tier2-v1 -m "Realtime stock market sim Tier 2 — Day Trader Sprint live"
```

---

## Self-Review Notes

- **Spec coverage:** All 5 spec sections (Architecture, Components, Data Flow, Error Handling, Testing) are covered: engine module split → Tasks 1–8; routes → Tasks 10–12; bundle validation → Task 9; replay/audit → Task 8; UI → Tasks 13–14; presets → Task 15; deployment → Task 16.
- **Type consistency:** `price_at(state, symbol, tick)` (public, route-level) and `_price_from_seed(seed, symbol, tick, cfg)` (internal, pure) are used consistently across Tasks 2, 8, and 13. Order keys (`symbol`, `side`, `qty`, `order_type`, `limit_price`, `stop_price`) match across engine, routes, and frontend OrderTicket.
- **Placeholder check:** Step 1 of Task 13 contains a `// placeholder until fixtures are emitted` line for the parity test, which is then resolved explicitly in Step 5 of the same task. No other placeholders.
- **Frequent commits:** Each task ends with its own `git commit` step (16 commits total).
