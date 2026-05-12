# backend/tests/test_failure_museum.py
import json
from pathlib import Path

EXPECTED = {"failure_stayzilla", "failure_doodhwala", "failure_tinyowl",
            "failure_dazo", "failure_askme", "failure_housing"}


def _lesson_id(lesson):
    return lesson.get("id") or lesson.get("lesson_id")


def test_failure_cards_present():
    mod = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "modules", "mento_entrepreneur_4week.json").read_text())
    all_ids = {_lesson_id(l) for w in mod["weeks"] for l in w.get("lessons", [])}
    missing = EXPECTED - all_ids
    assert not missing, f"missing failure cards: {missing}"
    by_id = {_lesson_id(l): l for w in mod["weeks"] for l in w.get("lessons", [])}
    for fid in EXPECTED:
        l = by_id[fid]
        assert l["type"] == "failure_card"
        for k in ("company_name", "what_they_tried", "why_they_failed", "lesson_text"):
            assert l.get(k), f"{fid} missing {k}"
