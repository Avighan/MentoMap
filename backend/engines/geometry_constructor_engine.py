"""
GeometryConstructorEngine — `geometry_constructor` compass-and-straightedge
construction grader.

JSON declares the construction goal as a list of `target_features` — each
a geometric assertion that should hold of the student's final figure
(e.g. "AB == BC" for an isoceles triangle, "angle ABC == 90" for a right
angle, "AB == 1.0" for a unit length). The renderer captures the student's
points/segments; on submit it POSTs the resulting set of named points
{name: [x, y]} and the engine evaluates each target_feature numerically.

Score = (features satisfied / total features) × 100. Default dimensions:
spatial_reasoning + precision.
"""
import math
from typing import Any, Dict, List, Tuple

from engines._grader_common import coerce_weights
from engines import scoring_registry

_DEFAULT_DIMENSION_WEIGHTS = {
    "spatial_reasoning": 0.6,
    "attention_to_detail": 0.4,
}


def _dist(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _angle_deg(p1, p2, p3) -> float:
    """Angle at p2 formed by p1-p2-p3, in degrees."""
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    m1 = math.hypot(*v1)
    m2 = math.hypot(*v2)
    if m1 == 0 or m2 == 0:
        return 0.0
    cos_t = max(-1.0, min(1.0, dot / (m1 * m2)))
    return math.degrees(math.acos(cos_t))


def _evaluate_feature(feature: Dict[str, Any], points: Dict[str, Tuple[float, float]],
                       tolerance: float) -> bool:
    """Each feature is one of:
      {kind: 'length_eq',  segments: ['AB','BC']}                — |AB| == |BC|
      {kind: 'length',     segment: 'AB', value: 1.0}            — |AB| == value
      {kind: 'angle',      vertices: ['A','B','C'], value: 90}   — ∠ABC == value
      {kind: 'distance',   points: ['A','B'], value: 5.0}        — alias of length
    """
    kind = feature.get("kind")

    def _seg(name: str):
        if not isinstance(name, str) or len(name) < 2:
            return None
        a, b = name[0], name[1:]
        # Single-letter point names by default; if name length > 2 split on first char.
        if len(name) == 2:
            a, b = name[0], name[1]
        if a in points and b in points:
            return _dist(points[a], points[b])
        return None

    if kind == "length_eq":
        segs = feature.get("segments") or []
        vals = [_seg(s) for s in segs]
        if any(v is None for v in vals) or len(vals) < 2:
            return False
        return all(abs(v - vals[0]) <= tolerance for v in vals)

    if kind in ("length", "distance"):
        s = feature.get("segment") or "".join(feature.get("points") or [])
        v = _seg(s)
        target = feature.get("value")
        if v is None or target is None:
            return False
        return abs(v - float(target)) <= tolerance

    if kind == "angle":
        verts = feature.get("vertices") or []
        target = feature.get("value")
        if len(verts) != 3 or target is None:
            return False
        if not all(v in points for v in verts):
            return False
        a = _angle_deg(points[verts[0]], points[verts[1]], points[verts[2]])
        return abs(a - float(target)) <= tolerance

    return False


class GeometryConstructorEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.target_features: List[Dict[str, Any]] = list(
            self.game_config.get("target_features") or []
        )
        self.tolerance = float(self.game_config.get("tolerance") or 0.05)
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )

    def grade_results(self, points: Dict[str, List[float]]) -> Dict[str, Any]:
        # Coerce input to (x, y) tuples.
        coerced: Dict[str, Tuple[float, float]] = {}
        for name, coords in (points or {}).items():
            try:
                coerced[name] = (float(coords[0]), float(coords[1]))
            except (TypeError, ValueError, IndexError):
                continue

        if not self.target_features:
            return {
                "score": 0,
                "features_satisfied": 0,
                "features_total": 0,
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        results: List[Dict[str, Any]] = []
        satisfied = 0
        for feat in self.target_features:
            ok = _evaluate_feature(feat, coerced, self.tolerance)
            if ok:
                satisfied += 1
            results.append({"feature": feat, "satisfied": ok})

        total = len(self.target_features)
        result = scoring_registry.compute(
            "fraction_correct", {"correct": satisfied, "total": total},
            {"weights": self.weights},
        )

        return {
            "score": result.total,
            "features_satisfied": satisfied,
            "features_total": total,
            "tolerance": self.tolerance,
            "feature_results": results,
            "dimension_scores": result.dimensions,
        }
