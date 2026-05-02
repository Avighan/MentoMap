"""Strip delayed_gratification skill_tags from timed_challenge games; add adaptability.

Reasoning: timed quizzes test the OPPOSITE of delayed gratification (speed over
deliberation). The audit (§9 step 6) flags this as a tag-mechanic mismatch.

Note: in this codebase the timed-challenge marker lives at
``minigame_config.subtype == "timed_challenge"`` (the wrapping ``game_type`` is
``minigame``). We match on either signal so the script stays robust if other
games adopt a top-level ``timed_challenge`` type later.

Idempotent. Writes .bak before mutation.
"""
import json
import os
import shutil
import sys
import glob

GAMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "games")


def is_timed_challenge(game):
    if game.get("game_type") == "timed_challenge":
        return True
    mc = game.get("minigame_config") or {}
    if isinstance(mc, dict) and mc.get("subtype") == "timed_challenge":
        return True
    return False


def strip_dg_in_obj(obj):
    """Recursively walk obj; replace 'delayed_gratification' with 'adaptability' in skill_tags arrays."""
    changed = False
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "skill_tags" and isinstance(v, list):
                if "delayed_gratification" in v:
                    obj[k] = [t if t != "delayed_gratification" else "adaptability" for t in v]
                    changed = True
            else:
                if strip_dg_in_obj(v):
                    changed = True
    elif isinstance(obj, list):
        for item in obj:
            if strip_dg_in_obj(item):
                changed = True
    return changed


def main():
    paths = sorted(glob.glob(os.path.join(GAMES_DIR, "*.json")))
    affected = []
    for p in paths:
        if ".bak" in p or ".retrofit.bak" in p:
            continue
        try:
            with open(p) as f:
                game = json.load(f)
        except Exception as e:
            print(f"SKIP {p}: {e}")
            continue
        if not is_timed_challenge(game):
            continue
        if not strip_dg_in_obj(game):
            print(f"clean: {os.path.basename(p)}")
            continue
        bak = p + ".pre_dg_strip.bak"
        if not os.path.exists(bak):
            shutil.copy2(p, bak)
        with open(p, "w") as f:
            json.dump(game, f, indent=2, ensure_ascii=False)
        affected.append(p)
        print(f"updated: {os.path.basename(p)}")
    print(f"\nTotal updated: {len(affected)}")


if __name__ == "__main__":
    main()
