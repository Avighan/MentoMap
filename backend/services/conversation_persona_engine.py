"""Generalized persona conversation engine. One persona JSON + history → next reply.

Used by interview_sim (Phase B) and reusable by negotiation/dating-sim."""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from backend.llm import call_llm  # existing helper
except ImportError:
    call_llm = None

# Resolve absolute path to backend/personas/ from this file's location.
_PERSONAS_DIR = Path(__file__).resolve().parent.parent / "personas"


def load_persona(category: str, persona_id: str) -> Dict[str, Any]:
    p = _PERSONAS_DIR / category / f"{persona_id}.json"
    if not p.exists():
        raise FileNotFoundError(f"persona not found: {category}/{persona_id}")
    return json.loads(p.read_text())


def list_personas(category: str) -> List[Dict[str, Any]]:
    d = _PERSONAS_DIR / category
    if not d.exists():
        return []
    return [json.loads(p.read_text()) for p in d.glob("*.json")]


def next_reply(persona: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
    """history: [{role: 'user'|'persona', text: str}, ...]"""
    if call_llm is None:
        return "(persona engine: LLM not configured)"
    messages = [{"role": "system", "content": persona["system_prompt"]}]
    for turn in history:
        role = "user" if turn["role"] == "user" else "assistant"
        messages.append({"role": role, "content": turn["text"]})
    return call_llm(messages=messages, max_tokens=200, temperature=0.8)
