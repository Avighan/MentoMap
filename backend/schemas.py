"""
Simple validation for demo_bundle.json (multi-game arcade).
Not full JSON Schema today; lightweight checks.
"""

def validate_bundle(b: dict) -> None:
    """Validate the bundle has required structure for multi-game arcade."""
    if "games" not in b or not isinstance(b["games"], list) or len(b["games"]) == 0:
        raise ValueError("Bundle must contain games[] array with at least 1 game")

    for g in b["games"]:
        game_type = g.get("game_type", "rounds")

        # Common required keys for all types
        for k in ["game_id", "title", "initial_state"]:
            if k not in g:
                raise ValueError(f"Game missing required key '{k}': {g.get('game_id','unknown')}")

        if game_type == "rounds":
            _validate_rounds_game(g)
        elif game_type == "board":
            _validate_board_game(g)
        elif game_type == "minigame":
            _validate_minigame(g)
        elif game_type == "card":
            _validate_card_game(g)
        elif game_type == "strategy":
            _validate_strategy_game(g)
        elif game_type == "ai_arena":
            _validate_ai_arena_game(g)
        elif game_type == "negotiation":
            _validate_negotiation_type_game(g)
        elif game_type == "negotiation_series":
            _validate_negotiation_series_game(g)
        elif game_type == "debate":
            _validate_debate_game(g)
        elif game_type == "story_branching":
            _validate_story_branching_game(g)
            _sb_errors = []
            _validate_story_branching_type_game(g, _sb_errors)
            if _sb_errors:
                raise ValueError(
                    f"Story branching game '{g.get('game_id','unknown')}' validation errors: "
                    + "; ".join(_sb_errors)
                )
        elif game_type == "chess_strategy":
            _validate_chess_strategy_game(g)
        elif game_type == "go_territory":
            _validate_go_territory_game(g)
        elif game_type == "reversi":
            _validate_reversi_game(g)
        elif game_type == "tower_defense":
            _validate_tower_defense_game(g)
        elif game_type == "puzzle_match":
            _validate_puzzle_match_game(g)
        elif game_type == "strategy_grid":
            _validate_strategy_grid_game(g)
        elif game_type == "card_board":
            if not (g.get("card_board_config") or g.get("deck") or g.get("board") or g.get("cards")):
                raise ValueError(f"card_board game '{g['game_id']}' missing card structure (expected 'deck', 'board', or 'card_board_config')")
        elif game_type == "trump_card":
            if not (g.get("trump_card_config") or g.get("cards") or g.get("deck") or g.get("attributes")):
                raise ValueError(f"trump_card game '{g['game_id']}' missing card data (expected 'cards', 'deck', or 'trump_card_config')")
        elif game_type == "wellbeing_survey":
            if not (g.get("questions") or g.get("rounds") or g.get("sections")):
                raise ValueError(f"wellbeing_survey game '{g['game_id']}' missing 'questions', 'rounds', or 'sections' key")
        elif game_type == "simulation":
            if not (g.get("rounds") and g.get("simulation_config")):
                raise ValueError(f"simulation game '{g['game_id']}' missing 'rounds' or 'simulation_config' key")
        elif game_type == "mystery_room":
            if not (g.get("rooms") and g.get("puzzles") and g.get("climax")):
                raise ValueError(f"mystery_room game '{g['game_id']}' missing 'rooms', 'puzzles', or 'climax' key")
        elif game_type == "ai_lab":
            if not g.get("ai_lab_config"):
                raise ValueError(f"ai_lab game '{g['game_id']}' missing 'ai_lab_config' key")
            tasks = g["ai_lab_config"].get("tasks")
            if not isinstance(tasks, list) or not tasks:
                raise ValueError(f"ai_lab game '{g['game_id']}' must have ai_lab_config.tasks[] with >=1 task")
            for t in tasks:
                for k in ("id", "title", "instruction", "rubric"):
                    if k not in t:
                        raise ValueError(f"ai_lab task missing '{k}' in '{g['game_id']}'")
        elif game_type == "music_match":
            if not g.get("music_rounds"):
                raise ValueError(f"music_match game '{g['game_id']}' missing 'music_rounds' key")
        elif game_type == "lab_titration":
            if not g.get("titration"):
                raise ValueError(f"lab_titration game '{g['game_id']}' missing 'titration' key")
        elif game_type == "pendulum_lab":
            if not (g.get("pendulum_lab") and g["pendulum_lab"].get("trials")):
                raise ValueError(f"pendulum_lab game '{g['game_id']}' missing 'pendulum_lab.trials'")
        elif game_type == "optics_lab":
            if not (g.get("optics_lab") and g["optics_lab"].get("trials")):
                raise ValueError(f"optics_lab game '{g['game_id']}' missing 'optics_lab.trials'")
        elif game_type == "circuit_debugger":
            if not (g.get("circuit_debugger") and g["circuit_debugger"].get("nodes")):
                raise ValueError(f"circuit_debugger game '{g['game_id']}' missing 'circuit_debugger.nodes'")
        elif game_type == "genetics_cross":
            if not (g.get("genetics_cross") and g["genetics_cross"].get("phenotypes")):
                raise ValueError(f"genetics_cross game '{g['game_id']}' missing 'genetics_cross.phenotypes'")
        elif game_type == "stoichiometry_mixer":
            if not g.get("stoichiometry_mixer"):
                raise ValueError(f"stoichiometry_mixer game '{g['game_id']}' missing 'stoichiometry_mixer' key")
        elif game_type == "mental_math":
            if not (g.get("mental_math") and g["mental_math"].get("problems")):
                raise ValueError(f"mental_math game '{g['game_id']}' missing 'mental_math.problems'")
        elif game_type == "typing_drill":
            if not (g.get("typing_drill") and g["typing_drill"].get("passages")):
                raise ValueError(f"typing_drill game '{g['game_id']}' missing 'typing_drill.passages'")
        elif game_type == "boggle":
            if not (g.get("boggle") and g["boggle"].get("grid")):
                raise ValueError(f"boggle game '{g['game_id']}' missing 'boggle.grid'")
        elif game_type == "mock_interview":
            if not (g.get("mock_interview") and g["mock_interview"].get("questions")):
                raise ValueError(f"mock_interview game '{g['game_id']}' missing 'mock_interview.questions'")
        elif game_type == "sudoku":
            if not (g.get("sudoku") and g["sudoku"].get("puzzle")):
                raise ValueError(f"sudoku game '{g['game_id']}' missing 'sudoku.puzzle'")
        elif game_type == "logic_grid":
            if not (g.get("logic_grid") and g["logic_grid"].get("solution")):
                raise ValueError(f"logic_grid game '{g['game_id']}' missing 'logic_grid.solution'")
        elif game_type == "geometry_constructor":
            if not (g.get("geometry_constructor") and g["geometry_constructor"].get("features")):
                raise ValueError(f"geometry_constructor game '{g['game_id']}' missing 'geometry_constructor.features'")
        else:
            raise ValueError(f"Game {g['game_id']}: invalid game_type '{game_type}'")

    # Validate negotiation_game if present (optional)
    if "negotiation_game" in b:
        validate_negotiation_game(b["negotiation_game"])
    
    # Validate layout_config if present in games (optional)
    for g in b["games"]:
        if "layout_config" in g:
            validate_layout_config(g["layout_config"], g["game_id"])
        if "mento_score_config" in g:
            validate_mento_score_config(g["mento_score_config"], g["game_id"])
    
    print(f"✓ Bundle validated: {len(b['games'])} games")


def _validate_rounds_game(g):
    """Validate a round-based game (original game type)."""
    if "rounds" not in g:
        raise ValueError(f"Game missing required key 'rounds': {g.get('game_id','unknown')}")

    if not isinstance(g["rounds"], list) or len(g["rounds"]) < 1:
        raise ValueError(f"Game {g['game_id']} must have at least 1 round")

    # Check each round
    for r in g["rounds"]:
        # Accept either 'id' or 'round_id' as the round identifier
        round_id = r.get("id") or r.get("round_id")
        if not round_id:
            raise ValueError(f"Round missing key 'id' or 'round_id' in game {g['game_id']}")

        # Check if round has either choices OR tabs
        has_choices = "choices" in r and isinstance(r["choices"], list) and len(r["choices"]) > 0
        has_tabs = "tabs" in r and isinstance(r["tabs"], list) and len(r["tabs"]) > 0

        if not has_choices and not has_tabs:
            raise ValueError(f"Round {round_id} must have either 'choices' array or 'tabs' array with at least 1 item")

        # Validate direct choices if present
        if has_choices:
            for c in r["choices"]:
                if "id" not in c or "label" not in c:
                    raise ValueError(f"Choice missing fields (id/label) in round {round_id}")
                if "delta" not in c and "effects" not in c:
                    raise ValueError(f"Choice missing 'delta' or 'effects' in round {round_id}")

        # Validate tabs if present
        if has_tabs:
            for tab in r["tabs"]:
                if "id" not in tab:
                    raise ValueError(f"Tab missing 'id' in round {round_id}")
                if "choices" not in tab or not isinstance(tab["choices"], list):
                    raise ValueError(f"Tab {tab.get('id', '?')} missing 'choices' array in round {round_id}")
                for c in tab["choices"]:
                    if "id" not in c or "label" not in c:
                        raise ValueError(f"Choice missing fields (id/label) in tab {tab['id']}, round {round_id}")
                    if "delta" not in c and "effects" not in c:
                        raise ValueError(f"Choice missing 'delta' or 'effects' in tab {tab['id']}, round {round_id}")


def _validate_board_game(g):
    """Validate a board game structure."""
    if "board_config" not in g:
        raise ValueError(f"Board game {g['game_id']} missing 'board_config'")
    bc = g["board_config"]
    if "grid_size" not in bc or "tiles" not in bc:
        raise ValueError(f"Board game {g['game_id']}: board_config needs 'grid_size' and 'tiles'")
    for tile in bc["tiles"]:
        if "type" not in tile or "position" not in tile:
            raise ValueError(f"Board game {g['game_id']}: each tile needs 'type' and 'position'")
    # Validate tile_types if present (accepts both string labels and object configs)
    if "tile_types" in bc:
        for k, v in bc["tile_types"].items():
            if not isinstance(v, (str, dict)):
                raise ValueError(f"Board game {g['game_id']}: tile_types['{k}'] must be a string or object")
    # Validate tile_effects if present (optional)
    if "tile_effects" in bc:
        if not isinstance(bc["tile_effects"], dict):
            raise ValueError(f"Board game {g['game_id']}: tile_effects must be a dictionary")
        for effect_type, effect in bc["tile_effects"].items():
            if not isinstance(effect, dict):
                raise ValueError(f"Board game {g['game_id']}: tile_effects['{effect_type}'] must be a dictionary")
    # Validate power_ups if present (optional)
    if "power_ups" in bc:
        if not isinstance(bc["power_ups"], list):
            raise ValueError(f"Board game {g['game_id']}: power_ups must be a list")
        for pu in bc["power_ups"]:
            if not isinstance(pu, dict) or "id" not in pu:
                raise ValueError(f"Board game {g['game_id']}: each power_up needs at least 'id'")
    # Validate ai_competitors if present (optional)
    if "ai_competitors" in bc:
        if not isinstance(bc["ai_competitors"], list):
            raise ValueError(f"Board game {g['game_id']}: ai_competitors must be a list")
        valid_personalities = ["aggressive", "balanced", "quality_focused", "follower"]
        for comp in bc["ai_competitors"]:
            if not isinstance(comp, dict) or "id" not in comp or "name" not in comp:
                raise ValueError(f"Board game {g['game_id']}: each ai_competitor needs 'id' and 'name'")
            if comp.get("personality") and comp["personality"] not in valid_personalities:
                raise ValueError(f"Board game {g['game_id']}: ai_competitor '{comp['id']}' has invalid personality '{comp['personality']}'. Valid: {valid_personalities}")
    # Validate world_events if present (top-level, optional)
    if "world_events" in g:
        if not isinstance(g["world_events"], list):
            raise ValueError(f"Board game {g['game_id']}: world_events must be a list")
        for we in g["world_events"]:
            if not isinstance(we, dict) or "id" not in we:
                raise ValueError(f"Board game {g['game_id']}: each world_event needs at least 'id'")
    # Validate achievements if present (top-level, optional)
    if "achievements" in g:
        if not isinstance(g["achievements"], list):
            raise ValueError(f"Board game {g['game_id']}: achievements must be a list")
        for ach in g["achievements"]:
            if not isinstance(ach, dict) or "id" not in ach:
                raise ValueError(f"Board game {g['game_id']}: each achievement needs at least 'id'")
    if "events" not in g:
        raise ValueError(f"Board game {g['game_id']} missing 'events' dict")
    print(f"✓ Board game validated: {g['game_id']}")


def _validate_minigame(g):
    """Validate a mini-game structure."""
    if "minigame_config" not in g:
        raise ValueError(f"Mini-game {g['game_id']} missing 'minigame_config'")
    mc = g["minigame_config"]
    valid_subtypes = [
        "matching", "sorting", "timed_challenge", "drag_drop", "stock_market", "escape_room",
        "timeline", "connection", "code_editor", "map_quiz", "word_puzzle",
        "flashcard", "typing_speed", "drag_drop_builder", "auction", "boggle",
    ]
    if mc.get("subtype") not in valid_subtypes:
        raise ValueError(f"Mini-game {g['game_id']}: invalid subtype '{mc.get('subtype')}'")
    print(f"✓ Mini-game validated: {g['game_id']}")


def _validate_card_game(g):
    """Validate a card game structure."""
    if "card_config" not in g:
        raise ValueError(f"Card game {g['game_id']} missing 'card_config'")
    cc = g["card_config"]
    if "cards" not in cc or not isinstance(cc["cards"], list) or len(cc["cards"]) < 1:
        raise ValueError(f"Card game {g['game_id']}: card_config needs 'cards' array with at least 1 card")
    for card in cc["cards"]:
        if "id" not in card or "name" not in card:
            raise ValueError(f"Card game {g['game_id']}: each card needs 'id' and 'name'")
    print(f"✓ Card game validated: {g['game_id']}")


def _validate_strategy_game(g):
    """Validate a strategy game structure."""
    if "strategy_config" not in g:
        raise ValueError(f"Strategy game {g['game_id']} missing 'strategy_config'")
    sc = g["strategy_config"]
    if "grid_size" not in sc:
        raise ValueError(f"Strategy game {g['game_id']}: strategy_config needs 'grid_size'")
    if "units" not in sc or not isinstance(sc["units"], list):
        raise ValueError(f"Strategy game {g['game_id']}: strategy_config needs 'units' array")
    print(f"✓ Strategy game validated: {g['game_id']}")


def _validate_ai_arena_game(g):
    """Validate an AI Arena game structure."""
    gid = g.get('game_id', 'unknown')

    # ai_arena_config is required
    if "ai_arena_config" not in g:
        raise ValueError(f"AI Arena game {gid} missing 'ai_arena_config'")
    cfg = g["ai_arena_config"]
    if not isinstance(cfg, dict):
        raise ValueError(f"AI Arena game {gid}: ai_arena_config must be a dictionary")

    # Must have either base_rounds or rounds
    has_base = "base_rounds" in g and isinstance(g["base_rounds"], list) and len(g["base_rounds"]) > 0
    has_rounds = "rounds" in g and isinstance(g["rounds"], list) and len(g["rounds"]) > 0
    if not has_base and not has_rounds:
        raise ValueError(f"AI Arena game {gid}: needs 'base_rounds' or 'rounds' array with at least 1 entry")

    # Validate base_rounds if present
    if has_base:
        for i, r in enumerate(g["base_rounds"]):
            if "id" not in r:
                raise ValueError(f"AI Arena game {gid}: base_round {i} missing 'id'")
            if not r.get("ai_generatable", False):
                # Fixed rounds should have choices
                if "choices" not in r or not isinstance(r["choices"], list):
                    raise ValueError(f"AI Arena game {gid}: fixed base_round '{r['id']}' needs 'choices' array")

    # Validate story_intro if present (optional)
    if "story_intro" in g and g["story_intro"]:
        si = g["story_intro"]
        if "scenes" in si and isinstance(si["scenes"], list):
            for scene in si["scenes"]:
                if "scene_id" not in scene:
                    raise ValueError(f"AI Arena game {gid}: story scene missing 'scene_id'")
                if "narrative" not in scene and "title" not in scene:
                    raise ValueError(f"AI Arena game {gid}: story scene '{scene.get('scene_id')}' needs 'narrative' or 'title'")

    # Validate npcs if present (optional)
    if "npcs" in g and isinstance(g["npcs"], list):
        for npc in g["npcs"]:
            if "id" not in npc or "name" not in npc:
                raise ValueError(f"AI Arena game {gid}: each NPC needs 'id' and 'name'")

    # Validate competitors if present (optional)
    if "competitors" in g and isinstance(g["competitors"], list):
        for comp in g["competitors"]:
            if "id" not in comp or "name" not in comp:
                raise ValueError(f"AI Arena game {gid}: each competitor needs 'id' and 'name'")

    print(f"✓ AI Arena game validated: {gid}")


def _find_scenarios_wrapper(g, canonical_keys=("negotiation_config", "debate_config")):
    """Locate a scenarios array across the canonical and historical wrapper shapes.
    Returns (wrapper_key, scenarios_list, wrapper_obj) or (None, None, None) if not found.
    Accepts: negotiation_config.scenarios, debate_config.scenarios, session_game.scenarios,
    negotiation_game.scenarios, debate_game.scenarios, investor_pitch_game.scenarios,
    mock_interview.scenarios, top-level scenarios.
    """
    for k in canonical_keys:
        v = g.get(k)
        if isinstance(v, dict) and isinstance(v.get("scenarios"), list) and len(v["scenarios"]) >= 1:
            return k, v["scenarios"], v
    for k in ("session_game", "negotiation_game", "debate_game", "investor_pitch_game", "mock_interview"):
        v = g.get(k)
        if isinstance(v, dict) and isinstance(v.get("scenarios"), list) and len(v["scenarios"]) >= 1:
            return k, v["scenarios"], v
    if isinstance(g.get("scenarios"), list) and len(g["scenarios"]) >= 1:
        return "scenarios", g["scenarios"], g
    return None, None, None


def _has_persona_pool(g, wrapper_obj):
    """A persona/role pool may live at game-level or inside the wrapper.
    Supported keys: persona_pool, investor_pool, interviewer_pool, mentor_pool, opponent_pool.
    """
    pool_keys = ("persona_pool", "investor_pool", "interviewer_pool", "mentor_pool", "opponent_pool")
    for src in (g, wrapper_obj):
        if not isinstance(src, dict):
            continue
        for k in pool_keys:
            v = src.get(k)
            if isinstance(v, list) and len(v) >= 1:
                return True
    return False


def _validate_negotiation_type_game(g):
    """Validate a negotiation game_type game.
    Accepts the canonical 'negotiation_config.scenarios' shape AND historical
    wrappers used by Live AI Sessions: session_game.scenarios,
    negotiation_game.scenarios, investor_pitch_game.scenarios, mock_interview.scenarios.
    """
    gid = g.get('game_id', 'unknown')
    wrapper, scenarios, wrapper_obj = _find_scenarios_wrapper(g, canonical_keys=("negotiation_config",))
    if scenarios is None:
        raise ValueError(f"Negotiation game {gid} missing 'negotiation_config' (or recognised scenario wrapper)")
    has_pool = _has_persona_pool(g, wrapper_obj)
    for s in scenarios:
        if "scenario_id" not in s or "title" not in s:
            raise ValueError(f"Negotiation game {gid}: each scenario needs 'scenario_id' and 'title'")
        if not has_pool:
            other = s.get("other_party") or s.get("opponent") or s.get("ai_persona")
            if not isinstance(other, dict):
                raise ValueError(f"Negotiation game {gid}: scenario '{s.get('scenario_id')}' needs 'other_party'/'opponent'/'ai_persona' dict (or persona_pool)")
    print(f"✓ Negotiation game validated: {gid} ({len(scenarios)} scenarios via {wrapper})")


def _validate_negotiation_series_game(g):
    """Validate a negotiation_series wrapper game (dispatches to negotiation_game scenarios)."""
    gid = g.get('game_id', 'unknown')
    series = g.get("scenario_series")
    if not isinstance(series, dict):
        raise ValueError(f"negotiation_series game {gid} missing 'scenario_series' dict")
    ordered = series.get("ordered_scenarios")
    if not isinstance(ordered, list) or len(ordered) < 1:
        raise ValueError(f"negotiation_series game {gid}: scenario_series.ordered_scenarios must be non-empty list")
    print(f"✓ Negotiation series wrapper validated: {gid} ({len(ordered)} scenarios)")


def _validate_debate_game(g):
    """Validate a debate game_type game.
    A debate game can either embed scenarios via debate_config, or be a thin
    wrapper that dispatches to a scenario in the bundle's debate_game via
    engine_scenario_id. Both shapes are allowed.
    """
    gid = g.get('game_id', 'unknown')
    if g.get("engine_scenario_id"):
        print(f"✓ Debate wrapper validated: {gid} -> {g['engine_scenario_id']}")
        return
    wrapper, scenarios, wrapper_obj = _find_scenarios_wrapper(g, canonical_keys=("debate_config",))
    if scenarios is None:
        raise ValueError(f"Debate game {gid} missing 'debate_config' or 'engine_scenario_id' (or recognised scenario wrapper)")
    has_pool = _has_persona_pool(g, wrapper_obj)
    for s in scenarios:
        if "scenario_id" not in s or "title" not in s:
            raise ValueError(f"Debate game {gid}: each scenario needs 'scenario_id' and 'title'")
        if not has_pool:
            opp = s.get("opponent") or s.get("other_party") or s.get("ai_persona")
            if not isinstance(opp, dict):
                raise ValueError(f"Debate game {gid}: scenario '{s.get('scenario_id')}' needs 'opponent'/'other_party'/'ai_persona' dict (or persona_pool)")
    print(f"✓ Debate game validated: {gid} ({len(scenarios)} scenarios via {wrapper})")


def _validate_story_branching_game(g):
    """Validate a story_branching game_type game."""
    gid = g.get('game_id', 'unknown')
    if "story_intro" not in g or not isinstance(g["story_intro"], dict):
        raise ValueError(f"Story branching game {gid} missing 'story_intro'")
    si = g["story_intro"]
    if "scenes" not in si or not isinstance(si["scenes"], list) or len(si["scenes"]) < 1:
        raise ValueError(f"Story branching game {gid}: story_intro needs 'scenes' array with at least 1 scene")
    scene_ids = set()
    has_terminal = False
    for scene in si["scenes"]:
        if "scene_id" not in scene:
            raise ValueError(f"Story branching game {gid}: each scene needs 'scene_id'")
        if "narrative" not in scene and "title" not in scene:
            raise ValueError(f"Story branching game {gid}: scene '{scene.get('scene_id')}' needs 'narrative' or 'title'")
        scene_ids.add(scene["scene_id"])
        if scene.get("transitions_to_gameplay"):
            has_terminal = True
    if not has_terminal:
        raise ValueError(f"Story branching game {gid}: at least one scene must have 'transitions_to_gameplay': true")
    # Validate scene references
    for scene in si["scenes"]:
        for choice in scene.get("choices", []):
            next_scene = choice.get("next_scene")
            if next_scene and next_scene not in scene_ids:
                raise ValueError(f"Story branching game {gid}: choice references unknown scene '{next_scene}'")
    print(f"✓ Story branching game validated: {gid} ({len(si['scenes'])} scenes)")


def _validate_chat_breakout(scene, scene_id, errors):
    """Validate optional chat_breakout block on a story_branching scene.

    If absent, no-op. If present, enforces the schema described in the
    Hybrid Narrative-Negotiation plan: ai_persona.name, opening_message,
    max_turns 1..20, outcome_bands (non-empty), next_scene_by_outcome
    whose keys equal outcome_bands keys.
    """
    cb = scene.get("chat_breakout")
    if cb is None:
        return
    prefix = f"scene '{scene_id}' chat_breakout"
    if not isinstance(cb, dict):
        errors.append(f"{prefix} must be an object")
        return
    if not isinstance(cb.get("ai_persona"), dict) or not cb["ai_persona"].get("name"):
        errors.append(f"{prefix} missing ai_persona.name")
    if not isinstance(cb.get("opening_message"), str) or not cb["opening_message"].strip():
        errors.append(f"{prefix} missing opening_message")
    max_turns = cb.get("max_turns")
    if not isinstance(max_turns, int) or isinstance(max_turns, bool) or max_turns < 1 or max_turns > 20:
        errors.append(f"{prefix} max_turns must be int 1..20")
    bands = cb.get("outcome_bands")
    if not isinstance(bands, dict) or not bands:
        errors.append(f"{prefix} outcome_bands must be a non-empty object")
        return
    for band_key, band in bands.items():
        if not isinstance(band, dict):
            errors.append(f"{prefix} outcome_bands.{band_key} must be an object")
            continue
        if not isinstance(band.get("min_score"), (int, float)) or isinstance(band.get("min_score"), bool):
            errors.append(f"{prefix} outcome_bands.{band_key}.min_score must be a number")
        if not isinstance(band.get("label"), str):
            errors.append(f"{prefix} outcome_bands.{band_key}.label must be a string")
    nsbo = cb.get("next_scene_by_outcome")
    if not isinstance(nsbo, dict) or not nsbo:
        errors.append(f"{prefix} next_scene_by_outcome must be a non-empty object")
        return
    band_keys = set(bands.keys())
    nsbo_keys = set(nsbo.keys())
    if band_keys != nsbo_keys:
        missing = band_keys - nsbo_keys
        extra = nsbo_keys - band_keys
        errors.append(
            f"{prefix} next_scene_by_outcome keys must match outcome_bands "
            f"(missing={sorted(missing)}, extra={sorted(extra)})"
        )


def _validate_story_branching_type_game(game, errors):
    """Error-accumulating validator for story_branching games.

    Unlike _validate_story_branching_game (which raises), this function
    appends strings to `errors` so callers can collect all problems.
    Validates chat_breakout blocks on each scene.
    """
    gid = game.get("game_id", "unknown")
    si = game.get("story_intro")
    if not isinstance(si, dict):
        errors.append(f"Story branching game {gid} missing 'story_intro'")
        return
    scenes = si.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 1:
        errors.append(f"Story branching game {gid}: story_intro needs 'scenes' array with at least 1 scene")
        return
    for scene in scenes:
        scene_id = scene.get("scene_id") or scene.get("id") or "?"
        _validate_chat_breakout(scene, scene_id, errors)


def validate_negotiation_game(ng: dict) -> None:
    """Validate the negotiation game structure (optional component)."""
    if not isinstance(ng, dict):
        raise ValueError("negotiation_game must be a dictionary")
    
    # Scenarios are optional but if present, must be valid
    if "scenarios" in ng:
        if not isinstance(ng["scenarios"], list):
            raise ValueError("negotiation_game.scenarios must be a list")
        
        for i, scenario in enumerate(ng["scenarios"]):
            # Check required scenario fields
            required_fields = ["scenario_id", "title", "description", "other_party"]
            for field in required_fields:
                if field not in scenario:
                    raise ValueError(f"Scenario {i} missing required field: {field}")
            
            # Validate other_party
            other_party = scenario.get("other_party", {})
            if not isinstance(other_party, dict):
                raise ValueError(f"Scenario {scenario.get('scenario_id')} other_party must be a dictionary")
            
            if "name" not in other_party:
                raise ValueError(f"Scenario {scenario.get('scenario_id')} other_party missing 'name'")
    
    print(f"✓ Negotiation game validated: {len(ng.get('scenarios', []))} scenarios")


def validate_mento_score_config(msc: dict, game_id: str) -> None:
    """Validate the mento_score_config structure (optional component for scoring)."""
    if not isinstance(msc, dict):
        raise ValueError(f"Game {game_id}: mento_score_config must be a dictionary")
    
    # Validate weights if present
    if "weights" in msc:
        weights = msc["weights"]
        if not isinstance(weights, dict):
            raise ValueError(f"Game {game_id}: mento_score_config.weights must be a dictionary")
        
        # Check that all weights are floats
        for key, value in weights.items():
            if not isinstance(value, (int, float)):
                raise ValueError(f"Game {game_id}: weight '{key}' must be a number, got {type(value)}")
        
        # Check that weights sum to approximately 1.0
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):
            print(f"[WARNING] Game {game_id}: mento_score weights sum to {total}, should be 1.0")
    
    print(f"✓ Mento Score config validated for game {game_id}")


def validate_layout_config(lc: dict, game_id: str) -> None:
    """Validate the layout_config structure (optional component for UI customization)."""
    if not isinstance(lc, dict):
        raise ValueError(f"Game {game_id}: layout_config must be a dictionary")
    
    # layout_type is required if layout_config exists
    if "layout_type" not in lc:
        raise ValueError(f"Game {game_id}: layout_config missing required 'layout_type'")
    
    valid_layout_types = [
        "classic", 
        "journey", 
        "split_top_stats", 
        "split_header", 
        "minimal", 
        "dashboard",  # Now implemented!
        "immersive",   # Now implemented!
        "split_horizontal_stats",  # Custom layout from image
        "kids_friendly",  # Age-appropriate layouts
        "teen_modern",
        "professional_dashboard",
        "executive_dashboard",
        "accessible_clear"
    ]
    
    if lc["layout_type"] not in valid_layout_types:
        raise ValueError(
            f"Game {game_id}: invalid layout_type '{lc['layout_type']}'. "
            f"Valid types: {', '.join(valid_layout_types)}"
        )
    
    # Theme is optional but if present, validate basic structure
    if "theme" in lc:
        if not isinstance(lc["theme"], dict):
            raise ValueError(f"Game {game_id}: layout_config.theme must be a dictionary")
        
        # Color values should be strings (hex, rgb, rgba, or CSS color names)
        color_fields = ["primary_color", "secondary_color", "accent_color", "background_color", "text_color"]
        for field in color_fields:
            if field in lc["theme"] and not isinstance(lc["theme"][field], str):
                raise ValueError(f"Game {game_id}: theme.{field} must be a string")
    
    # All section configs are optional but if present, must be dicts
    section_fields = [
        "header", "video_section", "story_section", "choices_section", 
        "stats_section", "glossary_section", "progress_display", "responsive"
    ]
    
    for field in section_fields:
        if field in lc and not isinstance(lc[field], dict):
            raise ValueError(f"Game {game_id}: layout_config.{field} must be a dictionary")
    
    print(f"✓ Layout config validated for game {game_id}: type '{lc['layout_type']}'")


# ─── Engine-specific validators ───────────────────────────────────────────

def _validate_chess_strategy_game(g: dict) -> None:
    """Validate chess_strategy game has required chess_config."""
    gid = g.get("game_id", "unknown")
    if "chess_config" not in g:
        raise ValueError(f"Game {gid}: chess_strategy game missing 'chess_config'")
    cc = g["chess_config"]
    if not isinstance(cc, dict):
        raise ValueError(f"Game {gid}: chess_config must be a dictionary")
    # theme_config is optional but recommended
    tc = cc.get("theme_config", {})
    if tc:
        for field in ["piece_stats", "piece_moves"]:
            if field in tc and not isinstance(tc[field], dict):
                raise ValueError(f"Game {gid}: chess_config.theme_config.{field} must be a dict")
    print(f"✓ Chess strategy config validated for game {gid}")


def _validate_go_territory_game(g: dict) -> None:
    """Validate go_territory game has required go_config."""
    gid = g.get("game_id", "unknown")
    if "go_config" not in g:
        raise ValueError(f"Game {gid}: go_territory game missing 'go_config'")
    gc = g["go_config"]
    if not isinstance(gc, dict):
        raise ValueError(f"Game {gid}: go_config must be a dictionary")
    bs = gc.get("board_size", 9)
    if bs not in (9, 13, 19):
        print(f"[WARNING] Game {gid}: non-standard go board_size {bs} (expected 9, 13, or 19)")
    print(f"✓ Go territory config validated for game {gid}")


def _validate_reversi_game(g: dict) -> None:
    """Validate reversi game has required reversi_config."""
    gid = g.get("game_id", "unknown")
    if "reversi_config" not in g:
        raise ValueError(f"Game {gid}: reversi game missing 'reversi_config'")
    rc = g["reversi_config"]
    if not isinstance(rc, dict):
        raise ValueError(f"Game {gid}: reversi_config must be a dictionary")
    print(f"✓ Reversi config validated for game {gid}")


def _validate_tower_defense_game(g: dict) -> None:
    """Validate tower_defense game has required td_config."""
    gid = g.get("game_id", "unknown")
    if "td_config" not in g:
        raise ValueError(f"Game {gid}: tower_defense game missing 'td_config'")
    tc = g["td_config"]
    if not isinstance(tc, dict):
        raise ValueError(f"Game {gid}: td_config must be a dictionary")
    for field in ["grid_width", "grid_height"]:
        if field in tc and not isinstance(tc[field], int):
            raise ValueError(f"Game {gid}: td_config.{field} must be an integer")
    print(f"✓ Tower defense config validated for game {gid}")


def _validate_puzzle_match_game(g: dict) -> None:
    """Validate puzzle_match game has required puzzle_config."""
    gid = g.get("game_id", "unknown")
    if "puzzle_config" not in g:
        raise ValueError(f"Game {gid}: puzzle_match game missing 'puzzle_config'")
    pc = g["puzzle_config"]
    if not isinstance(pc, dict):
        raise ValueError(f"Game {gid}: puzzle_config must be a dictionary")
    gs = pc.get("grid_size", 6)
    if not (4 <= gs <= 10):
        print(f"[WARNING] Game {gid}: unusual puzzle grid_size {gs} (expected 4-10)")
    tc = pc.get("theme_config", {})
    if tc and "tile_types" in tc:
        if len(tc["tile_types"]) < 3:
            print(f"[WARNING] Game {gid}: puzzle needs at least 3 tile_types, found {len(tc['tile_types'])}")
    print(f"✓ Puzzle match config validated for game {gid}")


def _validate_strategy_grid_game(g: dict) -> None:
    """Validate strategy_grid game has required strategy_grid_config."""
    gid = g.get("game_id", "unknown")
    if "strategy_grid_config" not in g:
        raise ValueError(f"Game {gid}: strategy_grid game missing 'strategy_grid_config'")
    sgc = g["strategy_grid_config"]
    if not isinstance(sgc, dict):
        raise ValueError(f"Game {gid}: strategy_grid_config must be a dictionary")
    gw = sgc.get("grid_width", 10)
    gh = sgc.get("grid_height", 10)
    if not (4 <= gw <= 32) or not (4 <= gh <= 32):
        print(f"[WARNING] Game {gid}: unusual grid dimensions {gw}x{gh} (expected 4-32)")
    # N-player mode uses 'players' array + 'piece_types' shared pool
    players = sgc.get("players", [])
    if players:
        if not isinstance(players, list):
            print(f"[WARNING] Game {gid}: players must be a list")
        else:
            for p in players:
                if "slot" not in p:
                    print(f"[WARNING] Game {gid}: player entry missing 'slot'")
        piece_types = sgc.get("piece_types", [])
        if len(piece_types) == 0:
            print(f"[WARNING] Game {gid}: multiplayer game has no piece_types defined")
    else:
        # Legacy 2-player mode
        pp = sgc.get("player_pieces", [])
        ap = sgc.get("ai_pieces", [])
        if len(pp) == 0:
            print(f"[WARNING] Game {gid}: strategy_grid has no player_pieces defined")
        if len(ap) == 0:
            print(f"[WARNING] Game {gid}: strategy_grid has no ai_pieces defined")
    print(f"✓ Strategy grid config validated for game {gid}")
