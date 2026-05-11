import json
import os
import glob
import pytest

GAMES = glob.glob(
    os.path.join(os.path.dirname(__file__), "..", "games", "*.json")
)
CANONICAL = [g for g in GAMES if ".bak" not in g]


@pytest.mark.parametrize("path", CANONICAL)
def test_reflection_prompt_present_and_valid(path):
    with open(path) as f:
        data = json.load(f)
    rp = data.get("reflection_prompt")
    assert rp, f"{os.path.basename(path)}: missing reflection_prompt"
    assert isinstance(rp, str), f"{os.path.basename(path)}: must be string"
    assert (
        20 <= len(rp) <= 400
    ), f"{os.path.basename(path)}: length {len(rp)} out of [20,400]"
    assert "?" in rp, f"{os.path.basename(path)}: should be a question"
