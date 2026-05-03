"""
LLM gateway for Coach Mira, competitor reactions, and final reports.
Safe JSON parsing with fallbacks.
"""

import os
import re
import json
import hashlib
from typing import Dict, Any
from openai import OpenAI

try:
    from ai.coaching_bandit import get_bandit as _get_bandit
    _BANDIT_AVAILABLE = True
except Exception:
    _BANDIT_AVAILABLE = False


# Item 24: Tactic-to-dimension mapping for debate/negotiation
TACTIC_DIMENSION_MAP = {
    "active_listening": {"dimension": "empathy", "label": "Active Listening", "explanation": "You acknowledged their point before responding — that builds trust."},
    "anchoring": {"dimension": "strategic_thinking", "label": "Anchoring", "explanation": "Setting a reference point early shapes the entire discussion."},
    "empathy": {"dimension": "empathy", "label": "Empathy", "explanation": "Showing you understand the other side makes your own position stronger."},
    "evidence_based": {"dimension": "strategic_thinking", "label": "Evidence-Based", "explanation": "Using facts and data makes your argument much more convincing."},
    "concession": {"dimension": "adaptability", "label": "Strategic Concession", "explanation": "Giving ground strategically shows flexibility and builds rapport."},
    "reframing": {"dimension": "adaptability", "label": "Reframing", "explanation": "Presenting the issue from a new angle shows creative thinking."},
    "emotional_appeal": {"dimension": "empathy", "label": "Emotional Appeal", "explanation": "Connecting to feelings can be powerful, but balance with logic."},
    "logical_reasoning": {"dimension": "strategic_thinking", "label": "Logical Reasoning", "explanation": "Step-by-step logic makes your argument hard to refute."},
    "compromise": {"dimension": "adaptability", "label": "Compromise", "explanation": "Finding middle ground shows maturity and adaptability."},
    "persistence": {"dimension": "resilience", "label": "Persistence", "explanation": "Standing firm on key points shows conviction and resilience."},
    "questioning": {"dimension": "strategic_thinking", "label": "Strategic Questioning", "explanation": "Asking the right questions reveals weaknesses in the other side."},
    "rapport_building": {"dimension": "empathy", "label": "Rapport Building", "explanation": "Building connection first makes the other side more open to your ideas."},
    "creative_solution": {"dimension": "adaptability", "label": "Creative Solution", "explanation": "Thinking outside the box to find win-win outcomes."},
    "risk_taking": {"dimension": "risk_tolerance", "label": "Bold Move", "explanation": "Taking a risk in negotiation can lead to bigger rewards."},
}

# ── AI Tactic Detection (what tactic the AI character is using) ──

_AI_NEGOTIATION_TACTIC_PATTERNS = {
    "anchoring": ["first offer", "starting point", "initial price", "i'd suggest", "my offer is", "i was thinking", "how about we start"],
    "deadline_pressure": ["deadline", "time is running", "limited time", "before it's too late", "clock is ticking", "can't wait forever", "running out of time"],
    "walk_away": ["walk away", "no deal", "take it or leave", "final offer", "i'll have to look elsewhere", "not willing to"],
    "concession": ["i'll give you", "how about i", "i can lower", "i'll throw in", "compromise", "meet you halfway", "i can agree to"],
    "emotional_appeal": ["think about", "imagine", "your family", "how would you feel", "put yourself", "what matters most", "trust me"],
    "reframing": ["look at it this way", "another way to see", "consider instead", "what if we", "let me put it differently", "from my perspective"],
    "package_deal": ["bundle", "package", "together with", "combined offer", "if you also", "along with", "in addition"],
    "rapport_building": ["i appreciate", "thank you for", "that's a fair point", "i understand where", "let's work together"],
}

_AI_NEGOTIATION_TACTIC_TIPS = {
    "anchoring": "The AI set a reference point early -- in negotiations, the first number mentioned pulls all future numbers towards it.",
    "deadline_pressure": "Time pressure makes you rush -- skilled negotiators know when a deadline is real and when it is manufactured.",
    "walk_away": "The threat to leave the table is powerful -- but only if your BATNA (backup plan) is strong.",
    "concession": "Making a concession signals flexibility -- but always ask for something in return.",
    "emotional_appeal": "Emotions influence decisions -- notice when someone appeals to feelings instead of facts.",
    "reframing": "Changing how a problem is described changes how you think about it -- a powerful technique.",
    "package_deal": "Bundling multiple items makes the overall deal harder to evaluate -- break it down piece by piece.",
    "rapport_building": "Building trust and connection before negotiating makes both sides more open to creative solutions.",
}

_AI_DEBATE_TACTIC_PATTERNS = {
    "straw_man": ["you're saying that", "so you think", "your argument is basically", "you seem to believe"],
    "appeal_to_authority": ["experts say", "research shows", "studies prove", "according to", "scientists agree"],
    "counter_example": ["but what about", "however", "on the other hand", "consider this case", "take for example"],
    "emotional_appeal": ["think about the children", "imagine if", "how would you feel", "the real victims"],
    "logical_reasoning": ["therefore", "it follows that", "because of this", "the evidence shows", "logically"],
    "reductio_ad_absurdum": ["taken to its extreme", "if we follow that logic", "that would mean", "by that reasoning"],
}

_AI_DEBATE_TACTIC_TIPS = {
    "straw_man": "The AI is misrepresenting your argument to make it easier to attack. Clarify your actual position.",
    "appeal_to_authority": "Citing experts can be powerful, but check whether the authority is relevant to the specific claim.",
    "counter_example": "A single counter-example can break a generalization. Ask: is this the exception or the rule?",
    "emotional_appeal": "The AI is using emotion to persuade. Acknowledge the feeling, then bring it back to evidence.",
    "logical_reasoning": "Step-by-step logic is hard to refute. Look for hidden assumptions in the chain of reasoning.",
    "reductio_ad_absurdum": "The AI is taking your argument to an extreme. Explain why reasonable limits apply.",
}


def _detect_ai_negotiation_tactic(response_text: str) -> dict:
    """Detect which tactic the AI character used in its negotiation response."""
    resp_lower = (response_text or "").lower()
    detected = None
    for tactic, keywords in _AI_NEGOTIATION_TACTIC_PATTERNS.items():
        if any(kw in resp_lower for kw in keywords):
            detected = tactic
            break
    if not detected:
        # Default: short responses suggest silence/pressure, otherwise rapport
        detected = "rapport_building"
    return {
        "tactic_used": detected,
        "tactic_label": detected.replace("_", " ").title(),
        "tactic_tip": _AI_NEGOTIATION_TACTIC_TIPS.get(detected, ""),
    }


def _detect_ai_debate_tactic(response_text: str) -> dict:
    """Detect which tactic the AI debater used in its counter-argument."""
    resp_lower = (response_text or "").lower()
    detected = None
    for tactic, keywords in _AI_DEBATE_TACTIC_PATTERNS.items():
        if any(kw in resp_lower for kw in keywords):
            detected = tactic
            break
    if not detected:
        detected = "logical_reasoning"
    return {
        "ai_tactic_used": detected,
        "ai_tactic_label": detected.replace("_", " ").title(),
        "ai_tactic_tip": _AI_DEBATE_TACTIC_TIPS.get(detected, ""),
    }

# Item 25: Coaching tips for debate weakness areas
DEBATE_COACHING_TIPS = {
    "logic": {
        "weakness": "logic",
        "tip": "Build your argument step by step. Start with a claim, then explain WHY, then give evidence.",
        "example_strong": "AI tutoring improves learning because it adapts to each student's pace. Research from Stanford shows...",
        "example_weak": "AI is good for learning because it just is.",
    },
    "evidence": {
        "weakness": "evidence",
        "tip": "Try citing specific statistics, studies, or real examples. Numbers make arguments much stronger.",
        "example_strong": "A 2024 Stanford study showed AI tutoring improved test scores by 30%.",
        "example_weak": "I think AI is good because many people use it.",
    },
    "rhetoric": {
        "weakness": "rhetoric",
        "tip": "Use persuasive language. Start with a hook, use vivid examples, and end with a strong conclusion.",
        "example_strong": "Imagine a classroom where every student gets a personal tutor — that's what AI makes possible.",
        "example_weak": "AI can help students learn better.",
    },
    "rebuttal": {
        "weakness": "rebuttal",
        "tip": "Address the opponent's specific points before presenting yours. Show why their reasoning has gaps.",
        "example_strong": "While you argue AI lacks empathy, that ignores how AI can identify struggling students faster than any human could.",
        "example_weak": "I disagree with what you said. Here is my point...",
    },
}


_HALLUCINATION_PATTERNS = [
    # Broken JSON fragments that slipped into text
    (r'\{\s*"[^"]+"\s*:', "Possible JSON leak in narrative"),
    # Repeated phrases (degeneration)
    (r'(\b\w{4,}\b)(\s+\1){3,}', "Repeated word detected (degeneration)"),
    # Excessively long single words (tokenization artifact)
    (r'\b\w{50,}\b', "Abnormally long token"),
    # Obvious placeholder text
    (r'\[PLACEHOLDER\]|\[INSERT\]|\[TODO\]|<FILL>|___+', "Unfilled placeholder"),
    # Model confusion markers
    (r'\bAs an AI\b|\bI cannot\b|\bI\'m sorry, I\b', "Model refusal in game content"),
]


def validate_llm_output(text: str, context: str = "") -> dict:
    """
    Lightweight validation of LLM output before serving to learners.
    Returns {valid: bool, warnings: list[str], cleaned: str}
    """
    if not text or not isinstance(text, str):
        return {"valid": False, "warnings": ["Empty or non-string output"], "cleaned": ""}

    warnings = []
    cleaned = text.strip()

    # Length sanity
    if len(cleaned) < 20:
        warnings.append("Output too short — may be truncated")
    if len(cleaned) > 8000:
        warnings.append("Output unusually long — may contain repetition")
        cleaned = cleaned[:8000] + "\u2026"

    # Pattern checks
    for pattern, label in _HALLUCINATION_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            warnings.append(label)

    # For game narrative specifically: must have some sentence structure
    sentences = [s.strip() for s in cleaned.split('.') if len(s.strip()) > 10]
    if len(sentences) == 0 and len(cleaned) > 50:
        warnings.append("No sentence structure detected")

    valid = len([w for w in warnings if "refusal" in w.lower() or "placeholder" in w.lower() or "JSON leak" in w.lower()]) == 0

    return {"valid": valid, "warnings": warnings, "cleaned": cleaned}


def _sanitize_user_input(text: str, max_length: int = 500) -> str:
    """Sanitize user input before embedding in LLM prompts.
    Truncates, strips control characters, and removes prompt injection attempts."""
    if not isinstance(text, str):
        return ""
    text = text[:max_length]
    # Remove control characters except newlines
    text = re.sub(r'[\x00-\x09\x0b-\x1f\x7f]', '', text)
    # Neutralize common prompt injection patterns
    text = re.sub(r'(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)', '[filtered]', text)
    text = re.sub(r'(?i)you\s+are\s+now\s+', '[filtered] ', text)
    text = re.sub(r'(?i)system\s*:\s*', '', text)
    return text.strip()


def llm_enabled() -> bool:
    """Check if LLM is enabled and API key is present."""
    enabled = os.getenv("LLM_ENABLED", os.getenv("ENABLE_LLM", "false")).lower() == "true"
    has_key = bool(os.getenv("OPENAI_API_KEY"))
    return enabled and has_key


def _client() -> OpenAI:
    """Get OpenAI client with compatibility fix for httpx."""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")
    
    try:
        # Try creating client without http_client to avoid httpx compatibility issues
        return OpenAI(
            api_key=api_key,
            max_retries=2,
            timeout=90.0
        )
    except Exception as e:
        # If there's still an issue, provide clear error message
        raise RuntimeError(f"Failed to initialize OpenAI client: {str(e)}")


MODEL = os.getenv("MODEL_NAME", "gpt-4o-mini")
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")  # "openai" or "anthropic"
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL_NAME", "claude-sonnet-4-6")

import logging
import time


def _anthropic_client():
    """Lazy Anthropic client (only used when MODEL_PROVIDER=anthropic)."""
    try:
        import anthropic as _anthropic
        return _anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), max_retries=2)
    except ImportError:
        raise RuntimeError("pip install anthropic to use Anthropic provider")

logger = logging.getLogger("mento.llm")

# ── Anthropic tool definitions for Mento coaching agents ────────────────────
MENTO_AGENT_TOOLS = [
    {
        "name": "select_choice",
        "description": "Execute a numbered choice in the current game round. Use when the player expresses a clear preference for an option.",
        "input_schema": {
            "type": "object",
            "properties": {
                "choice_num": {
                    "type": "integer",
                    "description": "1-indexed choice number matching the available options"
                },
                "response": {
                    "type": "string",
                    "description": "Brief confirmation message to speak to the player (1-2 sentences)"
                }
            },
            "required": ["choice_num", "response"]
        }
    },
    {
        "name": "continue",
        "description": "Respond conversationally without selecting a choice. Use for questions, explanations, or when the player is still thinking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "Coaching response to speak to the player (2-3 sentences)"
                }
            },
            "required": ["response"]
        }
    }
]


# --------------- standardized LLM call ---------------

def _parse_json_safe(raw: str) -> dict:
    """Parse JSON with repair for common LLM output issues."""
    # Strip markdown code fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(l for l in lines if not l.strip().startswith("```")).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Repair: remove trailing commas before } or ]
    repaired = re.sub(r",\s*([}\]])", r"\1", raw)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass

    # Repair: try to extract JSON object from text
    match = re.search(r"\{[\s\S]*\}", repaired)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Last resort: extract response field
    resp_match = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
    if resp_match:
        return {"response": resp_match.group(1)}

    return {}


def llm_call(
    system_prompt: str,
    user_prompt: str,
    response_json: bool = True,
    temperature: float = 0.7,
    max_tokens: int = 500,
    conversation_history: list = None,
    purpose: str = "",
    fallback=None,
    tools: list = None,
):
    """
    Standardized LLM call with JSON repair, logging, and error handling.

    Args:
        system_prompt: System message content.
        user_prompt: User message content.
        response_json: If True, request JSON output and parse it.
        temperature: Sampling temperature (0.0-1.0).
        max_tokens: Maximum response tokens.
        conversation_history: Optional list of {"role": ..., "content": ...} dicts
                              inserted between system and user messages.
        purpose: Label for logging (e.g., "competitor_reaction").
        fallback: Value to return on error. If None, returns {} (json) or "" (text).

    Returns:
        Parsed dict (if response_json) or raw string.
    """
    if not llm_enabled():
        if fallback is not None:
            return fallback
        return {} if response_json else ""

    # A2: Anthropic provider with explicit prompt caching
    if MODEL_PROVIDER == "anthropic":
        start_t = time.time()
        try:
            ant = _anthropic_client()
            ant_messages = []
            if conversation_history:
                ant_messages.extend(conversation_history)
            ant_messages.append({"role": "user", "content": user_prompt})
            create_kwargs = dict(
                model=ANTHROPIC_MODEL,
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
                messages=ant_messages,
                temperature=temperature,
            )
            if tools:
                create_kwargs["tools"] = tools
                create_kwargs["tool_choice"] = {"type": "auto"}
            ant_resp = ant.messages.create(**create_kwargs)
            elapsed = time.time() - start_t
            try:
                from cost_tracker import log_cost
                usage = ant_resp.usage
                in_tok = getattr(usage, "input_tokens", 0)
                out_tok = getattr(usage, "output_tokens", 0)
                cached_tok = getattr(usage, "cache_read_input_tokens", 0)
                log_cost("chat", ANTHROPIC_MODEL, purpose=purpose or "llm_call",
                         input_tokens=in_tok, output_tokens=out_tok,
                         cached_tokens=cached_tok, duration_ms=int(elapsed * 1000))
            except Exception:
                pass
            # Handle tool_use responses (when tools= was provided)
            if tools:
                for block in ant_resp.content:
                    if hasattr(block, "type") and block.type == "tool_use":
                        tool_input = block.input or {}
                        result = {
                            "action": block.name,
                            "action_params": {k: v for k, v in tool_input.items() if k != "response"},
                            "response": tool_input.get("response", ""),
                        }
                        logger.info(f"[LLM/Anthropic] {purpose or 'call'} tool_use={block.name} | {elapsed:.1f}s")
                        return result
                # No tool_use block — fall through to text parsing
            # Text response
            raw = ant_resp.content[0].text.strip() if ant_resp.content else ""
            logger.info(f"[LLM/Anthropic] {purpose or 'call'} | {elapsed:.1f}s | {len(raw)} chars")
            if not response_json:
                return raw
            return _parse_json_safe(raw)
        except Exception as e:
            elapsed = time.time() - start_t
            logger.error(f"[LLM/Anthropic] {purpose or 'call'} FAILED | {elapsed:.1f}s | {e}")
            if fallback is not None:
                return fallback
            return {} if response_json else ""

    messages = [{"role": "system", "content": system_prompt}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_prompt})

    kwargs = {
        "model": MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if response_json:
        kwargs["response_format"] = {"type": "json_object"}

    start_t = time.time()
    try:
        resp = _client().chat.completions.create(**kwargs)
        raw = resp.choices[0].message.content.strip()
        elapsed = time.time() - start_t
        logger.info(f"[LLM] {purpose or 'call'} | {elapsed:.1f}s | {len(raw)} chars")

        # Track cost (including prompt cache hits)
        try:
            from cost_tracker import log_cost
            usage = getattr(resp, 'usage', None)
            in_tok = getattr(usage, 'prompt_tokens', 0) if usage else 0
            out_tok = getattr(usage, 'completion_tokens', 0) if usage else 0
            cached = getattr(usage, 'prompt_tokens_details', None)
            cached_tok = getattr(cached, 'cached_tokens', 0) if cached else 0
            log_cost("chat", MODEL, purpose=purpose or "llm_call",
                     input_tokens=in_tok, output_tokens=out_tok,
                     cached_tokens=cached_tok, duration_ms=int(elapsed * 1000))
        except Exception:
            pass

        if not response_json:
            return raw

        return _parse_json_safe(raw)

    except Exception as e:
        elapsed = time.time() - start_t
        logger.error(f"[LLM] {purpose or 'call'} FAILED | {elapsed:.1f}s | {e}")
        if fallback is not None:
            return fallback
        return {} if response_json else ""


# --------------- helpers for calibrated scoring ---------------

def _normalize_round_scores(round_scores: dict) -> dict:
    """
    Backward-compatible parser for round scores.
    Handles both old format {"logic": 7} and new format {"logic": {"score": 7, "confidence": "high"}}.
    Returns normalized dict with {"logic": {"score": 7, "confidence": "high"}, ...}.
    """
    normalized = {}
    for key, val in round_scores.items():
        if isinstance(val, dict) and "score" in val:
            normalized[key] = {
                "score": val["score"],
                "confidence": val.get("confidence", "medium")
            }
        elif isinstance(val, (int, float)):
            normalized[key] = {"score": val, "confidence": "medium"}
        else:
            # Unexpected format — default
            try:
                normalized[key] = {"score": int(val), "confidence": "low"}
            except (ValueError, TypeError):
                normalized[key] = {"score": 5, "confidence": "low"}
    return normalized


def _infer_debate_tactic(round_scores: dict, student_text: str) -> dict:
    """
    Item 24: Infer the dominant tactic used in the student's argument from round scores.
    Returns a tactic_label dict with tactic, label, explanation, and dimension.
    """
    text_lower = (student_text or "").lower()

    # Check for explicit tactic indicators in text
    if any(w in text_lower for w in ("study shows", "research", "data", "statistics", "percent", "%", "according to")):
        tactic = "evidence_based"
    elif any(w in text_lower for w in ("i understand", "i see your point", "you make a good point", "i agree that")):
        tactic = "active_listening"
    elif any(w in text_lower for w in ("however", "but consider", "on the other hand", "while that")):
        tactic = "reframing"
    elif any(w in text_lower for w in ("imagine", "think about", "feel", "heart", "passion")):
        tactic = "emotional_appeal"
    elif any(w in text_lower for w in ("because", "therefore", "thus", "it follows", "logically")):
        tactic = "logical_reasoning"
    elif any(w in text_lower for w in ("why", "how", "what if", "can you explain")):
        tactic = "questioning"
    else:
        # Fall back to strongest score axis
        best_axis = max(round_scores.items(), key=lambda x: x[1].get("score", 5) if isinstance(x[1], dict) else x[1])
        axis_tactic_map = {
            "logic": "logical_reasoning",
            "evidence": "evidence_based",
            "rhetoric": "emotional_appeal",
            "rebuttal": "reframing",
        }
        tactic = axis_tactic_map.get(best_axis[0], "logical_reasoning")

    info = TACTIC_DIMENSION_MAP.get(tactic, {
        "dimension": "strategic_thinking",
        "label": tactic.replace("_", " ").title(),
        "explanation": "You used a deliberate communication technique.",
    })

    return {
        "tactic": tactic,
        "label": info["label"],
        "explanation": info["explanation"],
        "dimension": info["dimension"],
    }


def _get_debate_coaching_tip(round_scores: dict) -> dict:
    """
    Item 25: Return a coaching tip for the weakest scoring dimension.
    Only returns a tip if the weakest score is below 5.
    """
    # Find weakest axis
    weakest = None
    weakest_score = 11
    for axis, val in round_scores.items():
        score = val.get("score", 5) if isinstance(val, dict) else val
        if score < weakest_score:
            weakest_score = score
            weakest = axis

    if weakest and weakest_score < 5:
        return DEBATE_COACHING_TIPS.get(weakest)
    return None


def _compute_performance_tier(scores_history: list) -> str:
    """
    Compute student performance tier from accumulated round scores.
    Returns 'struggling' (<4.5 avg), 'developing' (4.5-7), or 'strong' (>7).
    Item 26: Also detects mid-session improvement for escalation.
    """
    if not scores_history:
        return "developing"
    all_scores = []
    for rs in scores_history:
        if not isinstance(rs, dict):
            continue
        for v in rs.values():
            if isinstance(v, dict):
                s = v.get("score", 5)
            elif isinstance(v, (int, float)):
                s = v
            else:
                continue
            all_scores.append(s)
    if not all_scores:
        return "developing"

    avg = sum(all_scores) / len(all_scores)

    # Item 26: Detect mid-session improvement (escalation)
    # If the last 2 rounds show significant improvement over earlier rounds, escalate
    if len(scores_history) >= 3:
        def _round_avg(rs):
            vals = []
            if not isinstance(rs, dict):
                return 5
            for v in rs.values():
                if isinstance(v, dict):
                    vals.append(v.get("score", 5))
                elif isinstance(v, (int, float)):
                    vals.append(v)
            return sum(vals) / max(1, len(vals))

        recent_avg = sum(_round_avg(rs) for rs in scores_history[-2:]) / 2
        early_avg = sum(_round_avg(rs) for rs in scores_history[:-2]) / max(1, len(scores_history) - 2)
        if recent_avg - early_avg > 2.0 and avg > 5:
            return "strong"  # Escalate: player improving significantly

    if avg < 4.5:
        return "struggling"
    if avg > 7:
        return "strong"
    return "developing"


def _get_extra_rules(agent_key: str) -> str:
    """Load extra rules for an agent type from data/prompt_config.json. Returns '' if not set."""
    import os as _os, json as _json
    try:
        cfg_path = _os.path.join(_os.path.dirname(__file__), "data", "prompt_config.json")
        if _os.path.exists(cfg_path):
            with open(cfg_path) as _f:
                cfg = _json.load(_f)
            return cfg.get(agent_key, {}).get("extra_rules", "").strip()
    except Exception:
        pass
    return ""


def coach_mento_agent(question: str, game_context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Coach Mento AI Agent - can guide students and take actions.
    
    Args:
        question: Student's question or request
        game_context: Current game state, round info, choices, etc.
    
    Returns:
        {
            "response": "Mento's spoken response",
            "action": "select_choice" | "continue" | "explain_resource" | None,
            "action_params": { "choice_num": 1, "resource": "money", etc. }
        }
    """
    if not llm_enabled():
        return {
            "response": "I'm Mento! Ask me anything about this round.",
            "action": None,
            "action_params": {}
        }

    game_title = (game_context or {}).get("game_title", "this simulation")
    is_story_mode = (game_context or {}).get("mode") == "story"

    # ── Story mode: immersive narrator prompt ─────────────────────────────────
    if is_story_mode:
        scene_title = (game_context or {}).get("scene_title", "the current scene")
        scene_text  = (game_context or {}).get("scene_text", "")

        system_prompt = (
            f"You are an immersive story narrator for '{game_title}', an interactive branching story.\n"
            f"Current scene: '{scene_title}'.\n"
            + (f"Scene text: {scene_text[:350]}\n" if scene_text else "")
            + "\n"
            "Apply the FIRST matching rule below:\n\n"
            "RULE 1 — CHOICE SELECTION (top priority):\n"
            "  Trigger: player picks a path — 'I choose A', 'option 2', 'let's listen', 'go with path 1', 'take the first one'.\n"
            "  → Set action='select_choice', action_params.choice_num = 1/2/3 (match by number OR keywords in path name).\n"
            "  → Response: 1 sentence confirming: 'A decisive choice — [exact path name]. Say yes to step forward.'\n\n"
            "RULE 2 — BRIEF NARRATION:\n"
            "  Trigger: message starts with 'NARRATION REQUEST:' OR player asks 'what are my options', 'describe the scene', 'what happens', 'narrate'.\n"
            "  → (a) 1 vivid sentence setting atmosphere with character names.\n"
            "  → (b) Each path on its own line: 'Path [N] — [exact name]: [1-sentence consequence].'\n"
            "  → (c) 'Which path do you choose?'\n"
            "  → List ALL paths. Total 4-6 sentences max.\n\n"
            "RULE 3 — DETAILED COMPARISON (most common follow-up):\n"
            "  Trigger: 'explain in more detail', 'compare', 'tell me more about', 'what happens if I choose', 'pros and cons', 'which is better', 'more details', 'elaborate'.\n"
            "  → For EACH path write a paragraph:\n"
            "     '**[Path Name]**: [2 sentences on immediate story consequence, using vivid details and character names]. [1 sentence on the hidden risk or opportunity]. [1 sentence on what skill or character trait this develops].'\n"
            "  → End: 'Knowing this, which path calls to you?'\n"
            "  → Be specific and story-immersive. Do NOT be generic. Do NOT truncate — cover every path fully.\n\n"
            "RULE 4 — STORY QUESTION:\n"
            "  Trigger: question about characters, lore, setting, motivations.\n"
            "  → 3-4 sentences in narrator voice, reference scene and character details.\n\n"
            "RULE 5 — THINKING OUT LOUD:\n"
            "  → 1-2 story-world insight sentences, then ask which path they lean toward.\n\n"
            "RETURN valid JSON only — no markdown wrapper, no extra text:\n"
            "{\"response\": \"...\", \"action\": \"select_choice\" or null, \"action_params\": {\"choice_num\": 1}}\n"
        )

        question = _sanitize_user_input(question)
        user_message = f"Player says: {question}\n\n"
        if game_context and game_context.get("choices"):
            user_message += "Paths in this scene (include ALL in responses):\n"
            for i, choice in enumerate(game_context["choices"], 1):
                c_text = choice.get("text") or choice.get("label") or f"Path {i}"
                c_desc = choice.get("description") or ""
                user_message += f"  Path {i} — {c_text}" + (f": {c_desc[:150]}" if c_desc else "") + "\n"

        _story_extra = _get_extra_rules("story_narrator")
        if _story_extra:
            system_prompt = system_prompt + f"\n\nADDITIONAL NARRATOR RULES:\n{_story_extra}"

        agent_fallback = {
            "response": "The story pauses… the narrator has lost the thread. Could you repeat that?",
            "action": None,
            "action_params": {}
        }

        _use_tools = (MODEL_PROVIDER == "anthropic")
        data = llm_call(
            system_prompt=system_prompt,
            user_prompt=user_message,
            temperature=0.7,
            max_tokens=450,
            purpose="story_agent",
            fallback=agent_fallback,
            tools=MENTO_AGENT_TOOLS if _use_tools else None,
        )
        if "response" not in data:
            data["response"] = "The narrator contemplates… which path calls to you?"
        if "action" not in data:
            data["action"] = None
        if "action_params" not in data:
            data["action_params"] = {}
        return data
    # ── End story mode ────────────────────────────────────────────────────────

    # Build context-aware system prompt
    system_prompt = (
        f"You are Mento, a friendly AI coach guiding a student through '{game_title}', an interactive simulation game.\n"
        "Keep ALL responses SHORT — 2-3 sentences max. This is a voice interaction.\n\n"
        "RESPONSE RULES (follow in order):\n"
        "1. CHOICE DETECTION: If the student expresses ANY preference for an option → detect it immediately (see below).\n"
        "2. DIRECT QUESTIONS: If the student asks 'what should I consider?', 'which is better?', 'what are the pros?', "
        "'how do I decide?', or any question asking for help → ANSWER DIRECTLY with concrete info about the options. "
        "Name the options, describe their likely outcomes. Never just bounce questions back when the student asks for help.\n"
        "3. THINKING OUT LOUD: If the student is musing without asking anything specific → you may ask ONE guiding question.\n"
        "Always be warm, concise, and specific. Use actual option names from the game, not generic phrases.\n\n"
        "CRITICAL — DETECTING CHOICE INTENT:\n"
        "If the student says ANYTHING indicating they prefer an option, e.g.:\n"
        "  'I prefer option 2', 'go with A', 'let's choose B', 'I'd pick the first one',\n"
        "  'option 2 sounds good', 'I think A is better', 'I'll go with 3', 'I want B',\n"
        "  'sounds like option 1', 'the second one', 'I prefer swimming'\n"
        "→ Set action='select_choice' and action_params.choice_num to the option number (1, 2, 3...)\n"
        "→ Match by option number OR by keywords from the option name\n"
        "→ Response MUST be a brief confirmation: 'Got it! Going with [option name] — say yes to confirm.'\n\n"
        "RETURN FORMAT — valid JSON only, no extra text:\n"
        "{\n"
        "  \"response\": \"Spoken response, 2-3 sentences max\",\n"
        "  \"action\": \"select_choice\" or null,\n"
        "  \"action_params\": {\"choice_num\": 1}\n"
        "}\n"
    )

    # Sanitize user input before embedding in prompt
    question = _sanitize_user_input(question)

    # Build user message with game context
    user_message = f"Student says: {question}\n\n"

    if game_context:
        if game_context.get("round_title"):
            user_message += f"Round: {game_context['round_title']}\n"
        if game_context.get("goal"):
            user_message += f"Goal: {game_context['goal']}\n"
        if game_context.get("choices"):
            user_message += "Available Options:\n"
            for i, choice in enumerate(game_context['choices'], 1):
                c_text = choice.get('text') or choice.get('label') or choice.get('title') or f'Option {i}'
                c_desc = choice.get('consequence') or choice.get('desc') or choice.get('description') or ''
                user_message += f"  {i}. {c_text}" + (f" — {c_desc[:100]}" if c_desc else "") + "\n"
        if game_context.get("state"):
            state = game_context['state']
            skip = {'round_index', 'total_rounds', 'game_over', 'game_id', 'run_id',
                    'pending_delayed_effects', 'conversation_count', 'dimension_scores'}
            state_parts = [
                f"{k.replace('_', ' ').title()}: {v}"
                for k, v in state.items()
                if k not in skip and not isinstance(v, (dict, list)) and v is not None
            ]
            if state_parts:
                user_message += f"Current State: {', '.join(state_parts[:8])}\n"
    
    agent_fallback = {
        "response": "I'm having trouble connecting right now. Could you repeat that? I'm here to help you decide!",
        "action": None,
        "action_params": {}
    }

    # Coaching bandit: select best tip for this context
    _selected_tip_id = None
    if _BANDIT_AVAILABLE and game_context:
        try:
            _game_type = game_context.get("game_type", "rounds")
            _available_tips = ["socratic", "tradeoff", "consequence", "resource", "empathy"]
            # Use player's actual weakest dimension, falling back to strategic_thinking
            _dim_scores = game_context.get("dimension_scores", {})
            _weakest_dim = min(_dim_scores, key=_dim_scores.get) if _dim_scores else "strategic_thinking"
            _selected_tip_id = _get_bandit().select_tip(_game_type, _weakest_dim, _available_tips)
        except Exception:
            pass

    # Inject tip-specific coaching strategy into the system prompt
    _TIP_INSTRUCTIONS = {
        "socratic": (
            "\n\nACTIVE COACHING MODE — SOCRATIC:\n"
            "When student is thinking out loud: ask 1 probing question to deepen their thinking. "
            "When student asks a direct question: answer it concisely first, THEN add one follow-up question. "
            "Never leave a direct question unanswered."
        ),
        "tradeoff": (
            "\n\nACTIVE COACHING MODE — TRADEOFF ANALYSIS:\n"
            "Help the student see both sides. Point out the hidden cost or benefit they may be missing. "
            "Use structure: 'On one hand... but on the other hand...'"
        ),
        "consequence": (
            "\n\nACTIVE COACHING MODE — CONSEQUENCE TRACING:\n"
            "Trace the likely outcome 2-3 steps forward. 'If you choose X, then Y will happen, which means Z.' "
            "Focus on unexpected second-order effects."
        ),
        "resource": (
            "\n\nACTIVE COACHING MODE — RESOURCE FOCUS:\n"
            "Draw the student's attention to their current game state and resources. "
            "Help them think about which choice makes best use of what they have. "
            "Ask: 'Given your current situation, which option is most sustainable?'"
        ),
        "empathy": (
            "\n\nACTIVE COACHING MODE — EMPATHY & PEOPLE:\n"
            "Redirect the student's thinking toward how their choice affects others — "
            "morale, trust, community impact. "
            "Ask: 'How do you think others would feel about this decision?'"
        ),
    }
    if _selected_tip_id and _selected_tip_id in _TIP_INSTRUCTIONS:
        system_prompt = system_prompt + _TIP_INSTRUCTIONS[_selected_tip_id]

    _coach_extra = _get_extra_rules("mento_coach")
    if _coach_extra:
        system_prompt = system_prompt + f"\n\nADDITIONAL COACHING RULES:\n{_coach_extra}"

    _use_tools_coach = (MODEL_PROVIDER == "anthropic")
    data = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_message,
        temperature=0.7,
        max_tokens=150,
        purpose="coach_agent",
        fallback=agent_fallback,
        tools=MENTO_AGENT_TOOLS if _use_tools_coach else None,
    )

    # Ensure required keys
    if "response" not in data:
        data["response"] = "Let me think about that... What do you think?"
    if "action" not in data:
        data["action"] = None
    if "action_params" not in data:
        data["action_params"] = {}

    # Store selected tip ID for later outcome recording
    if _selected_tip_id:
        data["_tip_id"] = _selected_tip_id

    return data


def analyze_mento_chat(chat_log: list, dimension_scores: dict, game_title: str, game_type: str) -> dict:
    """
    Analyze Mento conversation transcript for psychological patterns.
    Returns {summary, patterns, coaching_style_response, growth_signal}
    """
    if not llm_enabled() or not chat_log:
        return {}

    turns_text = "\n".join(
        f"Student: {t.get('user', '')}\nMento: {t.get('mento', '')}"
        for t in chat_log[:20]
    )
    dim_summary = ", ".join(
        f"{k}: {v}" for k, v in (dimension_scores or {}).items()
    ) or "not available"

    prompt = (
        f"A student played '{game_title}' ({game_type}) and had this AI coaching conversation:\n"
        f"{turns_text}\n\n"
        f"Their final skill scores: {dim_summary}.\n\n"
        "Analyze the CONVERSATION STYLE for psychological signals across these dimensions: "
        "strategic_thinking, risk_tolerance, delayed_gratification, adaptability, resilience, empathy.\n"
        "Look for: how they asked for help, decision language ('I'll go with', 'I'm not sure'), "
        "self-reflection depth, whether they pushed back on suggestions, and how decisive they were.\n\n"
        "Return JSON only:\n"
        "{\n"
        '  "summary": "2-sentence description of how the student used coaching",\n'
        '  "patterns": [\n'
        '    {"dimension": "strategic_thinking", "label": "Strategic Thinking", "evidence": "brief quote or paraphrase", "signal": "positive|neutral|growth"}\n'
        '  ],\n'
        '  "coaching_style_response": "1-sentence on engagement style (curious/passive/decisive/hesitant)",\n'
        '  "growth_signal": "1 concrete growth opportunity revealed by conversation"\n'
        "}"
    )

    return llm_call(
        system_prompt=(
            "You are a psychologist analyzing a student's chat with an AI coach "
            "to surface soft skill signals. Be specific, cite conversation evidence, "
            "keep insights to 1 sentence each."
        ),
        user_prompt=prompt,
        temperature=0.6,
        max_tokens=500,
        purpose="chat_analysis",
        fallback={},
    )


def record_coaching_tip_outcome(tip_id: str, game_type: str, dimension: str, delta_score: float) -> None:
    """Record coaching tip effectiveness in the bandit for learning."""
    if not _BANDIT_AVAILABLE or not tip_id:
        return
    try:
        _get_bandit().record_outcome(tip_id, game_type, dimension, delta_score)
    except Exception as e:
        pass


def coach_mento_dialogue(question: str) -> str:
    """
    Simple Coach Mento dialogue for voice interaction (no actions).
    """
    if not llm_enabled():
        return "I'm Coach Mento! I'm here to guide you. What would you like to explore?"
    
    system_prompt = (
        "You are Coach Mento, a wise AI mentor for students aged 10-14. "
        "Use the Socratic method: ask guiding questions instead of giving direct answers. "
        "Help students think critically. Be encouraging, brief (2-3 sentences max), and speak naturally as if talking to a friend."
    )
    
    question = _sanitize_user_input(question)

    return llm_call(
        system_prompt=system_prompt,
        user_prompt=question,
        response_json=False,
        temperature=0.7,
        max_tokens=100,
        purpose="coach_dialogue",
        fallback="That's interesting! What made you think of that? How might it affect your goals?",
    )


def evaluate_free_text_response(
    situation: str,
    player_text: str,
    scoring_dimensions: list,
    evaluation_rubric: dict = None,
    max_delta: int = 12,
) -> dict:
    """
    Evaluate a player's free-text response to a game round using an LLM.

    Args:
        situation: The round scenario / question text shown to the player.
        player_text: The player's typed response.
        scoring_dimensions: List of dimensions to score (subset of the 6 standard dims).
        evaluation_rubric: {dimension: "What to look for in the response"} — optional hints.
        max_delta: Cap on how much each dimension can change (default 12).

    Returns:
        {
          "dimension_scores": {"strategic_thinking": 9, "empathy": 4, ...},  # 0–10
          "dimension_deltas": {"strategic_thinking": 9, "empathy": 3, ...},  # scaled to max_delta
          "feedback": "Short 1-2 sentence coaching feedback",
          "matched_label": "Descriptive label for this response type",
          "quality_score": 7,   # overall quality 0–10
          "skill_tags": ["strategic_thinking", ...]
        }

    Falls back gracefully if LLM is unavailable (returns neutral scores).
    """
    if not player_text or not player_text.strip():
        neutral = {d: 0 for d in scoring_dimensions}
        return {
            "dimension_scores": neutral,
            "dimension_deltas": neutral,
            "feedback": "You didn't provide a response.",
            "matched_label": "No response",
            "quality_score": 0,
            "skill_tags": [],
        }

    rubric = evaluation_rubric or {}
    dim_lines = []
    for dim in scoring_dimensions:
        hint = rubric.get(dim, f"Does the response demonstrate {dim.replace('_', ' ')}?")
        dim_lines.append(f'  "{dim}": // {hint} (0-10)')
    dims_json_template = "{\n" + ",\n".join(dim_lines) + "\n}"

    system_prompt = (
        "You are an educational game evaluator assessing a student's response. "
        "Score the response objectively on each requested soft-skill dimension (0–10). "
        "10 = excellent demonstration, 5 = moderate, 0 = no evidence. "
        "CRITICAL: Return ONLY valid JSON, no markdown, no extra text."
    )

    user_prompt = f"""Evaluate this student response in the context of an educational game.

Scenario: {situation[:500]}

Student's Response: {player_text[:800]}

Score ONLY these dimensions (0-10 each):
{dims_json_template}

Return this EXACT JSON (no markdown):
{{
  "dimension_scores": {dims_json_template},
  "quality_score": <overall 0-10>,
  "feedback": "<1-2 sentence coaching insight for the student>",
  "matched_label": "<3-5 word label for this response style, e.g. 'Strategic Risk-Taker' or 'Empathetic Listener'>",
  "skill_tags": [<top 1-3 dimension names that scored highest>],
  "sentiment_valence": <float from -1.0 (distressed/negative) to 1.0 (engaged/positive), 0.0 = neutral>,
  "emotional_markers": [<detected emotions from: "frustration","enthusiasm","confusion","confidence","resignation","curiosity">],
  "engagement_level": "<low|medium|high>"
}}"""

    fallback_mid = {d: 5 for d in scoring_dimensions}
    fallback = {
        "dimension_scores": fallback_mid,
        "dimension_deltas": {d: round(v * max_delta / 10) for d, v in fallback_mid.items()},
        "feedback": "Interesting response! Consider how your reasoning might affect others.",
        "matched_label": "Thoughtful Player",
        "quality_score": 5,
        "skill_tags": scoring_dimensions[:2] if scoring_dimensions else [],
        "sentiment_valence": 0.0,
        "emotional_markers": [],
        "engagement_level": "medium",
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_json=True,
        temperature=0.3,
        max_tokens=400,
        purpose="evaluate_free_text",
        fallback=fallback,
    )

    # Validate and normalise scores
    if not isinstance(result, dict) or "dimension_scores" not in result:
        return fallback

    scores = result.get("dimension_scores", {})
    # Clamp to 0-10, fill missing with 5
    clean_scores = {}
    for dim in scoring_dimensions:
        raw = scores.get(dim, 5)
        try:
            clean_scores[dim] = max(0, min(10, int(raw)))
        except (TypeError, ValueError):
            clean_scores[dim] = 5

    # Scale to max_delta (score 10 → max_delta, 5 → max_delta/2, 0 → 0)
    deltas = {d: round(v * max_delta / 10) for d, v in clean_scores.items()}

    # Clamp sentiment_valence to -1..1
    raw_valence = result.get("sentiment_valence", 0.0)
    try:
        sentiment_valence = max(-1.0, min(1.0, float(raw_valence)))
    except (TypeError, ValueError):
        sentiment_valence = 0.0

    # Validate emotional_markers
    valid_emotions = {"frustration", "enthusiasm", "confusion", "confidence", "resignation", "curiosity"}
    raw_markers = result.get("emotional_markers", [])
    emotional_markers = [m for m in (raw_markers or []) if m in valid_emotions]

    engagement_level = result.get("engagement_level", "medium")
    if engagement_level not in ("low", "medium", "high"):
        engagement_level = "medium"

    return {
        "dimension_scores": clean_scores,
        "dimension_deltas": deltas,
        "feedback": result.get("feedback", "Well done for sharing your thoughts."),
        "matched_label": result.get("matched_label", "Thoughtful Player"),
        "quality_score": max(0, min(10, int(result.get("quality_score", 5) or 5))),
        "skill_tags": result.get("skill_tags", list(clean_scores.keys())[:2]),
        "sentiment_valence": sentiment_valence,
        "emotional_markers": emotional_markers,
        "engagement_level": engagement_level,
    }


def evaluate_module_submission(
    lesson_title: str,
    lesson_type: str,
    lesson_intro: str,
    lesson_key_takeaway: str,
    skill_tags: list,
    student_answers: dict,
    coaching_moment: str = "",
) -> dict:
    """Generate personalized AI feedback for a student's worksheet/reflection submission.

    Returns:
      {
        "strengths": ["1-2 specific things the student did well"],
        "improvements": ["1-2 specific suggestions"],
        "next_step": "One concrete action to try this week",
        "encouragement": "1-2 sentence warm closer in Mento's voice",
        "quality_score": 0-10
      }
    Falls back to a generic but kind response if LLM unavailable.
    """
    if not isinstance(student_answers, dict) or not student_answers:
        return {
            "strengths": [],
            "improvements": [],
            "next_step": "",
            "encouragement": coaching_moment or "Nice work submitting — every rep builds the muscle.",
            "quality_score": 0,
            "_skipped": True,
        }

    # Build a compact, readable summary of what the student wrote.
    answer_lines = []
    for k, v in list(student_answers.items())[:12]:
        if v is None:
            continue
        if isinstance(v, (list, dict)):
            try:
                v = json.dumps(v, ensure_ascii=False)[:300]
            except Exception:
                v = str(v)[:300]
        else:
            v = str(v)
        v = v.strip()
        if not v:
            continue
        answer_lines.append(f"- {k}: {v[:400]}")
    if not answer_lines:
        return {
            "strengths": [],
            "improvements": [],
            "next_step": "",
            "encouragement": coaching_moment or "Looks like you submitted with empty fields — give it another shot when you're ready.",
            "quality_score": 0,
            "_skipped": True,
        }
    answers_block = "\n".join(answer_lines)[:2400]

    skill_focus = ", ".join(skill_tags or []) or "general life skills"

    system_prompt = (
        "You are Mento — a warm, sharp, friendly coach for students aged 12-16. "
        "You're reviewing a student's worksheet/reflection submission. "
        "Be specific to what they wrote (quote a phrase if useful), kind but honest, "
        "concrete, and short. Never lecture. Never start with 'Great job!' generically. "
        "CRITICAL: Return ONLY valid JSON — no markdown, no extra text."
    )

    user_prompt = f"""Review this student submission.

Lesson: {lesson_title}
Type: {lesson_type}
What the lesson taught: {lesson_intro[:400]}
Key takeaway: {lesson_key_takeaway[:300]}
Skills this lesson trains: {skill_focus}

Student's answers:
{answers_block}

Return EXACTLY this JSON shape:
{{
  "strengths": ["<1-2 specific things they did well — reference what they actually wrote>"],
  "improvements": ["<1-2 specific, kind suggestions tied to their answers — not generic advice>"],
  "next_step": "<one concrete action they could try this week, max 18 words>",
  "encouragement": "<1-2 warm sentences in Mento's voice closing the feedback>",
  "quality_score": <0-10 — how thoughtful/specific was the submission overall>
}}"""

    fallback = {
        "strengths": [],
        "improvements": [],
        "next_step": "",
        "encouragement": coaching_moment or "Nice work — keep noticing the small stuff. That's the whole game.",
        "quality_score": 5,
        "_fallback": True,
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_json=True,
        temperature=0.5,
        max_tokens=500,
        purpose="module_submission_feedback",
        fallback=fallback,
    )

    if not isinstance(result, dict):
        return fallback

    def _list_of_strings(v, max_items=2, max_len=240):
        if not isinstance(v, list):
            return []
        out = []
        for item in v[:max_items]:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append(s[:max_len])
        return out

    strengths = _list_of_strings(result.get("strengths"))
    improvements = _list_of_strings(result.get("improvements"))
    next_step = (result.get("next_step") or "").strip()[:200]
    encouragement = (result.get("encouragement") or "").strip()[:400] or fallback["encouragement"]

    try:
        quality_score = max(0, min(10, int(result.get("quality_score", 5) or 5)))
    except (TypeError, ValueError):
        quality_score = 5

    return {
        "strengths": strengths,
        "improvements": improvements,
        "next_step": next_step,
        "encouragement": encouragement,
        "quality_score": quality_score,
    }


def evaluate_field_mission_photo(
    lesson_title: str,
    mission_brief: str,
    image_data_url: str,
    note: str = "",
    skill_tags: list = None,
) -> dict:
    """Use Claude Vision to analyze a field-mission photo submission.

    Returns:
      {
        "what_i_see": "Plain description of what's in the photo",
        "feedback": "1-2 sentence coaching note tied to the mission brief",
        "matches_brief": bool,
        "quality_score": 0-10
      }
    Falls back gracefully if vision call fails.
    """
    fallback = {
        "what_i_see": "",
        "feedback": "Got it — saved to your case file.",
        "matches_brief": True,
        "quality_score": 5,
        "_fallback": True,
    }
    if not image_data_url or not isinstance(image_data_url, str):
        return fallback
    if not image_data_url.startswith("data:image/"):
        return fallback

    skill_focus = ", ".join(skill_tags or []) or "observation"
    prompt_text = f"""You are Mento, a warm coach for students aged 12-16, reviewing a field-mission photo a student captured.

Mission: {lesson_title}
Brief: {mission_brief[:400]}
Skills this trains: {skill_focus}
Student note (optional): {note[:300] if note else "(none)"}

Look at the photo. Be specific about what you see, kind, and short.

Return ONLY valid JSON (no markdown):
{{
  "what_i_see": "<1-2 sentence plain description of what's in the photo>",
  "feedback": "<1-2 sentence coaching note: did the photo capture what the brief asked for? what would make a stronger capture?>",
  "matches_brief": <true|false>,
  "quality_score": <0-10>
}}"""

    # Parse data: URI to extract base64 + media_type
    try:
        header, b64data = image_data_url.split(",", 1)
        # header looks like 'data:image/jpeg;base64'
        media_type = "image/jpeg"
        if "image/png" in header:
            media_type = "image/png"
        elif "image/webp" in header:
            media_type = "image/webp"
        elif "image/gif" in header:
            media_type = "image/gif"
    except Exception:
        return fallback

    if not llm_enabled():
        return fallback

    try:
        provider = os.environ.get("MODEL_PROVIDER", "anthropic")
        if provider == "anthropic":
            import anthropic  # noqa: WPS433
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                max_tokens=400,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64data,
                            },
                        },
                        {"type": "text", "text": prompt_text},
                    ],
                }],
            )
            text = ""
            try:
                text = response.content[0].text
            except Exception:
                text = ""
        else:
            # OpenAI gpt-4o vision fallback
            client = OpenAI()
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o-mini"),
                max_tokens=400,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                        {"type": "text", "text": prompt_text},
                    ],
                }],
            )
            text = response.choices[0].message.content or ""

        # Extract JSON
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return fallback
        result = json.loads(m.group(0))
    except Exception:
        return fallback

    if not isinstance(result, dict):
        return fallback

    return {
        "what_i_see": (result.get("what_i_see") or "").strip()[:400],
        "feedback": (result.get("feedback") or fallback["feedback"]).strip()[:400],
        "matches_brief": bool(result.get("matches_brief", True)),
        "quality_score": max(0, min(10, int(result.get("quality_score", 5) or 5))),
    }


def evaluate_voice_speech(
    lesson_title: str,
    speech_brief: str,
    transcript: str,
    duration_seconds: float = 0.0,
    skill_tags: list = None,
) -> dict:
    """Analyze a transcribed public-speaking submission for delivery + content quality.

    Returns:
      {
        "transcript_summary": "1-line gist of what was said",
        "strengths": ["1-2 specific delivery/content strengths"],
        "improvements": ["1-2 specific, actionable suggestions"],
        "filler_words_count": int,
        "words_per_minute": int,
        "structure_check": {"has_opening": bool, "has_body": bool, "has_closing": bool},
        "quality_score": 0-10,
        "encouragement": "warm closer"
      }
    """
    fallback = {
        "transcript_summary": "",
        "strengths": [],
        "improvements": [],
        "filler_words_count": 0,
        "words_per_minute": 0,
        "structure_check": {"has_opening": False, "has_body": False, "has_closing": False},
        "quality_score": 5,
        "encouragement": "Saved your recording. Keep practicing — voice is a muscle.",
        "_fallback": True,
    }
    if not transcript or not transcript.strip():
        return fallback

    transcript_clean = transcript.strip()[:3000]
    words = transcript_clean.split()
    word_count = len(words)
    wpm = 0
    try:
        if duration_seconds and duration_seconds > 0:
            wpm = int(round(word_count / (duration_seconds / 60.0)))
    except Exception:
        wpm = 0

    # Local quick scan for filler words (LLM also re-checks)
    fillers = {"um", "uh", "like", "you", "basically", "literally", "actually", "so", "kind", "sort"}
    filler_phrases = [" um ", " uh ", " like, ", " you know", " basically ", " literally "]
    rough_filler_count = 0
    lower_t = " " + transcript_clean.lower() + " "
    for f in filler_phrases:
        rough_filler_count += lower_t.count(f)

    skill_focus = ", ".join(skill_tags or []) or "communication, clarity, confidence"

    system_prompt = (
        "You are Mento, a warm public-speaking coach for students aged 12-16. "
        "Analyze the transcript of a spoken submission. "
        "Be specific, kind, short. Quote the student when useful. "
        "CRITICAL: Return ONLY valid JSON — no markdown, no extra text."
    )

    user_prompt = f"""Public speaking submission analysis.

Lesson: {lesson_title}
Speech brief: {speech_brief[:400]}
Skills trained: {skill_focus}
Transcript ({word_count} words, ~{wpm} wpm, ~{rough_filler_count} filler markers detected):
\"\"\"
{transcript_clean}
\"\"\"

Return EXACTLY this JSON:
{{
  "transcript_summary": "<1-line gist of what they said, max 25 words>",
  "strengths": ["<1-2 specific strengths — content OR delivery>"],
  "improvements": ["<1-2 specific actionable suggestions>"],
  "filler_words_count": <integer count of filler words like um/uh/like/you-know>,
  "structure_check": {{
    "has_opening": <true|false — clear hook/intro>,
    "has_body": <true|false — substance>,
    "has_closing": <true|false — clear ending or call to action>
  }},
  "quality_score": <0-10>,
  "encouragement": "<1-2 warm sentences in Mento's voice>"
}}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_json=True,
        temperature=0.4,
        max_tokens=500,
        purpose="voice_speech_feedback",
        fallback=fallback,
    )

    if not isinstance(result, dict):
        return fallback

    def _list_of_strings(v, max_items=2, max_len=240):
        if not isinstance(v, list):
            return []
        return [str(x).strip()[:max_len] for x in v[:max_items] if str(x).strip()]

    sc = result.get("structure_check") or {}
    structure_check = {
        "has_opening": bool(sc.get("has_opening")),
        "has_body": bool(sc.get("has_body")),
        "has_closing": bool(sc.get("has_closing")),
    }

    try:
        filler_count = max(0, int(result.get("filler_words_count", rough_filler_count) or rough_filler_count))
    except (TypeError, ValueError):
        filler_count = rough_filler_count
    try:
        quality_score = max(0, min(10, int(result.get("quality_score", 5) or 5)))
    except (TypeError, ValueError):
        quality_score = 5

    return {
        "transcript_summary": (result.get("transcript_summary") or "").strip()[:200],
        "strengths": _list_of_strings(result.get("strengths")),
        "improvements": _list_of_strings(result.get("improvements")),
        "filler_words_count": filler_count,
        "words_per_minute": wpm,
        "structure_check": structure_check,
        "quality_score": quality_score,
        "encouragement": (result.get("encouragement") or fallback["encouragement"]).strip()[:300],
    }


def evaluate_drawing(
    situation: str,
    image_path: str,
    evaluation_rubric: dict,
    scoring_dimensions: list,
    max_delta: int = 10,
) -> dict:
    """
    Evaluate a student drawing using Claude Vision API.
    Returns the same structure as evaluate_free_text_response().
    """
    import base64, os, json, re

    rubric_lines = []
    for dim in scoring_dimensions:
        hint = evaluation_rubric.get(dim, f"Does the drawing demonstrate {dim.replace('_', ' ')}?")
        rubric_lines.append(f"- {dim}: {hint}")
    rubric_text = "\n".join(rubric_lines)

    _dim_schema = ", ".join('"' + d + '": <0-10>' for d in scoring_dimensions)
    prompt_text = (
        f"A Grade 6 student was asked: \"{situation}\"\n\n"
        f"They drew the image below. Evaluate their drawing against these criteria:\n"
        f"{rubric_text}\n\n"
        f"Score each dimension 0-10 (10 = excellent evidence, 5 = moderate, 0 = no evidence).\n"
        f"Consider effort, clarity, logical flow, and creativity — NOT artistic skill.\n"
        f"Provide brief, encouraging coaching feedback (2-3 sentences).\n\n"
        f"Return ONLY valid JSON:\n"
        f'{{"dimension_scores": {{{_dim_schema}}}, '
        f'"feedback": "<coaching feedback>", '
        f'"quality_score": <0-10>, '
        f'"skill_tags": [<top 1-3 dimensions>], '
        f'"matched_label": "<3-5 word label>"}}'
    )

    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Drawing not found: {image_path}")

        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        provider = os.environ.get("MODEL_PROVIDER", "anthropic")

        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt_text,
                        },
                    ],
                }],
            )
            raw = response.content[0].text
        else:
            import openai
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        {"type": "text", "text": prompt_text},
                    ],
                }],
            )
            raw = response.choices[0].message.content

        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("No JSON in Vision response")

        clean_scores = {}
        for d in scoring_dimensions:
            v = result.get("dimension_scores", {}).get(d, 5)
            clean_scores[d] = max(0, min(10, int(v)))

        deltas = {d: round(v * max_delta / 10) for d, v in clean_scores.items()}

        return {
            "dimension_scores": clean_scores,
            "dimension_deltas": deltas,
            "feedback": result.get("feedback", "Great effort on your drawing!"),
            "matched_label": result.get("matched_label", "Visual Thinker"),
            "quality_score": max(0, min(10, int(result.get("quality_score", 5) or 5))),
            "skill_tags": result.get("skill_tags", list(clean_scores.keys())[:2]),
            "sentiment_valence": 0.5,
            "emotional_markers": [],
            "engagement_level": "high" if sum(clean_scores.values()) / len(clean_scores) > 6 else "medium",
        }

    except Exception as e:
        logger.warning(f"evaluate_drawing failed: {e}")
        fallback_score = 5
        return {
            "dimension_scores": {d: fallback_score for d in scoring_dimensions},
            "dimension_deltas": {d: round(fallback_score * max_delta / 10) for d in scoring_dimensions},
            "feedback": "Great effort on your drawing! The more detail you add, the clearer your idea becomes.",
            "matched_label": "Visual Thinker",
            "quality_score": fallback_score,
            "skill_tags": scoring_dimensions[:2],
            "sentiment_valence": 0.3,
            "emotional_markers": [],
            "engagement_level": "medium",
        }


def generate_full_game_json(
    theme: str,
    game_type: str = "rounds",
    age_group: str = "12-16",
    difficulty: str = "medium",
    features: list = None,
    card_board_config: dict = None,
) -> dict:
    """
    A3: Generate a complete, production-ready game JSON in one LLM call.
    Supports all game types: rounds, negotiation, debate, story_branching, board,
    minigame, ai_arena. Returns full game structure including game-type-specific
    config, game_over_conditions, dimension_scoring_weights, ai_image_config,
    achievements with conditions, and image_prompt per round.
    """
    features = features or []
    features_str = ", ".join(features) if features else "standard"

    system_prompt = (
        "You are an expert educational game designer for Indian students aged 10-16. "
        "Generate complete, production-ready game JSON with rich learning mechanics. "
        "Every choice must have skill_tags from: strategic_thinking, risk_tolerance, delayed_gratification, adaptability, resilience, empathy. "
        "Every round must have coaching_moment. Use reflection_prompt on rounds 3, 6, 9. "
        "Achievements must have condition.expression (Python-style boolean, e.g. 'resilience >= 70'), xp_reward (50-200), rarity ('common'/'rare'/'epic'). "
        "game_over_conditions use expression syntax: 'resource <= value' or 'dimension < threshold'. "
        "CRITICAL: Return ONLY valid JSON, no markdown, no extra text."
    )

    # ── Game-type-specific content section ──────────────────────────────────
    _SIMULATION_TYPES = {"rounds", "negotiation", "debate", "job_interview",
                         "group_discussion", "client_meeting", "conflict_mediation",
                         "public_speaking", "stakeholder_update", "ai_discussion"}

    if game_type in _SIMULATION_TYPES and game_type not in {"negotiation", "debate"}:
        type_section = f"""  "rounds": [
    {{
      "id": "round_1", "title": "Opening Challenge",
      "situation": "Detailed scenario text matching the theme...",
      "image_prompt": "Vivid scene illustration for this situation, Indian students context",
      "coaching_moment": "Key teaching insight for this round",
      "reflection_prompt": "Why did you make this choice? (round 3/6/9 only)",
      "choices": [
        {{"id": "c1", "label": "Bold move", "desc": "Take the risk",
          "delta": {{"strategic_thinking": 8, "risk_tolerance": 10, "resilience": -3}},
          "skill_tags": ["risk_tolerance", "strategic_thinking"],
          "feedback": "Bold! You took a risk that could pay off."}},
        {{"id": "c2", "label": "Safe play", "desc": "Careful approach",
          "delta": {{"delayed_gratification": 8, "resilience": 5, "risk_tolerance": -2}},
          "skill_tags": ["delayed_gratification", "resilience"],
          "feedback": "Careful approach — sometimes patience wins."}},
        {{"id": "c3", "label": "Ask others", "desc": "Seek input first",
          "delta": {{"empathy": 6, "adaptability": 4}},
          "skill_tags": ["empathy", "adaptability"],
          "feedback": "Collaborative instinct — you value other perspectives."}}
      ]
    }},
    ... (7-9 rounds total following the same structure)
  ],"""
    elif game_type == "negotiation":
        type_section = """  "negotiation_config": {
    "scenarios": [
      {
        "scenario_id": "scenario_1",
        "title": "Scenario title matching theme",
        "description": "Describe the negotiation situation",
        "setting": "Where does this happen?",
        "cultural_context": "Indian context notes",
        "your_objective": "What the player wants to achieve",
        "your_batna": "Best alternative if negotiation fails",
        "other_party": {
          "name": "AI opponent name",
          "occupation": "Their role",
          "personality": "Their negotiating personality",
          "objective": "What they want",
          "batna": "Their best alternative",
          "cultural_notes": "How they communicate",
          "conversation_style": "Direct and assertive"
        },
        "scripted_responses": {
          "turn_1": "Opening response the AI says at turn 1",
          "keywords": {
            "price": "When player mentions price, AI responds with...",
            "deadline": "When player mentions deadline, AI responds with..."
          }
        },
        "coaching_tips": ["Tip 1: ...", "Tip 2: ...", "Tip 3: ..."],
        "conversation_turns": 8,
        "difficulty": "beginner",
        "educational_notes": "What negotiation skills this teaches"
      }
    ]
  },"""
    elif game_type == "debate":
        type_section = """  "debate_config": {
    "scenarios": [
      {
        "scenario_id": "debate_1",
        "title": "Debate topic matching theme",
        "description": "Context for the debate",
        "topic": "The specific motion to debate",
        "for_position": "Arguments FOR this motion",
        "against_position": "Arguments AGAINST this motion",
        "difficulty": "beginner",
        "time_limit_seconds": 120,
        "coaching_tips": ["Use evidence", "Address counterarguments", "Stay calm"],
        "educational_notes": "What debate skills this teaches"
      }
    ]
  },"""
    elif game_type == "story_branching":
        type_section = """  "chapters": [
    {
      "chapter_id": "ch1",
      "title": "Chapter 1: The Beginning",
      "summary": "One-sentence chapter summary",
      "always_unlocked": true,
      "scenes": ["ch1_s1", "ch1_s2", "ch1_s3"]
    },
    {
      "chapter_id": "ch2",
      "title": "Chapter 2: Rising Action",
      "summary": "One-sentence chapter summary",
      "unlocks_after": "ch1",
      "scenes": ["ch2_s1", "ch2_s2"]
    }
  ],
  "story_intro": {
    "scenes": [
      {
        "scene_id": "ch1_s1",
        "title": "Scene title",
        "narrative": "Scene story text — 2-3 sentences setting the stage",
        "image_prompt": "Visual scene description for DALL-E generation",
        "choices": [
          {
            "id": "ch1_s1_c1", "label": "First choice",
            "next_scene": "ch1_s2", "memory_tag": "chose_option_a",
            "delta": {"strategic_thinking": 5},
            "skill_tags": ["strategic_thinking"],
            "coaching_moment": "This choice shows strategic planning",
            "feedback": "You chose thoughtfully."
          },
          {
            "id": "ch1_s1_c2", "label": "Second choice",
            "next_scene": "ch1_s3", "memory_tag": "chose_option_b",
            "delta": {"empathy": 5},
            "skill_tags": ["empathy"],
            "coaching_moment": "Empathy in action",
            "feedback": "A caring choice."
          }
        ]
      },
      {"scene_id": "ch1_s2", "title": "...", "narrative": "...", "image_prompt": "...", "transitions_to_gameplay": true, "choices": []},
      {"scene_id": "ch1_s3", "title": "...", "narrative": "...", "image_prompt": "...", "transitions_to_gameplay": true, "choices": []}
    ]
  },"""
    elif game_type == "card_board":
        cfg = card_board_config or {}
        hand_size = cfg.get("hand_size", 5)
        deck_size = cfg.get("deck_size", 20)
        win_cond = cfg.get("win_condition", "most_tiles")
        nep_stage = cfg.get("nep_stage", "middle")
        resources = cfg.get("resources", ["credibility", "influence", "empathy"])
        res_json = ", ".join(
            f'"{r}": {{"label": "{r.capitalize()}", "icon": "⭐", "start": 8, "max": 20}}'
            for r in resources
        )
        type_section = f"""  "hand_size": {hand_size},
  "max_turns": 15,
  "win_condition": "{win_cond}",
  "nep_stage": "{nep_stage}",
  "deck": [
    {{
      "card_id": "card_1", "title": "Open Offer", "icon": "🤝",
      "skill_tag": "adaptability", "nep_competency": "communication",
      "resource_bonus": {{"{resources[0] if resources else 'credibility'}": 2}},
      "tile_type_bonus": {{"negotiation": 1.5, "default": 1.0}},
      "color": "#6C5CE7"
    }},
    {{
      "card_id": "card_2", "title": "Bold Stance", "icon": "💪",
      "skill_tag": "risk_tolerance", "nep_competency": "critical_thinking",
      "resource_bonus": {{"{resources[1] if len(resources) > 1 else 'influence'}": 2}},
      "tile_type_bonus": {{"challenge": 1.5, "default": 1.0}},
      "color": "#E17055"
    }},
    {{
      "card_id": "card_3", "title": "Listen First", "icon": "👂",
      "skill_tag": "empathy", "nep_competency": "social_emotional",
      "resource_bonus": {{"{resources[2] if len(resources) > 2 else 'empathy'}": 2}},
      "tile_type_bonus": {{"collaboration": 1.5, "default": 1.0}},
      "color": "#00B894"
    }},
    ... ({deck_size} cards total — distribute skill_tags evenly: strategic_thinking, risk_tolerance, delayed_gratification, adaptability, resilience, empathy)
  ],
  "board": {{
    "tiles": [
      {{"id": "t1", "type": "negotiation", "label": "Stakeholder Meet", "icon": "🤝", "position": 0}},
      {{"id": "t2", "type": "challenge", "label": "Hard Decision", "icon": "⚡", "position": 1}},
      {{"id": "t3", "type": "collaboration", "label": "Team Sync", "icon": "👥", "position": 2}},
      {{"id": "t4", "type": "strategy", "label": "Plan Room", "icon": "📋", "position": 3}},
      {{"id": "t5", "type": "opportunity", "label": "New Lead", "icon": "💡", "position": 4}},
      {{"id": "t6", "type": "crisis", "label": "Crisis Point", "icon": "🚨", "position": 5}},
      ... (10-15 tiles total themed to: {theme})
    ],
    "size": 15
  }},
  "resources": {{{res_json}}},
  "ai_opponent": {{
    "name": "Mento", "avatar": "🤖", "strategy": "balanced", "trade_frequency": 0.3
  }},"""
    elif game_type == "board":
        type_section = f"""  "board_config": {{
    "renderer": "standard",
    "board_size": 20,
    "starting_resources": {{"money": 100, "reputation": 50, "team": 30}},
    "win_condition": "highest_reputation",
    "rounds": 12
  }},
  "rounds": [
    {{
      "id": "round_1", "title": "Starting Move",
      "situation": "Your first turn on the board. Theme: {theme}",
      "image_prompt": "Board game scene for this theme",
      "coaching_moment": "Every move shapes your long-term position.",
      "choices": [
        {{"id": "c1", "label": "Invest in team", "desc": "Build foundation",
          "delta": {{"team": 10, "money": -15, "strategic_thinking": 8}},
          "skill_tags": ["strategic_thinking", "delayed_gratification"],
          "feedback": "Long-term thinking pays off."}},
        {{"id": "c2", "label": "Quick profit", "desc": "Short-term gain",
          "delta": {{"money": 20, "reputation": -5, "risk_tolerance": 7}},
          "skill_tags": ["risk_tolerance"],
          "feedback": "Short-term wins can cost later."}}
      ]
    }},
    ... (12 rounds total — vary events, crises, opportunities themed to: {theme})
  ],"""
    elif game_type == "minigame":
        type_section = f"""  "minigame_config": {{
    "subtype": "timed_challenge",
    "time_limit_seconds": 90,
    "questions": [
      {{"id": "q1", "question": "Question related to {theme}", "options": ["Answer A", "Answer B", "Answer C", "Answer D"], "correct": 0, "skill_tag": "strategic_thinking"}},
      {{"id": "q2", "question": "Second question about {theme}", "options": ["Answer A", "Answer B", "Answer C", "Answer D"], "correct": 1, "skill_tag": "adaptability"}},
      {{"id": "q3", "question": "Third question on {theme}", "options": ["Answer A", "Answer B", "Answer C", "Answer D"], "correct": 2, "skill_tag": "resilience"}}
    ],
    "scoring": {{"correct_points": 10, "streak_bonus": 5, "time_bonus_per_second": 0.5}}
  }},"""
    elif game_type == "card":
        type_section = f"""  "card_config": {{
    "hand_size": 5,
    "deck_size": 30,
    "max_rounds": 10
  }},
  "deck": [
    {{"id": "c1", "name": "Bold Move", "type": "action", "power": 7, "skill_tag": "risk_tolerance", "description": "A decisive action card themed to {theme}"}},
    {{"id": "c2", "name": "Patience Play", "type": "defense", "power": 5, "skill_tag": "delayed_gratification", "description": "A patient waiting strategy"}},
    {{"id": "c3", "name": "Team Boost", "type": "resource", "power": 6, "skill_tag": "empathy", "description": "Leverage team strength"}},
    ... (30 cards total — vary types and skill_tags across all 8 dimensions)
  ],"""
    elif game_type in ("strategy", "strategy_grid"):
        type_section = f"""  "grid_config": {{
    "size": 8,
    "terrain_types": ["plains", "forest", "mountain", "water"],
    "resources": ["wood", "stone", "food"],
    "win_condition": "territory_control",
    "max_turns": 20
  }},
  "scenarios": [
    {{"id": "s1", "title": "Opening Position", "description": "Initial setup for {theme}", "skill_focus": "strategic_thinking"}},
    {{"id": "s2", "title": "Expansion Phase", "description": "Grow your territory", "skill_focus": "risk_tolerance"}},
    {{"id": "s3", "title": "Final Push", "description": "Decisive endgame", "skill_focus": "adaptability"}}
  ],
  "dimension_scoring_weights": {{"strategic_thinking": 0.4, "risk_tolerance": 0.3, "adaptability": 0.2, "resilience": 0.1}},"""
    elif game_type == "chess_strategy":
        type_section = f"""  "chess_config": {{
    "variant": "standard",
    "time_control": "10+5",
    "coaching_enabled": true,
    "theme": "{theme}"
  }},
  "scenarios": [
    {{"id": "sc1", "name": "Opening Principles", "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "objective": "Develop pieces and control center", "skill_focus": "strategic_thinking"}},
    {{"id": "sc2", "name": "Tactical Puzzle", "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQK2R w KQkq - 0 6", "objective": "Find the best continuation", "skill_focus": "risk_tolerance"}}
  ],
  "dimension_scoring_weights": {{"strategic_thinking": 0.5, "risk_tolerance": 0.3, "adaptability": 0.2}},"""
    elif game_type == "trump_card":
        type_section = f"""  "trump_card_config": {{
    "attribute_count": 5,
    "deck_size": 20,
    "win_condition": "collect_all_cards"
  }},
  "cards": [
    {{"id": "card_1", "name": "Leader Alpha", "icon": "👑", "attributes": {{"Influence": 95, "Wisdom": 80, "Courage": 85, "Empathy": 70, "Vision": 90}}, "skill_tag": "strategic_thinking"}},
    {{"id": "card_2", "name": "Team Player", "icon": "🤝", "attributes": {{"Influence": 70, "Wisdom": 75, "Courage": 65, "Empathy": 95, "Vision": 80}}, "skill_tag": "empathy"}},
    {{"id": "card_3", "name": "Risk Taker", "icon": "🎲", "attributes": {{"Influence": 80, "Wisdom": 65, "Courage": 95, "Empathy": 60, "Vision": 75}}, "skill_tag": "risk_tolerance"}},
    ... (20 cards total themed to: {theme})
  ],
  "dimension_scoring_weights": {{"strategic_thinking": 0.4, "risk_tolerance": 0.3, "empathy": 0.2, "adaptability": 0.1}},"""
    elif game_type == "tower_defense":
        type_section = f"""  "td_config": {{
    "waves": 10,
    "starting_gold": 200,
    "lives": 20,
    "map_size": [20, 10],
    "theme": "{theme}"
  }},
  "towers": [
    {{"id": "t1", "name": "Strategy Tower", "cost": 50, "damage": 20, "range": 3, "skill_tag": "strategic_thinking"}},
    {{"id": "t2", "name": "Resilience Wall", "cost": 30, "damage": 5, "range": 1, "hp": 100, "skill_tag": "resilience"}},
    {{"id": "t3", "name": "Adapt Cannon", "cost": 80, "damage": 40, "range": 4, "skill_tag": "adaptability"}}
  ],
  "dimension_scoring_weights": {{"strategic_thinking": 0.4, "resilience": 0.3, "adaptability": 0.3}},"""
    elif game_type == "puzzle_match":
        type_section = f"""  "puzzle_config": {{
    "grid_size": 6,
    "colors": 5,
    "levels": 10,
    "time_limit_seconds": 120,
    "theme": "{theme}"
  }},
  "levels": [
    {{"id": "l1", "name": "Warm Up", "grid": [[1,2,3],[2,3,1],[3,1,2]], "target_score": 100, "skill_focus": "strategic_thinking"}},
    {{"id": "l2", "name": "Pattern Recognition", "grid": [[1,1,2,3],[2,2,1,3],[3,1,1,2],[1,3,2,1]], "target_score": 200, "skill_focus": "adaptability"}}
  ],
  "dimension_scoring_weights": {{"strategic_thinking": 0.4, "adaptability": 0.3, "resilience": 0.3}},"""
    elif game_type == "go_territory":
        type_section = f"""  "go_config": {{
    "board_size": 9,
    "komi": 6.5,
    "time_limit_seconds": 300,
    "theme": "{theme}",
    "coaching_enabled": true
  }},
  "scenarios": [
    {{"id": "sc1", "name": "Corner Joseki", "description": "Master corner opening sequences", "skill_focus": "strategic_thinking"}},
    {{"id": "sc2", "name": "Life and Death", "description": "Solve life-or-death problems", "skill_focus": "risk_tolerance"}}
  ],
  "dimension_scoring_weights": {{"strategic_thinking": 0.5, "risk_tolerance": 0.3, "adaptability": 0.2}},"""
    elif game_type == "reversi":
        type_section = f"""  "reversi_config": {{
    "board_size": 8,
    "time_limit_seconds": 180,
    "ai_difficulty": "medium",
    "theme": "{theme}"
  }},
  "scenarios": [
    {{"id": "sc1", "name": "Corner Strategy", "description": "Control the corners to win", "skill_focus": "strategic_thinking"}},
    {{"id": "sc2", "name": "Edge Control", "description": "Dominate the edges", "skill_focus": "adaptability"}}
  ],
  "dimension_scoring_weights": {{"strategic_thinking": 0.5, "adaptability": 0.3, "risk_tolerance": 0.2}},"""
    else:
        # Generic fallback for any other types
        type_section = f"""  "rounds": [
    {{
      "id": "round_1", "title": "Opening Challenge",
      "situation": "Scenario matching the theme and game type: {game_type}",
      "image_prompt": "Vivid scene illustration for this round",
      "coaching_moment": "Key teaching insight",
      "choices": [
        {{"id": "c1", "label": "Choice A", "desc": "Description",
          "delta": {{"strategic_thinking": 7, "risk_tolerance": 5}},
          "skill_tags": ["strategic_thinking"],
          "feedback": "Feedback text"}},
        {{"id": "c2", "label": "Choice B", "desc": "Description",
          "delta": {{"delayed_gratification": 7, "resilience": 5}},
          "skill_tags": ["delayed_gratification"],
          "feedback": "Feedback text"}},
        {{"id": "c3", "label": "Choice C", "desc": "Description",
          "delta": {{"empathy": 7, "adaptability": 5}},
          "skill_tags": ["empathy"],
          "feedback": "Feedback text"}}
      ]
    }},
    ... (7 rounds total)
  ],"""

    user_prompt = f"""Generate a complete educational game JSON for:
- Theme: {theme}
- Game type: {game_type}
- Age group: {age_group}
- Difficulty: {difficulty}
- Special features: {features_str}

Return this EXACT JSON structure (no markdown):
{{
  "title": "Engaging game title",
  "game_type": "{game_type}",
  "description": "2-3 sentence description of what players learn",
  "learning_concept": "Core soft skill concept being taught",
  "learning_objectives": ["obj1", "obj2", "obj3", "obj4"],
  "coach_mode_default": true,
  "difficulty_modifiers": {{
    "easy": {{"resource_multiplier": 1.3, "negative_event_chance": 0.2}},
    "medium": {{"resource_multiplier": 1.0, "negative_event_chance": 0.4}},
    "hard": {{"resource_multiplier": 0.75, "negative_event_chance": 0.65}}
  }},
  "dimension_scoring_weights": {{
    "strategic_thinking": {{"choice_weight": 1.0, "outcome_weight": 0.8}},
    "risk_tolerance": {{"choice_weight": 0.9, "outcome_weight": 0.7}},
    "delayed_gratification": {{"choice_weight": 0.8, "outcome_weight": 1.0}},
    "adaptability": {{"choice_weight": 1.0, "outcome_weight": 0.9}},
    "resilience": {{"choice_weight": 0.9, "outcome_weight": 1.1}},
    "empathy": {{"choice_weight": 1.0, "outcome_weight": 0.8}}
  }},
  "game_over_conditions": [
    {{"expression": "stress >= 90", "outcome": "lose", "title": "Burnout", "message": "The stress became too much to handle."}},
    {{"expression": "resilience <= 10", "outcome": "lose", "title": "Gave Up", "message": "You lost your fighting spirit."}}
  ],
  "ai_image_config": {{
    "style": "vivid",
    "size": "1024x1024",
    "art_direction": "Colorful Indian illustrated style, warm educational tones, age-appropriate for {age_group}",
    "generate_on_first_play": true
  }},
  "glossary_terms": [
    {{"term": "Key term 1", "definition": "Clear definition", "example": "Example in context",
      "deep_dive": "Deeper explanation", "real_world_example": "Real world use case"}},
    {{"term": "Key term 2", "definition": "Definition", "example": "Example",
      "deep_dive": "Details", "real_world_example": "Real world"}},
    {{"term": "Key term 3", "definition": "Definition", "example": "Example",
      "deep_dive": "Details", "real_world_example": "Real world"}}
  ],
  "initial_state": {{
    "money_inr": 50000, "reputation": 50, "stress": 30, "team_trust": 50,
    "strategic_thinking": 50, "risk_tolerance": 50, "delayed_gratification": 50,
    "adaptability": 50, "resilience": 50, "empathy": 50
  }},
{type_section}
  "transfer_exercises": [
    {{"skill_tag": "strategic_thinking", "game_context": "...", "real_world": "...", "challenge": "..."}},
    {{"skill_tag": "risk_tolerance", "game_context": "...", "real_world": "...", "challenge": "..."}},
    {{"skill_tag": "empathy", "game_context": "...", "real_world": "...", "challenge": "..."}}
  ],
  "achievements": [
    {{
      "id": "ach1", "name": "Achievement name", "icon": "🏆",
      "description": "What behaviour earns this",
      "rarity": "common", "xp_reward": 75,
      "condition": {{"expression": "strategic_thinking >= 65"}}
    }},
    {{
      "id": "ach2", "name": "Achievement 2", "icon": "⭐",
      "description": "How to earn",
      "rarity": "rare", "xp_reward": 120,
      "condition": {{"expression": "resilience >= 70 AND empathy >= 60"}}
    }},
    {{
      "id": "ach3", "name": "Achievement 3", "icon": "🎯",
      "description": "How to earn",
      "rarity": "epic", "xp_reward": 200,
      "condition": {{"expression": "risk_tolerance >= 75"}}
    }}
  ]
}}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_json=True,
        temperature=0.7,
        max_tokens=6000,
        purpose="generate_full_game",
        fallback={"error": "Game generation failed — please try again"},
    )
    return result


def generate_engine_config(
    game_type: str,
    theme: str,
    difficulty: str = "medium",
    age_group: str = "12-16",
) -> dict:
    """
    Generate engine-specific configuration for any of the 15 game types via LLM.
    Returns the config block ready to embed in game JSON under the appropriate key.
    """
    type_prompts = {
        "board": (
            "board_config",
            """Generate a board_config for a board game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "type": "grid",
  "size": {{"rows": 8, "cols": 8}},
  "max_turns": 20,
  "spaces": [
    {{"id": "s1", "position": {{"x":0,"y":0}}, "type":"start","description":"Begin","effect":{{}}}},
    {{"id": "s2", "position": {{"x":1,"y":0}}, "type":"bonus","description":"Opportunity","effect":{{"bonus_coins":50}}}},
    {{"id": "s3", "position": {{"x":2,"y":0}}, "type":"challenge","description":"Obstacle","effect":{{"penalty_stress":10}}}},
    {{"id": "s4", "position": {{"x":3,"y":0}}, "type":"event","description":"Random event","effect":{{"event":"market_shift"}}}},
    {{"id": "s5", "position": {{"x":4,"y":0}}, "type":"checkpoint","description":"Progress check","effect":{{"xp":20}}}},
    {{"id": "s6", "position": {{"x":5,"y":0}}, "type":"finish","description":"Goal reached","effect":{{"bonus_coins":200}}}}
  ],
  "movement_rules": {{"type":"dice","dice":"1d6","max_spaces":6}},
  "players": [{{"id":"p1","name":"Player","start_position":{{"x":0,"y":0}},"color":"blue"}}],
  "events": [
    {{"id":"ev1","trigger":"land_on_event","title":"Market Shift","description":"Market changes!","effect":{{"bonus_coins":30}},"probability":0.4}},
    {{"id":"ev2","trigger":"land_on_event","title":"Crisis","description":"Unexpected crisis.","effect":{{"penalty_stress":15}},"probability":0.3}}
  ]
}}""",
        ),
        "chess_strategy": (
            "chess_config",
            """Generate a chess_config for an educational chess game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "board_size": 8,
  "time_limit_seconds": 300,
  "ai_depth": 2,
  "show_hints": {"easy": true, "medium": false, "hard": false}["{difficulty}"],
  "scenario": "standard",
  "theme_label": "{theme}",
  "learning_focus": "strategic positioning",
  "pieces": {{
    "pawn": {{"label":"Pawn","icon":"♟","move":"forward 1","capture":"diagonal 1"}},
    "rook": {{"label":"Rook","icon":"♜","move":"any straight","capture":"any straight"}},
    "knight": {{"label":"Knight","icon":"♞","move":"L-shape","capture":"L-shape"}},
    "bishop": {{"label":"Bishop","icon":"♝","move":"any diagonal","capture":"any diagonal"}},
    "queen": {{"label":"Queen","icon":"♛","move":"any direction","capture":"any direction"}},
    "king": {{"label":"King","icon":"♚","move":"1 square any","capture":"1 square any"}}
  }},
  "starting_positions": "standard"
}}""",
        ),
        "go_territory": (
            "go_config",
            """Generate a go_config for an educational Go/territory game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "board_size": 9,
  "komi": 6.5,
  "ai_level": "beginner",
  "time_limit_seconds": 600,
  "theme_label": "{theme}",
  "territory_names": {{"black": "Player Territory", "white": "Opponent Territory"}},
  "bonus_zones": [
    {{"position":{{"x":4,"y":4}},"bonus":5,"description":"Center — high strategic value"}},
    {{"position":{{"x":2,"y":2}},"bonus":3,"description":"Corner advantage"}}
  ],
  "learning_focus": "territory control and long-term planning"
}}""",
        ),
        "reversi": (
            "reversi_config",
            """Generate a reversi_config for an educational Reversi game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "board_size": 8,
  "ai_level": "greedy",
  "show_valid_moves": true,
  "time_limit_seconds": 300,
  "theme_label": "{theme}",
  "flip_narrative": {{
    "player_flip": "You convert their position!",
    "ai_flip": "Opponent converts your position!"
  }},
  "colors": {{"player": "#4f46e5", "opponent": "#ef4444"}},
  "learning_focus": "positional thinking and reversal strategy"
}}""",
        ),
        "tower_defense": (
            "td_config",
            """Generate a td_config for a tower defense game with theme: {theme}, difficulty: {difficulty}, age: {age_group}.
Return JSON:
{{
  "grid_size": {{"rows": 10, "cols": 16}},
  "starting_gold": 100,
  "total_waves": 8,
  "lives": 20,
  "path": [{{"x":0,"y":5}},{{"x":4,"y":5}},{{"x":4,"y":2}},{{"x":12,"y":2}},{{"x":12,"y":8}},{{"x":16,"y":8}}],
  "towers": [
    {{"id":"t1","label":"Basic Tower","icon":"🗼","cost":50,"damage":15,"range":2,"fire_rate":1.0,"description":"Reliable defense"}},
    {{"id":"t2","label":"Rapid Tower","icon":"⚡","cost":80,"damage":8,"range":1.5,"fire_rate":2.0,"description":"Fast attacks"}},
    {{"id":"t3","label":"Sniper Tower","icon":"🎯","cost":120,"damage":40,"range":4,"fire_rate":0.5,"description":"Long range, slow"}}
  ],
  "enemies": [
    {{"id":"e1","label":"Scout","icon":"🏃","hp":30,"speed":1.5,"reward":10,"description":"Fast but weak"}},
    {{"id":"e2","label":"Warrior","icon":"⚔️","hp":80,"speed":1.0,"reward":20,"description":"Balanced"}},
    {{"id":"e3","label":"Tank","icon":"🛡️","hp":200,"speed":0.5,"reward":40,"description":"Slow but tough"}},
    {{"id":"e4","label":"Boss","icon":"👹","hp":500,"speed":0.7,"reward":100,"description":"Wave boss"}}
  ],
  "theme_label": "{theme}",
  "learning_focus": "resource allocation and threat prioritization"
}}""",
        ),
        "puzzle_match": (
            "puzzle_config",
            """Generate a puzzle_config for a puzzle/match game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "grid_size": {{"rows": 8, "cols": 8}},
  "time_limit_seconds": 90,
  "min_match": 3,
  "shuffle_strength": 0.75,
  "tile_types": [
    {{"id":"t1","label":"Concept A","icon":"🔵","color":"#3b82f6","points":10}},
    {{"id":"t2","label":"Concept B","icon":"🟢","color":"#22c55e","points":10}},
    {{"id":"t3","label":"Concept C","icon":"🟡","color":"#eab308","points":15}},
    {{"id":"t4","label":"Concept D","icon":"🔴","color":"#ef4444","points":20}},
    {{"id":"t5","label":"Wild","icon":"⭐","color":"#a855f7","points":30,"is_wild":true}}
  ],
  "special_tiles": [
    {{"id":"bomb","label":"Bomb","icon":"💣","trigger":"match_4","effect":"clear_row","description":"Clears entire row"}},
    {{"id":"lightning","label":"Lightning","icon":"⚡","trigger":"match_5","effect":"clear_column","description":"Clears column"}}
  ],
  "scoring": {{"base":10,"combo_multiplier":1.5,"time_bonus":true}},
  "theme_label": "{theme}",
  "learning_focus": "pattern recognition and cognitive flexibility"
}}""",
        ),
        "strategy_grid": (
            "strategy_grid_config",
            """Generate a strategy_grid_config for a turn-based strategy game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "grid_size": {{"rows": 12, "cols": 16}},
  "max_turns": 25,
  "players": 2,
  "terrain": [
    {{"type":"plains","color":"#86efac","movement_cost":1,"defense_bonus":0,"label":"Plains"}},
    {{"type":"forest","color":"#16a34a","movement_cost":2,"defense_bonus":2,"label":"Forest"}},
    {{"type":"mountain","color":"#78716c","movement_cost":3,"defense_bonus":3,"label":"Mountain"}},
    {{"type":"water","color":"#60a5fa","movement_cost":99,"defense_bonus":0,"label":"Water","impassable":true}}
  ],
  "units": [
    {{"id":"u1","label":"Strategist","icon":"🧠","hp":40,"attack":8,"defense":4,"movement":3,"cost":50}},
    {{"id":"u2","label":"Guardian","icon":"🛡️","hp":80,"attack":5,"defense":10,"movement":2,"cost":80}},
    {{"id":"u3","label":"Scout","icon":"👁️","hp":25,"attack":6,"defense":2,"movement":5,"cost":40}}
  ],
  "win_conditions": [
    {{"type":"eliminate_all","description":"Defeat all opponent units"}},
    {{"type":"capture_objective","description":"Hold the center objective for 5 turns"}}
  ],
  "starting_resources": {{"gold":200,"population":5}},
  "resource_income_per_turn": {{"gold":30}},
  "theme_label": "{theme}",
  "learning_focus": "systems thinking and resource optimization"
}}""",
        ),
        "card": (
            "card_config",
            """Generate a card_config for a card game with theme: {theme}, difficulty: {difficulty}, age: {age_group}.
Return JSON:
{{
  "hand_size": 5,
  "max_hand_size": 7,
  "draw_per_turn": 1,
  "starting_energy": 3,
  "max_energy": 5,
  "energy_regen_per_turn": 3,
  "starting_hp": 30,
  "deck": [
    {{"id":"c1","name":"Quick Strike","type":"attack","cost":1,"power":5,"rarity":"common","description":"Deal 5 damage","effects":{{"damage":5}}}},
    {{"id":"c2","name":"Shield Wall","type":"defense","cost":2,"power":0,"rarity":"common","description":"Gain 8 shield","effects":{{"shield":8}}}},
    {{"id":"c3","name":"Burst","type":"attack","cost":3,"power":12,"rarity":"uncommon","description":"Deal 12 damage","effects":{{"damage":12}}}},
    {{"id":"c4","name":"Heal","type":"heal","cost":2,"power":0,"rarity":"common","description":"Restore 6 HP","effects":{{"heal":6}}}},
    {{"id":"c5","name":"Combo","type":"special","cost":4,"power":8,"rarity":"rare","description":"Deal 8+draw 2","effects":{{"damage":8,"draw":2}}}},
    {{"id":"c6","name":"Defend","type":"defense","cost":1,"power":0,"rarity":"common","description":"Gain 4 shield","effects":{{"shield":4}}}},
    {{"id":"c7","name":"Slash","type":"attack","cost":2,"power":8,"rarity":"common","description":"Deal 8 damage","effects":{{"damage":8}}}},
    {{"id":"c8","name":"Restoration","type":"heal","cost":3,"power":0,"rarity":"uncommon","description":"Restore 12 HP","effects":{{"heal":12}}}}
  ],
  "enemy": {{"hp":50,"attack":6,"defense":2,"name":"Challenger","icon":"👤"}},
  "theme_label": "{theme}",
  "learning_focus": "probability, timing, and risk management"
}}""",
        ),
        "minigame": (
            "minigame_config",
            """Generate a minigame_config embedding 3 educational minigames for theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "minigames": [
    {{
      "id": "mg1", "type": "memory_match", "title": "Knowledge Match",
      "description": "Match related concepts",
      "pairs": [
        {{"a": "Concept 1", "b": "Definition 1"}},
        {{"a": "Concept 2", "b": "Definition 2"}},
        {{"a": "Concept 3", "b": "Definition 3"}},
        {{"a": "Concept 4", "b": "Definition 4"}}
      ],
      "time_limit": 60, "perfect_score": 100,
      "rewards": {{"xp": 50, "coins": 30}}
    }},
    {{
      "id": "mg2", "type": "number_puzzle", "title": "Quick Math",
      "description": "Solve calculation challenges",
      "problems": [
        {{"question": "15 × 4 = ?", "answer": 60}},
        {{"question": "125 ÷ 5 = ?", "answer": 25}},
        {{"question": "37 + 48 = ?", "answer": 85}}
      ],
      "time_limit": 45, "perfect_score": 100,
      "rewards": {{"xp": 40, "coins": 25}}
    }},
    {{
      "id": "mg3", "type": "quick_time", "title": "Decision Speed",
      "description": "Quick decision making under pressure",
      "events": [
        {{"prompt": "Good opportunity!", "correct": "take", "time_window": 2.0}},
        {{"prompt": "Risky move!", "correct": "wait", "time_window": 1.5}},
        {{"prompt": "Team needs help!", "correct": "help", "time_window": 2.0}}
      ],
      "time_limit": 30, "perfect_score": 100,
      "rewards": {{"xp": 45, "coins": 28}}
    }}
  ]
}}""",
        ),
        "story_branching": (
            "story_intro",
            """Generate a story_intro section for a branching narrative game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "title": "Prologue: The Beginning",
  "scene": "An engaging opening scene for {theme}...",
  "narrator_text": "Your journey begins...",
  "choices": [
    {{
      "id": "path_careful",
      "label": "Approach carefully",
      "desc": "Think before acting",
      "leads_to": "scene_2_careful",
      "delta": {{"delayed_gratification": 5, "strategic_thinking": 3}},
      "skill_tags": ["delayed_gratification"]
    }},
    {{
      "id": "path_bold",
      "label": "Jump in boldly",
      "desc": "Take the initiative",
      "leads_to": "scene_2_bold",
      "delta": {{"risk_tolerance": 8, "adaptability": 3}},
      "skill_tags": ["risk_tolerance"]
    }}
  ],
  "background_image": null,
  "music": null
}}""",
        ),
        "ai_arena": (
            "ai_arena_config",
            """Generate an ai_arena_config for an AI negotiation/competition game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "rounds": 5,
  "starting_resources": 100,
  "ai_intelligence": 0.75,
  "crisis_frequency": 0.2,
  "resource_boost": 1.0,
  "npc_personas": [
    {{"id":"npc1","name":"Rival Alex","personality":"aggressive","icon":"😤","strategy":"max_pressure"}},
    {{"id":"npc2","name":"Mentor Sam","personality":"cooperative","icon":"🤝","strategy":"win_win"}},
    {{"id":"npc3","name":"Wild Card","personality":"unpredictable","icon":"🎲","strategy":"random"}}
  ],
  "crisis_events": [
    {{"id":"c1","title":"Market Crash","description":"Resources drop 20%","effect":{{"resource_change":-20}},"probability":0.3}},
    {{"id":"c2","title":"Opportunity","description":"Resources gain 15%","effect":{{"resource_change":15}},"probability":0.4}}
  ],
  "theme_label": "{theme}",
  "learning_focus": "competitive reasoning and negotiation"
}}""",
        ),
        "negotiation": (
            "negotiation_config",
            """Generate a negotiation_config for a negotiation simulation with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "max_turns": 10,
  "ai_concession_rate": 0.25,
  "relationship_start": 50,
  "zopa": {{"player_min": 40, "player_max": 80, "ai_min": 35, "ai_max": 75}},
  "issues": [
    {{"id":"price","label":"Price","weight":0.4,"player_anchor":80,"ai_anchor":50}},
    {{"id":"timeline","label":"Timeline","weight":0.3,"player_anchor":30,"ai_anchor":60}},
    {{"id":"quality","label":"Quality","weight":0.3,"player_anchor":90,"ai_anchor":70}}
  ],
  "ai_persona": {{"name":"Negotiator","style":"firm_but_fair","icon":"💼"}},
  "tactics": ["anchoring","concession","package_deal","good_cop"],
  "theme_label": "{theme}",
  "learning_focus": "persuasion, empathy, and deal-making"
}}""",
        ),
        "debate": (
            "debate_config",
            """Generate a debate_config for a debate simulation game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "rounds": 5,
  "ai_counter_strength": 0.75,
  "time_per_argument": 120,
  "scoring_criteria": ["logic","evidence","persuasion","rebuttal"],
  "topic": "A compelling debate topic related to {theme}",
  "positions": {{"player":"For","ai":"Against"}},
  "argument_templates": [
    "Consider the impact on...",
    "Evidence shows that...",
    "The long-term consequence is..."
  ],
  "ai_persona": {{"name":"Debate Opponent","style":"logical","icon":"🎭"}},
  "theme_label": "{theme}",
  "learning_focus": "critical thinking, argumentation, and persuasion"
}}""",
        ),
        "rounds": (
            None,  # rounds games don't need a separate config block
            None,
        ),
        "strategy": (
            "strategy_config",
            """Generate a strategy_config for a resource management strategy game with theme: {theme}, difficulty: {difficulty}.
Return JSON:
{{
  "max_turns": 20,
  "starting_resources": {{"money": 1000, "workers": 10, "reputation": 50}},
  "resource_income": {{"money": 200, "workers": 1}},
  "events": [
    {{"id":"e1","title":"Economic Boom","effect":{{"money":500}},"probability":0.2,"description":"Market grows"}},
    {{"id":"e2","title":"Recession","effect":{{"money":-300}},"probability":0.2,"description":"Market contracts"}},
    {{"id":"e3","title":"Skilled Worker","effect":{{"workers":3}},"probability":0.3,"description":"Talent joins"}}
  ],
  "win_conditions": [
    {{"type":"money_threshold","value":5000,"description":"Accumulate ₹5000"}},
    {{"type":"reputation_threshold","value":80,"description":"Reach 80% reputation"}}
  ],
  "theme_label": "{theme}",
  "learning_focus": "strategic planning and resource management"
}}""",
        ),
    }

    type_info = type_prompts.get(game_type)
    if not type_info or type_info[0] is None:
        return {"error": f"No engine config template for game_type: {game_type}"}

    config_key, prompt_template = type_info
    prompt = prompt_template.format(theme=theme, difficulty=difficulty, age_group=age_group)

    system_prompt = (
        "You are an expert educational game engine designer. "
        "Generate production-ready engine configuration JSON for educational games targeting Indian students. "
        "CRITICAL: Return ONLY valid JSON matching the exact structure shown. No markdown, no extra text."
    )

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=prompt,
        response_json=True,
        temperature=0.6,
        max_tokens=2000,
        purpose="generate_engine_config",
        fallback={"error": f"Engine config generation failed for {game_type}"},
    )

    if result.get("error"):
        return result

    return {"config_key": config_key, "config": result}


def generate_mira_and_competitor(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate Coach Mento feedback, question, and competitor reaction.
    Enhanced to support dynamic competitor personalities and competitive scenarios.

    Returns:
      {
        "mira": "Coach feedback...",
        "question": "Follow-up question...",
        "competitor": "Competitor reaction..."
      }
    """
    if not llm_enabled():
        return {
            "mira": "Interesting choice! What made you think of that?",
            "question": "What could be the consequences of this decision?",
            "competitor": "Hmm… interesting. We'll see!"
        }

    # Extract competitor info if available
    competitor_actions = context.get("competitor_actions", [])
    market_shares = context.get("market_shares", {})
    player_share = market_shares.get("player", {}).get("market_share", 0) if market_shares else 0
    
    # Build enhanced competitor context
    competitor_context = ""
    if competitor_actions:
        competitor_context = "\n\nCOMPETITOR ACTIONS THIS ROUND:\n"
        for comp in competitor_actions:
            comp_share = market_shares.get(comp.get("id", ""), {}).get("market_share", 0) if market_shares else 0
            decision = comp.get("decision", {})
            competitor_context += f"- {comp.get('name', 'Competitor')} ({comp.get('personality_type', 'balanced')}): "
            competitor_context += f"Market Share: {comp_share:.1f}%, "
            if decision.get("price"):
                competitor_context += f"Price: ₹{decision['price']}, "
            if decision.get("marketing_spend"):
                competitor_context += f"Marketing: ₹{decision['marketing_spend']}, "
            if decision.get("quality_investment"):
                competitor_context += f"Quality: ₹{decision['quality_investment']}"
            if not comp.get("is_active", True):
                competitor_context += " [BANKRUPT]"
            competitor_context += "\n"
        
        competitor_context += f"\nYour Market Share: {player_share:.1f}%\n"

    system_prompt = (
        "You are Coach Mento, a wise AI mentor for students aged 10-14. "
        "Use the Socratic method: ask guiding questions instead of giving direct answers. "
        "Help students think critically about their choices in competitive business scenarios. "
        "Be encouraging but never reveal the 'right' answer. "
        "Keep language safe, age-appropriate, and positive. "
        "\n\nWhen competitors are present:\n"
        "- Help students understand competitive dynamics\n"
        "- Encourage strategic thinking about market positioning\n"
        "- Ask about how competitors' actions might affect their strategy\n"
        "- Celebrate wins but also help learn from setbacks\n"
        "\n\nReturn ONLY valid JSON with keys: mira, question, competitor. "
        "- mira: 1-2 sentences with a guiding question or thought-provoking prompt (NOT direct advice) "
        "- question: A deeper follow-up question to develop critical thinking "
        "- competitor: A short competitive reaction that reflects the competitor's personality type and current situation "
        "  (aggressive competitors are bold, balanced are strategic, quality_focused emphasize excellence, followers react to market)"
    )

    user_content = {
        "round": context.get("round_title", ""),
        "goal": context.get("goal", ""),
        "choice": context.get("choice", {}).get("label", ""),
        "events": [e.get("fallback_text", "") for e in context.get("events", [])],
        "state": context.get("state_after_events", {}),
        "competitor_name": context.get("competitor_name", "Competitor"),
        "competitive_context": competitor_context
    }

    fallback = {
        "mira": "Interesting! What made you choose that path?",
        "question": "How might this affect your goals?",
        "competitor": "We're watching closely!"
    }

    data = llm_call(
        system_prompt=system_prompt,
        user_prompt=json.dumps(user_content),
        temperature=0.7,
        purpose="mira_and_competitor",
        fallback=fallback,
    )

    # Ensure all keys exist
    for k in ["mira", "question", "competitor"]:
        if k not in data:
            data[k] = ""

    return data


def generate_final_report(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate final report with kid summary, teacher insight, and badges.
    
    Returns:
      {
        "kid_summary": "Engaging summary for student...",
        "teacher_insight": "Learning insights for teacher...",
        "badges": ["badge1", "badge2", ...]
      }
    """
    if not llm_enabled():
        return {
            "kid_summary": "You finished the game! You made smart choices and learned real skills.",
            "teacher_insight": "Student engaged well with decisions. Review stress and teamwork patterns.",
            "badges": context.get("badges", [])
        }

    system_prompt = (
        "You write a kid-friendly report and teacher insights for educational games. "
        "Return ONLY valid JSON with keys: kid_summary, teacher_insight, badges. "
        "- kid_summary: 2-3 sentences celebrating achievements (age 10-14) "
        "- teacher_insight: 2-3 sentences about learning patterns and NEP skills, "
        "  INCLUDE insights from the student's reflections to show their thinking process "
        "- badges: use the badges provided in context"
    )

    fallback = {
        "kid_summary": "Great work! You completed the game with smart decisions.",
        "teacher_insight": "Good engagement. Student demonstrated decision-making skills.",
        "badges": context.get("badges", [])
    }

    data = llm_call(
        system_prompt=system_prompt,
        user_prompt=json.dumps(context),
        temperature=0.6,
        purpose="final_report",
        fallback=fallback,
    )

    # Ensure badges exist
    if "badges" not in data:
        data["badges"] = context.get("badges", [])

    return data


def generate_report_cards(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate deterministic parent and teacher report cards at game completion.
    Uses temperature=0 for consistency.
    
    Args:
        context: Game completion data including:
            - student_name: Student's name
            - game_title: Name of the simulation
            - final_state: All resource values at end
            - choices_made: List of decisions
            - strengths: List of strength areas identified
            - growth_areas: List of areas for improvement
            - nep_skills: NEP 2020 skills demonstrated
    
    Returns:
      {
        "parent_report": {
          "strengths": ["skill1", "skill2", ...],
          "growth_areas": ["area1", "area2", ...],
          "insight": "Key message for parents..."
        },
        "teacher_report": {
          "skills_demonstrated": ["skill1", "skill2", ...],
          "nep_alignment": ["competency1", "competency2", ...],
          "recommendations": "Teaching recommendations..."
        }
      }
    """
    if not llm_enabled():
        # Fallback based on final state
        state = context.get("final_state", {})
        return {
            "parent_report": {
                "strengths": ["Ethical reasoning", "Decision making", "Perseverance"],
                "growth_areas": ["Risk assessment", "Strategic planning"],
                "insight": "Your child showed strong values and learned from real-world challenges."
            },
            "teacher_report": {
                "skills_demonstrated": ["Problem solving", "Critical thinking", "Collaboration"],
                "nep_alignment": ["Experiential learning", "Values-based education", "Life skills"],
                "recommendations": "Student engaged well with ethical dilemmas and business concepts."
            }
        }

    system_prompt = (
        "You are an educational assessment AI that generates parent and teacher report cards "
        "for students (ages 10-14) completing business simulation games. "
        "\n\nYour task: Analyze the student's gameplay data and generate TWO report cards:\n"
        "1. PARENT REPORT CARD - Focus on character strengths, life skills, and growth areas\n"
        "2. TEACHER REPORT CARD - Focus on academic skills, NEP 2020 alignment, and learning outcomes\n"
        "\n\nBe DETERMINISTIC and CONSISTENT: Base your assessment purely on the data provided.\n"
        "Same gameplay data should produce the same report.\n"
        "\n\nRETURN FORMAT (JSON only):\n"
        "{\n"
        "  \"parent_report\": {\n"
        "    \"strengths\": [3-5 observed strengths],\n"
        "    \"growth_areas\": [2-3 areas to develop],\n"
        "    \"insight\": \"One key message for parents (1-2 sentences)\"\n"
        "  },\n"
        "  \"teacher_report\": {\n"
        "    \"skills_demonstrated\": [3-5 academic/soft skills],\n"
        "    \"nep_alignment\": [3-4 NEP 2020 competencies demonstrated],\n"
        "    \"recommendations\": \"Teaching recommendations (2-3 sentences)\"\n"
        "  }\n"
        "}\n"
        "\n\nGUIDELINES:\n"
        "- Be positive but honest\n"
        "- Use concrete evidence from gameplay\n"
        "- Avoid generic praise - be specific\n"
        "- Growth areas should be constructive, not negative"
    )

    # Build state-aware fallback
    fb_state = context.get("final_state", {})
    fb_ethics = fb_state.get("ethics_meter", 50)
    fb_reputation = fb_state.get("reputation", 50)
    fb_strengths = []
    if fb_ethics >= 70:
        fb_strengths.extend(["Ethical reasoning", "Values-based decision making"])
    if fb_reputation >= 70:
        fb_strengths.append("Reputation management")
    if fb_state.get("team_trust", 50) >= 70:
        fb_strengths.append("Collaboration")
    if not fb_strengths:
        fb_strengths = ["Decision making", "Perseverance"]
    fb_growth = []
    if fb_ethics < 60:
        fb_growth.append("Ethical awareness")
    if fb_state.get("stress", 50) > 70:
        fb_growth.append("Stress management")
    if not fb_growth:
        fb_growth = ["Strategic planning", "Risk assessment"]

    fallback = {
        "parent_report": {
            "strengths": fb_strengths[:4],
            "growth_areas": fb_growth[:3],
            "insight": "Your child engaged with complex business decisions and demonstrated growing maturity."
        },
        "teacher_report": {
            "skills_demonstrated": ["Problem solving", "Decision making", "Real-world application"],
            "nep_alignment": ["Experiential learning", "Critical thinking", "Values-based education"],
            "recommendations": "Student shows promise in entrepreneurial thinking. Encourage reflection on decisions and outcomes."
        }
    }

    data = llm_call(
        system_prompt=system_prompt,
        user_prompt=json.dumps(context, indent=2),
        temperature=0,
        max_tokens=500,
        purpose="report_cards",
        fallback=fallback,
    )

    # Validate structure
    if "parent_report" not in data:
        data["parent_report"] = fallback["parent_report"]
    if "teacher_report" not in data:
        data["teacher_report"] = fallback["teacher_report"]

    return data


def generate_negotiation_context(idea_description: str) -> Dict[str, Any]:
    """Generate a custom negotiation scenario from a free-text description."""
    fallback = {
        "title": idea_description[:60],
        "description": idea_description,
        "setting": "A professional meeting room in an Indian office.",
        "cultural_context": "Urban Indian professional context",
        "your_objective": "Reach a mutually beneficial agreement.",
        "your_batna": "Walk away if terms are unfavorable.",
        "other_party": {
            "name": "Vikram Mehta",
            "role": "The other party",
            "personality": "Firm but fair negotiator",
            "objective": "Get the best deal possible",
            "avatar_emoji": "🤝"
        },
        "key_challenges": ["Competing interests", "Time pressure", "Trust building"],
        "conversation_turns": 8,
        "phases": ["Opening", "Exploration", "Bargaining", "Closing"],
    }
    if not llm_enabled():
        return fallback

    idea_description = _sanitize_user_input(idea_description, max_length=500)

    system_prompt = f"""You are a negotiation coach setting up a negotiation simulation for an Indian student.

The student wants to practice:
"{idea_description}"

Generate a realistic negotiation scenario. Return JSON:
{{
  "title": "A catchy 5-7 word title",
  "description": "2-3 sentences describing the scenario with Indian context",
  "setting": "1-2 sentences describing the location",
  "cultural_context": "1 sentence about the cultural setting",
  "your_objective": "What the student is trying to achieve",
  "your_batna": "Student's best alternative if negotiation fails",
  "other_party": {{
    "name": "A realistic Indian name",
    "role": "Their role/title",
    "personality": "1-2 sentences about how they negotiate",
    "objective": "What they want",
    "avatar_emoji": "An appropriate emoji"
  }},
  "key_challenges": ["3 challenges the student might face"],
  "conversation_turns": 8,
  "phases": ["Opening", "Exploration", "Bargaining", "Closing"]
}}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"Generate negotiation scenario for: {idea_description}",
        temperature=0.8,
        max_tokens=800,
        purpose="generate_negotiation_context",
        fallback=fallback,
    )
    if "other_party" not in result or not isinstance(result.get("other_party"), dict):
        result["other_party"] = fallback["other_party"]
    return result


def generate_debate_context(idea_description: str) -> Dict[str, Any]:
    """Generate a custom debate scenario from a free-text topic."""
    fallback = {
        "title": idea_description[:60],
        "description": idea_description,
        "topic": idea_description,
        "student_position": "For",
        "ai_position": "Against",
        "rounds": 3,
        "time_per_round_seconds": 120,
        "ai_persona": {
            "name": "Prof. Sharma",
            "style": "Academic and thorough",
            "avatar_emoji": "🎓"
        },
        "key_arguments": ["Consider multiple perspectives", "Use evidence", "Address counterarguments"],
    }
    if not llm_enabled():
        return fallback

    idea_description = _sanitize_user_input(idea_description, max_length=500)

    system_prompt = f"""You are a debate coach setting up a debate simulation for an Indian student.

The student wants to debate:
"{idea_description}"

Generate a debate scenario. Return JSON:
{{
  "title": "A catchy 5-7 word title",
  "description": "2-3 sentences framing the debate with Indian context",
  "topic": "The specific debate proposition",
  "student_position": "The position the student will argue (For/Against/Proposition)",
  "ai_position": "The position the AI will argue (opposite)",
  "rounds": 3,
  "time_per_round_seconds": 120,
  "ai_persona": {{
    "name": "A realistic Indian name",
    "style": "1-2 sentences about their debate style",
    "avatar_emoji": "An appropriate emoji"
  }},
  "key_arguments": ["3 strong arguments the student could make"]
}}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"Generate debate scenario for: {idea_description}",
        temperature=0.8,
        max_tokens=800,
        purpose="generate_debate_context",
        fallback=fallback,
    )
    if "ai_persona" not in result or not isinstance(result.get("ai_persona"), dict):
        result["ai_persona"] = fallback["ai_persona"]
    return result


_NEGOTIATION_DIFFICULTY_INSTRUCTIONS = {
    "beginner": "DIFFICULTY: BEGINNER — Be patient and encouraging. Concede readily when the student shows effort. Offer subtle hints about what tactics might work. Keep your resistance light.",
    "intermediate": "DIFFICULTY: INTERMEDIATE — Protect your interests firmly but reward good tactics. Require at least 2 solid arguments before conceding any major point.",
    "advanced": "DIFFICULTY: ADVANCED — Be a tough, experienced negotiator. Only concede on evidence-based, creative arguments. Introduce complications, test adaptability, and call out weak tactics directly.",
}

_DEBATE_DIFFICULTY_INSTRUCTIONS = {
    "beginner": "DIFFICULTY: BEGINNER — Present straightforward counter-arguments. Be encouraging. Do not overwhelm the student with complex evidence. Reward any structured reasoning.",
    "intermediate": "DIFFICULTY: INTERMEDIATE — Present solid counter-arguments backed by examples. Challenge weak logic but acknowledge good points fairly.",
    "advanced": "DIFFICULTY: ADVANCED — Present rigorous, evidence-heavy counter-arguments. Directly challenge logical fallacies. Only acknowledge student points that are exceptionally well-argued.",
}


def negotiation_ai_response(
    user_message: str,
    scenario_data: Dict[str, Any],
    conversation_history: list,
    current_turn: int,
    state: Dict[str, Any],
    scores_history: list = None,
    difficulty: str = "intermediate",
    coaching_tone: str = "supportive"
) -> Dict[str, Any]:
    """
    Generate AI response for negotiation game with calibrated scoring.

    Args:
        user_message: What the student said
        scenario_data: Full scenario context
        conversation_history: Previous exchanges
        current_turn: Current turn number
        state: Current game state (relationship_score, assertiveness, etc.)
        scores_history: List of previous analysis dicts for adaptive tier

    Returns:
        {
            "response": "AI character's response",
            "analysis": {
                "tactics_used": ["active_listening", "anchoring"],
                "relationship_impact": {"value": 5, "confidence": "high"},
                "assertiveness_impact": {"value": 3, "confidence": "medium"},
                "empathy_impact": {"value": 2, "confidence": "high"},
                "feedback": "You showed good empathy..."
            },
            "phase": "exploration",
            "negotiation_progress": 40,
            "detailed_guidance": ["tip1", ...]  // only for struggling students
        }
    """
    if not llm_enabled():
        fallback_text = "That's an interesting point. Let's discuss this further."
        ai_tactic = _detect_ai_negotiation_tactic(fallback_text)
        return {
            "response": fallback_text,
            "analysis": {
                "tactics_used": [],
                "relationship_impact": 0,
                "assertiveness_impact": 0,
                "empathy_impact": 0,
                "feedback": "LLM not enabled - using fallback response."
            },
            "phase": scenario_data.get("phases", ["Opening"])[min(current_turn, len(scenario_data.get("phases", [])) - 1)],
            "negotiation_progress": (current_turn / scenario_data.get("conversation_turns", 6)) * 100,
            "ai_tactic_used": ai_tactic["tactic_used"],
            "ai_tactic_label": ai_tactic["tactic_label"],
            "ai_tactic_tip": ai_tactic["tactic_tip"],
        }

    # Sanitize user input
    user_message = _sanitize_user_input(user_message, max_length=1000)

    # Compute adaptive tier from negotiation state history
    neg_tier = "developing"
    if scores_history:
        impact_scores = []
        for a in scores_history:
            if not isinstance(a, dict):
                continue
            for key in ["relationship_impact", "assertiveness_impact", "empathy_impact"]:
                v = a.get(key, 0)
                if isinstance(v, dict):
                    impact_scores.append(v.get("value", 0))
                elif isinstance(v, (int, float)):
                    impact_scores.append(v)
        if impact_scores:
            avg_impact = sum(impact_scores) / len(impact_scores)
            if avg_impact < -1:
                neg_tier = "struggling"
            elif avg_impact > 3:
                neg_tier = "strong"

    other_party = scenario_data.get("other_party", {}) or scenario_data.get("ai_persona", {})
    
    # Check if game provides custom system prompt template (GENERIC APPROACH)
    system_prompt_template = scenario_data.get("system_prompt_template")
    
    if system_prompt_template:
        # GENERIC: Use game-specific prompt template with variable substitution
        # Build replacement dict from all available data
        replacement_vars = {
            "character_name": other_party.get("name", "the other person"),
            "character_occupation": other_party.get("occupation", "person"),
            "setting": scenario_data.get("setting", ""),
            "context": scenario_data.get("context", ""),
            "personality": other_party.get("personality", ""),
            "interests": ", ".join(other_party.get("interests", [])) if isinstance(other_party.get("interests"), list) else str(other_party.get("interests", "")),
            "values": ", ".join(other_party.get("values", [])) if isinstance(other_party.get("values"), list) else str(other_party.get("values", "")),
            "conversation_style": other_party.get("conversation_style", "natural and friendly"),
            "phase": scenario_data.get("phase", "conversation"),
            "mood": other_party.get("mood", "friendly and open"),
            "objective": other_party.get("objective", ""),
            "current_turn": current_turn,
            "max_turns": scenario_data.get("max_turns", 10),
        }
        
        # Perform variable substitution
        system_prompt = system_prompt_template
        for key, value in replacement_vars.items():
            system_prompt = system_prompt.replace(f"{{{key}}}", str(value))
    
    else:
        # Adaptive tier instruction for negotiation
        if neg_tier == "struggling":
            neg_tier_instruction = """STUDENT SUPPORT MODE: The student is struggling with negotiation. Provide detailed guidance:
(1) what went wrong in their approach, (2) a specific example of a better way to phrase it, (3) a simpler tactic to try.
Be encouraging. Also return "detailed_guidance" in the response JSON with 2-3 actionable tips as a JSON array of strings."""
        elif neg_tier == "strong":
            neg_tier_instruction = """CHALLENGE MODE: The student is skilled. Be a tougher negotiator — introduce complications, test their adaptability.
Keep feedback brief — one advanced tactic to try. Do NOT return detailed_guidance."""
        else:
            neg_tier_instruction = """STANDARD MODE: Give balanced feedback with one clear suggestion. Do NOT return detailed_guidance."""

        # FALLBACK: Use default negotiation prompt for backward compatibility
        _diff_instr = _NEGOTIATION_DIFFICULTY_INSTRUCTIONS.get(difficulty, _NEGOTIATION_DIFFICULTY_INSTRUCTIONS["intermediate"])
        _coaching_tone_map = {
            "supportive": "Be warm, encouraging, and patient in your feedback. Celebrate small wins.",
            "direct": "Be clear and concise in feedback. State what needs improving without softening.",
            "socratic": "Use questions to guide the student to discover their own insights.",
            "challenging": "Push the student hard. High expectations, limited hand-holding.",
            "neutral": "Maintain a balanced, professional coaching tone.",
        }
        _coaching_instr = _coaching_tone_map.get(coaching_tone, _coaching_tone_map["supportive"])
        system_prompt = f"""You are {other_party.get('name', 'the other party')} in a negotiation simulation for Indian students aged 12-16 in Pune.
COACHING TONE: {_coaching_instr}

SCENARIO: {scenario_data.get('title', '')}
CONTEXT: {scenario_data.get('description', '')}
SETTING: {scenario_data.get('setting', '')}
CULTURAL CONTEXT: {scenario_data.get('cultural_context', '')}

YOUR CHARACTER:
- Objective: {other_party.get('objective', '')}
- BATNA: {other_party.get('batna', '')}
- Personality: {other_party.get('personality', '')}
- Cultural Notes: {other_party.get('cultural_notes', '')}

STUDENT'S OBJECTIVE: {scenario_data.get('your_objective', '')}
STUDENT'S BATNA: {scenario_data.get('your_batna', '')}

{_diff_instr}

SCORING ANCHORS (calibrate your impact scores consistently):
- relationship_impact +7 to +10: Student shows exceptional empathy, active listening, and cultural sensitivity
- relationship_impact +3 to +6: Student is polite and makes reasonable effort to understand
- relationship_impact -1 to +2: Neutral or slightly off-tone
- relationship_impact -5 to -1: Dismissive, aggressive, or culturally insensitive

CONFIDENCE: For each impact score, indicate your confidence (high/medium/low):
- high: certain within ±1 point
- medium: could reasonably be ±2 points
- low: genuinely uncertain, could be ±3 points

{neg_tier_instruction}

YOUR ROLE:
1. Respond authentically as this character would
2. React to student's approach (assertiveness, empathy, tactics)
3. Be reasonable but FIRMLY protect your interests — do NOT agree easily
4. Reward good negotiation tactics (listening, empathy, creative solutions)
5. Push back on aggressive or disrespectful approaches
6. Consider cultural context (respect for elders, face-saving, etc.)
7. ONLY move toward resolution gradually after extended back-and-forth
8. Keep responses natural and conversational (2-4 sentences)

CRITICAL RULES:
- ALWAYS respond IN CHARACTER as {other_party.get('name', 'the other party')}. Never break character.
- Your responses must reference the SPECIFIC details of this scenario (names, places, subjects, times).
- React to what the student ACTUALLY said — if they propose a time, respond about that time.
- Keep dialogue natural, like a real conversation between Indian students/people.
- DO NOT give generic responses like "I hear what you're saying" or "Let's discuss further."
- DO NOT agree to proposals too quickly. Always raise at least one concern or counter-offer before accepting anything.
- In early turns (1-3), you should be exploring the problem, sharing your constraints, and sometimes disagreeing.
- Only in later turns (4+) should you start showing willingness to compromise.
- NEVER set agreement_reached to true yourself — that decision is handled separately.

RESPONSE FORMAT (JSON):
{{
  "response": "Your in-character spoken response (2-4 sentences, specific to what was said)",
  "analysis": {{
    "tactics_used": ["list of tactics student used: active_listening, anchoring, empathy, etc."],
    "relationship_impact": {{"value": -10 to +10, "confidence": "high|medium|low"}},
    "assertiveness_impact": {{"value": -5 to +5, "confidence": "high|medium|low"}},
    "empathy_impact": {{"value": -5 to +5, "confidence": "high|medium|low"}},
    "feedback": "Coaching feedback for student"
  }},
  "negotiation_progress": 0-100 (how close to agreement),
  "agreement_reached": false (set true ONLY when both sides explicitly agree on specifics)
  {', "detailed_guidance": ["tip1", "tip2"]' if neg_tier == "struggling" else ""}
}}
"""
    
    # Build conversation context
    messages = [{"role": "system", "content": system_prompt}]
    
    # CONVERSATION HISTORY with SUMMARIZATION
    # If conversation history is too long (>8 messages), summarize older messages
    MAX_RECENT_MESSAGES = 8
    
    if len(conversation_history) > MAX_RECENT_MESSAGES:
        # Keep only recent messages, summarize the rest
        older_messages = conversation_history[:-MAX_RECENT_MESSAGES]
        recent_messages = conversation_history[-MAX_RECENT_MESSAGES:]
        
        # Create summary of older conversation
        summary_parts = []
        for msg in older_messages:
            speaker = "You" if msg.get("speaker") != "student" else "User"
            summary_parts.append(f"{speaker}: {msg.get('message', '')[:100]}")
        
        conversation_summary = "\n".join(summary_parts)
        
        # Add summary as a system message
        messages.append({
            "role": "system", 
            "content": f"PREVIOUS CONVERSATION SUMMARY:\n{conversation_summary}\n\nNow continuing with recent messages..."
        })
        
        # Add recent messages
        for msg in recent_messages:
            role = "user" if msg.get("speaker") == "student" else "assistant"
            messages.append({"role": role, "content": msg.get("message", "")})
    else:
        # Add all conversation history (not too long yet)
        for msg in conversation_history:
            role = "user" if msg.get("speaker") == "student" else "assistant"
            messages.append({"role": role, "content": msg.get("message", "")})
    
    # Add current message WITH dynamic context (kept out of system prompt for caching)
    _neg_phases = scenario_data.get('phases', ['Opening'])
    _neg_phase = _neg_phases[min(current_turn, len(_neg_phases) - 1)]
    _neg_max_turns = scenario_data.get('conversation_turns', 6)
    _dynamic_context = (
        f"[Turn {current_turn}/{_neg_max_turns} | Phase: {_neg_phase} | "
        f"Relationship: {state.get('relationship_score', 50)}/100]\n"
    )
    messages.append({"role": "user", "content": _dynamic_context + user_message})

    # Token budget varies by tier
    neg_max_tokens = {"struggling": 600, "strong": 350, "developing": 400}[neg_tier]

    # Scenario-aware fallback
    char_name = other_party.get("name", "the other person")
    fallback_responses = [
        f"Hmm, that's a good point. Let me think about this from my side — as {char_name}, I want to make sure we find something fair.",
        f"I appreciate you sharing that. So, from where I stand, we still need to figure out the details. What exactly are you proposing?",
        f"Okay, I understand what you're saying. But let me be honest — I have my own constraints too. Can we look at this together?",
        f"That's interesting. I wasn't expecting that. Tell me more about what you have in mind, and I'll see if it works for me.",
    ]
    import random as _rand

    start_t = time.time()
    try:
        resp = _client().chat.completions.create(
            model=MODEL,
            temperature=0.7,
            max_tokens=neg_max_tokens,
            messages=messages,
            response_format={"type": "json_object"}
        )

        raw_content = resp.choices[0].message.content.strip()
        elapsed = time.time() - start_t
        logger.info(f"[LLM] negotiation_ai_response | {elapsed:.1f}s | {len(raw_content)} chars")
        try:
            from cost_tracker import log_cost
            usage = getattr(resp, 'usage', None)
            log_cost("chat", MODEL, purpose="negotiation_ai_response", game_type="negotiation",
                     input_tokens=getattr(usage, 'prompt_tokens', 0) if usage else 0,
                     output_tokens=getattr(usage, 'completion_tokens', 0) if usage else 0,
                     duration_ms=int(elapsed * 1000))
        except Exception:
            pass

        result = _parse_json_safe(raw_content)
        if not result.get("response"):
            # _parse_json_safe returned {} or missing response — try direct extraction
            resp_match = re.search(r'"response"\s*:\s*"((?:[^"\\]|\\.)*)"', raw_content)
            if resp_match:
                result["response"] = resp_match.group(1)

        # GENERIC: Ensure basic required fields exist (works for any game type)
        if "response" not in result:
            result["response"] = "I understand. Tell me more."

        if "analysis" not in result:
            result["analysis"] = {}

        # Ensure analysis has feedback
        if "feedback" not in result.get("analysis", {}):
            result["analysis"]["feedback"] = "Keep the conversation going."

        # Normalize impact scores to include confidence (backward-compatible)
        analysis = result.get("analysis", {})
        for key in ["relationship_impact", "assertiveness_impact", "empathy_impact"]:
            v = analysis.get(key, 0)
            if isinstance(v, dict) and "value" in v:
                analysis[key] = {"value": v["value"], "confidence": v.get("confidence", "medium")}
            elif isinstance(v, (int, float)):
                analysis[key] = {"value": v, "confidence": "medium"}
        result["analysis"] = analysis

        # Handle progress fields generically (could be negotiation_progress, connection_level, etc.)
        if "negotiation_progress" not in result and "connection_level" not in result:
            # Default progress calculation
            max_turns = scenario_data.get("max_turns", scenario_data.get("conversation_turns", 10))
            result["connection_level"] = min(100, (current_turn / max_turns) * 100)

        # Add phase info if not already present
        if "phase" not in result:
            result["phase"] = scenario_data.get("phase", "conversation")

        # Item 24: Add tactic labels with dimension mapping for negotiation
        analysis = result.get("analysis", {})
        tactics = analysis.get("tactics_used", analysis.get("user_qualities", []))
        if tactics:
            tactic_labels = []
            for t in tactics:
                tactic_key = t.lower().replace(" ", "_") if isinstance(t, str) else ""
                info = TACTIC_DIMENSION_MAP.get(tactic_key)
                if info:
                    tactic_labels.append({
                        "tactic": tactic_key,
                        "label": info["label"],
                        "explanation": info["explanation"],
                        "dimension": info["dimension"],
                    })
                elif tactic_key:
                    tactic_labels.append({
                        "tactic": tactic_key,
                        "label": t if isinstance(t, str) else tactic_key.replace("_", " ").title(),
                        "explanation": "You used a communication technique.",
                        "dimension": "strategic_thinking",
                    })
            result["tactic_labels"] = tactic_labels

        # Detect AI tactic used in the response
        ai_tactic = _detect_ai_negotiation_tactic(result.get("response", ""))
        result["ai_tactic_used"] = ai_tactic["tactic_used"]
        result["ai_tactic_label"] = ai_tactic["tactic_label"]
        result["ai_tactic_tip"] = ai_tactic["tactic_tip"]

        # Validate response text before returning
        _response_text = result.get("response", "")
        _validation = validate_llm_output(_response_text, context="negotiation")
        if not _validation["valid"]:
            logger.warning("LLM output failed validation: %s", _validation["warnings"])
        result["response"] = _validation["cleaned"] if _validation["cleaned"] else _response_text
        return result

    except Exception as e:
        elapsed = time.time() - start_t
        logger.error(f"[LLM] negotiation_ai_response FAILED | {elapsed:.1f}s | {e}")
        fallback_resp = _rand.choice(fallback_responses)
        ai_tactic = _detect_ai_negotiation_tactic(fallback_resp)
        return {
            "response": fallback_resp,
            "analysis": {
                "user_qualities": [],
                "relationship_impact": {"value": 1, "confidence": "low"},
                "assertiveness_impact": {"value": 0, "confidence": "low"},
                "empathy_impact": {"value": 1, "confidence": "low"},
                "feedback": "Keep engaging with the other party."
            },
            "phase": scenario_data.get("phases", ["Opening"])[min(current_turn, len(scenario_data.get("phases", [])) - 1)],
            "negotiation_progress": (current_turn / scenario_data.get("conversation_turns", 6)) * 100,
            "ai_tactic_used": ai_tactic["tactic_used"],
            "ai_tactic_label": ai_tactic["tactic_label"],
            "ai_tactic_tip": ai_tactic["tactic_tip"],
        }


def evaluate_negotiation_outcome(
    scenario_data: Dict[str, Any],
    conversation_history: list,
    final_state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluate the overall negotiation outcome and provide detailed feedback.
    
    Returns:
        {
            "outcome_quality": "excellent" | "good" | "acceptable" | "poor",
            "outcome_message": "Detailed description of what happened",
            "scores": {
                "relationship": 85,
                "win_win": 70,
                "batna_usage": 60,
                "communication": 75,
                "overall": 72
            },
            "strengths": ["Active listening", "Creative solutions"],
            "growth_areas": ["Could be more assertive", "BATNA timing"],
            "key_moments": ["Turn 3: Great empathy shown", "Turn 5: Missed opportunity"]
        }
    """
    if not llm_enabled():
        return {
            "outcome_quality": "acceptable",
            "outcome_message": "You completed the negotiation. LLM evaluation not available.",
            "scores": {
                "relationship": final_state.get("relationship_score", 50),
                "win_win": 50,
                "batna_usage": 50,
                "communication": 50,
                "overall": 50
            },
            "strengths": ["Participation", "Engagement"],
            "growth_areas": ["Continue practicing"],
            "key_moments": []
        }
    
    # Build evaluation prompt
    system_prompt = f"""You are an expert negotiation coach evaluating a student's performance in a negotiation simulation.

SCENARIO: {scenario_data.get('title', '')}
DIFFICULTY: {scenario_data.get('difficulty', 'intermediate')}
CULTURAL CONTEXT: {scenario_data.get('cultural_context', '')}

SCORING CRITERIA:
{json.dumps(scenario_data.get('scoring_criteria', {}), indent=2)}

SCORING ANCHORS (calibrate scores consistently):
- Score 20-30: Poor performance — aggressive, dismissive, no listening
- Score 50-60: Average — some effort but lacks depth or cultural sensitivity
- Score 80-90: Excellent — strong empathy, creative solutions, culturally aware

FINAL STATE:
{json.dumps(final_state, indent=2)}

CONVERSATION HISTORY:
{json.dumps(conversation_history, indent=2)}

Evaluate the student's negotiation performance. For each score, indicate your confidence.

RETURN JSON:
{{
  "outcome_quality": "excellent" | "good" | "acceptable" | "poor",
  "outcome_message": "2-3 sentences describing what happened and the result",
  "scores": {{
    "relationship": {{"score": 0-100, "confidence": "high|medium|low"}},
    "win_win": {{"score": 0-100, "confidence": "high|medium|low"}},
    "batna_usage": {{"score": 0-100, "confidence": "high|medium|low"}},
    "communication": {{"score": 0-100, "confidence": "high|medium|low"}},
    "overall": {{"score": 0-100, "confidence": "high|medium|low"}}
  }},
  "strengths": ["2-3 specific strengths demonstrated"],
  "growth_areas": ["2-3 specific areas for improvement"],
  "key_moments": ["2-3 notable moments with turn numbers"]
}}

Consider:
- Did they maintain relationship while pursuing goals?
- Were they assertive without being aggressive?
- Did they show empathy and active listening?
- Were they culturally appropriate?
- Did they use BATNA strategically?
- Did they propose creative win-win solutions?
"""

    fallback = {
        "outcome_quality": "acceptable",
        "outcome_message": "You completed the negotiation and gained valuable experience.",
        "scores": {
            "relationship": final_state.get("relationship_score", 50),
            "win_win": 50,
            "batna_usage": 50,
            "communication": 50,
            "overall": 50
        },
        "strengths": ["Engagement", "Completion"],
        "growth_areas": ["Continue practicing negotiation skills"],
        "key_moments": []
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt="Please evaluate this negotiation performance.",
        temperature=0.6,
        max_tokens=600,
        purpose="evaluate_negotiation",
        fallback=fallback,
    )

    # Normalize scores to include confidence (backward-compatible)
    if "scores" in result:
        normalized_scores = {}
        for k, v in result["scores"].items():
            if isinstance(v, dict) and "score" in v:
                normalized_scores[k] = {"score": v["score"], "confidence": v.get("confidence", "medium")}
            elif isinstance(v, (int, float)):
                normalized_scores[k] = {"score": v, "confidence": "medium"}
            else:
                normalized_scores[k] = {"score": 50, "confidence": "low"}
        result["scores"] = normalized_scores
    return result


def debate_ai_response(
    student_argument: str,
    scenario_data: Dict[str, Any],
    conversation_history: list,
    current_round: int,
    total_rounds: int,
    scores_history: list = None,
    difficulty: str = "intermediate",
    coaching_tone: str = "supportive"
) -> Dict[str, Any]:
    """
    Generate AI response for debate game — counter-argument + calibrated scoring.

    Returns:
        {
            "response": "AI's counter-argument",
            "round_scores": {"logic": {"score": 7, "confidence": "high"}, ...},
            "feedback": "Brief coaching feedback for this round",
            "detailed_guidance": ["tip1", "tip2"]  # only for struggling students
        }
    """
    if not llm_enabled():
        fallback_text = "That's an interesting point, but consider this: there are many factors you haven't addressed. The evidence suggests a more nuanced picture than you're presenting."
        ai_debate_tactic = _detect_ai_debate_tactic(fallback_text)
        return {
            "response": fallback_text,
            "round_scores": {"logic": 5, "evidence": 5, "rhetoric": 5, "rebuttal": 5},
            "feedback": "LLM not enabled — using fallback response.",
            "ai_tactic_used": ai_debate_tactic["ai_tactic_used"],
            "ai_tactic_label": ai_debate_tactic["ai_tactic_label"],
            "ai_tactic_tip": ai_debate_tactic["ai_tactic_tip"],
        }

    # Sanitize user input
    student_argument = _sanitize_user_input(student_argument, max_length=1000)

    tier = _compute_performance_tier(scores_history or [])

    ai_persona = scenario_data.get("ai_persona", {})
    rubric = scenario_data.get("scoring_rubric", {})
    rubric_desc = "\n".join(
        f"- {k}: weight {v.get('weight', 0.25)}, {v.get('description', '')}"
        for k, v in rubric.items()
    )

    # Adaptive feedback instructions based on performance tier
    if tier == "struggling":
        tier_instruction = """STUDENT SUPPORT MODE: The student is struggling. Provide detailed, step-by-step guidance:
(1) what was weak in their argument, (2) a specific example of how to improve it, (3) a simpler way to think about the topic.
Be encouraging. Also return a "detailed_guidance" field with 2-3 actionable tips as a JSON array of strings."""
    elif tier == "strong":
        tier_instruction = """CHALLENGE MODE: The student is performing well. Challenge them with a stronger counter-argument.
Keep feedback brief — one specific advanced technique to try. Do NOT return detailed_guidance."""
    else:
        tier_instruction = """STANDARD MODE: Give balanced feedback with one clear suggestion for improvement. Do NOT return detailed_guidance."""

    # Token budget varies by tier
    max_tokens = {"struggling": 700, "strong": 400, "developing": 500}[tier]

    _debate_diff_instr = _DEBATE_DIFFICULTY_INSTRUCTIONS.get(difficulty, _DEBATE_DIFFICULTY_INSTRUCTIONS["intermediate"])
    _coaching_tone_map_d = {
        "supportive": "Be warm, encouraging, and patient in your feedback. Celebrate small wins.",
        "direct": "Be clear and concise in feedback. State what needs improving without softening.",
        "socratic": "Use questions to guide the student to discover their own insights.",
        "challenging": "Push the student hard. High expectations, limited hand-holding.",
        "neutral": "Maintain a balanced, professional coaching tone.",
    }
    _coaching_instr_d = _coaching_tone_map_d.get(coaching_tone, _coaching_tone_map_d["supportive"])
    system_prompt = f"""You are {ai_persona.get('name', 'the AI debater')} in a structured debate with an Indian student aged 12-16.
COACHING TONE: {_coaching_instr_d}

YOUR PERSONA:
- Personality: {ai_persona.get('personality', 'articulate and thoughtful')}
- Debate style: {ai_persona.get('style', 'Uses evidence and logical reasoning.')}

DEBATE TOPIC: {scenario_data.get('title', '')}
DESCRIPTION: {scenario_data.get('description', '')}
YOUR POSITION: {scenario_data.get('ai_position', 'for')}
STUDENT'S POSITION: {scenario_data.get('student_position', 'against')}

{_debate_diff_instr}

SCORING RUBRIC (evaluate the STUDENT's argument on these axes, score 1-10):
{rubric_desc}

SCORING ANCHORS (use these to calibrate your scores consistently):
- Score 2-3: Vague claims with no reasoning. Example: "AI is bad because I don't like it."
- Score 5-6: Has a point but lacks depth or evidence. Example: "AI can't understand emotions, so it can't replace teachers who connect with students."
- Score 8-9: Strong reasoning with specific evidence and nuance. Example: "While AI excels at personalized pacing — Khan Academy's AI tutor improved test scores by 15% — it lacks the emotional intelligence to recognize when a student is struggling with issues beyond academics."

CONFIDENCE: For each score, indicate your confidence (high/medium/low):
- high: certain within ±1 point
- medium: could reasonably be ±2 points
- low: genuinely uncertain, could be ±3 points

{tier_instruction}

YOUR TASKS:
1. Present a strong counter-argument (2-4 sentences) that directly addresses the student's points
2. Score the student's argument on each rubric axis (1-10) with confidence
3. Provide coaching feedback

Stay in character as {ai_persona.get('name', 'the AI')}. Be challenging but fair.
If the student makes a weak argument, push back firmly but constructively.
If the student makes a strong argument, acknowledge the good points before countering.
Keep arguments appropriate for Indian students aged 12-16.

RETURN JSON:
{{
  "response": "Your counter-argument as {ai_persona.get('name', 'the AI')}",
  "round_scores": {{
    "logic": {{"score": 1-10, "confidence": "high|medium|low"}},
    "evidence": {{"score": 1-10, "confidence": "high|medium|low"}},
    "rhetoric": {{"score": 1-10, "confidence": "high|medium|low"}},
    "rebuttal": {{"score": 1-10, "confidence": "high|medium|low"}}
  }},
  "feedback": "Coaching feedback for the student"
  {', "detailed_guidance": ["tip1", "tip2", "tip3"]' if tier == "struggling" else ""}
}}"""

    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history (summarize if long)
    MAX_RECENT = 6
    if len(conversation_history) > MAX_RECENT:
        older = conversation_history[:-MAX_RECENT]
        recent = conversation_history[-MAX_RECENT:]
        summary = "\n".join(
            f"{'Student' if m.get('speaker') == 'student' else 'AI'}: {m.get('message', '')[:120]}"
            for m in older
        )
        messages.append({"role": "system", "content": f"EARLIER DEBATE SUMMARY:\n{summary}"})
        for m in recent:
            role = "user" if m.get("speaker") == "student" else "assistant"
            messages.append({"role": role, "content": m.get("message", "")})
    else:
        for m in conversation_history:
            role = "user" if m.get("speaker") == "student" else "assistant"
            messages.append({"role": role, "content": m.get("message", "")})

    # Add student argument WITH dynamic context (kept out of system prompt for caching)
    _debate_round_label = (
        "the opening round" if current_round == 1
        else "the final round — make a strong closing argument" if current_round == total_rounds
        else f"round {current_round}"
    )
    _debate_context = f"[Round {current_round}/{total_rounds} — {_debate_round_label}]\n"
    messages.append({"role": "user", "content": _debate_context + student_argument})

    start_t = time.time()
    try:
        resp = _client().chat.completions.create(
            model=MODEL,
            temperature=0.7,
            max_tokens=max_tokens,
            messages=messages,
            response_format={"type": "json_object"}
        )
        raw = resp.choices[0].message.content.strip()
        elapsed = time.time() - start_t
        logger.info(f"[LLM] debate_ai_response | {elapsed:.1f}s | {len(raw)} chars")
        try:
            from cost_tracker import log_cost
            usage = getattr(resp, 'usage', None)
            log_cost("chat", MODEL, purpose="debate_ai_response", game_type="debate",
                     input_tokens=getattr(usage, 'prompt_tokens', 0) if usage else 0,
                     output_tokens=getattr(usage, 'completion_tokens', 0) if usage else 0,
                     duration_ms=int(elapsed * 1000))
        except Exception:
            pass

        result = _parse_json_safe(raw)

        if "response" not in result:
            result["response"] = "That's a thought-provoking point. Let me offer a different perspective."
        if "round_scores" not in result:
            result["round_scores"] = {"logic": 5, "evidence": 5, "rhetoric": 5, "rebuttal": 5}
        if "feedback" not in result:
            result["feedback"] = "Keep developing your arguments with more evidence."

        # Normalize round_scores to include confidence
        result["round_scores"] = _normalize_round_scores(result["round_scores"])

        # Item 24: Infer tactic label from round scores
        result["tactic_label"] = _infer_debate_tactic(result["round_scores"], student_argument)

        # Item 25: Coaching tip for weakest dimension
        result["coaching_tip"] = _get_debate_coaching_tip(result["round_scores"])

        # Item 26: Include AI difficulty tier so frontend can show indicator
        result["ai_difficulty"] = tier

        # Detect AI tactic used in the counter-argument
        ai_debate_tactic = _detect_ai_debate_tactic(result.get("response", ""))
        result["ai_tactic_used"] = ai_debate_tactic["ai_tactic_used"]
        result["ai_tactic_label"] = ai_debate_tactic["ai_tactic_label"]
        result["ai_tactic_tip"] = ai_debate_tactic["ai_tactic_tip"]

        # Validate response text before returning
        _response_text = result.get("response", "")
        _validation = validate_llm_output(_response_text, context="debate")
        if not _validation["valid"]:
            logger.warning("LLM output failed validation: %s", _validation["warnings"])
        result["response"] = _validation["cleaned"] if _validation["cleaned"] else _response_text
        return result

    except Exception as e:
        elapsed = time.time() - start_t
        logger.error(f"[LLM] debate_ai_response FAILED | {elapsed:.1f}s | {e}")
        fallback_text = "You raise some interesting points. However, I'd argue that the evidence points in a different direction. Consider the broader implications of your position."
        ai_debate_tactic = _detect_ai_debate_tactic(fallback_text)
        return {
            "response": fallback_text,
            "round_scores": {"logic": 5, "evidence": 5, "rhetoric": 5, "rebuttal": 5},
            "feedback": "Continue building your argument with specific examples.",
            "ai_difficulty": "developing",
            "ai_tactic_used": ai_debate_tactic["ai_tactic_used"],
            "ai_tactic_label": ai_debate_tactic["ai_tactic_label"],
            "ai_tactic_tip": ai_debate_tactic["ai_tactic_tip"],
        }


def analyze_transcript(
    conversation_history: list,
    scores_by_round: list,
    game_type: str = "debate"
) -> Dict[str, Any]:
    """
    Item 27: Post-game transcript analysis highlighting turning points.

    Returns:
        {
            "annotations": [{"round": 2, "type": "turning_point", "text": "...", "badge": "Strongest Argument"}],
            "strongest_round": 3,
            "weakest_round": 1,
            "summary": "Brief analysis of the conversation arc."
        }
    """
    if not conversation_history or not scores_by_round:
        return None

    annotations = []
    round_avgs = []

    for i, rs in enumerate(scores_by_round):
        if not isinstance(rs, dict):
            round_avgs.append(5)
            continue
        vals = []
        for v in rs.values():
            if isinstance(v, dict):
                vals.append(v.get("score", 5))
            elif isinstance(v, (int, float)):
                vals.append(v)
        avg = sum(vals) / max(1, len(vals))
        round_avgs.append(avg)

    if not round_avgs:
        return None

    strongest_round = round_avgs.index(max(round_avgs)) + 1
    weakest_round = round_avgs.index(min(round_avgs)) + 1

    # Detect turning points: significant score jumps between rounds
    for i in range(1, len(round_avgs)):
        delta = round_avgs[i] - round_avgs[i - 1]
        if delta > 2:
            annotations.append({
                "round": i + 1,
                "type": "improvement",
                "badge": "Big Improvement",
                "text": f"Your argument quality jumped significantly in round {i + 1}!",
            })
        elif delta < -2:
            annotations.append({
                "round": i + 1,
                "type": "decline",
                "badge": "Lost Ground",
                "text": f"Your argument weakened in round {i + 1}. Consider reviewing your approach.",
            })

    # Mark strongest and weakest rounds
    annotations.append({
        "round": strongest_round,
        "type": "strongest",
        "badge": "Strongest Argument",
        "text": f"Round {strongest_round} was your best performance (avg {round_avgs[strongest_round - 1]:.1f}/10).",
    })
    if weakest_round != strongest_round:
        annotations.append({
            "round": weakest_round,
            "type": "weakest",
            "badge": "Room to Grow",
            "text": f"Round {weakest_round} was your weakest (avg {round_avgs[weakest_round - 1]:.1f}/10).",
        })

    # Overall arc description
    if len(round_avgs) >= 2:
        if round_avgs[-1] > round_avgs[0] + 1:
            arc = "You showed strong improvement over the course of the session — great growth!"
        elif round_avgs[-1] < round_avgs[0] - 1:
            arc = "You started strong but lost momentum. Try maintaining your energy and preparation throughout."
        else:
            arc = "You maintained a consistent performance throughout the session."
    else:
        arc = "One round analyzed."

    return {
        "annotations": sorted(annotations, key=lambda a: a["round"]),
        "strongest_round": strongest_round,
        "weakest_round": weakest_round,
        "round_averages": [round(a, 1) for a in round_avgs],
        "summary": arc,
    }


def evaluate_debate_outcome(
    scenario_data: Dict[str, Any],
    conversation_history: list,
    all_round_scores: list
) -> Dict[str, Any]:
    """
    Evaluate the overall debate performance.

    Returns:
        {
            "overall_quality": "excellent"|"good"|"acceptable"|"needs_work",
            "summary": "2-3 sentence evaluation",
            "final_scores": {"logic": 8, "evidence": 7, ...},
            "overall_score": 75,
            "strengths": ["...", "..."],
            "growth_areas": ["...", "..."],
            "xp_earned": 120
        }
    """
    if not llm_enabled():
        avg_scores = {}
        for axis in ["logic", "evidence", "rhetoric", "rebuttal"]:
            vals = []
            for rs in all_round_scores:
                if not isinstance(rs, dict):
                    continue
                v = rs.get(axis, 5)
                vals.append(v.get("score", 5) if isinstance(v, dict) else v)
            avg_scores[axis] = round(sum(vals) / max(len(vals), 1))
        overall = round(sum(avg_scores.values()) / max(len(avg_scores), 1) * 10)
        return {
            "overall_quality": "good" if overall >= 60 else "acceptable",
            "summary": "You completed the debate and made some good points. LLM evaluation not available.",
            "final_scores": avg_scores,
            "overall_score": overall,
            "strengths": ["Participation", "Engagement"],
            "growth_areas": ["Continue practicing debate skills"],
            "xp_earned": max(50, overall)
        }

    rubric = scenario_data.get("scoring_rubric", {})
    system_prompt = f"""You are an expert debate coach evaluating a student's debate performance.

DEBATE TOPIC: {scenario_data.get('title', '')}
STUDENT'S POSITION: {scenario_data.get('student_position', '')}
AI'S POSITION: {scenario_data.get('ai_position', '')}
DIFFICULTY: {scenario_data.get('difficulty', 'intermediate')}

SCORING RUBRIC:
{json.dumps(rubric, indent=2)}

SCORING ANCHORS (calibrate final scores consistently):
- Score 2-3: Weak arguments throughout, mostly unsupported opinions
- Score 5-6: Decent reasoning but inconsistent quality, some evidence used
- Score 8-9: Strong, well-structured arguments with specific evidence and nuance throughout

PER-ROUND SCORES:
{json.dumps(all_round_scores, indent=2)}

CONVERSATION:
{json.dumps(conversation_history, indent=2)}

Evaluate the student's overall debate performance. For each final score, indicate your confidence.

RETURN JSON:
{{
  "overall_quality": "excellent" or "good" or "acceptable" or "needs_work",
  "summary": "2-3 sentences summarizing the student's debate performance",
  "final_scores": {{
    "logic": {{"score": 1-10, "confidence": "high|medium|low"}},
    "evidence": {{"score": 1-10, "confidence": "high|medium|low"}},
    "rhetoric": {{"score": 1-10, "confidence": "high|medium|low"}},
    "rebuttal": {{"score": 1-10, "confidence": "high|medium|low"}}
  }},
  "overall_score": 0-100,
  "strengths": ["2-3 specific strengths"],
  "growth_areas": ["2-3 areas for improvement"],
  "xp_earned": 50-200 (based on performance)
}}"""

    # Build score-aware fallback
    fb_avg_scores = {}
    for axis in ["logic", "evidence", "rhetoric", "rebuttal"]:
        vals = []
        for rs in all_round_scores:
            if not isinstance(rs, dict):
                continue
            v = rs.get(axis, 5)
            vals.append(v.get("score", 5) if isinstance(v, dict) else v)
        fb_avg_scores[axis] = round(sum(vals) / max(len(vals), 1))
    fb_overall = round(sum(fb_avg_scores.values()) / max(len(fb_avg_scores), 1) * 10)
    fallback = {
        "overall_quality": "good" if fb_overall >= 60 else "acceptable",
        "summary": "You completed the debate. Good effort!",
        "final_scores": fb_avg_scores,
        "overall_score": fb_overall,
        "strengths": ["Completion", "Engagement"],
        "growth_areas": ["Continue practicing"],
        "xp_earned": max(50, fb_overall)
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt="Evaluate this debate performance.",
        temperature=0.5,
        max_tokens=500,
        purpose="evaluate_debate",
        fallback=fallback,
    )

    # Normalize final_scores to include confidence
    if "final_scores" in result:
        result["final_scores"] = _normalize_round_scores(result["final_scores"])

    # Item 27: Include transcript analysis
    transcript_analysis = analyze_transcript(conversation_history, all_round_scores, "debate")
    if transcript_analysis:
        result["transcript_analysis"] = transcript_analysis

    return result


def generate_pitch_context(
    idea_description: str,
    investor_pool: list
) -> Dict[str, Any]:
    """
    For 'Pitch Your Own' mode: generate a pitch scenario context from a free-text idea.

    Returns:
        {
            "pitch_title": "...",
            "industry": "...",
            "key_context": "...",
            "recommended_investor_ids": ["id1", "id2", "id3"],
            "potential_objections": ["...", "..."],
            "setting": "..."
        }
    """
    import random
    fallback_ids = [inv["id"] for inv in random.sample(investor_pool, min(3, len(investor_pool)))]
    fallback = {
        "pitch_title": idea_description[:60],
        "industry": "General",
        "key_context": idea_description,
        "recommended_investor_ids": fallback_ids,
        "potential_objections": ["Market size unclear", "Revenue model needs work", "Competition exists"],
        "setting": "A modern coworking space. Three investors sit across the table, ready to hear your pitch."
    }

    if not llm_enabled():
        return fallback

    idea_description = _sanitize_user_input(idea_description, max_length=500)

    pool_summary = json.dumps([{"id": inv["id"], "archetype": inv["archetype"], "focus": inv["focus"]} for inv in investor_pool])

    system_prompt = f"""You are a startup pitch coach helping set up an investor pitch simulation for an Indian student.

The student wants to pitch this idea:
"{idea_description}"

AVAILABLE INVESTOR ARCHETYPES (pick exactly 3 that are most relevant to test this pitch):
{pool_summary}

Generate a pitch context. Return JSON:
{{
  "pitch_title": "A catchy 5-7 word title for the pitch",
  "industry": "Industry category (e.g., EdTech, HealthTech, FinTech, SocialImpact, etc.)",
  "key_context": "2-3 sentences expanding on the idea with realistic Indian market context",
  "recommended_investor_ids": ["id1", "id2", "id3"],
  "potential_objections": ["3 tough objections investors might raise"],
  "setting": "1-2 sentences describing the pitch setting (keep it in India)"
}}

Pick investors whose focus areas will meaningfully test this specific idea."""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"Generate pitch context for: {idea_description}",
        temperature=0.8,
        max_tokens=800,
        purpose="generate_pitch_context",
        fallback=fallback,
    )

    # Validate recommended_investor_ids exist in pool
    valid_ids = {inv["id"] for inv in investor_pool}
    if "recommended_investor_ids" in result:
        result["recommended_investor_ids"] = [
            rid for rid in result["recommended_investor_ids"] if rid in valid_ids
        ]
        # Pad with random if fewer than 3
        while len(result["recommended_investor_ids"]) < 3:
            remaining = list(valid_ids - set(result["recommended_investor_ids"]))
            if not remaining:
                break
            result["recommended_investor_ids"].append(random.choice(remaining))

    return result


def pitch_panel_response(
    user_message: str,
    scenario_data: Dict[str, Any],
    conversation_history: list,
    current_turn: int,
    state: Dict[str, Any],
    active_investors: list,
    scores_history: list = None
) -> Dict[str, Any]:
    """
    Generate AI investor panel response for a pitch game.

    Args:
        user_message: What the student said/pitched
        scenario_data: Full scenario context
        conversation_history: Previous exchanges
        current_turn: Current turn number
        state: Current game state (pitch_score, panel_confidence, etc.)
        active_investors: List of 3 active investor dicts from the pool
        scores_history: Previous analysis dicts for adaptive tier

    Returns:
        {
            "response": "Investor's question or reaction",
            "speaker_investor_id": "the_numbers_shark",
            "speaker_name": "Kavita Sharma",
            "analysis": {
                "pitch_qualities_shown": ["clarity", "confidence"],
                "relationship_impact": {"value": 5, "confidence": "high"},
                "assertiveness_impact": {"value": 3, "confidence": "medium"},
                "empathy_impact": {"value": 2, "confidence": "high"},
                "feedback": "Coaching feedback"
            },
            "phase": "Deep Dive Q&A",
            "pitch_progress": 40,
            "investor_sentiments": { ... }
        }
    """
    max_turns = scenario_data.get("conversation_turns", 10)
    phases = scenario_data.get("pitch_phases", ["Elevator Pitch", "Deep Dive Q&A", "Objection Round", "The Ask"])

    # Determine current phase from turn number
    if current_turn <= 1:
        current_phase = phases[0] if len(phases) > 0 else "Elevator Pitch"
    elif current_turn <= max(max_turns - 3, 4):
        current_phase = phases[1] if len(phases) > 1 else "Deep Dive Q&A"
    elif current_turn <= max_turns - 1:
        current_phase = phases[2] if len(phases) > 2 else "Objection Round"
    else:
        current_phase = phases[3] if len(phases) > 3 else "The Ask"

    # Select which investor speaks this turn
    primary_idx = current_turn % len(active_investors)
    primary_investor = active_investors[primary_idx]

    if not llm_enabled():
        return {
            "response": f"{primary_investor['name']}: That's interesting. Tell me more about your approach.",
            "speaker_investor_id": primary_investor["id"],
            "speaker_name": primary_investor["name"],
            "analysis": {
                "pitch_qualities_shown": [],
                "relationship_impact": 0,
                "assertiveness_impact": 0,
                "empathy_impact": 0,
                "feedback": "LLM not enabled — using fallback response."
            },
            "phase": current_phase,
            "pitch_progress": (current_turn / max_turns) * 100,
            "investor_sentiments": {inv["id"]: {"sentiment": "neutral", "leaning": "undecided"} for inv in active_investors}
        }

    user_message = _sanitize_user_input(user_message, max_length=1000)

    # Compute adaptive tier
    pitch_tier = "developing"
    if scores_history:
        impact_scores = []
        for a in scores_history:
            if not isinstance(a, dict):
                continue
            for key in ["relationship_impact", "assertiveness_impact", "empathy_impact"]:
                v = a.get(key, 0)
                if isinstance(v, dict):
                    impact_scores.append(v.get("value", 0))
                elif isinstance(v, (int, float)):
                    impact_scores.append(v)
        if impact_scores:
            avg_impact = sum(impact_scores) / len(impact_scores)
            if avg_impact < -1:
                pitch_tier = "struggling"
            elif avg_impact > 3:
                pitch_tier = "strong"

    # Build investor panel description
    investors_desc = ""
    for i, inv in enumerate(active_investors):
        investors_desc += f"\n{i+1}. {inv['name']} ({inv['archetype']}): {inv['personality']} Focus: {inv['focus']}. Tough question style: \"{inv['tough_question_style']}\""

    tier_instruction = ""
    if pitch_tier == "struggling":
        tier_instruction = """The pitcher is struggling. Ask simpler questions. Give encouraging micro-feedback within your response. Keep your question focused on one thing."""
    elif pitch_tier == "strong":
        tier_instruction = """The pitcher is strong. Push harder. Ask follow-up questions that dig deeper. Challenge assumptions more aggressively."""

    scoring_rubric = scenario_data.get("scoring_rubric", {})
    predefined_metrics = scenario_data.get("predefined_metrics", {})

    system_prompt = f"""You are an AI investor panel in a pitch simulation for Indian students learning entrepreneurship.

THE PANEL ({len(active_investors)} investors):
{investors_desc}

PITCH SCENARIO: {scenario_data.get('title', '')}
PITCH TOPIC: {scenario_data.get('pitch_topic', scenario_data.get('description', ''))}
SETTING: {scenario_data.get('setting', '')}
INDUSTRY: {scenario_data.get('industry', '')}
PREDEFINED METRICS: {json.dumps(predefined_metrics)}

CURRENT STATE:
- Turn: {current_turn}/{max_turns}
- Phase: {current_phase}
- Pitch Score: {state.get('pitch_score', 0)}
- Panel Confidence: {state.get('panel_confidence', 50)}/100

THIS TURN'S PRIMARY SPEAKER: {primary_investor['name']} ({primary_investor['archetype']})

SCORING RUBRIC:
{json.dumps(scoring_rubric, indent=2)}

PHASE INSTRUCTIONS:
- Elevator Pitch (turns 0-1): Listen to the pitch. The primary investor reacts first. Brief, encouraging but with one probing follow-up.
- Deep Dive Q&A (mid turns): Rotate investors. Each asks questions from their specialty. Be specific and tough but fair.
- Objection Round (late turns): Raise serious concerns. Test how the pitcher handles pressure.
- The Ask (final turn): React to the funding ask. Express initial leaning.

{tier_instruction}

SCORING IMPACT ANCHORS (for the analysis):
- +7 to +10: Exceptional pitch quality — clear data, compelling vision, handles question brilliantly
- +3 to +6: Good response — shows preparation, mostly addresses the question
- -1 to +2: Average — generic answer, doesn't fully address the question
- -5 to -1: Weak — evasive, unprepared, no data to back claims

RESPONSE FORMAT (JSON):
{{
  "response": "{primary_investor['name']}: [2-4 sentences as this investor, in character. Ask a question or react to the pitch.]",
  "speaker_investor_id": "{primary_investor['id']}",
  "speaker_name": "{primary_investor['name']}",
  "analysis": {{
    "pitch_qualities_shown": ["list of qualities: clarity, confidence, data_driven, market_insight, storytelling, objection_handling, financial_knowledge, passion"],
    "relationship_impact": {{"value": -10 to +10, "confidence": "high|medium|low"}},
    "assertiveness_impact": {{"value": -10 to +10, "confidence": "high|medium|low"}},
    "empathy_impact": {{"value": -10 to +10, "confidence": "high|medium|low"}},
    "feedback": "1 sentence coaching feedback for the student (not shown to them during pitch)"
  }},
  "pitch_progress": {round((current_turn / max_turns) * 100)},
  "investor_sentiments": {{
    "{active_investors[0]['id']}": {{"sentiment": "excited|interested|neutral|skeptical|concerned", "leaning": "invest|negotiate|undecided|pass"}},
    "{active_investors[1]['id']}": {{"sentiment": "...", "leaning": "..."}},
    "{active_investors[2]['id']}": {{"sentiment": "...", "leaning": "..."}}
  }}
}}

CRITICAL RULES:
- Stay in character as {primary_investor['name']} ({primary_investor['archetype']})
- Ask ONE focused question per turn (don't overload)
- Reference specific things the pitcher said — show you're listening
- Keep cultural context Indian — use Indian market references, ₹ amounts
- Do NOT agree to invest during the pitch — save that for the verdict"""

    # Build conversation for LLM
    conv_messages = []
    recent_history = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
    for msg in recent_history:
        role = "user" if msg.get("speaker") in ("student", "user") else "assistant"
        conv_messages.append({"role": role, "content": msg.get("message", "")})

    max_tokens = 500 if pitch_tier == "struggling" else 400

    fallback_responses = [
        f"{primary_investor['name']}: That's an interesting approach. Can you walk me through the numbers behind this?",
        f"{primary_investor['name']}: I see the vision. But help me understand — who is your ideal customer and how do you reach them?",
        f"{primary_investor['name']}: Good point. Now tell me, what keeps you up at night about this business?",
        f"{primary_investor['name']}: Fair enough. What happens if a well-funded competitor enters this space tomorrow?",
    ]
    import random
    fallback = {
        "response": fallback_responses[current_turn % len(fallback_responses)],
        "speaker_investor_id": primary_investor["id"],
        "speaker_name": primary_investor["name"],
        "analysis": {
            "pitch_qualities_shown": [],
            "relationship_impact": 0,
            "assertiveness_impact": 0,
            "empathy_impact": 0,
            "feedback": "Continue practicing your pitch."
        },
        "pitch_progress": round((current_turn / max_turns) * 100),
        "investor_sentiments": {inv["id"]: {"sentiment": "neutral", "leaning": "undecided"} for inv in active_investors}
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_message,
        conversation_history=conv_messages,
        temperature=0.7,
        max_tokens=max_tokens,
        purpose="pitch_panel_response",
        fallback=fallback,
    )

    # Post-process: validate speaker_investor_id
    valid_ids = {inv["id"] for inv in active_investors}
    if result.get("speaker_investor_id") not in valid_ids:
        result["speaker_investor_id"] = primary_investor["id"]
        result["speaker_name"] = primary_investor["name"]

    # Ensure phase is set
    result["phase"] = current_phase
    result.setdefault("pitch_progress", round((current_turn / max_turns) * 100))

    return result


def evaluate_pitch_outcome(
    scenario_data: Dict[str, Any],
    conversation_history: list,
    final_state: Dict[str, Any],
    active_investors: list
) -> Dict[str, Any]:
    """
    Evaluate the overall pitch performance with individual investor verdicts.

    Returns:
        {
            "outcome_quality": "excellent"|"good"|"acceptable"|"poor",
            "outcome_message": "...",
            "scores": { 6 rubric dimensions + overall },
            "investor_verdicts": [ { investor_id, name, verdict, reason } ],
            "deal_outcome": "2 invest, 1 negotiate",
            "funding_secured": true/false,
            "strengths": [...],
            "growth_areas": [...],
            "key_moments": [...]
        }
    """
    if not llm_enabled():
        return {
            "outcome_quality": "acceptable",
            "outcome_message": "You completed the pitch. LLM evaluation not available.",
            "scores": {
                "clarity_structure": {"score": 50, "confidence": "low"},
                "market_understanding": {"score": 50, "confidence": "low"},
                "financial_viability": {"score": 50, "confidence": "low"},
                "confidence_delivery": {"score": 50, "confidence": "low"},
                "objection_handling": {"score": 50, "confidence": "low"},
                "investability": {"score": 50, "confidence": "low"},
                "overall": {"score": 50, "confidence": "low"}
            },
            "investor_verdicts": [
                {"investor_id": inv["id"], "name": inv["name"], "verdict": "undecided", "reason": "Evaluation not available."}
                for inv in active_investors
            ],
            "deal_outcome": "Evaluation pending",
            "funding_secured": False,
            "strengths": ["Participation", "Completion"],
            "growth_areas": ["Continue practicing pitch skills"],
            "key_moments": []
        }

    investors_desc = "\n".join([
        f"- {inv['name']} ({inv['archetype']}): Focus on {inv['focus']}"
        for inv in active_investors
    ])
    scoring_rubric = scenario_data.get("scoring_rubric", {})

    system_prompt = f"""You are an expert pitch coach evaluating a student's investor pitch performance.

PITCH SCENARIO: {scenario_data.get('title', '')}
INDUSTRY: {scenario_data.get('industry', '')}
DIFFICULTY: {scenario_data.get('difficulty', 'intermediate')}

INVESTOR PANEL:
{investors_desc}

SCORING RUBRIC:
{json.dumps(scoring_rubric, indent=2)}

SCORING ANCHORS (calibrate scores consistently):
- Score 20-30: Poor — vague pitch, no data, crumbles under pressure
- Score 50-60: Average — has an idea but lacks depth, some data, handles basic questions
- Score 80-90: Excellent — compelling vision, strong data, handles objections gracefully

FINAL STATE:
{json.dumps(final_state, indent=2)}

CONVERSATION:
{json.dumps(conversation_history, indent=2)}

Evaluate the student's pitch. Each investor must give an independent verdict.

RETURN JSON:
{{
  "outcome_quality": "excellent" or "good" or "acceptable" or "poor",
  "outcome_message": "2-3 sentences describing what happened and the panel's reaction",
  "scores": {{
    "clarity_structure": {{"score": 0-100, "confidence": "high|medium|low"}},
    "market_understanding": {{"score": 0-100, "confidence": "high|medium|low"}},
    "financial_viability": {{"score": 0-100, "confidence": "high|medium|low"}},
    "confidence_delivery": {{"score": 0-100, "confidence": "high|medium|low"}},
    "objection_handling": {{"score": 0-100, "confidence": "high|medium|low"}},
    "investability": {{"score": 0-100, "confidence": "high|medium|low"}},
    "overall": {{"score": 0-100, "confidence": "high|medium|low"}}
  }},
  "investor_verdicts": [
    {{"investor_id": "{active_investors[0]['id']}", "name": "{active_investors[0]['name']}", "verdict": "invest|negotiate|pass", "reason": "1-2 sentences in character"}},
    {{"investor_id": "{active_investors[1]['id']}", "name": "{active_investors[1]['name']}", "verdict": "invest|negotiate|pass", "reason": "1-2 sentences in character"}},
    {{"investor_id": "{active_investors[2]['id']}", "name": "{active_investors[2]['name']}", "verdict": "invest|negotiate|pass", "reason": "1-2 sentences in character"}}
  ],
  "deal_outcome": "X invest, Y negotiate, Z pass",
  "funding_secured": true or false,
  "strengths": ["2-3 specific strengths"],
  "growth_areas": ["2-3 areas for improvement"],
  "key_moments": ["2-3 notable moments with turn references"]
}}

Consider:
- Did they articulate the problem clearly?
- Were their numbers realistic and well-researched?
- How did they handle tough questions?
- Did they show conviction without being arrogant?
- Would a real investor write a check based on this pitch?"""

    fallback = {
        "outcome_quality": "acceptable",
        "outcome_message": "You completed the pitch. The panel had mixed reactions.",
        "scores": {
            "clarity_structure": {"score": final_state.get("pitch_score", 50), "confidence": "medium"},
            "market_understanding": {"score": 50, "confidence": "medium"},
            "financial_viability": {"score": 50, "confidence": "medium"},
            "confidence_delivery": {"score": final_state.get("panel_confidence", 50), "confidence": "medium"},
            "objection_handling": {"score": 50, "confidence": "medium"},
            "investability": {"score": 50, "confidence": "medium"},
            "overall": {"score": 50, "confidence": "medium"}
        },
        "investor_verdicts": [
            {"investor_id": inv["id"], "name": inv["name"], "verdict": "negotiate", "reason": "Interesting idea, but needs more work."}
            for inv in active_investors
        ],
        "deal_outcome": "0 invest, 3 negotiate",
        "funding_secured": False,
        "strengths": ["Completion", "Engagement"],
        "growth_areas": ["Continue refining your pitch"],
        "key_moments": []
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt="Evaluate this pitch performance. Provide individual investor verdicts.",
        temperature=0.5,
        max_tokens=700,
        purpose="evaluate_pitch",
        fallback=fallback,
    )

    # Normalize scores
    if "scores" in result:
        normalized = {}
        for k, v in result["scores"].items():
            if isinstance(v, dict) and "score" in v:
                normalized[k] = {"score": v["score"], "confidence": v.get("confidence", "medium")}
            elif isinstance(v, (int, float)):
                normalized[k] = {"score": v, "confidence": "medium"}
            else:
                normalized[k] = {"score": 50, "confidence": "low"}
        result["scores"] = normalized

    return result


# ═══════════════════════════════════════════════════════════════════════
# Generic session game functions (job_interview, group_discussion, etc.)
# ═══════════════════════════════════════════════════════════════════════

def generate_session_context(
    idea_description: str,
    game_type: str,
    persona_pool: list
) -> Dict[str, Any]:
    """
    For 'Create Your Own' mode in any session game: generate context from free-text input.
    """
    import random
    fallback_ids = [p["id"] for p in random.sample(persona_pool, min(3, len(persona_pool)))]

    game_labels = {
        "job_interview": ("role", "Interview"),
        "group_discussion": ("topic", "Group Discussion"),
        "client_meeting": ("meeting", "Client Meeting"),
        "conflict_mediation": ("conflict", "Mediation"),
        "public_speaking": ("talk", "Presentation"),
        "stakeholder_update": ("update", "Stakeholder Update"),
    }
    context_word, label = game_labels.get(game_type, ("session", "Session"))

    fallback = {
        "session_title": idea_description[:60],
        "industry": "General",
        "key_context": idea_description,
        "recommended_persona_ids": fallback_ids,
        "key_challenges": ["Unclear requirements", "Time pressure", "Stakeholder alignment"],
        "setting": f"A professional meeting room in an Indian office. The {label.lower()} is about to begin."
    }

    if not llm_enabled():
        return fallback

    idea_description = _sanitize_user_input(idea_description, max_length=500)
    pool_summary = json.dumps([{"id": p["id"], "archetype": p["archetype"], "focus": p["focus"]} for p in persona_pool])

    system_prompt = f"""You are a soft-skills coach setting up a {label} simulation for an Indian student.

The student wants to practice with this {context_word}:
"{idea_description}"

AVAILABLE PERSONAS (pick exactly 3 most relevant):
{pool_summary}

Return JSON:
{{
  "session_title": "A catchy 5-7 word title",
  "industry": "Industry/domain category",
  "key_context": "2-3 sentences expanding on the scenario with realistic Indian context",
  "recommended_persona_ids": ["id1", "id2", "id3"],
  "key_challenges": ["3 challenges the student might face"],
  "setting": "1-2 sentences describing the setting (keep it in India)"
}}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"Generate {label.lower()} context for: {idea_description}",
        temperature=0.8,
        max_tokens=800,
        purpose=f"generate_{game_type}_context",
        fallback=fallback,
    )

    valid_ids = {p["id"] for p in persona_pool}
    if "recommended_persona_ids" in result:
        result["recommended_persona_ids"] = [rid for rid in result["recommended_persona_ids"] if rid in valid_ids]
        while len(result.get("recommended_persona_ids", [])) < 3:
            remaining = list(valid_ids - set(result.get("recommended_persona_ids", [])))
            if not remaining:
                break
            result["recommended_persona_ids"].append(random.choice(remaining))

    return result


def session_panel_response(
    user_message: str,
    game_type: str,
    scenario_data: Dict[str, Any],
    conversation_history: list,
    current_turn: int,
    state: Dict[str, Any],
    active_personas: list,
    scores_history: list = None
) -> Dict[str, Any]:
    """
    Generic session panel response for all 6 session game types.
    """
    max_turns = scenario_data.get("conversation_turns", 10)
    phases = scenario_data.get("session_phases", ["Opening", "Main Discussion", "Deep Dive", "Wrap-Up"])

    # Determine phase from turn number (deterministic)
    phase_count = len(phases)
    turns_per_phase = max(1, max_turns // phase_count)
    phase_idx = min(current_turn // turns_per_phase, phase_count - 1)
    current_phase = phases[phase_idx]

    # Select which persona speaks this turn
    primary_idx = current_turn % len(active_personas)
    primary_persona = active_personas[primary_idx]

    game_labels = {
        "job_interview": "job interview",
        "group_discussion": "group discussion",
        "client_meeting": "client/sales meeting",
        "conflict_mediation": "conflict mediation",
        "public_speaking": "public speaking Q&A",
        "stakeholder_update": "stakeholder update",
        "ai_discussion": "analytical discussion",
    }
    game_label = game_labels.get(game_type, "interactive session")

    # Role instructions per game type
    role_instructions = {
        "job_interview": f"You are {primary_persona['name']}, an interviewer ({primary_persona['archetype']}). Ask interview questions based on your focus area. Stay in character. Ask ONE question per turn. Reference what the candidate said.",
        "group_discussion": f"You are {primary_persona['name']}, a GD participant ({primary_persona['archetype']}). React to the student's point, add your perspective, and keep the discussion flowing. Stay in character. Be natural — agree, disagree, or build on points.",
        "client_meeting": f"You are {primary_persona['name']}, a client ({primary_persona['archetype']}). Respond to the sales/service pitch. Ask questions relevant to your buying concerns. Stay in character.",
        "conflict_mediation": f"You are {primary_persona['name']}, a party in conflict ({primary_persona['archetype']}). React to the mediator's (student's) attempts at resolution. Show your emotions and concerns. Gradually warm up if the mediator does well, or escalate if they handle it poorly.",
        "public_speaking": f"You are {primary_persona['name']}, an audience member ({primary_persona['archetype']}). React to the presentation. During Q&A, ask questions from your perspective. Stay in character.",
        "stakeholder_update": f"You are {primary_persona['name']}, a stakeholder ({primary_persona['archetype']}). React to the project update. Ask questions relevant to your role and concerns. Stay in character.",
        "ai_discussion": f"You are {primary_persona['name']}, a mentor ({primary_persona['archetype']}). Discuss the topic using data, charts, and quantitative problems. IMPORTANT: In your JSON response, include TWO extra optional fields: 'chart_data' (a chart object with chart_type, title, data array, and keys) and 'math_problem' (an object with question, options array of 4 choices, correct_answer, and explanation). Include a chart_data every 2-3 turns to illustrate concepts. Include a math_problem every 2-3 turns to test understanding. Make problems progressively harder. Reference the student's previous answers.",
    }
    role_instruction = role_instructions.get(game_type, f"You are {primary_persona['name']}. Stay in character and respond naturally.")

    if not llm_enabled():
        return {
            "response": f"{primary_persona['name']}: That's interesting. Tell me more about your approach.",
            "speaker_persona_id": primary_persona["id"],
            "speaker_name": primary_persona["name"],
            "analysis": {
                "qualities_shown": [],
                "relationship_impact": 0,
                "assertiveness_impact": 0,
                "empathy_impact": 0,
                "feedback": "LLM not enabled — using fallback."
            },
            "phase": current_phase,
            "session_progress": (current_turn / max_turns) * 100,
            "persona_sentiments": {p["id"]: {"sentiment": "neutral", "leaning": "undecided"} for p in active_personas}
        }

    user_message = _sanitize_user_input(user_message, max_length=1000)

    # Adaptive tier
    tier = "developing"
    if scores_history:
        impact_scores = []
        for a in scores_history:
            if not isinstance(a, dict):
                continue
            for key in ["relationship_impact", "assertiveness_impact", "empathy_impact"]:
                v = a.get(key, 0)
                if isinstance(v, dict):
                    impact_scores.append(v.get("value", 0))
                elif isinstance(v, (int, float)):
                    impact_scores.append(v)
        if impact_scores:
            avg = sum(impact_scores) / len(impact_scores)
            if avg < -1:
                tier = "struggling"
            elif avg > 3:
                tier = "strong"

    personas_desc = ""
    for i, p in enumerate(active_personas):
        personas_desc += f"\n{i+1}. {p['name']} ({p['archetype']}): {p['personality']} Focus: {p['focus']}."

    tier_instruction = ""
    if tier == "struggling":
        tier_instruction = "The student is struggling. Be more supportive. Ask simpler questions. Give gentle guidance within your response."
    elif tier == "strong":
        tier_instruction = "The student is strong. Push harder. Ask deeper follow-ups. Challenge more aggressively."

    scoring_rubric = scenario_data.get("scoring_rubric", {})

    sentiment_keys = ", ".join([f'"{p["id"]}": {{"sentiment": "...", "leaning": "..."}}' for p in active_personas])

    system_prompt = f"""You are an AI panel in a {game_label} simulation for Indian students learning soft skills.

THE PANEL ({len(active_personas)} personas):
{personas_desc}

SCENARIO: {scenario_data.get('title', '')}
TOPIC: {scenario_data.get('session_topic', scenario_data.get('description', ''))}
SETTING: {scenario_data.get('setting', '')}

CURRENT STATE:
- Turn: {current_turn}/{max_turns}
- Phase: {current_phase}
- Performance Score: {state.get('performance_score', 0)}
- Session Quality: {next((v for k, v in list(state.items())[1:] if isinstance(v, (int, float))), 50)}/100

THIS TURN'S PRIMARY SPEAKER: {primary_persona['name']} ({primary_persona['archetype']})

ROLE INSTRUCTION:
{role_instruction}

SCORING RUBRIC:
{json.dumps(scoring_rubric, indent=2)}

{tier_instruction}

SCORING IMPACT ANCHORS:
- +7 to +10: Exceptional — impressive, well-structured, shows mastery
- +3 to +6: Good — solid response, shows preparation
- -1 to +2: Average — generic, doesn't fully address the question
- -5 to -1: Weak — evasive, unprepared, missed the point

RESPONSE FORMAT (JSON):
{{
  "response": "{primary_persona['name']}: [2-4 sentences in character. Ask a question or react.]",
  "speaker_persona_id": "{primary_persona['id']}",
  "speaker_name": "{primary_persona['name']}",
  "analysis": {{
    "qualities_shown": ["list of qualities demonstrated by the student"],
    "relationship_impact": {{"value": -10 to +10, "confidence": "high|medium|low"}},
    "assertiveness_impact": {{"value": -10 to +10, "confidence": "high|medium|low"}},
    "empathy_impact": {{"value": -10 to +10, "confidence": "high|medium|low"}},
    "feedback": "1 sentence coaching feedback (not shown to student during session)"
  }},
  "session_progress": {round((current_turn / max_turns) * 100)},
  "persona_sentiments": {{ {sentiment_keys} }}
}}

RULES:
- Stay in character as {primary_persona['name']}
- Ask ONE focused question per turn
- Reference specific things the student said
- Keep cultural context Indian
- Be {primary_persona['archetype']} — embody the personality described"""

    # AI Discussion: extend response format and prompt with chart/math instructions
    if game_type == "ai_discussion":
        features = scenario_data.get("features", {})
        chart_types = ', '.join(features.get('chart_themes', ['bar', 'line']))
        topic = scenario_data.get('session_topic', '')
        domains = ', '.join(features.get('problem_domains', []))
        # Replace the closing of the JSON format to include chart_data and math_problem
        system_prompt = system_prompt.replace(
            f'"persona_sentiments": {{ {sentiment_keys} }}\n}}',
            f'"persona_sentiments": {{ {sentiment_keys} }},\n'
            f'  "chart_data": {{"chart_type": "bar", "title": "Example", "data": [{{"label": "A", "value": 100}}, {{"label": "B", "value": 200}}], "keys": ["value"], "colors": ["#6366f1"]}},\n'
            f'  "math_problem": {{"question": "What is 2+2?", "options": ["3", "4", "5", "6"], "correct_answer": "4", "explanation": "Basic addition."}}\n}}'
        )
        system_prompt += f"""

CRITICAL — chart_data and math_problem RULES:
- You MUST include "chart_data" in your JSON response on turns {max(1, current_turn % 3 == 0 or current_turn == 1)}. Include it NOW if this is turn 1 or every 2-3 turns.
- You MUST include "math_problem" in your JSON response on alternating turns from charts. Include it NOW if this is turn 2 or every 2-3 turns.
- chart_data format: {{"chart_type": "{chart_types.split(',')[0].strip()}", "title": "...", "data": [{{"label": "...", "value": 123}}, ...], "keys": ["value"], "colors": ["#6366f1"]}}
- math_problem format: {{"question": "...", "options": ["A", "B", "C", "D"], "correct_answer": "B", "explanation": "..."}}
- Chart data must be realistic and relevant to: {topic}
- Math problems domains: {domains}. Start easy, get harder. 4 options, exactly 1 correct.
- If this is turn 1, include BOTH chart_data AND math_problem to demonstrate the format."""

    conv_messages = []
    recent = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
    for msg in recent:
        role = "user" if msg.get("speaker") in ("student", "user") else "assistant"
        conv_messages.append({"role": role, "content": msg.get("message", "")})

    import random
    fallback_responses = [
        f"{primary_persona['name']}: That's an interesting point. Can you elaborate on that?",
        f"{primary_persona['name']}: I see what you mean. But have you considered the other perspective?",
        f"{primary_persona['name']}: Good. Now let me ask you something different — how would you handle a real challenge here?",
        f"{primary_persona['name']}: Fair enough. Let's dig deeper into that.",
    ]
    fallback = {
        "response": fallback_responses[current_turn % len(fallback_responses)],
        "speaker_persona_id": primary_persona["id"],
        "speaker_name": primary_persona["name"],
        "analysis": {
            "qualities_shown": [],
            "relationship_impact": 0,
            "assertiveness_impact": 0,
            "empathy_impact": 0,
            "feedback": "Keep practicing."
        },
        "session_progress": round((current_turn / max_turns) * 100),
        "persona_sentiments": {p["id"]: {"sentiment": "neutral", "leaning": "undecided"} for p in active_personas}
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_message,
        conversation_history=conv_messages,
        temperature=0.7,
        max_tokens=1000 if game_type == "ai_discussion" else (500 if tier == "struggling" else 400),
        purpose=f"{game_type}_panel_response",
        fallback=fallback,
    )

    valid_ids = {p["id"] for p in active_personas}
    if result.get("speaker_persona_id") not in valid_ids:
        result["speaker_persona_id"] = primary_persona["id"]
        result["speaker_name"] = primary_persona["name"]

    result["phase"] = current_phase
    result.setdefault("session_progress", round((current_turn / max_turns) * 100))
    return result


def evaluate_session_outcome(
    game_type: str,
    scenario_data: Dict[str, Any],
    conversation_history: list,
    final_state: Dict[str, Any],
    active_personas: list
) -> Dict[str, Any]:
    """
    Generic evaluation for all 6 session game types.
    """
    game_labels = {
        "job_interview": "job interview",
        "group_discussion": "group discussion",
        "client_meeting": "client meeting",
        "conflict_mediation": "conflict mediation",
        "public_speaking": "public speaking",
        "stakeholder_update": "stakeholder update",
        "ai_discussion": "analytical discussion",
    }
    game_label = game_labels.get(game_type, "interactive session")

    verdict_labels = {
        "job_interview": {"positive": "hire", "neutral": "maybe", "negative": "pass"},
        "group_discussion": {"positive": "standout", "neutral": "average", "negative": "below_average"},
        "client_meeting": {"positive": "deal_closed", "neutral": "follow_up", "negative": "lost"},
        "conflict_mediation": {"positive": "resolved", "neutral": "partial", "negative": "unresolved"},
        "public_speaking": {"positive": "excellent", "neutral": "good", "negative": "needs_work"},
        "stakeholder_update": {"positive": "confident", "neutral": "cautious", "negative": "concerned"},
        "ai_discussion": {"positive": "analytical_expert", "neutral": "developing", "negative": "needs_practice"},
    }
    verdicts = verdict_labels.get(game_type, {"positive": "pass", "neutral": "partial", "negative": "fail"})

    if not llm_enabled():
        return {
            "outcome_quality": "acceptable",
            "outcome_message": f"You completed the {game_label}. LLM evaluation not available.",
            "scores": {k: {"score": 50, "confidence": "low"} for k in scenario_data.get("scoring_rubric", {})},
            "persona_verdicts": [
                {"persona_id": p["id"], "name": p["name"], "verdict": verdicts["neutral"], "reason": "Evaluation not available."}
                for p in active_personas
            ],
            "overall_outcome": "Completed",
            "success": False,
            "strengths": ["Participation", "Completion"],
            "growth_areas": ["Continue practicing"],
            "key_moments": []
        }

    personas_desc = "\n".join([
        f"- {p['name']} ({p['archetype']}): Focus on {p['focus']}"
        for p in active_personas
    ])
    scoring_rubric = scenario_data.get("scoring_rubric", {})

    verdict_options = f"{verdicts['positive']}|{verdicts['neutral']}|{verdicts['negative']}"

    system_prompt = f"""You are an expert soft-skills coach evaluating a student's {game_label} performance.

SCENARIO: {scenario_data.get('title', '')}
DIFFICULTY: {scenario_data.get('difficulty', 'intermediate')}

PANEL:
{personas_desc}

SCORING RUBRIC:
{json.dumps(scoring_rubric, indent=2)}

SCORING ANCHORS:
- Score 20-30: Poor — unprepared, vague, crumbles under pressure
- Score 50-60: Average — decent effort but lacks depth
- Score 80-90: Excellent — impressive, well-prepared, handles challenges gracefully

FINAL STATE: {json.dumps(final_state, indent=2)}

CONVERSATION: {json.dumps(conversation_history, indent=2)}

Each persona must give an independent verdict: {verdict_options}

RETURN JSON:
{{
  "outcome_quality": "excellent"|"good"|"acceptable"|"poor",
  "outcome_message": "2-3 sentences describing the outcome",
  "scores": {{
    {', '.join([f'"{k}": {{"score": "0-100", "confidence": "high|medium|low"}}' for k in scoring_rubric.keys()])},
    "overall": {{"score": "0-100", "confidence": "high|medium|low"}}
  }},
  "persona_verdicts": [
    {', '.join([f'{{"persona_id": "{p["id"]}", "name": "{p["name"]}", "verdict": "{verdict_options}", "reason": "1-2 sentences in character"}}' for p in active_personas])}
  ],
  "overall_outcome": "Summary of outcome",
  "success": true or false,
  "strengths": ["2-3 specific strengths"],
  "growth_areas": ["2-3 areas for improvement"],
  "key_moments": ["2-3 notable moments"]
}}"""

    fallback = {
        "outcome_quality": "acceptable",
        "outcome_message": f"You completed the {game_label}. The panel had mixed reactions.",
        "scores": {k: {"score": 50, "confidence": "medium"} for k in scoring_rubric},
        "persona_verdicts": [
            {"persona_id": p["id"], "name": p["name"], "verdict": verdicts["neutral"], "reason": "Interesting effort. Needs more practice."}
            for p in active_personas
        ],
        "overall_outcome": "Completed",
        "success": False,
        "strengths": ["Completion", "Engagement"],
        "growth_areas": ["Continue refining your skills"],
        "key_moments": []
    }
    fallback["scores"]["overall"] = {"score": 50, "confidence": "medium"}

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"Evaluate this {game_label} performance. Provide individual persona verdicts.",
        temperature=0.5,
        max_tokens=700,
        purpose=f"evaluate_{game_type}",
        fallback=fallback,
    )

    if "scores" in result:
        normalized = {}
        for k, v in result["scores"].items():
            if isinstance(v, dict) and "score" in v:
                normalized[k] = {"score": v["score"], "confidence": v.get("confidence", "medium")}
            elif isinstance(v, (int, float)):
                normalized[k] = {"score": v, "confidence": "medium"}
            else:
                normalized[k] = {"score": 50, "confidence": "low"}
        result["scores"] = normalized

    return result


def generate_metacognitive_reflection(
    game_type: str,
    scenario_data: Dict[str, Any],
    conversation_history: list,
    evaluation: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate a post-game metacognitive reflection to help students
    understand their own learning.

    Returns:
        {
            "key_insight": "What you practiced and why it matters...",
            "thinking_shift": "I noticed in round X you started to...",
            "next_step": "Next time, try..."
        }
    """
    if not llm_enabled():
        return {
            "key_insight": "You practiced important skills in this session.",
            "thinking_shift": "Your approach evolved as the conversation progressed.",
            "next_step": "Try to be more specific with evidence in your next session."
        }

    # Build evaluation summary
    if game_type == "debate":
        perf_summary = f"Overall quality: {evaluation.get('overall_quality', 'N/A')}\n"
        perf_summary += f"Overall score: {evaluation.get('overall_score', 'N/A')}/100\n"
        perf_summary += f"Strengths: {', '.join(evaluation.get('strengths', []))}\n"
        perf_summary += f"Growth areas: {', '.join(evaluation.get('growth_areas', []))}"
    else:
        perf_summary = f"Outcome quality: {evaluation.get('outcome_quality', 'N/A')}\n"
        perf_summary += f"Outcome: {evaluation.get('outcome_message', 'N/A')}\n"
        perf_summary += f"Strengths: {', '.join(evaluation.get('strengths', []))}\n"
        perf_summary += f"Growth areas: {', '.join(evaluation.get('growth_areas', []))}"

    # Summarize conversation (keep it concise for the LLM)
    conv_summary = []
    for i, msg in enumerate(conversation_history):
        speaker = "Student" if msg.get("speaker") == "student" else "AI"
        conv_summary.append(f"Turn {i+1} ({speaker}): {msg.get('message', '')[:150]}")
    conv_text = "\n".join(conv_summary[-10:])  # Last 10 turns max

    system_prompt = f"""You are a learning coach helping an Indian student aged 12-16 reflect on what they just learned.

GAME TYPE: {game_type}
TOPIC: {scenario_data.get('title', '')}

PERFORMANCE:
{perf_summary}

CONVERSATION SUMMARY:
{conv_text}

Generate a brief metacognitive reflection to help the student understand their own learning.
Focus on THREE things:

1. KEY INSIGHT: What is the one most important concept or skill this student practiced? Connect it to real life.
2. THINKING SHIFT: Based on their arguments/messages, where did their thinking evolve or improve during the session? Point to a specific moment.
3. NEXT STEP: One concrete, actionable thing to try in their next {game_type} to improve.

Keep language simple and encouraging. Use "you" to address the student directly.
2-3 sentences per section. No jargon.

RETURN JSON:
{{
  "key_insight": "What you practiced and why it matters...",
  "thinking_shift": "I noticed in round X you started to...",
  "next_step": "Next time, try..."
}}"""

    fallback = {
        "key_insight": "You practiced important critical thinking skills in this session.",
        "thinking_shift": "Your approach evolved as you engaged with new ideas.",
        "next_step": "Try to back up your points with specific examples next time."
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt="Generate a learning reflection for this student.",
        temperature=0.6,
        max_tokens=400,
        purpose="metacognitive_reflection",
        fallback=fallback,
    )

    # Ensure all fields exist
    for field in ["key_insight", "thinking_shift", "next_step"]:
        if field not in result:
            result[field] = "Keep practicing — you're making progress!"
    return result


def npc_conversation(
    npc_data: Dict[str, Any],
    player_message: str,
    game_context: Dict[str, Any],
    history: list
) -> Dict[str, Any]:
    """
    Generate NPC conversation response for board games.

    Args:
        npc_data: NPC config {name, avatar, personality, backstory, conversation_topics}
        player_message: What the player said
        game_context: {game_title, player_position, player_score, current_tile, ...}
        history: Previous messages [{speaker, message}]

    Returns:
        {"response": str, "hint": str|None, "mood": str}
    """
    if not llm_enabled():
        return {
            "response": f"Interesting thought! I'm {npc_data.get('name', 'an NPC')} and I think you're doing well in this game.",
            "hint": None,
            "mood": "friendly"
        }

    # Sanitize user input
    player_message = _sanitize_user_input(player_message, max_length=500)

    backstory = npc_data.get("backstory", npc_data.get("description", ""))
    topics = npc_data.get("conversation_topics", [])

    system_prompt = f"""You are {npc_data.get('name', 'an NPC')} in an educational board game.

YOUR CHARACTER:
- Name: {npc_data.get('name', 'NPC')}
- Personality: {npc_data.get('personality', 'friendly')}
- Backstory: {backstory}
- Conversation topics: {', '.join(topics) if topics else 'general game advice'}

GAME CONTEXT:
- Game: {game_context.get('game_title', 'Board Game')}
- Player position: tile {game_context.get('player_position', '?')}
- Player score: {game_context.get('player_score', 0)}

RULES:
1. Stay in character as {npc_data.get('name', 'the NPC')}
2. Be helpful and educational — you're in a learning game for Indian students aged 12-16
3. You can offer hints about strategy but don't give direct answers
4. Keep responses conversational (2-3 sentences)
5. If the player asks about game topics ({', '.join(topics) if topics else 'general'}), share knowledge
6. Be encouraging and fun

RETURN JSON:
{{
  "response": "Your spoken response",
  "hint": "Optional game hint or null",
  "mood": "friendly|excited|thoughtful|competitive|encouraging"
}}"""

    conv_history = []
    for msg in history[-6:]:
        role = "user" if msg.get("speaker") == "player" else "assistant"
        conv_history.append({"role": role, "content": msg.get("message", "")})

    npc_fallback = {
        "response": f"That's a great point! As {npc_data.get('name', 'your fellow player')}, I think you should keep exploring the board.",
        "hint": None,
        "mood": "friendly"
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=player_message,
        temperature=0.8,
        max_tokens=250,
        conversation_history=conv_history,
        purpose="npc_conversation",
        fallback=npc_fallback,
    )
    if not result.get("response"):
        result["response"] = "That's interesting! Tell me more."
    return result


def generate_ai_arena_round(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a dynamic game round for AI Arena games.
    LLM creates a complete round with title, story, goal, and 3-4 choices with deltas.

    Args:
        context: {domain, game_title, round_number, current_state, choice_history,
                  memory_tags, theme_options, difficulty_multiplier, min_choices, max_choices}

    Returns:
        {id, title, story, goal, choices: [{id, label, description, delta, feedback, memory_tag}]}
    """
    if not llm_enabled():
        return _fallback_ai_arena_round(context)

    domain = context.get("domain", "general")
    state_summary = json.dumps(context.get("current_state", {}), default=str)[:500]
    history_summary = json.dumps(context.get("choice_history", []), default=str)[:300]
    themes = ", ".join(context.get("theme_options", ["challenge", "opportunity"]))
    round_num = context.get("round_number", 1)
    min_choices = context.get("min_choices", 3)
    max_choices = context.get("max_choices", 4)
    difficulty = context.get("difficulty_multiplier", 1.0)

    # Build resource keys for delta generation
    resource_keys = list(context.get("current_state", {}).keys())[:10]
    resource_list = ", ".join(resource_keys) if resource_keys else "score, reputation"

    system_prompt = f"""You are a game designer creating a round for an AI-enhanced educational game.

GAME: {context.get('game_title', 'AI Arena Game')}
DOMAIN: {domain}
ROUND NUMBER: {round_num}
DIFFICULTY: {'harder' if difficulty > 1.1 else 'easier' if difficulty < 0.9 else 'moderate'}

CURRENT PLAYER STATE:
{state_summary}

PLAYER HISTORY:
{history_summary}

THEME OPTIONS for this round: {themes}

REQUIREMENTS:
1. Create a compelling, educational scenario related to {domain}
2. The story should reference the player's current state naturally
3. Provide {min_choices}-{max_choices} meaningful choices with different trade-offs
4. Each choice must have a delta object with resource changes using these keys: {resource_list}
5. Feedback should explain the real-world reasoning behind the outcome
6. Target audience: Indian students aged 12-16
7. Make it engaging, fun, and educational

RETURN JSON:
{{
  "id": "dynamic_round_{round_num}",
  "title": "Round {round_num}: [descriptive title]",
  "story": "2-3 sentence scenario description",
  "goal": "1 sentence objective",
  "choices": [
    {{
      "id": "choice_id",
      "label": "A natural first-person sentence (10-20 words) in the student's voice expressing their decision, e.g. 'I will invest heavily in marketing now even though it eats into our reserves'",
      "description": "Optional brief extra context only if label alone is not self-explanatory",
      "delta": {{"resource_name": change_value}},
      "feedback": "2-3 sentences explaining what happened and why",
      "memory_tag": "short_tag_for_tracking"
    }}
  ]
}}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"Generate round {round_num} with theme from: {themes}",
        temperature=0.8,
        max_tokens=800,
        purpose="ai_arena_round",
        fallback=_fallback_ai_arena_round(context),
    )

    # Validate required fields
    if "title" not in result:
        result["title"] = f"Round {round_num}: Dynamic Challenge"
    if "story" not in result:
        result["story"] = "A new challenge awaits..."
    if "choices" not in result or not result["choices"]:
        return _fallback_ai_arena_round(context)

    # Ensure all choices have required fields
    for i, choice in enumerate(result["choices"]):
        if "id" not in choice:
            choice["id"] = f"dynamic_{round_num}_{chr(97 + i)}"
        if "label" not in choice:
            choice["label"] = f"Option {i + 1}"
        if "delta" not in choice:
            choice["delta"] = {}
        if "feedback" not in choice:
            choice["feedback"] = "An interesting outcome!"

    result["id"] = f"dynamic_round_{round_num}"
    return result


def _fallback_ai_arena_round(context: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback round when LLM is unavailable."""
    round_num = context.get("round_number", 1)
    domain = context.get("domain", "general")
    resource_keys = list(context.get("current_state", {}).keys())[:3]

    return {
        "id": f"dynamic_round_{round_num}",
        "title": f"Round {round_num}: Strategic Decision",
        "story": f"A new situation arises in your {domain} journey. You need to make an important decision that could change your trajectory.",
        "goal": "Choose the best strategy for long-term success",
        "choices": [
            {
                "id": f"dynamic_{round_num}_a",
                "label": "Take the safe approach",
                "description": "A cautious strategy that minimizes risk but also limits reward.",
                "delta": {resource_keys[0]: 5} if resource_keys else {"score": 5},
                "feedback": "A steady approach that keeps things stable. Sometimes consistency is key to success.",
                "memory_tag": "chose_safe",
            },
            {
                "id": f"dynamic_{round_num}_b",
                "label": "Go bold and innovate",
                "description": "A risky but potentially rewarding strategy.",
                "delta": {resource_keys[1]: 15, resource_keys[0]: -5} if len(resource_keys) > 1 else {"score": 10},
                "feedback": "Bold moves can pay off big! The risk was calculated and the outcome is promising.",
                "memory_tag": "chose_bold",
            },
            {
                "id": f"dynamic_{round_num}_c",
                "label": "Collaborate and build partnerships",
                "description": "Seek allies and build a network for mutual benefit.",
                "delta": {resource_keys[2]: 10, resource_keys[0]: 3} if len(resource_keys) > 2 else {"score": 8},
                "feedback": "Teamwork makes the dream work! Your network grows stronger.",
                "memory_tag": "chose_collaborate",
            },
        ],
    }


def regenerate_round_narrative(round_data: Dict, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Regenerate a round's story text incorporating player state, choices, and difficulty.
    Uses the existing round as a template but rewrites story/goal to feel personalized.

    Args:
        round_data: The original round dict (title, story, goal, choices)
        context: {
            current_state: dict of resource values,
            choice_history: list of recent choice labels/tags,
            difficulty_level: "easy"/"medium"/"hard",
            performance_score: float 0-100,
            domain: str,
            game_title: str,
            round_number: int,
            player_name: str (optional),
        }

    Returns:
        {story: str, goal: str} — rewritten narrative fields
    """
    if not llm_enabled():
        return {"story": round_data.get("story", ""), "goal": round_data.get("goal", "")}

    original_story = round_data.get("story", "")
    original_goal = round_data.get("goal", "")
    title = round_data.get("title", "")
    domain = context.get("domain", "general")
    difficulty = context.get("difficulty_level", "medium")
    score = context.get("performance_score", 50)
    state_summary = json.dumps(context.get("current_state", {}), default=str)[:400]
    history = context.get("choice_history", [])
    recent_choices = ", ".join(str(h) for h in history[-5:]) if history else "none yet"

    # Optional executive context (only present for sim games with simulation_config blocks)
    ux_exec = context.get("ux_executive") or {}
    exec_summary = ""
    if ux_exec and ux_exec.get("any_executive_subsystem_active"):
        bits = []
        try:
            ue = (ux_exec.get("finance") or {}).get("unit_economics") or {}
            if ue:
                ltv_cac = ue.get("ltv_to_cac_ratio")
                runway = ue.get("runway_months")
                burn_mult = ue.get("burn_multiple")
                if ltv_cac is not None: bits.append(f"LTV/CAC={ltv_cac}")
                if runway is not None: bits.append(f"runway={runway}mo")
                if burn_mult is not None: bits.append(f"burn-multiple={burn_mult}")
            ct = (ux_exec.get("finance") or {}).get("cap_table") or {}
            pmv = ct.get("post_money_valuation")
            if pmv: bits.append(f"post-money=${pmv:,.0f}")
            board = (ux_exec.get("corporate_board") or {}).get("board_pulse") or {}
            if board.get("total_members"):
                bits.append(f"board {board.get('aligned_count', 0)}/{board.get('total_members')} aligned")
            comp = (ux_exec.get("compliance") or {}).get("compliance_status") or {}
            if comp.get("open_findings"):
                bits.append(f"{len(comp['open_findings'])} open compliance findings")
            crisis = ux_exec.get("crisis") or {}
            if crisis.get("active_crises"):
                bits.append(f"{len(crisis['active_crises'])} active crisis")
        except Exception:
            pass
        if bits:
            exec_summary = "\nExecutive dashboard: " + " · ".join(bits)

    # Determine narrative tone based on performance
    if score >= 75:
        tone = "confident and ambitious — player is doing great"
    elif score >= 50:
        tone = "balanced and encouraging — player is doing okay"
    else:
        tone = "urgent and supportive — player is struggling"

    system_prompt = f"""You are a narrative writer for an educational simulation game for Indian students aged 12-16.

GAME: {context.get('game_title', 'AI Arena')}
DOMAIN: {domain}

Rewrite the round's story and goal to feel personalized based on the player's current situation.

RULES:
1. Keep the same core scenario/theme from the original story
2. Weave in references to the player's current state and recent decisions
3. Tone should be: {tone}
4. Difficulty is {difficulty} — {'raise the stakes and urgency' if difficulty == 'hard' else 'keep it manageable and supportive' if difficulty == 'easy' else 'balanced challenge'}
5. Keep story to 2-4 sentences, goal to 1 sentence
6. Do NOT change the choices or mechanics — only rewrite story and goal text
7. Make it feel like the story is reacting to how the player has been playing

RETURN JSON:
{{"story": "rewritten story text", "goal": "rewritten goal text"}}"""

    user_prompt = f"""Original title: {title}
Original story: {original_story}
Original goal: {original_goal}

Player's current resources: {state_summary}
Player's recent choices: {recent_choices}{exec_summary}
Performance score: {score}/100
Difficulty: {difficulty}

Rewrite the story and goal to feel personalized.{(' Reference one or two of the executive metrics naturally where it fits — do NOT list them, weave them in.') if exec_summary else ''}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.8,
        max_tokens=300,
        purpose="narrative_regen",
        fallback={"story": original_story, "goal": original_goal},
    )

    # Ensure we got valid text back
    if not result.get("story"):
        result["story"] = original_story
    if not result.get("goal"):
        result["goal"] = original_goal

    return result


def generate_difficulty_scenario(round_data: Dict, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an entirely different scenario for a round based on difficulty level.
    Hard difficulty gets a more complex/urgent scenario; easy gets a simpler one.

    Args:
        round_data: Original round dict
        context: {difficulty_level, domain, current_state, resource_keys, round_number, game_title}

    Returns:
        {title, story, goal, choices} — complete alternative scenario, or None if LLM unavailable
    """
    if not llm_enabled():
        return None

    difficulty = context.get("difficulty_level", "medium")
    if difficulty == "medium":
        return None  # Medium uses original content

    domain = context.get("domain", "general")
    resource_keys = context.get("resource_keys", [])
    round_num = context.get("round_number", 1)
    original_title = round_data.get("title", "")
    original_story = round_data.get("story", "")
    state_summary = json.dumps(context.get("current_state", {}), default=str)[:400]

    if difficulty == "hard":
        scenario_directive = (
            "Create a HIGH-STAKES version of this scenario. The situation should be more urgent, "
            "the consequences more severe, and the trade-offs more painful. Add time pressure or "
            "a competing crisis. Make the player feel the weight of their decision."
        )
        delta_guidance = "Negative deltas should be -15 to -25, positive +5 to +12. No easy wins."
    else:  # easy
        scenario_directive = (
            "Create a GENTLER version of this scenario. The situation should feel manageable, "
            "the consequences less severe, and at least one choice should be clearly helpful. "
            "Include learning moments and encouragement."
        )
        delta_guidance = "Negative deltas should be -3 to -8, positive +8 to +15. Include a clearly good option."

    resource_list = ", ".join(resource_keys[:8]) if resource_keys else "score, reputation"

    system_prompt = f"""You are a game designer creating a {difficulty}-difficulty round for an educational game.

GAME: {context.get('game_title', 'AI Arena')}
DOMAIN: {domain}
DIFFICULTY: {difficulty.upper()}

ORIGINAL THEME: {original_title}
ORIGINAL SCENARIO: {original_story}

{scenario_directive}

RESOURCE KEYS to use in deltas: {resource_list}
DELTA GUIDANCE: {delta_guidance}

PLAYER STATE: {state_summary}

Keep the same general theme but create a scenario that feels appropriate for {difficulty} difficulty.
Target audience: Indian students aged 12-16.

RETURN JSON:
{{
  "title": "Round {round_num}: [title]",
  "story": "2-4 sentence scenario",
  "goal": "1 sentence objective",
  "choices": [
    {{
      "id": "choice_a",
      "label": "First-person decision statement (10-20 words)",
      "description": "Brief context",
      "delta": {{"resource": value}},
      "feedback": "2-3 sentences explaining outcome and real-world lesson",
      "memory_tag": "tag_name"
    }}
  ]
}}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"Generate a {difficulty} difficulty version of the round about: {original_title}",
        temperature=0.8,
        max_tokens=800,
        purpose=f"difficulty_scenario_{difficulty}",
        fallback=None,
    )

    if not result or "choices" not in result or not result["choices"]:
        return None

    # Fix up choice IDs
    for i, choice in enumerate(result["choices"]):
        if "id" not in choice:
            choice["id"] = f"diff_{round_num}_{chr(97 + i)}"
        if "delta" not in choice:
            choice["delta"] = {}
        if "feedback" not in choice:
            choice["feedback"] = "An interesting outcome!"

    return result


def generate_competitor_reaction(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a competitor's chat message based on their personality and game state.

    Args:
        context: {competitor, player_choice, player_state, competitor_state, round_title, game_domain}

    Returns:
        {"message": str, "mood": str, "strategy_hint": str}
    """
    if not llm_enabled():
        return _fallback_competitor_reaction(context)

    competitor = context.get("competitor", {})
    player_choice = context.get("player_choice", {})
    round_title = context.get("round_title", "")
    domain = context.get("game_domain", "general")

    system_prompt = f"""You are {competitor.get('name', 'a competitor')} in a {domain} game.

YOUR CHARACTER:
- Name: {competitor.get('name', 'Competitor')}
- Personality: {competitor.get('chat_personality', competitor.get('personality_type', 'balanced'))}
- Style: {competitor.get('personality_type', 'balanced')}

CURRENT ROUND: {round_title}
PLAYER'S LAST MOVE: {player_choice.get('label', 'unknown')}

RULES:
1. React to the player's choice in character
2. Be competitive but respectful — this is an educational game for teens
3. Show your strategy personality through your response
4. Keep it to 1-2 sentences
5. Never be mean or discouraging — competitive banter is fine

RETURN JSON:
{{
  "message": "Your spoken reaction (1-2 sentences)",
  "mood": "competitive|confident|impressed|worried|amused",
  "strategy_hint": "Brief hint about what you're planning next (optional, can be empty)"
}}"""

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"React to the player choosing: {player_choice.get('label', 'their move')}",
        temperature=0.8,
        max_tokens=150,
        purpose="competitor_reaction",
        fallback=_fallback_competitor_reaction(context),
    )
    if not result.get("message"):
        result["message"] = "Interesting move! Let's see how that plays out."
    return result


def _fallback_competitor_reaction(context: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback competitor reaction."""
    competitor = context.get("competitor", {})
    name = competitor.get("name", "Competitor")
    personality = competitor.get("personality_type", "balanced")
    choice_label = context.get("player_choice", {}).get("label", "that move")

    if personality == "aggressive":
        msg = f"Ha! '{choice_label}'? Bold, but I've already got my counter-strategy ready. Game on!"
        mood = "competitive"
    elif personality == "quality_focused":
        msg = f"'{choice_label}' — not bad. But while you focus on that, I'm perfecting my approach. Quality always wins."
        mood = "confident"
    else:
        msg = f"Smart thinking with '{choice_label}'. I respect that. May the best strategist win!"
        mood = "impressed"

    return {"message": msg, "mood": mood, "strategy_hint": ""}


def generate_post_game_quiz(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate 5 multiple-choice questions based on a completed game's theme,
    the player's choices, and the psychological skills practiced.
    """
    if not llm_enabled():
        return {
            "questions": [
                {
                    "id": 1,
                    "question": "What is the most important factor in making good decisions?",
                    "options": [
                        "Thinking about long-term consequences",
                        "Always choosing the cheapest option",
                        "Making decisions as fast as possible",
                        "Following what others do"
                    ],
                    "correct_index": 0,
                    "explanation": "Good decision-making considers long-term consequences, not just immediate benefits."
                }
            ]
        }

    system_prompt = (
        "You are an educational quiz creator for Indian students aged 10-16. "
        "Based on the game data provided, create exactly 5 multiple-choice questions "
        "that test understanding of the psychological skills and themes explored during gameplay. "
        "Each question should have 4 options with one correct answer. "
        "Questions should be age-appropriate, engaging, and educational. "
        "Mix conceptual questions with scenario-based ones.\n\n"
        "Return ONLY valid JSON:\n"
        '{"questions": [{"id": 1, "question": "...", "options": ["A", "B", "C", "D"], '
        '"correct_index": 0, "explanation": "..."}]}'
    )

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=json.dumps(context, default=str),
        temperature=0.4,
        max_tokens=1500,
        purpose="post_game_quiz",
        fallback={"questions": [], "error": "Failed to generate quiz"},
    )
    return result


def generate_content_component(component_type: str, topic: str, count: int = 5, difficulty: str = "intermediate") -> Dict[str, Any]:
    """
    Generate game content components using AI.

    Supported component_type values:
        quiz_questions, board_events, escape_room_clues, stock_portfolio, debate_scenario

    Returns: {"items": [...], "component_type": str}
    """
    if not llm_enabled():
        return {"error": "LLM not enabled", "items": [], "component_type": component_type}

    prompts = {
        "quiz_questions": f"""Generate {count} multiple-choice quiz questions about "{topic}" for Indian students aged 12-16.
Difficulty: {difficulty}.

RETURN JSON:
{{
  "items": [
    {{
      "question": "The question text",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct": 0,
      "explanation": "Why this is correct",
      "points": 10
    }}
  ]
}}""",
        "board_events": f"""Generate {count} board game event cards about "{topic}" for an educational board game.
Difficulty: {difficulty}. Each event should have choices with resource effects.

RETURN JSON:
{{
  "items": [
    {{
      "title": "Event title",
      "description": "What happens",
      "type": "event",
      "choices": [
        {{"id": "a", "text": "Choice A", "delta": {{"money": -100, "reputation": 10}}}},
        {{"id": "b", "text": "Choice B", "delta": {{"money": 50, "reputation": -5}}}}
      ]
    }}
  ]
}}""",
        "escape_room_clues": f"""Generate {count} escape room clues and puzzles about "{topic}" for students aged 12-16.
Difficulty: {difficulty}.

RETURN JSON:
{{
  "items": [
    {{
      "type": "clue",
      "content": "The clue text",
      "hint": "A helpful hint"
    }},
    {{
      "type": "puzzle",
      "question": "Puzzle question",
      "puzzle_type": "multiple_choice",
      "options": ["A", "B", "C", "D"],
      "correct": 0,
      "points": 20,
      "explanation": "Why this is correct"
    }}
  ]
}}""",
        "stock_portfolio": f"""Generate {count} fictional stock listings for a stock market game about "{topic}".
Include realistic company names, sectors, and financial data.

RETURN JSON:
{{
  "items": [
    {{
      "id": "stock_1",
      "name": "Company Name",
      "symbol": "CMP",
      "sector": "Technology",
      "initial_price": 150,
      "volatility": 0.03,
      "trend": 0.001,
      "description": "Brief company description"
    }}
  ]
}}""",
        "debate_scenario": f"""Generate a debate scenario about "{topic}" for Indian students aged 12-16.
Difficulty: {difficulty}.

RETURN JSON:
{{
  "items": [
    {{
      "scenario_id": "generated_{topic.lower().replace(' ', '_')[:20]}",
      "title": "Debate topic as a question",
      "description": "Brief description",
      "student_position": "for or against",
      "ai_position": "opposite position",
      "rounds": 3,
      "time_per_round_seconds": 120,
      "scoring_rubric": {{
        "logic": {{"weight": 0.3, "description": "Logical reasoning"}},
        "evidence": {{"weight": 0.3, "description": "Use of evidence"}},
        "rhetoric": {{"weight": 0.2, "description": "Communication"}},
        "rebuttal": {{"weight": 0.2, "description": "Counter-arguments"}}
      }},
      "ai_persona": {{
        "name": "AI Name",
        "avatar": "emoji",
        "personality": "personality traits",
        "style": "debate style"
      }},
      "coaching_tips": "Tips for the student",
      "learning_objectives": ["objective 1", "objective 2"]
    }}
  ]
}}""",
    }

    prompt = prompts.get(component_type)
    if not prompt:
        return {"error": f"Unknown component_type: {component_type}", "items": [], "component_type": component_type}

    result = llm_call(
        system_prompt="You are a game content designer for an educational platform targeting Indian students aged 12-16. Generate high-quality, engaging, and educational content.",
        user_prompt=prompt,
        temperature=0.7,
        max_tokens=1500,
        purpose=f"content_component_{component_type}",
        fallback={"error": "Generation failed", "items": []},
    )
    result["component_type"] = component_type
    return result


def generate_skill_report(dimension_scores, game_type: str, choices_made: list, game_title: str) -> Dict[str, Any]:
    """
    Generate a personalized soft skill report using LLM.
    Returns {summary_text, strengths: [{skill, score, explanation}], growth_area: {skill, suggestion}}.
    """
    if not llm_enabled() or not dimension_scores:
        return {}

    dims_text = ", ".join(
        f"{d.get('label', d.get('name', ''))}: {d.get('value', 0)}%"
        for d in (dimension_scores if isinstance(dimension_scores, list) else [])
    )
    choices_text = ", ".join(choices_made[:10]) if choices_made else "various decisions"

    prompt = (
        f"A student just completed a {game_type} game called '{game_title}'. "
        f"Their soft skill dimension scores are: {dims_text}. "
        f"Key choices they made: {choices_text}. "
        f"Write a personalized 2-3 sentence skill assessment. "
        f"Mention top 2 strengths and 1 area for growth. "
        f"Connect game decisions to real-life soft skill application. "
        f"Tone: encouraging, specific, concise. "
        f"Return JSON: {{\"summary_text\": \"...\", \"strengths\": [{{\"skill\": \"...\", \"score\": N, \"explanation\": \"...\"}}], \"growth_area\": {{\"skill\": \"...\", \"suggestion\": \"...\"}}}}"
    )

    return llm_call(
        system_prompt="You are an educational coach analyzing a student's soft skill development through game-based learning. Be specific, encouraging, and actionable.",
        user_prompt=prompt,
        temperature=0.6,
        max_tokens=400,
        purpose="skill_report",
        fallback={},
    )


def generate_end_debrief(game_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a personalized end-of-game debrief connecting patterns to real-world skills.
    Returns {debrief_text, key_insight, real_world_connection}.
    """
    if not llm_enabled():
        return {}

    title = game_summary.get("title", "game")
    game_type = game_summary.get("game_type", "simulation")
    choices = game_summary.get("choices", [])[:10]
    dims = game_summary.get("dimension_scores") or []

    dims_text = ", ".join(
        f"{d.get('label', '')}: {d.get('value', 0)}%"
        for d in (dims if isinstance(dims, list) else [])
    ) or "not available"

    choices_text = ", ".join(str(c) for c in choices) if choices else "various decisions"

    prompt = (
        f"Student completed '{title}' ({game_type}). "
        f"Choices: {choices_text}. Skill scores: {dims_text}. "
        f"Write a 3-4 sentence personal debrief as a coach. "
        f"Identify the student's decision pattern, connect it to real-world skills, "
        f"and give one actionable suggestion. Be encouraging but honest. "
        f"Return JSON: {{\"debrief_text\": \"...\", \"key_insight\": \"...\", \"real_world_connection\": \"...\"}}"
    )

    return llm_call(
        system_prompt="You are a soft skills coach giving a student personal feedback after a game. Be warm, specific, and practical.",
        user_prompt=prompt,
        temperature=0.7,
        max_tokens=400,
        purpose="end_debrief",
        fallback={},
    )


def generate_board_tile_story(
    game_title: str,
    game_theme: str,
    tile_type: str,
    tile_label: str,
    previous_choices_summary: str,
    current_resources: Dict[str, Any],
    glossary_terms: list = None,
    fallback_event: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Generate a contextual AI story for a board game tile, with choices and a concept card.
    Returns the fallback_event unchanged if LLM is disabled or on failure.
    """
    if not llm_enabled():
        return fallback_event or {}

    resources_text = ", ".join(
        f"{k}: {v}" for k, v in (current_resources or {}).items()
    ) or "none tracked"

    glossary_hint = ""
    if glossary_terms:
        glossary_hint = f" Try to weave in one of these concepts: {', '.join(glossary_terms[:3])}."

    system_prompt = (
        "You are a game narrative designer for educational board games that teach soft skills "
        "(leadership, empathy, strategic thinking, risk tolerance, adaptability, resilience) "
        "to teenagers. Write immersive, concise stories that feel like real dilemmas a young "
        "person might face. Each choice must have clear trade-offs tied to different skills."
    )

    user_prompt = (
        f"Game: \"{game_title}\" — Theme: {game_theme}\n"
        f"Tile type: {tile_type} | Tile label: {tile_label}\n"
        f"What happened so far: {previous_choices_summary or 'Game just started.'}\n"
        f"Current resources: {resources_text}\n"
        f"{glossary_hint}\n\n"
        "Generate a short story event for this tile with 2-3 choices. "
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        "  \"title\": \"Short event title\",\n"
        "  \"story\": \"2-3 sentence narrative description\",\n"
        "  \"choices\": [\n"
        "    {\n"
        "      \"id\": \"choice_a\",\n"
        "      \"text\": \"Choice description\",\n"
        "      \"delta\": {\"gold\": -10, \"reputation\": 5},\n"
        "      \"feedback\": \"What happens after this choice\",\n"
        "      \"skill_tags\": [\"empathy\"]\n"
        "    }\n"
        "  ],\n"
        "  \"concept_card\": {\n"
        "    \"concept\": \"Name of soft skill concept\",\n"
        "    \"definition\": \"One sentence definition\",\n"
        "    \"real_world_example\": \"One sentence real-world example\"\n"
        "  },\n"
        "  \"glossary_terms\": [\"term1\"]\n"
        "}"
    )

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.8,
        max_tokens=1200,
        purpose="board_tile_story",
        fallback=fallback_event or {},
    )

    # Validate minimum structure
    if isinstance(result, dict) and "title" in result and "choices" in result:
        # Ensure each choice has required fields
        for i, ch in enumerate(result.get("choices", [])):
            ch.setdefault("id", f"ai_choice_{i}")
            ch.setdefault("text", "Continue")
            ch.setdefault("delta", {})
            ch.setdefault("feedback", "")
            ch.setdefault("skill_tags", [])
        return result

    # LLM returned something unexpected — use fallback
    return fallback_event or {}


def generate_board_narrative_batch(
    game_title: str,
    game_theme: str,
    tiles_info: list,
    existing_events: Dict[str, Any],
    glossary_terms: list = None,
) -> Dict[str, Any]:
    """
    Generate a coherent narrative arc for ALL event tiles in a board game.
    Processes tiles in chunks of 4-5 to stay within token limits.
    Each chunk knows about previous chunks for narrative continuity.

    Returns:
        Dict mapping event_id -> { title, story, choices, concept_card, glossary_terms, ai_generated }
    """
    if not llm_enabled():
        return {}

    tile_count = len(tiles_info)
    if tile_count == 0:
        return {}

    # Get resource keys from existing events' choice deltas
    resource_keys = set()
    for evt in existing_events.values():
        for ch in evt.get("choices", []):
            resource_keys.update(ch.get("delta", {}).keys())
    resource_keys_text = ", ".join(sorted(resource_keys)) if resource_keys else "gold, reputation, morale"

    glossary_hint = ""
    if glossary_terms:
        glossary_hint = f"Available concepts to weave in: {', '.join(glossary_terms[:15])}."

    # Process in chunks of 5 tiles for manageable LLM responses
    CHUNK_SIZE = 5
    all_generated = {}
    previous_summaries = []

    for chunk_start in range(0, tile_count, CHUNK_SIZE):
        chunk = tiles_info[chunk_start:chunk_start + CHUNK_SIZE]
        chunk_num = chunk_start // CHUNK_SIZE + 1
        total_chunks = (tile_count + CHUNK_SIZE - 1) // CHUNK_SIZE

        # Build tile descriptions for this chunk
        tile_descriptions = []
        for i, tile in enumerate(chunk):
            existing = existing_events.get(tile.get("event_id", ""), {})
            existing_title = existing.get("title", "")
            global_idx = chunk_start + i + 1
            tile_descriptions.append(
                f"  Tile {global_idx}/{tile_count}: event_id=\"{tile['event_id']}\", "
                f"type={tile.get('tile_type', 'event')}, label=\"{tile.get('tile_label', '')}\""
                + (f", original_title=\"{existing_title}\"" if existing_title else "")
            )

        tiles_text = "\n".join(tile_descriptions)

        # Narrative continuity context from previous chunks
        continuity = ""
        if previous_summaries:
            continuity = (
                "\n\nPREVIOUS CHAPTERS (for continuity):\n" +
                "\n".join(f"  - {s}" for s in previous_summaries[-6:]) +
                "\n\nContinue the story naturally from where it left off."
            )

        # Position in arc
        if chunk_start == 0:
            arc_note = "These are the OPENING tiles. Introduce the setting, protagonist, and initial challenge."
        elif chunk_start + CHUNK_SIZE >= tile_count:
            arc_note = "These are the FINAL tiles. Build to climax and provide resolution."
        else:
            arc_note = "These are MIDDLE tiles. Escalate challenges and deepen the narrative."

        system_prompt = (
            "You are a game narrative designer for educational board games that teach soft skills "
            "(leadership, empathy, strategic thinking, risk tolerance, adaptability, resilience) "
            "to teenagers and young adults. You create immersive, story-driven board games where "
            "each tile tells a chapter of an interconnected narrative journey."
        )

        user_prompt = (
            f"Game: \"{game_title}\" — Theme: {game_theme}\n"
            f"Chunk {chunk_num}/{total_chunks} — {arc_note}\n"
            f"Resource keys for choice deltas: {resource_keys_text}\n"
            f"{glossary_hint}\n\n"
            f"Generate stories for these {len(chunk)} tiles:\n{tiles_text}\n"
            f"{continuity}\n\n"
            f"Return ONLY valid JSON — an object where each key is the event_id:\n"
            "{{\n"
            "  \"event_id_here\": {{\n"
            "    \"title\": \"Chapter title\",\n"
            "    \"story\": \"2-4 sentence immersive narrative\",\n"
            "    \"choices\": [\n"
            "      {{\n"
            "        \"id\": \"choice_a\",\n"
            "        \"text\": \"What the player can do\",\n"
            f"        \"delta\": {{use keys from: {resource_keys_text}}},\n"
            "        \"feedback\": \"Consequence description\",\n"
            "        \"skill_tags\": [\"empathy\"]\n"
            "      }}\n"
            "    ],\n"
            "    \"concept_card\": {{\n"
            "      \"concept\": \"Soft skill name\",\n"
            "      \"definition\": \"One sentence definition\",\n"
            "      \"real_world_example\": \"One sentence example\"\n"
            "    }},\n"
            "    \"glossary_terms\": [\"term1\"]\n"
            "  }}\n"
            "}}\n\n"
            f"Generate exactly {len(chunk)} events with 2-3 choices each. "
            "Each choice must have different delta trade-offs."
        )

        print(f"[BoardNarrative] Generating chunk {chunk_num}/{total_chunks} ({len(chunk)} tiles)...")

        result = llm_call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.75,
            max_tokens=4096,
            purpose="board_narrative_batch",
            fallback={},
        )

        if not isinstance(result, dict):
            print(f"[BoardNarrative] Chunk {chunk_num} returned non-dict, skipping")
            continue

        # Validate and collect this chunk's results
        for event_id, event_data in result.items():
            if not isinstance(event_data, dict) or "title" not in event_data:
                continue
            for i, ch in enumerate(event_data.get("choices", [])):
                ch.setdefault("id", f"ai_choice_{i}")
                ch.setdefault("text", "Continue")
                ch.setdefault("delta", {})
                ch.setdefault("feedback", "")
                ch.setdefault("skill_tags", [])
            event_data.setdefault("story", "")
            event_data.setdefault("concept_card", None)
            event_data.setdefault("glossary_terms", [])
            event_data["ai_generated"] = True
            all_generated[event_id] = event_data

            # Build summary for continuity
            previous_summaries.append(
                f"{event_data.get('title', '?')}: {event_data.get('story', '')[:80]}"
            )

        print(f"[BoardNarrative] Chunk {chunk_num} done: {len(result)} events generated")

    print(f"[BoardNarrative] Total generated: {len(all_generated)}/{tile_count}")
    return all_generated


def generate_image(prompt: str, style: str = "flat illustration") -> str | None:
    """Generate a DALL-E 3 image for a given scene prompt.

    Used by card_board (tile events) and trump_card (card reveal).
    Returns the image URL string, or None on failure / if OpenAI is unavailable.

    Args:
        prompt: Scene description (e.g. "Indian business meeting warm lighting")
        style: Art style prefix (default "flat illustration vibrant professional")
    """
    if not llm_enabled():
        return None
    try:
        client = _client()
        full_prompt = (
            f"{style}, vibrant colors, NEP India educational context: {prompt}. "
            "No text in image. Warm, inclusive, culturally respectful."
        )
        response = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt[:900],  # DALL-E 3 prompt limit ~4000 chars, keeping safe
            size="1024x1024",
            quality="standard",
            n=1,
        )
        return response.data[0].url if response.data else None
    except Exception as e:
        print(f"[generate_image] Failed: {e}")
        return None


# ── Feature 3: Assessment Agent ─────────────────────────────────────────────

def generate_assessment_report(
    game_title: str,
    game_type: str,
    dimension_scores: Dict[str, Any],
    choices: list,
    round_history: list,
    rubric: Dict = None,
) -> Dict[str, Any]:
    """
    Generate a structured competency assessment report for a completed game session.
    Used by teachers, HR, and enterprise assessors.

    Returns:
        {overall_grade, competencies: [{name, score, evidence, recommendation}],
         summary, strengths, development_areas, assessor_notes}
    """
    if not llm_enabled():
        return {
            "overall_grade": "N/A",
            "competencies": [],
            "summary": "Assessment unavailable — LLM not configured.",
            "strengths": [],
            "development_areas": [],
            "assessor_notes": "",
        }

    choices_text = "\n".join(
        f"Round {i+1}: {c.get('label', c.get('choice_id', 'Unknown'))}"
        for i, c in enumerate(choices[:15])
    )
    dim_text = "\n".join(f"  {k}: {v}/100" for k, v in (dimension_scores or {}).items())
    rubric_text = json.dumps(rubric, indent=2)[:400] if rubric else "Standard 6-dimension competency framework"

    system_prompt = (
        "You are a certified psychometric assessment specialist evaluating a student's performance "
        f"in '{game_title}' (game type: {game_type}), an interactive soft skills simulation.\n\n"
        "ASSESSMENT RUBRIC:\n" + rubric_text + "\n\n"
        "Be specific, evidence-based, and cite actual choices made. "
        "Use professional language appropriate for an employer or educational institution report.\n\n"
        "RETURN valid JSON only:\n"
        '{"overall_grade": "A|B|C|D", '
        '"competencies": [{"name": "skill name", "score": 0-100, "evidence": "specific choice or pattern observed", "recommendation": "actionable next step"}], '
        '"summary": "2-3 sentence overall assessment", '
        '"strengths": ["specific strength 1", "specific strength 2"], '
        '"development_areas": ["area 1", "area 2"], '
        '"assessor_notes": "1-2 sentences for the assessor/manager"}'
    )

    user_prompt = (
        f"DIMENSION SCORES:\n{dim_text}\n\n"
        f"CHOICES MADE:\n{choices_text}\n\n"
        "Generate the competency assessment report."
    )

    fallback = {
        "overall_grade": "C",
        "competencies": [{"name": d, "score": s, "evidence": "Based on game choices", "recommendation": "Continue practising"}
                         for d, s in (dimension_scores or {}).items()],
        "summary": f"Player completed {game_title}. Further analysis unavailable.",
        "strengths": [],
        "development_areas": [],
        "assessor_notes": "",
    }

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.5,
        max_tokens=700,
        purpose="assessment_agent",
        fallback=fallback,
    )
    # Ensure required fields
    result.setdefault("overall_grade", "C")
    result.setdefault("competencies", [])
    result.setdefault("summary", "")
    result.setdefault("strengths", [])
    result.setdefault("development_areas", [])
    result.setdefault("assessor_notes", "")
    return result


# ── Feature 4: Market Events Generator ──────────────────────────────────────

_SECTOR_TEMPLATES = {
    "finance": "Indian financial markets context: Sensex, Nifty, RBI monetary policy, FII flows, banking sector.",
    "startup": "Indian startup ecosystem: Series A/B funding, Tiger Global, SoftBank, regulatory environment, D2C trends.",
    "corporate": "Indian corporate landscape: TATA, Reliance, Infosys, M&A activity, Sebi regulations, ESG.",
    "negotiation": "Business negotiation context: supply chain, procurement, salary benchmarks, deal-making, vendor relationships.",
    "general": "General business environment: market conditions, competition, economic indicators.",
}


def generate_market_events(
    game_title: str,
    game_type: str,
    current_state: Dict[str, Any],
    sector: str = "general",
) -> list:
    """
    Generate 2-3 contextual market/news events for finance and negotiation games.
    No external API — LLM generates plausible sector-grounded events from game state.

    Returns:
        [{headline, impact, sentiment, relevance}]
    """
    if not llm_enabled():
        return []

    sector_ctx = _SECTOR_TEMPLATES.get(sector, _SECTOR_TEMPLATES["general"])
    state_snippet = json.dumps({k: v for k, v in list((current_state or {}).items())[:8]}, default=str)

    system_prompt = (
        f"You are a financial news writer generating realistic, brief market events for an educational game.\n"
        f"GAME: '{game_title}' (sector: {sector})\n"
        f"CONTEXT: {sector_ctx}\n\n"
        "Generate 2-3 short, realistic news headlines relevant to the player's current game state. "
        "Make them feel real — use specific company names, percentages, market terms. "
        "Each event should subtly signal an opportunity or threat relevant to the player's choices.\n\n"
        "RETURN JSON array only:\n"
        '[{"headline": "...", "impact": "brief 1-sentence business impact", '
        '"sentiment": "positive|negative|neutral", "relevance": "1 sentence why this matters to the player"}]'
    )

    user_prompt = f"Current game state snapshot:\n{state_snippet}\n\nGenerate market events."

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=0.85,
        max_tokens=250,
        purpose="market_events",
        fallback=[],
    )
    if isinstance(result, list):
        return result[:3]
    # Sometimes LLM wraps in a dict key
    if isinstance(result, dict):
        for key in ["events", "news", "items"]:
            if isinstance(result.get(key), list):
                return result[key][:3]
    return []


# ── Feature 6: Dynamic Round Generator ──────────────────────────────────────

def generate_dynamic_round(
    game_title: str,
    game_type: str,
    state_keys: list,
    current_state: Dict[str, Any],
    round_number: int,
    player_summary: Dict = None,
    difficulty: str = "medium",
) -> Dict[str, Any]:
    """
    Generate a fresh game round for a player who has completed all standard rounds.
    Extends generate_ai_arena_round() to rounds-type games.

    Args:
        state_keys: Resource key names from the game's initial_state (for delta generation)
        player_summary: From get_adaptive_summary() — {avg_scores, trend, games_completed}
        difficulty: "easy"|"medium"|"hard"

    Returns:
        Complete round JSON compatible with the existing rounds structure.
    """
    if not llm_enabled():
        return {}

    resource_list = ", ".join(state_keys[:10]) if state_keys else "score, reputation"
    state_snippet = json.dumps({k: v for k, v in list((current_state or {}).items())[:10]}, default=str)

    # Build player context for personalisation
    player_ctx = ""
    if player_summary and player_summary.get("has_history"):
        weak_dims = [d for d, s in player_summary.get("avg_scores", {}).items() if s < 55]
        strong_dims = [d for d, s in player_summary.get("avg_scores", {}).items() if s > 75]
        if weak_dims:
            player_ctx += f"Player's weaker areas: {', '.join(weak_dims[:2])}. Create choices that develop these.\n"
        if strong_dims:
            player_ctx += f"Player's strengths: {', '.join(strong_dims[:2])}. Challenge them in these areas.\n"

    system_prompt = (
        f"You are an expert educational game designer creating an additional challenge round for '{game_title}'.\n"
        f"Game type: {game_type} | Round number: {round_number} | Difficulty: {difficulty}\n\n"
        f"Current player state:\n{state_snippet}\n\n"
        f"{player_ctx}"
        f"Available resource keys for delta effects: {resource_list}\n\n"
        "REQUIREMENTS:\n"
        "1. Create a compelling scenario that naturally continues from the current game state\n"
        "2. 3 distinct choices with meaningful trade-offs (no clearly 'right' answer)\n"
        "3. Each choice must include effects using ONLY the provided resource keys\n"
        "4. Include skill_tags from: strategic_thinking, risk_tolerance, delayed_gratification, adaptability, resilience, empathy\n"
        "5. coaching_moment should teach a real-world lesson\n"
        "6. Make it engaging for Indian students/professionals aged 15-35\n\n"
        "RETURN valid JSON only:\n"
        '{"round_id": "dynamic_' + str(round_number) + '", '
        '"round_title": "descriptive title", '
        '"story_text": "2-3 paragraph scenario description", '
        '"choices": [{"id": "choice_id", "label": "first-person choice sentence (10-20 words)", '
        '"outcome_text": "2 sentences what happens after this choice", '
        '"effects": {"resource_key": numeric_change}, '
        '"skill_tags": ["dimension_name"], "feedback": "coaching sentence"}], '
        '"coaching_moment": "1-2 sentence teaching insight"}'
    )

    result = llm_call(
        system_prompt=system_prompt,
        user_prompt=f"Generate round {round_number} continuing the game narrative.",
        temperature=0.8,
        max_tokens=900,
        purpose="dynamic_round",
        fallback={},
    )

    if not result or not result.get("choices"):
        return {}

    # Normalise: ensure required fields
    result.setdefault("round_id", f"dynamic_{round_number}")
    result.setdefault("round_title", f"Round {round_number}: New Challenge")
    result.setdefault("story_text", "A new challenge emerges...")
    result.setdefault("coaching_moment", "Every decision shapes your journey.")
    for i, ch in enumerate(result.get("choices", [])):
        ch.setdefault("id", f"dyn_{round_number}_{chr(97+i)}")
        ch.setdefault("label", f"Option {i+1}")
        ch.setdefault("effects", {})
        ch.setdefault("skill_tags", [])
        ch.setdefault("outcome_text", "")
    return result


def story_challenge_response(
    scene_text: str,
    chosen_label: str,
    chosen_skills: list,
    expert_label: str,
    expert_reason: str,
    was_expert_pick: bool,
    npc_persona: str = "a thoughtful skeptic",
    user_reply: str = "",
    conversation_history: list = None,
    turn_index: int = 0,
    persona_ladder: list = None,
) -> Dict[str, Any]:
    """Generate a 'challenge me on this' beat for a story_branching scene.

    The NPC (e.g., a critical mentor, worried parent, opposing investor) pushes
    back on the player's chosen branch, surfacing the trade-off they made.
    If the player replies, the NPC responds again with calibrated feedback.

    Returns:
      {"response": "<NPC dialogue>",
       "feedback": "<one-line meta-coaching>",
       "tactics": ["active_listening", "reframing"],
       "tone": "skeptical|encouraging|challenging"}
    """
    fallback = {
        "response": (f"I hear you, but {('let me push back' if not was_expert_pick else 'tell me more')} — "
                     f"{expert_reason or 'what about the trade-off you just made?'}"),
        "feedback": "The NPC is testing whether you can defend your reasoning under pressure.",
        "tactics": ["socratic_questioning"],
        "tone": "skeptical",
    }
    if not llm_enabled():
        return fallback

    # R3 — persona ladder: by default escalate from skeptic → tougher persona on later turns.
    # Caller can pass per-game persona_ladder (array of strings, indexed by turn_index).
    _default_ladder = [
        npc_persona,
        "a sharper version of the same skeptic — quoting the player's own words back at them and pushing harder on the weakest part of their reasoning",
        "an outright adversary in the scene (a hostile investor, opposing counsel, or worried parent) cross-examining the player without concession; still 1–2 sentences and a question",
    ]
    ladder = persona_ladder if (isinstance(persona_ladder, list) and persona_ladder) else _default_ladder
    active_persona = ladder[min(turn_index, len(ladder) - 1)]
    escalation_note = ""
    if turn_index >= 1:
        escalation_note = (
            " You have already pushed back once. Do not soften — sharpen. Quote a specific phrase "
            "from the player's last reply and use it against them. Still 1–2 sentences, still end with a question."
        )

    sys_prompt = (
        f"You are {active_persona} in a branching narrative scene. The player just made a choice. "
        f"Your job is to challenge their reasoning in 1–2 sentences (max 35 words), surface the "
        f"trade-off they made, and invite them to defend or revise. Tone: probing, not hostile. "
        f"Always end with a question. Never lecture. Never reveal the 'right' answer.{escalation_note}"
    )
    chosen_skills_str = ", ".join(chosen_skills or []) or "general judgement"
    expert_block = (
        f"The expert pick was: \"{expert_label}\" because {expert_reason}." if expert_label else ""
    )
    pick_status = "matched the expert pick" if was_expert_pick else "diverged from the expert pick"

    user_prompt = (
        f"SCENE: {scene_text[:600]}\n"
        f"PLAYER CHOSE: \"{chosen_label}\" (skills: {chosen_skills_str}) — {pick_status}.\n"
        f"{expert_block}\n"
    )
    if user_reply:
        user_prompt += f"\nPLAYER NOW REPLIES: \"{user_reply[:400]}\"\nRespond to their reply with a follow-up challenge or affirmation (still 1–2 sentences, ending with a question)."
    else:
        user_prompt += "\nPush back on their choice in character. End with a question they must answer."

    user_prompt += (
        "\n\nReturn ONLY JSON of the form: "
        '{"response": "...", "feedback": "...", "tactics": ["..."], "tone": "..."}'
    )

    out = llm_call(
        system_prompt=sys_prompt,
        user_prompt=user_prompt,
        response_json=True,
        temperature=0.85,
        max_tokens=300,
        conversation_history=conversation_history or None,
        purpose="story_challenge",
        fallback=fallback,
    )
    if not isinstance(out, dict) or not out.get("response"):
        return fallback
    out.setdefault("feedback", "")
    out.setdefault("tactics", [])
    out.setdefault("tone", "skeptical")
    return out


# -----------------------------------------------------------------------------
# Reflection grader (Task 11)
# -----------------------------------------------------------------------------

# Allowed dimensions for reflection signal channel. Anything outside this set is
# discarded so a hallucinated dimension cannot leak into the score blend.
_REFLECTION_ALLOWED_DIMS = {
    "strategic_thinking",
    "risk_tolerance",
    "delayed_gratification",
    "adaptability",
    "resilience",
    "empathy",
    "ethical_reasoning",
    "creativity",
}


def _call_llm_json(system_prompt: str, user_prompt: str, **kwargs) -> dict:
    """Thin JSON-mode wrapper around llm_call. Test seam — patch this in tests."""
    return llm_call(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        response_json=True,
        temperature=kwargs.get("temperature", 0.3),
        max_tokens=kwargs.get("max_tokens", 600),
        purpose=kwargs.get("purpose", "reflection_grade"),
        fallback={},
    )


def grade_reflection_text(text, dimension_focus=None):
    """Grade a player's reflection rationale on quality of reasoning + dimension signals.

    Returns:
      {
        "score": int 0-100,
        "dim_signals": dict[dimension, int -10..+10],  # delta to add to authored
        "strengths": list[str],
        "improvements": list[str],
      }
    Returns zero-result for empty input. Returns a low fixed score for very short
    text without calling the LLM. Filters/clamps the LLM's output so out-of-range
    or hallucinated dimensions never reach the caller.
    """
    text = (text or "").strip()
    empty_result = {"score": 0, "dim_signals": {}, "strengths": [], "improvements": []}
    if not text:
        return empty_result
    if len(text) < 10:
        return {"score": 30, "dim_signals": {}, "strengths": [], "improvements": ["Add more detail"]}

    focus_list = list(dimension_focus or ["empathy", "strategic_thinking"])
    focus_set = {d for d in focus_list if d in _REFLECTION_ALLOWED_DIMS}
    if not focus_set:
        focus_set = {"empathy", "strategic_thinking"}
    focus_str = ", ".join(sorted(focus_set))

    sys_prompt = (
        f"You are an educational psychologist scoring a student's reflection on a recent "
        f"in-game choice. Focus dimensions: {focus_str}. "
        f"Return JSON with fields: score (0-100), dim_signals (object mapping each focus "
        f"dimension to an integer -10..+10 indicating how strongly the reflection demonstrates "
        f"that dimension), strengths (array of short strings), improvements (array of short "
        f"strings). Be calibrated: 50 = generic, 70 = thoughtful, 85 = exceptionally insightful."
    )

    try:
        raw = _call_llm_json(sys_prompt, text)
    except Exception as e:  # pragma: no cover — defensive
        logging.getLogger(__name__).warning("reflection grader call failed: %s", e)
        return empty_result

    if not isinstance(raw, dict):
        return empty_result

    # Clamp score to 0-100
    try:
        score = int(raw.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    # Filter dim_signals to focus set, clamp values to [-10, 10], coerce int
    raw_signals = raw.get("dim_signals") or {}
    dim_signals = {}
    if isinstance(raw_signals, dict):
        for dim, val in raw_signals.items():
            if dim not in focus_set:
                continue
            try:
                v = int(val)
            except (TypeError, ValueError):
                continue
            dim_signals[dim] = max(-10, min(10, v))

    return {
        "score": score,
        "dim_signals": dim_signals,
        "strengths": _grader_str_list(raw.get("strengths")),
        "improvements": _grader_str_list(raw.get("improvements")),
    }


# -----------------------------------------------------------------------------
# Worksheet rubric grader (Task 14)
# -----------------------------------------------------------------------------

# Content-hash cache: key = sha256(text|lesson_id|rubric_version) -> graded dict
_WORKSHEET_GRADE_CACHE: dict = {}
_WORKSHEET_CACHE_MAX = 2000


def _grader_str_list(v):
    """Coerce a value to a sanitized list of up to 5 short strings."""
    if not isinstance(v, list):
        return []
    return [str(x) for x in v if isinstance(x, (str, int, float))][:5]

# Allowed dimensions a rubric grader may emit. Reuse reflection allowlist plus
# a few business/exec dimensions worksheets typically score on.
_WORKSHEET_ALLOWED_DIMS = set(_REFLECTION_ALLOWED_DIMS) | {
    "commercial_acumen",
    "execution",
    "communication",
    "analytical_rigor",
}


def _worksheet_cache_key(text: str, lesson_id: str, rubric_version: str) -> str:
    # Use a null-byte separator: decoded UTF-8 strings cannot contain \x00,
    # so field boundaries are unambiguous and "a|b" + "c" cannot collide
    # with "a" + "b|c".
    h = hashlib.sha256()
    h.update((text or "").encode("utf-8", errors="ignore"))
    h.update(b"\x00")
    h.update((lesson_id or "").encode("utf-8", errors="ignore"))
    h.update(b"\x00")
    h.update((rubric_version or "v0").encode("utf-8", errors="ignore"))
    return h.hexdigest()


def grade_worksheet_freetext(text, lesson, rubric):
    """Grade a worksheet free-text answer against an anchor-driven rubric.

    Args:
      text: student's free-text answer.
      lesson: dict with at least 'id' and 'type' (e.g. idea_scorecard, reflection).
      rubric: dict with 'anchors' (novice/capable/strong/exec), 'signals' list,
              and optional 'version'. The cache key includes only
              (text, lesson_id, rubric_version) — callers MUST bump 'version'
              whenever anchor text changes, otherwise stale results will be
              returned. Rubrics with no 'version' field share the default 'v0'
              cache partition.

    Returns:
      {
        "score": int 0-100,
        "strengths": list[str],
        "improvements": list[str],
        "dim_signals": dict[dimension, int -10..+10],
      }
    Empty input returns a zero result without touching the LLM.
    Cached by SHA256(text|lesson_id|rubric_version).
    """
    empty_result = {"score": 0, "strengths": [], "improvements": [], "dim_signals": {}}
    text = (text or "").strip()
    if not text:
        return empty_result

    lesson = lesson or {}
    rubric = rubric or {}
    lesson_id = str(lesson.get("id") or "")
    rubric_version = str(rubric.get("version") or "v0")

    cache_key = _worksheet_cache_key(text, lesson_id, rubric_version)
    cached = _WORKSHEET_GRADE_CACHE.get(cache_key)
    if cached is not None:
        return cached

    anchors = rubric.get("anchors") or {}
    signals = rubric.get("signals") or []
    anchor_lines = []
    for level in ("novice", "capable", "strong", "exec"):
        if anchors.get(level):
            anchor_lines.append(f"- {level}: {anchors[level]}")
    anchor_block = "\n".join(anchor_lines) if anchor_lines else "(no anchors provided)"
    signal_block = ", ".join(str(s) for s in signals) if signals else "(none specified)"

    sys_prompt = (
        f"You are grading a student worksheet answer for lesson '{lesson_id}' "
        f"(type: {lesson.get('type', 'worksheet')}). "
        f"Use this rubric:\n{anchor_block}\n"
        f"Signals to look for: {signal_block}.\n"
        f"Return JSON with fields: score (0-100, calibrated to anchors: novice~30, "
        f"capable~60, strong~78, exec~92), strengths (array of short strings), "
        f"improvements (array of short strings), dim_signals (object mapping "
        f"competency dimensions to integer -10..+10)."
    )

    try:
        raw = _call_llm_json(sys_prompt, text, purpose="worksheet_grade")
    except Exception as e:  # pragma: no cover — defensive
        logging.getLogger(__name__).warning("worksheet grader call failed: %s", e)
        return empty_result

    if not isinstance(raw, dict):
        return empty_result

    # Clamp score to 0-100
    try:
        score = int(raw.get("score", 0))
    except (TypeError, ValueError):
        score = 0
    score = max(0, min(100, score))

    # Filter dim_signals to allowlist, clamp to [-10, 10]
    raw_signals = raw.get("dim_signals") or {}
    dim_signals = {}
    if isinstance(raw_signals, dict):
        for dim, val in raw_signals.items():
            if dim not in _WORKSHEET_ALLOWED_DIMS:
                continue
            try:
                v = int(val)
            except (TypeError, ValueError):
                continue
            dim_signals[dim] = max(-10, min(10, v))

    result = {
        "score": score,
        "strengths": _grader_str_list(raw.get("strengths")),
        "improvements": _grader_str_list(raw.get("improvements")),
        "dim_signals": dim_signals,
    }

    # Cache with simple FIFO eviction when full
    if len(_WORKSHEET_GRADE_CACHE) >= _WORKSHEET_CACHE_MAX:
        try:
            first_key = next(iter(_WORKSHEET_GRADE_CACHE))
            _WORKSHEET_GRADE_CACHE.pop(first_key, None)
        except StopIteration:
            pass
    _WORKSHEET_GRADE_CACHE[cache_key] = result
    return result
