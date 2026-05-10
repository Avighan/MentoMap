"""Decision Panel Engine — applies player slider/dial/dropdown decisions
to executive simulation state and tracks drift from expert picks.

Phase A.1 of the HBR/CapSim parity uplift. Each round of a multi-tab
executive sim ships a `decision_panel` config block declaring the
controls the player must commit, e.g.:

    {
      "controls": [
        {"id": "price", "type": "slider", "min": 100, "max": 300, "step": 5,
         "default": 200, "expert_pick": 220, "applies_to": "market.price"},
        {"id": "rd_pct", "type": "slider", "min": 0.0, "max": 0.30, "step": 0.01,
         "default": 0.10, "expert_pick": 0.15, "applies_to": "finance.rd_spend_ratio"},
        {"id": "hire_plan", "type": "dropdown",
         "options": ["freeze", "slow", "aggressive"],
         "default": "slow", "expert_pick": "slow", "applies_to": "org.hire_mode"}
      ]
    }

The player submits {control_id: value}. The engine:
  1. Validates each value is in range / step / options.
  2. Applies via `applies_to` dotted path into state, creating
     intermediate dicts as needed.
  3. Computes per-control drift from `expert_pick`:
        numeric:     drift_pct = |player - expert| / max(|expert|, 1)
        categorical: drift_pct = 0.0 if equal else 1.0
     Labels: <0.10 on_track, <0.30 modest, <0.60 wide, else extreme.

Pure stdlib. Not yet registered in engines/__init__.py — wiring lands
in a later phase when callers in app.py adopt it.
"""

from __future__ import annotations

from typing import Any


_FLOAT_TOL = 1e-6


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _set_dotted(target: dict, path: str, value: Any) -> None:
    """Set a dotted path inside `target`, creating intermediate dicts."""
    parts = path.split(".")
    cursor = target
    for key in parts[:-1]:
        nxt = cursor.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[key] = nxt
        cursor = nxt
    cursor[parts[-1]] = value


def _label_for_drift(drift_pct: float) -> str:
    if drift_pct < 0.10:
        return "on_track"
    if drift_pct < 0.30:
        return "modest"
    if drift_pct < 0.60:
        return "wide"
    return "extreme"


class DecisionPanelEngine:
    """Applies player decisions from sliders/dials/dropdowns to executive sim state."""

    # ------------------------------------------------------------------ validation

    def validate_submission(
        self, controls: list, submission: dict
    ) -> tuple[bool, list[str]]:
        """Return ``(ok, errors)`` where errors is a list of human-readable strings."""
        errors: list[str] = []
        if not isinstance(submission, dict):
            return False, ["submission must be a dict of {control_id: value}"]

        for ctrl in controls or []:
            cid = ctrl.get("id")
            if not cid:
                errors.append("control missing id")
                continue
            if cid not in submission:
                errors.append(f"{cid}: missing from submission")
                continue
            value = submission[cid]
            ctype = ctrl.get("type", "slider")

            if ctype in ("slider", "dial", "number"):
                if not _is_numeric(value):
                    errors.append(f"{cid}: expected numeric value, got {type(value).__name__}")
                    continue
                cmin = ctrl.get("min")
                cmax = ctrl.get("max")
                if cmin is not None and value < cmin:
                    errors.append(f"{cid}: value {value} below min {cmin}")
                    continue
                if cmax is not None and value > cmax:
                    errors.append(f"{cid}: value {value} above max {cmax}")
                    continue
                step = ctrl.get("step")
                if step is not None and step > 0 and cmin is not None:
                    offset = (value - cmin) / step
                    if abs(round(offset) - offset) > _FLOAT_TOL:
                        errors.append(f"{cid}: value {value} not aligned to step {step}")
                        continue
            elif ctype == "dropdown":
                options = ctrl.get("options") or []
                if value not in options:
                    errors.append(
                        f"{cid}: value {value!r} not in options {options}"
                    )
                    continue
            else:
                errors.append(f"{cid}: unknown control type {ctype!r}")

        # Flag unknown control ids in the submission
        known_ids = {c.get("id") for c in (controls or []) if c.get("id")}
        for sid in submission.keys():
            if sid not in known_ids:
                errors.append(f"{sid}: unknown control id")

        return (len(errors) == 0), errors

    # ------------------------------------------------------------------ apply

    def apply_submission(
        self, state: dict, controls: list, submission: dict
    ) -> dict:
        """Apply submitted values to state via dotted ``applies_to``.

        Mutates and returns ``state``.
        """
        if state is None:
            state = {}
        for ctrl in controls or []:
            cid = ctrl.get("id")
            if not cid or cid not in submission:
                continue
            applies_to = ctrl.get("applies_to")
            if not applies_to:
                continue
            _set_dotted(state, applies_to, submission[cid])
        return state

    # ------------------------------------------------------------------ drift

    def compute_drift(self, controls: list, submission: dict) -> dict:
        """Per-control drift summary from ``expert_pick``."""
        out: dict[str, dict] = {}
        for ctrl in controls or []:
            cid = ctrl.get("id")
            if not cid or cid not in submission:
                continue
            expert = ctrl.get("expert_pick")
            player = submission[cid]
            ctype = ctrl.get("type", "slider")

            if ctype in ("slider", "dial", "number") and _is_numeric(expert) and _is_numeric(player):
                denom = max(abs(expert), 1)
                drift_pct = abs(player - expert) / denom
            else:
                drift_pct = 0.0 if player == expert else 1.0

            out[cid] = {
                "expert_pick": expert,
                "player_value": player,
                "drift_pct": drift_pct,
                "drift_label": _label_for_drift(drift_pct),
            }
        return out

    # ------------------------------------------------------------------ commit

    def commit_round(
        self, state: dict, controls: list, submission: dict
    ) -> dict:
        """Full pipeline: validate -> apply -> drift.

        Raises ``ValueError`` if the submission is invalid. Returns
        ``{"state": state, "drift": {...}, "applied": {control_id: value}}``.
        """
        ok, errors = self.validate_submission(controls, submission)
        if not ok:
            raise ValueError("invalid decision-panel submission: " + "; ".join(errors))

        if state is None:
            state = {}
        self.apply_submission(state, controls, submission)
        drift = self.compute_drift(controls, submission)

        applied = {
            ctrl["id"]: submission[ctrl["id"]]
            for ctrl in (controls or [])
            if ctrl.get("id") and ctrl["id"] in submission
        }

        return {"state": state, "drift": drift, "applied": applied}
