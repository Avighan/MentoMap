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
    # Mark-to-market at the game's final tick (tick_count), which is the
    # authoritative end-of-session moment. The last fill's tick only records
    # when the order was placed — the session runs to tick_count regardless.
    final_tick = int(config.get("tick_count", last_tick))
    state["current_tick"] = final_tick
    latest_quotes = {}
    for s in config["stocks"]:
        if s["symbol"] in state["holdings"]:
            q = price_from_seed(state["seed"], s["symbol"], final_tick, s)
            latest_quotes[s["symbol"]] = q["mid"]
    pnl = compute_pnl(state, latest_quotes)
    dims = score_dimensions(state, config)
    return {"pnl": pnl, "dimensions": dims, "ending_state": state}
