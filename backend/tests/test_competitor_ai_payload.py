"""Tests for competitor_ai_engine.build_competitor_payload + get_competitor_config."""

import pytest

from engines.competitor_ai_engine import (
    get_competitor_config,
    build_competitor_payload,
)


class _State:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


_GAME_WITH_COMPETITORS = {
    "simulation_config": {
        "competitor_ai": {
            "firms": [
                {"id": "atlas", "name": "Atlas Innovate", "persona": "aggressive_rd",
                 "starting_market_share": 0.34, "starting_price": 110,
                 "starting_marketing": 1_500_000, "starting_rd_alloc": 0.30},
                {"id": "beacon", "name": "Beacon Trust", "persona": "defensive_cost_leader",
                 "starting_market_share": 0.33, "starting_price": 90,
                 "starting_marketing": 2_000_000, "starting_rd_alloc": 0.10},
            ],
            "seed": 42,
        }
    }
}


def test_get_competitor_config_returns_config_when_present():
    cfg = get_competitor_config(_GAME_WITH_COMPETITORS)
    assert cfg is not None
    assert "firms" in cfg


def test_get_competitor_config_returns_none_when_no_simulation_config():
    assert get_competitor_config({"game_type": "rounds"}) is None


def test_get_competitor_config_returns_none_when_no_firms():
    game = {"simulation_config": {"competitor_ai": {}}}
    assert get_competitor_config(game) is None


def test_payload_returns_none_when_no_config():
    state = _State()
    assert build_competitor_payload(state, {"game_type": "rounds"}) is None


def test_payload_synthesizes_initial_board_from_firms():
    """Round 0: no runtime tick yet, payload reads from declared firms."""
    state = _State()
    payload = build_competitor_payload(state, _GAME_WITH_COMPETITORS)
    assert payload is not None
    assert len(payload["competitors"]) == 2
    ids = {c["id"] for c in payload["competitors"]}
    assert ids == {"atlas", "beacon"}
    assert payload["moves"] == []  # no tick yet


def test_payload_uses_runtime_when_tick_has_run():
    """When _competitor_runtime is populated, payload uses it (not the seeds)."""
    runtime = {
        "competitors": [
            {"id": "atlas", "name": "Atlas", "persona": "aggressive_rd",
             "market_share": 0.40, "price": 115.0, "marketing_spend": 1_600_000,
             "r_and_d_alloc": 0.35},
        ],
        "player": {"market_share": 0.30, "price": 100.0,
                   "marketing_spend": 1_200_000, "r_and_d_alloc": 0.25},
        "competitor_moves": [{"id": "atlas", "rationale": "raised R&D"}],
    }
    state = _State(_competitor_runtime=runtime)
    payload = build_competitor_payload(state, _GAME_WITH_COMPETITORS)
    assert payload["competitors"][0]["market_share"] == 0.40
    assert len(payload["moves"]) == 1
    assert payload["player"]["market_share"] == 0.30


def test_payload_lists_personas_in_play():
    state = _State()
    payload = build_competitor_payload(state, _GAME_WITH_COMPETITORS)
    assert "aggressive_rd" in payload["personas_in_play"]
    assert "defensive_cost_leader" in payload["personas_in_play"]
