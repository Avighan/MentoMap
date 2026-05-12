# backend/tests/test_indian_case_studies.py
import json
from pathlib import Path

EXPECTED_FOUNDERS = {
    "case_study_vembu", "case_study_nayar", "case_study_oyo",
    "case_study_byju", "case_study_kunal_shah", "case_study_ghazal_alagh",
    "case_study_bhavish", "case_study_neighborhood",
}


def _lesson_id(lesson):
    return lesson.get("id") or lesson.get("lesson_id")


def test_all_8_founder_cards_present():
    mod = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "modules", "mento_entrepreneur_4week.json").read_text())
    all_ids = {_lesson_id(l) for w in mod["weeks"] for l in w.get("lessons", [])}
    missing = EXPECTED_FOUNDERS - all_ids
    assert not missing, f"missing case study lessons: {missing}"
    # Each must be type case_study_card with required fields:
    by_id = {_lesson_id(l): l for w in mod["weeks"] for l in w.get("lessons", [])}
    for fid in EXPECTED_FOUNDERS:
        l = by_id[fid]
        assert l["type"] == "case_study_card"
        for k in ("founder_name", "backstory", "takeaway", "reflection_prompt"):
            assert l.get(k), f"{fid} missing {k}"
