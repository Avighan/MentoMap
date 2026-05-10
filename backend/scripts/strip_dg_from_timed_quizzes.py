"""Strip delayed_gratification from timed_challenge games and re-key to adaptability.

Reasoning: timed quizzes test the OPPOSITE of delayed gratification (speed over
deliberation). The audit (§9 step 6) flags this as a tag-mechanic mismatch.

Strips delayed_gratification from THREE structural locations:
  1. skill_tags arrays (replace with adaptability).
  2. dimension_scoring_weights dict (re-key dg -> adaptability, summing weights).
  3. psychological_skills (list[str|dict] or dict) — drop dg entry/key.

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


def _merge_dg_value_into_adaptability(adapt_val, dg_val):
    """Best-effort merge of two values. Numbers sum (clamped to [0,100]); dicts merge value field clamped to max."""
    # numeric + numeric -> sum, clamped to [0,100]
    if isinstance(adapt_val, (int, float)) and isinstance(dg_val, (int, float)):
        return round(max(0.0, min(100.0, float(adapt_val) + float(dg_val))), 3)
    # both dicts: keep adapt_val structure, sum 'value' clamped to [min,max] if present
    if isinstance(adapt_val, dict) and isinstance(dg_val, dict):
        merged = dict(adapt_val)
        if isinstance(adapt_val.get("value"), (int, float)) and isinstance(dg_val.get("value"), (int, float)):
            lo = float(adapt_val.get("min", 0)) if isinstance(adapt_val.get("min"), (int, float)) else 0.0
            hi = float(adapt_val.get("max", 100)) if isinstance(adapt_val.get("max"), (int, float)) else 100.0
            merged["value"] = round(max(lo, min(hi, float(adapt_val["value"]) + float(dg_val["value"]))), 3)
        return merged
    # one missing/null
    if adapt_val is None:
        return dg_val
    return adapt_val  # prefer existing


def _rekey_dg_in_dict(d):
    """If dict has 'delayed_gratification' key, re-key to 'adaptability' (merging if needed). Returns True if mutated."""
    if not isinstance(d, dict) or "delayed_gratification" not in d:
        return False
    dg_val = d.pop("delayed_gratification")
    if "adaptability" in d:
        d["adaptability"] = _merge_dg_value_into_adaptability(d["adaptability"], dg_val)
    else:
        d["adaptability"] = dg_val
    return True


def strip_dg_in_obj(obj):
    """Recursively walk obj; remove 'delayed_gratification' from all known structural locations.

    Handles:
      - skill_tags arrays: replace 'delayed_gratification' string with 'adaptability'.
      - any dict with a 'delayed_gratification' key: re-key to 'adaptability' (merge with smart strategy).
      - any list of skill-descriptor dicts where item['id'] == 'delayed_gratification': re-id to 'adaptability'
        if no sibling already has that id, else drop the dg item entirely.
    """
    changed = False
    if isinstance(obj, dict):
        if _rekey_dg_in_dict(obj):
            changed = True
        for v in obj.values():
            if isinstance(v, list):
                # special: skill_tags list[str]
                if all(isinstance(x, str) for x in v) and "delayed_gratification" in v:
                    v[:] = [t if t != "delayed_gratification" else "adaptability" for t in v]
                    changed = True
                    continue
                # special: list[dict] with id field — re-id or drop dg entries
                sibling_ids = {x.get("id") for x in v if isinstance(x, dict)}
                if "delayed_gratification" in sibling_ids:
                    if "adaptability" in sibling_ids:
                        v[:] = [x for x in v if not (isinstance(x, dict) and x.get("id") == "delayed_gratification")]
                    else:
                        for x in v:
                            if isinstance(x, dict) and x.get("id") == "delayed_gratification":
                                x["id"] = "adaptability"
                    changed = True
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
