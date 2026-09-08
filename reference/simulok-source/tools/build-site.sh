#!/usr/bin/env bash
# Assemble the public site into a single folder.
#
#   ./tools/build-site.sh [outdir]      (default: _site)
#
# Layout produced:
#   <out>/            the marketing site   (from website/, minus its README)
#   <out>/platform/   the prototype, for the team only (root index.html + assets/)
#
# /platform/ is published on the same simulok.in deploy, but nothing on the
# marketing site links to it — a visitor browsing simulok.in can never reach
# it, and it doesn't appear in the nav, the CTA, or any page copy. It exists
# so the team can open a URL and always get whatever is on main, instead of
# pulling the repo or re-zipping index.html + assets/ every time something
# changes. Anyone holding the URL can open it — it is unlisted, not access
# controlled — so do not treat it as a substitute for keeping the link inside
# the team.
#
# index.html is copied, never edited: the file on main stays the single
# source of truth that also runs standalone (double-click, or the zip).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-_site}"
[[ "$OUT" = /* ]] || OUT="$ROOT/$OUT"

rm -rf "$OUT"
mkdir -p "$OUT/platform"

cp -R "$ROOT/website/." "$OUT/"
cp "$ROOT/index.html" "$OUT/platform/index.html"
cp -R "$ROOT/assets" "$OUT/platform/assets"

# Copy standalone simulator folders into platform/ (team-only, unlisted).
for dir in "$ROOT"/operations-simulators "$ROOT"/entrepreneurship-simulators; do
  [ -d "$dir" ] && cp -R "$dir" "$OUT/platform/$(basename "$dir")"
done
if [[ -d "$ROOT/cost-accounting" ]]; then
  cp -R "$ROOT/cost-accounting" "$OUT/platform/cost-accounting"
fi
if [[ -d "$ROOT/classroom" ]]; then
  cp -R "$ROOT/classroom" "$OUT/platform/classroom"
fi
# Copy standalone HTML sims
for f in "$ROOT"/dashmart.html "$ROOT"/zara.html; do
  [ -f "$f" ] && cp "$f" "$OUT/platform/$(basename "$f")"
done

# website/README.md is internal build notes — keep it in the repo, off the site.
rm -f "$OUT/README.md"

touch "$OUT/.nojekyll"

echo "Built $OUT"
echo "  marketing site  : $OUT/index.html"
echo "  team platform   : $OUT/platform/index.html  (unlinked from the site)"
if [[ -f "$OUT/platform/cost-accounting/zenith-appliances.html" ]]; then
  echo "  zenith (team)   : $OUT/platform/cost-accounting/zenith-appliances.html"
fi
