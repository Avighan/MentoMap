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
