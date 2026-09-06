"""Crafting Engine — recipe-based item crafting for `card_board`/RPG-flavoured games.

app.py builds a fresh `CraftingEngine(game["crafting"])` per request (`/api/craft`,
`/api/crafting/available`) and calls `can_craft`, `craft`, `get_available_recipes`
against the run's `RunState`. No committed game JSON exercises a `crafting` block
yet, so the recipe schema below is derived from how app.py reads the engine's
output rather than from an example config: the `/api/crafting/available` handler
pulls `recipe.get("materials_status")`, `.get("inputs")`, `.get("outputs")`,
`.get("effects")`, `.get("unlocks")`, `.get("crafting_time_seconds")` off each dict
`get_available_recipes` returns, so those are exactly the keys each returned recipe
carries alongside `id`/`name`/`description`.

Config shape: {"recipes": [{id, name, description, inputs: {resource: qty},
outputs: {resource: qty}, effects: {resource: delta}, unlocks: [recipe_id, ...],
crafting_time_seconds}]}.

Inputs/outputs/effects apply straight to flat RunState attributes, mirroring how
choice `delta` dicts apply directly to top-level state attributes elsewhere in the
app (see mento_score.py's note on the same convention).
"""
from typing import Any, Dict, List, Tuple


def _get(state: Any, key: str, default=0):
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _set(state: Any, key: str, value) -> None:
    if isinstance(state, dict):
        state[key] = value
    else:
        setattr(state, key, value)


class CraftingEngine:
    def __init__(self, crafting_config: Dict[str, Any]):
        self.config = crafting_config or {}
        recipes = self.config.get("recipes", []) or []
        self.recipes: Dict[str, Dict[str, Any]] = {
            r["id"]: r for r in recipes if isinstance(r, dict) and r.get("id")
        }
        # A recipe named in another recipe's `unlocks` stays hidden until that
        # source recipe has actually been crafted once.
        self._gated_by: Dict[str, str] = {}
        for recipe in recipes:
            for unlocked_id in recipe.get("unlocks", []) or []:
                self._gated_by[unlocked_id] = recipe["id"]

    def _is_visible(self, recipe_id: str, state: Any) -> bool:
        gate = self._gated_by.get(recipe_id)
        if not gate:
            return True
        return gate in (_get(state, "crafted_recipes", []) or [])

    def _materials_status(self, recipe: Dict[str, Any], state: Any) -> Dict[str, Any]:
        status = {}
        for material, needed in (recipe.get("inputs") or {}).items():
            have = _get(state, material, 0) or 0
            status[material] = {"required": needed, "have": have, "sufficient": have >= needed}
        return status

    def can_craft(self, recipe_id: str, state: Any) -> Tuple[bool, str]:
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return False, "Unknown recipe"
        if not self._is_visible(recipe_id, state):
            return False, "Recipe not yet unlocked"
        for material, needed in (recipe.get("inputs") or {}).items():
            have = _get(state, material, 0) or 0
            if have < needed:
                return False, f"Not enough {material} (have {have}, need {needed})"
        return True, ""

    def craft(self, recipe_id: str, state: Any) -> Tuple[Any, str]:
        recipe = self.recipes[recipe_id]
        for material, qty in (recipe.get("inputs") or {}).items():
            _set(state, material, _get(state, material, 0) - qty)
        for item, qty in (recipe.get("outputs") or {}).items():
            _set(state, item, _get(state, item, 0) + qty)
        for resource, delta in (recipe.get("effects") or {}).items():
            _set(state, resource, _get(state, resource, 0) + delta)

        crafted = list(_get(state, "crafted_recipes", []) or [])
        if recipe_id not in crafted:
            crafted.append(recipe_id)
        _set(state, "crafted_recipes", crafted)

        return state, f"Crafted {recipe.get('name', recipe_id)}!"

    def get_available_recipes(self, state: Any) -> List[Dict[str, Any]]:
        available = []
        for recipe_id, recipe in self.recipes.items():
            if not self._is_visible(recipe_id, state):
                continue
            can, _reason = self.can_craft(recipe_id, state)
            entry = dict(recipe)
            entry["craftable"] = can
            entry["materials_status"] = self._materials_status(recipe, state)
            available.append(entry)
        return available
