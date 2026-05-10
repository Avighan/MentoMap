"""Tests for engines/competitor_ai_engine.py — 3-firm reactive AI for HBR sims."""

import copy
import pytest

from engines.competitor_ai_engine import (
    CompetitorAIEngine,
    DEFAULT_PERSONAS,
)


@pytest.fixture
def base_state():
    """Minimal sim state with three seeded competitors and a market."""
    return {
        "market": {
            "total_demand": 1_000_000,
            "price_index": 100.0,
        },
        "competitors": [
            {
                "id": "atlas",
                "name": "Atlas Innovate",
                "persona": "aggressive_rd",
                "market_share": 0.34,
                "price": 110.0,
                "marketing_spend": 1_500_000,
                "r_and_d_alloc": 0.30,
                "health": 1.0,
            },
            {
                "id": "beacon",
                "name": "Beacon Trust",
                "persona": "defensive_cost_leader",
                "market_share": 0.33,
                "price": 90.0,
                "marketing_spend": 2_000_000,
                "r_and_d_alloc": 0.10,
                "health": 1.0,
            },
            {
                "id": "cygnus",
                "name": "Cygnus Forge",
                "persona": "fast_follower",
                "market_share": 0.33,
                "price": 100.0,
                "marketing_spend": 1_000_000,
                "r_and_d_alloc": 0.20,
                "health": 1.0,
            },
        ],
        "player": {
            "market_share": 0.0,
            "price": 100.0,
            "marketing_spend": 1_000_000,
            "r_and_d_alloc": 0.20,
        },
    }


def test_tick_returns_three_competitor_moves(base_state):
    eng = CompetitorAIEngine()
    out = eng.tick(base_state, player_move={"price": 100.0}, seed=42)
    assert "competitor_moves" in out
    assert len(out["competitor_moves"]) == 3
    ids = {m["id"] for m in out["competitor_moves"]}
    assert ids == {"atlas", "beacon", "cygnus"}


def test_market_shares_sum_to_one_after_tick(base_state):
    eng = CompetitorAIEngine()
    out = eng.tick(base_state, player_move={"price": 95.0}, seed=42)
    total = sum(c["market_share"] for c in out["competitors"]) + out["player"]["market_share"]
    assert abs(total - 1.0) < 1e-6, f"shares must sum to 1.0, got {total}"


def test_atlas_raises_rd_when_player_pumps_rd(base_state):
    eng = CompetitorAIEngine()
    out = eng.tick(
        base_state,
        player_move={"r_and_d_alloc": 0.40, "price": 100.0},
        seed=42,
    )
    atlas_after = next(c for c in out["competitors"] if c["id"] == "atlas")
    assert atlas_after["r_and_d_alloc"] > 0.30, (
        "Atlas (aggressive_rd) should match-or-raise R&D when player escalates"
    )


def test_beacon_drops_price_when_player_undercuts(base_state):
    eng = CompetitorAIEngine()
    out = eng.tick(
        base_state,
        player_move={"price": 80.0},
        seed=42,
    )
    beacon_after = next(c for c in out["competitors"] if c["id"] == "beacon")
    assert beacon_after["price"] < 90.0, (
        "Beacon (defensive_cost_leader) should defend on price when undercut"
    )


def test_cygnus_mimics_player_marketing_pump(base_state):
    eng = CompetitorAIEngine()
    out = eng.tick(
        base_state,
        player_move={"marketing_spend": 4_000_000, "price": 100.0},
        seed=42,
    )
    cygnus_after = next(c for c in out["competitors"] if c["id"] == "cygnus")
    assert cygnus_after["marketing_spend"] > 1_000_000, (
        "Cygnus (fast_follower) should mimic when player pumps marketing"
    )


def test_tick_is_deterministic_given_seed(base_state):
    eng = CompetitorAIEngine()
    out_a = eng.tick(base_state, player_move={"price": 95.0}, seed=7)
    out_b = eng.tick(base_state, player_move={"price": 95.0}, seed=7)
    assert out_a == out_b


def test_tick_does_not_mutate_input_state(base_state):
    eng = CompetitorAIEngine()
    snapshot = copy.deepcopy(base_state)
    eng.tick(base_state, player_move={"price": 95.0}, seed=42)
    assert base_state == snapshot, "tick must not mutate input state"


def test_unknown_persona_falls_back_to_neutral(base_state):
    base_state["competitors"][0]["persona"] = "made_up_persona"
    eng = CompetitorAIEngine()
    # Should not crash, should produce a move for that competitor
    out = eng.tick(base_state, player_move={"price": 100.0}, seed=42)
    atlas_move = next(m for m in out["competitor_moves"] if m["id"] == "atlas")
    assert "rationale" in atlas_move


def test_empty_player_move_still_produces_moves(base_state):
    """Tick must produce competitor moves even when player skips a round."""
    eng = CompetitorAIEngine()
    out = eng.tick(base_state, player_move={}, seed=42)
    assert len(out["competitor_moves"]) == 3


def test_default_personas_are_exposed(base_state):
    assert "aggressive_rd" in DEFAULT_PERSONAS
    assert "defensive_cost_leader" in DEFAULT_PERSONAS
    assert "fast_follower" in DEFAULT_PERSONAS
