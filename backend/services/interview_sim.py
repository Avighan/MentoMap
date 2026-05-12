"""Customer-interview simulator: persona-driven voice conversation.

Persistent conversation state on disk (JSON per conversation).
Pure service — no HTTP. Wraps:
  - conversation_persona_engine for persona loading + LLM replies
  - tts_service for spoken persona audio

Depth score = number of distinct "why"-style probing questions the user asked
(counted via simple regex on English + Hindi/Devanagari forms).
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Tuple

from services.conversation_persona_engine import load_persona, next_reply
from services.tts_service import synthesize

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
CONV_DIR = _BACKEND_ROOT / "data" / "interview_sim_convs"
CONV_DIR.mkdir(parents=True, exist_ok=True)

_DISK_LOCK = Lock()  # intra-process atomicity for save/load


@dataclass
class ConvState:
    conv_id: str
    user_id: str
    module_id: str
    persona: Dict[str, Any]
    turns: List[Dict[str, Any]] = field(default_factory=list)


def _conv_path(conv_id: str) -> Path:
    return CONV_DIR / f"{conv_id}.json"


def _save(state: ConvState) -> None:
    payload = {
        "conv_id": state.conv_id,
        "user_id": state.user_id,
        "module_id": state.module_id,
        "persona_id": state.persona.get("persona_id"),
        "turns": state.turns,
    }
    p = _conv_path(state.conv_id)
    tmp = p.with_suffix(".tmp")
    with _DISK_LOCK:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)


def _load(conv_id: str) -> ConvState:
    p = _conv_path(conv_id)
    if not p.exists():
        raise FileNotFoundError(f"conv not found: {conv_id}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    persona = load_persona("entrepreneur", raw["persona_id"])
    return ConvState(
        conv_id=raw["conv_id"],
        user_id=raw["user_id"],
        module_id=raw["module_id"],
        persona=persona,
        turns=raw.get("turns", []),
    )


def start_conversation(user_id: str, module_id: str, persona_id: str) -> ConvState:
    persona = load_persona("entrepreneur", persona_id)
    state = ConvState(
        conv_id=uuid.uuid4().hex,
        user_id=user_id,
        module_id=module_id,
        persona=persona,
        turns=[],
    )
    _save(state)
    return state


def take_turn(conv_id: str, user_text: str) -> Tuple[ConvState, str, bytes]:
    """Advance the conversation by one user → persona exchange.

    Returns (state, persona_reply_text, persona_reply_audio_bytes).
    """
    state = _load(conv_id)
    state.turns.append({"role": "user", "text": user_text})
    reply_text = next_reply(state.persona, state.turns)
    state.turns.append({"role": "persona", "text": reply_text})
    _save(state)
    reply_audio = synthesize(
        reply_text,
        provider="openai",
        lang=state.persona.get("voice_lang", "en"),
        voice=state.persona.get("voice_id_openai"),
    )
    return state, reply_text, reply_audio


# Match English "why" word OR Devanagari "क्यों" (with word boundaries on the EN side).
_WHY_RE = re.compile(r"\bwhy\b|क्यों", re.IGNORECASE)


def _count_whys(turns: List[Dict[str, Any]]) -> int:
    return sum(
        1
        for t in turns
        if t.get("role") == "user" and _WHY_RE.search(t.get("text", "") or "")
    )


def end_conversation(state: ConvState) -> Dict[str, Any]:
    whys = _count_whys(state.turns)
    threshold = int(state.persona.get("reveal_threshold", 3))
    hint = state.persona.get("hidden_pain_point", "")
    if whys >= threshold:
        missed = "Good interview."
    else:
        missed = f"You stopped digging too early. The deeper truth was: {hint}"
    return {
        "transcript": state.turns,
        "depth_score": min(whys, 5),
        "missed_note": missed,
        "persona_display_name": state.persona.get("display_name"),
    }
