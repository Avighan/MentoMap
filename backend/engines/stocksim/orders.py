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

    return {"status": "rejected", "error_code": "INVALID_ORDER",
            "message": f"order_type {order_type} not supported yet",
            "recoverable": True}
