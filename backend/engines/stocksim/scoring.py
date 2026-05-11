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
        risk_tolerance = _clamp(size_pct * 3.0)  # 5% -> 15, 15% -> 45, 30% -> 90
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

    # ---- delayed_gratification: holding ratio approximation ----
    n_buys = sum(1 for t in trade_log if t.get("side") == "buy")
    n_sells = sum(1 for t in trade_log if t.get("side") == "sell")
    if n_buys > 0:
        hold_ratio = max(0, n_buys - n_sells) / n_buys
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
