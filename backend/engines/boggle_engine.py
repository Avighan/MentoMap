"""
BoggleEngine — `boggle` word-finder scorer.

JSON declares a 4×4 (or NxN) grid and a `dictionary` (list of valid words)
plus optional `min_word_length`. The renderer collects words the student
forms; on submit it POSTs {words: [...]}. The engine:

  - validates each word is in the JSON dictionary
  - validates each word is reachable on the grid (adjacent letters,
    no-reuse-of-cell — BFS)
  - dedupes
  - awards Boggle-style points by length (3-4: 1, 5: 2, 6: 3, 7: 5, 8+: 11)

Score = clamp(0..100, raw_points / max_possible_points * 100), where
max_possible_points is the same scoring applied to all dictionary words
that *are* findable on the grid. So the ceiling is grid-aware, not an
arbitrary points target.

Default dimensions: pattern_recognition + vocabulary.
"""
from typing import Any, Dict, List, Set, Tuple

from engines._grader_common import coerce_weights, distribute_dimension_scores

_DEFAULT_DIMENSION_WEIGHTS = {
    "pattern_recognition": 0.5,
    "vocabulary": 0.5,
}


def _word_points(word: str) -> int:
    n = len(word)
    if n <= 4:
        return 1
    if n == 5:
        return 2
    if n == 6:
        return 3
    if n == 7:
        return 5
    return 11


def _findable_on_grid(word: str, grid: List[List[str]]) -> bool:
    """DFS — can we trace `word` on adjacent cells without reusing a cell?"""
    if not word or not grid or not grid[0]:
        return False
    rows, cols = len(grid), len(grid[0])
    word_lower = word.lower()
    grid_lower = [[(c or "").lower() for c in row] for row in grid]

    def neighbors(r: int, c: int):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    yield nr, nc

    def dfs(r: int, c: int, idx: int, used: Set[Tuple[int, int]]) -> bool:
        if grid_lower[r][c] != word_lower[idx]:
            return False
        if idx == len(word_lower) - 1:
            return True
        used.add((r, c))
        for nr, nc in neighbors(r, c):
            if (nr, nc) not in used and dfs(nr, nc, idx + 1, used):
                return True
        used.remove((r, c))
        return False

    for r in range(rows):
        for c in range(cols):
            if grid_lower[r][c] == word_lower[0] and dfs(r, c, 0, set()):
                return True
    return False


class BoggleEngine:
    def __init__(self, game_config: Dict[str, Any]):
        self.game_config = game_config or {}
        self.grid: List[List[str]] = list(self.game_config.get("grid") or [])
        self.dictionary: Set[str] = {
            w.lower() for w in (self.game_config.get("dictionary") or [])
            if isinstance(w, str)
        }
        self.min_word_length = int(self.game_config.get("min_word_length") or 3)
        self.weights = coerce_weights(
            self.game_config.get("dimension_scoring_weights"),
            _DEFAULT_DIMENSION_WEIGHTS,
        )

    def _max_possible_points(self) -> int:
        if not self.grid or not self.dictionary:
            return 0
        total = 0
        for w in self.dictionary:
            if len(w) < self.min_word_length:
                continue
            if _findable_on_grid(w, self.grid):
                total += _word_points(w)
        return total

    def grade_results(self, words: List[str]) -> Dict[str, Any]:
        seen: Set[str] = set()
        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        for w in (words or []):
            if not isinstance(w, str):
                continue
            wl = w.lower().strip()
            if not wl or wl in seen:
                continue
            seen.add(wl)
            if len(wl) < self.min_word_length:
                rejected.append({"word": wl, "reason": "too_short"})
                continue
            if wl not in self.dictionary:
                rejected.append({"word": wl, "reason": "not_in_dictionary"})
                continue
            if not _findable_on_grid(wl, self.grid):
                rejected.append({"word": wl, "reason": "not_on_grid"})
                continue
            accepted.append({"word": wl, "points": _word_points(wl)})

        raw = sum(a["points"] for a in accepted)
        ceiling = max(self._max_possible_points(), 1)
        score = int(round(min(raw, ceiling) / ceiling * 100))

        return {
            "score": score,
            "raw_points": raw,
            "max_possible_points": ceiling,
            "accepted": accepted,
            "rejected": rejected,
            "dimension_scores": distribute_dimension_scores(score, self.weights),
        }
