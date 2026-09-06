"""DialogueEngine — branching NPC conversation trees with relationship tracking.

app.py builds a fresh `DialogueEngine(game["dialogue"])` per request
(`/api/dialogue/*`) and reads `.npcs` / `.conversations` directly off the
instance as dicts — e.g. `dialogue_engine.npcs.get(npc_id, {})` and
`dialogue_engine.conversations.get(conversation_id, {})` — not through an
accessor method, so the constructor must normalise the config's `npcs` /
`conversations` (either a list or an id-keyed dict) into id-keyed dicts of
those exact attribute names.

No committed game JSON exercises `dialogue` yet, so the node/response schema
is otherwise inferred from what each method is required to return:
`start_conversation` must hand back a dict carrying `node_data.get("npc_id")`;
`choose_response` must hand back `(next_node_data, new_state, message)`, per
`next_node_data, new_state, result = dialogue_engine.choose_response(...)`.

Conversation shape:
{"id", "npc_id", "start_node", "requires": {"requires_conversation": id,
"min_relationship": n}, "nodes": {node_id: {"id", "text", "responses":
[{"id", "text", "next_node": id|null, "feedback", "effects": {"relationship": n,
resource: delta}}]}}}
"""
from typing import Any, Dict, List, Tuple


def _get(state: Any, key: str, default=None):
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def _set(state: Any, key: str, value) -> None:
    if isinstance(state, dict):
        state[key] = value
    else:
        setattr(state, key, value)


def _index_by_id(items: Any) -> Dict[str, Dict[str, Any]]:
    if isinstance(items, dict):
        return dict(items)
    return {
        item["id"]: item for item in (items or [])
        if isinstance(item, dict) and item.get("id")
    }


# Ordered high-to-low; first band whose threshold the relationship value clears wins.
_RELATIONSHIP_BANDS = [
    (75, "Beloved"),
    (40, "Friendly"),
    (10, "Warming Up"),
    (-10, "Neutral"),
    (-40, "Wary"),
    (float("-inf"), "Hostile"),
]


class DialogueEngine:
    def __init__(self, dialogue_config: Dict[str, Any]):
        self.config = dialogue_config or {}
        self.npcs: Dict[str, Dict[str, Any]] = _index_by_id(self.config.get("npcs"))
        self.conversations: Dict[str, Dict[str, Any]] = _index_by_id(self.config.get("conversations"))

    def _relationships(self, state: Any) -> Dict[str, float]:
        return dict(_get(state, "npc_relationships", {}) or {})

    def get_npc_relationship(self, npc_id: str, state: Any) -> float:
        default = self.npcs.get(npc_id, {}).get("default_relationship", 0)
        return self._relationships(state).get(npc_id, default)

    def get_relationship_status(self, npc_id: str, state: Any) -> str:
        value = self.get_npc_relationship(npc_id, state)
        for threshold, label in _RELATIONSHIP_BANDS:
            if value >= threshold:
                return label
        return _RELATIONSHIP_BANDS[-1][1]

    def _node(self, conversation: Dict[str, Any], node_id: str) -> Dict[str, Any]:
        return (conversation.get("nodes") or {}).get(node_id, {})

    def start_conversation(self, conversation_id: str, state: Any) -> Tuple[Dict[str, Any], Any]:
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return {"error": "Unknown conversation", "npc_id": None, "responses": []}, state

        start_node_id = conversation.get("start_node") or conversation.get("start")
        node_data = dict(self._node(conversation, start_node_id))
        node_data["npc_id"] = conversation.get("npc_id")
        node_data["conversation_id"] = conversation_id

        started = list(_get(state, "started_conversations", []) or [])
        if conversation_id not in started:
            started.append(conversation_id)
        _set(state, "started_conversations", started)

        return node_data, state

    def choose_response(
        self, conversation_id: str, node_id: str, response_id: str, state: Any
    ) -> Tuple[Dict[str, Any], Any, str]:
        conversation = self.conversations.get(conversation_id)
        if not conversation:
            return {"error": "Unknown conversation", "responses": []}, state, "Conversation not found"

        node = self._node(conversation, node_id)
        response = next(
            (r for r in (node.get("responses") or []) if r.get("id") == response_id), None
        )
        if not response:
            return {"error": "Unknown response", "responses": []}, state, "Response not found"

        npc_id = conversation.get("npc_id")
        effects = response.get("effects", {}) or {}
        if "relationship" in effects and npc_id:
            relationships = self._relationships(state)
            relationships[npc_id] = relationships.get(npc_id, 0) + effects["relationship"]
            _set(state, "npc_relationships", relationships)
        for resource, delta in effects.items():
            if resource == "relationship":
                continue
            _set(state, resource, _get(state, resource, 0) + delta)

        next_node_id = response.get("next_node")
        if next_node_id:
            next_node_data = dict(self._node(conversation, next_node_id))
            next_node_data["npc_id"] = npc_id
            next_node_data["conversation_id"] = conversation_id
        else:
            completed = list(_get(state, "completed_conversations", []) or [])
            if conversation_id not in completed:
                completed.append(conversation_id)
            _set(state, "completed_conversations", completed)
            next_node_data = {
                "npc_id": npc_id, "conversation_id": conversation_id,
                "ended": True, "responses": [],
            }

        result = response.get("feedback") or response.get("text", "")
        return next_node_data, state, result

    def get_available_conversations(self, state: Any) -> List[Dict[str, Any]]:
        completed = _get(state, "completed_conversations", []) or []
        started = _get(state, "started_conversations", []) or []
        out = []
        for conv_id, conversation in self.conversations.items():
            requires = conversation.get("requires", {}) or {}
            npc_id = conversation.get("npc_id")
            unlocked = True
            required_conv = requires.get("requires_conversation")
            if required_conv and required_conv not in completed:
                unlocked = False
            min_relationship = requires.get("min_relationship")
            if min_relationship is not None and self.get_npc_relationship(npc_id, state) < min_relationship:
                unlocked = False
            out.append({
                "id": conv_id,
                "npc_id": npc_id,
                "title": conversation.get("title", conversation.get("name", conv_id)),
                "description": conversation.get("description", ""),
                "completed": conv_id in completed,
                "started": conv_id in started,
                "available": unlocked,
            })
        return out
