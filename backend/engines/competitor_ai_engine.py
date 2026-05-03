"""
CompetitorAIEngine — reactive 3-firm competitor AI for HBR-parity simulations.

Pure-function engine. `tick(state, player_move, seed=None)` reads the player's
decision-panel move plus the current state of three seeded firms (each with a
strategy persona) and returns a slice that:
  - emits one move per competitor (with a short rationale string),
  - mutates each firm's price / marketing_spend / r_and_d_alloc per its persona,
  - re-balances `market_share` across player + 3 firms so they sum to 1.0.

Personas (HBR-canon):
  - aggressive_rd          — Atlas Innovate. Match-or-raise R&D when the player
                             escalates; willing to bleed margin to defend R&D lead.
  - defensive_cost_leader  — Beacon Trust. Defends share by undercutting price
                             when undercut; modest marketing escalation only.
  - fast_follower          — Cygnus Forge. Mimics the player's strongest signal
                             (whichever lever the player moved most aggressively).

Design intent: this is the CapSim-borrow ("reactive multi-firm competitor model")
scaled for the 35–45 minute HBR runtime envelope, not the full Capstone Courier
firm AI. Output is deterministic given a seed for snapshot-test stability.

Wiring point: `core/rounds.py` calls `tick()` after the player's
decision_panel.controls have been applied to state. Not registered in
engines/__init__.py until HBR Phase B (frontend tabs).
"""

from __future__ import annotations

import copy
import random
from typing import Any, Dict, List, Optional


# ---- Persona definitions ----------------------------------------------------

DEFAULT_PERSONAS: Dict[str, Dict[str, float]] = {
    "aggressive_rd": {
        # Reaction weights: how strongly each lever moves in response to the
        # corresponding player lever. Positive = match/raise, negative = undercut.
        "rd_match_strength": 0.6,        # match player R&D escalation
        "price_premium_drift": 0.05,     # drift price up over time (premium tilt)
        "marketing_match": 0.2,
        "share_attractiveness": 1.1,     # higher = stickier share holder
    },
    "defensive_cost_leader": {
        "rd_match_strength": 0.1,
        "price_undercut_strength": 0.5,  # drop price aggressively when undercut
        "marketing_match": 0.3,
        "share_attractiveness": 1.0,
    },
    "fast_follower": {
        "rd_match_strength": 0.4,
        "marketing_mimic_strength": 0.7,  # mimic player marketing
        "price_mimic_strength": 0.3,
        "share_attractiveness": 0.9,
    },
    # Fallback persona — neutral drift only
    "neutral": {
        "rd_match_strength": 0.0,
        "marketing_match": 0.0,
        "share_attractiveness": 1.0,
    },
}


# ---- Engine -----------------------------------------------------------------

class CompetitorAIEngine:
    """Pure-function competitor AI. Construct once, call `tick()` per round."""

    def __init__(self, personas: Optional[Dict[str, Dict[str, float]]] = None):
        self._personas = personas or DEFAULT_PERSONAS

    def tick(
        self,
        state: Dict[str, Any],
        player_move: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return updated `competitors`, `player`, and `competitor_moves` slice.

        Does not mutate `state`. The returned dict is a slice the caller is
        expected to merge into the broader sim state — it intentionally does
        not echo back unrelated keys (market.total_demand, etc.).
        """
        s = copy.deepcopy(state)
        rng = random.Random(seed if seed is not None else 0)
        pm = dict(player_move or {})

        competitors_in: List[Dict[str, Any]] = list(s.get("competitors", []))
        moves: List[Dict[str, Any]] = []
        competitors_out: List[Dict[str, Any]] = []

        for firm in competitors_in:
            persona_key = firm.get("persona", "neutral")
            persona = self._personas.get(persona_key, self._personas["neutral"])
            new_firm = dict(firm)
            move = self._react(new_firm, persona, pm, rng)
            move["id"] = firm.get("id", "?")
            moves.append(move)
            competitors_out.append(new_firm)

        # Recompute market shares: persona attractiveness × marketing × inverse-price
        player = dict(s.get("player", {}))
        shares = self._compute_shares(competitors_out, player)

        for firm, share in zip(competitors_out, shares["competitors"]):
            firm["market_share"] = share
        player["market_share"] = shares["player"]

        return {
            "competitors": competitors_out,
            "player": player,
            "competitor_moves": moves,
        }

    # ---- internals ----------------------------------------------------------

    def _react(
        self,
        firm: Dict[str, Any],
        persona: Dict[str, float],
        player_move: Dict[str, Any],
        rng: random.Random,
    ) -> Dict[str, Any]:
        """Mutate `firm` in place per persona; return a {action, rationale} log."""
        persona_key = firm.get("persona", "neutral")
        actions: List[str] = []

        # --- R&D reaction ---
        player_rd = float(player_move.get("r_and_d_alloc", firm.get("r_and_d_alloc", 0.2)))
        firm_rd = float(firm.get("r_and_d_alloc", 0.2))
        rd_match = persona.get("rd_match_strength", 0.0)
        rd_gap = max(0.0, player_rd - firm_rd)
        if rd_gap > 0 and rd_match > 0:
            new_rd = min(0.6, firm_rd + rd_match * rd_gap + rng.uniform(0, 0.02))
            firm["r_and_d_alloc"] = round(new_rd, 4)
            actions.append(f"raised R&D to {new_rd:.0%}")

        # --- Price reaction ---
        player_price = player_move.get("price")
        firm_price = float(firm.get("price", 100.0))
        if player_price is not None:
            player_price = float(player_price)
            if persona_key == "defensive_cost_leader" and player_price < firm_price:
                # Undercut the undercutter
                strength = persona.get("price_undercut_strength", 0.5)
                new_price = max(60.0, firm_price - strength * (firm_price - player_price) - rng.uniform(0, 1.0))
                firm["price"] = round(new_price, 2)
                actions.append(f"dropped price to ${new_price:.2f} to defend share")
            elif persona_key == "fast_follower":
                strength = persona.get("price_mimic_strength", 0.3)
                new_price = firm_price + strength * (player_price - firm_price)
                firm["price"] = round(new_price, 2)
                actions.append(f"mirrored price toward ${new_price:.2f}")
            elif persona_key == "aggressive_rd":
                drift = persona.get("price_premium_drift", 0.0)
                new_price = firm_price * (1.0 + drift)
                firm["price"] = round(new_price, 2)
                actions.append(f"drifted price up to ${new_price:.2f} (premium tilt)")

        # --- Marketing reaction ---
        player_mkt = player_move.get("marketing_spend")
        firm_mkt = float(firm.get("marketing_spend", 1_000_000))
        if player_mkt is not None:
            player_mkt = float(player_mkt)
            if persona_key == "fast_follower":
                strength = persona.get("marketing_mimic_strength", 0.7)
                new_mkt = firm_mkt + strength * (player_mkt - firm_mkt)
                firm["marketing_spend"] = round(max(0.0, new_mkt), 2)
                actions.append(f"matched marketing to ${new_mkt:,.0f}")
            else:
                match = persona.get("marketing_match", 0.0)
                if match > 0 and player_mkt > firm_mkt:
                    new_mkt = firm_mkt + match * (player_mkt - firm_mkt)
                    firm["marketing_spend"] = round(new_mkt, 2)
                    actions.append(f"raised marketing to ${new_mkt:,.0f}")

        rationale = "; ".join(actions) if actions else "held position; no material player escalation"
        return {"action_summary": rationale, "rationale": rationale}

    def _compute_shares(
        self,
        competitors: List[Dict[str, Any]],
        player: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Re-balance share via attractiveness scores. Sums to 1.0."""
        def score(actor: Dict[str, Any], persona_key: str = "neutral") -> float:
            persona = self._personas.get(persona_key, self._personas["neutral"])
            attractiveness = persona.get("share_attractiveness", 1.0)
            price = max(1.0, float(actor.get("price", 100.0)))
            mkt = float(actor.get("marketing_spend", 0))
            # Mild non-linearity: lower price + higher marketing → more share
            raw = attractiveness * (1_000_000 + mkt) / price
            return max(1e-6, raw)

        comp_scores = [score(c, c.get("persona", "neutral")) for c in competitors]
        player_score = score(player, player.get("persona", "neutral"))
        total = sum(comp_scores) + player_score
        if total <= 0:
            n = len(competitors) + 1
            equal = 1.0 / n if n else 0.0
            return {
                "competitors": [equal for _ in competitors],
                "player": equal,
            }
        return {
            "competitors": [s / total for s in comp_scores],
            "player": player_score / total,
        }
