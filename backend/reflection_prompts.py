"""
Age-bucketed reflection-prompt library.

Every game tries to surface a "Why did you choose that?" reflection moment.
Until now the prompt was the same string regardless of age — fine for
teens, alienating for 7-year-olds. This module provides a helper that
returns developmentally-appropriate prompts based on the student's age
band.

Bands:
  - kids   : 6-9   — picture-first, short, single-clause, emoji
  - tweens : 10-12 — concrete reasoning ("what was your plan?")
  - teens  : 13-17 — abstract, identity-linked
  - adults : 18+   — reflective practice, transferability
"""
from typing import Dict, List

_PROMPTS_BY_BAND: Dict[str, List[str]] = {
    "kids": [
        "Why did you pick this one? 🤔",
        "What were you thinking? 💭",
        "Was it tricky or easy?",
        "How does this make you feel?",
        "Would you pick it again next time?",
    ],
    "tweens": [
        "What was your plan when you made that choice?",
        "What did you notice that helped you decide?",
        "Was there another option you almost picked?",
        "What did you learn from how it turned out?",
        "If you had a clue from a friend, what would you ask?",
    ],
    "teens": [
        "What value or principle guided this choice?",
        "What trade-off were you making here?",
        "Whose perspective did you weigh — and whose did you not?",
        "If you had to defend this choice in front of others, what would you say?",
        "What surprised you about the outcome, and why?",
    ],
    "adults": [
        "Which of your assumptions did this choice rest on?",
        "What signal would have made you choose differently?",
        "How does this connect to a real-world situation you've faced?",
        "What's one principle you'd take from this into next week's work?",
        "If you replayed this with a different stakeholder watching, would you change your move?",
    ],
}


def _band_for_age(age: int) -> str:
    if age <= 9:
        return "kids"
    if age <= 12:
        return "tweens"
    if age <= 17:
        return "teens"
    return "adults"


def get_prompt(age: int, choice_index: int = 0) -> str:
    """Return a reflection prompt suited to the given age.

    `choice_index` is rotated through the band's list so consecutive
    reflections in the same session don't repeat verbatim.
    """
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 13
    band = _band_for_age(age)
    prompts = _PROMPTS_BY_BAND[band]
    idx = max(0, int(choice_index)) % len(prompts)
    return prompts[idx]


def get_band(age: int) -> str:
    """Public helper — returns the band name for a given age."""
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 13
    return _band_for_age(age)


def get_all_prompts(age: int) -> List[str]:
    """Return the full prompt list for a band — useful for variation pools
    on the client (e.g. picking a random one each round)."""
    try:
        age = int(age)
    except (TypeError, ValueError):
        age = 13
    return list(_PROMPTS_BY_BAND[_band_for_age(age)])
