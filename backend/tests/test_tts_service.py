# backend/tests/test_tts_service.py
import os
from pathlib import Path
import pytest
from backend.services.tts_service import synthesize, cache_key_for

def test_cache_key_is_deterministic():
    k1 = cache_key_for("hello", "voice_a", "en", "openai")
    k2 = cache_key_for("hello", "voice_a", "en", "openai")
    assert k1 == k2

def test_cache_key_changes_with_text():
    k1 = cache_key_for("hello", "voice_a", "en", "openai")
    k2 = cache_key_for("hi there", "voice_a", "en", "openai")
    assert k1 != k2

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_openai_tts_synthesize_returns_mp3_bytes():
    audio = synthesize("Hello from Mento.", provider="openai", lang="en")
    assert isinstance(audio, bytes)
    assert len(audio) > 1000
    assert audio[:3] == b"ID3" or audio[:2] == b"\xff\xfb"  # mp3 magic

@pytest.mark.skipif(not os.getenv("ELEVENLABS_API_KEY"), reason="needs ELEVENLABS_API_KEY")
def test_elevenlabs_tts_synthesize_returns_mp3_bytes():
    audio = synthesize("Hello from Mento.", provider="elevenlabs", lang="en")
    assert isinstance(audio, bytes)
    assert len(audio) > 1000

@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="needs OPENAI_API_KEY")
def test_cached_call_does_not_hit_api_twice(tmp_path, monkeypatch):
    monkeypatch.setenv("TTS_CACHE_DIR", str(tmp_path))
    text = "Hello cached."
    a1 = synthesize(text, provider="openai", lang="en")
    a2 = synthesize(text, provider="openai", lang="en")
    assert a1 == a2  # same bytes from cache
