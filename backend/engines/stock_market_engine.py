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
