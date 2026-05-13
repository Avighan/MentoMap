"""Render an Idea Journal as a 'My Pitch Deck' PDF.

Layout: cover page (student name + module + date), then one page per week
containing entries from that week, plus a closing page with starred entries.
Uses reportlab (already a transitive dep via certificate.py stack).
"""
import io
from typing import Any, Dict, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak


def render_journal_pdf(
    student_name: str,
    module_title: str,
    completion_date: str,
    entries: List[Dict[str, Any]],
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=28, leading=34, alignment=1)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=18, leading=22)
    body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=11, leading=16)

    story: List[Any] = []
    # Cover
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("My Pitch Deck", h1))
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(student_name or "Founder", h2))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(module_title, body))
    story.append(Paragraph(completion_date, body))
    story.append(PageBreak())

    # Group entries by lesson_id prefix (w1_/w2_/...)
    by_week: Dict[str, List[Dict[str, Any]]] = {f"w{i}": [] for i in range(1, 5)}
    other: List[Dict[str, Any]] = []
    for e in entries:
        lid = (e.get("lesson_id") or "").split("_", 1)[0]
        if lid in by_week:
            by_week[lid].append(e)
        else:
            other.append(e)

    for wk, items in by_week.items():
        if not items:
            continue
        story.append(Paragraph(f"Week {wk[1:]}", h2))
        for e in items:
            title = e.get("lesson_title") or e.get("type", "Entry")
            story.append(Paragraph(f"<b>{_escape(title)}</b>", body))
            story.append(Paragraph(_escape(e.get("content", "")), body))
            story.append(Spacer(1, 0.3 * cm))
        story.append(PageBreak())

    if other:
        story.append(Paragraph("Free-form notes", h2))
        for e in other:
            story.append(Paragraph(_escape(e.get("content", "")), body))
            story.append(Spacer(1, 0.2 * cm))
        story.append(PageBreak())

    starred = [e for e in entries if e.get("starred")]
    if starred:
        story.append(Paragraph("⭐ Highlights", h2))
        for e in starred:
            story.append(Paragraph(_escape(e.get("content", "")), body))
            story.append(Spacer(1, 0.2 * cm))

    doc.build(story)
    return buf.getvalue()


def _escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
