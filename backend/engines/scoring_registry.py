"""
Scoring-formula registry.

Before this module, adding a new way to turn raw game telemetry into a
score meant writing a brand-new engine class *and* a brand-new hardcoded
Flask route. This module gives the scoring *math* itself a pluggable,
name-keyed home so any engine (existing or future) can declare which
formula it uses instead of re-implementing (or copy-pasting) one.

Every formula implements the same tiny interface:

    class ScoringFormula(Protocol):
        def compute(self, state: Any, config: Dict[str, Any]) -> ScoringResult: ...

`state` carries the domain-specific numbers the caller already derived
(e.g. "how far off was the measurement", "how many cells matched the
solution"); deriving those numbers from a submission is still each
engine's job — that is domain knowledge the registry has no business
knowing. `config` carries game-authored tuning (dimension weights, grade
tables, benchmark names, ...). The formula's only responsibility is the
last mile: numbers in, {total, band, label, dimensions} out.

Registered formulas:
  - "proximity_band"       — continuous value vs. true value, banded by
                              tolerance (wraps `_grader_common`).
  - "fraction_correct"     — N-of-M items correct, no partial credit
                              per item.
  - "penalized_fraction"   — fraction_correct plus a validity multiplier
                              and/or flat point penalty (sudoku's shape).
  - "mae_accuracy"         — 100 - mean absolute error, floored at 0
                              (genetics_cross's shape).
  - "speed_accuracy_factor"— accuracy blended with a speed *factor*
                              centered on 1.0 (mental_math's shape).
  - "speed_accuracy_capped"— accuracy blended with a speed ratio capped
                              at 1.0 (typing_drill's shape).
  - "points_ceiling_ratio" — points earned vs. a grid-aware ceiling
                              (boggle's shape).
  - "dimension_average"    — plain average of named 0-100 dimension
                              scores (mock_interview's LLM-scored path).
  - "benchmark_scorecard"  — weighted KPI snapshot vs. named industry
                              benchmark bands (wraps `ScorecardEngine`).
  - "weighted_kpi_normalize" — normalize KPIs against min/max ranges,
                              weight into categories, sum into a total,
                              look up a grade from a game-supplied table.
  - "settlement_engine"    — identical shape to weighted_kpi_normalize,
                              registered separately for games whose round
                              mechanics involve a period-close settlement
                              step (shipping, holding cost, debt) that the
                              stateless snapshot formula doesn't model —
                              see games/mumbai_manufacturer_engine.py.
  - "expert_drift"         — end-of-run aggregation of per-round
                              expert-vs-player control drift (extends
                              `DecisionPanelEngine.compute_drift`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from engines._grader_common import (
    band_score_by_diff,
    distribute_dimension_scores,
)


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------


@dataclass
class ScoringResult:
    """Common return shape every formula produces.

    `raw` carries formula-specific extras (e.g. `mean_abs_error_pct`) that
    a caller may want to fold into its own response dict; it is never
    required reading.
    """

    total: float
    band: str
    label: str
    dimensions: Dict[str, int] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        out = {
            "score": self.total,
            "band": self.band,
            "label": self.label,
            "dimension_scores": self.dimensions,
        }
        out.update(self.raw)
        return out


@runtime_checkable
class ScoringFormula(Protocol):
    def compute(self, state: Any, config: Dict[str, Any]) -> ScoringResult: ...


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------


_REGISTRY: Dict[str, ScoringFormula] = {}


def register(name: str, formula: ScoringFormula) -> None:
    """Register (or overwrite) a formula under `name`."""
    _REGISTRY[name] = formula


def get(name: str) -> ScoringFormula:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"Unknown scoring formula '{name}'. Registered: {sorted(_REGISTRY)}"
        )


def available() -> List[str]:
    return sorted(_REGISTRY)


def compute(name: str, state: Any, config: Optional[Dict[str, Any]] = None) -> ScoringResult:
    """Convenience: `get(name).compute(state, config or {})`."""
    return get(name).compute(state, config or {})


# --------------------------------------------------------------------------
# Generic band helper shared by the "no natural band" formulas below.
# --------------------------------------------------------------------------


def _generic_band(score: float) -> str:
    if score >= 80:
        return "strong"
    if score >= 50:
        return "developing"
    return "needs_work"


# --------------------------------------------------------------------------
# Formula: proximity_band
# --------------------------------------------------------------------------


class ProximityBandFormula:
    """Continuous-value-vs-true-value scoring, banded by tolerance.

    state:  {"diff": float, "tolerance": float}
    config: {"weights": Dict[str, float]}  # already-normalized dimension weights

    Used by pendulum_lab, optics_lab, and stoichiometry_mixer, which all
    reduce to: derive a scalar, compare to a true value, band the result.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        diff = float(state.get("diff", 0.0))
        tolerance = float(state.get("tolerance", 1.0))
        weights = config.get("weights") or {}
        score, band = band_score_by_diff(diff, tolerance)
        dims = distribute_dimension_scores(score, weights)
        return ScoringResult(total=score, band=band, label=band, dimensions=dims)


# --------------------------------------------------------------------------
# Formula: fraction_correct
# --------------------------------------------------------------------------


class FractionCorrectFormula:
    """N-of-M items correct, no partial credit per item.

    state:  {"correct": int, "total": int}
    config: {"weights": Dict[str, float]}

    Used by circuit_debugger (nodes within tolerance), logic_grid (cells
    matching solution), and geometry_constructor (features satisfied) —
    all three reduce to the identical `round(correct/total*100)`.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        correct = state.get("correct") or 0
        total = state.get("total") or 0
        weights = config.get("weights") or {}
        score = int(round((correct / total) * 100)) if total else 0
        dims = distribute_dimension_scores(score, weights)
        band = _generic_band(score)
        return ScoringResult(total=score, band=band, label=band, dimensions=dims)


# --------------------------------------------------------------------------
# Formula: penalized_fraction
# --------------------------------------------------------------------------


class PenalizedFractionFormula:
    """fraction_correct, plus an optional validity multiplier and/or a
    flat point penalty applied after the percentage conversion.

    state:  {"correct": int, "total": int, "valid": bool (default True),
             "penalty_points": number (default 0)}
    config: {"weights": Dict[str, float], "invalid_multiplier": float (default 1.0)}

    Used by sudoku: base = cells_correct/81, base *= 0.8 if invalid,
    then flat hint penalty is subtracted, clamped to [0, 100].
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        correct = state.get("correct") or 0
        total = state.get("total") or 0
        valid = state.get("valid", True)
        penalty_points = state.get("penalty_points") or 0
        weights = config.get("weights") or {}
        invalid_multiplier = config.get("invalid_multiplier", 1.0)

        base = (correct / total) if total else 0.0
        if not valid:
            base *= invalid_multiplier
        score = int(round(base * 100)) - int(penalty_points)
        score = max(0, min(100, score))

        dims = distribute_dimension_scores(score, weights)
        band = _generic_band(score)
        return ScoringResult(total=score, band=band, label=band, dimensions=dims)


# --------------------------------------------------------------------------
# Formula: mae_accuracy
# --------------------------------------------------------------------------


class MaeAccuracyFormula:
    """100 - mean absolute error (over a set of expected/predicted pairs),
    floored at 0.

    state:  {"predicted": Dict[str, float], "expected": Dict[str, float]}
    config: {"weights": Dict[str, float]}

    Used by genetics_cross: predicted phenotype percentages vs. the
    Mendelian-derived expected distribution. Missing predictions count
    as 0.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        predicted = state.get("predicted") or {}
        expected = state.get("expected") or {}
        weights = config.get("weights") or {}

        if not expected:
            dims = {dim: 0 for dim in weights}
            return ScoringResult(total=0, band="no_data", label="no_data", dimensions=dims)

        diffs: List[float] = []
        for key, exp_val in expected.items():
            try:
                pred_val = float(predicted.get(key, 0))
            except (TypeError, ValueError):
                pred_val = 0.0
            diffs.append(abs(pred_val - float(exp_val)))
        mae = sum(diffs) / len(diffs)
        score = max(0, int(round(100 - mae)))

        dims = distribute_dimension_scores(score, weights)
        band = _generic_band(score)
        return ScoringResult(
            total=score, band=band, label=band, dimensions=dims,
            raw={"mean_abs_error_pct": round(mae, 2)},
        )


# --------------------------------------------------------------------------
# Formula: speed_accuracy_factor
# --------------------------------------------------------------------------


class SpeedAccuracyFactorFormula:
    """Accuracy blended with a speed *factor* centered on 1.0.

    state:  {"accuracy": float 0..1, "speed_factor": float, already
             clamped to [min_factor, max_factor]}
    config: {"weights": Dict[str, float],
             "accuracy_weight": float (default 0.8),
             "speed_weight": float (default 0.2),
             "min_factor": float (default 0.75),
             "max_factor": float (default 1.25)}

    Used by mental_math: 1.0 at exactly the per-problem time target, up
    to 1.25 at 2x faster, down to 0.75 at 2x slower.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        accuracy = float(state.get("accuracy", 0.0))
        speed_factor = float(state.get("speed_factor", 1.0))
        weights = config.get("weights") or {}
        accuracy_weight = config.get("accuracy_weight", 0.8)
        speed_weight = config.get("speed_weight", 0.2)
        min_factor = config.get("min_factor", 0.75)
        max_factor = config.get("max_factor", 1.25)

        span = max(1e-9, max_factor - min_factor)
        speed_unit = (speed_factor - min_factor) / span
        raw = (accuracy * accuracy_weight + speed_unit * speed_weight) * 100
        score = max(0, min(100, int(round(raw))))

        dims = distribute_dimension_scores(score, weights)
        band = _generic_band(score)
        return ScoringResult(total=score, band=band, label=band, dimensions=dims)


# --------------------------------------------------------------------------
# Formula: speed_accuracy_capped
# --------------------------------------------------------------------------


class SpeedAccuracyCappedFormula:
    """Accuracy blended with a speed ratio capped at 1.0 (no bonus for
    being faster than target, unlike speed_accuracy_factor).

    state:  {"accuracy": float 0..1, "actual": float, "target": float}
    config: {"weights": Dict[str, float],
             "accuracy_weight": float (default 70),
             "speed_weight": float (default 30)}

    Used by typing_drill: WPM / target_wpm, capped at 1.0.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        accuracy = float(state.get("accuracy", 0.0))
        actual = float(state.get("actual", 0.0))
        target = float(state.get("target", 0.0))
        weights = config.get("weights") or {}
        accuracy_weight = config.get("accuracy_weight", 70)
        speed_weight = config.get("speed_weight", 30)

        speed_ratio = min(1.0, actual / target) if target > 0 else 0.0
        raw = accuracy * accuracy_weight + speed_ratio * speed_weight
        score = max(0, min(100, int(round(raw))))

        dims = distribute_dimension_scores(score, weights)
        band = _generic_band(score)
        return ScoringResult(total=score, band=band, label=band, dimensions=dims)


# --------------------------------------------------------------------------
# Formula: points_ceiling_ratio
# --------------------------------------------------------------------------


class PointsCeilingRatioFormula:
    """Points earned vs. a domain-computed ceiling (e.g. "every findable
    word on this specific grid").

    state:  {"raw_points": number, "ceiling": number}
    config: {"weights": Dict[str, float]}

    Used by boggle: ceiling is the sum of point values for every
    dictionary word that is actually reachable on this grid.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        raw_points = state.get("raw_points") or 0
        ceiling = max(state.get("ceiling") or 0, 1)
        weights = config.get("weights") or {}

        score = int(round(min(raw_points, ceiling) / ceiling * 100))
        dims = distribute_dimension_scores(score, weights)
        band = _generic_band(score)
        return ScoringResult(total=score, band=band, label=band, dimensions=dims)


# --------------------------------------------------------------------------
# Formula: dimension_average
# --------------------------------------------------------------------------


class DimensionAverageFormula:
    """Plain average of a set of already-0-100-scored named dimensions.

    state:  {"dimension_scores": Dict[str, number]}
    config: {}  (no weighting — each named dimension counts equally)

    Used by mock_interview's LLM-graded path: the LLM already returns a
    0-100 score per rubric dimension; the "formula" is just averaging
    them into one total.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        dim_scores = state.get("dimension_scores") or {}
        if not dim_scores:
            return ScoringResult(total=0, band="no_data", label="no_data", dimensions={})
        avg = int(round(sum(dim_scores.values()) / len(dim_scores)))
        band = _generic_band(avg)
        return ScoringResult(total=avg, band=band, label=band, dimensions=dict(dim_scores))


# --------------------------------------------------------------------------
# Formula: benchmark_scorecard
# --------------------------------------------------------------------------


class BenchmarkScorecardFormula:
    """Weighted KPI snapshot vs. a named industry-benchmark profile.

    state:  {"state": Dict[str, Any]}  # KPI snapshot
    config: {"weights": Dict[str, float], "business_model": str,
             "benchmarks": Optional[Dict] (defaults to the built-in
             industry_benchmarks.json via ScorecardEngine)}

    Thin wrapper around the existing `ScorecardEngine` — HBR-parity
    executive-sim scorecards keep using it unchanged; this just gives the
    same math a name in the registry so future callers can reach it by
    string instead of importing ScorecardEngine directly.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        from engines.scorecard_engine import ScorecardEngine

        kpi_state = state.get("state") or {}
        weights = config.get("weights") or {}
        business_model = config.get("business_model") or "saas_smb"
        benchmarks = config.get("benchmarks")

        engine = ScorecardEngine(benchmarks=benchmarks)
        card = engine.build_scorecard(
            state=kpi_state, weights=weights, business_model=business_model,
        )
        dims = {d["name"]: int(round(d["score"])) for d in card.get("dimensions", [])}
        label = card.get("business_model_label", business_model)
        return ScoringResult(
            total=card.get("overall_score", 0.0),
            band=card.get("overall_band", "unknown"),
            label=label,
            dimensions=dims,
            raw=card,
        )


# --------------------------------------------------------------------------
# Formula: weighted_kpi_normalize  (new — no game wired up yet)
# --------------------------------------------------------------------------


class WeightedKpiNormalizeFormula:
    """Normalize several KPIs against a min/max range, weight into
    per-category scores, sum categories into a total, and look up a
    grade from a game-supplied grade table.

    state:
        {"kpis": {kpi_name: value, ...}}

    config:
        {
          "categories": [
            {
              "name": "financial",
              "kpis": [
                {"name": "revenue", "min": 0, "max": 1_000_000, "weight": 0.6},
                {"name": "margin_pct", "min": 0, "max": 100, "weight": 0.4},
              ],
            },
            ...
          ],
          "grade_table": [
            {"min": 90, "grade": "A", "label": "Outstanding"},
            {"min": 75, "grade": "B", "label": "Solid"},
            {"min": 60, "grade": "C", "label": "Passing"},
            {"min": 0,  "grade": "F", "label": "Needs Improvement"},
          ],  # must be sorted descending by "min"
        }

    Each KPI is normalized to 0-100 via `(value - min) / (max - min)`,
    clamped to [0, 100], then multiplied by its weight. A category's
    score is the sum of its KPI contributions (category weights are
    implicit in how each category's KPI weights are scaled — a category
    is not itself re-normalized, so category KPI weights should already
    sum to that category's intended share of the 100-point total across
    all categories, e.g. two categories each weighted to contribute up
    to 50 points). The total is the sum of category scores, clamped to
    [0, 100]. The grade table is walked top-to-bottom (highest `min`
    first); the first row whose `min` the total meets or exceeds wins.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        kpis = state.get("kpis") or {}
        categories = config.get("categories") or []
        grade_table = config.get("grade_table") or []

        category_scores: Dict[str, float] = {}
        for cat in categories:
            cat_name = cat.get("name") or "category"
            category_scores[cat_name] = self._category_score(cat, kpis)

        total = max(0.0, min(100.0, sum(category_scores.values())))
        grade, label = self._lookup_grade(total, grade_table)

        return ScoringResult(
            total=round(total, 2),
            band=grade,
            label=label,
            dimensions={k: round(v, 2) for k, v in category_scores.items()},
            raw={"category_scores": {k: round(v, 2) for k, v in category_scores.items()}},
        )

    @staticmethod
    def _category_score(cat: Dict[str, Any], kpis: Dict[str, Any]) -> float:
        cat_total = 0.0
        for kpi_cfg in cat.get("kpis") or []:
            kpi_name = kpi_cfg.get("name")
            if kpi_name is None or kpi_name not in kpis:
                continue
            try:
                value = float(kpis[kpi_name])
            except (TypeError, ValueError):
                continue
            kpi_min = float(kpi_cfg.get("min", 0))
            kpi_max = float(kpi_cfg.get("max", 100))
            weight = float(kpi_cfg.get("weight", 0))
            span = kpi_max - kpi_min
            normalized = 0.0 if span <= 0 else (value - kpi_min) / span * 100
            normalized = max(0.0, min(100.0, normalized))
            cat_total += normalized * weight
        return cat_total

    @staticmethod
    def _lookup_grade(total: float, grade_table: List[Dict[str, Any]]) -> tuple:
        rows = sorted(grade_table, key=lambda r: r.get("min", 0), reverse=True)
        for row in rows:
            if total >= row.get("min", 0):
                return row.get("grade", "N/A"), row.get("label", row.get("grade", "N/A"))
        return "N/A", "N/A"


# --------------------------------------------------------------------------
# Formula: settlement_engine  (new — Mumbai Manufacturer)
# --------------------------------------------------------------------------


class SettlementEngineFormula:
    """End-of-run scoring for games with period-close/settlement round
    mechanics (inventory, cash-flow, debt) — same weighted-category-vs-
    range shape as `weighted_kpi_normalize`, kept as its own registered
    name so the round-by-round settlement math a game like this needs
    (shipping revenue, holding cost, bullwhip drift, debt conversion —
    see `games/mumbai_manufacturer_engine.py`) isn't confused with, or
    forced into, the *stateless* snapshot formula.

    state / config shape is identical to `weighted_kpi_normalize` — see
    that formula's docstring. "Lower is better" KPIs (bullwhip_index,
    supply_chain_cost_ratio, bank_debt, ...) are expressed the same way
    weighted_kpi_normalize already supports: set `min` to the worst
    (highest) value and `max` to the best (lowest) value for that KPI, so
    the min/max normalization inverts naturally without special-casing.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        kpis = state.get("kpis") or {}
        categories = config.get("categories") or []
        grade_table = config.get("grade_table") or []

        category_scores: Dict[str, float] = {}
        for cat in categories:
            cat_name = cat.get("name") or "category"
            category_scores[cat_name] = WeightedKpiNormalizeFormula._category_score(cat, kpis)

        total = max(0.0, min(100.0, sum(category_scores.values())))
        grade, label = WeightedKpiNormalizeFormula._lookup_grade(total, grade_table)

        return ScoringResult(
            total=round(total, 2),
            band=grade,
            label=label,
            dimensions={k: round(v, 2) for k, v in category_scores.items()},
            raw={"category_scores": {k: round(v, 2) for k, v in category_scores.items()}},
        )


# --------------------------------------------------------------------------
# Formula: expert_drift  (new — no game wired up yet)
# --------------------------------------------------------------------------


class ExpertDriftFormula:
    """End-of-run aggregation of continuous-lever decisions (sliders/dials)
    against an expert-recommended value per control.

    `decision_panel_engine.DecisionPanelEngine.compute_drift` already
    computes PER-ROUND drift for a single round's controls. This formula
    reuses that per-round shape and aggregates it across every round of
    a run into one end-of-run score/grade, instead of duplicating the
    per-control drift math.

    state:
        {"rounds": [
            {"controls": [...], "submission": {control_id: value}},
            ...
         ]}
        Each round's "controls"/"submission" pair is exactly what
        `DecisionPanelEngine.compute_drift(controls, submission)` expects.

    config:
        {"weights": Dict[str, float] (optional per-control weights,
                    defaults to equal weight),
         "grade_table": [{"min": 90, "grade": "A", "label": "..."}]}

    Aggregate score = 100 - weighted_avg(drift_pct across every control
    in every round) * 100, floored at 0.
    """

    def compute(self, state: Dict[str, Any], config: Dict[str, Any]) -> ScoringResult:
        from engines.decision_panel_engine import DecisionPanelEngine

        rounds = state.get("rounds") or []
        weights = config.get("weights") or {}
        grade_table = config.get("grade_table") or []

        engine = DecisionPanelEngine()
        per_control_drift: Dict[str, List[float]] = {}
        for rnd in rounds:
            controls = rnd.get("controls") or []
            submission = rnd.get("submission") or {}
            drift_map = engine.compute_drift(controls, submission)
            for cid, d in drift_map.items():
                per_control_drift.setdefault(cid, []).append(d["drift_pct"])

        if not per_control_drift:
            return ScoringResult(total=0, band="no_data", label="no_data", dimensions={})

        control_avg_drift = {
            cid: sum(vals) / len(vals) for cid, vals in per_control_drift.items()
        }

        total_weight = sum(weights.get(cid, 1.0) for cid in control_avg_drift) or 1.0
        weighted_drift = sum(
            control_avg_drift[cid] * weights.get(cid, 1.0) for cid in control_avg_drift
        ) / total_weight

        score = max(0.0, min(100.0, 100.0 - weighted_drift * 100.0))
        dims = {
            cid: max(0, min(100, int(round(100 - drift * 100))))
            for cid, drift in control_avg_drift.items()
        }

        if grade_table:
            band, label = WeightedKpiNormalizeFormula._lookup_grade(score, grade_table)
        else:
            band = _generic_band(score)
            label = band

        return ScoringResult(
            total=round(score, 2), band=band, label=label, dimensions=dims,
            raw={"control_avg_drift_pct": {k: round(v, 4) for k, v in control_avg_drift.items()}},
        )


# --------------------------------------------------------------------------
# Built-in registration
# --------------------------------------------------------------------------


def _register_builtins() -> None:
    register("proximity_band", ProximityBandFormula())
    register("fraction_correct", FractionCorrectFormula())
    register("penalized_fraction", PenalizedFractionFormula())
    register("mae_accuracy", MaeAccuracyFormula())
    register("speed_accuracy_factor", SpeedAccuracyFactorFormula())
    register("speed_accuracy_capped", SpeedAccuracyCappedFormula())
    register("points_ceiling_ratio", PointsCeilingRatioFormula())
    register("dimension_average", DimensionAverageFormula())
    register("benchmark_scorecard", BenchmarkScorecardFormula())
    register("weighted_kpi_normalize", WeightedKpiNormalizeFormula())
    register("settlement_engine", SettlementEngineFormula())
    register("expert_drift", ExpertDriftFormula())


_register_builtins()
