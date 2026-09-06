"""
API route for the HBR/CapSim-parity "decision panel" engine family:
decision_panel_engine, competitor_ai_engine, expert_debrief_engine.

Why these three live here, grounded in grep evidence:

  - engines/decision_panel_engine.py docstring: "Pure stdlib. Not yet
    registered in engines/__init__.py — wiring lands in a later phase
    when callers in app.py adopt it."
  - engines/competitor_ai_engine.py docstring: "Wiring point: core/rounds.py
    calls tick() after the player's decision_panel.controls have been
    applied to state." (`core/rounds.py` does not exist in this checkout.)
  - engines/expert_debrief_engine.py docstring: "Wiring lives in
    executive_ux.build_executive_payload (per-round, like decision_panel)."
  - `grep -rl decision_panel_engine|competitor_ai_engine|expert_debrief_engine
    backend/*.py backend/routes/*.py` (before this file existed) turned up
    ONLY engines/executive_ux.py (read-only payload composition, already
    wired straight into app.py) and unit tests — never a Flask route.
  - frontend-react/src/components/game/exec/DecisionPanelWidget.jsx:
    "On Submit, calls onSubmit({control_id: value}) — the parent (typically
    GamePlayPage) forwards to /api/run/<id>/decision-panel"

So the read side (payload composition) is already wired elsewhere; the one
write action missing end-to-end is the player's per-round decision-panel
submission, which this blueprint provides. Confirmed by the frontend
comment: POST /api/run/<run_id>/decision-panel.

NOTE: `engines/executive_ux.py` itself currently fails to import (it pulls
in market_engine/org_engine/corporate_board_engine/compliance_engine/
decision_engine/crisis_engine/intrapreneur_engine/stochastic_engine/
market_actors_engine — none of which exist in this checkout). This module
deliberately imports only the three engines above directly (each is
pure-stdlib) so it does not inherit that breakage.
"""
from typing import Any, Dict, Optional

from flask import Blueprint, jsonify, request

from storage import get_run, update_run
from game_storage import load_game
from storage_interface import SessionNotFoundError, SessionExpiredError, StorageIOError

from engines.decision_panel_engine import DecisionPanelEngine, build_decision_panel_payload
from engines.competitor_ai_engine import CompetitorAIEngine, get_competitor_config, build_competitor_payload
from engines.expert_debrief_engine import build_expert_debrief_payload


engines_bp = Blueprint("engines", __name__, url_prefix="/api/run")


class _StateProxy:
    """Adapts run['state'] to the getattr/setattr interface these engines
    are written against (per storage.py's docstring, some callers store a
    typed state object rather than a plain dict; after a JSON round-trip
    through storage.py it comes back as a plain dict). Reads/writes pass
    straight through to the same underlying dict so mutations land back
    in the run that gets persisted.
    """

    def __init__(self, state):
        object.__setattr__(self, "_state", state)

    def __getattr__(self, name):
        state = object.__getattribute__(self, "_state")
        if isinstance(state, dict):
            if name in state:
                return state[name]
            raise AttributeError(name)
        return getattr(state, name)

    def __setattr__(self, name, value):
        state = object.__getattribute__(self, "_state")
        if isinstance(state, dict):
            state[name] = value
        else:
            setattr(state, name, value)


def _load_run(run_id: str):
    try:
        run = get_run(run_id)
    except SessionNotFoundError:
        return None, (jsonify({"error": "Run not found"}), 404)
    except SessionExpiredError:
        return None, (jsonify({"error": "Run has expired"}), 410)
    except StorageIOError as e:
        return None, (jsonify({"error": str(e)}), 500)

    if "game" not in run or run.get("game") is None:
        run["game"] = load_game(run.get("game_id", ""))
    if not run.get("game"):
        return None, (jsonify({"error": "Game data not found"}), 404)
    return run, None


def _current_round(run: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    game = run.get("game") or {}
    rounds = game.get("rounds") or []
    if not rounds:
        return None
    state = run.get("state")
    raw_idx = state.get("round_index", 0) if isinstance(state, dict) else getattr(state, "round_index", 0)
    try:
        idx = int(raw_idx or 0)
    except (TypeError, ValueError):
        idx = 0
    idx = max(0, min(idx, len(rounds) - 1))
    return rounds[idx]


def _synth_competitors(cfg: Dict[str, Any]) -> list:
    """Same defaults build_competitor_payload's fallback uses for round 0,
    kept here so tick() has a roster to react against even before any
    competitor_runtime snapshot exists."""
    out = []
    for f in (cfg.get("firms") or []):
        out.append({
            "id": f.get("id"),
            "name": f.get("name") or f.get("id", "Firm"),
            "persona": f.get("persona", "neutral"),
            "market_share": float(f.get("starting_market_share", 0.25) or 0.25),
            "price": float(f.get("starting_price", 100.0) or 100.0),
            "marketing_spend": float(f.get("starting_marketing", 1_000_000) or 1_000_000),
            "r_and_d_alloc": float(f.get("starting_rd_alloc", 0.20) or 0.20),
        })
    return out


@engines_bp.route("/<run_id>/decision-panel", methods=["POST"])
def decision_panel_submit(run_id):
    """Commit the player's per-round decision-panel submission.

    Body is either `{control_id: value, ...}` directly (what
    DecisionPanelWidget.jsx's onSubmit(draft) sends) or `{"submission": {...}}`.

    Validates + applies the submission (decision_panel_engine.commit_round),
    records it on state._decision_panel_submission[round_id], then — if the
    game also declares competitor_ai — runs one CompetitorAIEngine.tick()
    using the levers the submission just wrote (price / marketing_spend /
    r_and_d_alloc), storing the result on state._competitor_runtime so
    build_competitor_payload and build_expert_debrief_payload (which gates
    on this same submission) reflect it immediately.
    """
    run, err = _load_run(run_id)
    if err:
        return err

    current_round = _current_round(run)
    if not isinstance(current_round, dict):
        return jsonify({"error": "Run has no current round"}), 400

    panel_cfg = current_round.get("decision_panel") or {}
    controls = panel_cfg.get("controls")
    if not isinstance(controls, list) or not controls:
        return jsonify({"error": "Current round has no decision_panel configured"}), 400

    body = request.get_json(silent=True) or {}
    submission = body.get("submission") if isinstance(body.get("submission"), dict) else body

    if run.get("state") is None:
        run["state"] = dict((run["game"] or {}).get("initial_state") or {})
    state = run["state"]
    if not isinstance(state, dict):
        return jsonify({"error": "Run state is not in a dict-compatible shape for this engine"}), 500

    engine = DecisionPanelEngine()
    try:
        result = engine.commit_round(state, controls, submission)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    proxy = _StateProxy(state)
    round_id = current_round.get("id")
    submissions = dict(getattr(proxy, "_decision_panel_submission", None) or {})
    submissions[round_id] = result["applied"]
    proxy._decision_panel_submission = submissions

    competitor_board = None
    competitor_cfg = get_competitor_config(run["game"])
    if competitor_cfg:
        try:
            runtime = getattr(proxy, "_competitor_runtime", None) or {}
            competitors_in = runtime.get("competitors") or _synth_competitors(competitor_cfg)
            player_in = runtime.get("player") or {}
            player_move = {
                k: state[k] for k in ("price", "marketing_spend", "r_and_d_alloc") if k in state
            }
            tick_engine = CompetitorAIEngine()
            tick_result = tick_engine.tick(
                {"competitors": competitors_in, "player": player_in},
                player_move=player_move,
                seed=competitor_cfg.get("seed"),
            )
            proxy._competitor_runtime = {
                "competitors": tick_result["competitors"],
                "player": tick_result["player"],
                "competitor_moves": tick_result["competitor_moves"],
            }
            competitor_board = build_competitor_payload(proxy, run["game"])
        except Exception as e:  # noqa: BLE001 — competitor AI is a bonus subsystem
            competitor_board = {"error": f"Competitor AI tick failed: {e}"}

    update_run(run_id, run)

    return jsonify({
        "success": True,
        "applied": result["applied"],
        "drift": result["drift"],
        "decision_panel": build_decision_panel_payload(proxy, current_round),
        "competitor_board": competitor_board,
        "expert_debrief": build_expert_debrief_payload(proxy, current_round),
    })
