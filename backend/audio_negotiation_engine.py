"""
Audio Negotiation Engine — voice-driven negotiation rounds.

Wraps the existing text-based negotiation LLM helpers (`llm.negotiation_ai_response`,
`llm.evaluate_negotiation_outcome`) with speech-to-text / text-to-speech so a
`negotiation` game_type game whose `negotiation_config` opts in to audio mode
can be played by voice instead of typed chat.

A game opts in by setting one of the following (checked by
`is_audio_negotiation_game`):
  - negotiation_config.audio_enabled = true
  - negotiation_config.mode in ("audio", "voice")
  - top-level audio_negotiation_enabled = true

Rounds are the game's `negotiation_config.scenarios` (or the historical
`negotiation_game.scenarios` / `session_game.scenarios` / `investor_pitch_game.scenarios`
wrappers) — each scenario is treated as one voice negotiation round with its
own objective and AI persona.
"""

import io
import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

import llm

logger = logging.getLogger(__name__)


class STTProvider(Enum):
    OPENAI_WHISPER = "openai_whisper"
    BROWSER = "browser"


class TTSProvider(Enum):
    OPENAI_TTS = "openai_tts"
    BROWSER = "browser"


# Wrapper keys (in priority order) that may hold a `scenarios` list, mirroring
# schemas._find_scenarios_wrapper so any game that already validates as a
# negotiation-type game is automatically round-shaped for this engine.
_WRAPPER_KEYS = (
    "negotiation_config",
    "session_game",
    "negotiation_game",
    "debate_game",
    "investor_pitch_game",
    "mock_interview",
)


def _find_wrapper(game: Dict[str, Any]):
    """Return (wrapper_key, wrapper_obj, scenarios_list) or (None, None, None)."""
    for key in _WRAPPER_KEYS:
        wrapper = game.get(key)
        if isinstance(wrapper, dict) and isinstance(wrapper.get("scenarios"), list) and wrapper["scenarios"]:
            return key, wrapper, wrapper["scenarios"]
    if isinstance(game.get("scenarios"), list) and game["scenarios"]:
        return "scenarios", game, game["scenarios"]
    return None, None, None


def _audio_flag(game: Dict[str, Any], wrapper: Optional[Dict[str, Any]]) -> bool:
    if game.get("audio_negotiation_enabled"):
        return True
    if game.get("audio_negotiation"):
        return True
    for src in (wrapper, game):
        if not isinstance(src, dict):
            continue
        if src.get("audio_enabled"):
            return True
        mode = str(src.get("mode", "")).lower()
        if mode in ("audio", "voice"):
            return True
    return False


def is_audio_negotiation_game(game: Optional[Dict[str, Any]]) -> bool:
    """True if `game` is a negotiation game explicitly configured for voice play."""
    if not isinstance(game, dict):
        return False
    if game.get("game_type") not in ("negotiation", "negotiation_series"):
        return False
    _, wrapper, scenarios = _find_wrapper(game)
    if not scenarios:
        return False
    return _audio_flag(game, wrapper)


class AudioNegotiationEngine:
    """Runs one negotiation game's rounds over voice (STT in, TTS out)."""

    def __init__(self, game: Dict[str, Any]):
        self.game = game
        _, self.wrapper, self.rounds = _find_wrapper(game)
        self.rounds = self.rounds or []
        self.stt_provider = STTProvider.OPENAI_WHISPER
        self.tts_provider = TTSProvider.OPENAI_TTS
        self.voice_settings = {
            "voice": (self.wrapper or {}).get("voice", "nova"),
            "model": "tts-1",
            "speed": 1.0,
        }

    def is_enabled(self) -> bool:
        return llm.llm_enabled()

    def get_total_rounds(self) -> int:
        return len(self.rounds)

    def get_round_config(self, index: int) -> Optional[Dict[str, Any]]:
        if index is None or index < 0 or index >= len(self.rounds):
            return None
        scenario = self.rounds[index]
        round_config = dict(scenario)
        round_config.setdefault("id", scenario.get("scenario_id") or f"round-{index}")
        round_config.setdefault(
            "objective", scenario.get("your_objective") or scenario.get("objective") or scenario.get("description", "")
        )
        round_config.setdefault(
            "ai_persona", scenario.get("other_party") or scenario.get("opponent") or scenario.get("ai_persona") or {}
        )
        round_config.setdefault("max_turns", scenario.get("conversation_turns", 6))
        return round_config

    # ---------- STT / TTS ----------

    def transcribe_audio(self, audio_file, audio_format: str = "webm") -> str:
        """Transcribe an uploaded audio file (werkzeug FileStorage) via OpenAI Whisper."""
        client = llm._client()
        audio_bytes = audio_file.read()
        buf = io.BytesIO(audio_bytes)
        buf.name = f"recording.{audio_format}"
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=buf,
            language="en",
        )
        try:
            from cost_tracker import log_cost
            duration_seconds = len(audio_bytes) / 32000
            log_cost("stt", "whisper-1", purpose="audio_negotiation_transcribe", duration_seconds=duration_seconds)
        except Exception as e:
            logger.debug("Suppressed %s: %s", type(e).__name__, e)
        return result.text or ""

    def synthesize_speech(self, text: str) -> bytes:
        """Synthesize speech for `text` via OpenAI TTS. Returns raw MP3 bytes."""
        client = llm._client()
        response = client.audio.speech.create(
            model=self.voice_settings.get("model", "tts-1"),
            voice=self.voice_settings.get("voice", "nova"),
            input=text[:4096],
        )
        try:
            from cost_tracker import log_cost
            log_cost("tts", self.voice_settings.get("model", "tts-1"),
                      purpose="audio_negotiation_speak", characters=len(text[:4096]))
        except Exception as e:
            logger.debug("Suppressed %s: %s", type(e).__name__, e)
        return response.content

    # ---------- Conversation ----------

    def _scenario_data(self, round_config: Dict[str, Any]) -> Dict[str, Any]:
        """Adapt a round_config into the `scenario_data` shape llm.negotiation_ai_response expects."""
        scenario_data = dict(round_config)
        scenario_data.setdefault("other_party", round_config.get("ai_persona"))
        scenario_data.setdefault("conversation_turns", round_config.get("max_turns", 6))
        scenario_data.setdefault("phases", round_config.get("phases", ["Opening", "Exploration", "Bargaining", "Closing"]))
        scenario_data.setdefault("title", round_config.get("title", ""))
        return scenario_data

    def process_conversation_turn(
        self,
        user_message: str,
        round_config: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        current_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Advance the negotiation by one turn. Returns ai_response/assessment/updated_state/should_progress."""
        scenario_data = self._scenario_data(round_config)
        current_turn = sum(1 for m in conversation_history if m.get("speaker") == "student")

        # negotiation_ai_response speaks the "relationship_score" vocabulary; audio
        # rounds track rapport/understanding/assertiveness — bridge the two so the
        # calibrated LLM prompt (which cites `state.relationship_score`) still works.
        bridged_state = dict(current_state)
        bridged_state.setdefault("relationship_score", current_state.get("rapport_score", 50))

        result = llm.negotiation_ai_response(
            user_message=user_message,
            scenario_data=scenario_data,
            conversation_history=conversation_history,
            current_turn=current_turn,
            state=bridged_state,
        )

        analysis = result.get("analysis", {}) or {}

        def _impact(key: str) -> float:
            v = analysis.get(key, 0)
            if isinstance(v, dict):
                return float(v.get("value", 0) or 0)
            try:
                return float(v or 0)
            except (TypeError, ValueError):
                return 0.0

        updated_state = dict(current_state)
        updated_state["rapport_score"] = max(0, min(100, current_state.get("rapport_score", 50) + _impact("relationship_impact")))
        updated_state["understanding_score"] = max(0, min(100, current_state.get("understanding_score", 50) + _impact("empathy_impact")))
        updated_state["assertiveness_score"] = max(0, min(100, current_state.get("assertiveness_score", 50) + _impact("assertiveness_impact")))

        max_turns = round_config.get("max_turns", 6)
        should_progress = bool(result.get("agreement_reached")) or (current_turn + 1) >= max_turns

        return {
            "ai_response": result.get("response", ""),
            "assessment": analysis,
            "updated_state": updated_state,
            "should_progress": should_progress,
            "phase": result.get("phase", "conversation"),
            "negotiation_progress": result.get("negotiation_progress", 0),
        }

    def evaluate_round_completion(
        self,
        round_config: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
        final_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Score a completed round via the shared LLM negotiation-outcome evaluator."""
        scenario_data = self._scenario_data(round_config)
        bridged_state = dict(final_state)
        bridged_state.setdefault("relationship_score", final_state.get("rapport_score", 50))
        return llm.evaluate_negotiation_outcome(
            scenario_data=scenario_data,
            conversation_history=conversation_history,
            final_state=bridged_state,
        )


def create_audio_negotiation_engine(game: Optional[Dict[str, Any]]) -> Optional[AudioNegotiationEngine]:
    """Build an AudioNegotiationEngine for `game`, or None if the game isn't round-shaped."""
    if not isinstance(game, dict):
        return None
    _, _, scenarios = _find_wrapper(game)
    if not scenarios:
        return None
    return AudioNegotiationEngine(game)
