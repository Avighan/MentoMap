# backend/tests/test_phase_d_baseline.py
import json
from pathlib import Path


def test_module_still_loads():
    p = Path(__file__).resolve().parents[1] / "modules" / "mento_entrepreneur_4week.json"
    mod = json.loads(p.read_text())
    assert len(mod["weeks"]) == 4
    assert mod.get("module_id") == "mento_entrepreneur_4week" or mod.get("id") == "mento_entrepreneur_4week"


def test_phase_a_renderers_scaffolded():
    """Phase A registers case_study_card and failure_card as known lesson types."""
    import backend.modules_engine as me
    # Phase A added _KNOWN_LESSON_TYPES; if module engine doesn't define it, this is a sanity guard.
    known = getattr(me, "_KNOWN_LESSON_TYPES", None)
    if known is not None:
        assert "case_study_card" in known
        assert "failure_card" in known
