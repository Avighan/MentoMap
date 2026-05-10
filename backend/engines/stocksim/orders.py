"""Order validation, matching, and portfolio update.

Order types: market, limit (more added in Task 5: stop_loss, sip).
Matching against bid-ask spread. Charges applied per Task 3.
T+1 settlement queue tracked here; sells of unsettled qty are rejected.
"""
from __future__ import annotations
import uuid

from engines.stocksim.pricing import price_from_seed
from engines.stocksim.charges import compute_charges, ChargesError


def _fill_or_reject_market(state: dict, order: dict, quote: dict, charges_cfg: dict) -> dict:
    side = order["side"]
    qty = int(order["qty"])
    symbol = order["symbol"]
    price = quote["ask"] if side == "buy" else quote["bid"]

    if state.get("halted_symbols", {}).get(symbol):
        return {"status": "rejected", "error_code": "MARKET_HALTED",
                "message": f"{symbol} halted (circuit breaker)",
                "recoverable": True}

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
        state["settlement_queue"].append({
            "symbol": symbol, "qty": qty, "buy_tick": order["tick"]
        })
    else:
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
        cost_basis = h["avg_price"] * qty
        trade_pnl = qty * price - cost_basis - charges["total"]
        state["realized_pnl"] += trade_pnl
        h["qty"] -= qty
        h["settled_qty"] -= qty
        if h["qty"] == 0:
            del state["holdings"][symbol]

    fill = {
        "order_id": str(uuid.uuid4()),
        "tick": order["tick"], "symbol": symbol, "side": side,
        "qty": qty, "price": price, "charges": charges,
        "order_type_used": order.get("order_type", "market"),
    }
    if side == "sell":
        fill["realized_pnl"] = trade_pnl
    state["trade_log"].append(fill)
    return {"status": "filled", "fill": fill, "charges": charges,
            "new_cash": state["cash"], "new_holdings": dict(state["holdings"])}


def place_order(state: dict, order: dict, config: dict) -> dict:
    """Validate and route an order. Mutates state."""
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
        if (side == "buy" and limit_price >= quote["ask"]) or \
           (side == "sell" and limit_price <= quote["bid"]):
            fill_quote = dict(quote)
            if side == "buy":
                fill_quote["ask"] = min(quote["ask"], limit_price)
            else:
                fill_quote["bid"] = max(quote["bid"], limit_price)
            return _fill_or_reject_market(state, order, fill_quote, charges_cfg)
        pending = {
            "order_id": str(uuid.uuid4()),
            "type": "limit",
            "side": side, "symbol": symbol, "qty": qty,
            "limit_price": limit_price, "placed_tick": order["tick"],
        }
        state["pending_orders"].append(pending)
        return {"status": "queued", "order_id": pending["order_id"],
                "message": "Limit order queued"}

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

    return {"status": "rejected", "error_code": "INVALID_ORDER",
            "message": f"order_type {order_type} not supported yet",
            "recoverable": True}


def _check_circuit_breakers(state: dict, config: dict, tick: int) -> None:
    """Update state['halted_symbols'] based on cumulative move from start."""
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
    """Lazy sweep: fire pending orders, T+1 settle, then update circuit breakers.

    Order rationale (deviates from initial spec): halted_symbols is a flat
    per-session flag, not per-tick. If breakers were checked first, a halt set
    at the destination tick would retroactively block fills that historically
    triggered at earlier (un-halted) ticks during the sweep. Filling pending
    orders first preserves their tick-of-trigger semantics; the halt then takes
    effect for any subsequent direct place_order calls in this session.
    """
    if tick <= state.get("current_tick", 0):
        return {"current_tick": state["current_tick"]}
    _sweep_pending_orders(state, config, tick)
    _settle_t1(state, tick)
    _check_circuit_breakers(state, config, tick)
    state["current_tick"] = tick
    return {"current_tick": tick,
            "halted_symbols": list(state.get("halted_symbols", {}).keys())}
