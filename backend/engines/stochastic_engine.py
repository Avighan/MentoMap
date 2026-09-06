"""
Stochastic Engine — executive-tier Monte-Carlo forecast bands + forecast
calibration scoring subsystem for simulation games.

Activated only when game JSON declares `simulation_config.stochastic`, and
its two sub-features gate independently off the same block's two flags —
hence two separate config getters:

    simulation_config.stochastic = {
      "enabled": true,               # gates get_stochastic_config (forecast bands)
      "calibration_enabled": true,   # gates get_calibration_config (forecast scoring)
      "confidence_pct": 80,
      "default_distribution": "triangular"   # "triangular" | "normal"
    }

This schema is verbatim from games/series-a-founders-journey.json and
games/the-founders-gauntlet.json, real committed examples.

Forecast-band Monte Carlo runs over a single headline metric — prefers
state.arr, falls back to state.monthly_revenue * 12, then state.money — using
`n_sims` per-period draws from the configured distribution.

Forecast calibration reads authored predictions from:

    state._forecast_log = [
      {"label": "Q4 ARR", "predicted": 2_000_000, "confidence_pct": 80,
       "actual": 1_850_000}
    ]
`actual` is optional — entries without it are excluded from the score but
still surfaced as open forecasts.

All helpers are pure functions of (state, game) — they read state, never
mutate it, except `random` draws which are seeded per call for
reproducibility within a single payload build.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


def _get(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


# ────────────────────────────────────────────────────────────────────
# Schema activation (two independent gates on one config block)
# ────────────────────────────────────────────────────────────────────

def _stochastic_block(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("stochastic")
    if not isinstance(cfg, dict):
        return None
    return cfg


def get_stochastic_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the stochastic block when forecast bands are enabled."""
    cfg = _stochastic_block(game)
    if not cfg or not cfg.get("enabled"):
        return None
    return cfg


def get_calibration_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the stochastic block when forecast calibration is enabled."""
    cfg = _stochastic_block(game)
    if not cfg or not cfg.get("calibration_enabled"):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Forecast bands
# ────────────────────────────────────────────────────────────────────

def _headline_metric(state: Any) -> float:
    arr = _get(state, "arr", None)
    if isinstance(arr, (int, float)) and arr:
        return float(arr)
    mrr = _get(state, "monthly_revenue", None)
    if isinstance(mrr, (int, float)) and mrr:
        return float(mrr) * 12.0
    return float(_get(state, "money", 0) or 0)


def compute_forecast_bands(
    state: Any,
    cfg: Dict[str, Any],
    horizon_periods: int = 4,
    n_sims: int = 200,
) -> Dict[str, Any]:
    distribution = cfg.get("default_distribution", "triangular")
    confidence_pct = int(cfg.get("confidence_pct", 80) or 80)
    baseline = _headline_metric(state)
    rng = random.Random(42)  # deterministic within a single payload build

    def _draw(period: int) -> float:
        drift = 1.0 + 0.05 * period  # modest 5%/period base growth assumption
        if distribution == "normal":
            factor = rng.gauss(drift, 0.15 * period if period else 0.05)
        else:  # triangular
            low = drift * 0.8
            high = drift * 1.25
            factor = rng.triangular(low, high, drift)
        return max(0.0, baseline * factor)

    bands = []
    for period in range(1, horizon_periods + 1):
        samples = sorted(_draw(period) for _ in range(n_sims))
        lo_idx = int(len(samples) * (1 - confidence_pct / 100.0) / 2)
        hi_idx = len(samples) - 1 - lo_idx
        bands.append({
            "period": period,
            "low": round(samples[lo_idx], 0),
            "median": round(samples[len(samples) // 2], 0),
            "high": round(samples[hi_idx], 0),
        })
    return {
        "baseline": round(baseline, 0),
        "distribution": distribution,
        "confidence_pct": confidence_pct,
        "n_sims": n_sims,
        "horizon_periods": horizon_periods,
        "bands": bands,
    }


# ────────────────────────────────────────────────────────────────────
# Calibration
# ────────────────────────────────────────────────────────────────────

def compute_calibration(state: Any) -> Optional[Dict[str, Any]]:
    log = [d for d in (_get(state, "_forecast_log", []) or []) if isinstance(d, dict)]
    if not log:
        return None
    resolved = [d for d in log if isinstance(d.get("actual"), (int, float))]
    open_forecasts = [d for d in log if not isinstance(d.get("actual"), (int, float))]

    scored = []
    for d in resolved:
        predicted = float(d.get("predicted", 0) or 0)
        actual = float(d["actual"])
        error_pct = (abs(predicted - actual) / actual * 100.0) if actual else None
        scored.append({
            "label": d.get("label", "Forecast"),
            "predicted": predicted,
            "actual": actual,
            "confidence_pct": d.get("confidence_pct"),
            "error_pct": round(error_pct, 1) if error_pct is not None else None,
        })
    avg_error = (
        sum(s["error_pct"] for s in scored if s["error_pct"] is not None)
        / max(1, len([s for s in scored if s["error_pct"] is not None]))
    ) if scored else None
    return {
        "resolved_forecasts": scored,
        "open_forecasts": [{"label": d.get("label", "Forecast"),
                             "predicted": d.get("predicted"),
                             "confidence_pct": d.get("confidence_pct")} for d in open_forecasts],
        "avg_error_pct": round(avg_error, 1) if avg_error is not None else None,
        "calibration_score": round(max(0.0, 100.0 - avg_error), 1) if avg_error is not None else None,
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_stochastic_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    neither forecast bands nor calibration are enabled for this game."""
    bands_cfg = get_stochastic_config(game)
    calib_cfg = get_calibration_config(game)
    if not bands_cfg and not calib_cfg:
        return None

    payload: Dict[str, Any] = {
        "forecast_bands": None,
        "calibration": None,
    }
    try:
        if bands_cfg:
            payload["forecast_bands"] = compute_forecast_bands(state, bands_cfg)
    except Exception:
        pass
    try:
        if calib_cfg:
            payload["calibration"] = compute_calibration(state)
    except Exception:
        pass
    return payload
