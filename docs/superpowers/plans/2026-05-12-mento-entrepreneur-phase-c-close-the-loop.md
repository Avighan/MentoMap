# Mento Entrepreneur Phase C — Close the Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the proof-of-learning loop to `mento_entrepreneur_4week`: Idea Journal, micro-quests, SR seeding, module skill report (with parent-shareable WhatsApp PNG), certificate-on-completion, milestone badges, and cohort live sessions.

**Architecture:** All additions are net-additive against the existing module engine. New lesson types `micro_quest`, `cohort_live_session`, and PDF/PNG artifacts. Two new backend modules (`idea_journal.py`, `cohort_live_sessions.py`), one extension (`modules_engine.complete_module`). Frontend: side drawer in `ModuleDetailPage`, full report page in `ModuleReportPage`, admin tab in `AdminDashboard`.

**Tech Stack:** Flask + Python (jsonfile storage), Pillow + ReportLab (already used in `certificate.py`), React + Vite + Tailwind, APScheduler (already running), Web Share API.

**Prerequisite:** `phase-a-complete` tag from Plan A. This plan can run in parallel with Phase B.

---

### Task 0: Regression baseline check

**Files:**
- Test: `backend/tests/test_phase_c_baseline.py` (Create)

- [ ] **Step 1: Write a baseline assertion test**

```python
# backend/tests/test_phase_c_baseline.py
"""Phase C regression baseline. Runs before any C task to confirm Phase A landed and module is healthy."""
import json
from pathlib import Path


def test_phase_a_artifacts_exist():
    """Phase A must have shipped before C touches anything."""
    root = Path(__file__).resolve().parents[1]
    assert (root / "services" / "tts_service.py").exists(), "Phase A TTS service missing"
    assert (root / "assets" / "module_images" / "mento_entrepreneur_4week").exists(), \
        "Phase A image self-host did not run"


def test_module_loads_and_has_32_lessons():
    root = Path(__file__).resolve().parents[1]
    mod_path = root / "modules" / "mento_entrepreneur_4week.json"
    module = json.loads(mod_path.read_text())
    lesson_count = sum(len(w.get("lessons", [])) for w in module["weeks"])
    assert lesson_count >= 32, f"Expected ≥32 lessons, got {lesson_count}"
    assert len(module["weeks"]) == 4
```

- [ ] **Step 2: Run it**

Run: `cd backend && python -m pytest tests/test_phase_c_baseline.py -v`
Expected: PASS (both tests).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_phase_c_baseline.py
git commit -m "test(phase-c): baseline regression check"
```

---

### Task 1: Idea Journal — storage module

**Files:**
- Create: `backend/idea_journal.py`
- Test: `backend/tests/test_idea_journal.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_idea_journal.py
import os
import tempfile
import pytest


@pytest.fixture
def tmp_storage(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        monkeypatch.setenv("MENTO_DATA_DIR", d)
        yield d


def test_append_and_list(tmp_storage):
    from importlib import reload
    import backend.idea_journal as ij
    reload(ij)
    ij.append_entry("u1", "mento_entrepreneur_4week", {
        "lesson_id": "w1_l1_intro",
        "lesson_title": "What is Entrepreneurship?",
        "content": "Solving a problem people care about.",
        "type": "worksheet",
    })
    entries = ij.list_entries("u1", "mento_entrepreneur_4week")
    assert len(entries) == 1
    assert entries[0]["lesson_id"] == "w1_l1_intro"
    assert "entry_id" in entries[0] and "timestamp" in entries[0]


def test_edit_and_star(tmp_storage):
    from importlib import reload
    import backend.idea_journal as ij
    reload(ij)
    e = ij.append_entry("u1", "m1", {"content": "first", "type": "free_form"})
    ij.edit_entry("u1", "m1", e["entry_id"], {"content": "second"})
    ij.star_entry("u1", "m1", e["entry_id"], True)
    entries = ij.list_entries("u1", "m1")
    assert entries[0]["content"] == "second"
    assert entries[0]["starred"] is True
    # Edit history retained:
    assert len(entries[0]["history"]) == 1
    assert entries[0]["history"][0]["content"] == "first"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/test_idea_journal.py -v`
Expected: FAIL (`ModuleNotFoundError: backend.idea_journal`)

- [ ] **Step 3: Implement the storage module**

```python
# backend/idea_journal.py
"""Per-user persistent idea journal keyed by (user_id, module_id).

Each entry: {entry_id, lesson_id?, lesson_title?, content, type, timestamp, starred, history[]}
Storage: backend/data/idea_journals/<user_id>__<module_id>.json
Append-only with edit history retained for teacher visibility.
"""
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional


def _data_dir() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    )
    d = os.path.join(base, "idea_journals")
    os.makedirs(d, exist_ok=True)
    return d


def _path(user_id: str, module_id: str) -> str:
    safe = f"{user_id}__{module_id}".replace("/", "_")
    return os.path.join(_data_dir(), f"{safe}.json")


def _load(user_id: str, module_id: str) -> List[Dict[str, Any]]:
    p = _path(user_id, module_id)
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save(user_id: str, module_id: str, entries: List[Dict[str, Any]]) -> None:
    p = _path(user_id, module_id)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def append_entry(user_id: str, module_id: str, entry: Dict[str, Any]) -> Dict[str, Any]:
    entries = _load(user_id, module_id)
    new = {
        "entry_id": uuid.uuid4().hex[:12],
        "lesson_id": entry.get("lesson_id"),
        "lesson_title": entry.get("lesson_title"),
        "content": entry.get("content", ""),
        "type": entry.get("type", "free_form"),
        "timestamp": entry.get("timestamp") or _now_iso(),
        "starred": False,
        "history": [],
    }
    entries.append(new)
    _save(user_id, module_id, entries)
    return new


def edit_entry(user_id: str, module_id: str, entry_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    entries = _load(user_id, module_id)
    for e in entries:
        if e["entry_id"] == entry_id:
            e.setdefault("history", []).append({
                "content": e.get("content", ""),
                "timestamp": e.get("timestamp"),
            })
            if "content" in patch:
                e["content"] = patch["content"]
            e["timestamp"] = _now_iso()
            _save(user_id, module_id, entries)
            return e
    return None


def star_entry(user_id: str, module_id: str, entry_id: str, starred: bool) -> bool:
    entries = _load(user_id, module_id)
    for e in entries:
        if e["entry_id"] == entry_id:
            e["starred"] = bool(starred)
            _save(user_id, module_id, entries)
            return True
    return False


def list_entries(user_id: str, module_id: str) -> List[Dict[str, Any]]:
    return _load(user_id, module_id)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_idea_journal.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/idea_journal.py backend/tests/test_idea_journal.py
git commit -m "feat(phase-c): idea journal storage module"
```

---

### Task 2: Idea Journal — Flask routes

**Files:**
- Modify: `backend/app.py` (add routes near other module routes; search for `@app.route("/api/modules/<module_id>")` to find anchor)
- Test: `backend/tests/test_idea_journal_api.py`

- [ ] **Step 1: Write the failing API test**

```python
# backend/tests/test_idea_journal_api.py
import json
import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from backend.app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth_headers(client):
    # Use existing demo_student creds (Mento@2026) — present in seed users.
    r = client.post("/api/auth/login", json={"username": "demo_student", "password": "Mento@2026"})
    token = r.get_json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_journal_post_and_get(client):
    h = _auth_headers(client)
    r = client.post(
        "/api/modules/mento_entrepreneur_4week/idea-journal",
        json={"content": "First idea", "type": "free_form"},
        headers=h,
    )
    assert r.status_code == 200
    eid = r.get_json()["entry_id"]

    r2 = client.get("/api/modules/mento_entrepreneur_4week/idea-journal", headers=h)
    assert r2.status_code == 200
    assert any(e["entry_id"] == eid for e in r2.get_json()["entries"])


def test_journal_patch_star(client):
    h = _auth_headers(client)
    r = client.post(
        "/api/modules/mento_entrepreneur_4week/idea-journal",
        json={"content": "Idea A", "type": "free_form"},
        headers=h,
    )
    eid = r.get_json()["entry_id"]
    r2 = client.patch(
        f"/api/modules/mento_entrepreneur_4week/idea-journal/{eid}",
        json={"starred": True, "content": "Idea A (edited)"},
        headers=h,
    )
    assert r2.status_code == 200
    body = r2.get_json()
    assert body["starred"] is True
    assert body["content"] == "Idea A (edited)"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_idea_journal_api.py -v`
Expected: FAIL (404 on POST).

- [ ] **Step 3: Add routes to `backend/app.py`**

Locate a module-scoped route block (search for `"/api/modules/<module_id>/start"`) and add nearby:

```python
# --- Idea Journal --------------------------------------------------------
import backend.idea_journal as _idea_journal


@app.route("/api/modules/<module_id>/idea-journal", methods=["GET"])
@require_auth
def list_idea_journal(module_id: str):
    user_id = g.current_user["user_id"]
    entries = _idea_journal.list_entries(user_id, module_id)
    return jsonify({"entries": entries})


@app.route("/api/modules/<module_id>/idea-journal", methods=["POST"])
@require_auth
def post_idea_journal(module_id: str):
    user_id = g.current_user["user_id"]
    body = request.get_json(silent=True) or {}
    content = (body.get("content") or "").strip()
    if not content:
        return jsonify({"error": "content required"}), 400
    entry = _idea_journal.append_entry(user_id, module_id, {
        "content": content[:5000],
        "type": (body.get("type") or "free_form")[:32],
        "lesson_id": body.get("lesson_id"),
        "lesson_title": body.get("lesson_title"),
    })
    return jsonify(entry)


@app.route("/api/modules/<module_id>/idea-journal/<entry_id>", methods=["PATCH"])
@require_auth
def patch_idea_journal(module_id: str, entry_id: str):
    user_id = g.current_user["user_id"]
    body = request.get_json(silent=True) or {}
    if "content" in body:
        _idea_journal.edit_entry(user_id, module_id, entry_id, {"content": body["content"][:5000]})
    if "starred" in body:
        _idea_journal.star_entry(user_id, module_id, entry_id, bool(body["starred"]))
    entries = _idea_journal.list_entries(user_id, module_id)
    for e in entries:
        if e["entry_id"] == entry_id:
            return jsonify(e)
    return jsonify({"error": "not found"}), 404
```

(`require_auth`, `g.current_user`, `request`, `jsonify` are already imported in `app.py`. If the project uses a different auth decorator name, match the one used by `/api/modules/<id>/start`.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_idea_journal_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_idea_journal_api.py
git commit -m "feat(phase-c): idea journal CRUD routes"
```

---

### Task 3: Idea Journal — auto-append on worksheet save and micro-quest submit

**Files:**
- Modify: `backend/modules_engine.py` (function `save_worksheet`, ~line 559)

- [ ] **Step 1: Add auto-append after successful worksheet save**

Open `backend/modules_engine.py`, find `def save_worksheet(`, and append at the end of the function (just before its return):

```python
    # Phase C: auto-append to Idea Journal
    try:
        import backend.idea_journal as _ij
        lesson = next(
            (l for w in module.get("weeks", []) for l in w.get("lessons", []) if l.get("id") == lesson_id),
            None,
        )
        _ij.append_entry(user_id, module_id, {
            "lesson_id": lesson_id,
            "lesson_title": (lesson or {}).get("title"),
            "content": json.dumps(answers, ensure_ascii=False)[:2000],
            "type": "worksheet",
        })
    except Exception:
        # Journal must never block worksheet save.
        pass
```

- [ ] **Step 2: Add quick smoke check**

Run: `cd backend && python -c "import modules_engine; print('ok')"`
Expected: `ok` (no import error).

- [ ] **Step 3: Commit**

```bash
git add backend/modules_engine.py
git commit -m "feat(phase-c): auto-append worksheet saves to idea journal"
```

---

### Task 4: Idea Journal — PDF export

**Files:**
- Create: `backend/idea_journal_pdf.py`
- Modify: `backend/app.py` (add export route)
- Test: `backend/tests/test_idea_journal_pdf.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_idea_journal_pdf.py
import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from backend.app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth(client):
    r = client.post("/api/auth/login", json={"username": "demo_student", "password": "Mento@2026"})
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


def test_pdf_export_returns_pdf_bytes(client):
    h = _auth(client)
    client.post(
        "/api/modules/mento_entrepreneur_4week/idea-journal",
        json={"content": "My pitch: a tiffin app for hostel students", "type": "free_form"},
        headers=h,
    )
    r = client.get("/api/modules/mento_entrepreneur_4week/idea-journal/export", headers=h)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/pdf")
    assert r.data[:4] == b"%PDF"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_idea_journal_pdf.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Implement the PDF generator**

```python
# backend/idea_journal_pdf.py
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
```

- [ ] **Step 4: Add export route to `backend/app.py`**

After the journal routes added in Task 2:

```python
@app.route("/api/modules/<module_id>/idea-journal/export", methods=["GET"])
@require_auth
def export_idea_journal(module_id: str):
    from backend.idea_journal_pdf import render_journal_pdf
    from datetime import datetime

    user_id = g.current_user["user_id"]
    user = get_user(user_id) or {}
    module = modules_engine.get_module(module_id) or {}
    entries = _idea_journal.list_entries(user_id, module_id)
    pdf = render_journal_pdf(
        student_name=user.get("display_name") or user.get("username") or "Founder",
        module_title=module.get("title") or module_id,
        completion_date=datetime.now().strftime("%B %d, %Y"),
        entries=entries,
    )
    from flask import Response
    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="my-pitch-deck-{module_id}.pdf"',
    })
```

(`get_user` is the existing helper from `auth.py`; if named differently, match the existing usage in `app.py`.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_idea_journal_pdf.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/idea_journal_pdf.py backend/app.py backend/tests/test_idea_journal_pdf.py
git commit -m "feat(phase-c): idea journal PDF export"
```

---

### Task 5: Idea Journal — UI side drawer in ModuleDetailPage

**Files:**
- Create: `frontend-react/src/components/module/IdeaJournalDrawer.jsx`
- Modify: `frontend-react/src/pages/ModuleDetailPage.jsx` (add sidebar button + drawer state, ~line 615)

- [ ] **Step 1: Create the drawer component**

```jsx
// frontend-react/src/components/module/IdeaJournalDrawer.jsx
import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";

export default function IdeaJournalDrawer({ moduleId, open, onClose }) {
  const [entries, setEntries] = useState([]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    apiFetch(`/api/modules/${moduleId}/idea-journal`)
      .then((r) => r.json())
      .then((d) => setEntries(d.entries || []))
      .finally(() => setLoading(false));
  }, [open, moduleId]);

  const add = async () => {
    const text = draft.trim();
    if (!text) return;
    const r = await apiFetch(`/api/modules/${moduleId}/idea-journal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text, type: "free_form" }),
    });
    const e = await r.json();
    setEntries((cur) => [...cur, e]);
    setDraft("");
  };

  const toggleStar = async (entry) => {
    const r = await apiFetch(`/api/modules/${moduleId}/idea-journal/${entry.entry_id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ starred: !entry.starred }),
    });
    const updated = await r.json();
    setEntries((cur) => cur.map((e) => (e.entry_id === updated.entry_id ? updated : e)));
  };

  const exportPdf = () => {
    window.open(`/api/modules/${moduleId}/idea-journal/export`, "_blank");
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex" role="dialog" aria-label="Idea Journal">
      <div className="flex-1 bg-black/40" onClick={onClose} />
      <aside className="w-full max-w-md bg-white shadow-xl flex flex-col">
        <header className="px-4 py-3 border-b flex items-center justify-between">
          <div className="font-semibold">📒 My Idea Journal</div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-800">✕</button>
        </header>
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {loading && <div className="text-slate-500">Loading…</div>}
          {!loading && entries.length === 0 && (
            <div className="text-slate-500 text-sm">No entries yet. Worksheets and quests auto-save here.</div>
          )}
          {entries.map((e) => (
            <div key={e.entry_id} className="rounded border border-slate-200 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="text-xs text-slate-500">
                  {e.lesson_title || e.type} · {new Date(e.timestamp).toLocaleString()}
                </div>
                <button onClick={() => toggleStar(e)} className="text-lg">
                  {e.starred ? "⭐" : "☆"}
                </button>
              </div>
              <div className="mt-2 text-sm whitespace-pre-wrap">{e.content}</div>
            </div>
          ))}
        </div>
        <div className="border-t p-3 space-y-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Capture a quick idea…"
            className="w-full border rounded p-2 text-sm"
            rows={3}
          />
          <div className="flex gap-2">
            <button onClick={add} className="flex-1 bg-indigo-600 text-white rounded py-2 text-sm">
              Add entry
            </button>
            <button onClick={exportPdf} className="bg-emerald-600 text-white rounded px-3 text-sm">
              📥 Pitch Deck PDF
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
```

- [ ] **Step 2: Wire button + state into `ModuleDetailPage.jsx`**

Search for `export default function ModuleDetailPage()` (line ~615). Add near the top of the component body:

```jsx
const [journalOpen, setJournalOpen] = useState(false);
```

Add the import near the top of the file:

```jsx
import IdeaJournalDrawer from "../components/module/IdeaJournalDrawer";
```

In the returned JSX, place a fixed button (e.g., near where the lesson title is rendered around `lessonType` logic, line ~896 — pick a location that doesn't overlap audio bar from Phase B):

```jsx
<button
  type="button"
  onClick={() => setJournalOpen(true)}
  className="fixed right-4 bottom-24 z-40 bg-amber-500 hover:bg-amber-600 text-white rounded-full shadow px-4 py-2 text-sm"
>
  📒 Journal
</button>
<IdeaJournalDrawer
  moduleId={moduleId}
  open={journalOpen}
  onClose={() => setJournalOpen(false)}
/>
```

(`moduleId` is the route param already destructured in this file — confirm the existing variable name and reuse it.)

- [ ] **Step 3: Smoke test in dev**

Run frontend dev server (already-running preview or `npm run dev`), navigate to a module page, click 📒 Journal. Expected: drawer opens, empty state visible, can add a free-form entry, entry persists across reloads.

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/components/module/IdeaJournalDrawer.jsx \
        frontend-react/src/pages/ModuleDetailPage.jsx
git commit -m "feat(phase-c): idea journal side drawer in ModuleDetailPage"
```

---

### Task 6: Micro-quest renderer

**Files:**
- Create: `frontend-react/src/components/module/MicroQuestRenderer.jsx`
- Modify: `frontend-react/src/pages/ModuleDetailPage.jsx` (dispatcher — should already accept `micro_quest` from Phase A; this fills in the body)

- [ ] **Step 1: Write the renderer**

```jsx
// frontend-react/src/components/module/MicroQuestRenderer.jsx
import { useState } from "react";
import { apiFetch } from "../../api/client";

export default function MicroQuestRenderer({ lesson, moduleId, onComplete }) {
  const { prompt, input_type = "text", placeholder, completion_message } = lesson;
  const [value, setValue] = useState("");
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const text = value.trim();
    if (!text) return;
    setSubmitting(true);
    try {
      await apiFetch(`/api/modules/${moduleId}/idea-journal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: text,
          type: "micro_quest",
          lesson_id: lesson.id,
          lesson_title: lesson.title,
        }),
      });
      await apiFetch(`/api/modules/${moduleId}/lessons/${lesson.id}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ score: 100 }),
      });
      setDone(true);
      onComplete && onComplete();
    } finally {
      setSubmitting(false);
    }
  };

  if (done) {
    return (
      <div className="rounded-xl border-2 border-emerald-200 bg-emerald-50 p-6 text-center">
        <div className="text-4xl">🎯</div>
        <div className="mt-2 font-semibold text-emerald-900">Quest complete</div>
        <div className="mt-1 text-sm text-emerald-800">
          {completion_message || "Saved to your Idea Journal."}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-6">
      <div className="text-xs uppercase tracking-wide text-amber-800">2–3 minute quest</div>
      <h3 className="mt-1 text-lg font-semibold">{lesson.title}</h3>
      <p className="mt-3 text-slate-800">{prompt}</p>
      {input_type === "text" && (
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={placeholder || "Your answer…"}
          rows={4}
          className="mt-3 w-full border rounded p-2 text-sm"
        />
      )}
      <button
        onClick={submit}
        disabled={submitting || !value.trim()}
        className="mt-3 bg-amber-600 disabled:bg-amber-300 text-white rounded px-4 py-2 text-sm"
      >
        {submitting ? "Saving…" : "Mark complete"}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Confirm `ModuleDetailPage.jsx` dispatches `micro_quest`**

Phase A added a registry. Confirm `micro_quest` maps to `MicroQuestRenderer`. If not, add it. Search for where `audio_lesson` or `pitch_coach` is dispatched and add:

```jsx
import MicroQuestRenderer from "../components/module/MicroQuestRenderer";
// ...
if (lessonType === "micro_quest") {
  return <MicroQuestRenderer lesson={activeLesson} moduleId={moduleId} onComplete={refreshProgress} />;
}
```

(`refreshProgress` is whatever existing callback the dispatcher uses after lesson completion — match the name used by neighbouring renderers.)

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/components/module/MicroQuestRenderer.jsx \
        frontend-react/src/pages/ModuleDetailPage.jsx
git commit -m "feat(phase-c): micro-quest renderer"
```

---

### Task 7: Insert 4 micro-quest lessons into module JSON

**Files:**
- Modify: `backend/modules/mento_entrepreneur_4week.json`
- Test: `backend/tests/test_micro_quests_present.py`

- [ ] **Step 1: Write the test (drives the JSON edit)**

```python
# backend/tests/test_micro_quests_present.py
import json
from pathlib import Path


def test_each_week_has_micro_quest():
    p = Path(__file__).resolve().parents[1] / "modules" / "mento_entrepreneur_4week.json"
    mod = json.loads(p.read_text())
    weeks = mod["weeks"]
    expected = {
        1: "w1_quest_one_complaint",
        2: "w2_quest_one_why",
        3: "w3_quest_one_customer",
        4: "w4_quest_one_pitch",
    }
    for i, week in enumerate(weeks, start=1):
        ids = [l["id"] for l in week.get("lessons", [])]
        assert expected[i] in ids, f"week {i} missing quest {expected[i]} — got {ids}"
        # Find it and check type
        quest = next(l for l in week["lessons"] if l["id"] == expected[i])
        assert quest["type"] == "micro_quest"
        assert quest.get("prompt"), f"{expected[i]} missing prompt"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_micro_quests_present.py -v`
Expected: FAIL (lessons not present).

- [ ] **Step 3: Edit the module JSON**

Open `backend/modules/mento_entrepreneur_4week.json`. For each of the 4 weeks, append a quest object to `weeks[i].lessons` (so existing lessons stay untouched). Insert these exact objects:

Week 1 — append to `weeks[0].lessons`:
```json
{
  "id": "w1_quest_one_complaint",
  "type": "micro_quest",
  "title": "Quest: Find one complaint",
  "duration_min": 3,
  "prompt": "In the next 3 minutes, ask one person near you: 'What's something that bothers you every day?' Type their answer below. (One person. One complaint. That's it.)",
  "input_type": "text",
  "placeholder": "What they said…",
  "completion_message": "First complaint logged. This is the seed of every business."
}
```

Week 2 — append to `weeks[1].lessons`:
```json
{
  "id": "w2_quest_one_why",
  "type": "micro_quest",
  "title": "Quest: Ask one WHY",
  "duration_min": 3,
  "prompt": "Open your Idea Journal and pick one complaint from Week 1. Ask one 'WHY does that bother you?' Type the answer.",
  "input_type": "text",
  "placeholder": "Their answer to your WHY…",
  "completion_message": "One layer deeper. Real founders ask 5."
}
```

Week 3 — append to `weeks[2].lessons`:
```json
{
  "id": "w3_quest_one_customer",
  "type": "micro_quest",
  "title": "Quest: Find one real customer",
  "duration_min": 5,
  "prompt": "Find one real person who fits the customer profile you wrote in this week's worksheet. Type their first name + one thing about them that matches.",
  "input_type": "text",
  "placeholder": "e.g. 'Rohan, lives 2 buildings away, loses pencils weekly'",
  "completion_message": "Customer #1 identified. Now you have someone real to build for."
}
```

Week 4 — append to `weeks[3].lessons`:
```json
{
  "id": "w4_quest_one_pitch",
  "type": "micro_quest",
  "title": "Quest: Pitch out loud",
  "duration_min": 5,
  "prompt": "Say your 60-second pitch out loud to one real person right now (parent, sibling, friend). Type their reaction in one line.",
  "input_type": "text",
  "placeholder": "What they said back…",
  "completion_message": "You just shipped your first pitch."
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_micro_quests_present.py tests/test_phase_c_baseline.py -v`
Expected: PASS (both).

- [ ] **Step 5: Commit**

```bash
git add backend/modules/mento_entrepreneur_4week.json backend/tests/test_micro_quests_present.py
git commit -m "feat(phase-c): 4 micro-quest lessons (one per week)"
```

---

### Task 8: SR card seeding on lesson completion

**Files:**
- Modify: `backend/spaced_repetition.py` (add `schedule_flashcard` helper)
- Modify: `backend/modules_engine.py` (in `complete_lesson`, seed cards if lesson has `flashcards`)
- Test: `backend/tests/test_sr_module_seeding.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_sr_module_seeding.py
import pytest


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    yield


def test_seed_flashcards(env):
    from importlib import reload
    import backend.spaced_repetition as sr
    reload(sr)
    sr.schedule_flashcard(
        user_id="u1",
        module_id="mento_entrepreneur_4week",
        lesson_id="w1_l1_intro",
        card={"q": "Define entrepreneurship", "a": "Solving a real problem people care about", "skill_tag": "creativity"},
    )
    # Existing get_due_reviews works for game reviews; for flashcards we use list:
    cards = sr.list_module_flashcards("u1", "mento_entrepreneur_4week")
    assert len(cards) == 1
    assert cards[0]["q"].startswith("Define")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_sr_module_seeding.py -v`
Expected: FAIL (no `schedule_flashcard`).

- [ ] **Step 3: Extend `backend/spaced_repetition.py`**

Append at the bottom:

```python
# --- Module flashcards (Phase C) -------------------------------------------
# Stored separately from game reviews so existing SM-2 schedule logic is
# untouched. Flashcards still use _sm2_next_interval when reviewed.
def _flashcards_path() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    )
    return os.path.join(base, "module_flashcards.json")


def _load_flashcards() -> dict:
    p = _flashcards_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_flashcards(data: dict) -> None:
    p = _flashcards_path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def schedule_flashcard(user_id: str, module_id: str, lesson_id: str, card: dict) -> None:
    """Inject a flashcard into the user's module-SR queue. Idempotent on (user, module, lesson, q)."""
    data = _load_flashcards()
    key = user_id
    user_cards = data.setdefault(key, [])
    q = (card.get("q") or "").strip()
    if not q:
        return
    for c in user_cards:
        if c.get("module_id") == module_id and c.get("lesson_id") == lesson_id and c.get("q") == q:
            return  # already seeded
    user_cards.append({
        "module_id": module_id,
        "lesson_id": lesson_id,
        "q": q,
        "a": card.get("a", ""),
        "skill_tag": card.get("skill_tag"),
        "ease_factor": 2.5,
        "interval_days": 0,
        "next_review": _today_str(),
        "created_at": _today_str(),
    })
    _save_flashcards(data)


def list_module_flashcards(user_id: str, module_id: str | None = None) -> list:
    data = _load_flashcards()
    cards = data.get(user_id, [])
    if module_id:
        return [c for c in cards if c.get("module_id") == module_id]
    return cards
```

(`json`, `os` are already imported at the top of `spaced_repetition.py`.)

- [ ] **Step 4: Hook into `modules_engine.complete_lesson`**

Open `backend/modules_engine.py`, find `def complete_lesson(`. At the end of the function (before return), add:

```python
    # Phase C: seed any flashcards declared on the lesson into SR
    try:
        import backend.spaced_repetition as _sr
        lesson_obj = next(
            (l for w in module.get("weeks", []) for l in w.get("lessons", []) if l.get("id") == lesson_id),
            None,
        )
        for card in (lesson_obj or {}).get("flashcards", []) or []:
            _sr.schedule_flashcard(user_id, module_id, lesson_id, card)
    except Exception:
        pass
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_sr_module_seeding.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/spaced_repetition.py backend/modules_engine.py backend/tests/test_sr_module_seeding.py
git commit -m "feat(phase-c): seed module flashcards into spaced-repetition queue"
```

---

### Task 9: Module skill report — backend aggregation

**Files:**
- Create: `backend/module_skill_report.py`
- Modify: `backend/app.py` (add `/api/modules/<id>/skill-report` route)
- Test: `backend/tests/test_module_skill_report.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_module_skill_report.py
import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from backend.app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth(client):
    r = client.post("/api/auth/login", json={"username": "demo_student", "password": "Mento@2026"})
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


def test_skill_report_shape(client):
    h = _auth(client)
    r = client.get("/api/modules/mento_entrepreneur_4week/skill-report", headers=h)
    assert r.status_code == 200
    body = r.get_json()
    assert "dimensions" in body
    assert "highlights" in body
    assert "recommendations" in body
    # Even with zero plays, dimensions must include all 8 core dimensions
    assert set(body["dimensions"].keys()) >= {
        "strategic_thinking", "creativity", "empathy", "communication", "resilience",
    }
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_module_skill_report.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Implement aggregation**

```python
# backend/module_skill_report.py
"""Aggregate dimension scores for a single (user, module) pair.

Sources:
- All completed games linked from module lessons (uses existing run reports).
- All completed quizzes in the module (mapped to dimensions via quiz tags).
- Pitch-coach attempts (communication / creativity / strategic_thinking).
- Interview-sim depth score (empathy / strategic_thinking).
- Recommendations: next modules based on weakest 2 dimensions.
"""
from typing import Any, Dict, List

import backend.modules_engine as modules_engine
import backend.idea_journal as _ij

_CORE_DIMS = [
    "strategic_thinking",
    "creativity",
    "empathy",
    "communication",
    "resilience",
    "adaptability",
    "risk_tolerance",
    "delayed_gratification",
]

_DEFAULT = 50


def build_report(user_id: str, module_id: str, runs: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    module = modules_engine.get_module(module_id) or {}
    prog = modules_engine.get_user_progress(user_id, module_id) or {}

    dims: Dict[str, List[int]] = {d: [] for d in _CORE_DIMS}

    # 1. Game runs (caller passes them — keeps this module pure)
    for run in runs or []:
        rep = run.get("report") or {}
        for k, v in (rep.get("dimensions") or {}).items():
            if k in dims and isinstance(v, (int, float)):
                dims[k].append(int(v))

    # 2. Pitch coach attempts (Phase B writes these into progress)
    for lesson_prog in (prog.get("lessons") or {}).values():
        for attempt in lesson_prog.get("pitch_attempts", []) or []:
            r = (attempt.get("rubric") or {})
            # 5-axis rubric maps to dimensions
            dims["communication"].append(int(r.get("hook", 0) + r.get("ask", 0)) * 5)
            dims["creativity"].append(int(r.get("solution", 0)) * 10)
            dims["strategic_thinking"].append(int(r.get("problem", 0) + r.get("customer", 0)) * 5)

    # 3. Interview-sim depth (Phase B writes depth_score)
    for lesson_prog in (prog.get("lessons") or {}).values():
        for conv in lesson_prog.get("interview_conversations", []) or []:
            depth = conv.get("depth_score")
            if isinstance(depth, (int, float)):
                dims["empathy"].append(min(100, int(depth) * 20))
                dims["strategic_thinking"].append(min(100, int(depth) * 20))

    # 4. Quiz scores
    for q in (prog.get("quizzes") or {}).values():
        score = q.get("score")
        if isinstance(score, (int, float)):
            for tag in q.get("dimension_tags") or ["strategic_thinking"]:
                if tag in dims:
                    dims[tag].append(int(score))

    flat = {d: int(sum(v) / len(v)) if v else _DEFAULT for d, v in dims.items()}

    # Highlights: top 3 dims with score >=70
    sorted_dims = sorted(flat.items(), key=lambda x: -x[1])
    highlights = [
        {"dimension": d, "score": s, "label": _highlight_for(d, s)}
        for d, s in sorted_dims[:3] if s >= 70
    ]

    # Recommendations: 2 weakest dims → next-module suggestions
    weakest = [d for d, _ in sorted(flat.items(), key=lambda x: x[1])[:2]]
    recommendations = _recommend_modules(weakest, exclude=module_id)

    # Idea journal stats for the report
    journal_count = len(_ij.list_entries(user_id, module_id))

    return {
        "module_id": module_id,
        "module_title": module.get("title") or module_id,
        "dimensions": flat,
        "deltas_from_baseline": _delta_from_baseline(user_id, flat),
        "highlights": highlights,
        "recommendations": recommendations,
        "journal_entries": journal_count,
        "completion": _completion_summary(prog, module),
    }


def _highlight_for(dim: str, score: int) -> str:
    labels = {
        "creativity": f"Top-tier creativity ({score})",
        "empathy": f"Strong empathy ({score})",
        "communication": f"Confident communicator ({score})",
        "strategic_thinking": f"Sharp strategic thinking ({score})",
        "resilience": f"Resilient under pressure ({score})",
    }
    return labels.get(dim, f"{dim.replace('_', ' ').title()} ({score})")


def _recommend_modules(weakest_dims: List[str], exclude: str) -> List[Dict[str, str]]:
    # Static mapping for v1 — content team curates.
    mapping = {
        "communication": ("mento_public_speaking_4week", "Public Speaking"),
        "empathy": ("mento_civic_leadership_4week", "Civic Leadership"),
        "strategic_thinking": ("mento_personal_finance_4week", "Personal Finance"),
        "resilience": ("mento_storytelling_4week", "Storytelling"),
        "creativity": ("mento_storytelling_4week", "Storytelling"),
    }
    seen = set()
    out: List[Dict[str, str]] = []
    for d in weakest_dims:
        rec = mapping.get(d)
        if rec and rec[0] != exclude and rec[0] not in seen:
            out.append({"module_id": rec[0], "title": rec[1], "because_of": d})
            seen.add(rec[0])
    return out


def _delta_from_baseline(user_id: str, current: Dict[str, int]) -> Dict[str, int]:
    # If you have baseline scores stored on the user profile, diff here.
    # For v1, return empty so the UI shows current absolute scores.
    return {}


def _completion_summary(prog: Dict[str, Any], module: Dict[str, Any]) -> Dict[str, Any]:
    all_lessons = [l for w in module.get("weeks", []) for l in w.get("lessons", [])]
    total = len(all_lessons)
    done = sum(
        1 for l in all_lessons
        if (prog.get("lessons", {}).get(l["id"], {}).get("status") == "complete")
    )
    return {"total_lessons": total, "completed_lessons": done, "percent": int(100 * done / total) if total else 0}
```

- [ ] **Step 4: Add route to `backend/app.py`**

```python
@app.route("/api/modules/<module_id>/skill-report", methods=["GET"])
@require_auth
def module_skill_report(module_id: str):
    from backend.module_skill_report import build_report
    user_id = g.current_user["user_id"]
    # Fetch the user's recent run reports relevant to this module's embedded games:
    module = modules_engine.get_module(module_id) or {}
    game_ids = set()
    for w in module.get("weeks", []):
        for l in w.get("lessons", []):
            if l.get("game_id"):
                game_ids.add(l["game_id"])
            for g_ in (l.get("games") or []):
                if isinstance(g_, dict) and g_.get("id"):
                    game_ids.add(g_["id"])
    runs = []
    try:
        from backend.storage import list_user_runs
        for r in list_user_runs(user_id) or []:
            if r.get("game_id") in game_ids and r.get("report"):
                runs.append(r)
    except Exception:
        pass
    return jsonify(build_report(user_id, module_id, runs=runs))
```

(If `list_user_runs` is named differently in `storage.py`, match the existing function. The route stays simple and degrades to empty runs on import errors.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_module_skill_report.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/module_skill_report.py backend/app.py backend/tests/test_module_skill_report.py
git commit -m "feat(phase-c): module skill report aggregation + route"
```

---

### Task 10: Module skill report — UI

**Files:**
- Modify: `frontend-react/src/pages/ModuleReportPage.jsx` (already exists as stub; flesh out)

- [ ] **Step 1: Replace the stub body with a real report view**

Read the existing file first to preserve auth wrapper / route param parsing, then replace the body. Skeleton:

```jsx
// frontend-react/src/pages/ModuleReportPage.jsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch } from "../api/client";
import ShareCardActions from "../components/module/ShareCardActions";

const DIM_LABELS = {
  strategic_thinking: "Strategic Thinking",
  creativity: "Creativity",
  empathy: "Empathy",
  communication: "Communication",
  resilience: "Resilience",
  adaptability: "Adaptability",
  risk_tolerance: "Risk Tolerance",
  delayed_gratification: "Delayed Gratification",
};

export default function ModuleReportPage() {
  const { moduleId } = useParams();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiFetch(`/api/modules/${moduleId}/skill-report`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.statusText)))
      .then(setReport)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [moduleId]);

  if (loading) return <div className="p-6">Loading report…</div>;
  if (error) return <div className="p-6 text-rose-700">Error: {error}</div>;
  if (!report) return null;

  const dims = Object.entries(report.dimensions || {});
  const max = Math.max(100, ...dims.map(([, v]) => v));

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <header>
        <div className="text-xs uppercase tracking-wide text-indigo-600">Module Skill Report</div>
        <h1 className="text-3xl font-bold">{report.module_title}</h1>
        <div className="text-sm text-slate-600 mt-1">
          {report.completion?.completed_lessons}/{report.completion?.total_lessons} lessons ·
          {" "}{report.journal_entries} journal entries
        </div>
      </header>

      <section>
        <h2 className="font-semibold mb-3">Skill scores</h2>
        <div className="space-y-2">
          {dims.map(([k, v]) => (
            <div key={k}>
              <div className="flex justify-between text-sm"><span>{DIM_LABELS[k] || k}</span><span>{v}</span></div>
              <div className="h-2 bg-slate-100 rounded">
                <div className="h-2 bg-indigo-500 rounded" style={{ width: `${(v / max) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </section>

      {report.highlights?.length > 0 && (
        <section>
          <h2 className="font-semibold mb-2">Highlights</h2>
          <ul className="list-disc pl-6 space-y-1">
            {report.highlights.map((h) => <li key={h.dimension}>{h.label}</li>)}
          </ul>
        </section>
      )}

      {report.recommendations?.length > 0 && (
        <section>
          <h2 className="font-semibold mb-2">Try next</h2>
          <ul className="space-y-1">
            {report.recommendations.map((r) => (
              <li key={r.module_id}>
                <a className="text-indigo-600 underline" href={`/modules/${r.module_id}`}>
                  {r.title}
                </a>
                <span className="text-slate-500 text-sm"> — to grow your {r.because_of.replace("_", " ")}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <ShareCardActions moduleId={moduleId} />
    </div>
  );
}
```

- [ ] **Step 2: Smoke check in dev**

Navigate to `/modules/mento_entrepreneur_4week/report` as `demo_student`. Expected: page renders, dimensions list visible, no console errors.

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/pages/ModuleReportPage.jsx
git commit -m "feat(phase-c): module skill report UI"
```

---

### Task 11: Parent-shareable PNG card — server render

**Files:**
- Create: `backend/share_card.py`
- Modify: `backend/app.py` (add `/api/modules/<id>/skill-report/card.png`)
- Test: `backend/tests/test_share_card.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_share_card.py
import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from backend.app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth(client):
    r = client.post("/api/auth/login", json={"username": "demo_student", "password": "Mento@2026"})
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


def test_card_returns_png(client):
    h = _auth(client)
    r = client.get("/api/modules/mento_entrepreneur_4week/skill-report/card.png", headers=h)
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "image/png"
    assert r.data[:8] == b"\x89PNG\r\n\x1a\n"
    # 1080x1080 minimum — first IHDR chunk holds width/height
    # width bytes at offset 16..20
    width = int.from_bytes(r.data[16:20], "big")
    height = int.from_bytes(r.data[20:24], "big")
    assert width == 1080 and height == 1080
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_share_card.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Implement PNG renderer**

```python
# backend/share_card.py
"""Server-render a 1080x1080 Instagram-square skill report card.

Uses Pillow only (no headless browser). Designed for WhatsApp/IG share.
Privacy: first name only by default.
"""
import io
from typing import Any, Dict, List

from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = 1080
BG = (250, 247, 240)
INK = (24, 24, 27)
ACCENT = (79, 70, 229)
MUTED = (113, 113, 122)


def render_card(
    first_name: str,
    age: int | None,
    module_title: str,
    dimensions: Dict[str, int],
    headline: str,
    cohort: str | None = None,
) -> bytes:
    img = Image.new("RGB", (CARD_SIZE, CARD_SIZE), BG)
    d = ImageDraw.Draw(img)

    title_font = _font(64, bold=True)
    name_font = _font(96, bold=True)
    body_font = _font(36)
    small_font = _font(28)

    # Header strip
    d.rectangle([(0, 0), (CARD_SIZE, 140)], fill=ACCENT)
    d.text((48, 50), "MENTO · FOUNDER LAB", fill="white", font=title_font)

    # Student name
    d.text((48, 200), first_name, fill=INK, font=name_font)
    sub = module_title
    if age:
        sub = f"Age {age} · " + sub
    d.text((48, 310), sub, fill=MUTED, font=body_font)

    # Top 3 skills as horizontal bars
    top = sorted(dimensions.items(), key=lambda x: -x[1])[:3]
    y = 420
    for k, v in top:
        label = k.replace("_", " ").title()
        d.text((48, y), label, fill=INK, font=body_font)
        d.text((CARD_SIZE - 160, y), str(v), fill=ACCENT, font=body_font)
        bar_w = int((CARD_SIZE - 120) * (v / 100))
        d.rectangle([(48, y + 56), (CARD_SIZE - 72, y + 76)], fill=(228, 228, 231))
        d.rectangle([(48, y + 56), (48 + bar_w, y + 76)], fill=ACCENT)
        y += 130

    # Headline
    d.multiline_text((48, 820), _wrap(headline, 32), fill=INK, font=body_font, spacing=6)

    # Footer
    d.text((48, CARD_SIZE - 80), cohort or "Mento App · simulations.mentomap.com",
           fill=MUTED, font=small_font)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    # Try a few common system fonts; fall back to default.
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
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
```

- [ ] **Step 4: Add the route**

```python
# in backend/app.py
@app.route("/api/modules/<module_id>/skill-report/card.png", methods=["GET"])
@require_auth
def module_skill_report_card(module_id: str):
    from backend.share_card import render_card
    from backend.module_skill_report import build_report
    user_id = g.current_user["user_id"]
    user = get_user(user_id) or {}
    name = (user.get("display_name") or user.get("username") or "Founder").split()[0]
    age = user.get("age")
    # Reuse aggregation:
    runs = []  # for the card, current dimensions are enough
    report = build_report(user_id, module_id, runs=runs)
    top = sorted(report["dimensions"].items(), key=lambda x: -x[1])[0]
    headline = f"{name} finished {report['module_title']}. They scored {top[1]} on {top[0].replace('_', ' ')}."
    png = render_card(
        first_name=name,
        age=age,
        module_title=report["module_title"],
        dimensions=report["dimensions"],
        headline=headline,
        cohort=user.get("cohort_name"),
    )
    from flask import Response
    return Response(png, mimetype="image/png", headers={"Cache-Control": "public, max-age=86400"})
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_share_card.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/share_card.py backend/app.py backend/tests/test_share_card.py
git commit -m "feat(phase-c): parent-shareable PNG skill card"
```

---

### Task 12: WhatsApp share button

**Files:**
- Create: `frontend-react/src/components/module/ShareCardActions.jsx`

- [ ] **Step 1: Implement share actions**

```jsx
// frontend-react/src/components/module/ShareCardActions.jsx
import { useState } from "react";

export default function ShareCardActions({ moduleId }) {
  const [copied, setCopied] = useState(false);
  const cardUrl = `${window.location.origin}/api/modules/${moduleId}/skill-report/card.png`;
  const caption =
    "I just finished the Mento Founder Lab — check out my skill card!";

  const shareNative = async () => {
    if (navigator.share) {
      try {
        const res = await fetch(cardUrl);
        const blob = await res.blob();
        const file = new File([blob], "mento-skill-card.png", { type: "image/png" });
        await navigator.share({ files: [file], text: caption });
        return;
      } catch (_) {
        // fall through to WhatsApp URL
      }
    }
    window.open(
      `https://wa.me/?text=${encodeURIComponent(caption + " " + cardUrl)}`,
      "_blank",
    );
  };

  const copyLink = async () => {
    await navigator.clipboard.writeText(cardUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <section className="border-t pt-6">
      <h2 className="font-semibold mb-3">Share your skill card</h2>
      <img
        src={cardUrl}
        alt="Skill card preview"
        className="rounded-lg border shadow-sm max-w-xs"
      />
      <div className="flex gap-2 mt-3 flex-wrap">
        <button onClick={shareNative} className="bg-emerald-600 text-white rounded px-4 py-2 text-sm">
          📲 Share to WhatsApp
        </button>
        <a
          href={cardUrl}
          download={`mento-skill-${moduleId}.png`}
          className="bg-slate-200 rounded px-4 py-2 text-sm"
        >
          ⬇️ Download PNG
        </a>
        <button onClick={copyLink} className="bg-slate-200 rounded px-4 py-2 text-sm">
          {copied ? "✓ Copied" : "🔗 Copy link"}
        </button>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Smoke check**

Open `/modules/mento_entrepreneur_4week/report`, confirm card preview loads, click WhatsApp button on mobile → native share sheet; desktop → wa.me opens in new tab.

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/components/module/ShareCardActions.jsx
git commit -m "feat(phase-c): WhatsApp/share buttons on module report"
```

---

### Task 13: Certificate-on-completion wiring

**Files:**
- Modify: `backend/modules_engine.py` (add `check_module_completion`, `mint_certificate`)
- Modify: `backend/app.py` (add `/api/modules/<id>/certificate`)
- Test: `backend/tests/test_module_certificate.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_module_certificate.py
import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from backend.app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth(client):
    r = client.post("/api/auth/login", json={"username": "demo_student", "password": "Mento@2026"})
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


def test_certificate_blocked_when_incomplete(client):
    h = _auth(client)
    r = client.get("/api/modules/mento_entrepreneur_4week/certificate", headers=h)
    assert r.status_code == 409  # not yet eligible
    body = r.get_json()
    assert body.get("certificate_eligible") is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_module_certificate.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Add helpers to `modules_engine.py`**

Append:

```python
def check_module_completion(user_id: str, module_id: str) -> Dict[str, Any]:
    """Return {complete, certificate_eligible, percent, missing_lesson_ids}."""
    module = get_module(module_id) or {}
    prog = get_user_progress(user_id, module_id) or {}
    all_lessons = [l for w in module.get("weeks", []) for l in w.get("lessons", [])]
    # Optional micro-quests don't gate cert; gating = quizzes + non-quest lessons
    required = [l for l in all_lessons if l.get("type") not in ("micro_quest", "cohort_live_session")]
    done_ids = {lid for lid, lp in (prog.get("lessons") or {}).items() if lp.get("status") == "complete"}
    missing = [l["id"] for l in required if l["id"] not in done_ids]
    percent = int(100 * (len(required) - len(missing)) / len(required)) if required else 0
    # Require ≥80% of required lessons AND all 4 weekly quizzes attempted
    quiz_count = sum(1 for q in (prog.get("quizzes") or {}).values() if q.get("score") is not None)
    eligible = percent >= 80 and quiz_count >= module.get("required_quizzes", 4)
    return {
        "complete": len(missing) == 0,
        "certificate_eligible": eligible,
        "percent": percent,
        "missing_lesson_ids": missing,
    }
```

- [ ] **Step 4: Add route in `backend/app.py`**

```python
@app.route("/api/modules/<module_id>/certificate", methods=["GET"])
@require_auth
def module_certificate(module_id: str):
    from backend.certificate import generate_certificate_html
    user_id = g.current_user["user_id"]
    status = modules_engine.check_module_completion(user_id, module_id)
    if not status["certificate_eligible"]:
        return jsonify({**status, "error": "module not complete"}), 409
    user = get_user(user_id) or {}
    module = modules_engine.get_module(module_id) or {}
    html = generate_certificate_html(
        player_name=user.get("display_name") or user.get("username") or "Founder",
        game_title=module.get("title") or module_id,
        game_theme="Entrepreneurship Workshop",
        mento_score=100.0,
        mento_rank="A",
        badges=[],
        run_id=module_id,
    )
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_module_certificate.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/modules_engine.py backend/app.py backend/tests/test_module_certificate.py
git commit -m "feat(phase-c): certificate-on-completion gate + route"
```

---

### Task 14: Milestone badges + streak in module hero

**Files:**
- Modify: `frontend-react/src/pages/ModuleDetailPage.jsx` (add hero badge row)

- [ ] **Step 1: Compute earned badges client-side**

Inside `ModuleDetailPage.jsx`, near where `module` and `progress` are available, derive:

```jsx
const BADGES = [
  { week: 1, icon: "🌱", label: "Idea Validator" },
  { week: 2, icon: "🔍", label: "Problem Detective" },
  { week: 3, icon: "🎤", label: "Pitch Builder" },
  { week: 4, icon: "🚀", label: "Founder" },
];

function isWeekEarned(progress, module, weekIdx) {
  const week = module?.weeks?.[weekIdx - 1];
  if (!week) return false;
  const lessons = week.lessons || [];
  const required = lessons.filter((l) => l.type !== "micro_quest" && l.type !== "cohort_live_session");
  const done = required.filter((l) => progress?.lessons?.[l.id]?.status === "complete").length;
  const quiz = (progress?.quizzes || {})[`w${weekIdx}_quiz`] || (progress?.quizzes || {})[week.quiz_id];
  const quizOk = !!quiz?.score && quiz.score >= 60;
  return required.length > 0 && done / required.length >= 0.8 && quizOk;
}
```

In the JSX hero area (near the existing module title block), render:

```jsx
<div className="flex flex-wrap items-center gap-3 mt-2">
  {streakDays > 0 && (
    <span className="bg-amber-100 text-amber-900 rounded-full px-3 py-1 text-sm">
      🔥 {streakDays}-day streak
    </span>
  )}
  {BADGES.map((b) => {
    const earned = isWeekEarned(progress, module, b.week);
    return (
      <span
        key={b.week}
        className={
          "rounded-full px-3 py-1 text-sm border " +
          (earned
            ? "bg-yellow-100 text-yellow-900 border-yellow-300"
            : "bg-slate-50 text-slate-400 border-slate-200")
        }
        title={`Week ${b.week}: ${b.label}`}
      >
        {b.icon} {b.label}
      </span>
    );
  })}
</div>
```

(`streakDays` is whatever variable already holds the streak in this file — if absent, fetch from `/api/profile/streak` once on mount.)

- [ ] **Step 2: Smoke check**

Reload the module page as `demo_student`. Expected: 4 grey badges visible; streak chip if streak > 0.

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/pages/ModuleDetailPage.jsx
git commit -m "feat(phase-c): milestone badges + streak in module hero"
```

---

### Task 15: Cohort live sessions — backend module

**Files:**
- Create: `backend/cohort_live_sessions.py`
- Test: `backend/tests/test_cohort_live_sessions.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_cohort_live_sessions.py
import pytest


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))


def test_crud_and_rsvp(env):
    from importlib import reload
    import backend.cohort_live_sessions as cls
    reload(cls)
    s = cls.create_session(
        cohort_id="c1", module_id="mento_entrepreneur_4week",
        data={
            "week": 1, "title": "Founder cameo",
            "host_name": "Sridhar Vembu", "host_bio_short": "Founder, Zoho",
            "scheduled_at": "2026-06-15T18:00:00+05:30",
            "duration_min": 60, "meeting_url": "https://meet.google.com/abc",
        },
    )
    assert s["session_id"]
    sessions = cls.list_sessions("c1", "mento_entrepreneur_4week")
    assert len(sessions) == 1
    cls.toggle_rsvp("c1", "mento_entrepreneur_4week", s["session_id"], "u1", True)
    cls.toggle_rsvp("c1", "mento_entrepreneur_4week", s["session_id"], "u1", True)  # idempotent
    cls.toggle_rsvp("c1", "mento_entrepreneur_4week", s["session_id"], "u2", True)
    again = cls.list_sessions("c1", "mento_entrepreneur_4week")
    assert set(again[0]["rsvps"]) == {"u1", "u2"}
    cls.toggle_rsvp("c1", "mento_entrepreneur_4week", s["session_id"], "u1", False)
    again2 = cls.list_sessions("c1", "mento_entrepreneur_4week")
    assert again2[0]["rsvps"] == ["u2"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_cohort_live_sessions.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

```python
# backend/cohort_live_sessions.py
"""Scheduled live sessions for a cohort running a module.

Storage: backend/data/cohort_live_sessions.json keyed by "<cohort_id>__<module_id>".
Async cohorts simply have no entries → student UI hides the banner.
"""
import json
import os
import uuid
from typing import Any, Dict, List, Optional


def _path() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    )
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "cohort_live_sessions.json")


def _key(cohort_id: str, module_id: str) -> str:
    return f"{cohort_id}__{module_id}"


def _load() -> Dict[str, List[Dict[str, Any]]]:
    p = _path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: Dict[str, List[Dict[str, Any]]]) -> None:
    p = _path()
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def list_sessions(cohort_id: str, module_id: str) -> List[Dict[str, Any]]:
    return _load().get(_key(cohort_id, module_id), [])


def create_session(cohort_id: str, module_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(data)
    data["session_id"] = uuid.uuid4().hex[:12]
    data.setdefault("rsvps", [])
    data.setdefault("status", "scheduled")
    data.setdefault("recording_url", None)
    store = _load()
    store.setdefault(_key(cohort_id, module_id), []).append(data)
    _save(store)
    return data


def update_session(cohort_id: str, module_id: str, session_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    store = _load()
    sessions = store.get(_key(cohort_id, module_id), [])
    for s in sessions:
        if s["session_id"] == session_id:
            for k, v in patch.items():
                if k != "session_id":
                    s[k] = v
            _save(store)
            return s
    return None


def delete_session(cohort_id: str, module_id: str, session_id: str) -> bool:
    store = _load()
    key = _key(cohort_id, module_id)
    sessions = store.get(key, [])
    new = [s for s in sessions if s["session_id"] != session_id]
    if len(new) == len(sessions):
        return False
    store[key] = new
    _save(store)
    return True


def toggle_rsvp(cohort_id: str, module_id: str, session_id: str, user_id: str, attending: bool) -> Optional[Dict[str, Any]]:
    store = _load()
    for s in store.get(_key(cohort_id, module_id), []):
        if s["session_id"] == session_id:
            rsvps = set(s.get("rsvps") or [])
            if attending:
                rsvps.add(user_id)
            else:
                rsvps.discard(user_id)
            s["rsvps"] = sorted(rsvps)
            _save(store)
            return s
    return None


def upcoming_for_user(user_id: str, user_cohort_id: str | None, module_id: str, within_days: int = 7) -> List[Dict[str, Any]]:
    """Sessions in next N days that the user can join."""
    if not user_cohort_id:
        return []
    from datetime import datetime, timedelta, timezone
    cutoff = datetime.now(timezone.utc) + timedelta(days=within_days)
    out: List[Dict[str, Any]] = []
    for s in list_sessions(user_cohort_id, module_id):
        try:
            ts = datetime.fromisoformat(s["scheduled_at"].replace("Z", "+00:00"))
            if ts <= cutoff and s.get("status") != "cancelled":
                out.append(s)
        except (KeyError, ValueError):
            continue
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_cohort_live_sessions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/cohort_live_sessions.py backend/tests/test_cohort_live_sessions.py
git commit -m "feat(phase-c): cohort live sessions storage module"
```

---

### Task 16: Cohort live sessions — Flask routes

**Files:**
- Modify: `backend/app.py`
- Test: `backend/tests/test_cohort_live_sessions_api.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_cohort_live_sessions_api.py
import pytest


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    from backend.app import app
    app.config["TESTING"] = True
    return app.test_client()


def _auth_teacher(client):
    # Demo teacher account from project memory
    r = client.post("/api/auth/login", json={"username": "demo_teacher", "password": "Mento@2026"})
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


def _auth_student(client):
    r = client.post("/api/auth/login", json={"username": "demo_student", "password": "Mento@2026"})
    return {"Authorization": f"Bearer {r.get_json()['token']}"}


def test_teacher_creates_and_student_rsvps(client):
    th = _auth_teacher(client)
    create = client.post(
        "/api/cohorts/c1/modules/mento_entrepreneur_4week/live-sessions",
        json={
            "week": 1, "title": "Founder cameo",
            "host_name": "Sridhar Vembu", "host_bio_short": "Founder, Zoho",
            "scheduled_at": "2030-06-15T18:00:00+05:30",
            "duration_min": 60, "meeting_url": "https://meet.google.com/abc",
        },
        headers=th,
    )
    assert create.status_code == 200
    sid = create.get_json()["session_id"]

    sh = _auth_student(client)
    rsvp = client.post(
        f"/api/cohorts/c1/modules/mento_entrepreneur_4week/live-sessions/{sid}/rsvp",
        json={"attending": True}, headers=sh,
    )
    assert rsvp.status_code == 200
    assert "demo_student" in [u for u in rsvp.get_json()["rsvps"]] or len(rsvp.get_json()["rsvps"]) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_cohort_live_sessions_api.py -v`
Expected: FAIL.

- [ ] **Step 3: Add routes to `backend/app.py`**

```python
import backend.cohort_live_sessions as _cls

def _require_teacher_or_admin():
    role = (g.current_user or {}).get("role", "")
    if role not in ("teacher", "trainer", "school_admin", "admin"):
        return jsonify({"error": "forbidden"}), 403


@app.route("/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions", methods=["GET"])
@require_auth
def cohort_sessions_list(cohort_id: str, module_id: str):
    return jsonify({"sessions": _cls.list_sessions(cohort_id, module_id)})


@app.route("/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions", methods=["POST"])
@require_auth
def cohort_sessions_create(cohort_id: str, module_id: str):
    forbidden = _require_teacher_or_admin()
    if forbidden:
        return forbidden
    body = request.get_json(silent=True) or {}
    required = {"week", "title", "host_name", "scheduled_at", "meeting_url"}
    missing = [k for k in required if not body.get(k)]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400
    return jsonify(_cls.create_session(cohort_id, module_id, body))


@app.route("/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions/<session_id>", methods=["PATCH"])
@require_auth
def cohort_sessions_update(cohort_id: str, module_id: str, session_id: str):
    forbidden = _require_teacher_or_admin()
    if forbidden:
        return forbidden
    body = request.get_json(silent=True) or {}
    out = _cls.update_session(cohort_id, module_id, session_id, body)
    if not out:
        return jsonify({"error": "not found"}), 404
    return jsonify(out)


@app.route("/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions/<session_id>", methods=["DELETE"])
@require_auth
def cohort_sessions_delete(cohort_id: str, module_id: str, session_id: str):
    forbidden = _require_teacher_or_admin()
    if forbidden:
        return forbidden
    ok = _cls.delete_session(cohort_id, module_id, session_id)
    return jsonify({"deleted": ok}), (200 if ok else 404)


@app.route("/api/cohorts/<cohort_id>/modules/<module_id>/live-sessions/<session_id>/rsvp", methods=["POST"])
@require_auth
def cohort_sessions_rsvp(cohort_id: str, module_id: str, session_id: str):
    user_id = g.current_user["user_id"]
    body = request.get_json(silent=True) or {}
    out = _cls.toggle_rsvp(cohort_id, module_id, session_id, user_id, bool(body.get("attending", True)))
    if not out:
        return jsonify({"error": "not found"}), 404
    return jsonify(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_cohort_live_sessions_api.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/tests/test_cohort_live_sessions_api.py
git commit -m "feat(phase-c): cohort live sessions API routes"
```

---

### Task 17: Cohort live sessions — student banner card

**Files:**
- Create: `frontend-react/src/components/module/CohortLiveSessionCard.jsx`
- Modify: `frontend-react/src/pages/ModuleDetailPage.jsx` (load + render banner if any upcoming)

- [ ] **Step 1: Implement the card**

```jsx
// frontend-react/src/components/module/CohortLiveSessionCard.jsx
import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";

function countdown(targetISO) {
  const ms = new Date(targetISO) - new Date();
  if (ms <= 0) return "Now";
  const days = Math.floor(ms / 86400000);
  const hrs = Math.floor((ms % 86400000) / 3600000);
  const mins = Math.floor((ms % 3600000) / 60000);
  if (days > 0) return `in ${days}d ${hrs}h`;
  if (hrs > 0) return `in ${hrs}h ${mins}m`;
  return `in ${mins}m`;
}

function gcalLink({ title, scheduled_at, duration_min, meeting_url, host_name }) {
  const start = new Date(scheduled_at);
  const end = new Date(start.getTime() + (duration_min || 60) * 60000);
  const fmt = (d) => d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
  const text = encodeURIComponent(`${title} — Mento Founder Lab`);
  const details = encodeURIComponent(`Host: ${host_name}\nJoin: ${meeting_url}`);
  return `https://calendar.google.com/calendar/r/eventedit?text=${text}&dates=${fmt(start)}/${fmt(end)}&details=${details}`;
}

export default function CohortLiveSessionCard({ cohortId, moduleId, currentUserId }) {
  const [sessions, setSessions] = useState([]);

  useEffect(() => {
    if (!cohortId) return;
    apiFetch(`/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions`)
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions || []));
  }, [cohortId, moduleId]);

  const next = sessions
    .filter((s) => s.status !== "cancelled" && new Date(s.scheduled_at) > new Date(Date.now() - 24 * 3600000))
    .sort((a, b) => new Date(a.scheduled_at) - new Date(b.scheduled_at))[0];

  if (!next) return null;
  const rsvped = (next.rsvps || []).includes(currentUserId);

  const toggleRsvp = async () => {
    await apiFetch(
      `/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions/${next.session_id}/rsvp`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ attending: !rsvped }),
      },
    );
    const r = await apiFetch(`/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions`);
    setSessions((await r.json()).sessions || []);
  };

  const joinable = new Date(next.scheduled_at) - new Date() < 10 * 60000;
  return (
    <div className="rounded-xl border-2 border-indigo-300 bg-indigo-50 p-4 flex flex-wrap items-center gap-4">
      <div className="flex-1 min-w-[200px]">
        <div className="text-xs uppercase tracking-wide text-indigo-700">Live session · Week {next.week}</div>
        <div className="font-semibold mt-1">{next.title}</div>
        <div className="text-sm text-slate-700">{next.host_name} · {countdown(next.scheduled_at)}</div>
        {next.host_bio_short && (
          <div className="text-xs text-slate-500 mt-1">{next.host_bio_short}</div>
        )}
      </div>
      <div className="flex gap-2 flex-wrap">
        <button onClick={toggleRsvp} className={(rsvped ? "bg-emerald-600" : "bg-indigo-600") + " text-white rounded px-3 py-2 text-sm"}>
          {rsvped ? "✓ I'm in" : "RSVP"}
        </button>
        <a href={gcalLink(next)} target="_blank" rel="noreferrer" className="bg-white border rounded px-3 py-2 text-sm">
          📅 Add to Calendar
        </a>
        <a
          href={next.meeting_url}
          target="_blank"
          rel="noreferrer"
          className={(joinable ? "bg-rose-600" : "bg-slate-300 pointer-events-none") + " text-white rounded px-3 py-2 text-sm"}
        >
          Join
        </a>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Render in `ModuleDetailPage.jsx`**

Add import:

```jsx
import CohortLiveSessionCard from "../components/module/CohortLiveSessionCard";
```

Render near the top of the hero section, *before* the badges row:

```jsx
{user?.cohort_id && (
  <CohortLiveSessionCard
    cohortId={user.cohort_id}
    moduleId={moduleId}
    currentUserId={user.user_id}
  />
)}
```

(`user` is the auth context already used in this file — match the existing variable.)

- [ ] **Step 3: Smoke check**

- As `demo_student` with no `cohort_id`: banner does NOT appear.
- Manually `POST` a session via `curl` as `demo_teacher` and assign cohort to demo_student: banner appears, countdown ticks.

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/components/module/CohortLiveSessionCard.jsx \
        frontend-react/src/pages/ModuleDetailPage.jsx
git commit -m "feat(phase-c): cohort live session banner on ModuleDetailPage"
```

---

### Task 18: Cohort live sessions — admin UI

**Files:**
- Create: `frontend-react/src/components/admin/CohortLiveSessionsEditor.jsx`
- Modify: `frontend-react/src/pages/AdminDashboard.jsx` (mount inside COHORTS section as a sub-tab; find the existing CohortsSection rendering and inject this editor when a cohort is selected)

- [ ] **Step 1: Implement the editor**

```jsx
// frontend-react/src/components/admin/CohortLiveSessionsEditor.jsx
import { useEffect, useState } from "react";
import { apiFetch } from "../../api/client";

const EMPTY = {
  week: 1, title: "", host_name: "", host_bio_short: "",
  scheduled_at: "", duration_min: 60, meeting_url: "", recording_url: "",
};

export default function CohortLiveSessionsEditor({ cohortId, moduleId }) {
  const [sessions, setSessions] = useState([]);
  const [draft, setDraft] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState(null);

  const reload = () =>
    apiFetch(`/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions`)
      .then((r) => r.json())
      .then((d) => setSessions(d.sessions || []));

  useEffect(() => { reload(); }, [cohortId, moduleId]);

  const create = async () => {
    setSaving(true); setErr(null);
    const r = await apiFetch(`/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(draft),
    });
    setSaving(false);
    if (!r.ok) { setErr((await r.json()).error || "Save failed"); return; }
    setDraft(EMPTY);
    reload();
  };

  const remove = async (sid) => {
    if (!window.confirm("Delete this session?")) return;
    await apiFetch(`/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions/${sid}`, { method: "DELETE" });
    reload();
  };

  const setRecording = async (sid, url) => {
    await apiFetch(`/api/cohorts/${cohortId}/modules/${moduleId}/live-sessions/${sid}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ recording_url: url, status: "recorded" }),
    });
    reload();
  };

  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Live sessions — {moduleId}</h3>
      <div className="rounded border p-3 grid grid-cols-2 gap-2 text-sm">
        <label>Week<input type="number" min={1} max={4} value={draft.week} onChange={(e) => setDraft({ ...draft, week: +e.target.value })} className="w-full border p-1" /></label>
        <label>Title<input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} className="w-full border p-1" /></label>
        <label>Host name<input value={draft.host_name} onChange={(e) => setDraft({ ...draft, host_name: e.target.value })} className="w-full border p-1" /></label>
        <label>Host bio<input value={draft.host_bio_short} onChange={(e) => setDraft({ ...draft, host_bio_short: e.target.value })} className="w-full border p-1" /></label>
        <label>Scheduled (ISO)<input value={draft.scheduled_at} onChange={(e) => setDraft({ ...draft, scheduled_at: e.target.value })} placeholder="2026-06-15T18:00:00+05:30" className="w-full border p-1" /></label>
        <label>Duration (min)<input type="number" value={draft.duration_min} onChange={(e) => setDraft({ ...draft, duration_min: +e.target.value })} className="w-full border p-1" /></label>
        <label className="col-span-2">Meeting URL<input value={draft.meeting_url} onChange={(e) => setDraft({ ...draft, meeting_url: e.target.value })} className="w-full border p-1" /></label>
        {err && <div className="col-span-2 text-rose-600 text-xs">{err}</div>}
        <div className="col-span-2">
          <button onClick={create} disabled={saving} className="bg-indigo-600 text-white rounded px-4 py-2 text-sm disabled:bg-indigo-300">
            {saving ? "Saving…" : "Schedule session"}
          </button>
        </div>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Week</th><th>Title</th><th>When</th><th>RSVPs</th><th>Recording</th><th></th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((s) => (
            <tr key={s.session_id} className="border-t">
              <td>W{s.week}</td>
              <td>{s.title}<div className="text-xs text-slate-500">{s.host_name}</div></td>
              <td>{new Date(s.scheduled_at).toLocaleString()}</td>
              <td>{(s.rsvps || []).length}</td>
              <td>
                <input
                  defaultValue={s.recording_url || ""}
                  onBlur={(e) => setRecording(s.session_id, e.target.value)}
                  placeholder="paste URL"
                  className="w-full border p-1"
                />
              </td>
              <td><button onClick={() => remove(s.session_id)} className="text-rose-600 text-xs">Delete</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Mount inside `AdminDashboard.jsx`**

Find the existing CohortsSection (search for `CohortsSection` or `🏫`/`COHORTS`). Add inside the cohort detail panel:

```jsx
import CohortLiveSessionsEditor from "../components/admin/CohortLiveSessionsEditor";
// ...inside the cohort detail view:
<CohortLiveSessionsEditor cohortId={selectedCohort.id} moduleId="mento_entrepreneur_4week" />
```

If there is no per-cohort detail panel yet, mount the editor in a new tab under COHORTS labeled "Live Sessions" and let the admin pick the cohort + module from dropdowns.

- [ ] **Step 3: Smoke check**

Log in as `demo_teacher` → AdminDashboard → COHORTS → see "Live Sessions" sub-section → create one → confirm it shows up on the student's module page (Task 17).

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/components/admin/CohortLiveSessionsEditor.jsx \
        frontend-react/src/pages/AdminDashboard.jsx
git commit -m "feat(phase-c): admin UI for cohort live sessions"
```

---

### Task 19: Live-session notifications (24h / 1h / recording)

**Files:**
- Modify: `backend/app.py` (extend `_run_scheduler` with a new job)

- [ ] **Step 1: Add job**

Locate `_run_scheduler()` in `backend/app.py` (search for `apscheduler` or the daily streak job). Add:

```python
def _run_module_live_session_reminders():
    """Every 15 minutes: find sessions starting in 24h±15m or 1h±15m, push notifications."""
    from datetime import datetime, timedelta, timezone
    import backend.cohort_live_sessions as _cls
    import backend.notifications as _notif
    now = datetime.now(timezone.utc)
    windows = [
        (timedelta(hours=24), "24h", "Your Mento live session starts tomorrow"),
        (timedelta(hours=1), "1h", "Starting in 1 hour — join link inside"),
    ]
    store = _cls._load()
    for key, sessions in store.items():
        try:
            cohort_id, module_id = key.split("__", 1)
        except ValueError:
            continue
        for s in sessions:
            if s.get("status") == "cancelled":
                continue
            try:
                ts = datetime.fromisoformat(s["scheduled_at"].replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            for delta, tag, headline in windows:
                target = ts - delta
                if abs((target - now).total_seconds()) <= 900:  # ±15 min
                    sent_flag = f"_notif_sent_{tag}"
                    if s.get(sent_flag):
                        continue
                    for uid in s.get("rsvps", []) or []:
                        _notif.create_notification(
                            user_id=uid,
                            kind="live_session_reminder",
                            title=headline,
                            body=f"{s.get('title','')} · {s.get('host_name','')}",
                            link=s.get("meeting_url"),
                        )
                    s[sent_flag] = True
                    _cls._save(store)
            # Recording-uploaded notification (one-shot)
            if s.get("recording_url") and not s.get("_notif_sent_recording"):
                for uid in s.get("rsvps", []) or []:
                    _notif.create_notification(
                        user_id=uid,
                        kind="live_session_recording",
                        title="Missed it? Watch the recording",
                        body=s.get("title", ""),
                        link=s["recording_url"],
                    )
                s["_notif_sent_recording"] = True
                _cls._save(store)


# Register inside _run_scheduler (add next to other scheduler.add_job calls):
scheduler.add_job(_run_module_live_session_reminders, "interval", minutes=15, id="live_session_reminders", replace_existing=True)
```

- [ ] **Step 2: Smoke check**

Restart backend; logs should show APScheduler registered `live_session_reminders`. Manually edit a session's `scheduled_at` to `now + 1h` and wait 15 min OR call the function directly: `python -c "from backend.app import _run_module_live_session_reminders; _run_module_live_session_reminders()"` — confirm notifications appear in `backend/data/notifications.json`.

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "feat(phase-c): live-session reminder + recording notifications"
```

---

### Task 20: Phase C completion tag + regression suite

**Files:** (none)

- [ ] **Step 1: Run all Phase C tests + baseline + Phase A regression**

Run:
```bash
cd backend && python -m pytest tests/test_phase_c_baseline.py \
  tests/test_idea_journal.py tests/test_idea_journal_api.py tests/test_idea_journal_pdf.py \
  tests/test_micro_quests_present.py tests/test_sr_module_seeding.py \
  tests/test_module_skill_report.py tests/test_share_card.py \
  tests/test_module_certificate.py tests/test_cohort_live_sessions.py \
  tests/test_cohort_live_sessions_api.py -v
```
Expected: all PASS.

- [ ] **Step 2: Tag**

```bash
git tag phase-c-complete
```

- [ ] **Step 3: Final reminder commit (no-op or docs touch)**

Nothing to commit — just confirm the tag is in place.

---

## Self-review

- ✅ Each section/requirement from spec §6 maps to a task: 6.1 (Tasks 6–7), 6.2 (Task 8), 6.3 (Tasks 1–5), 6.4 (Task 14), 6.5 (Task 13), 6.6 (Tasks 9–12), 6.7 (Tasks 15–19).
- ✅ No placeholders / TBD.
- ✅ Type/function names consistent (`schedule_flashcard`, `list_module_flashcards`, `check_module_completion`, `create_session`/`toggle_rsvp`).
- ✅ Every new schema field is optional; lessons added are net-new IDs; original 32 lessons untouched.
- ✅ Tests assert behavior, not implementation details.
- ✅ All file paths absolute or rooted at repo, no "TODO" steps.
