"""Generate v1 baseline snapshots for regression testing.

Runs 8 reference games to a fixed seed and saves end-of-game state.
P0+ changes must keep these stable for any game NOT opted into v2.

NOTE: _compute_rounds_dimension_scores, _compute_strategy_dimension_scores,
and _compute_story_dimension_scores are copied verbatim from app.py lines
20111, 20198, and 20216 respectively for snapshot isolation.  app.py cannot
be imported directly because it has module-level side effects that require
openai, anthropic, and other optional packages not installed in the snapshot
venv.  Keep these copies in sync when the originals change.

**FROZEN COPIES:** The three `_compute_*_dimension_scores` functions copied
below are intentionally PERMANENT v1 snapshots.  They MUST NOT be updated
when `app.py` evolves in Tasks 5–7+ (which add the behavioral blend).  Their
purpose is to reproduce v1 scoring exactly so the regression suite catches
any drift.

The ``# COPY of app.py:LINE`` banners on each copied function mean: "if a
hotfix corrects a bug in the original *before* Task 5, sync the fix here
too."  From Task 5 onward, these copies are frozen.  Treat any apparent
divergence between this file and `app.py` as expected, not a merge mistake.
"""
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_storage import load_game

REFERENCE_GAMES = [
    "cfo-quarterly-close",
    "lemonade-empire-enhanced",
    "founders-gambit",            # chess_strategy: round has no JSON choices — round_count=0 by design
    "series-a-founders-journey",
    "project-management-mastery",
    "the-startup-decision",       # story_branching uses chapters[].scenes[] — round_count=0 by design
    "climate-champions",          # story_branching uses chapters[].scenes[] — round_count=0 by design
    "city-mayor",                 # story_branching uses chapters[].scenes[] — round_count=0 by design
]

SEED = 42


# ---------------------------------------------------------------------------
# COPY of app.py:20111 for snapshot isolation; keep in sync
# NOTE: _w() intentionally extends app.py's one-liner with an isinstance(val, dict)
# guard so legacy float-valued dimension_scoring_weights (e.g., lemonade-empire-enhanced)
# fall through to defaults instead of raising AttributeError on float.get().
# ---------------------------------------------------------------------------
def _compute_rounds_dimension_scores(state, game=None):
    """Compute dimension scores from rounds game state.

    Supports per-game customisation via game JSON:
        "dimension_scoring_weights": {
            "strategic_thinking": {"base": 35, "tag_bonus": 7, "completion_bonus": 25},
            "risk_tolerance":      {"base": 30, "risk_choices_bonus": 9, "tag_bonus": 7},
            "delayed_gratification":{"base": 35, "safe_choices_bonus": 6, "tag_bonus": 7, "completion_bonus": 20},
            "adaptability":        {"base": 30, "variety_bonus": 8, "tag_bonus": 7},
            "resilience":          {"base": 30, "tag_bonus": 8, "completion_bonus": 20, "choices_bonus": 2},
            "empathy":             {"base": 30, "tag_bonus": 9}
        }
    Any missing keys fall back to the built-in defaults.
    """
    w = (game or {}).get("dimension_scoring_weights", {})

    def _w(dim, key, default):
        # dimension_scoring_weights may be a dict of dicts (new style) or a dict of
        # floats (old style normalised weights).  For the old style, fall through to
        # default so the baseline scoring logic is unchanged.
        val = w.get(dim, {})
        if not isinstance(val, dict):
            return default
        return val.get(key, default)

    choice_history = state.get("choice_history", [])
    rounds_completed = state.get("rounds_completed", [])
    total_rounds = state.get("total_rounds", max(1, len(rounds_completed)))
    completion_rate = len(rounds_completed) / max(1, total_rounds)

    num_choices = max(1, len(choice_history))
    risk_choices = sum(1 for c in choice_history if c.get("risk_level") in ("high", "bold"))
    safe_choices = sum(1 for c in choice_history if c.get("risk_level") in ("safe", "low"))
    tag_counts = {}
    for c in choice_history:
        for tag in c.get("skill_tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1

    strategic = min(100,
        _w("strategic_thinking", "base", 35) +
        tag_counts.get("strategic_thinking", 0) * _w("strategic_thinking", "tag_bonus", 7) +
        int(completion_rate * _w("strategic_thinking", "completion_bonus", 25)))
    risk = min(100,
        _w("risk_tolerance", "base", 30) +
        risk_choices * _w("risk_tolerance", "risk_choices_bonus", 9) +
        tag_counts.get("risk_tolerance", 0) * _w("risk_tolerance", "tag_bonus", 7))
    delayed = min(100,
        _w("delayed_gratification", "base", 35) +
        safe_choices * _w("delayed_gratification", "safe_choices_bonus", 6) +
        tag_counts.get("delayed_gratification", 0) * _w("delayed_gratification", "tag_bonus", 7) +
        int(completion_rate * _w("delayed_gratification", "completion_bonus", 20)))
    adaptability_val = min(100,
        _w("adaptability", "base", 30) +
        len(set(c.get("choice_type", "") for c in choice_history)) * _w("adaptability", "variety_bonus", 8) +
        tag_counts.get("adaptability", 0) * _w("adaptability", "tag_bonus", 7))
    resilience_val = min(100,
        _w("resilience", "base", 30) +
        tag_counts.get("resilience", 0) * _w("resilience", "tag_bonus", 8) +
        int(completion_rate * _w("resilience", "completion_bonus", 20)) +
        min(15, num_choices * _w("resilience", "choices_bonus", 2)))
    empathy_val = min(100,
        _w("empathy", "base", 30) +
        tag_counts.get("empathy", 0) * _w("empathy", "tag_bonus", 9))

    scores = {
        "strategic_thinking": strategic,
        "risk_tolerance": risk,
        "delayed_gratification": delayed,
        "adaptability": adaptability_val,
        "resilience": resilience_val,
        "empathy": empathy_val,
    }
    # Optional 7th/8th dimensions — only emitted when skill_tags are present
    ethics_count = tag_counts.get("ethical_reasoning", 0)
    if ethics_count > 0:
        scores["ethical_reasoning"] = min(100, _w("ethical_reasoning", "base", 30) + ethics_count * _w("ethical_reasoning", "tag_bonus", 9))
    creativity_count = tag_counts.get("creativity", 0)
    if creativity_count > 0:
        scores["creativity"] = min(100, _w("creativity", "base", 30) + creativity_count * _w("creativity", "tag_bonus", 9))
    # Executive-tier dimensions — emitted only when the game's choices declare
    # the matching skill_tags. Same opt-in pattern as ethics/creativity so existing
    # SEL games are unaffected.
    for exec_dim in (
        "capital_allocation", "vision_setting", "governance_judgment",
        "talent_strategy", "commercial_acumen", "systems_thinking",
        "narrative_persuasion", "decision_quality",
    ):
        cnt = tag_counts.get(exec_dim, 0)
        if cnt > 0:
            scores[exec_dim] = min(100, _w(exec_dim, "base", 30) + cnt * _w(exec_dim, "tag_bonus", 9))
    return scores


# ---------------------------------------------------------------------------
# COPY of app.py:20198 for snapshot isolation; keep in sync
# ---------------------------------------------------------------------------
def _compute_strategy_dimension_scores(state):
    """Compute dimension scores from strategy/chess_strategy game state."""
    moves = state.get("moves_made", state.get("total_moves", 0))
    score = state.get("score", state.get("final_score", 50))
    resources = state.get("resources", {})
    sustainability = min(100, int(sum(resources.values()) / max(1, len(resources)))) if resources else 50
    efficiency = min(100, 35 + min(40, moves * 3)) if moves else 50
    risk_score = min(100, 30 + int(score * 0.4))
    return {
        "strategic_thinking": efficiency,
        "risk_tolerance": risk_score,
        "delayed_gratification": sustainability,
        "adaptability": min(100, 40 + int(score * 0.3)),
        "resilience": min(100, 35 + int(score * 0.35)),
        "empathy": 50,
    }


# ---------------------------------------------------------------------------
# COPY of app.py:20216 for snapshot isolation; keep in sync
# ---------------------------------------------------------------------------
def _compute_story_dimension_scores(state_or_log, ending_type="standard"):
    """Compute dimension scores from story_branching gameplay.
    Uses actual choice deltas and skill_tags — not just choice count.
    """
    state = state_or_log if isinstance(state_or_log, dict) else {}
    log = state.get("log", []) if isinstance(state, dict) else (state_or_log if isinstance(state_or_log, list) else [])

    num_choices = max(1, len(log))
    ending_bonus = {"best": 20, "triumph": 20, "growth": 12, "bittersweet": 8,
                    "redemption": 12, "standard": 5, "bad": 0}.get(ending_type, 5)

    # Collect all skill_tags from choices — these reflect actual choice quality
    tag_counts = {}
    total_positive_delta = 0
    total_negative_delta = 0
    for entry in log:
        for tag in entry.get("skill_tags", []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        delta = entry.get("delta", {})
        for v in delta.values():
            if isinstance(v, (int, float)):
                if v > 0:
                    total_positive_delta += v
                else:
                    total_negative_delta += abs(v)

    # Quality ratio: how much positive impact vs negative
    quality_ratio = total_positive_delta / max(1, total_positive_delta + total_negative_delta)
    quality_bonus = int(quality_ratio * 20)  # 0-20 bonus for good choices

    # Use gameplay-accumulated dimension_scores if available (from skill_tags during play)
    gameplay_dims = state.get("dimension_scores", {}) if isinstance(state, dict) else {}

    # Base computation + quality adjustment
    ALL_DIMS = ["strategic_thinking", "risk_tolerance", "delayed_gratification",
                "adaptability", "resilience", "empathy"]
    scores = {}
    for dim in ALL_DIMS:
        # Start from gameplay score if available, else base 35
        base = gameplay_dims.get(dim, 35) if isinstance(gameplay_dims, dict) else 35
        # Add tag bonus (+5 per tag for this dimension)
        tag_bonus = tag_counts.get(dim, 0) * 5
        # Add ending + quality bonuses
        score = base + tag_bonus + quality_bonus + ending_bonus // 2
        scores[dim] = min(100, max(10, score))

    # Ethical reasoning and creativity from tags
    if tag_counts.get("ethical_reasoning", 0) > 0:
        scores["ethical_reasoning"] = min(100, 30 + tag_counts["ethical_reasoning"] * 8 + quality_bonus)
    if tag_counts.get("creativity", 0) > 0:
        scores["creativity"] = min(100, 30 + tag_counts["creativity"] * 8 + quality_bonus)
    # Executive-tier dimensions — same opt-in (skill_tag presence) pattern
    for exec_dim in (
        "capital_allocation", "vision_setting", "governance_judgment",
        "talent_strategy", "commercial_acumen", "systems_thinking",
        "narrative_persuasion", "decision_quality",
    ):
        if tag_counts.get(exec_dim, 0) > 0:
            scores[exec_dim] = min(100, 30 + tag_counts[exec_dim] * 8 + quality_bonus)

    return scores


def simulate_game(game_id):
    """Run the game with fixed seed, choosing first option each round.
    Returns end-of-game state for snapshotting.
    """
    game = load_game(game_id)
    if game is None:
        return None
    state = {
        "user_id": "snapshot_user",
        "game_id": game_id,
        "seed": SEED,
        "choice_history": [],
        "resource_trajectory": [],
        "round_index": 0,
    }
    rounds = game.get("rounds", []) or game.get("scenes", [])
    for r in rounds:
        choices = r.get("choices", [])
        if not choices:
            continue
        chosen = choices[0]
        state["choice_history"].append({
            "round_id": r.get("id") or r.get("round_id"),
            "choice_id": chosen.get("id"),
            "skill_tags": chosen.get("skill_tags", []),
            "deltas": chosen.get("deltas", {}),
            "risk_level": chosen.get("risk_level"),
            "decision_time_ms": 5000,
        })
        deltas = chosen.get("deltas", {})
        prev = state["resource_trajectory"][-1] if state["resource_trajectory"] else {}
        next_r = {**prev, **{k: prev.get(k, 0) + v for k, v in deltas.items() if isinstance(v, (int, float))}}
        state["resource_trajectory"].append(next_r)
        state["round_index"] += 1

    game_type = game.get("game_type", "rounds")
    if game_type == "story_branching":
        scores = _compute_story_dimension_scores(state, ending_type="standard")
    elif game_type in ("chess_strategy", "strategy_grid"):
        scores = _compute_strategy_dimension_scores(state)
    else:
        scores = _compute_rounds_dimension_scores(state, game)

    final_kpis = state["resource_trajectory"][-1] if state["resource_trajectory"] else {}
    return {
        "game_id": game_id,
        "seed": SEED,
        "completion_rate": 1.0,
        "total_score": sum(v for v in final_kpis.values() if isinstance(v, (int, float))),
        "final_dimension_scores": scores,
        "kpis": final_kpis,
        "round_count": len(state["choice_history"]),
    }


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "snapshots")
    os.makedirs(out_dir, exist_ok=True)
    for game_id in REFERENCE_GAMES:
        result = simulate_game(game_id)
        if result is None:
            print(f"SKIP: {game_id} not found")
            continue
        path = os.path.join(out_dir, f"{game_id}_v1.json")
        with open(path, "w") as f:
            json.dump(result, f, indent=2, sort_keys=True)
        print(f"WROTE: {path}")


if __name__ == "__main__":
    main()
