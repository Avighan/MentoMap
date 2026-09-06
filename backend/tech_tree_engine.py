"""Tech Tree Engine — prerequisite-gated research for strategy/city-builder games.

app.py builds a fresh `TechTreeEngine(game.get("tech_tree") or game.get("techTree"))`
per request (`/api/research`, `/api/tech-tree/available`), gated on the config
having a `"nodes"` list. `can_research` is called for its truthiness alone
(`if not tech_tree_engine.can_research(...)`), so it returns a plain bool, unlike
`CraftingEngine.can_craft` which also returns a reason string. The node schema
below (id, name, description, icon, prerequisites, cost, effects) mirrors the
`tech_tree` arrays already used elsewhere in games/*.json (e.g.
age-of-empires-conquest.json) for an unrelated building-tech system, and matches
exactly the fields the `/api/tech-tree/available` handler reads off each node:
`.get("cost")`, `.get("prerequisites")`, plus the `researchable`/`condition_met`/
`can_afford` flags this engine adds.

Costs/effects apply to flat RunState attributes, same convention as CraftingEngine.
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


class TechTreeEngine:
    def __init__(self, tech_tree: Dict[str, Any]):
        self.config = tech_tree or {}
        nodes = self.config.get("nodes", []) or []
        self.techs: Dict[str, Dict[str, Any]] = {
            n["id"]: n for n in nodes if isinstance(n, dict) and n.get("id")
        }

    def _unlocked(self, state: Any) -> List[str]:
        return list(_get(state, "unlocked_techs", []) or [])

    def _can_afford(self, tech: Dict[str, Any], state: Any) -> bool:
        return all(
            _get(state, resource, 0) >= amount
            for resource, amount in (tech.get("cost") or {}).items()
        )

    def _condition_met(self, tech: Dict[str, Any], unlocked: List[str]) -> bool:
        return all(prereq in unlocked for prereq in (tech.get("prerequisites") or []))

    def can_research(self, tech_id: str, state: Any) -> bool:
        tech = self.techs.get(tech_id)
        if not tech:
            return False
        unlocked = self._unlocked(state)
        if tech_id in unlocked:
            return False
        return self._condition_met(tech, unlocked) and self._can_afford(tech, state)

    def _apply_effects(self, effects: Dict[str, Any], state: Any) -> None:
        for key, value in effects.items():
            if key.startswith("unlock_") and isinstance(value, list):
                existing = list(_get(state, key, []) or [])
                for v in value:
                    if v not in existing:
                        existing.append(v)
                _set(state, key, existing)
            elif key.startswith("bonus_") and isinstance(value, (int, float)):
                resource = key[len("bonus_"):]
                _set(state, resource, _get(state, resource, 0) + value)
            elif isinstance(value, (int, float)):
                _set(state, key, _get(state, key, 0) + value)

    def research(self, tech_id: str, state: Any) -> Tuple[Any, str]:
        tech = self.techs[tech_id]
        for resource, amount in (tech.get("cost") or {}).items():
            _set(state, resource, _get(state, resource, 0) - amount)

        unlocked = self._unlocked(state)
        if tech_id not in unlocked:
            unlocked.append(tech_id)
        _set(state, "unlocked_techs", unlocked)

        self._apply_effects(tech.get("effects") or {}, state)

        return state, f"Researched {tech.get('name', tech_id)}!"

    def get_available_techs(self, state: Any) -> List[Dict[str, Any]]:
        unlocked = self._unlocked(state)
        out = []
        for tech_id, tech in self.techs.items():
            if tech_id in unlocked:
                continue
            condition_met = self._condition_met(tech, unlocked)
            can_afford = self._can_afford(tech, state)
            entry = dict(tech)
            entry["researchable"] = condition_met and can_afford
            entry["condition_met"] = condition_met
            entry["can_afford"] = can_afford
            out.append(entry)
        return out
