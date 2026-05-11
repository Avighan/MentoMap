"""
Regression baseline for module loading — Task 0, Phase A.

These tests must always pass.  Any subsequent task that changes module
loading, file structure, or the mento_entrepreneur_4week content must
keep these green (or explicitly update the assertions with a documented
reason).

NOTE: The loader function is `get_module` (not `load_module`) as defined
in backend/modules_engine.py.
"""
import json
from pathlib import Path

from modules_engine import get_module


def test_mento_entrepreneur_loads_unchanged():
    """Baseline: module loads with same 33 lessons, 4 weeks, no errors."""
    module = get_module("mento_entrepreneur_4week")
    assert module is not None
    assert module["module_id"] == "mento_entrepreneur_4week"
    weeks = module["weeks"]
    assert len(weeks) == 4
    total_lessons = sum(len(w["lessons"]) for w in weeks)
    assert total_lessons == 33


def test_other_modules_load_unchanged():
    """All other modules in backend/modules/ must still load."""
    modules_dir = Path(__file__).resolve().parent.parent / "modules"
    json_files = [f for f in modules_dir.glob("*.json") if not f.name.startswith(".")]
    for f in json_files:
        with open(f) as fh:
            data = json.load(fh)
        assert "module_id" in data, f"{f} missing module_id"
