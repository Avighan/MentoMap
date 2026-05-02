import json
import os
import pytest

SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "snapshots")
REFERENCE_GAMES = [
    "cfo-quarterly-close",
    "lemonade-empire-enhanced",
    "founders-gambit",
    "series-a-founders-journey",
    "project-management-mastery",
    "the-startup-decision",
    "climate-champions",
    "city-mayor",
]


@pytest.mark.parametrize("game_id", REFERENCE_GAMES)
def test_snapshot_exists(game_id):
    path = os.path.join(SNAPSHOT_DIR, f"{game_id}_v1.json")
    assert os.path.exists(path), f"Missing baseline snapshot: {path}"
    with open(path) as f:
        snap = json.load(f)
    assert "final_dimension_scores" in snap
    assert "kpis" in snap
    assert "total_score" in snap
    assert "completion_rate" in snap
    assert "seed" in snap
