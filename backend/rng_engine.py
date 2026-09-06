"""RNGEngine — deterministic, replayable randomness for procedural content.

app.py seeds one `RNGEngine(f"{run_id}_{...}_{state.round_index}")` per request
(see the `/api/procedural/*` routes), not once per run — re-rolling the same
round on the same run must reproduce the same loot/event/template outcome, so
the seed *string* is the sole source of randomness, never wall-clock entropy.
`random.Random(seed)` gives exactly that guarantee (same seed -> same stream)
without a third-party dependency.

`weighted_choice` and `randint` are the two methods app.py calls directly
(`rng.weighted_choice(weights)`, `rng.randint(min_qty, max_qty)`); the rest are
generic conveniences for `TemplateEngine`, which is handed the same engine
instance to keep every random draw in one generated round on one seeded stream.
"""
import random
from typing import Dict, List, Sequence, TypeVar

T = TypeVar("T")


class RNGEngine:
    def __init__(self, seed: str):
        self.seed = seed
        self._rng = random.Random(seed)

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, options: Sequence[T]) -> T:
        return self._rng.choice(list(options))

    def shuffle(self, items: List[T]) -> List[T]:
        shuffled = list(items)
        self._rng.shuffle(shuffled)
        return shuffled

    def sample(self, options: Sequence[T], k: int) -> List[T]:
        pool = list(options)
        return self._rng.sample(pool, min(k, len(pool)))

    def roll_dice(self, sides: int = 6, count: int = 1) -> int:
        return sum(self._rng.randint(1, sides) for _ in range(count))

    def weighted_choice(self, weights: Dict[str, float]) -> str:
        """Pick one key from `{id: weight}` — exactly the shape app.py builds from
        `item["weight"]`/`event["weight"]` before calling this for loot/event rolls."""
        ids = list(weights.keys())
        if not ids:
            raise ValueError("weighted_choice requires at least one option")
        totals = [max(0.0, float(w)) for w in weights.values()]
        total = sum(totals)
        if total <= 0:
            return self._rng.choice(ids)
        roll = self._rng.random() * total
        cumulative = 0.0
        for key, weight in zip(ids, totals):
            cumulative += weight
            if roll <= cumulative:
                return key
        return ids[-1]
