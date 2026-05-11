import json, os, pytest

NEW_GAMES = [
    "kids-kindness-quest.json", "kids-piggy-bank.json", "kids-share-the-toys.json",
    "kids-feelings-detective.json", "kids-tiny-leader.json",
    "pro-difficult-1on1.json", "pro-stakeholder-pushback.json", "pro-burnout-recovery.json",
    "pro-cross-functional-blocker.json", "pro-promotion-case.json",
]
GAMES_DIR = os.path.join(os.path.dirname(__file__), "..", "games")

@pytest.mark.parametrize("fn", NEW_GAMES)
def test_new_game_present_and_valid(fn):
    path = os.path.join(GAMES_DIR, fn)
    assert os.path.exists(path), f"missing {fn}"
    with open(path) as f:
        data = json.load(f)
    for k in ("game_id", "game_type", "title", "target_age", "grade", "learning_objectives", "reflection_prompt"):
        assert data.get(k), f"{fn}: missing {k}"
    assert data["target_audience"] in ("kids", "students", "professionals", "young_adults")
