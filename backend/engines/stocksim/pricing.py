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
