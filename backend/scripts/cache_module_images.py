"""
One-time script: download every Pollinations image referenced in a module to
  backend/assets/module_images/<module_id>/<lesson_id>.png
and rewrite URLs in the module JSON.  Keeps original URL in
`image_url_fallback` so callers can fall back if the local file is absent.

Covers two locations per lesson:
  lesson["image_url"]           — top-level hero image
  lesson["content"]["image_url"] — image embedded in the content block

Paths are resolved relative to this script's location so it can be invoked
from any working directory:
  python backend/scripts/cache_module_images.py                 # uses default module id
  python backend/scripts/cache_module_images.py mento_entrepreneur_4week
"""
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Resolve repo-relative paths from this script's own location:
# backend/scripts/cache_module_images.py → backend/
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent


def _download(url: str, dest: Path) -> bool:
    """Download *url* to *dest*. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MentoApp/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
        return True
    except (urllib.error.URLError, OSError, Exception) as exc:
        print(f"  FAILED: {exc}")
        return False


def cache_module_images(module_id: str) -> None:
    module_path = BACKEND_DIR / "modules" / f"{module_id}.json"
    assets_dir = BACKEND_DIR / "assets" / "module_images" / module_id
    assets_dir.mkdir(parents=True, exist_ok=True)

    print(f"Module file : {module_path}")
    print(f"Assets dir  : {assets_dir}")

    with open(module_path, encoding="utf-8") as f:
        module = json.load(f)

    downloaded = 0
    failed = 0
    skipped = 0

    for week in module.get("weeks", []):
        for lesson in week.get("lessons", []):
            lesson_id = lesson.get("lesson_id", "")
            if not lesson_id:
                continue

            # ── 1. Top-level image_url ──────────────────────────────────────
            top_url = lesson.get("image_url", "")
            if top_url and not top_url.startswith("/static/"):
                out_path = assets_dir / f"{lesson_id}.png"
                if not out_path.exists():
                    print(f"  [{lesson_id}] downloading top-level image…")
                    ok = _download(top_url, out_path)
                    if ok:
                        downloaded += 1
                    else:
                        failed += 1
                        # Leave original URL intact on failure
                        continue
                else:
                    skipped += 1
                lesson["image_url_fallback"] = top_url
                lesson["image_url"] = f"/static/module_images/{module_id}/{lesson_id}.png"

            # ── 2. content.image_url ────────────────────────────────────────
            content = lesson.get("content", {})
            if isinstance(content, dict):
                content_url = content.get("image_url", "")
                if content_url and not content_url.startswith("/static/"):
                    # Use a distinct filename so it doesn't collide with the top-level one
                    content_out = assets_dir / f"{lesson_id}_content.png"
                    if not content_out.exists():
                        print(f"  [{lesson_id}] downloading content image…")
                        ok = _download(content_url, content_out)
                        if ok:
                            downloaded += 1
                        else:
                            failed += 1
                            continue
                    else:
                        skipped += 1
                    content["image_url_fallback"] = content_url
                    content["image_url"] = (
                        f"/static/module_images/{module_id}/{lesson_id}_content.png"
                    )

    with open(module_path, "w", encoding="utf-8") as f:
        json.dump(module, f, indent=2, ensure_ascii=False)

    print(
        f"\nDone. downloaded={downloaded}  skipped(already cached)={skipped}"
        f"  failed={failed}"
    )
    if failed:
        print(
            "  NOTE: failed lessons keep their original Pollinations URL — "
            "the frontend will still show images via the fallback."
        )


if __name__ == "__main__":
    module_id = sys.argv[1] if len(sys.argv) > 1 else "mento_entrepreneur_4week"
    cache_module_images(module_id)
