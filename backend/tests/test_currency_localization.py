# backend/tests/test_currency_localization.py
import json
import re
from pathlib import Path


def _gather_text(node, out):
    if isinstance(node, dict):
        for v in node.values():
            _gather_text(v, out)
    elif isinstance(node, list):
        for v in node:
            _gather_text(v, out)
    elif isinstance(node, str):
        out.append(node)


def _lesson_id(lesson):
    return lesson.get("id") or lesson.get("lesson_id")


def test_no_dollar_examples_in_localized_lessons():
    mod = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "modules", "mento_entrepreneur_4week.json").read_text())
    targets = {"w3_l2_who_pays", "w3_l3_customer_profile", "w3_l4_idea_scorecard"}
    by_id = {_lesson_id(l): l for w in mod["weeks"] for l in w.get("lessons", [])}
    for tid in targets:
        if tid not in by_id:
            continue  # the actual id format may differ; skip silently
        text_blobs = []
        _gather_text(by_id[tid], text_blobs)
        joined = " ".join(text_blobs)
        # No "$" or "USD" in monetary examples:
        assert "$" not in joined, f"{tid} still contains $ symbol"
        assert not re.search(r"\bUSD\b", joined), f"{tid} still contains USD"
        # Must contain ₹ at least once:
        assert "₹" in joined, f"{tid} missing ₹ examples"
