"""Find engines under backend/engines/ that are not imported anywhere outside themselves.

A 'use' is any of:
 - an `import` or `from` line in a non-test, non-engine .py file under backend/
 - a string literal containing the engine module name in a game JSON or schemas.py
"""
import os, re, json, glob

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENGINES_DIR = os.path.join(BACKEND, "engines")
GAMES_DIR = os.path.join(BACKEND, "games")

def list_engines():
    out = []
    for fn in os.listdir(ENGINES_DIR):
        if fn.endswith(".py") and fn not in ("__init__.py",):
            out.append(fn[:-3])  # module name without .py
    return sorted(out)

def find_usages(engine_mod: str) -> list:
    """Return list of file paths that reference engine_mod outside its own file and tests."""
    hits = []
    pat_import = re.compile(rf"\b(import|from)\s+(\.|engines\.){engine_mod}\b")
    pat_string = re.compile(rf"\b{re.escape(engine_mod)}\b")
    for root, _, files in os.walk(BACKEND):
        # skip venvs, the engine's own file, and engine tests
        if "/.venv" in root or "/__pycache__" in root or "/.venv_corrupted_backup" in root:
            continue
        for fn in files:
            path = os.path.join(root, fn)
            rel = os.path.relpath(path, BACKEND)
            if rel == f"engines/{engine_mod}.py":
                continue
            if rel.startswith("tests/") or rel.startswith("test_") or "/test_" in rel or rel.startswith("scripts/audit_engine_usage"):
                continue
            try:
                if fn.endswith(".py"):
                    with open(path) as f:
                        text = f.read()
                    if pat_import.search(text):
                        hits.append(rel)
                elif fn.endswith(".json") and root.startswith(GAMES_DIR):
                    with open(path) as f:
                        text = f.read()
                    if pat_string.search(text):
                        hits.append(rel)
            except Exception:
                pass
    return hits

def main():
    engines = list_engines()
    unused = []
    for e in engines:
        if not find_usages(e):
            unused.append(e)
    print(f"Total engines: {len(engines)}")
    print(f"Unused (no import outside self/tests, no JSON ref): {len(unused)}\n")
    for e in unused:
        print(e)

if __name__ == "__main__":
    main()
