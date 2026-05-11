"""
delete_unused_engines.py — idempotent cleanup script for unused engine files.

Usage:
    python scripts/delete_unused_engines.py /path/to/unused_engines.txt

The list file format (as produced by audit_engine_usage.py):
  - Lines starting with '#' are comments.
  - Lines that are not valid Python identifiers (headers, blanks, numbers) are skipped.
  - Each valid line is treated as an engine module name (no .py extension).

What this script does:
  1. Deletes backend/engines/<name>.py for each engine in the list (if it exists).
  2. Removes any line from backend/engines/__init__.py matching
         ^\s*from \.<name> import .*$
     for each engine name, preserving all other lines verbatim.
  3. Prints a summary.

What this script does NOT touch:
  - backend/games/
  - backend/routes/
  - Any file outside backend/engines/ and backend/engines/__init__.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def _is_valid_identifier(s: str) -> bool:
    """Return True if s looks like a Python module name (identifier)."""
    return bool(re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', s.strip()))


def load_engine_names(list_path: Path) -> list[str]:
    """Parse the engine list file, skipping headers, blanks, and comments."""
    names = []
    for raw_line in list_path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        if not _is_valid_identifier(line):
            # Skip header lines like "Total engines: 94" or "Unused (...): 26"
            continue
        names.append(line)
    return names


def delete_engines(engine_names: list[str], backend_dir: Path) -> tuple[int, int]:
    """
    Delete engine .py files and remove matching lines from __init__.py.

    Returns:
        (files_deleted, init_lines_removed)
    """
    engines_dir = backend_dir / "engines"
    init_path = engines_dir / "__init__.py"

    files_deleted = 0
    init_lines_removed = 0

    # --- Step 1: delete the .py files ---
    for name in engine_names:
        target = engines_dir / f"{name}.py"
        if target.exists():
            target.unlink()
            print(f"  deleted: engines/{name}.py")
            files_deleted += 1
        else:
            print(f"  skip (not found): engines/{name}.py")

    # --- Step 2: strip matching lines from __init__.py ---
    if not init_path.exists():
        print(f"  WARNING: {init_path} not found; skipping __init__.py edit.")
        return files_deleted, init_lines_removed

    original_lines = init_path.read_text().splitlines(keepends=True)

    # Build a set of patterns — one per engine name
    # Match: optional whitespace, "from .", engine_name, " import ", anything
    patterns = {
        name: re.compile(r'^\s*from\s+\.' + re.escape(name) + r'\s+import\s+.*$')
        for name in engine_names
    }

    kept_lines: list[str] = []
    for line in original_lines:
        line_stripped = line.rstrip('\n').rstrip('\r')
        removed = False
        for name, pat in patterns.items():
            if pat.match(line_stripped):
                print(f"  removed from __init__.py: {line_stripped!r}")
                init_lines_removed += 1
                removed = True
                break
        if not removed:
            kept_lines.append(line)

    if init_lines_removed > 0:
        init_path.write_text("".join(kept_lines))

    return files_deleted, init_lines_removed


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/delete_unused_engines.py <list_file>", file=sys.stderr)
        sys.exit(1)

    list_path = Path(sys.argv[1])
    if not list_path.exists():
        print(f"ERROR: list file not found: {list_path}", file=sys.stderr)
        sys.exit(1)

    # Locate backend/ relative to this script (scripts/delete_unused_engines.py → backend/)
    backend_dir = Path(__file__).parent.parent

    print(f"Loading engine list from: {list_path}")
    engine_names = load_engine_names(list_path)
    print(f"  Found {len(engine_names)} engine name(s) to process:\n    " + ", ".join(engine_names))
    print()

    print("Processing deletions...")
    files_deleted, init_lines_removed = delete_engines(engine_names, backend_dir)

    print()
    print("=" * 60)
    print(f"Summary:")
    print(f"  Engine .py files deleted : {files_deleted}")
    print(f"  __init__.py lines removed: {init_lines_removed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
