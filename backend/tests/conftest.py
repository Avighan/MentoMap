"""Shared pytest configuration for backend unit/integration tests.

No global monkeypatching here: `schemas.validate_bundle` already wraps each
game's per-type validation in a try/except that logs a warning instead of
raising (see backend/schemas.py), so unrecognised game_type values do not
prevent `from app import app` from succeeding. A previous version of this
file additionally replaced `schemas.validate_bundle` with a permissive stub
for the whole test session; that stub predated (or was never cleaned up
after) the try/except wrapper landed, and its only effect now was to break
backend/tests/test_schemas.py's own tests of validate_bundle's raise
behavior, since `from schemas import validate_bundle` in that module bound
to the stub instead of the real function.
"""
