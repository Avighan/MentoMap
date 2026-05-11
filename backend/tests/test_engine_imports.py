"""Smoke test: every engine listed as 'in use' actually imports cleanly."""
import importlib, glob, os

ENGINES_DIR = os.path.join(os.path.dirname(__file__), "..", "engines")

def test_all_engines_in_init_importable():
    init_path = os.path.join(ENGINES_DIR, "__init__.py")
    with open(init_path) as f:
        src = f.read()
    # naive parse: lines like "from .foo_engine import Foo"
    for line in src.splitlines():
        line = line.strip()
        if line.startswith("from .") and " import " in line:
            mod = line.split(" import ")[0].replace("from .", "engines.")
            importlib.import_module(mod)
