"""
Offline activity-card generator — the "Khan Academy Kids" pairing.

After a child completes a digital game, the parent dashboard can offer
a printable PDF / shareable text "activity card" that extends the same
soft skill into the physical world (no screen needed). This module
contains the curated card library + a chooser that picks the right card
for a game's top dimension and the child's age band.

Each card is a 1-page printable: title + materials + steps + reflect.
"""
from typing import Dict, List, Optional

# Library: keyed by (dimension, age_band) → list of activity cards.
_CARDS: Dict[str, List[Dict[str, str]]] = {
    "empathy_kids": [
        {
            "title": "Feelings Detective 🕵️",
            "materials": "A book or movie scene",
            "steps": (
                "1. Watch or read together for 5 minutes.\n"
                "2. Pause and ask: \"How is this character feeling?\"\n"
                "3. Make the same face! Try to feel what they feel.\n"
                "4. Guess what helped you know."
            ),
            "reflect": "Did your guess match what happened next?",
            "minutes": 10,
        },
    ],
    "empathy_tweens": [
        {
            "title": "Two-Sides Story 📖",
            "materials": "Paper + pen",
            "steps": (
                "1. Pick a small argument from this week (real or pretend).\n"
                "2. Write the story from one person's view.\n"
                "3. Now write it again — same events, the OTHER person's view.\n"
                "4. Compare what changed."
            ),
            "reflect": "What's something the second person noticed that the first one missed?",
            "minutes": 20,
        },
    ],
    "strategic_thinking_kids": [
        {
            "title": "The 3-Step Plan 🎯",
            "materials": "Paper + crayons",
            "steps": (
                "1. Pick a small goal (build a tower, finish a snack).\n"
                "2. Draw THREE pictures: my goal, my plan, what I'll do first.\n"
                "3. Try it!\n"
                "4. Did it work? Draw what happened."
            ),
            "reflect": "If you tried again, what would you change?",
            "minutes": 15,
        },
    ],
    "strategic_thinking_tweens": [
        {
            "title": "Pre-mortem 🔮",
            "materials": "Paper + pen",
            "steps": (
                "1. Pick a thing you want to do this weekend.\n"
                "2. Imagine it FAILS. Write 3 reasons why it might fail.\n"
                "3. For each reason, write one thing you can do today to prevent it.\n"
                "4. Do at least one of those things."
            ),
            "reflect": "Which prevention idea was easiest? Which was hardest?",
            "minutes": 15,
        },
    ],
    "delayed_gratification_kids": [
        {
            "title": "The Marshmallow Game 🍬",
            "materials": "1 small treat, 1 timer",
            "steps": (
                "1. Set the timer for 5 minutes.\n"
                "2. Put the treat in front of you. Don't eat it yet!\n"
                "3. While you wait, sing a song or count.\n"
                "4. When the timer rings — enjoy your treat!"
            ),
            "reflect": "What helped you wait? What was hard?",
            "minutes": 10,
        },
    ],
    "resilience_kids": [
        {
            "title": "The Bounce-Back Jar 🫙",
            "materials": "A jar, paper slips, pen",
            "steps": (
                "1. Each day, write ONE small mistake on a slip.\n"
                "2. Add ONE thing you learned next to it.\n"
                "3. Drop it in the jar.\n"
                "4. End of week — read them all out loud."
            ),
            "reflect": "What's a mistake that taught you something useful?",
            "minutes": 5,
        },
    ],
    "creativity_kids": [
        {
            "title": "What Else Could It Be? 🎨",
            "materials": "Any household object",
            "steps": (
                "1. Pick a spoon (or any object).\n"
                "2. In 2 minutes, list 10 ways to use it that AREN'T eating.\n"
                "3. Pick the silliest one and act it out."
            ),
            "reflect": "Which one made you laugh? Which one might actually work?",
            "minutes": 10,
        },
    ],
    "communication_tweens": [
        {
            "title": "Explain-Like-I'm-Five 🎤",
            "materials": "A timer",
            "steps": (
                "1. Pick a thing you learned this week (school, hobby, anything).\n"
                "2. In 60 seconds, explain it to someone younger.\n"
                "3. They get to ask 3 questions. You answer.\n"
                "4. Swap: now they teach you something."
            ),
            "reflect": "Which words were too 'big'? What helped them understand?",
            "minutes": 10,
        },
    ],
}


def _band_for_age(age: int) -> str:
    if age <= 9:
        return "kids"
    if age <= 12:
        return "tweens"
    return "teens"


def get_activity_card(dimension: str, age: int) -> Optional[Dict[str, str]]:
    """Return the best matching card, or a generic fallback."""
    band = _band_for_age(age)
    key = f"{dimension}_{band}"
    cards = _CARDS.get(key)
    if cards:
        return cards[0]
    # Fall back to a generic kids/tweens card if exact dim not in library.
    fallback_key = f"empathy_{band}"  # empathy is broad enough as a default
    cards = _CARDS.get(fallback_key)
    return cards[0] if cards else None


def list_cards(dimension: Optional[str] = None,
               age: Optional[int] = None) -> List[Dict[str, str]]:
    """List all cards, optionally filtered."""
    out: List[Dict[str, str]] = []
    for key, cards in _CARDS.items():
        d, _, band = key.rpartition("_")
        if dimension and d != dimension:
            continue
        if age is not None and _band_for_age(int(age)) != band:
            continue
        out.extend(cards)
    return out


def card_count() -> int:
    return sum(len(v) for v in _CARDS.values())
