"""
Behavioral signal extraction from raw gameplay telemetry.

Provides low-level statistics over a run's `choice_history` (decision
timing, consistency, risk-seeking) and `resource_trajectory` (recovery
from setbacks, grit under adversity). These feed `engines.dimension_utils
.aggregate_behavioral_signals`, which rolls them into the six standard
soft-skill dimensions for the authored+behavioral 50/50 blend.

All score_* functions return a float in [0, 1]; compute_timing_stats
returns a stats dict consumed by both dimension_utils.aggregate_behavioral_
signals and dimension_utils.adjust_scores_for_timing.
"""
from typing import Any, Dict, List, Optional

_FAST_DECISION_MS = 3000


def _entry_time_ms(entry: Dict[str, Any]) -> Optional[float]:
    for key in ("time_to_decide_ms", "decision_time_ms"):
        val = entry.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    return None


def _entry_delta_sum(entry: Dict[str, Any]) -> float:
    delta = entry.get("deltas", entry.get("delta"))
    if isinstance(delta, dict):
        return sum(v for v in delta.values() if isinstance(v, (int, float)))
    if isinstance(delta, (int, float)):
        return float(delta)
    return 0.0


def compute_timing_stats(history: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Aggregate decision-timing telemetry across a choice history.

    Returns {mean_ms, count, fast_decisions_count}. `count` is the number
    of entries carrying timing data (not len(history)); mean_ms defaults
    to a neutral 5000ms when no entry has timing data.
    """
    times = [t for t in (_entry_time_ms(e) for e in (history or []) if isinstance(e, dict)) if t is not None]
    if not times:
        return {"mean_ms": 5000, "count": 0, "fast_decisions_count": 0}
    mean_ms = sum(times) / len(times)
    fast_count = sum(1 for t in times if t < _FAST_DECISION_MS)
    return {"mean_ms": mean_ms, "count": len(times), "fast_decisions_count": fast_count}


def score_consistency(history: Optional[List[Dict[str, Any]]], trajectory: Optional[List[Dict[str, Any]]]) -> float:
    """Score how steady the player's decision pace was, in [0, 1].

    Low relative variance in decision timing -> high consistency. Falls
    back to a neutral 0.5 when there isn't enough timing data to judge.
    """
    history = history or []
    times = [t for t in (_entry_time_ms(e) for e in history if isinstance(e, dict)) if t is not None]
    if len(times) < 2:
        return 0.5
    mean_ms = sum(times) / len(times)
    if mean_ms <= 0:
        return 0.5
    variance = sum((t - mean_ms) ** 2 for t in times) / len(times)
    std_ms = variance ** 0.5
    coeff_var = std_ms / mean_ms
    # coeff_var of 0 -> perfectly consistent (1.0); >=1.5 -> essentially erratic (0.0)
    return max(0.0, min(1.0, 1.0 - coeff_var / 1.5))


def score_recovery_ability(trajectory: Optional[List[Dict[str, Any]]]) -> float:
    """Score how well the player recovered from their worst drawdown, in [0, 1].

    Walks the resource trajectory (using the first numeric resource found
    per snapshot), finds the largest peak-to-trough drawdown, then measures
    how much of that drawdown was clawed back by the final snapshot.
    """
    points = []
    for snap in trajectory or []:
        if not isinstance(snap, dict):
            continue
        numeric = [v for v in snap.values() if isinstance(v, (int, float))]
        if numeric:
            points.append(float(sum(numeric)))
    if len(points) < 2:
        return 0.5

    peak = points[0]
    trough = points[0]
    trough_after_peak = points[0]
    for v in points:
        if v > peak:
            peak = v
            trough_after_peak = v
        elif v < trough_after_peak:
            trough_after_peak = v
        trough = min(trough, trough_after_peak)

    drawdown = peak - trough
    if drawdown <= 0:
        return 0.75  # no drawdown at all reads as steady, above-neutral resilience
    recovery_ratio = (points[-1] - trough) / drawdown
    return max(0.0, min(1.0, recovery_ratio))


def score_risk_seeking(history: Optional[List[Dict[str, Any]]], trajectory: Optional[List[Dict[str, Any]]]) -> float:
    """Score revealed risk appetite from tagged `risk_level` choices, in [0, 1]."""
    weights = {"low": 0.15, "medium": 0.5, "med": 0.5, "high": 0.9}
    levels = [e.get("risk_level") for e in (history or []) if isinstance(e, dict) and e.get("risk_level")]
    if not levels:
        return 0.5
    scored = [weights.get(str(lv).lower(), 0.5) for lv in levels]
    return max(0.0, min(1.0, sum(scored) / len(scored)))


def score_grit(trajectory: Optional[List[Dict[str, Any]]], history: Optional[List[Dict[str, Any]]]) -> float:
    """Score persistence through adverse outcomes, in [0, 1].

    Grit rises with the share of choices made despite a net-negative
    delta on that same choice -- the player kept playing through setbacks
    rather than only advancing on wins.
    """
    history = history or []
    if not history:
        return 0.5
    negative_count = sum(1 for e in history if isinstance(e, dict) and _entry_delta_sum(e) < 0)
    return max(0.0, min(1.0, 0.5 + 0.5 * (negative_count / len(history))))
