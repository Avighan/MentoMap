"""
Player Profile System — Cross-game XP, levels, and badges.
File-based storage at game_sessions/profiles.json.
"""

import json
import os
import secrets
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
import math
from statistics import mean, stdev, median

PROFILES_FILE = os.path.join(os.path.dirname(__file__), "game_sessions", "profiles.json")
UNLOCK_RULES_FILE = os.path.join(os.path.dirname(__file__), "data", "unlock_rules.json")

_PROFILES_LOCK = threading.Lock()

# XP formula: level = floor(sqrt(xp / 50))
# level 1 = 50 XP, level 5 = 1250 XP, level 10 = 5000 XP
def get_level(xp: int) -> int:
    return max(1, int(math.sqrt(xp / 50))) if xp >= 50 else 0

def xp_for_level(level: int) -> int:
    return level * level * 50

def xp_progress(xp) -> Dict:
    """Return current level, XP into this level, XP needed for next level."""
    xp = int(round(xp)) if isinstance(xp, float) else int(xp or 0)
    level = get_level(xp)
    current_threshold = xp_for_level(level)
    next_threshold = xp_for_level(level + 1)
    return {
        "level": level,
        "current_xp": xp,
        "xp_into_level": xp - current_threshold,
        "xp_for_next": next_threshold - current_threshold,
        "progress_pct": round(((xp - current_threshold) / max(1, next_threshold - current_threshold)) * 100),
    }

# Load achievements from config (falls back to legacy BADGES if config missing)
ACHIEVEMENTS_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config", "global_achievements.json")

def _load_achievements():
    """Load achievements from config file."""
    try:
        with open(ACHIEVEMENTS_CONFIG_FILE, "r") as f:
            data = json.load(f)
            return data.get("achievements", []), data.get("categories", {})
    except (FileNotFoundError, json.JSONDecodeError):
        # Fallback to legacy hardcoded badges
        return [
            {"id": "first_steps", "name": "First Steps", "description": "Complete any game", "icon": "🎯", "rarity": "common", "category": "milestones", "condition": {"type": "games_completed", "value": 1}},
            {"id": "veteran", "name": "Veteran Player", "description": "Complete 10 games", "icon": "🏅", "rarity": "rare", "category": "milestones", "condition": {"type": "games_completed", "value": 10}},
            {"id": "dedicated", "name": "Dedicated Learner", "description": "Complete 25 games", "icon": "📚", "rarity": "epic", "category": "milestones", "condition": {"type": "games_completed", "value": 25}},
        ], {}

BADGES = _load_achievements()[0]  # backward compat alias


def _load_profiles() -> Dict[str, Any]:
    try:
        with open(PROFILES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_profiles(profiles: Dict[str, Any]):
    os.makedirs(os.path.dirname(PROFILES_FILE), exist_ok=True)
    with _PROFILES_LOCK:
        with open(PROFILES_FILE, "w") as f:
            json.dump(profiles, f, indent=2, default=str)


def _ensure_profile(profiles: Dict, user_id: str) -> Dict:
    if user_id not in profiles:
        profiles[user_id] = {
            "xp": 0,
            "games_completed": 0,
            "game_types_played": [],
            "debates_completed": 0,
            "negotiations_completed": 0,
            "highest_score": 0,
            "badges_earned": [],
            "card_bank": [],  # [{game_id, game_title, card_id, name, icon, rarity, knowledge, collected_at}]
            "daily_completions": {},  # {date_str: count}
            "history": [],  # recent activity
            "psychological_scores": {},  # {skill_id: {total, count, latest, name, icon}}
            "created_at": datetime.now().isoformat(),
            "avatar_url": "",
            "avatar_frame": "default",
            "avatar_outfit": "none",
            "quit_history": [],  # [{game_id, round, timestamp}]
        }
    # Backfill new fields on existing profiles
    p = profiles[user_id]
    if "avatar_url" not in p:
        p["avatar_url"] = ""
    if "avatar_frame" not in p:
        p["avatar_frame"] = "default"
    if "avatar_outfit" not in p:
        p["avatar_outfit"] = "none"
    if "quit_history" not in p:
        p["quit_history"] = []
    if "xp" not in p:
        p["xp"] = 0
    if "games_completed" not in p:
        p["games_completed"] = 0
    if "game_types_played" not in p:
        p["game_types_played"] = []
    if "debates_completed" not in p:
        p["debates_completed"] = 0
    if "negotiations_completed" not in p:
        p["negotiations_completed"] = 0
    if "highest_score" not in p:
        p["highest_score"] = 0
    if "badges_earned" not in p:
        p["badges_earned"] = []
    if "card_bank" not in p:
        p["card_bank"] = []
    if "daily_completions" not in p:
        p["daily_completions"] = {}
    if "history" not in p:
        p["history"] = []
    if "psychological_scores" not in p:
        p["psychological_scores"] = {}
    # Wellbeing fields (Round 15)
    if "wellbeing_consent" not in p:
        p["wellbeing_consent"] = None
    if "wellbeing_consent_at" not in p:
        p["wellbeing_consent_at"] = None
    if "wellbeing_consent_version" not in p:
        p["wellbeing_consent_version"] = None
    if "wellbeing_consent_minor" not in p:
        p["wellbeing_consent_minor"] = False
    if "wellbeing_checks" not in p:
        p["wellbeing_checks"] = []
    if "streak_shield_count" not in p:
        p["streak_shield_count"] = 0
    if "streak_shield_used_dates" not in p:
        p["streak_shield_used_dates"] = []
    if "institution" not in p:
        p["institution"] = ""
    if "profile_setup_complete" not in p:
        p["profile_setup_complete"] = False
    if "baseline_complete" not in p:
        p["baseline_complete"] = False  # explicit default; gate condition uses == False (rejects None)
    if "skills_introduced" not in p:
        p["skills_introduced"] = []  # list of skill IDs already shown to the user
    return profiles[user_id]


def mark_skills_introduced(user_id: str, skill_ids: List[str]) -> List[str]:
    """Mark skills as introduced for a user. Returns list of newly introduced skill IDs."""
    if not skill_ids:
        return []
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    existing = set(p.get("skills_introduced", []))
    new_skills = [s for s in skill_ids if s not in existing]
    if new_skills:
        p["skills_introduced"] = list(existing | set(new_skills))
        _save_profiles(profiles)
    return new_skills


def get_skills_introduced(user_id: str) -> List[str]:
    """Return list of skill IDs already introduced to the user."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    return p.get("skills_introduced", [])


def save_card_to_bank(user_id: str, card_data: Dict[str, Any]) -> Dict:
    """Persist a collected card to the user's permanent card bank (no duplicates per game+card_id)."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    bank = p.setdefault("card_bank", [])
    already = any(
        c.get("game_id") == card_data.get("game_id") and c.get("card_id") == card_data.get("card_id")
        for c in bank
    )
    if not already:
        bank.append({**card_data, "collected_at": datetime.now().isoformat()})
        _save_profiles(profiles)
    return p


def get_card_bank(user_id: str) -> List[Dict]:
    """Return all cards in the user's permanent card bank."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    return p.get("card_bank", [])


def get_experience_tier(profile: Dict) -> Dict:
    """Return experience tier info based on games_completed."""
    n = profile.get("games_completed", 0)
    if n < 4:
        return {"tier": 0, "name": "Explorer",    "next_at": 4,  "next_name": "Learner",     "games_completed": n}
    if n < 10:
        return {"tier": 1, "name": "Learner",     "next_at": 10, "next_name": "Competitor",  "games_completed": n}
    return     {"tier": 2, "name": "Competitor",  "next_at": None, "next_name": None,         "games_completed": n}


def _load_unlock_rules() -> Dict:
    try:
        with open(UNLOCK_RULES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"always_unlocked": [], "rules": []}


def check_unlocks(user_id: str, retroactive: bool = False) -> Dict:
    """
    Evaluate unlock rules for a user.
    Returns {
        unlocked_types: list,
        unlocked_game_ids: list,
        locked: [{type_or_id, hint, rule_type}]
    }

    Args:
        user_id: The user to evaluate.
        retroactive: When True, iterates ALL games in unlock_rules and ensures
                     every newly-qualified game/type is added to the cached unlocks
                     list (not just games that just triggered). Useful to call after
                     awarding XP to ensure the unlock state is fully consistent.
    """
    rules_data = _load_unlock_rules()
    # Backward compat: always_unlocked may still be a list of game types
    always_unlocked = set(rules_data.get("always_unlocked", []))
    # New: always_unlocked_game_ids — specific game IDs always accessible
    always_unlocked_game_ids = set(rules_data.get("always_unlocked_game_ids", []))
    # New: baseline_unlocks — game types unlocked once baseline is complete
    baseline_unlocks_config = rules_data.get("baseline_unlocks", {})
    rules = rules_data.get("rules", [])

    profiles = _load_profiles()
    p = profiles.get(user_id, {})
    games_completed = p.get("games_completed", 0)
    game_type_counts = p.get("game_type_counts", {})
    dimension_scores = p.get("dimension_scores", {})
    baseline_complete = p.get("baseline_complete", False)

    unlocked_types = set(always_unlocked)
    unlocked_game_ids = set(always_unlocked_game_ids)
    locked = []

    # Baseline unlocks: if the user has completed the baseline assessment,
    # all game types listed in baseline_unlocks.unlocks_game_types are unlocked.
    if baseline_complete and baseline_unlocks_config:
        for gtype in baseline_unlocks_config.get("unlocks_game_types", []):
            unlocked_types.add(gtype)

    for rule in rules:
        req = rule.get("requires", {})
        hint = rule.get("hint", "")
        satisfied = False

        if "baseline_complete" in req:
            satisfied = baseline_complete == req["baseline_complete"]
        elif "games_completed" in req:
            satisfied = games_completed >= req["games_completed"]
        elif "game_type" in req and "count" in req:
            satisfied = game_type_counts.get(req["game_type"], 0) >= req["count"]
        elif "dimension" in req and "min" in req:
            satisfied = dimension_scores.get(req["dimension"], 0) >= req["min"]

        if "unlocks_game_type" in rule:
            if satisfied:
                unlocked_types.add(rule["unlocks_game_type"])
            else:
                locked.append({"game_type": rule["unlocks_game_type"], "hint": hint})
        elif "unlocks_game_id" in rule:
            if satisfied:
                unlocked_game_ids.add(rule["unlocks_game_id"])
            else:
                locked.append({"game_id": rule["unlocks_game_id"], "hint": hint})

    result = {
        "unlocked_types": list(unlocked_types),
        "unlocked_game_ids": list(unlocked_game_ids),
        "locked": locked,
    }

    if retroactive:
        # Persist the fully-evaluated unlock state back into the profile cache
        # so every qualified game is recognised, even if not triggered in this session.
        profiles = _load_profiles()
        p = _ensure_profile(profiles, user_id)
        p["_cached_unlocks"] = result
        _save_profiles(profiles)

    return result


def award_streak_shield(user_id: str, count: int = 1) -> Dict:
    """Award streak shield(s) to a user (earned by completing bonus challenges or milestones)."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    p["streak_shield_count"] = p.get("streak_shield_count", 0) + count
    _save_profiles(profiles)
    return {"streak_shield_count": p["streak_shield_count"]}


def use_streak_shield(user_id: str) -> Dict:
    """Use one streak shield to protect a broken streak. Returns success/fail."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    shields = p.get("streak_shield_count", 0)
    if shields <= 0:
        return {"ok": False, "reason": "No shields available", "streak_shield_count": 0}
    from datetime import datetime, date
    today = date.today().isoformat()
    used_dates = p.get("streak_shield_used_dates", [])
    if today in used_dates:
        return {"ok": False, "reason": "Shield already used today", "streak_shield_count": shields}
    p["streak_shield_count"] = shields - 1
    used_dates.append(today)
    p["streak_shield_used_dates"] = used_dates[-30:]  # keep last 30 entries
    # Restore streak: add 1 to streak_days if it dropped to 0 from yesterday
    if p.get("streak_days", 0) == 0:
        p["streak_days"] = 1
    _save_profiles(profiles)
    return {"ok": True, "streak_shield_count": p["streak_shield_count"], "streak_days": p["streak_days"]}


def get_profile(user_id: str) -> Dict[str, Any]:
    """Get full player profile."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    level_info = xp_progress(p["xp"])
    bio = p.get("bio", {})
    tier_info = get_experience_tier(p)
    return {
        **level_info,
        "games_completed": p["games_completed"],
        "game_types_played": p["game_types_played"],
        "debates_completed": p["debates_completed"],
        "negotiations_completed": p["negotiations_completed"],
        "highest_score": p["highest_score"],
        "badges_earned": p["badges_earned"],
        "recent_activity": p.get("history", [])[-10:],
        "display_name": p.get("display_name", ""),
        "avatar": p.get("avatar", ""),
        "first_name": bio.get("first_name", ""),
        "last_name": bio.get("last_name", ""),
        "email": bio.get("email", ""),
        "school": bio.get("school", ""),
        "age": bio.get("age", ""),
        "gender": bio.get("gender", ""),
        "location": bio.get("location", ""),
        "about": bio.get("about", ""),
        "social": bio.get("social", {}),
        "experience_tier": tier_info,
        "streak_days": p.get("streak_days", 0),
        "streak_shield_count": p.get("streak_shield_count", 0),
        "last_active_date": p.get("last_active_date", ""),
        "trait_profile": p.get("trait_profile", None),
        "dimension_scores": p.get("dimension_scores", {}),
        "baseline_scores": p.get("baseline_scores"),
        "baseline_completed_at": p.get("baseline_completed_at"),
        "avatar_url": p.get("avatar_url", ""),
        "avatar_frame": p.get("avatar_frame", "default"),
        "avatar_outfit": p.get("avatar_outfit", "none"),
        "psychological_scores": p.get("psychological_scores", {}),
        "dimension_history": p.get("dimension_history", [])[-10:],
        "average_dimensions": {
            dim: round(data["total"] / max(1, data["count"]), 1)
            for dim, data in p.get("psychological_scores", {}).items()
            if isinstance(data, dict) and "total" in data and "count" in data
        },
        "wellbeing_consent": p.get("wellbeing_consent"),
        "wellbeing_consent_at": p.get("wellbeing_consent_at"),
        "preferences": p.get("preferences", {}),
        # Onboarding / baseline lifecycle
        "profile_setup_complete": p.get("profile_setup_complete", False),
        "baseline_complete": p.get("baseline_complete", False),
        "baseline_skipped": p.get("baseline_skipped", False),
        "onboarding_complete": p.get("onboarding_complete", False),
        "institution": p.get("institution", ""),
        "persona": p.get("persona", {}),
        "game_history": p.get("history", []),
    }


def get_or_create_share_token(user_id: str) -> str:
    """Return a stable share token for the user's public report, creating one if needed."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    if not p.get("share_token"):
        p["share_token"] = secrets.token_hex(12)
        _save_profiles(profiles)
    return p["share_token"]


def get_profile_by_share_token(token: str) -> Optional[Dict[str, Any]]:
    """Look up a profile by its share token. Returns raw profile dict or None."""
    profiles = _load_profiles()
    for uid, p in profiles.items():
        if not isinstance(p, dict):
            continue
        if p.get("share_token") == token:
            return {"_user_id": uid, **p}
    return None


def store_baseline_scores(user_id: str, dimension_scores: Dict[str, Any]):
    """Store baseline scores the first time a user completes the baseline assessment."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    if not p.get("baseline_scores"):
        p["baseline_scores"] = {k: v for k, v in dimension_scores.items() if isinstance(v, (int, float))}
        p["baseline_completed_at"] = datetime.now().isoformat()
        _save_profiles(profiles)


def complete_baseline(user_id: str, dimension_scores: Dict[str, Any]):
    """Atomically store baseline scores, mark complete, and clear any skip flag."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    if not p.get("baseline_scores"):
        p["baseline_scores"] = {k: v for k, v in dimension_scores.items() if isinstance(v, (int, float))}
        p["baseline_completed_at"] = datetime.now().isoformat()
    p["baseline_complete"] = True
    p["baseline_skipped"] = False
    _save_profiles(profiles)


def save_trait_profile(user_id: str, trait_data: Dict[str, Any]):
    """Persist a personality trait profile for the user.

    Merges attribute_history across games (cumulative).
    """
    try:
        profiles = _load_profiles()
        p = _ensure_profile(profiles, user_id)
        existing = p.get("trait_profile", {})
        # Merge attribute history (cumulative)
        merged_history = dict(existing.get("attribute_history") or {})
        for attr, count in (trait_data.get("attribute_history") or {}).items():
            merged_history[attr] = merged_history.get(attr, 0) + count
        trait_data["attribute_history"] = merged_history
        trait_data["games_played"] = existing.get("games_played", 0) + 1
        p["trait_profile"] = trait_data
        _save_profiles(profiles)
    except Exception as e:
        print(f"[save_trait_profile] Error: {e}")


_DIM_META = {
    "strategic_thinking": {"name": "Strategic Thinking", "icon": "🧠"},
    "risk_tolerance": {"name": "Risk Tolerance", "icon": "🎲"},
    "delayed_gratification": {"name": "Delayed Gratification", "icon": "⏳"},
    "adaptability": {"name": "Adaptability", "icon": "🦎"},
    "resilience": {"name": "Resilience", "icon": "💪"},
    "empathy": {"name": "Empathy", "icon": "❤️"},
    "ethical_reasoning": {"name": "Ethical Reasoning", "icon": "⚖️"},
    "creativity": {"name": "Creativity", "icon": "✨"},
}


def update_dimension_scores(user_id: str, game_id: str, dimension_scores) -> None:
    """
    Accumulate normalized dimension scores from a completed game into the player profile.
    Accepts either:
      - a dict  {dim_name: score, ...}
      - a list  [{"name": dim_name, "value": score}, ...]  (output of normalize_dimension_scores)
    Stores running total/count per dimension so an average can be derived.
    """
    # Normalise input to a plain dict
    scores_dict: Dict[str, float] = {}
    if isinstance(dimension_scores, list):
        for d in dimension_scores:
            key = d.get("name", d.get("id", ""))
            val = d.get("value", 0)
            if key and isinstance(val, (int, float)):
                scores_dict[key] = val
    elif isinstance(dimension_scores, dict):
        scores_dict = {k: v for k, v in dimension_scores.items() if isinstance(v, (int, float))}
    else:
        return  # nothing usable

    if not scores_dict:
        return

    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)

    ps = p.setdefault("psychological_scores", {})

    for dim, score in scores_dict.items():
        if score <= 0:
            continue
        if dim not in ps:
            meta = _DIM_META.get(dim, {"name": dim.replace("_", " ").title(), "icon": "📊"})
            ps[dim] = {"total": 0, "count": 0, "latest": 0, **meta}
        ps[dim]["total"] = ps[dim].get("total", 0) + score
        ps[dim]["count"] = ps[dim].get("count", 0) + 1
        ps[dim]["latest"] = score

    # Dimension history (per-game snapshots for trend charts)
    dh = p.setdefault("dimension_history", [])
    dh.append({
        "game_id": game_id,
        "scores": scores_dict,
        "timestamp": datetime.now().isoformat(),
    })
    # Keep last 50 entries
    if len(dh) > 50:
        p["dimension_history"] = dh[-50:]

    _save_profiles(profiles)


def award_xp(user_id: str, xp_amount: int, reason: str, game_type: str = "rounds",
             game_title: str = "", score: int = 0,
             psychological_scores: Optional[Dict] = None,
             dimension_scores: Optional[Dict] = None,
             increment_game_count: bool = True) -> Dict[str, Any]:
    """
    Award XP and update profile stats. Returns XP change info + any new badges.
    Set increment_game_count=False for partial awards (e.g. chapter completions).
    """
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)

    # Ensure XP is always an integer (fix any legacy float contamination)
    p["xp"] = int(round(p.get("xp", 0)))
    xp_amount = int(round(xp_amount))
    old_level = get_level(p["xp"])
    p["xp"] += xp_amount
    new_level = get_level(p["xp"])
    if increment_game_count:
        p["games_completed"] += 1

    if game_type and game_type not in p["game_types_played"]:
        p["game_types_played"].append(game_type)

    # Track per-game-type completion counts
    gtc = p.setdefault("game_type_counts", {})
    if game_type:
        gtc[game_type] = gtc.get(game_type, 0) + 1

    if score > p["highest_score"]:
        p["highest_score"] = score

    # Track daily completions + streak
    today = datetime.now().strftime("%Y-%m-%d")
    daily = p.get("daily_completions", {})
    daily[today] = daily.get(today, 0) + 1
    p["daily_completions"] = daily

    # Calculate consecutive day streak
    streak = 1
    check_date = datetime.now()
    for i in range(1, 365):
        check_date_str = (check_date - __import__('datetime').timedelta(days=i)).strftime("%Y-%m-%d")
        if daily.get(check_date_str, 0) > 0:
            streak += 1
        else:
            break
    p["streak_days"] = streak
    p["last_active_date"] = today
    # Award streak shield at 7-day milestones
    if p.get("streak_days", 0) % 7 == 0 and p.get("streak_days", 0) > 0:
        p["streak_shield_count"] = p.get("streak_shield_count", 0) + 1

    # Add to history
    p.setdefault("history", []).append({
        "type": "game_complete",
        "game_title": game_title,
        "game_type": game_type,
        "xp_earned": xp_amount,
        "score": score,
        "timestamp": datetime.now().isoformat(),
    })
    # Keep last 50 entries
    p["history"] = p["history"][-50:]

    # Store psychological scores if provided
    if psychological_scores:
        existing = p.setdefault("psychological_scores", {})
        for skill_id, skill_data in psychological_scores.items():
            final_val = skill_data.get("final", 0) if isinstance(skill_data, dict) else skill_data
            name = skill_data.get("name", "") if isinstance(skill_data, dict) else ""
            icon = skill_data.get("icon", "") if isinstance(skill_data, dict) else ""
            if skill_id not in existing:
                existing[skill_id] = {"total": final_val, "count": 1, "latest": final_val, "name": name, "icon": icon}
            else:
                existing[skill_id]["total"] += final_val
                existing[skill_id]["count"] += 1
                existing[skill_id]["latest"] = final_val
                if name:
                    existing[skill_id]["name"] = name
                if icon:
                    existing[skill_id]["icon"] = icon

    # Track soft skill dimension history (longitudinal trend)
    if dimension_scores:
        skill_entry = {
            "timestamp": datetime.now().isoformat(),
            "game_type": game_type,
            "game_title": game_title,
            "scores": {k: v for k, v in dimension_scores.items() if isinstance(v, (int, float))},
        }
        p.setdefault("skill_history", []).append(skill_entry)
        p["skill_history"] = p["skill_history"][-200:]  # keep last 200 sessions
        # Also store latest dimension scores snapshot
        p["dimension_scores"] = {k: v for k, v in dimension_scores.items() if isinstance(v, (int, float))}

    # Check for new badges
    new_badges = _check_badges(p)

    # Check for skill-level micro-credential badges
    skill_level_badges = _check_skill_level_badges(p)
    for slb in skill_level_badges:
        if not any(b.get("id") == slb["id"] for b in p.get("badges_earned", [])):
            p.setdefault("badges_earned", []).append(slb)
            new_badges.append(slb)

    # Check for newly unlocked content (retroactive=True ensures all qualified games are captured)
    old_unlocks = p.get("_cached_unlocks", {})
    new_unlocks_data = check_unlocks(user_id, retroactive=True)
    newly_unlocked = []
    new_types = set(new_unlocks_data["unlocked_types"])
    new_ids = set(new_unlocks_data["unlocked_game_ids"])
    old_types = set(old_unlocks.get("unlocked_types", []))
    old_ids = set(old_unlocks.get("unlocked_game_ids", []))
    for t in new_types - old_types:
        newly_unlocked.append({"type": "game_type", "value": t})
    for gid in new_ids - old_ids:
        newly_unlocked.append({"type": "game_id", "value": gid})
    p["_cached_unlocks"] = new_unlocks_data

    _save_profiles(profiles)

    return {
        "xp_earned": xp_amount,
        "total_xp": p["xp"],
        "old_level": old_level,
        "new_level": new_level,
        "level_up": new_level > old_level,
        "new_badges": new_badges,
        "experience_tier": get_experience_tier(p),
        "newly_unlocked": newly_unlocked,
        "streak_days": p.get("streak_days", 0),
    }


def award_debate_xp(user_id: str, xp_amount: int, scenario_title: str = "") -> Dict:
    """Award XP specifically for debate completion."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    p["debates_completed"] = p.get("debates_completed", 0) + 1

    old_level = get_level(p["xp"])
    p["xp"] += xp_amount
    new_level = get_level(p["xp"])

    if "debate" not in p["game_types_played"]:
        p["game_types_played"].append("debate")

    p.setdefault("history", []).append({
        "type": "debate_complete",
        "game_title": scenario_title,
        "game_type": "debate",
        "xp_earned": xp_amount,
        "timestamp": datetime.now().isoformat(),
    })
    p["history"] = p["history"][-50:]

    new_badges = _check_badges(p)
    _save_profiles(profiles)

    return {
        "xp_earned": xp_amount,
        "total_xp": p["xp"],
        "level_up": new_level > old_level,
        "new_badges": new_badges,
    }


def mark_module_completed(user_id: str, module_id: str, xp_amount: int = 0) -> Dict:
    """Record a module completion and trigger badge checks.

    Idempotent: completing the same module twice doesn't double-count.
    Returns dict with newly-earned badges and any XP awarded.
    """
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    completed = p.setdefault("modules_completed", [])
    already = module_id in completed
    if not already:
        completed.append(module_id)
        if xp_amount:
            old_level = get_level(p.get("xp", 0))
            p["xp"] = p.get("xp", 0) + xp_amount
            new_level = get_level(p["xp"])
        else:
            old_level = new_level = get_level(p.get("xp", 0))
        p.setdefault("history", []).append({
            "type": "module_complete",
            "module_id": module_id,
            "xp_earned": xp_amount,
            "timestamp": datetime.now().isoformat(),
        })
        p["history"] = p["history"][-50:]
    else:
        old_level = new_level = get_level(p.get("xp", 0))

    new_badges = _check_badges(p)
    _save_profiles(profiles)
    return {
        "already_completed": already,
        "new_badges": new_badges,
        "xp_earned": 0 if already else xp_amount,
        "level_up": new_level > old_level,
    }


def award_negotiation_xp(user_id: str, xp_amount: int, scenario_title: str = "") -> Dict:
    """Award XP for negotiation completion."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    p["negotiations_completed"] = p.get("negotiations_completed", 0) + 1

    old_level = get_level(p["xp"])
    p["xp"] += xp_amount
    new_level = get_level(p["xp"])

    if "negotiation" not in p["game_types_played"]:
        p["game_types_played"].append("negotiation")

    p.setdefault("history", []).append({
        "type": "negotiation_complete",
        "game_title": scenario_title,
        "game_type": "negotiation",
        "xp_earned": xp_amount,
        "timestamp": datetime.now().isoformat(),
    })
    p["history"] = p["history"][-50:]

    new_badges = _check_badges(p)
    _save_profiles(profiles)

    return {
        "xp_earned": xp_amount,
        "total_xp": p["xp"],
        "level_up": new_level > old_level,
        "new_badges": new_badges,
    }


def _get_achievement_progress(profile: Dict, cond: Dict) -> tuple:
    """Return (current_value, target_value) for an achievement condition."""
    ctype = cond["type"]
    target = cond.get("value", 1)

    if ctype == "games_completed":
        return profile.get("games_completed", 0), target
    elif ctype == "game_types_played":
        return len(profile.get("game_types_played", [])), target
    elif ctype == "debates_completed":
        return profile.get("debates_completed", 0), target
    elif ctype == "negotiations_completed":
        return profile.get("negotiations_completed", 0), target
    elif ctype == "high_score":
        return profile.get("highest_score", 0), target
    elif ctype == "level":
        return get_level(profile.get("xp", 0)), target
    elif ctype == "daily_games":
        today = datetime.now().strftime("%Y-%m-%d")
        return profile.get("daily_completions", {}).get(today, 0), target
    elif ctype == "game_type_count":
        gt = cond.get("game_type", "")
        history = profile.get("history", [])
        count = sum(1 for h in history if h.get("game_type") == gt and h.get("type") in ("game_complete",))
        # Also check from game_type_counts if tracked
        counts = profile.get("game_type_counts", {})
        return max(count, counts.get(gt, 0)), target
    elif ctype == "avg_score":
        history = profile.get("history", [])
        scores = [h["score"] for h in history if h.get("score", 0) > 0]
        avg = sum(scores) / max(1, len(scores)) if scores else 0
        return round(avg), target
    elif ctype == "login_streak":
        return profile.get("login_streak", 0), target
    elif ctype == "skills_unlocked":
        psych = profile.get("psychological_scores", {})
        unlocked = sum(1 for s in psych.values() if isinstance(s, dict) and s.get("count", 0) >= 1)
        return unlocked, target
    elif ctype == "specific_skill":
        skill_id = cond.get("skill_id", "")
        psych = profile.get("psychological_scores", {})
        skill = psych.get(skill_id, {})
        has_it = 1 if isinstance(skill, dict) and skill.get("count", 0) >= 3 else 0
        return has_it, 1
    elif ctype == "coins_total":
        return profile.get("coins_earned_total", 0), target
    elif ctype == "coins_spent":
        return profile.get("coins_spent_total", 0), target
    elif ctype == "module_completed":
        # Specific module completion (e.g. "mento_entrepreneur_4week")
        mid = cond.get("module_id", "")
        completed = profile.get("modules_completed", [])
        has_it = 1 if mid and mid in completed else 0
        return has_it, 1
    elif ctype == "modules_completed_count":
        return len(profile.get("modules_completed", [])), target
    return 0, target


def _check_badges(profile: Dict) -> List[Dict]:
    """Check and award any newly earned badges. Returns list of newly earned badges."""
    achievements, _ = _load_achievements()
    earned_ids = set(b["id"] for b in profile.get("badges_earned", []))
    new_badges = []

    for badge in achievements:
        if badge["id"] in earned_ids:
            continue

        current, target = _get_achievement_progress(profile, badge["condition"])
        if current >= target:
            badge_entry = {
                "id": badge["id"],
                "name": badge["name"],
                "icon": badge["icon"],
                "rarity": badge.get("rarity", "common"),
                "earned_at": datetime.now().isoformat(),
            }
            profile.setdefault("badges_earned", []).append(badge_entry)
            new_badges.append(badge_entry)

            # Award bonus XP if configured
            xp_reward = badge.get("xp_reward", 0)
            if xp_reward > 0:
                profile["xp"] = profile.get("xp", 0) + xp_reward

    return new_badges


def update_profile(user_id: str, **kwargs) -> Dict[str, Any]:
    """Update editable profile fields."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)

    if "display_name" in kwargs and kwargs["display_name"] is not None:
        p["display_name"] = str(kwargs["display_name"]).strip()[:50]
    if "avatar" in kwargs and kwargs["avatar"] is not None:
        p["avatar"] = str(kwargs["avatar"]).strip()[:10]
    if "avatar_url" in kwargs and kwargs["avatar_url"] is not None:
        p["avatar_url"] = str(kwargs["avatar_url"]).strip()[:200]
    if "avatar_frame" in kwargs and kwargs["avatar_frame"] is not None:
        valid_frames = ("default", "gold", "rainbow", "dark", "neon", "minimal")
        p["avatar_frame"] = kwargs["avatar_frame"] if kwargs["avatar_frame"] in valid_frames else "default"
    if "avatar_outfit" in kwargs and kwargs["avatar_outfit"] is not None:
        p["avatar_outfit"] = str(kwargs["avatar_outfit"]).strip()[:30]

    # Bio/personal info stored in nested dict
    bio = p.setdefault("bio", {})
    BIO_FIELDS = {
        "first_name": 50, "last_name": 50, "email": 100,
        "school": 100, "age": 3, "gender": 20,
        "location": 100, "about": 500,
    }
    for field, max_len in BIO_FIELDS.items():
        if field in kwargs and kwargs[field] is not None:
            bio[field] = str(kwargs[field]).strip()[:max_len]

    # Social accounts as dict
    if "social" in kwargs and isinstance(kwargs.get("social"), dict):
        bio["social"] = {
            k: str(v).strip()[:100]
            for k, v in kwargs["social"].items()
            if k in ("instagram", "twitter", "linkedin", "youtube", "github", "website")
        }

    # Onboarding / baseline lifecycle flags
    if "onboarding_complete" in kwargs and kwargs["onboarding_complete"] is not None:
        p["onboarding_complete"] = bool(kwargs["onboarding_complete"])
    if "baseline_skipped" in kwargs and kwargs["baseline_skipped"] is not None:
        p["baseline_skipped"] = bool(kwargs["baseline_skipped"])

    # Free-form notification/UX preferences (toggles like module_daily_dispatch)
    if "preferences" in kwargs and isinstance(kwargs.get("preferences"), dict):
        prefs = p.setdefault("preferences", {})
        # Only accept boolean / scalar values to keep this dict bounded.
        for k, v in kwargs["preferences"].items():
            if not isinstance(k, str) or len(k) > 64:
                continue
            if v is None or isinstance(v, (bool, int, float, str)):
                prefs[k] = v

    _save_profiles(profiles)
    return {"ok": True}


_SKILL_LEVEL_META = {
    "strategic_thinking":    {"icon": "🧠", "label": "Strategist"},
    "risk_tolerance":        {"icon": "🎯", "label": "Risk Taker"},
    "delayed_gratification": {"icon": "⏳", "label": "Patient Thinker"},
    "adaptability":          {"icon": "🔄", "label": "Adapter"},
    "resilience":            {"icon": "💪", "label": "Resilient"},
    "empathy":               {"icon": "❤️",  "label": "Empath"},
    "ethical_reasoning":     {"icon": "⚖️",  "label": "Ethicist"},
    "creativity":            {"icon": "🎨", "label": "Creative"},
}


def _check_skill_level_badges(p: Dict) -> List[Dict]:
    """Check if any dimension qualifies for a Level 2 (avg ≥ 70, 3+ games) or Level 3 (avg ≥ 85, 5+ games) badge."""
    earned_ids = {b.get("id") for b in p.get("badges_earned", [])}
    new_badges = []
    psych_scores = p.get("psychological_scores", {})
    for dim, meta in _SKILL_LEVEL_META.items():
        data = psych_scores.get(dim)
        if not data:
            continue
        count = data.get("count", 0)
        avg = data.get("total", 0) / count if count > 0 else 0
        label = meta["label"]
        icon = meta["icon"]
        # Level 3 — Master (avg ≥ 85, 5+ games)
        badge_id_3 = f"{dim}_level_3"
        if count >= 5 and avg >= 85 and badge_id_3 not in earned_ids:
            new_badges.append({
                "id": badge_id_3,
                "name": f"Master {label}",
                "description": f"Achieved {label} mastery across 5+ games (avg ≥ 85)",
                "icon": icon,
                "rarity": "legendary",
                "category": "skill_level",
                "earned_at": datetime.now().isoformat(),
            })
        # Level 2 — Advanced (avg ≥ 70, 3+ games)
        badge_id_2 = f"{dim}_level_2"
        if count >= 3 and avg >= 70 and badge_id_2 not in earned_ids:
            new_badges.append({
                "id": badge_id_2,
                "name": f"Advanced {label}",
                "description": f"Demonstrated strong {label} skills across 3+ games (avg ≥ 70)",
                "icon": icon,
                "rarity": "epic",
                "category": "skill_level",
                "earned_at": datetime.now().isoformat(),
            })
    return new_badges


def log_quit(user_id: str, game_id: str, run_id: str = "", round_number: int = 0, reason: str = "") -> Dict:
    """Log a quit event and return frustration info if threshold hit."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    quit_history = p.setdefault("quit_history", [])
    quit_history.append({
        "game_id": game_id,
        "run_id": run_id,
        "round": round_number,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    })
    # Keep last 50 quit events
    p["quit_history"] = quit_history[-50:]
    _save_profiles(profiles)

    # Count quits of same game in last 7 days
    cutoff = datetime.now().timestamp() - 7 * 86400
    recent_quits = [
        q for q in p["quit_history"]
        if q["game_id"] == game_id and
        datetime.fromisoformat(q["timestamp"]).timestamp() > cutoff
    ]
    quit_count = len(recent_quits)
    result = {"quit_count": quit_count, "support_message": None, "suggest_easier": False}
    if quit_count >= 3:
        result["support_message"] = (
            f"You've tried this game {quit_count} times — it might be challenging right now. "
            "Consider revisiting the tutorial or trying a related game first."
        )
        result["suggest_easier"] = True
    return result


def get_frustration_check(user_id: str, game_id: str) -> Dict:
    """Return frustration data before a game starts."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    cutoff = datetime.now().timestamp() - 7 * 86400
    recent_quits = [
        q for q in p.get("quit_history", [])
        if q["game_id"] == game_id and
        datetime.fromisoformat(q["timestamp"]).timestamp() > cutoff
    ]
    quit_count = len(recent_quits)
    result = {"quit_count": quit_count, "support_message": None, "suggest_easier": False}
    if quit_count >= 3:
        result["support_message"] = (
            f"You've attempted this game {quit_count} times recently. "
            "Here's a tip: focus on the coaching moments after each choice — they'll guide your strategy."
        )
        result["suggest_easier"] = True
    return result


def get_all_badges() -> List[Dict]:
    """Return all possible badges with definitions."""
    achievements, _ = _load_achievements()
    return achievements


def get_achievements_with_progress(user_id: str) -> Dict:
    """Return all achievements with progress info for a user."""
    achievements, categories = _load_achievements()
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    earned_ids = set(b["id"] for b in p.get("badges_earned", []))
    earned_map = {b["id"]: b for b in p.get("badges_earned", [])}

    result = []
    for a in achievements:
        current, target = _get_achievement_progress(p, a["condition"])
        is_earned = a["id"] in earned_ids
        is_secret = a.get("secret", False)

        entry = {
            "id": a["id"],
            "name": "???" if is_secret and not is_earned else a["name"],
            "description": "This achievement is hidden..." if is_secret and not is_earned else a["description"],
            "icon": "❓" if is_secret and not is_earned else a["icon"],
            "rarity": a.get("rarity", "common"),
            "category": a.get("category", "milestones"),
            "earned": is_earned,
            "earned_at": earned_map[a["id"]].get("earned_at") if is_earned else None,
            "progress": min(current, target),
            "target": target,
            "progress_pct": min(100, round((current / max(1, target)) * 100)),
            "secret": is_secret,
            "xp_reward": a.get("xp_reward", 0),
        }
        result.append(entry)

    return {
        "badges": result,
        "earned_count": len(earned_ids),
        "total_count": len(achievements),
        "secret_count": sum(1 for a in achievements if a.get("secret")),
        "categories": categories,
    }


def get_global_xp_leaderboard(limit: int = 20) -> List[Dict]:
    """Get top players by XP."""
    profiles = _load_profiles()
    entries = []
    for user_id, p in profiles.items():
        if not isinstance(p, dict):
            continue  # skip metadata keys like last_accessed
        entries.append({
            "user_id": user_id,
            "xp": p.get("xp", 0),
            "level": get_level(p.get("xp", 0)),
            "games_completed": p.get("games_completed", 0),
            "badges_count": len(p.get("badges_earned", [])),
        })
    entries.sort(key=lambda x: x["xp"], reverse=True)
    return entries[:limit]


def get_skill_history(user_id: str) -> Dict:
    """Return timestamped dimension score history for trend charts."""
    profiles = _load_profiles()
    p = profiles.get(user_id, {})
    return {
        "skill_history": p.get("skill_history", []),
        "latest_scores": p.get("dimension_scores", {}),
    }


def get_skill_goals(user_id: str) -> Dict:
    """Return skill goals for a user."""
    profiles = _load_profiles()
    p = profiles.get(user_id, {})
    return {"goals": p.get("skill_goals", {})}


def set_skill_goals(user_id: str, goals: Dict) -> Dict:
    """Set or update skill goals. goals = {dimension: {target, deadline_optional}}"""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    existing = p.get("skill_goals", {})
    for dim, goal in goals.items():
        if goal is None:
            existing.pop(dim, None)
        else:
            existing[dim] = {
                "target": int(goal.get("target", 70)),
                "deadline": goal.get("deadline"),
                "set_at": datetime.now().isoformat(),
                "baseline": p.get("dimension_scores", {}).get(dim, 0),
            }
    p["skill_goals"] = existing
    _save_profiles(profiles)
    return {"goals": existing}


def get_certificate_eligibility(user_id: str) -> list:
    """Return earned certificates (games completed with strong dimension scores)."""
    profiles = _load_profiles()
    p = profiles.get(user_id, {})
    certs = p.get("certificates", [])
    return certs


def get_adaptive_summary(user_id: str) -> Dict:
    """
    Returns a cross-session adaptive profile for personalised difficulty.
    Reads the last 10 skill_history entries and computes per-dimension averages + trend.

    Returns:
        {
            "avg_scores": {dimension: avg_score (0-100)},
            "trend": {dimension: "+" | "-" | "~"},
            "games_completed": int,
            "has_history": bool
        }
    """
    DIMS = ["strategic_thinking", "risk_tolerance", "delayed_gratification",
            "adaptability", "resilience", "empathy"]
    profiles = _load_profiles()
    p = profiles.get(user_id, {})
    history = p.get("skill_history", [])[-10:]  # last 10 entries
    if not history:
        return {"avg_scores": {}, "trend": {}, "games_completed": p.get("games_completed", 0), "has_history": False}

    # Compute per-dimension averages
    sums: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    for entry in history:
        for dim in DIMS:
            val = entry.get(dim) or entry.get("scores", {}).get(dim)
            if val is not None:
                sums[dim] = sums.get(dim, 0) + float(val)
                counts[dim] = counts.get(dim, 0) + 1

    avg_scores = {d: round(sums[d] / counts[d]) for d in sums if counts.get(d, 0) > 0}

    # Compute trend: compare last 3 vs previous 3-7 entries
    trend: Dict[str, str] = {}
    if len(history) >= 6:
        recent = history[-3:]
        older = history[-6:-3]
        for dim in avg_scores:
            r_vals = [e.get(dim) or e.get("scores", {}).get(dim, 0) for e in recent]
            o_vals = [e.get(dim) or e.get("scores", {}).get(dim, 0) for e in older]
            r_avg = sum(r_vals) / len(r_vals) if r_vals else 0
            o_avg = sum(o_vals) / len(o_vals) if o_vals else 0
            diff = r_avg - o_avg
            trend[dim] = "+" if diff > 3 else "-" if diff < -3 else "~"

    return {
        "avg_scores": avg_scores,
        "trend": trend,
        "games_completed": p.get("games_completed", 0),
        "has_history": bool(avg_scores),
    }


def award_certificate(user_id: str, cert_id: str, game_title: str, skills: list) -> Dict:
    """Award a certificate to the user if not already earned."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    certs = p.setdefault("certificates", [])
    already = any(c.get("id") == cert_id for c in certs)
    if already:
        return {"already_earned": True, "cert_id": cert_id}
    cert = {
        "id": cert_id,
        "game_title": game_title,
        "skills": skills,
        "earned_at": datetime.now().isoformat(),
    }
    certs.append(cert)
    _save_profiles(profiles)
    return {"awarded": True, "certificate": cert}


# ── Round 15: Behavioral Intelligence ──────────────────────────────────────

def compute_decision_speed_profile(choice_history: list) -> dict:
    """
    Analyse time_to_decide_ms across a choice history to produce a speed profile.
    Returns dict with mean, median, std, CV, deceleration_ratio, etc.
    """
    times = [
        c["time_to_decide_ms"] for c in choice_history
        if isinstance(c.get("time_to_decide_ms"), (int, float)) and c["time_to_decide_ms"] > 100
    ]
    if len(times) < 3:
        return {"insufficient_data": True}
    avg = mean(times)
    sd = stdev(times) if len(times) > 1 else 0.0
    mid = len(times) // 2
    early_avg = mean(times[:mid]) if times[:mid] else avg
    late_avg = mean(times[mid:]) if times[mid:] else avg
    return {
        "mean_ms": round(avg),
        "median_ms": round(median(times)),
        "std_ms": round(sd),
        "cv": round(sd / avg, 3) if avg > 0 else 0,
        "fastest_ms": min(times),
        "slowest_ms": max(times),
        "early_avg_ms": round(early_avg),
        "late_avg_ms": round(late_avg),
        "deceleration_ratio": round(late_avg / early_avg, 2) if early_avg > 0 else 1.0,
        "n": len(times),
    }


_ARCHETYPES = [
    ("Bold Strategist",    "⚔️",  "Takes decisive risks with clear strategic intent.",
     lambda d: d.get("risk_tolerance", 0) > 70 and d.get("strategic_thinking", 0) > 65),
    ("Careful Planner",    "♟️",  "Thinks several steps ahead before committing.",
     lambda d: d.get("strategic_thinking", 0) > 70 and d.get("risk_tolerance", 0) < 45),
    ("Empathetic Leader",  "🤝",  "Leads through understanding and genuine connection.",
     lambda d: d.get("empathy", 0) > 70 and d.get("adaptability", 0) > 60),
    ("Resilient Achiever", "💪",  "Bounces back stronger from every setback.",
     lambda d: d.get("resilience", 0) > 70 and d.get("delayed_gratification", 0) > 60),
    ("Adaptable Explorer", "🧭",  "Thrives in change and ambiguity.",
     lambda d: d.get("adaptability", 0) > 70),
    ("Ethical Thinker",    "⚖️",  "Consistently prioritises integrity in decisions.",
     lambda d: d.get("ethical_reasoning", 0) > 70),
    ("Balanced Leader",    "👑",  "Demonstrates strength across all skill dimensions.",
     lambda d: all(v > 55 for v in d.values() if isinstance(v, (int, float)))),
    ("Growth Learner",     "🌱",  "Building skills and resilience session by session.",
     lambda d: True),  # fallback
]


def _linear_slope(vals: list) -> float:
    """Simple linear trend (no numpy). Returns slope per session."""
    n = len(vals)
    if n < 2:
        return 0.0
    xm = (n - 1) / 2
    ym = mean(vals)
    num = sum((i - xm) * (v - ym) for i, v in enumerate(vals))
    den = sum((i - xm) ** 2 for i in range(n))
    return num / den if den else 0.0


def compute_behavioral_signature(user_id: str) -> dict:
    """
    Compute cross-session archetype, consistency score, and growth trajectory.
    Requires at least 3 sessions in skill_history.
    """
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    history = p.get("skill_history", [])
    if len(history) < 3:
        return {"insufficient_data": True, "sessions_needed": max(0, 3 - len(history))}

    recent = history[-10:]
    dims = [
        "strategic_thinking", "risk_tolerance", "delayed_gratification",
        "adaptability", "resilience", "empathy", "ethical_reasoning", "creativity",
    ]
    dim_series = {d: [s.get("scores", {}).get(d, 0) for s in recent] for d in dims}
    avg_scores = {d: round(mean(v)) for d, v in dim_series.items() if v}

    # Consistency: 1 - mean(CV per dimension)
    cvs = []
    for d, vals in dim_series.items():
        if len(vals) > 1 and mean(vals) > 0:
            cvs.append(stdev(vals) / mean(vals))
    consistency = round((1 - min(1.0, mean(cvs) if cvs else 0.0)) * 100)

    # Trajectory per dimension
    trajectories = {d: _linear_slope(v) for d, v in dim_series.items() if v}
    improving = [d for d, t in trajectories.items() if t > 0.5]
    declining = [d for d, t in trajectories.items() if t < -0.5]
    overall_traj = (
        "improving" if len(improving) >= 4 else
        "declining" if len(declining) >= 4 else
        "stable"
    )

    # Match archetype
    archetype_name = archetype_icon = archetype_desc = None
    for name, icon, desc, cond in _ARCHETYPES:
        if cond(avg_scores):
            archetype_name, archetype_icon, archetype_desc = name, icon, desc
            break

    return {
        "archetype": archetype_name,
        "archetype_icon": archetype_icon,
        "archetype_description": archetype_desc,
        "consistency_score": consistency,
        "overall_trajectory": overall_traj,
        "improving_dimensions": improving,
        "declining_dimensions": declining,
        "avg_scores": avg_scores,
        "sessions_analyzed": len(recent),
        "dominant_dimension": max(avg_scores, key=avg_scores.get) if avg_scores else None,
    }


def store_wellbeing_check(user_id: str, check_data: dict):
    """Store a PHQ-9 / GAD-7 / DASS-21 survey result for the user."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    checks = p.setdefault("wellbeing_checks", [])
    checks.append({
        "survey": check_data.get("survey", "unknown"),
        "raw_score": check_data.get("raw_score", 0),
        "severity": check_data.get("severity", "minimal"),
        "timestamp": check_data.get("timestamp", datetime.now().isoformat()),
    })
    # Keep last 50 checks
    p["wellbeing_checks"] = checks[-50:]
    _save_profiles(profiles)


def update_wellbeing_consent(user_id: str, action: str, minor: bool = False):
    """Update wellbeing consent: action = 'given' | 'withdrawn'."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    p["wellbeing_consent"] = action
    p["wellbeing_consent_at"] = datetime.now().isoformat()
    p["wellbeing_consent_version"] = "1.0"
    p["wellbeing_consent_minor"] = minor
    _save_profiles(profiles)


def get_wellbeing_history(user_id: str) -> dict:
    """Return wellbeing check history for the user."""
    profiles = _load_profiles()
    p = profiles.get(user_id, {})
    return {
        "wellbeing_checks": p.get("wellbeing_checks", []),
        "wellbeing_consent": p.get("wellbeing_consent"),
    }


def delete_wellbeing_data(user_id: str):
    """Erase all wellbeing data for DPDP right-to-erasure compliance."""
    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    p["wellbeing_checks"] = []
    p["wellbeing_consent"] = None
    p["wellbeing_consent_at"] = None
    p["wellbeing_consent_version"] = None
    p["wellbeing_consent_minor"] = False
    _save_profiles(profiles)


# ─── NEP 2020 Progression Tracking ─────────────────────────────────────────

_NEP_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "nep_competency_levels.json")
_NEP_CONFIG = None

def _load_nep_config():
    global _NEP_CONFIG
    if _NEP_CONFIG is None:
        try:
            with open(_NEP_CONFIG_FILE) as f:
                _NEP_CONFIG = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _NEP_CONFIG = {"competencies": {}, "dimension_to_nep_map": {}}
    return _NEP_CONFIG


def _get_nep_level(competency_config, score):
    """Return the highest level achieved for a given score."""
    levels = competency_config.get("levels", [])
    achieved = levels[0] if levels else {"level": 1, "name": "Beginner"}
    for lvl in levels:
        if score >= lvl["min_score"]:
            achieved = lvl
    return achieved


def update_nep_progression(user_id: str, game_id: str, dimension_scores: dict) -> None:
    """Update NEP competency progression based on dimension scores from a completed game."""
    config = _load_nep_config()
    dim_to_nep = config.get("dimension_to_nep_map", {})
    competencies = config.get("competencies", {})

    if not dimension_scores or not dim_to_nep:
        return

    # Map dimension scores to NEP competencies
    nep_scores = {}
    for dim, score in dimension_scores.items():
        if not isinstance(score, (int, float)) or score <= 0:
            continue
        mapped_comps = dim_to_nep.get(dim, [])
        for comp in mapped_comps:
            if comp in competencies:
                if comp not in nep_scores:
                    nep_scores[comp] = []
                nep_scores[comp].append(score)

    if not nep_scores:
        return

    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    nep = p.setdefault("nep_progression", {})

    for comp_id, scores in nep_scores.items():
        avg_score = sum(scores) / len(scores)
        entry = nep.setdefault(comp_id, {
            "score": 0, "games_contributed": [], "level": 1,
            "level_name": "Observer", "last_updated": None,
        })
        # Running average: blend old score with new (weighted toward recent)
        old_score = entry.get("score", 0)
        old_count = len(entry.get("games_contributed", []))
        if old_count > 0:
            entry["score"] = round((old_score * old_count + avg_score) / (old_count + 1), 1)
        else:
            entry["score"] = round(avg_score, 1)

        # Track contributing games
        games = entry.setdefault("games_contributed", [])
        if game_id not in games:
            games.append(game_id)
            if len(games) > 20:
                entry["games_contributed"] = games[-20:]

        # Update level
        comp_config = competencies.get(comp_id, {})
        level_info = _get_nep_level(comp_config, entry["score"])
        entry["level"] = level_info.get("level", 1)
        entry["level_name"] = level_info.get("name", "Observer")
        entry["last_updated"] = datetime.now().isoformat()

    _save_profiles(profiles)


def get_nep_progression(user_id: str) -> dict:
    """Get student's NEP competency progression with level info."""
    config = _load_nep_config()
    competencies = config.get("competencies", {})

    profiles = _load_profiles()
    p = _ensure_profile(profiles, user_id)
    nep = p.get("nep_progression", {})

    result = {}
    for comp_id, comp_config in competencies.items():
        entry = nep.get(comp_id, {})
        score = entry.get("score", 0)
        level_info = _get_nep_level(comp_config, score)
        result[comp_id] = {
            "label": comp_config.get("label", comp_id),
            "icon": comp_config.get("icon", "📊"),
            "score": score,
            "level": level_info.get("level", 1),
            "level_name": level_info.get("name", "Observer"),
            "level_description": level_info.get("description", ""),
            "max_level": 5,
            "games_contributed": entry.get("games_contributed", []),
            "games_count": len(entry.get("games_contributed", [])),
            "last_updated": entry.get("last_updated"),
        }

    return result
