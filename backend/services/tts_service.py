# backend/services/tts_service.py
"""Unified TTS wrapper for OpenAI TTS and ElevenLabs. Caches results."""
import hashlib
import os
from pathlib import Path
from typing import Literal, Optional

try:
    from backend.cost_tracker import record_cost
except ImportError:
    def record_cost(category: str, amount: float, meta: Optional[dict] = None) -> None:
        pass

Provider = Literal["openai", "elevenlabs"]
Lang = Literal["en", "hi", "hi_mix"]

_DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent / "assets" / "audio" / "cache"
_DEFAULT_VOICES = {
    "openai": {"en": "nova", "hi": "nova", "hi_mix": "nova"},
    "elevenlabs": {
        "en": os.getenv("ELEVENLABS_VOICE_EN", "21m00Tcm4TlvDq8ikWAM"),
        "hi": os.getenv("ELEVENLABS_VOICE_HI", "21m00Tcm4TlvDq8ikWAM"),
        "hi_mix": os.getenv("ELEVENLABS_VOICE_HI_MIX", "21m00Tcm4TlvDq8ikWAM"),
    },
}

def _cache_dir() -> Path:
    p = Path(os.getenv("TTS_CACHE_DIR", _DEFAULT_CACHE_DIR))
    p.mkdir(parents=True, exist_ok=True)
    return p

def cache_key_for(text: str, voice: str, lang: str, provider: str) -> str:
    raw = f"{provider}|{lang}|{voice}|{text}".encode()
    return hashlib.sha1(raw).hexdigest()

def _read_cache(key: str) -> Optional[bytes]:
    p = _cache_dir() / f"{key}.mp3"
    return p.read_bytes() if p.exists() else None

def _write_cache(key: str, data: bytes) -> None:
    dest = _cache_dir() / f"{key}.mp3"
    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(data)
    tmp.replace(dest)

def synthesize(
    text: str,
    provider: Provider = "openai",
    lang: Lang = "en",
    voice: Optional[str] = None,
) -> bytes:
    voice = voice or _DEFAULT_VOICES[provider][lang]
    key = cache_key_for(text, voice, lang, provider)
    cached = _read_cache(key)
    if cached:
        return cached
    if provider == "openai":
        data = _synthesize_openai(text, voice)
    elif provider == "elevenlabs":
        data = _synthesize_elevenlabs(text, voice)
    else:
        raise ValueError(f"unknown provider: {provider}")
    record_cost(f"tts_{provider}", _estimate_cost(text, provider), {"voice": voice, "lang": lang})
    _write_cache(key, data)
    return data

def _synthesize_openai(text: str, voice: str) -> bytes:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    r = client.audio.speech.create(model="tts-1", voice=voice, input=text)
    return r.content

def _synthesize_elevenlabs(text: str, voice_id: str) -> bytes:
    from elevenlabs.client import ElevenLabs
    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    chunks = client.text_to_speech.convert(voice_id=voice_id, text=text, model_id="eleven_multilingual_v2")
    return b"".join(chunks)

def _estimate_cost(text: str, provider: str) -> float:
    chars = len(text)
    if provider == "openai":
        return (chars / 1_000_000) * 15.0  # ~$15/M chars for tts-1
    return (chars / 1000) * 0.30  # ~$0.30/1000 chars elevenlabs multilingual
