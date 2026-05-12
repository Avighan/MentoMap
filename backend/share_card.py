"""Server-render a 1080x1080 Instagram-square skill report card.

Uses Pillow only (no headless browser). Designed for WhatsApp/IG share.
Privacy: first name only by default.
"""
import io
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = 1080
BG = (250, 247, 240)
INK = (24, 24, 27)
ACCENT = (79, 70, 229)
MUTED = (113, 113, 122)


def render_card(
    first_name: str,
    age: Optional[int],
    module_title: str,
    dimensions: Dict[str, int],
    headline: str,
    cohort: Optional[str] = None,
) -> bytes:
    img = Image.new("RGB", (CARD_SIZE, CARD_SIZE), BG)
    d = ImageDraw.Draw(img)

    title_font = _font(64, bold=True)
    name_font = _font(96, bold=True)
    body_font = _font(36)
    small_font = _font(28)

    # Header strip
    d.rectangle([(0, 0), (CARD_SIZE, 140)], fill=ACCENT)
    d.text((48, 50), "MENTO \u00b7 FOUNDER LAB", fill="white", font=title_font)

    # Student name
    d.text((48, 200), first_name, fill=INK, font=name_font)
    sub = module_title
    if age:
        sub = f"Age {age} \u00b7 " + sub
    d.text((48, 310), sub, fill=MUTED, font=body_font)

    # Top 3 skills as horizontal bars
    top = sorted(dimensions.items(), key=lambda x: -x[1])[:3]
    y = 420
    for k, v in top:
        label = k.replace("_", " ").title()
        d.text((48, y), label, fill=INK, font=body_font)
        d.text((CARD_SIZE - 160, y), str(v), fill=ACCENT, font=body_font)
        bar_w = int((CARD_SIZE - 120) * (max(0, min(100, v)) / 100))
        d.rectangle([(48, y + 56), (CARD_SIZE - 72, y + 76)], fill=(228, 228, 231))
        d.rectangle([(48, y + 56), (48 + bar_w, y + 76)], fill=ACCENT)
        y += 130

    # Headline
    d.multiline_text((48, 820), _wrap(headline, 32), fill=INK, font=body_font, spacing=6)

    # Footer
    d.text(
        (48, CARD_SIZE - 80),
        cohort or "Mento App \u00b7 simulations.mentomap.com",
        fill=MUTED,
        font=small_font,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _font(size: int, bold: bool = False):
    # Try a few common system fonts; fall back to default.
    candidates = [
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        "/Library/Fonts/Arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _wrap(text: str, width: int) -> str:
    words = text.split()
    lines: List[str] = []
    cur = ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)
