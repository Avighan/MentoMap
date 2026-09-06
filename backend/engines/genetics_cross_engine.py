"""
GeneticsCrossEngine — `genetics_cross` Punnett-square discovery game.

JSON config declares a Mendelian cross — a parent_a genotype like "Aa"
and a parent_b genotype like "Aa". The engine derives the *true* offspring
phenotype distribution (e.g. for Aa × Aa with dominance: 75% dominant,
25% recessive) and grades the student's predicted percentages against it.

Score = 100 - mean_absolute_percentage_error (capped at 0). For a single
trait, this maps perfectly-correct predictions to 100 and nonsense to ~0.

Default dimensions: pattern_recognition + prediction_accuracy.
"""
from typing import Any, Dict

from engines._grader_common import coerce_weights
from engines import scoring_registry

_DEFAULT_DIMENSION_WEIGHTS = {
    "pattern_recognition": 0.5,
    "prediction_accuracy": 0.5,
}


def _expected_phenotype_pct(parent_a: str, parent_b: str, dominance: bool) -> Dict[str, float]:
    """Compute expected offspring distribution for a single-trait Mendelian cross.

    For dominance=True (classic Mendel), uppercase allele dominates, lowercase
    recessive. The keys returned are "dominant" / "recessive". For
    dominance=False (incomplete dominance), keys are "homo_dom" /
    "hetero" / "homo_rec".
    """
    a = list(parent_a or "")
    b = list(parent_b or "")
    if len(a) != 2 or len(b) != 2:
        return {}
    counts: Dict[str, int] = {}
    for x in a:
        for y in b:
            geno = "".join(sorted([x, y], key=lambda c: c.islower()))
            counts[geno] = counts.get(geno, 0) + 1
    total = sum(counts.values())
    if total == 0:
        return {}

    if dominance:
        dom = sum(c for g, c in counts.items() if any(ch.isupper() for ch in g))
        rec = total - dom
        return {
            "dominant": round(dom / total * 100, 2),
            "recessive": round(rec / total * 100, 2),
        }
    # Incomplete dominance: distinguish heterozygote
    homo_dom = sum(c for g, c in counts.items() if g.isupper())
    homo_rec = sum(c for g, c in counts.items() if g.islower())
    hetero = total - homo_dom - homo_rec
    return {
        "homo_dom": round(homo_dom / total * 100, 2),
        "hetero": round(hetero / total * 100, 2),
        "homo_rec": round(homo_rec / total * 100, 2),
    }


class GeneticsCrossEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.cross = self.game_config.get("cross") or {}
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )

    def grade_results(self, predictions: Dict[str, float]) -> Dict[str, Any]:
        parent_a = self.cross.get("parent_a") or "Aa"
        parent_b = self.cross.get("parent_b") or "Aa"
        dominance = self.cross.get("dominance", True)

        expected = _expected_phenotype_pct(parent_a, parent_b, dominance)
        if not expected:
            return {
                "score": 0,
                "expected": {},
                "predicted": predictions or {},
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        result = scoring_registry.compute(
            "mae_accuracy", {"predicted": predictions or {}, "expected": expected},
            {"weights": self.weights},
        )

        return {
            "score": result.total,
            "expected": expected,
            "predicted": {k: round(float(v), 2) for k, v in (predictions or {}).items()},
            "mean_abs_error_pct": result.raw["mean_abs_error_pct"],
            "dimension_scores": result.dimensions,
        }
