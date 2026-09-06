"""AI hero-image generation for game rounds/scenes/stocks, with a local cache.

Call sites (app.py's story-image routes) always try `check_cached()` first,
then `generate_story_image()` on a miss. When `OPENAI_API_KEY` is set (see
llm.py's `llm_enabled()` — the same env-var gate used everywhere else in
this codebase for AI features), this calls DALL-E; otherwise it falls back
to pollinations.ai's free, keyless image API (`get_pollinations_fallback`),
so image URLs are always real and renderable even with no API key
configured, just without a paid model behind them.
"""
import hashlib
import json
import logging
import os
import urllib.parse
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(os.path.dirname(_THIS_DIR), "data")
    d = os.path.join(base, "story_images")
    os.makedirs(d, exist_ok=True)
    return d


def _cache_path() -> str:
    return os.path.join(_data_dir(), "cache.json")


def _cache_key(game_id: str, round_id: str) -> str:
    return f"{game_id}::{round_id}"


def _load_cache() -> Dict[str, str]:
    path = _cache_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache: Dict[str, str]) -> None:
    path = _cache_path()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(cache, f)
    os.replace(tmp_path, path)


def check_cached(game_id: str, round_id: str) -> Optional[str]:
    return _load_cache().get(_cache_key(game_id, round_id))


def get_pollinations_fallback(image_prompt: str, style: str = "vivid") -> str:
    """A deterministic, keyless image URL via pollinations.ai's public API —
    the same prompt always resolves to the same seed, so repeated calls for
    the same round return a stable-looking image without needing our own
    caching to prevent it changing on every page load.
    """
    seed = int(hashlib.sha256(image_prompt.encode("utf-8")).hexdigest()[:8], 16)
    encoded = urllib.parse.quote(image_prompt[:500])
    return f"https://image.pollinations.ai/prompt/{encoded}?width=768&height=512&seed={seed}&nologo=true"


def _generate_with_dalle(image_prompt: str, style: str) -> Optional[str]:
    try:
        import openai
    except ImportError:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1024x1024",
            style=style if style in ("vivid", "natural") else "vivid",
            n=1,
        )
        return response.data[0].url
    except Exception as e:  # noqa: BLE001 — any API failure just falls back
        logger.warning("DALL-E generation failed: %s", e)
        return None


def generate_story_image(game_id: str, round_id: str, image_prompt: str = "",
                          scene_hint: Optional[str] = None, style: str = "vivid",
                          image_style: str = "cartoon", force: bool = False) -> Dict[str, Any]:
    """Generate (or return the cached) hero image for a round/scene/stock.

    Returns `{"image_url": str, "cached": bool}`. `force=True` bypasses the
    cache and regenerates (used by the admin regenerate-image route).
    """
    key = _cache_key(game_id, round_id)
    cache = _load_cache()
    if not force and key in cache:
        return {"image_url": cache[key], "cached": True}

    prompt = image_prompt or scene_hint or f"{game_id} {round_id}"
    image_url = _generate_with_dalle(prompt, style) or get_pollinations_fallback(prompt, style)

    cache[key] = image_url
    _save_cache(cache)
    return {"image_url": image_url, "cached": False}
