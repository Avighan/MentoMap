"""
Decision Engine — executive-tier decision-quality scoring and rationale /
calibration tracking subsystem for simulation games.

Activated only when game JSON declares `simulation_config.decision_quality`.
When absent, `build_decision_payload` returns None and existing games are
unaffected.

Schema (verbatim, from games/series-a-founders-journey.json, a real
committed example):

    simulation_config.decision_quality = {
      "log_decisions": true,
      "track_calibration": true
    }

Decision history is authored elsewhere (choice-effect handlers) into:

    state._decision_log = [
      {"round_id": "q4_security_incident", "choice_id": "full_disclosure",
       "rationale": "Trust is the moat", "confidence_pct": 80,
       "quality_score": 85,               # optional, 0-100
       "outcome_correct": true,           # optional, for calibration
       "skill_tags": ["governance_judgment", "decision_quality"]}
    ]

Every field on a log entry beyond round_id/choice_id is optional — this
engine degrades gracefully as entries fill in over the course of a game.

All helpers are pure functions of (state, game) — they read state, never
mutate it.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


# ────────────────────────────────────────────────────────────────────
# Schema activation
# ────────────────────────────────────────────────────────────────────

def get_decision_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the decision_quality block, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("decision_quality")
    if not isinstance(cfg, dict):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Sub-computations
# ────────────────────────────────────────────────────────────────────

def _decision_log(state: Any) -> List[Dict[str, Any]]:
    log = _get(state, "_decision_log", []) or []
    return [d for d in log if isinstance(d, dict)]


def compute_decision_quality(state: Any) -> Optional[Dict[str, Any]]:
    log = _decision_log(state)
    if not log:
        return None
    scored = [d for d in log if isinstance(d.get("quality_score"), (int, float))]
    avg_quality = (sum(d["quality_score"] for d in scored) / len(scored)) if scored else None
    tag_totals: Dict[str, List[float]] = {}
    for d in log:
        for tag in (d.get("skill_tags") or []):
            if isinstance(d.get("quality_score"), (int, float)):
                tag_totals.setdefault(tag, []).append(d["quality_score"])
    by_skill_tag = {
        tag: round(sum(vals) / len(vals), 1) for tag, vals in tag_totals.items() if vals
    }
    return {
        "decisions_logged": len(log),
        "decisions_scored": len(scored),
        "avg_quality_score": round(avg_quality, 1) if avg_quality is not None else None,
        "by_skill_tag": by_skill_tag or None,
    }


def compute_calibration(state: Any) -> Optional[Dict[str, Any]]:
    """Calibration: does stated confidence match realized correctness?

    Uses a simple Brier-score-style measure over entries carrying both
    confidence_pct and outcome_correct.
    """
    log = _decision_log(state)
    calibratable = [
        d for d in log
        if isinstance(d.get("confidence_pct"), (int, float)) and isinstance(d.get("outcome_correct"), bool)
    ]
    if not calibratable:
        return None
    errors = []
    for d in calibratable:
        p = max(0.0, min(100.0, float(d["confidence_pct"]))) / 100.0
        outcome = 1.0 if d["outcome_correct"] else 0.0
        errors.append((p - outcome) ** 2)
    brier = sum(errors) / len(errors)
    calibration_score = round((1.0 - brier) * 100.0, 1)  # 100 = perfectly calibrated
    avg_confidence = sum(d["confidence_pct"] for d in calibratable) / len(calibratable)
    correct_pct = sum(1 for d in calibratable if d["outcome_correct"]) / len(calibratable) * 100.0
    bias = "overconfident" if avg_confidence > correct_pct + 10 else (
        "underconfident" if avg_confidence < correct_pct - 10 else "well_calibrated"
    )
    return {
        "n": len(calibratable),
        "brier_score": round(brier, 3),
        "calibration_score": calibration_score,
        "avg_stated_confidence_pct": round(avg_confidence, 1),
        "realized_correct_pct": round(correct_pct, 1),
        "bias": bias,
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_decision_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    decision_quality isn't configured for this game."""
    cfg = get_decision_config(game)
    if not cfg:
        return None
    payload: Dict[str, Any] = {
        "log_decisions": bool(cfg.get("log_decisions", True)),
        "track_calibration": bool(cfg.get("track_calibration", False)),
        "quality": None,
        "calibration": None,
        "recent_decisions": None,
    }
    try:
        payload["quality"] = compute_decision_quality(state)
    except Exception:
        pass
    try:
        if payload["track_calibration"]:
            payload["calibration"] = compute_calibration(state)
    except Exception:
        pass
    try:
        log = _decision_log(state)
        payload["recent_decisions"] = [
            {
                "round_id": d.get("round_id"),
                "choice_id": d.get("choice_id"),
                "rationale": d.get("rationale"),
                "confidence_pct": d.get("confidence_pct"),
                "quality_score": d.get("quality_score"),
            }
            for d in log[-5:]
        ] or None
    except Exception:
        pass
    return payload
