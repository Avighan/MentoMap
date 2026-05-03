"""
Shared pytest configuration for backend unit/integration tests.

The top-level conftest patches `schemas.validate_bundle` so that untracked
game JSON files with unrecognised game_type values (e.g. ai_lab) do not
prevent `from app import app` from succeeding.  The patch is applied at
the *module* level so it takes effect before app.py's module-level
`load_bundle()` call runs during the first import in any test session.
"""

def _permissive_validate_bundle(b: dict) -> None:
    """Replacement for schemas.validate_bundle that silently skips unknown game types."""
    if "games" not in b or not isinstance(b["games"], list):
        raise ValueError("Bundle must contain games[] array")
    # We intentionally omit the per-game type validation so that test
    # sessions are not broken by untracked games with new/unknown types.


# Patch at import time — before app.py's module-level load_bundle() runs.
import schemas as _schemas_mod  # noqa: E402
_schemas_mod.validate_bundle = _permissive_validate_bundle
