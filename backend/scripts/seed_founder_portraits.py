"""One-off: seed founder portrait placeholders for case-study cards.

Run when no designer-supplied art exists. Generates simple Pillow
placeholders (initial + name + warm gradient background) at the exact
paths referenced by Phase D Task 3 case_study_card lessons.

Run:
    cd backend && python3 scripts/seed_founder_portraits.py

After running, the static paths under
`/static/module_images/mento_entrepreneur_4week/founder_*.png`
resolve, and the CaseStudyCardRenderer renders the portrait. Replace
the PNGs with designer art at any time without code changes.
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

NAMES = {
    "founder_vembu": "Sridhar Vembu",
    "founder_nayar": "Falguni Nayar",
    "founder_ritesh": "Ritesh Agarwal",
    "founder_byju": "Byju Raveendran",
    "founder_kunal": "Kunal Shah",
    "founder_ghazal": "Ghazal Alagh",
    "founder_bhavish": "Bhavish Aggarwal",
    "founder_neighborhood": "Kirana Aunty & Uncle",
}

# Warm cartoon-friendly palette (background gradient stops)
PALETTES = [
    ((255, 217, 165), (255, 175, 122)),  # warm peach
    ((255, 234, 167), (250, 177, 160)),  # apricot
    ((253, 203, 110), (225, 112, 85)),   # marigold
    ((162, 213, 246), (108, 92, 231)),   # sky → indigo
    ((253, 167, 223), (162, 155, 254)),  # pink → lavender
    ((196, 229, 175), (105, 169, 138)),  # mint
    ((255, 234, 167), (255, 159, 67)),   # honey
    ((180, 198, 252), (108, 92, 231)),   # periwinkle
]


def _gradient(size, top_rgb, bottom_rgb):
    img = Image.new("RGB", size, top_rgb)
    draw = ImageDraw.Draw(img)
    w, h = size
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top_rgb[0] * (1 - t) + bottom_rgb[0] * t)
        g = int(top_rgb[1] * (1 - t) + bottom_rgb[1] * t)
        b = int(top_rgb[2] * (1 - t) + bottom_rgb[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))
    return img


def _font(size_px):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size_px)
            except Exception:
                continue
    return ImageFont.load_default()


def _initials(full_name: str) -> str:
    parts = [p for p in full_name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _draw_portrait(name: str, palette):
    size = (512, 512)
    img = _gradient(size, *palette)
    draw = ImageDraw.Draw(img, "RGBA")

    # White circle “avatar” backdrop
    cx, cy, r = 256, 230, 150
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, 235))

    # Initials inside the circle
    initials = _initials(name)
    font_lg = _font(140)
    bbox = draw.textbbox((0, 0), initials, font=font_lg)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]),
        initials,
        fill=(60, 60, 80),
        font=font_lg,
    )

    # Name caption
    font_sm = _font(34)
    bbox = draw.textbbox((0, 0), name, font=font_sm)
    tw = bbox[2] - bbox[0]
    draw.text(
        (256 - tw / 2 - bbox[0], 420),
        name,
        fill=(40, 40, 60),
        font=font_sm,
    )
    return img


def main():
    out_dir = Path(__file__).resolve().parents[1] / "assets" / "module_images" / "mento_entrepreneur_4week"
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, (slug, name) in enumerate(NAMES.items()):
        out = out_dir / f"{slug}.png"
        if out.exists():
            print(f"skip (exists): {out.name}")
            continue
        img = _draw_portrait(name, PALETTES[i % len(PALETTES)])
        img.save(out, "PNG", optimize=True)
        print(f"wrote: {out.name}")


if __name__ == "__main__":
    main()
