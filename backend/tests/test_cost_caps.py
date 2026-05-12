"""Cost-cap enforcement for usage-limited module features."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from modules_engine import check_and_increment_usage, UsageLimitExceeded


def test_first_call_allowed(tmp_path, monkeypatch):
    monkeypatch.setenv("MODULE_PROGRESS_FILE", str(tmp_path / "p.json"))
    n = check_and_increment_usage("u1", "mod1", "pitch_coach_runs", limit=3)
    assert n == 1


def test_third_call_allowed_fourth_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("MODULE_PROGRESS_FILE", str(tmp_path / "p.json"))
    for _ in range(3):
        check_and_increment_usage("u1", "mod1", "pitch_coach_runs", limit=3)
    with pytest.raises(UsageLimitExceeded):
        check_and_increment_usage("u1", "mod1", "pitch_coach_runs", limit=3)
