"""Deterministic price evolution from seed.

`price_from_seed(seed, symbol, tick, stock_cfg)` is purely functional:
same inputs → identical output forever. This is the determinism backbone —
both server and client compute prices via this function (JS port for client).

Math: log-return random walk per tick, drawn from Box-Muller normal seeded by
hash(seed, symbol, tick). Volatility scales the std-dev. Bid-ask spread widens
with volatility. mid is clamped to [0.01, 10× starting]; bid/ask are derived from mid via the
spread formula and may extend slightly outside that range (consistent with
real-market behaviour where the LTP is bounded by circuit breakers but
order-book quotes are not).

NOTE on JS port (Task 13, frontend-react/src/utils/stocksimPricing.js):
the client uses mulberry32 + FNV-1a (NOT SHA-256) for performance. The two
implementations therefore produce different numeric sequences. This is OK:
the server is authoritative for all order fills, P&L, and end-of-game scoring.
The client uses its local sequence only to render the price chart between
state polls. Tests in the JS port assert match within 0.05 tolerance to keep
the visual gap imperceptible at the chart scale.
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
    # NOTE: no per-tick clamp here. The full sum is clamped to ±4 in
    # `price_from_seed` before exp(). For 22-tick sessions this is fine; if
    # session length grows beyond ~50 ticks at extreme vol, consider per-tick
    # clamping. The JS port (frontend-react/src/utils/stocksimPricing.js) must
    # mirror this behaviour exactly to preserve client-server price agreement.
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
    # Min spread floor: ensure bid < mid < ask survives 2-decimal rounding even
    # at low prices (e.g. penny stocks). 1 paisa per side = 2 paise total.
    half_spread = max(half_spread, 0.01)
    bid = max(0.01, mid - half_spread)
    ask = mid + half_spread

    # Volume — deterministic, depends on volatility (high-vol = more action).
    # 10000 = base shares/tick (loose proxy for mid-cap NSE stock at ~1m daily
    # divided over ~20 ticks). vol*5 boost so a 5% vol stock trades 25% more.
    # 0.3 noise coefficient gives ±30% per-tick variance, enough for
    # student-visible market-feel without dominating the signal.
    vol_z = _seeded_normal(seed, symbol, tick, "vol")
    base_vol = 10000 * (1.0 + vol * 5.0)
    volume = max(0, int(base_vol * (1.0 + 0.3 * vol_z)))

    return {
        "mid": round(mid, 2),
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "volume": volume,
    }
