"""
Parent visibility — daily soft-skill summary.

Existing ParentDashboardPage shows scores and game counts but doesn't
plainly answer "what soft skill did my child practice today?". This
module reads run logs and produces a short, non-technical daily summary
a parent can read in 10 seconds.

Output shape:
  {
    "date": "2026-05-05",
    "child_id": "...",
    "games_played": 2,
    "minutes": 18,
    "top_skill_today": {"name": "Empathy", "delta": 8, "icon": "🫶"},
    "skills_practiced": [
      {"name": "Empathy", "icon": "🫶", "summary": "..."},
      {"name": "Strategic Thinking", "icon": "🧠", "summary": "..."}
    ],
    "talking_points": [
      "Ask: 'What did you decide in the city-mayor game?'"
    ]
  }
"""
import datetime as _dt
from typing import Any, Dict, Iterable, List, Optional

# Plain-language mapping. Parents don't read "delayed_gratification".
_SKILL_LABELS: Dict[str, Dict[str, str]] = {
    "strategic_thinking":     {"name": "Strategic Thinking",   "icon": "🧠"},
    "risk_tolerance":         {"name": "Risk Awareness",       "icon": "⚖️"},
    "delayed_gratification":  {"name": "Patience",             "icon": "⏳"},
    "adaptability":           {"name": "Flexibility",          "icon": "🌱"},
    "resilience":             {"name": "Bouncing Back",        "icon": "💪"},
    "empathy":                {"name": "Empathy",              "icon": "🫶"},
    "ethical_reasoning":      {"name": "Ethical Thinking",     "icon": "⚖️"},
    "creativity":             {"name": "Creativity",           "icon": "🎨"},
    "focus":                  {"name": "Focus",                "icon": "🎯"},
    "attention_to_detail":    {"name": "Attention to Detail",  "icon": "🔍"},
    "deductive_reasoning":    {"name": "Logical Thinking",     "icon": "🔎"},
    "pattern_recognition":    {"name": "Pattern Spotting",     "icon": "🧩"},
    "communication":          {"name": "Communication",        "icon": "🗣️"},
    "persistence":            {"name": "Persistence",          "icon": "🚀"},
}


def _label_for(dim: str) -> Dict[str, str]:
    return _SKILL_LABELS.get(dim, {"name": dim.replace("_", " ").title(), "icon": "✨"})


def _date_str(ts: float) -> str:
    return _dt.datetime.utcfromtimestamp(float(ts)).strftime("%Y-%m-%d")


def build_daily_summary(
    child_id: str,
    runs: Iterable[Dict[str, Any]],
    target_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Args:
        child_id: the student's user id
        runs: iterable of run records — each must include 'created_at'
              (epoch float) or 'date' (YYYY-MM-DD), 'dimension_scores'
              (dict of dim → 0-100), 'duration_minutes' (optional),
              and 'game_title' (optional).
        target_date: YYYY-MM-DD; defaults to today UTC.

    Returns: parent-facing summary dict (see module docstring).
    """
    today = target_date or _dt.datetime.utcnow().strftime("%Y-%m-%d")
    todays_runs: List[Dict[str, Any]] = []
    for r in runs or []:
        if not isinstance(r, dict):
            continue
        d = r.get("date")
        if not d and r.get("created_at"):
            try:
                d = _date_str(r.get("created_at"))
            except (TypeError, ValueError):
                d = None
        if d == today:
            todays_runs.append(r)

    minutes = 0
    skill_totals: Dict[str, int] = {}
    skill_counts: Dict[str, int] = {}
    games_seen: List[str] = []
    for r in todays_runs:
        try:
            minutes += int(r.get("duration_minutes") or 0)
        except (TypeError, ValueError):
            pass
        title = r.get("game_title")
        if title:
            games_seen.append(title)
        for dim, score in (r.get("dimension_scores") or {}).items():
            try:
                s = int(score)
            except (TypeError, ValueError):
                continue
            skill_totals[dim] = skill_totals.get(dim, 0) + s
            skill_counts[dim] = skill_counts.get(dim, 0) + 1

    # Average per skill, rank, take top 3.
    avg_by_skill = {
        dim: round(skill_totals[dim] / skill_counts[dim])
        for dim in skill_totals
    }
    ranked = sorted(avg_by_skill.items(), key=lambda kv: -kv[1])
    top = ranked[:3]

    skills_practiced: List[Dict[str, Any]] = []
    for dim, avg in top:
        meta = _label_for(dim)
        skills_practiced.append({
            "dimension": dim,
            "name": meta["name"],
            "icon": meta["icon"],
            "avg_score": avg,
            "summary": f"Practiced {meta['name'].lower()} — averaged {avg}/100 today.",
        })

    top_skill = None
    if skills_practiced:
        first = skills_practiced[0]
        top_skill = {
            "name": first["name"],
            "icon": first["icon"],
            "delta": first["avg_score"],
        }

    # Talking points — concrete questions parents can ask.
    talking_points: List[str] = []
    if top_skill and games_seen:
        talking_points.append(
            f"Ask: \"In {games_seen[0]}, what helped you with {top_skill['name'].lower()}?\""
        )
    if len(skills_practiced) >= 2:
        second = skills_practiced[1]
        talking_points.append(
            f"Ask: \"Tell me about a moment you used {second['name'].lower()} today.\""
        )
    if not talking_points:
        talking_points.append(
            "Ask: \"What's one thing you learned playing today?\""
        )

    return {
        "date": today,
        "child_id": child_id,
        "games_played": len(todays_runs),
        "minutes": minutes,
        "top_skill_today": top_skill,
        "skills_practiced": skills_practiced,
        "talking_points": talking_points,
        "games_titles": games_seen,
    }
