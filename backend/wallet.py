"""Per-user coin wallet: balances, transaction history, and a global
lifetime-coins leaderboard.

Call sites (see app.py's WALLET routes and the per-choice/per-completion
coin-credit hooks) establish this as a points/currency ledger tied to
gameplay: coins are earned per-choice (`credit_round_coins`), on game
completion (`credit_game_completion`), and via daily login streaks
(`credit_daily_reward`), then spent (`spend_coins`) or displayed
(`get_wallet`, `get_transaction_history`, `get_global_leaderboard`). One
JSON file at `data/wallets.json`, keyed by user_id.
"""
import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(_THIS_DIR, "data")
    os.makedirs(base, exist_ok=True)
    return base


def _path() -> str:
    return os.path.join(_data_dir(), "wallets.json")


_LOCK = threading.Lock()


def _load() -> Dict[str, dict]:
    path = _path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: Dict[str, dict]) -> None:
    path = _path()
    tmp_path = path + ".tmp"
    with _LOCK:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)


def _ensure_wallet(data: Dict[str, dict], user_id: str) -> dict:
    if user_id not in data:
        data[user_id] = {
            "user_id": user_id,
            "balance": 0,
            "lifetime_coins": 0,
            "transactions": [],
        }
    return data[user_id]


def _credit(user_id: str, amount: int, reason: str, meta: Dict[str, Any] = None) -> dict:
    data = _load()
    w = _ensure_wallet(data, user_id)
    w["balance"] = w.get("balance", 0) + amount
    if amount > 0:
        w["lifetime_coins"] = w.get("lifetime_coins", 0) + amount
    txn = {
        "amount": amount,
        "reason": reason,
        "balance_after": w["balance"],
        "timestamp": datetime.now().isoformat(),
        **(meta or {}),
    }
    w.setdefault("transactions", []).append(txn)
    _save(data)
    return {"wallet": {k: v for k, v in w.items() if k != "transactions"}, "transaction": txn}


def get_wallet(user_id: str) -> dict:
    data = _load()
    w = data.get(user_id)
    if not w:
        return {"user_id": user_id, "balance": 0, "lifetime_coins": 0}
    return {"user_id": user_id, "balance": w.get("balance", 0), "lifetime_coins": w.get("lifetime_coins", 0)}


def get_transaction_history(user_id: str, limit: int = 50) -> List[dict]:
    data = _load()
    w = data.get(user_id)
    if not w:
        return []
    return list(reversed(w.get("transactions", [])))[:limit]


def spend_coins(user_id: str, amount: int, purpose: str = "") -> dict:
    if amount <= 0:
        return {"error": "Amount must be positive"}
    data = _load()
    w = _ensure_wallet(data, user_id)
    if w.get("balance", 0) < amount:
        return {"error": "Insufficient balance", "balance": w.get("balance", 0)}
    result = _credit(user_id, -amount, purpose or "spend", {"purpose": purpose})
    return {"success": True, **result}


def credit_round_coins(user_id: str, game_id: str, game_title: str, round_title: str,
                        coins: int, reason: str = "") -> dict:
    return _credit(user_id, coins, reason, {
        "game_id": game_id, "game_title": game_title, "round_title": round_title,
    })


def credit_game_completion(user_id: str, game_id: str, game_title: str, mento_rank: str,
                            achievement_count: int, total_achievements: int) -> dict:
    rank_bonus = {"A": 50, "B": 35, "C": 20, "D": 10, "F": 5}.get((mento_rank or "F")[:1].upper(), 5)
    achievement_bonus = achievement_count * 5
    total = rank_bonus + achievement_bonus
    return _credit(user_id, total, f"Completed {game_title}", {
        "game_id": game_id, "game_title": game_title, "mento_rank": mento_rank,
        "achievement_count": achievement_count, "total_achievements": total_achievements,
        "rank_bonus": rank_bonus, "achievement_bonus": achievement_bonus,
    })


def credit_daily_reward(user_id: str, total_coins: int, streak: int) -> dict:
    return _credit(user_id, total_coins, "Daily login reward", {"streak": streak})


def get_global_leaderboard(limit: int = 20) -> List[dict]:
    data = _load()
    entries = [
        {
            "user_id": uid,
            "display_name": uid,
            "lifetime_coins": w.get("lifetime_coins", 0),
            "balance": w.get("balance", 0),
        }
        for uid, w in data.items()
    ]
    entries.sort(key=lambda e: e["lifetime_coins"], reverse=True)
    return entries[:limit]
