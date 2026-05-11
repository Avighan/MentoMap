"""
Reading-free mode for kids 6-9.

Augments any rounds-style game JSON with two affordances:
  1. `tts_text`     — short, simplified text for each round + each choice,
                      for the existing voice/TTS pipeline to read aloud.
  2. `emoji_choice` — each choice mapped to a single icon (emoji or asset
                      key) the renderer shows large, with no text required.

Both are derived from the existing scenario/choice text via simple rules
(short summarisation + emoji lookup). For better quality the admin UI
can still override per-round, but defaults work without any authoring
effort, which is the point: shipping kids content shouldn't require
re-authoring every game.
"""
import re
from typing import Any, Dict, List

# Cheap emoji map — words → emoji. Order matters: first match wins.
_EMOJI_KEYWORDS: List[tuple] = [
    (r"\bhelp(s|ed)?\b", "🤝"),
    (r"\b(share|sharing)\b", "🤝"),
    (r"\b(angry|argue|fight)\b", "😠"),
    (r"\b(sad|cry|cried|crying)\b", "😢"),
    (r"\b(happy|smile|smiled)\b", "😊"),
    (r"\b(money|coin|rupee|rupees)\b", "💰"),
    (r"\b(school|class|homework)\b", "🏫"),
    (r"\b(friend|friends)\b", "👫"),
    (r"\b(family|mom|dad|parents)\b", "👨‍👩‍👧"),
    (r"\b(food|eat|hungry|lunch)\b", "🍎"),
    (r"\b(safe|safety)\b", "🛡️"),
    (r"\b(danger|risky|risk)\b", "⚠️"),
    (r"\b(think|plan|idea)\b", "💡"),
    (r"\b(ask|tell|talk)\b", "💬"),
    (r"\b(run|hide|away)\b", "🏃"),
    (r"\b(wait|patien)\b", "⏳"),
    (r"\b(yes|agree|ok)\b", "✅"),
    (r"\b(no|don't|stop)\b", "🚫"),
]


def emoji_for_text(text: str, fallback: str = "❓") -> str:
    """Pick a single representative emoji for a short choice/scenario."""
    if not text or not isinstance(text, str):
        return fallback
    lower = text.lower()
    for pattern, emoji in _EMOJI_KEYWORDS:
        if re.search(pattern, lower):
            return emoji
    return fallback


_FILLER_RE = re.compile(
    r"\b(actually|basically|literally|just|really|that|which|who|whom|whose|"
    r"however|therefore|moreover|furthermore|consequently)\b",
    re.IGNORECASE,
)


def simplify_for_tts(text: str, max_words: int = 18) -> str:
    """Return a short, kid-friendly version of a passage for TTS.

    Strips filler words, takes the first sentence (or first N words),
    and leaves punctuation. Not a quality summariser — just enough so
    the TTS narration isn't a 3-minute paragraph.
    """
    if not text or not isinstance(text, str):
        return ""
    # First sentence break.
    first = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    cleaned = _FILLER_RE.sub("", first)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    words = cleaned.split()
    if len(words) > max_words:
        cleaned = " ".join(words[:max_words]) + "…"
    return cleaned


def augment_game_for_kids(game_config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a new game dict with `tts_text` and `emoji_choice` filled in
    for every round and choice. Idempotent — won't overwrite values an
    author has already provided. Doesn't mutate the input.
    """
    if not isinstance(game_config, dict):
        return game_config
    out = dict(game_config)
    out["kids_mode"] = True

    rounds = list(out.get("rounds") or [])
    new_rounds: List[Dict[str, Any]] = []
    for r in rounds:
        if not isinstance(r, dict):
            new_rounds.append(r)
            continue
        rcopy = dict(r)
        scenario = rcopy.get("scenario") or rcopy.get("text") or ""
        if "tts_text" not in rcopy:
            rcopy["tts_text"] = simplify_for_tts(scenario)

        choices = list(rcopy.get("choices") or [])
        new_choices: List[Dict[str, Any]] = []
        for c in choices:
            if not isinstance(c, dict):
                new_choices.append(c)
                continue
            ccopy = dict(c)
            ctext = ccopy.get("text") or ccopy.get("label") or ""
            if "tts_text" not in ccopy:
                ccopy["tts_text"] = simplify_for_tts(ctext, max_words=10)
            if "emoji_choice" not in ccopy:
                ccopy["emoji_choice"] = emoji_for_text(ctext)
            new_choices.append(ccopy)
        rcopy["choices"] = new_choices
        new_rounds.append(rcopy)
    out["rounds"] = new_rounds
    return out
