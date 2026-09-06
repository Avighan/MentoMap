"""
LogicGridEngine — `logic_grid` zebra-puzzle scorer.

JSON declares categories (e.g. names, houses, drinks), a unique solution
(a list of dicts, one per row, with one value from each category), and
the constraints that make the puzzle solvable. The renderer lets the
student fill in their proposed assignment; on submit it POSTs the
proposed grid as a list of dicts.

Score = (cells matching solution / total cells) × 100. Default dimensions:
deductive_reasoning + working_memory.
"""
from typing import Any, Dict, List

from engines._grader_common import coerce_weights
from engines import scoring_registry

_DEFAULT_DIMENSION_WEIGHTS = {
    "deductive_reasoning": 0.7,
    "working_memory": 0.3,
}


class LogicGridEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.solution: List[Dict[str, Any]] = list(self.game_config.get("solution") or [])
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )

    def grade_results(self, submission: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.solution or not submission:
            return {
                "score": 0,
                "cells_correct": 0,
                "cells_total": 0,
                "rows_correct": 0,
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        # Match rows by the first category value (acts as the row key —
        # students must place the right values in the row matching the
        # known anchor). If anchor missing, match by index as fallback.
        if not self.solution:
            return {"score": 0, "dimension_scores": {dim: 0 for dim in self.weights}}
        anchor_key = list(self.solution[0].keys())[0]
        sub_by_anchor = {s.get(anchor_key): s for s in submission if isinstance(s, dict)}

        cells_correct = 0
        cells_total = 0
        rows_correct = 0
        for sol_row in self.solution:
            anchor_val = sol_row.get(anchor_key)
            sub_row = sub_by_anchor.get(anchor_val) or {}
            row_match = 0
            row_total = 0
            for k, v in sol_row.items():
                row_total += 1
                cells_total += 1
                if sub_row.get(k) == v:
                    row_match += 1
                    cells_correct += 1
            if row_match == row_total and row_total > 0:
                rows_correct += 1

        result = scoring_registry.compute(
            "fraction_correct", {"correct": cells_correct, "total": cells_total},
            {"weights": self.weights},
        )

        return {
            "score": result.total,
            "cells_correct": cells_correct,
            "cells_total": cells_total,
            "rows_correct": rows_correct,
            "rows_total": len(self.solution),
            "dimension_scores": result.dimensions,
        }
