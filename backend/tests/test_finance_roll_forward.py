"""Tests for finance_engine.roll_forward_period — period close + carry-forward."""

import copy
import pytest

from engines.finance_engine import roll_forward_period, get_finance_config


class _MockState:
    """Minimal state object with the attrs roll_forward_period reads/writes."""
    def __init__(self, **kw):
        self.money = kw.pop("money", 1_000_000)
        self.finance_periods = kw.pop("finance_periods", [])
        self.finance_history = kw.pop("finance_history", [])
        for k, v in kw.items():
            setattr(self, k, v)


_FINANCE_GAME = {
    "simulation_config": {
        "finance": {
            "cap_table": {
                "founders": [{"name": "Founder", "shares": 8_000_000}],
                "esop_pool_pct": 0.10,
                "rounds": [],
            }
        }
    }
}


def test_roll_forward_returns_dict_with_expected_keys():
    state = _MockState()
    out = roll_forward_period(state, _FINANCE_GAME, period_label="Q1 FY26")
    assert isinstance(out, dict)
    assert "period_label" in out
    assert "period_index" in out
    assert "cash_carry_forward" in out


def test_roll_forward_no_op_when_finance_disabled():
    state = _MockState()
    plain_game = {"game_type": "rounds"}
    out = roll_forward_period(state, plain_game)
    assert out is None


def test_roll_forward_appends_period_entry():
    state = _MockState(monthly_revenue=100_000, monthly_burn=50_000)
    before = len(state.finance_periods)
    roll_forward_period(
        state, _FINANCE_GAME, period_label="Q1",
        period_inputs={"revenue": 300_000, "cogs": 90_000, "opex": {"sales": 60_000, "rd": 40_000}},
    )
    assert len(state.finance_periods) == before + 1
    last = state.finance_periods[-1]
    assert last["label"] == "Q1"
    assert last["revenue"] == 300_000
    assert last["cogs"] == 90_000


def test_roll_forward_increments_period_index():
    state = _MockState()
    out1 = roll_forward_period(state, _FINANCE_GAME, period_label="Q1")
    out2 = roll_forward_period(state, _FINANCE_GAME, period_label="Q2")
    assert out2["period_index"] == out1["period_index"] + 1


def test_roll_forward_carries_cash_to_next_period():
    """Cash from end of period N is the opening cash for period N+1."""
    state = _MockState(money=500_000)
    out = roll_forward_period(state, _FINANCE_GAME, period_label="Q1")
    assert out["cash_carry_forward"] == 500_000


def test_roll_forward_does_not_mutate_game_dict():
    state = _MockState()
    snapshot = copy.deepcopy(_FINANCE_GAME)
    roll_forward_period(state, _FINANCE_GAME, period_label="Q1")
    assert _FINANCE_GAME == snapshot


def test_roll_forward_appends_history_snapshot():
    """A roll-forward also takes a finance_history snapshot for replay."""
    state = _MockState()
    roll_forward_period(
        state, _FINANCE_GAME, period_label="Q1",
        period_inputs={"revenue": 100_000, "cogs": 30_000, "opex": {"ops": 20_000}},
    )
    assert len(state.finance_history) >= 1
    snap = state.finance_history[-1]
    assert snap.get("label") == "Q1"
    assert "pnl" in snap
    assert snap["pnl"] is not None


def test_roll_forward_default_label_uses_period_index():
    state = _MockState()
    out = roll_forward_period(state, _FINANCE_GAME)
    assert "Period" in out["period_label"]
