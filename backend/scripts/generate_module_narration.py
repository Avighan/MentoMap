"""Batch narration generator for Mento module audio (EN + HI + Hinglish).

Usage (CLI):
    cd backend
    python3 -m scripts.generate_module_narration [module_id] [langs] [provider]

    module_id  — default: mento_entrepreneur_4week
    langs      — comma-separated, default: en,hi,hi_mix
    provider   — default: elevenlabs
"""
import json
import logging
import re
import sys
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Optional LLM import (per Phase A convention)
# ---------------------------------------------------------------------------
try:
    from llm import llm_call  # type: ignore
except ImportError:
    llm_call = None  # type: ignore

# ---------------------------------------------------------------------------
# Optional TTS import
# ---------------------------------------------------------------------------
try:
    from services.tts_service import synthesize  # type: ignore
except ImportError:
    synthesize = None  # type: ignore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path constants (absolute, CWD-independent)
# ---------------------------------------------------------------------------
_BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent
_MODULES_DIR: Path = _BACKEND_ROOT / "modules"
_AUDIO_ROOT: Path = _BACKEND_ROOT / "assets" / "audio" / "module"

# Lesson types that get audio narration
_NARRATED_TYPES = {"lesson", "audio_lesson", "case_study_card", "failure_card"}

# ---------------------------------------------------------------------------
# HTML stripping
# ---------------------------------------------------------------------------
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    if not isinstance(text, str):
        return ""
    stripped = _HTML_TAG_RE.sub(" ", text)
    # collapse runs of whitespace
    return re.sub(r"\s+", " ", stripped).strip()


# Narration order for dict-shaped lesson.content
# (skip image_url, image_url_fallback — not narratable)
_NARRATION_KEYS = ("intro", "mento_says", "story_hook", "cards", "key_takeaway", "question")


def _flatten_content(content) -> str:
    """Reduce a lesson's content field to a single narration string.

    Supports three shapes:
    - str  → HTML-stripped string
    - list → joined string items / dict ``body`` fields
    - dict → values for keys in :data:`_NARRATION_KEYS` joined in reading order
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return _strip_html(content)
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(_strip_html(item))
            elif isinstance(item, dict):
                body = item.get("body") or item.get("text") or ""
                parts.append(_strip_html(body))
        return ". ".join(p for p in parts if p)
    if isinstance(content, dict):
        parts: List[str] = []
        for key in _NARRATION_KEYS:
            if key not in content:
                continue
            val = content[key]
            flat = _flatten_content(val)  # recurse for nested cards/lists
            if flat:
                parts.append(flat)
        return ". ".join(parts)
    return ""


# ---------------------------------------------------------------------------
# Public: build_script
# ---------------------------------------------------------------------------

def build_script(lesson: dict, lang: str = "en") -> str:
    """Return a narration script string for *lesson* in the requested *lang*.

    - Strips HTML and flattens dict/list ``lesson["content"]`` shapes.
    - Joins title and body: ``"<title>. <body>"``.
    - For ``lang in ("hi", "hi_mix")``: attempts LLM translation; on any
      error or if ``llm_call`` is None, falls back to the base English string.
    - Always returns a non-empty string when the lesson has content.
    """
    title: str = lesson.get("title", "")
    body = _flatten_content(lesson.get("content"))

    # Build base (English) script
    parts = [p for p in (title, body) if p]
    base = ". ".join(parts) if parts else ""

    if not base:
        return ""

    if lang == "en":
        return base

    # Hindi / Hinglish — attempt LLM translation, fall back to English
    if lang in ("hi", "hi_mix") and llm_call is not None:
        try:
            lang_label = "Hindi" if lang == "hi" else "Hinglish (Hindi-English mix)"
            prompt = (
                f"Translate the following educational narration script into {lang_label}. "
                f"Return only the translated text, no extra commentary.\n\n{base}"
            )
            result = llm_call(
                system_prompt="You are a translator producing natural classroom narration for Indian 12-year-old students.",
                user_prompt=prompt,
                response_json=False,
                temperature=0.4,
                max_tokens=600,
                purpose="module_narration_translate",
            )
            if result and result.strip():
                return result.strip()
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM translation failed for lang=%s: %s", lang, exc)

    # Fallback: return English base
    return base


# ---------------------------------------------------------------------------
# Public: generate_for_module
# ---------------------------------------------------------------------------

def generate_for_module(
    module_id: str,
    langs: Optional[List[str]] = None,
    provider: str = "elevenlabs",
) -> None:
    """Batch-generate audio for all narrated lessons in *module_id*.

    Idempotent — skips synthesis if the mp3 file already exists but still
    records the ``audio_urls`` entry.  Writes updated module JSON back to disk
    when done.
    """
    if langs is None:
        langs = ["en", "hi", "hi_mix"]

    module_path = _MODULES_DIR / f"{module_id}.json"
    if not module_path.exists():
        logger.error("Module file not found: %s", module_path)
        return

    with module_path.open(encoding="utf-8") as fh:
        module_data: dict = json.load(fh)

    weeks: List[dict] = module_data.get("weeks", [])
    changed = False

    for week in weeks:
        for lesson in week.get("lessons", []):
            lesson_type = lesson.get("type", "")
            if lesson_type not in _NARRATED_TYPES:
                continue

            lesson_id: str = lesson.get("lesson_id") or lesson.get("id", "unknown")
            audio_urls: dict = lesson.get("audio_urls", {})

            for lang in langs:
                out_path = _AUDIO_ROOT / module_id / lesson_id / f"{lang}.mp3"
                static_url = f"/static/audio/module/{module_id}/{lesson_id}/{lang}.mp3"

                # Always record URL regardless of synthesis
                if out_path.exists():
                    audio_urls[lang] = static_url
                    continue

                script = build_script(lesson, lang=lang)
                if not script:
                    logger.warning(
                        "Empty script for lesson=%s lang=%s — skipping.", lesson_id, lang
                    )
                    continue

                if synthesize is None:
                    logger.warning(
                        "TTS service unavailable — cannot synthesize lesson=%s lang=%s.",
                        lesson_id, lang,
                    )
                    continue

                try:
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    audio_bytes = synthesize(script, provider=provider, lang=lang)
                    tmp = out_path.with_suffix(".tmp")
                    tmp.write_bytes(audio_bytes)
                    tmp.replace(out_path)
                    audio_urls[lang] = static_url
                    logger.info("Synthesised %s", out_path)
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Synthesis failed for lesson=%s lang=%s: %s", lesson_id, lang, exc
                    )

            if audio_urls:
                lesson["audio_urls"] = audio_urls
                changed = True

    if changed:
        with module_path.open("w", encoding="utf-8") as fh:
            json.dump(module_data, fh, ensure_ascii=False, indent=2)
        logger.info("Updated module JSON: %s", module_path)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _args = sys.argv[1:]
    _module_id = _args[0] if len(_args) > 0 else "mento_entrepreneur_4week"
    _langs: List[str] = _args[1].split(",") if len(_args) > 1 else ["en", "hi", "hi_mix"]
    _provider = _args[2] if len(_args) > 2 else "elevenlabs"
    generate_for_module(_module_id, langs=_langs, provider=_provider)
