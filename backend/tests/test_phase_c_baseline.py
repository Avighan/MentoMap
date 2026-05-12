"""Phase C regression baseline. Runs before any C task to confirm Phase A landed and module is healthy."""
import json
from pathlib import Path


def test_phase_a_artifacts_exist():
    """Phase A must have shipped before C touches anything."""
    root = Path(__file__).resolve().parents[1]
    assert (root / "services" / "tts_service.py").exists(), "Phase A TTS service missing"
    assert (root / "assets" / "module_images" / "mento_entrepreneur_4week").exists(), \
        "Phase A image self-host did not run"


def test_module_loads_and_has_32_lessons():
    root = Path(__file__).resolve().parents[1]
    mod_path = root / "modules" / "mento_entrepreneur_4week.json"
    module = json.loads(mod_path.read_text())
    lesson_count = sum(len(w.get("lessons", [])) for w in module["weeks"])
    assert lesson_count >= 32, f"Expected ≥32 lessons, got {lesson_count}"
    assert len(module["weeks"]) == 4
