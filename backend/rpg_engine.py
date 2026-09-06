"""RPGEngine — party management, equipment, and turn-based combat.

app.py builds a fresh `RPGEngine(game["rpg"])` per request (`/api/rpg/*`) and
drives turn-based combat itself (see `api_rpg_combat_action`): it reads
`combat_state["party"/"enemies"/"turn_order"/"current_turn"/"round"/"log"/
"active"/"result"]` directly as plain dicts/lists, calls `rpg_engine.Character(d)`
to wrap a raw combat-state member back into an object exposing `.is_alive()`,
`.current_hp`, `.current_mp`, `.id`, and expects `get_party()` to hand back
`Character` objects with a `.to_dict()`. `start_combat`'s combat_state is a
*separate* copy of the party (app.py syncs `current_hp`/`current_mp` back onto
`state.party` by hand after each action), which is why `execute_action` mutates
and returns `combat_state` in place rather than touching `state`.

No committed game JSON exercises `rpg` yet (the rpg-dungeon-quest.json game is a
plain `"rounds"` game reusing this system's theme, not its config), so the
party/enemy/item/skill catalogue schema below is inferred purely from the
attribute/key access patterns above.

Config shape: {"party": [{id, name, class, max_hp, max_mp, attack, defense,
speed, skills: [skill_id]}], "enemies": [{id, name, max_hp, attack, defense,
speed, skills}], "items": [{id, name, slot, effects: {heal}}], "skills":
[{id, name, mp_cost, power, heal}]}.
"""
import random
from typing import Any, Dict, List, Optional, Tuple


def _get(state: Any, key: str, default=None):
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _set(state: Any, key: str, value) -> None:
    if isinstance(state, dict):
        state[key] = value
    else:
        setattr(state, key, value)


class Character:
    """Wraps a party/enemy dict. Constructed both from `RunState.party` entries
    and from raw `combat_state["enemies"/"party"]` dicts (see
    `rpg_engine.Character(enemy)` in app.py's combat loop) — every field needs a
    default since neither source is guaranteed to carry every key."""

    def __init__(self, data: Dict[str, Any]):
        data = data or {}
        self.id = data.get("id")
        self.name = data.get("name", self.id or "Unknown")
        self.char_class = data.get("class", data.get("char_class", "adventurer"))
        self.level = data.get("level", 1)
        self.exp = data.get("exp", 0)
        self.max_hp = data.get("max_hp", data.get("hp", 100))
        self.current_hp = data.get("current_hp", self.max_hp)
        self.max_mp = data.get("max_mp", data.get("mp", 20))
        self.current_mp = data.get("current_mp", self.max_mp)
        self.attack = data.get("attack", data.get("atk", 10))
        self.defense = data.get("defense", data.get("def", 5))
        self.speed = data.get("speed", data.get("spd", 10))
        self.equipment = dict(data.get("equipment", {}) or {})
        self.skills = list(data.get("skills", []) or [])
        self.is_enemy = data.get("is_enemy", False)

    def is_alive(self) -> bool:
        return self.current_hp > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "class": self.char_class,
            "level": self.level,
            "exp": self.exp,
            "max_hp": self.max_hp,
            "current_hp": self.current_hp,
            "max_mp": self.max_mp,
            "current_mp": self.current_mp,
            "attack": self.attack,
            "defense": self.defense,
            "speed": self.speed,
            "equipment": self.equipment,
            "skills": self.skills,
            "is_enemy": self.is_enemy,
        }


def _exp_to_next_level(level: int) -> int:
    return level * 100


class RPGEngine:
    # Exposed as a class attribute so app.py's `rpg_engine.Character(enemy)` works
    # off any instance without a dedicated factory method.
    Character = Character

    def __init__(self, rpg_config: Dict[str, Any]):
        self.config = rpg_config or {}
        self.party_template = self.config.get("party", self.config.get("characters", [])) or []
        self.items = {i["id"]: i for i in (self.config.get("items", []) or []) if i.get("id")}
        self.skills = {s["id"]: s for s in (self.config.get("skills", []) or []) if s.get("id")}
        self.enemy_catalog = {e["id"]: e for e in (self.config.get("enemies", []) or []) if e.get("id")}

    # ---------- Party management ----------

    def initialize_party(self, state: Any) -> Any:
        party = []
        for template in self.party_template:
            member = dict(template)
            member.setdefault("level", 1)
            member.setdefault("exp", 0)
            member.setdefault("max_hp", member.get("hp", 100))
            member.setdefault("max_mp", member.get("mp", 20))
            member["current_hp"] = member["max_hp"]
            member["current_mp"] = member["max_mp"]
            member.setdefault("attack", member.get("atk", 10))
            member.setdefault("defense", member.get("def", 5))
            member.setdefault("speed", member.get("spd", 10))
            member.setdefault("equipment", {})
            member.setdefault("skills", [])
            party.append(member)
        _set(state, "party", party)
        return state

    def get_party(self, state: Any) -> List[Character]:
        return [Character(member) for member in (_get(state, "party", []) or [])]

    def save_party(self, state: Any, party: List[Character]) -> Any:
        _set(state, "party", [char.to_dict() for char in party])
        return state

    def equip_item(
        self, state: Any, character_id: str, slot: str, item_id: Optional[str]
    ) -> Tuple[Any, str]:
        party = _get(state, "party", []) or []
        member = next((m for m in party if m.get("id") == character_id), None)
        if member is None:
            return state, "Character not found"

        equipment = dict(member.get("equipment", {}) or {})
        if not item_id:
            equipment.pop(slot, None)
            message = f"Unequipped {slot}"
        else:
            item = self.items.get(item_id)
            if not item:
                return state, f"Unknown item: {item_id}"
            if item.get("slot", slot) != slot:
                return state, f"{item.get('name', item_id)} cannot be equipped in slot {slot}"
            equipment[slot] = item_id
            message = f"Equipped {item.get('name', item_id)} to {slot}"

        member["equipment"] = equipment
        _set(state, "party", party)
        return state, message

    def gain_exp(self, state: Any, character_id: str, exp_amount: int) -> Tuple[Any, bool]:
        party = _get(state, "party", []) or []
        member = next((m for m in party if m.get("id") == character_id), None)
        if member is None:
            return state, False

        member["exp"] = member.get("exp", 0) + max(0, exp_amount)
        level = member.get("level", 1)
        leveled_up = False
        while member["exp"] >= _exp_to_next_level(level):
            member["exp"] -= _exp_to_next_level(level)
            level += 1
            leveled_up = True
            member["max_hp"] = member.get("max_hp", 100) + 10
            member["max_mp"] = member.get("max_mp", 20) + 5
            member["attack"] = member.get("attack", 10) + 2
            member["defense"] = member.get("defense", 5) + 1
            # Level-up fully restores HP/MP, a standard RPG convention.
            member["current_hp"] = member["max_hp"]
            member["current_mp"] = member["max_mp"]
        member["level"] = level

        _set(state, "party", party)
        return state, leveled_up

    # ---------- Combat ----------

    def _spawn_enemies(self, enemy_ids: List[str]) -> List[Dict[str, Any]]:
        enemies = []
        counts: Dict[str, int] = {}
        for enemy_id in enemy_ids:
            template = self.enemy_catalog.get(enemy_id, {"id": enemy_id, "name": enemy_id})
            counts[enemy_id] = counts.get(enemy_id, 0) + 1
            instance_id = enemy_id if counts[enemy_id] == 1 else f"{enemy_id}_{counts[enemy_id]}"
            enemy = dict(template)
            enemy["id"] = instance_id
            enemy["name"] = template.get("name", enemy_id)
            enemy["max_hp"] = template.get("max_hp", template.get("hp", 50))
            enemy["current_hp"] = enemy["max_hp"]
            enemy["max_mp"] = template.get("max_mp", template.get("mp", 0))
            enemy["current_mp"] = enemy["max_mp"]
            enemy["attack"] = template.get("attack", template.get("atk", 8))
            enemy["defense"] = template.get("defense", template.get("def", 3))
            enemy["speed"] = template.get("speed", template.get("spd", 8))
            enemy["skills"] = template.get("skills", [])
            enemy["is_enemy"] = True
            enemies.append(enemy)
        return enemies

    def start_combat(self, state: Any, enemy_ids: List[str]) -> Tuple[Any, Dict[str, Any]]:
        party = [c.to_dict() for c in self.get_party(state) if c.is_alive()]
        enemies = self._spawn_enemies(enemy_ids)
        turn_order = [
            c["id"] for c in sorted(party + enemies, key=lambda c: c.get("speed", 0), reverse=True)
        ]
        combat_state = {
            "active": True,
            "party": party,
            "enemies": enemies,
            "turn_order": turn_order,
            "current_turn": 0,
            "round": 1,
            "log": [f"Combat started against {', '.join(e.get('name', e['id']) for e in enemies)}!"],
            "result": None,
        }
        return state, combat_state

    def _find_combatant(self, combat_state: Dict[str, Any], combatant_id: str) -> Optional[Dict[str, Any]]:
        for member in combat_state.get("party", []) + combat_state.get("enemies", []):
            if member.get("id") == combatant_id:
                return member
        return None

    def _roll_damage(self, actor: Dict[str, Any], target: Dict[str, Any], power: float = 1.0) -> int:
        base = max(1.0, actor.get("attack", 10) * power - target.get("defense", 0) * 0.5)
        if target.get("defending"):
            base *= 0.5
        variance = random.uniform(0.85, 1.15)
        return max(1, int(base * variance))

    def execute_action(
        self, combat_state: Dict[str, Any], actor_id: str, action: Dict[str, Any]
    ) -> Dict[str, Any]:
        actor = self._find_combatant(combat_state, actor_id)
        if not actor or actor.get("current_hp", 0) <= 0:
            return combat_state

        # A "defend" bonus only protects until this combatant's next action.
        actor["defending"] = False
        action_type = action.get("type", "attack")
        target_id = action.get("target_id")
        target = self._find_combatant(combat_state, target_id) if target_id else None
        log = combat_state.setdefault("log", [])

        if action_type == "defend":
            actor["defending"] = True
            log.append(f"{actor.get('name', actor_id)} defends.")
            return combat_state

        if action_type == "item":
            item = self.items.get(action.get("item_id"), {})
            heal = (item.get("effects") or {}).get("heal", item.get("heal", 0))
            heal_target = target or actor
            heal_target["current_hp"] = min(
                heal_target.get("max_hp", 100), heal_target.get("current_hp", 0) + heal
            )
            log.append(f"{actor.get('name', actor_id)} uses {item.get('name', 'an item')}.")
            return combat_state

        if not target:
            return combat_state

        if action_type == "skill":
            skill = self.skills.get(action.get("skill_id"), {})
            cost = skill.get("mp_cost", 0)
            if actor.get("current_mp", 0) < cost:
                log.append(f"{actor.get('name', actor_id)} doesn't have enough MP.")
                return combat_state
            actor["current_mp"] -= cost
            heal_amount = skill.get("heal")
            if heal_amount:
                target["current_hp"] = min(target.get("max_hp", 100), target.get("current_hp", 0) + heal_amount)
                log.append(f"{actor.get('name', actor_id)} heals {target.get('name')} for {heal_amount}.")
                return combat_state
            damage = self._roll_damage(actor, target, skill.get("power", 1.5))
            target["current_hp"] = max(0, target.get("current_hp", 0) - damage)
            log.append(
                f"{actor.get('name', actor_id)} uses {skill.get('name', 'a skill')} on "
                f"{target.get('name')} for {damage} damage."
            )
            return combat_state

        # Default: a basic attack.
        damage = self._roll_damage(actor, target, 1.0)
        target["current_hp"] = max(0, target.get("current_hp", 0) - damage)
        log.append(f"{actor.get('name', actor_id)} attacks {target.get('name')} for {damage} damage.")
        return combat_state

    def check_combat_end(self, combat_state: Dict[str, Any]) -> Optional[str]:
        if all(e.get("current_hp", 0) <= 0 for e in combat_state.get("enemies", [])):
            return "victory"
        if all(p.get("current_hp", 0) <= 0 for p in combat_state.get("party", [])):
            return "defeat"
        return None

    def get_enemy_action(self, enemy_char: Character, party_chars: List[Character]) -> Dict[str, Any]:
        alive_targets = [c for c in party_chars if c.is_alive()]
        if not alive_targets:
            return {"type": "defend", "target_id": enemy_char.id}
        target = random.choice(alive_targets)
        if enemy_char.skills and enemy_char.current_mp > 0 and random.random() < 0.3:
            return {"type": "skill", "skill_id": random.choice(enemy_char.skills), "target_id": target.id}
        return {"type": "attack", "target_id": target.id}
