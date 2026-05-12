import json
from pathlib import Path


def test_each_week_has_micro_quest():
    p = Path(__file__).resolve().parents[1] / "modules" / "mento_entrepreneur_4week.json"
    mod = json.loads(p.read_text())
    weeks = mod["weeks"]
    expected = {
        1: "w1_quest_one_complaint",
        2: "w2_quest_one_why",
        3: "w3_quest_one_customer",
        4: "w4_quest_one_pitch",
    }
    for i, week in enumerate(weeks, start=1):
        # Module schema uses `lesson_id` as the canonical key — match it here.
        ids = [l.get("lesson_id") or l.get("id") for l in week.get("lessons", [])]
        assert expected[i] in ids, f"week {i} missing quest {expected[i]} — got {ids}"
        # Find it and check type
        quest = next(
            l for l in week["lessons"]
            if (l.get("lesson_id") or l.get("id")) == expected[i]
        )
        assert quest["type"] == "micro_quest"
        assert quest.get("prompt"), f"{expected[i]} missing prompt"
