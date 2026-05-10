"""
ScorecardEngine — final weighted scorecard for HBR-parity executive sims.

Produces a 0-100 weighted scorecard at end-of-game (or end-of-period) with:
  - per-dimension band (`great` / `good` / `below`) against industry benchmarks
  - per-dimension score (0-100) and contribution (= score × normalized_weight)
  - overall_score (sum of contributions) + overall_band

Banding logic (higher-better metric):
  value >= great_upper       → score 100, band "great"
  great_low ≤ value < upper  → linear 75–95, band "great"
  good_low  ≤ value < g_low  → linear 50–75, band "good"
  value < good_low           → linear 0–50, band "below"

For `_lower_better` metrics (e.g. monthly_churn_pct_lower_better), the bands
are inverted: smaller value = better score. The state key may be supplied
without the `_lower_better` suffix (e.g. `monthly_churn_pct`) — the engine
matches by stripping the suffix on benchmark keys.

Benchmarks are loaded from `data/industry_benchmarks.json` by default;
callers can inject a custom dict for tests or org-specific overrides.
"""

from __future__ import annotations

import copy
import json
import os
from typing import Any, Dict, List, Optional, Tuple


_DEFAULT_BENCHMARKS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "industry_benchmarks.json",
)

_LOWER_BETTER_SUFFIX = "_lower_better"


class ScorecardEngine:
    """Build a weighted 0-100 scorecard against industry benchmarks."""

    def __init__(self, benchmarks: Optional[Dict[str, Any]] = None):
        if benchmarks is not None:
            self._benchmarks = benchmarks
        else:
            self._benchmarks = self._load_default_benchmarks()

    # ---- public API ---------------------------------------------------------

    def build_scorecard(
        self,
        state: Dict[str, Any],
        weights: Dict[str, float],
        business_model: str,
    ) -> Dict[str, Any]:
        """Compute a weighted scorecard.

        Args:
            state: KPI snapshot, e.g. {"gross_margin_pct": 85, "ltv_to_cac": 5}.
                   Does not need to carry the `_lower_better` suffix; engine
                   matches benchmarks by stripping it.
            weights: relative importance per KPI, e.g. {"gross_margin_pct": 0.5}.
                     Auto-normalized; missing KPIs are dropped before normalize.
            business_model: e.g. "saas_smb", "marketplace". If unknown, returns
                            a graceful empty card with a warning.
        Returns: dict with overall_score, overall_band, dimensions[], and
                 optionally a `warning` string.
        """
        state_in = copy.deepcopy(state)  # never mutate caller state
        bench = self._benchmarks.get(business_model)
        if bench is None:
            return {
                "overall_score": 0.0,
                "overall_band": "unknown",
                "dimensions": [],
                "warning": f"Unknown business_model '{business_model}'.",
                "business_model": business_model,
            }

        # Build (state_key, bench_key, lower_better) tuples for each KPI
        # in `weights` that ALSO has a value in `state_in`.
        active: List[Tuple[str, str, bool, float, float]] = []
        for state_key, w in weights.items():
            if state_key not in state_in:
                continue  # missing KPI — skip silently
            bench_key, lower_better = self._resolve_benchmark_key(bench, state_key)
            if bench_key is None:
                continue
            try:
                value = float(state_in[state_key])
            except (TypeError, ValueError):
                continue
            try:
                w_val = float(w)
            except (TypeError, ValueError):
                continue
            if w_val <= 0:
                continue
            active.append((state_key, bench_key, lower_better, value, w_val))

        if not active:
            return {
                "overall_score": 0.0,
                "overall_band": "below",
                "dimensions": [],
                "business_model": business_model,
                "business_model_label": bench.get("label", business_model),
            }

        total_w = sum(t[4] for t in active)
        dimensions: List[Dict[str, Any]] = []
        overall = 0.0

        for state_key, bench_key, lower_better, value, w_val in active:
            band_data = bench[bench_key]
            score, band = self._score_value(value, band_data, lower_better)
            norm_w = w_val / total_w if total_w > 0 else 0.0
            contribution = score * norm_w
            overall += contribution
            dimensions.append({
                "name": state_key,
                "value": value,
                "score": round(score, 2),
                "band": band,
                "weight": w_val,
                "normalized_weight": round(norm_w, 4),
                "contribution": round(contribution, 4),
                "lower_better": lower_better,
                "good_band": list(band_data.get("good", [])),
                "great_band": list(band_data.get("great", [])),
            })

        overall = round(overall, 4)
        return {
            "overall_score": overall,
            "overall_band": self._overall_band(overall),
            "dimensions": dimensions,
            "business_model": business_model,
            "business_model_label": bench.get("label", business_model),
        }

    # ---- internals ----------------------------------------------------------

    def _resolve_benchmark_key(
        self,
        bench: Dict[str, Any],
        state_key: str,
    ) -> Tuple[Optional[str], bool]:
        """Find the benchmark band-dict for `state_key`.

        State keys typically omit the `_lower_better` suffix; benchmark keys
        encode that flag in the suffix. Returns (matched_key, lower_better).
        """
        if state_key in bench and isinstance(bench[state_key], dict):
            return state_key, state_key.endswith(_LOWER_BETTER_SUFFIX)
        suffixed = f"{state_key}{_LOWER_BETTER_SUFFIX}"
        if suffixed in bench and isinstance(bench[suffixed], dict):
            return suffixed, True
        return None, False

    def _score_value(
        self,
        value: float,
        band_data: Dict[str, Any],
        lower_better: bool,
    ) -> Tuple[float, str]:
        """Map a raw KPI value to (score 0-100, band)."""
        good = band_data.get("good") or [0, 0]
        great = band_data.get("great") or [0, 0]
        good_low, good_upper = float(good[0]), float(good[1])
        great_low, great_upper = float(great[0]), float(great[1])

        if lower_better:
            # Smaller value = better. Great band has the smaller numbers.
            if value <= great_low:
                return 100.0, "great"
            if value <= great_upper:
                span = max(1e-9, great_upper - great_low)
                frac = (value - great_low) / span
                return 95.0 - frac * 20.0, "great"
            if value <= good_upper:
                span = max(1e-9, good_upper - great_upper)
                frac = (value - great_upper) / span
                return 75.0 - frac * 25.0, "good"
            # below good_upper end — score linearly to 0 at 2× good_upper
            denom = max(1e-9, abs(good_upper))
            ratio = (value - good_upper) / denom
            return max(0.0, 50.0 - ratio * 50.0), "below"

        # Higher-better.
        if value >= great_upper:
            return 100.0, "great"
        if value >= great_low:
            span = max(1e-9, great_upper - great_low)
            frac = (value - great_low) / span
            return 75.0 + frac * 20.0, "great"
        if value >= good_low:
            span = max(1e-9, great_low - good_low)
            frac = (value - good_low) / span
            return 50.0 + frac * 25.0, "good"
        # below good_low — score linearly to 0 at value=0
        denom = max(1e-9, abs(good_low))
        ratio = (good_low - value) / denom
        return max(0.0, 50.0 - ratio * 50.0), "below"

    def _overall_band(self, overall: float) -> str:
        if overall >= 75.0:
            return "great"
        if overall >= 50.0:
            return "good"
        return "below"

    @staticmethod
    def _load_default_benchmarks() -> Dict[str, Any]:
        try:
            with open(_DEFAULT_BENCHMARKS_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # strip top-level meta key if present
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except (OSError, json.JSONDecodeError):
            return {}
