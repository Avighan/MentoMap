"""
Compliance Engine — executive-tier regulatory / audit compliance subsystem
for simulation games.

Activated only when game JSON declares `simulation_config.compliance`. When
absent, `build_compliance_payload` returns None and existing games are
unaffected.

Schema (derived from games/series-a-founders-journey.json, a real committed
example):

    simulation_config.compliance = {
      "checks": [
        {"id": "gdpr_dpa", "label": "GDPR DPA with EU customers",
         "severity": "high", "trigger": "eu_customers > 0", "status": "open"},
        {"id": "soc2_in_flight", "label": "SOC 2 Type 1 audit underway",
         "severity": "medium", "trigger": "enterprise_customers > 5",
         "status": "open"},
        ...
      ]
    }

`trigger` is a tiny authored expression: "<state_attr> <op> <number>" where
op is one of >, >=, <, <=, ==, !=. It is evaluated against `state` — if the
referenced attribute is missing, the check is treated as not-yet-triggered
(rather than erroring), matching an early-game state where the resource
doesn't exist yet.

Runtime overrides (optional):
    state._compliance_resolved: set/list of check ids the player has resolved

All helpers are pure functions of (state, game) — they read state, never
mutate it.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_TRIGGER_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(>=|<=|==|!=|>|<)\s*(-?\d+(?:\.\d+)?)\s*$")

_SEVERITY_WEIGHT = {"high": 20, "medium": 10, "low": 5}


def _get(state: Any, key: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


# ────────────────────────────────────────────────────────────────────
# Schema activation
# ────────────────────────────────────────────────────────────────────

def get_compliance_config(game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the compliance block, or None if the game doesn't declare one."""
    sim = (game or {}).get("simulation_config") or {}
    cfg = sim.get("compliance")
    if not isinstance(cfg, dict):
        return None
    return cfg


# ────────────────────────────────────────────────────────────────────
# Trigger evaluation
# ────────────────────────────────────────────────────────────────────

def evaluate_trigger(state: Any, trigger: Optional[str]) -> Optional[bool]:
    """Evaluate a tiny "attr OP number" trigger expression against state.

    Returns True/False, or None if the trigger can't be parsed or the
    referenced attribute doesn't exist on state yet.
    """
    if not trigger or not isinstance(trigger, str):
        return None
    m = _TRIGGER_RE.match(trigger)
    if not m:
        return None
    attr, op, num_str = m.groups()
    value = _get(state, attr, None)
    if value is None or not isinstance(value, (int, float)):
        return None
    num = float(num_str)
    if op == ">":
        return value > num
    if op == ">=":
        return value >= num
    if op == "<":
        return value < num
    if op == "<=":
        return value <= num
    if op == "==":
        return value == num
    if op == "!=":
        return value != num
    return None


# ────────────────────────────────────────────────────────────────────
# Sub-computations
# ────────────────────────────────────────────────────────────────────

def compute_checks(state: Any, cfg: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    checks = cfg.get("checks")
    if not isinstance(checks, list) or not checks:
        return None
    resolved = set(_get(state, "_compliance_resolved", set()) or [])
    out = []
    for c in checks:
        cid = c.get("id")
        triggered = evaluate_trigger(state, c.get("trigger"))
        is_resolved = cid in resolved or c.get("status") == "resolved"
        out.append({
            "id": cid,
            "label": c.get("label", "Compliance item"),
            "severity": c.get("severity", "low"),
            "trigger": c.get("trigger"),
            "triggered": bool(triggered),
            "status": "resolved" if is_resolved else ("open" if triggered else "not_triggered"),
        })
    return out


def compute_compliance_score(checks: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    if not checks:
        return {"score": 100, "open_by_severity": {}, "open_count": 0}
    deduction = 0
    open_by_severity: Dict[str, int] = {}
    open_count = 0
    for c in checks:
        if c["status"] != "open":
            continue
        open_count += 1
        sev = c.get("severity", "low")
        open_by_severity[sev] = open_by_severity.get(sev, 0) + 1
        deduction += _SEVERITY_WEIGHT.get(sev, 5)
    score = max(0, 100 - deduction)
    return {
        "score": score,
        "open_by_severity": open_by_severity,
        "open_count": open_count,
    }


# ────────────────────────────────────────────────────────────────────
# Public payload builder
# ────────────────────────────────────────────────────────────────────

def build_compliance_payload(state: Any, game: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One-shot builder used by the UX enrichment layer. Returns None when
    compliance isn't configured for this game."""
    cfg = get_compliance_config(game)
    if not cfg:
        return None
    payload: Dict[str, Any] = {
        "checks": None,
        "score": None,
        "open_by_severity": None,
        "open_count": None,
    }
    try:
        checks = compute_checks(state, cfg)
        payload["checks"] = checks
        summary = compute_compliance_score(checks)
        payload["score"] = summary["score"]
        payload["open_by_severity"] = summary["open_by_severity"]
        payload["open_count"] = summary["open_count"]
    except Exception:
        pass
    return payload
