"""Real unit tests for backend/wallet.py, restored on this branch."""
import pytest


@pytest.fixture
def wallet_mod(monkeypatch, tmp_path):
    # wallet.py recomputes its data path per call via _data_dir(), so
    # monkeypatching MENTO_DATA_DIR is enough — no reload() (see
    # test_auth_module.py's fixture for why reload() is the wrong tool here).
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    import wallet
    yield wallet


def test_new_user_has_zero_balance(wallet_mod):
    w = wallet_mod.get_wallet("newuser")
    assert w["balance"] == 0
    assert w["lifetime_coins"] == 0


def test_credit_game_completion_awards_coins(wallet_mod):
    result = wallet_mod.credit_game_completion(
        "u1", "dealcraft", "Dealcraft", mento_rank="A",
        achievement_count=2, total_achievements=3,
    )
    assert result["transaction"]["amount"] > 0
    w = wallet_mod.get_wallet("u1")
    assert w["balance"] == result["transaction"]["amount"]
    assert w["lifetime_coins"] == w["balance"]


def test_higher_rank_earns_more_than_lower_rank(wallet_mod):
    a_result = wallet_mod.credit_game_completion("u_a", "g", "G", "A", 0, 0)
    f_result = wallet_mod.credit_game_completion("u_f", "g", "G", "F", 0, 0)
    assert a_result["transaction"]["amount"] > f_result["transaction"]["amount"]


def test_spend_coins_deducts_balance(wallet_mod):
    wallet_mod.credit_daily_reward("u2", 100, streak=1)
    result = wallet_mod.spend_coins("u2", 40, "cosmetic_hat")
    assert result["success"] is True
    assert wallet_mod.get_wallet("u2")["balance"] == 60


def test_spend_coins_rejects_insufficient_balance(wallet_mod):
    wallet_mod.credit_daily_reward("u3", 10, streak=1)
    result = wallet_mod.spend_coins("u3", 999, "too_expensive")
    assert "error" in result
    assert wallet_mod.get_wallet("u3")["balance"] == 10  # unchanged


def test_spend_coins_does_not_reduce_lifetime_coins(wallet_mod):
    wallet_mod.credit_daily_reward("u4", 100, streak=1)
    wallet_mod.spend_coins("u4", 30, "purchase")
    w = wallet_mod.get_wallet("u4")
    assert w["balance"] == 70
    assert w["lifetime_coins"] == 100  # lifetime total unaffected by spending


def test_transaction_history_orders_most_recent_first(wallet_mod):
    wallet_mod.credit_daily_reward("u5", 10, streak=1)
    wallet_mod.credit_daily_reward("u5", 20, streak=2)
    history = wallet_mod.get_transaction_history("u5", limit=10)
    assert len(history) == 2
    assert history[0]["amount"] == 20  # most recent first


def test_global_leaderboard_ranks_by_lifetime_coins(wallet_mod):
    wallet_mod.credit_daily_reward("low", 10, streak=1)
    wallet_mod.credit_daily_reward("high", 500, streak=1)
    board = wallet_mod.get_global_leaderboard(limit=10)
    assert board[0]["user_id"] == "high"
    assert board[0]["lifetime_coins"] == 500
