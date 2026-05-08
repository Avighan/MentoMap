"""Tier-2 charges: brokerage + STT + exchange fees + GST.

Sanity cap: total charges <= 5% of trade value. If config breaches this,
raise ChargesError so misconfigured games fail loudly at session start
rather than silently stealing user capital.
"""
from __future__ import annotations


class ChargesError(Exception):
    """Raised when charge config produces > 5% trade-value charges."""


def compute_charges(side: str, qty: int, price: float, cfg: dict) -> dict:
    """Return charges breakdown {brokerage, stt, exchange, gst, total} in Rs.

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
