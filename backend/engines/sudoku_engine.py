"""
SudokuEngine — `sudoku` constraint-solver scorer.

JSON declares an initial 9×9 puzzle and the unique solution. The renderer
lets the student fill cells; on submit it POSTs the final 9×9 grid plus
hint usage count. The engine grades:

  - cells_correct = matches with the solution / 81
  - hint penalty: each hint reduces the cap on perfect score
  - validity bonus: only awarded if grid satisfies row/col/box constraints

Score = max(0, base * 100 - hint_penalty), where base ∈ [0, 1] is fraction
of cells correct AND the grid is a legal Sudoku solution.

Default dimensions: deductive_reasoning + persistence.
"""
from typing import Any, Dict, List

from engines._grader_common import coerce_weights, distribute_dimension_scores

_DEFAULT_DIMENSION_WEIGHTS = {
    "deductive_reasoning": 0.6,
    "persistence": 0.4,
}


def _is_valid_sudoku(grid: List[List[int]]) -> bool:
    """A solved (or partially-filled) grid is valid if no row/col/box has dupes."""
    if len(grid) != 9 or any(len(row) != 9 for row in grid):
        return False
    for i in range(9):
        row = [v for v in grid[i] if v]
        col = [grid[r][i] for r in range(9) if grid[r][i]]
        if len(set(row)) != len(row) or len(set(col)) != len(col):
            return False
    for br in range(3):
        for bc in range(3):
            box = [grid[br * 3 + r][bc * 3 + c] for r in range(3) for c in range(3) if grid[br * 3 + r][bc * 3 + c]]
            if len(set(box)) != len(box):
                return False
    return True


class SudokuEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.solution: List[List[int]] = list(self.game_config.get("solution") or [])
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )
        # Each hint costs 5 points (cap), tunable via JSON.
        self.hint_penalty_per_use = int(self.game_config.get("hint_penalty") or 5)

    def grade_results(self, submission: Dict[str, Any]) -> Dict[str, Any]:
        grid = submission.get("grid") if isinstance(submission, dict) else None
        try:
            hints_used = int((submission or {}).get("hints_used", 0))
        except (TypeError, ValueError):
            hints_used = 0
        if not grid or len(self.solution) != 9:
            return {
                "score": 0,
                "cells_correct": 0,
                "valid": False,
                "hints_used": hints_used,
                "dimension_scores": {dim: 0 for dim in self.weights},
            }

        # Coerce grid cells to ints (0 = blank).
        coerced: List[List[int]] = []
        for row in grid:
            row_out: List[int] = []
            for v in row:
                try:
                    row_out.append(int(v))
                except (TypeError, ValueError):
                    row_out.append(0)
            coerced.append(row_out)

        cells_correct = 0
        for r in range(9):
            for c in range(9):
                if r < len(coerced) and c < len(coerced[r]) and coerced[r][c] == self.solution[r][c]:
                    cells_correct += 1
        base = cells_correct / 81

        valid = _is_valid_sudoku(coerced)
        # Validity bonus: invalid grids cap at 80% of base.
        if not valid:
            base *= 0.8

        score = int(round(base * 100)) - (hints_used * self.hint_penalty_per_use)
        score = max(0, min(100, score))

        return {
            "score": score,
            "cells_correct": cells_correct,
            "valid": valid,
            "hints_used": hints_used,
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
