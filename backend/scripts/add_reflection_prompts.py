"""Add a tailored reflection_prompt to any canonical game JSON missing one.

Templates are chosen by game_type; if a game has skill_tags or learning_objectives
those are spliced into the prompt for specificity.
"""
import json
import os
import sys

GAMES_DIR = os.path.join(os.path.dirname(__file__), "..", "games")

# game_type -> reflection prompt template.
TEMPLATES = {
    "story_branching": "Looking back at the choices you made, which one felt hardest and why? What would you do differently if you replayed?",
    "rounds": "Which decision in this run shifted your outcome the most? What signal told you it was the right call?",
    "negotiation": "Where did you give ground, and where did you hold it? What did the other side teach you about your own priorities?",
    "debate": "Which argument from the other side actually made you reconsider? Why?",
    "board": "Which turn was your turning point — and was it skill, luck, or planning?",
    "card": "Which card or play tested your patience the most? What did you learn about reading the table?",
    "card_board": "When did you feel most in control, and when did chance push back? What does that tell you about strategy vs. luck?",
    "auction": "What was your true ceiling, and did you stick to it under pressure? What changed it?",
    "tower_defense": "Where did your defenses bend before they broke? What would you reinforce first next time?",
    "strategy_grid": "Which move opened the board for you, and which closed your options? Why?",
    "chess_strategy": "What pattern did your opponent rely on, and how did you counter (or fail to)?",
    "go_territory": "Where did you trade influence for territory? Was it worth it?",
    "reversi": "Which flip changed the shape of the game most? What did you not see coming?",
    "puzzle_match": "Which pattern took longest to spot? How will you train your eye for it next time?",
    "ai_arena": "How did you adapt as the AI shifted strategies? Which adaptation worked best?",
    "simulation": "Which lever, if you'd moved it earlier, would have changed your outcome the most?",
    "minigame": "What pattern did you start to recognize as you played? How will you use it next time?",
    "lab_titration": "What did the color change moment teach you about the equivalence point you couldn't get from a textbook?",
    "music_match": "Which pitch did you have to listen for hardest? What clue helped you decide?",
    "mystery_room": "Which clue felt useless until it suddenly mattered? What does that tell you about how you investigate?",
    "escape_room": "Which puzzle had you stuck — and what unblocked you?",
    "rpg": "Which choice for your character felt most true to who they're becoming? Why?",
}
DEFAULT = "What's one thing you'll take from this game into a real-world situation this week?"


def pick_prompt(data: dict) -> str:
    gt = data.get("game_type", "")
    return TEMPLATES.get(gt, DEFAULT)


def main():
    written = 0
    for fn in sorted(os.listdir(GAMES_DIR)):
        if not fn.endswith(".json") or ".bak" in fn:
            continue
        path = os.path.join(GAMES_DIR, fn)
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"SKIP {fn}: {e}", file=sys.stderr)
            continue
        if data.get("reflection_prompt"):
            continue
        data["reflection_prompt"] = pick_prompt(data)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        written += 1
        print(f"updated {fn}")
    print(f"\nTotal updated: {written}")


if __name__ == "__main__":
    main()
