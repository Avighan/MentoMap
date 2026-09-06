"""
Trump Card engine — "Top Trumps" style `game_type: "trump_card"` games
(e.g. games/soft-skills-trump.json): each card carries an `attributes` dict of
named stats; players compare one attribute at a time, and whoever's top card
scores higher takes both cards (a tie banks both into a `pot` awarded to the
next round's winner). The player who wins a round leads the attribute pick
for the next one, matching the physical card game's turn order.
"""

import random
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def _attributes_config(game: Dict[str, Any]) -> List[Dict[str, Any]]:
    return game.get("attributes") or []


def init_game(game: Dict[str, Any]) -> Dict[str, Any]:
    deck = list(game.get("deck") or [])
    random.shuffle(deck)
    half = (len(deck) + 1) // 2

    return {
        "game_id": game.get("game_id"),
        "rounds_played": 0,
        "max_rounds": int(game.get("max_rounds", 20)),
        "win_condition": game.get("win_condition", "most_cards"),
        "current_player": random.choice(["player", "ai"]),
        "game_over": False,
        "winner": None,
        "player_hand": deck[:half],
        "ai_hand": deck[half:],
        "pot": [],
        "attribute_pick_counts": {},
        "skill_tag_counts": {},
        "log": [],
    }


def _valid_attribute_keys(game: Dict[str, Any]) -> List[str]:
    return [a.get("key") for a in _attributes_config(game) if a.get("key")]


def pick_attribute(state: Dict[str, Any], game: Dict[str, Any], attribute: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Compare the top card of each hand on `attribute`. Winner takes both
    cards (plus any banked pot); a tie banks both cards into the pot."""
    if state.get("game_over"):
        raise ValueError("Game is already over")
    if attribute not in _valid_attribute_keys(game):
        raise ValueError(f"Unknown attribute: {attribute}")
    if not state["player_hand"] or not state["ai_hand"]:
        raise ValueError("A player has no cards left")

    player_card = state["player_hand"].pop(0)
    ai_card = state["ai_hand"].pop(0)
    player_val = (player_card.get("attributes") or {}).get(attribute, 0)
    ai_val = (ai_card.get("attributes") or {}).get(attribute, 0)

    pot = state.setdefault("pot", [])
    at_stake = pot + [player_card, ai_card]

    if player_val > ai_val:
        result = "player_win"
        state["player_hand"].extend(at_stake)
        state["pot"] = []
        state["current_player"] = "player"
    elif ai_val > player_val:
        result = "ai_win"
        state["ai_hand"].extend(at_stake)
        state["pot"] = []
        state["current_player"] = "ai"
    else:
        result = "tie"
        state["pot"] = at_stake
        # current_player unchanged — same side picks again to break the tie.

    counts = state.setdefault("attribute_pick_counts", {})
    counts[attribute] = counts.get(attribute, 0) + 1

    attr_cfg = next((a for a in _attributes_config(game) if a.get("key") == attribute), {})
    skill_tag = attr_cfg.get("skill_tag")
    if skill_tag and result == "player_win":
        tags = state.setdefault("skill_tag_counts", {})
        tags[skill_tag] = tags.get(skill_tag, 0) + 1

    state["rounds_played"] += 1

    round_result = {
        "attribute": attribute,
        "player_card": player_card,
        "ai_card": ai_card,
        "player_value": player_val,
        "ai_value": ai_val,
        "result": result,
        "cards_at_stake": len(at_stake),
        "image_prompt": (player_card if result != "ai_win" else ai_card).get("image_prompt", ""),
    }
    state["log"].append({"round": state["rounds_played"], **{k: v for k, v in round_result.items() if k not in ("player_card", "ai_card")}})

    _check_game_over(state)
    return state, round_result


def _check_game_over(state: Dict[str, Any]) -> None:
    if state.get("game_over"):
        return
    player_empty = not state["player_hand"]
    ai_empty = not state["ai_hand"]
    rounds_exhausted = state["rounds_played"] >= state["max_rounds"]

    if not (player_empty or ai_empty or rounds_exhausted):
        return

    state["game_over"] = True
    if player_empty and not ai_empty:
        state["winner"] = "ai"
    elif ai_empty and not player_empty:
        state["winner"] = "player"
    else:
        p, a = len(state["player_hand"]), len(state["ai_hand"])
        state["winner"] = "player" if p > a else ("ai" if a > p else "tie")


def ai_pick_attribute(state: Dict[str, Any], game: Dict[str, Any]) -> Optional[str]:
    """AI leads with whichever attribute its own top card is strongest in."""
    if not state.get("ai_hand"):
        return None
    card = state["ai_hand"][0]
    attrs = card.get("attributes") or {}
    valid_keys = _valid_attribute_keys(game)
    candidates = {k: v for k, v in attrs.items() if k in valid_keys} or attrs
    if not candidates:
        return random.choice(valid_keys) if valid_keys else None

    strategy = (game.get("ai_opponent") or {}).get("strategy", "balanced")
    if strategy == "random":
        return random.choice(list(candidates.keys()))
    return max(candidates, key=candidates.get)


def compute_trait_profile(state: Dict[str, Any], game: Dict[str, Any]) -> Dict[str, Any]:
    """Match the player's collected hand against `game.trait_profiles` by
    whichever attribute their cards average highest on."""
    profiles = game.get("trait_profiles") or []
    valid_keys = _valid_attribute_keys(game)
    hand = state.get("player_hand") or []

    averages: Dict[str, float] = {}
    for key in valid_keys:
        values = [(c.get("attributes") or {}).get(key) for c in hand]
        values = [v for v in values if isinstance(v, (int, float))]
        if values:
            averages[key] = sum(values) / len(values)

    if not averages:
        return {"dominant": None, "label": "Undetermined", "averages": {}}

    dominant = max(averages, key=averages.get)
    profile = next((p for p in profiles if p.get("dominant") == dominant), None)
    result = dict(profile) if profile else {"dominant": dominant, "label": dominant}
    result["averages"] = {k: round(v, 1) for k, v in averages.items()}
    result["cards_collected"] = len(hand)
    return result


def compute_skill_dimensions(state: Dict[str, Any], game: Dict[str, Any]) -> Dict[str, int]:
    """0-100 per `dimension_scoring_weights` dim, blending which skill_tags the
    player's won cards carry with which attributes they leaned on picking."""
    weights = game.get("dimension_scoring_weights") or {}
    dims = list(weights.keys())
    if not dims:
        dims = sorted({a.get("skill_tag") for a in _attributes_config(game) if a.get("skill_tag")})

    hand_tags = Counter(c.get("skill_tag") for c in state.get("player_hand", []) if c.get("skill_tag"))
    win_tags = Counter(state.get("skill_tag_counts") or {})
    total_hand = sum(hand_tags.values()) or 1
    total_wins = sum(win_tags.values()) or 1

    scores = {}
    for dim in dims:
        score = 50
        score += int(25 * (hand_tags.get(dim, 0) / total_hand))
        score += int(25 * (win_tags.get(dim, 0) / total_wins))
        scores[dim] = max(0, min(100, score))
    return scores
