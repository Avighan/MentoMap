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
        elif not isinstance(cfg["tick_count"], int) or isinstance(cfg["tick_count"], bool) or cfg["tick_count"] < 1:
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

    # ---- pricing ----
    def price_at(self, state: dict, symbol: str, tick: int) -> dict:
        """Public price lookup. Reads seed from state; delegates to pure function."""
        from engines.stocksim.pricing import price_from_seed
        seed = state["seed"]
        cfg = next((s for s in self.config["stocks"] if s["symbol"] == symbol), None)
        if cfg is None:
            raise ValueError(f"unknown symbol: {symbol}")
        return price_from_seed(seed, symbol, tick, cfg)

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

    def advance_to_tick(self, state: dict, tick: int) -> dict:
        from engines.stocksim.orders import advance_to_tick
        return advance_to_tick(state, tick, self.config)

    def news_at(self, state: dict, tick: int) -> list:
        from engines.stocksim.events import news_at
        return news_at(state, tick, self.config)

    def event_at(self, state: dict, tick: int):
        from engines.stocksim.events import event_at
        return event_at(state, tick, self.config)

    # ---- scoring ----
    def compute_pnl(self, state, latest_quotes=None):
        from engines.stocksim.scoring import compute_pnl
        if latest_quotes is None:
            tick = state.get("current_tick", 0)
            latest_quotes = {}
            for s in self.config["stocks"]:
                if s["symbol"] in state.get("holdings", {}):
                    q = self.price_at(state, s["symbol"], tick)
                    latest_quotes[s["symbol"]] = q["mid"]
        return compute_pnl(state, latest_quotes)

    def score_dimensions(self, state):
        from engines.stocksim.scoring import score_dimensions
        return score_dimensions(state, self.config)

    def replay(self, seed, config, trade_log):
        from engines.stocksim.replay import replay
        return replay(seed, config, trade_log)
