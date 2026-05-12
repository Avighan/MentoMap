"""Aggregate dimension scores for a single (user, module) pair.

Sources:
- All completed games linked from module lessons (uses existing run reports).
- All completed quizzes in the module (mapped to dimensions via quiz tags).
- Pitch-coach attempts (communication / creativity / strategic_thinking).
- Interview-sim depth score (empathy / strategic_thinking).
- Recommendations: next modules based on weakest 2 dimensions.
"""
from typing import Any, Dict, List, Optional

import modules_engine
import idea_journal as _ij

_CORE_DIMS = [
    "strategic_thinking",
    "creativity",
    "empathy",
    "communication",
    "resilience",
    "adaptability",
    "risk_tolerance",
    "delayed_gratification",
]

_DEFAULT = 50


def build_report(
    user_id: str,
    module_id: str,
    runs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    module = modules_engine.get_module(module_id) or {}
    prog = modules_engine.get_user_progress(user_id, module_id) or {}

    dims: Dict[str, List[int]] = {d: [] for d in _CORE_DIMS}

    # 1. Game runs (caller passes them — keeps this module pure)
    for run in runs or []:
        rep = run.get("report") or {}
        for k, v in (rep.get("dimensions") or {}).items():
            if k in dims and isinstance(v, (int, float)):
                dims[k].append(int(v))

    # 2. Pitch coach attempts (Phase B writes these into progress)
    for lesson_prog in (prog.get("lessons") or {}).values():
        for attempt in lesson_prog.get("pitch_attempts", []) or []:
            r = (attempt.get("rubric") or {})
            # 5-axis rubric maps to dimensions
            dims["communication"].append(int(r.get("hook", 0) + r.get("ask", 0)) * 5)
            dims["creativity"].append(int(r.get("solution", 0)) * 10)
            dims["strategic_thinking"].append(
                int(r.get("problem", 0) + r.get("customer", 0)) * 5
            )

    # 3. Interview-sim depth (Phase B writes depth_score)
    for lesson_prog in (prog.get("lessons") or {}).values():
        for conv in lesson_prog.get("interview_conversations", []) or []:
            depth = conv.get("depth_score")
            if isinstance(depth, (int, float)):
                dims["empathy"].append(min(100, int(depth) * 20))
                dims["strategic_thinking"].append(min(100, int(depth) * 20))

    # 4. Quiz scores
    for q in (prog.get("quizzes") or {}).values():
        score = q.get("score")
        if isinstance(score, (int, float)):
            for tag in q.get("dimension_tags") or ["strategic_thinking"]:
                if tag in dims:
                    dims[tag].append(int(score))

    flat = {d: int(sum(v) / len(v)) if v else _DEFAULT for d, v in dims.items()}

    # Highlights: top 3 dims with score >=70
    sorted_dims = sorted(flat.items(), key=lambda x: -x[1])
    highlights = [
        {"dimension": d, "score": s, "label": _highlight_for(d, s)}
        for d, s in sorted_dims[:3] if s >= 70
    ]

    # Recommendations: 2 weakest dims → next-module suggestions
    weakest = [d for d, _ in sorted(flat.items(), key=lambda x: x[1])[:2]]
    recommendations = _recommend_modules(weakest, exclude=module_id)

    # Idea journal stats for the report
    try:
        journal_count = len(_ij.list_entries(user_id, module_id))
    except Exception:
        journal_count = 0

    return {
        "module_id": module_id,
        "module_title": module.get("title") or module_id,
        "dimensions": flat,
        "deltas_from_baseline": _delta_from_baseline(user_id, flat),
        "highlights": highlights,
        "recommendations": recommendations,
        "journal_entries": journal_count,
        "completion": _completion_summary(prog, module),
    }


def _highlight_for(dim: str, score: int) -> str:
    labels = {
        "creativity": f"Top-tier creativity ({score})",
        "empathy": f"Strong empathy ({score})",
        "communication": f"Confident communicator ({score})",
        "strategic_thinking": f"Sharp strategic thinking ({score})",
        "resilience": f"Resilient under pressure ({score})",
    }
    return labels.get(dim, f"{dim.replace('_', ' ').title()} ({score})")


def _recommend_modules(weakest_dims: List[str], exclude: str) -> List[Dict[str, str]]:
    # Static mapping for v1 — content team curates.
    mapping = {
        "communication": ("mento_public_speaking_4week", "Public Speaking"),
        "empathy": ("mento_civic_leadership_4week", "Civic Leadership"),
        "strategic_thinking": ("mento_personal_finance_4week", "Personal Finance"),
        "resilience": ("mento_storytelling_4week", "Storytelling"),
        "creativity": ("mento_storytelling_4week", "Storytelling"),
    }
    seen = set()
    out: List[Dict[str, str]] = []
    for d in weakest_dims:
        rec = mapping.get(d)
        if rec and rec[0] != exclude and rec[0] not in seen:
            out.append({"module_id": rec[0], "title": rec[1], "because_of": d})
            seen.add(rec[0])
    return out


def _delta_from_baseline(user_id: str, current: Dict[str, int]) -> Dict[str, int]:
    # If you have baseline scores stored on the user profile, diff here.
    # For v1, return empty so the UI shows current absolute scores.
    return {}


def _completion_summary(prog: Dict[str, Any], module: Dict[str, Any]) -> Dict[str, Any]:
    all_lessons = [
        l for w in module.get("weeks", []) for l in w.get("lessons", [])
    ]
    total = len(all_lessons)
    done = sum(
        1 for l in all_lessons
        if (
            prog.get("lessons", {}).get(l.get("lesson_id") or l.get("id"), {})
                .get("status") == "complete"
        )
    )
    return {
        "total_lessons": total,
        "completed_lessons": done,
        "percent": int(100 * done / total) if total else 0,
    }
