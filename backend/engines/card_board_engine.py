"""
Card + Board hybrid engine — `game_type: "card_board"` games (e.g.
games/negotiation-card-board.json).

Two mechanics share one piece of state:
  - Card play: each card in a hand carries a `resource_bonus` and a
    `tile_type_bonus` multiplier table. Playing a card on a board tile
    "claims" that tile for whoever's power (bonus x tile-type multiplier) is
    higher, applying the (scaled) resource bonus to that player.
  - Monopoly mode (`game["monopoly_mode"]`): the player also rolls dice and
    moves a token around the board, triggering `go`/`rest`/`event` tiles
    automatically; `claim`/`challenge` tiles still require a card play.

State is a plain JSON-serializable dict — app.py stores it verbatim on the
run and returns it verbatim to the client, so every field here is part of
the frontend contract.
"""

import random
from typing import Any, Dict, List, Optional, Tuple


def _resources_config(game: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    cfg = game.get("resources")
    if isinstance(cfg, dict) and cfg:
        return cfg
    # Fallback: build a minimal config from initial_state's flat number map.
    out = {}
    for k, v in (game.get("initial_state") or {}).items():
        if isinstance(v, (int, float)):
            out[k] = {"label": k.replace("_", " ").title(), "icon": "", "start": v, "max": max(20, v * 2)}
    return out


def _starting_resources(resources_cfg: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    return {k: v.get("start", 0) for k, v in resources_cfg.items()}


def init_game(game: Dict[str, Any], hand_size_override: Optional[int] = None) -> Dict[str, Any]:
    """Deal hands, seed the board, and return a fresh card_board state dict."""
    resources_cfg = _resources_config(game)
    deck = list(game.get("deck") or [])
    random.shuffle(deck)

    hand_size = int(hand_size_override or game.get("hand_size", 5))
    player_hand = deck[:hand_size]
    ai_hand = deck[hand_size:hand_size * 2]
    draw_pile = deck[hand_size * 2:]

    board_cfg = game.get("board") or {"size": 0, "tiles": []}
    tiles = []
    for t in board_cfg.get("tiles", []):
        tile = dict(t)
        tile.setdefault("owner", None)
        tile.setdefault("claim_power", 0)
        tiles.append(tile)

    return {
        "game_id": game.get("game_id"),
        "turn": 0,
        "turns_taken": 0,
        "max_turns": int(game.get("max_turns", 20)),
        "hand_size": hand_size,
        "win_condition": game.get("win_condition", "most_tiles"),
        "current_player": "player",
        "game_over": False,
        "winner": None,
        "resources": _starting_resources(resources_cfg),
        "ai_resources": _starting_resources(resources_cfg),
        "player_hand": player_hand,
        "ai_hand": ai_hand,
        "draw_pile": draw_pile,
        "discard_pile": [],
        "board": {"size": board_cfg.get("size", len(tiles)), "tiles": tiles},
        "player_position": 0,
        "ai_position": 0,
        "pending_trade": None,
        "skill_tag_counts": {},
        "image_cache": {},
        "log": [],
    }


def _card_power(card: Dict[str, Any], tile: Dict[str, Any]) -> float:
    bonus_total = sum(v for v in (card.get("resource_bonus") or {}).values() if isinstance(v, (int, float)))
    tile_bonus = card.get("tile_type_bonus") or {}
    multiplier = tile_bonus.get(tile.get("type"), tile_bonus.get("default", 1.0))
    return bonus_total * multiplier


def _apply_resource_delta(resources: Dict[str, float], resources_cfg: Dict[str, Dict[str, Any]], delta: Dict[str, float]) -> Dict[str, float]:
    applied = {}
    for key, amount in (delta or {}).items():
        if not isinstance(amount, (int, float)):
            continue
        cap = (resources_cfg.get(key) or {}).get("max")
        new_val = resources.get(key, 0) + amount
        if isinstance(cap, (int, float)):
            new_val = max(0, min(cap, new_val))
        else:
            new_val = max(0, new_val)
        applied[key] = new_val - resources.get(key, 0)
        resources[key] = new_val
    return applied


def _find_tile(state: Dict[str, Any], tile_id: str) -> Optional[Dict[str, Any]]:
    for t in state.get("board", {}).get("tiles", []):
        if t.get("id") == tile_id:
            return t
    return None


def _claim_tile(state: Dict[str, Any], game: Dict[str, Any], side: str, card: Dict[str, Any], tile: Dict[str, Any]) -> Tuple[Dict[str, float], str]:
    """Resolve one card-on-tile play for `side` ("player" or "ai"). Returns (applied_delta, outcome_text)."""
    resources_cfg = _resources_config(game)
    resources_key = "resources" if side == "player" else "ai_resources"
    resources = state[resources_key]
    power = _card_power(card, tile)

    if tile.get("owner") is None or tile.get("owner") == side:
        # Uncontested (or reinforcing your own claim): full bonus applies.
        applied = _apply_resource_delta(resources, resources_cfg, card.get("resource_bonus") or {})
        tile["owner"] = side
        tile["claim_power"] = max(tile.get("claim_power", 0), power)
        outcome = f"{card.get('title', 'Card')} claims {tile.get('label', tile.get('id'))}."
    elif power > tile.get("claim_power", 0):
        # Contested and won: take the tile, full bonus applies.
        applied = _apply_resource_delta(resources, resources_cfg, card.get("resource_bonus") or {})
        tile["owner"] = side
        tile["claim_power"] = power
        outcome = f"{card.get('title', 'Card')} overtakes {tile.get('label', tile.get('id'))}!"
    else:
        # Contested and lost: only half the bonus, as consolation.
        half_bonus = {k: v / 2 for k, v in (card.get("resource_bonus") or {}).items()}
        applied = _apply_resource_delta(resources, resources_cfg, half_bonus)
        outcome = f"{card.get('title', 'Card')} isn't strong enough to take {tile.get('label', tile.get('id'))}."

    if side == "player":
        tags = state.setdefault("skill_tag_counts", {})
        tag = card.get("skill_tag")
        if tag:
            tags[tag] = tags.get(tag, 0) + 1

    return applied, outcome


def _check_game_over(state: Dict[str, Any], game: Dict[str, Any]) -> None:
    if state.get("game_over"):
        return
    tiles = state.get("board", {}).get("tiles", [])
    all_claimed = bool(tiles) and all(t.get("owner") for t in tiles)
    turns_exhausted = state.get("turns_taken", 0) >= state.get("max_turns", 20)
    if not (all_claimed or turns_exhausted):
        return

    state["game_over"] = True
    win_condition = state.get("win_condition", "most_tiles")
    if win_condition == "most_tiles":
        player_tiles = sum(1 for t in tiles if t.get("owner") == "player")
        ai_tiles = sum(1 for t in tiles if t.get("owner") == "ai")
        state["winner"] = "player" if player_tiles > ai_tiles else ("ai" if ai_tiles > player_tiles else "tie")
    else:
        player_total = sum(state.get("resources", {}).values())
        ai_total = sum(state.get("ai_resources", {}).values())
        state["winner"] = "player" if player_total > ai_total else ("ai" if ai_total > player_total else "tie")


def play_card(state: Dict[str, Any], game: Dict[str, Any], card_id: str, tile_id: str) -> Tuple[Dict[str, Any], str, Dict[str, float]]:
    if state.get("game_over"):
        raise ValueError("Game is already over")
    card = next((c for c in state["player_hand"] if c.get("card_id") == card_id), None)
    if not card:
        raise ValueError(f"Card not in hand: {card_id}")
    tile = _find_tile(state, tile_id)
    if not tile:
        raise ValueError(f"Tile not found: {tile_id}")

    delta, outcome_text = _claim_tile(state, game, "player", card, tile)

    state["player_hand"] = [c for c in state["player_hand"] if c.get("card_id") != card_id]
    state["discard_pile"].append(card)
    state["turns_taken"] += 1
    state["turn"] += 1
    state["current_player"] = "ai"
    state["log"].append({"side": "player", "card_id": card_id, "tile_id": tile_id, "outcome": outcome_text})

    _check_game_over(state, game)
    return state, outcome_text, delta


def draw_card(state: Dict[str, Any], game: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    if not state["draw_pile"]:
        # Reshuffle discards back into the draw pile (classic deck-builder refill).
        if state["discard_pile"]:
            state["draw_pile"] = state["discard_pile"]
            state["discard_pile"] = []
            random.shuffle(state["draw_pile"])
        else:
            return state, None

    drawn = state["draw_pile"].pop(0)
    max_hand = state.get("hand_size", 5) + 2  # small buffer over the starting hand size
    if len(state["player_hand"]) < max_hand:
        state["player_hand"].append(drawn)
    else:
        state["discard_pile"].append(drawn)
    return state, drawn


def _ai_choose_card_and_tile(state: Dict[str, Any], game: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    hand = state.get("ai_hand") or []
    tiles = [t for t in state.get("board", {}).get("tiles", []) if t.get("owner") != "ai"]
    if not hand or not tiles:
        return None, None

    strategy = (game.get("ai_opponent") or {}).get("strategy", "balanced")
    best_card, best_tile, best_power = None, None, -1.0
    for card in hand:
        for tile in tiles:
            power = _card_power(card, tile)
            if strategy == "aggressive" and tile.get("owner") == "player":
                power *= 1.2  # prefers contesting the player's tiles
            elif strategy == "cautious" and tile.get("owner") is None:
                power *= 1.2  # prefers uncontested tiles
            if power > best_power:
                best_power = power
                best_card, best_tile = card, tile
    return best_card, best_tile


def ai_turn(state: Dict[str, Any], game: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if state.get("game_over"):
        raise ValueError("Game is already over")

    card, tile = _ai_choose_card_and_tile(state, game)
    if not card or not tile:
        ai_action = {"card_id": None, "tile_id": None, "outcome_text": "Mento has nothing to play.", "delta": {}}
    else:
        delta, outcome_text = _claim_tile(state, game, "ai", card, tile)
        state["ai_hand"] = [c for c in state["ai_hand"] if c.get("card_id") != card.get("card_id")]
        state["discard_pile"].append(card)
        ai_action = {"card_id": card.get("card_id"), "tile_id": tile.get("id"), "outcome_text": outcome_text, "delta": delta}

    state["turns_taken"] += 1
    state["turn"] += 1
    state["current_player"] = "player"
    state["log"].append({"side": "ai", **ai_action})

    _check_game_over(state, game)
    return state, ai_action


def propose_trade(state: Dict[str, Any], game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if state.get("game_over"):
        return None
    freq = (game.get("ai_opponent") or {}).get("trade_frequency", 0.2)
    if not state.get("ai_hand") or not state.get("player_hand"):
        return None
    if random.random() >= freq:
        return None

    ai_card = random.choice(state["ai_hand"])
    wanted_card = random.choice(state["player_hand"])
    ai_name = (game.get("ai_opponent") or {}).get("name", "Mento")
    return {
        "ai_card_id": ai_card.get("card_id"),
        "ai_card": ai_card,
        "wanted_player_card_id": wanted_card.get("card_id"),
        "wanted_player_card": wanted_card,
        "message": f"{ai_name} offers {ai_card.get('title')} in exchange for your {wanted_card.get('title')}.",
    }


def accept_trade(state: Dict[str, Any], player_card_id: str, ai_card_id: str) -> Dict[str, Any]:
    player_card = next((c for c in state["player_hand"] if c.get("card_id") == player_card_id), None)
    ai_card = next((c for c in state["ai_hand"] if c.get("card_id") == ai_card_id), None)
    if not player_card:
        raise ValueError(f"Card not in your hand: {player_card_id}")
    if not ai_card:
        raise ValueError(f"Card not in Mento's hand: {ai_card_id}")

    state["player_hand"] = [c for c in state["player_hand"] if c.get("card_id") != player_card_id]
    state["ai_hand"] = [c for c in state["ai_hand"] if c.get("card_id") != ai_card_id]
    state["player_hand"].append(ai_card)
    state["ai_hand"].append(player_card)
    state["pending_trade"] = None
    return state


def compute_skill_dimensions(state: Dict[str, Any], game: Dict[str, Any]) -> Dict[str, int]:
    """0-100 score per dimension in `game.dimension_scoring_weights`, blending
    how often the player leaned on each dimension's skill_tag and how far
    they pushed the matching resource toward its cap."""
    weights = game.get("dimension_scoring_weights") or {}
    dims = list(weights.keys()) or list(_resources_config(game).keys()) or ["strategic_thinking"]
    tag_counts = state.get("skill_tag_counts", {}) or {}
    total_tags = sum(tag_counts.values())
    resources_cfg = _resources_config(game)
    resources = state.get("resources", {})

    scores = {}
    for dim in dims:
        score = 50
        if total_tags:
            score += int(30 * (tag_counts.get(dim, 0) / total_tags))
        res_cfg = resources_cfg.get(dim)
        if res_cfg:
            cap = res_cfg.get("max", 20) or 20
            score += int(20 * min(1.0, resources.get(dim, 0) / cap))
        scores[dim] = max(0, min(100, score))
    return scores


def roll_dice(state: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """2d6 roll (board tiles are typically laid out for a ~7-average move)."""
    roll = random.randint(1, 6) + random.randint(1, 6)
    state["last_roll"] = roll
    return roll, state


def move_player(state: Dict[str, Any], game: Dict[str, Any], roll: int) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    board = state.get("board", {})
    tiles = board.get("tiles", [])
    size = board.get("size") or len(tiles)
    if not tiles or not size:
        return state, None

    resources_cfg = _resources_config(game)
    old_pos = state.get("player_position", 0)
    new_pos = (old_pos + roll) % size
    passed_go = new_pos < old_pos or (old_pos + roll) >= size
    state["player_position"] = new_pos

    tile = tiles[new_pos]
    applied_delta: Dict[str, float] = {}

    if passed_go and tile.get("type") != "go":
        go_bonus = game.get("go_bonus") or {}
        applied_delta.update(_apply_resource_delta(state["resources"], resources_cfg, go_bonus))

    event_card = None
    if tile.get("type") in ("go", "rest") and tile.get("delta"):
        applied_delta.update(_apply_resource_delta(state["resources"], resources_cfg, tile["delta"]))
    elif tile.get("type") == "event":
        events = game.get("event_cards") or []
        if events:
            event_card = random.choice(events)
            applied_delta.update(_apply_resource_delta(state["resources"], resources_cfg, event_card.get("delta") or {}))

    requires_card_play = tile.get("type") in ("claim", "challenge", "crisis") and tile.get("owner") != "player"

    tile_event = {
        "tile_id": tile.get("id"),
        "type": tile.get("type"),
        "label": tile.get("label"),
        "icon": tile.get("icon"),
        "story": tile.get("story") or (event_card or {}).get("story"),
        "delta": applied_delta or None,
        "event_card": event_card,
        "image_prompt": tile.get("image_prompt") or (event_card or {}).get("image_prompt"),
        "requires_card_play": requires_card_play,
    }
    state["log"].append({"side": "player", "action": "move", "roll": roll, **{"tile_id": tile.get("id")}})
    return state, tile_event
