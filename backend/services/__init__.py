"""Services layer - business logic, data operations, and Phase A audio/module services.

The game/round/state/choice/leaderboard services are imported defensively so
this package still works in branch contexts where only some service modules
exist on disk (Phase A/B development).  At production runtime on main, all
modules are present and exports succeed normally.
"""
try:
    from .game_service import game_service  # noqa: F401
    from .round_service import build_round_payload  # noqa: F401
    from .state_service import state_service  # noqa: F401
    from .choice_service import choice_service  # noqa: F401
    from .leaderboard_service import leaderboard_service  # noqa: F401

    __all__ = [
        "game_service",
        "build_round_payload",
        "state_service",
        "choice_service",
        "leaderboard_service",
    ]
except ImportError:
    __all__ = []
