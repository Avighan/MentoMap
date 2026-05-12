# backend/tests/test_daily_dispatch_content.py
import json
from pathlib import Path


def test_dispatch_has_28_messages():
    p = Path(__file__).resolve().parents[1] / "data" / "module_daily_dispatch" / "mento_entrepreneur_4week.json"
    msgs = json.loads(p.read_text())
    assert isinstance(msgs, list)
    assert len(msgs) == 28
    seen_days = set()
    for m in msgs:
        assert "day" in m and 1 <= m["day"] <= 28
        assert m["day"] not in seen_days, f"duplicate day {m['day']}"
        seen_days.add(m["day"])
        assert m.get("title")
        assert m.get("body")
        assert len(m["body"]) <= 280, f"day {m['day']} body too long for WhatsApp/notif"
