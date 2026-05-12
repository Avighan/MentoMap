# backend/tests/test_regulatory_primer.py
import json
from pathlib import Path

EXPECTED = {"w4_bonus_udyam", "w4_bonus_gst", "w4_bonus_bank_account"}


def _lesson_id(lesson):
    return lesson.get("id") or lesson.get("lesson_id")


def test_regulatory_primer_lessons():
    mod = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "modules", "mento_entrepreneur_4week.json").read_text())
    all_ids = {_lesson_id(l) for w in mod["weeks"] for l in w.get("lessons", [])}
    assert EXPECTED.issubset(all_ids), f"missing: {EXPECTED - all_ids}"
    by_id = {_lesson_id(l): l for w in mod["weeks"] for l in w.get("lessons", [])}
    for eid in EXPECTED:
        l = by_id[eid]
        assert l["type"] == "audio_lesson", f"{eid} should be audio_lesson"
        # Optional / does not gate completion:
        assert l.get("optional") is True, f"{eid} must be marked optional"
        # Must carry a disclaimer:
        body = json.dumps(l, ensure_ascii=False)
        assert "general overview" in body.lower() or "not legal advice" in body.lower(), \
            f"{eid} missing disclaimer"
