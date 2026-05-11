"""List canonical game JSONs missing top-level reflection_prompt."""
import json, os, sys

GAMES_DIR = os.path.join(os.path.dirname(__file__), "..", "games")

def main():
    missing = []
    for fn in sorted(os.listdir(GAMES_DIR)):
        if not fn.endswith(".json") or ".bak" in fn:
            continue
        path = os.path.join(GAMES_DIR, fn)
        try:
            with open(path) as f:
                data = json.load(f)
        except Exception as e:
            print(f"SKIP {fn}: {e}", file=sys.stderr)
            continue
        if not data.get("reflection_prompt"):
            missing.append((fn, data.get("title", ""), data.get("game_type", ""),
                            data.get("target_age", ""), (data.get("learning_objectives") or [])[:1]))
    print(f"Total missing: {len(missing)}\n")
    for fn, title, gt, age, objs in missing:
        print(f"{fn}\t{gt}\t{age}\t{title}\t{(objs[0] if objs else '')[:80]}")

if __name__ == "__main__":
    main()
