"""Shared exception types for the run-storage layer.

`storage.py` raises these so callers across `app.py` and `routes/*` can
catch storage failures distinctly from generic `KeyError`s. Kept in their
own module (rather than inside `storage.py`) so other modules can import
just the exception types without pulling in the full storage implementation.
"""


class StorageIOError(Exception):
    """Raised when a run cannot be read from or written to disk."""


class SessionNotFoundError(KeyError):
    """Raised when a run_id has no corresponding stored session.

    Subclasses KeyError so existing `except KeyError` call sites across the
    codebase keep working unchanged even where they haven't been updated to
    catch this type explicitly.
    """

    def __init__(self, run_id: str):
        super().__init__(run_id)
        self.run_id = run_id

    def __str__(self):
        return f"No session found for run_id={self.run_id!r}"


class SessionExpiredError(Exception):
    """Raised when a run_id exists but its session has passed its TTL."""

    def __init__(self, run_id: str):
        super().__init__(run_id)
        self.run_id = run_id

    def __str__(self):
        return f"Session for run_id={self.run_id!r} has expired"
