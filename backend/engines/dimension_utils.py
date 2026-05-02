"""
Soft Skill Dimension Utilities
Provides standardized dimension scoring, labels, and normalization
across all game engines.
"""
# P0 CI alpha = 0.10 (90% CI). Decision: docs/decisions/2026-05-02-canonical-dimension-taxonomy.md

from typing import Dict, List, Any, Optional


# Standard soft skill dimensions with metadata
# All engines map their computed scores to these standard dimensions.
STANDARD_DIMENSIONS = {
    "strategic_thinking": {
        "label": "Strategic Thinking",
        "description": "Planning, pattern recognition, and systems analysis",
        "icon": "brain",
        "color": "#3B82F6",
        "short_label": "Strategic",
    },
    "risk_tolerance": {
        "label": "Risk Tolerance",
        "description": "Willingness to take calculated risks for potential rewards",
        "icon": "flame",
        "color": "#EF4444",
        "short_label": "Risk",
    },
    "delayed_gratification": {
        "label": "Delayed Gratification",
        "description": "Patience and long-term thinking over short-term gains",
        "icon": "hourglass",
        "color": "#8B5CF6",
        "short_label": "Patience",
    },
    "adaptability": {
        "label": "Adaptability",
        "description": "Changing strategy when conditions shift",
        "icon": "refresh",
        "color": "#10B981",
        "short_label": "Adaptive",
    },
    "resilience": {
        "label": "Resilience",
        "description": "Persisting and recovering from setbacks",
        "icon": "shield",
        "color": "#F59E0B",
        "short_label": "Resilient",
    },
    "empathy": {
        "label": "Empathy",
        "description": "Understanding and considering others' perspectives",
        "icon": "heart",
        "color": "#EC4899",
        "short_label": "Empathy",
    },
}

# Map from game-specific dimension names to standard names
DIMENSION_ALIASES = {
    "impulse_control": "delayed_gratification",
    "emotional_regulation": "resilience",
    "self_awareness": "adaptability",
    "growth_mindset": "resilience",
    "leadership": "strategic_thinking",
}


def normalize_dimension_scores(raw_scores: Optional[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
    """
    Normalize engine-specific dimension scores into a standard list
    with labels, descriptions, and metadata for frontend display.

    Args:
        raw_scores: Dict of dimension_name -> score (0-100) from any engine

    Returns:
        List of dicts with {name, value, label, description, icon, color, short_label}
        or None if no scores available
    """
    if not raw_scores or not isinstance(raw_scores, dict):
        return None

    result = []
    seen = set()

    for key, value in raw_scores.items():
        if not isinstance(value, (int, float)):
            continue

        # Map aliases to standard names
        standard_key = DIMENSION_ALIASES.get(key, key)

        # Skip if already processed (e.g., alias collision)
        if standard_key in seen:
            continue
        seen.add(standard_key)

        # Clamp to 0-100
        clamped = max(0, min(100, round(value)))

        # Get metadata from STANDARD_DIMENSIONS if available, else build generic
        meta = STANDARD_DIMENSIONS.get(standard_key)
        if meta:
            result.append({
                "name": standard_key,
                "value": clamped,
                "label": meta["label"],
                "description": meta["description"],
                "icon": meta["icon"],
                "color": meta["color"],
                "short_label": meta["short_label"],
            })
        else:
            # Unknown dimension — still include with auto-generated label
            result.append({
                "name": standard_key,
                "value": clamped,
                "label": standard_key.replace("_", " ").title(),
                "description": "",
                "icon": "circle",
                "color": "#6B7280",
                "short_label": standard_key.replace("_", " ").title()[:10],
            })

    # Sort by value descending for consistent display
    result.sort(key=lambda d: d["value"], reverse=True)

    return result if result else None


def get_dimension_metadata() -> Dict[str, Dict[str, str]]:
    """Return the full dimension metadata dict for frontend config."""
    return {
        key: {
            "label": meta["label"],
            "description": meta["description"],
            "icon": meta["icon"],
            "color": meta["color"],
            "short_label": meta["short_label"],
        }
        for key, meta in STANDARD_DIMENSIONS.items()
    }


def infer_skill_tags_from_deltas(deltas: Dict[str, Any], choice_text: str = "") -> List[str]:
    """
    Infer which soft skill dimensions a choice exercises based on its deltas
    and text content. Returns a list of standard dimension names.

    This is a lightweight heuristic — no LLM needed.
    """
    if not deltas and not choice_text:
        return []

    tags = []
    text_lower = (choice_text or "").lower()
    deltas = deltas or {}

    # Heuristic: large negative resource + positive other = risk-taking
    neg_count = sum(1 for v in deltas.values() if isinstance(v, (int, float)) and v < -5)
    pos_count = sum(1 for v in deltas.values() if isinstance(v, (int, float)) and v > 5)

    if neg_count > 0 and pos_count > 0:
        tags.append("risk_tolerance")
    elif neg_count == 0 and pos_count > 0:
        tags.append("strategic_thinking")

    # Keywords in choice text
    risk_words = {"risk", "gamble", "bold", "aggressive", "invest heavily", "all-in", "bet"}
    patience_words = {"wait", "save", "long-term", "patient", "conserve", "prepare", "plan ahead"}
    empathy_words = {"help", "support", "listen", "empathy", "care", "protect", "volunteer", "donate"}
    adapt_words = {"change", "pivot", "adapt", "switch", "flexible", "adjust", "new approach"}
    resilience_words = {"recover", "persist", "rebuild", "despite", "overcome", "endure", "bounce back"}

    if any(w in text_lower for w in risk_words):
        if "risk_tolerance" not in tags:
            tags.append("risk_tolerance")
    if any(w in text_lower for w in patience_words):
        tags.append("delayed_gratification")
    if any(w in text_lower for w in empathy_words):
        tags.append("empathy")
    if any(w in text_lower for w in adapt_words):
        tags.append("adaptability")
    if any(w in text_lower for w in resilience_words):
        tags.append("resilience")

    # If nothing matched, check delta relationships for teams/people
    people_keys = {"team_trust", "team_morale", "relationships", "customer_love", "npc_trust", "morale"}
    if not tags and any(k in deltas for k in people_keys):
        tags.append("empathy")

    # Default: strategic_thinking if we have deltas but no specific match
    if not tags and deltas:
        tags.append("strategic_thinking")

    # Limit to 2 tags max
    return tags[:2]


def build_skill_callout(dimension: str, delta_value: float = 0) -> Optional[Dict[str, str]]:
    """
    Build a skill callout message for a given dimension after a choice.
    Returns None if dimension is unknown.
    """
    meta = STANDARD_DIMENSIONS.get(dimension)
    if not meta:
        return None

    # Callout templates by dimension
    templates = {
        "strategic_thinking": [
            "Smart move! You thought ahead.",
            "Strategic play — planning pays off.",
            "Good analysis of the situation.",
        ],
        "risk_tolerance": [
            "Bold move! That took courage.",
            "A calculated risk — let's see how it plays out.",
            "Fortune favors the brave.",
        ],
        "delayed_gratification": [
            "Patient choice — investing in the future.",
            "Playing the long game. Smart.",
            "Short-term sacrifice for long-term gain.",
        ],
        "adaptability": [
            "Good pivot! Adapting to change.",
            "Flexible thinking in action.",
            "You adjusted your approach — that's adaptability.",
        ],
        "resilience": [
            "Bouncing back strong!",
            "Persevering through difficulty.",
            "That's resilience — not giving up.",
        ],
        "empathy": [
            "Putting others first — that's empathy.",
            "Considering others' needs. Well done.",
            "A compassionate choice.",
        ],
    }

    import random
    msgs = templates.get(dimension, ["Good choice!"])
    msg = msgs[hash(str(delta_value)) % len(msgs)]

    return {
        "dimension": dimension,
        "label": meta["short_label"],
        "message": msg,
        "icon": meta["icon"],
        "color": meta["color"],
    }


def build_checkpoint_message(progress: int, dimension_scores: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build a mid-game checkpoint message based on progress percentage and current dimension scores.
    Returns a checkpoint dict for frontend display.
    """
    # Progress-based encouragement (template-driven, not hardcoded)
    milestones = {
        25: {
            "title": "Quarter Mark",
            "templates": [
                "You're getting started! Your early decisions are shaping your path.",
                "Good momentum so far. Your choices are setting the stage.",
            ],
        },
        50: {
            "title": "Halfway There",
            "templates": [
                "Halfway through! Time to reflect on your strategy so far.",
                "You've reached the midpoint. Consider what's working and what isn't.",
            ],
        },
        75: {
            "title": "Final Stretch",
            "templates": [
                "Almost there! Your final decisions will have the biggest impact.",
                "The home stretch — make every choice count.",
            ],
        },
    }

    # Find closest milestone
    closest = min(milestones.keys(), key=lambda m: abs(m - progress))
    milestone = milestones[closest]

    msg = milestone["templates"][hash(str(progress)) % len(milestone["templates"])]

    # Build dimension snapshot from scores if available
    dimension_snapshot = None
    if dimension_scores and isinstance(dimension_scores, dict):
        sorted_dims = sorted(
            [(k, v) for k, v in dimension_scores.items() if isinstance(v, (int, float))],
            key=lambda x: x[1],
            reverse=True,
        )
        if sorted_dims:
            top = sorted_dims[:2]
            bottom = sorted_dims[-1:] if len(sorted_dims) > 2 else []
            snapshot_items = []
            for dim_name, score in top:
                meta = STANDARD_DIMENSIONS.get(dim_name)
                snapshot_items.append({
                    "name": dim_name,
                    "label": meta["short_label"] if meta else dim_name.replace("_", " ").title(),
                    "value": round(score),
                    "position": "top",
                })
            for dim_name, score in bottom:
                meta = STANDARD_DIMENSIONS.get(dim_name)
                snapshot_items.append({
                    "name": dim_name,
                    "label": meta["short_label"] if meta else dim_name.replace("_", " ").title(),
                    "value": round(score),
                    "position": "bottom",
                })
            dimension_snapshot = snapshot_items

            # Enhance message with dimension insight
            if top and bottom:
                top_label = STANDARD_DIMENSIONS.get(top[0][0], {}).get("short_label", top[0][0])
                bot_label = STANDARD_DIMENSIONS.get(bottom[0][0], {}).get("short_label", bottom[0][0])
                msg += f" Your {top_label} skills are strong. Consider exercising more {bot_label}."

    return {
        "progress": progress,
        "title": milestone["title"],
        "message": msg,
        "dimension_snapshot": dimension_snapshot,
    }


def build_teachable_moment(dimension: str, choice_label: str = "", net_delta: float = 0) -> Optional[Dict[str, Any]]:
    """
    Build a teachable moment card for a negative outcome.
    Uses the dimension to select an educational insight.
    Returns None if dimension is unknown.
    """
    meta = STANDARD_DIMENSIONS.get(dimension)
    if not meta:
        return None

    # Teachable moment templates by dimension
    lessons = {
        "strategic_thinking": [
            {
                "title": "Think Before You Leap",
                "lesson": "Every decision has ripple effects. Taking a moment to consider second-order consequences can prevent costly mistakes.",
            },
            {
                "title": "The Planning Paradox",
                "lesson": "Sometimes the fastest path forward starts with slowing down to plan. Quick decisions aren't always the best ones.",
            },
        ],
        "risk_tolerance": [
            {
                "title": "Calculated vs. Reckless Risk",
                "lesson": "Bold moves can pay off, but only when the potential reward justifies the risk. Assess before you act.",
            },
            {
                "title": "The Safety Net Principle",
                "lesson": "Smart risk-takers always have a fallback plan. Risk without preparation is just gambling.",
            },
        ],
        "delayed_gratification": [
            {
                "title": "The Marshmallow Test",
                "lesson": "Choosing short-term comfort often costs long-term success. Building patience is one of the most valuable skills you can develop.",
            },
            {
                "title": "Invest in Tomorrow",
                "lesson": "Small sacrifices today compound into significant advantages over time. The best leaders think in weeks, not moments.",
            },
        ],
        "adaptability": [
            {
                "title": "Adapt or Fall Behind",
                "lesson": "Sticking to a plan when conditions change isn't persistence — it's stubbornness. Flexibility is a strength.",
            },
            {
                "title": "Read the Room",
                "lesson": "The best strategy is the one that works right now. Adaptable thinkers thrive in uncertainty.",
            },
        ],
        "resilience": [
            {
                "title": "Setbacks Are Setups",
                "lesson": "Every setback contains a lesson. Resilient people don't avoid failure — they learn from it faster than others.",
            },
            {
                "title": "Bounce Back Stronger",
                "lesson": "It's not about never falling — it's about getting back up with new knowledge. That's how growth works.",
            },
        ],
        "empathy": [
            {
                "title": "The Other Perspective",
                "lesson": "Decisions that ignore others' needs often backfire. Understanding how your choices affect people around you is a leadership superpower.",
            },
            {
                "title": "People Over Numbers",
                "lesson": "Resources can be rebuilt, but trust is hard to regain. Considering the human impact of your decisions pays long-term dividends.",
            },
        ],
    }

    available = lessons.get(dimension, [{"title": "Learning Moment", "lesson": "Every outcome is a chance to learn and improve."}])
    selected = available[hash(choice_label + str(net_delta)) % len(available)]

    return {
        "title": selected["title"],
        "lesson": selected["lesson"],
        "skill": dimension,
        "skill_label": meta["short_label"],
        "icon": meta["icon"],
        "color": meta["color"],
    }



# ──────────────────────────────────────────────────────────────────────────────
# Behavioral signal aggregation (Task 2 — P0 plan)
# Wired into _compute_*_dimension_scores in Tasks 5–7 for the 50/50 authored+
# behavioral scoring blend.
# ──────────────────────────────────────────────────────────────────────────────
from engines.behavioral_analytics import (
    compute_timing_stats,
    score_consistency,
    score_recovery_ability,
    score_risk_seeking,
    score_grit,
)


def aggregate_behavioral_signals(state):
    """Roll behavioral signals from behavioral_analytics into per-dimension 0-100 scores.

    Returns a dict with keys matching STANDARD_DIMENSIONS.
    Returns 50 (neutral) for any dimension with insufficient signal.
    """
    history = state.get("choice_history", []) or []
    trajectory = state.get("resource_trajectory", []) or []
    if not history:
        return {d: 50 for d in (
            "strategic_thinking", "risk_tolerance", "delayed_gratification",
            "adaptability", "resilience", "empathy"
        )}

    timing = compute_timing_stats(history)
    consistency = score_consistency(history, trajectory)
    recovery = score_recovery_ability(trajectory)
    risk_seek = score_risk_seeking(history, trajectory)
    grit = score_grit(trajectory, history)

    mean_ms = (timing or {}).get("mean_ms", 5000)
    deliberation_score = max(0, min(100, ((mean_ms - 2000) / 80)))

    return {
        "strategic_thinking": int(0.6 * consistency * 100 + 0.4 * deliberation_score),
        "risk_tolerance": int(risk_seek * 100),
        "delayed_gratification": int(deliberation_score),
        "adaptability": int(0.5 * consistency * 100 + 0.5 * recovery * 100),
        "resilience": int(0.7 * recovery * 100 + 0.3 * grit * 100),
        # TODO(Task 5): empathy is hardcoded neutral until authored empathy deltas
        # are blended in. Behavioral analytics has no empathy proxy today.
        "empathy": 50,
    }


def adjust_scores_for_timing(raw_scores: Dict[str, Any], timing_stats: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Adjust dimension scores based on timing data.
    - Very fast avg (< 1500ms): reduce all scores by 5% (likely random clicking)
    - Fast + high risk (< 3000ms, > 50% fast): reduce delayed_gratification by 10
    - Slow + deliberate (> 8000ms): boost strategic_thinking by 8
    """
    if not timing_stats or not raw_scores:
        return raw_scores

    adjusted = dict(raw_scores)
    mean_ms = timing_stats.get("mean_ms", 5000)
    fast_count = timing_stats.get("fast_decisions_count", 0)
    total = timing_stats.get("count", 1)
    fast_pct = fast_count / max(total, 1)

    # Very fast clicking — likely not reading; reduce all scores by 5%
    if mean_ms < 1500:
        for dim in adjusted:
            if isinstance(adjusted[dim], (int, float)):
                adjusted[dim] = max(0, round(adjusted[dim] * 0.95))

    # Fast + high risk pattern — reduce delayed_gratification
    if mean_ms < 3000 and fast_pct > 0.5:
        if "delayed_gratification" in adjusted and isinstance(adjusted["delayed_gratification"], (int, float)):
            adjusted["delayed_gratification"] = max(0, adjusted["delayed_gratification"] - 10)

    # Slow + deliberate — boost strategic_thinking
    if mean_ms > 8000:
        if "strategic_thinking" in adjusted and isinstance(adjusted["strategic_thinking"], (int, float)):
            adjusted["strategic_thinking"] = min(100, adjusted["strategic_thinking"] + 8)

    return adjusted
