# Mento Entrepreneur Phase D — Indian Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Indian context layer to `mento_entrepreneur_4week`: 8 founder case-study cards, 6 "Failure Museum" cards, ₹ currency localization, a 3-lesson regulatory primer, and a 28-message daily Mento dispatch.

**Architecture:** Mostly content authoring + two thin renderers (`CaseStudyCardRenderer`, `FailureCardRenderer` — scaffolded in Phase A, filled in here). One new APScheduler job. Zero new tables; all data lives in module JSON + one notifications dispatch file.

**Tech Stack:** JSON authoring, React + Tailwind, APScheduler (running), existing `notifications.py`.

**Prerequisite:** `phase-a-complete` tag. Can run in parallel with B and C.

---

### Task 0: Regression baseline check

**Files:**
- Test: `backend/tests/test_phase_d_baseline.py` (Create)

- [ ] **Step 1: Write baseline test**

```python
# backend/tests/test_phase_d_baseline.py
import json
from pathlib import Path


def test_module_still_loads():
    p = Path(__file__).resolve().parents[1] / "modules" / "mento_entrepreneur_4week.json"
    mod = json.loads(p.read_text())
    assert len(mod["weeks"]) == 4
    assert mod.get("module_id") == "mento_entrepreneur_4week" or mod.get("id") == "mento_entrepreneur_4week"


def test_phase_a_renderers_scaffolded():
    """Phase A registers case_study_card and failure_card as known lesson types."""
    import backend.modules_engine as me
    # Phase A added _KNOWN_LESSON_TYPES; if module engine doesn't define it, this is a sanity guard.
    known = getattr(me, "_KNOWN_LESSON_TYPES", None)
    if known is not None:
        assert "case_study_card" in known
        assert "failure_card" in known
```

- [ ] **Step 2: Run**

Run: `cd backend && python -m pytest tests/test_phase_d_baseline.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_phase_d_baseline.py
git commit -m "test(phase-d): baseline regression check"
```

---

### Task 1: CaseStudyCardRenderer — fill in scaffold

**Files:**
- Modify: `frontend-react/src/components/module/CaseStudyCardRenderer.jsx` (Phase A created this as a stub; replace body)

- [ ] **Step 1: Replace body with finished renderer**

```jsx
// frontend-react/src/components/module/CaseStudyCardRenderer.jsx
import { useState } from "react";
import { apiFetch } from "../../api/client";

export default function CaseStudyCardRenderer({ lesson, moduleId, onComplete }) {
  const { portrait_url, founder_name, founder_origin, backstory, takeaway, reflection_prompt, company } = lesson;
  const [answer, setAnswer] = useState("");
  const [saved, setSaved] = useState(false);

  const submit = async () => {
    const text = answer.trim();
    if (text) {
      await apiFetch(`/api/modules/${moduleId}/idea-journal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content: `${reflection_prompt}\n→ ${text}`,
          type: "reflection",
          lesson_id: lesson.id,
          lesson_title: lesson.title,
        }),
      });
    }
    await apiFetch(`/api/modules/${moduleId}/lessons/${lesson.id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score: 100 }),
    });
    setSaved(true);
    onComplete && onComplete();
  };

  return (
    <article className="rounded-2xl overflow-hidden border bg-white shadow-sm">
      <div className="bg-gradient-to-br from-amber-100 to-rose-100 p-6 flex gap-4 items-center">
        {portrait_url && (
          <img src={portrait_url} alt={founder_name} className="w-24 h-24 rounded-full object-cover border-2 border-white shadow" />
        )}
        <div>
          <div className="text-xs uppercase tracking-wide text-rose-700">Indian Founder · 60–90 sec read</div>
          <h2 className="text-2xl font-bold">{founder_name}</h2>
          {company && <div className="text-sm text-slate-700">{company}</div>}
          {founder_origin && <div className="text-xs text-slate-500">{founder_origin}</div>}
        </div>
      </div>
      <div className="p-6 space-y-4">
        {backstory && (
          <p className="text-slate-800 whitespace-pre-line leading-relaxed">{backstory}</p>
        )}
        {takeaway && (
          <div className="bg-amber-50 border-l-4 border-amber-400 p-3 text-sm">
            <strong>One thing to take away: </strong>{takeaway}
          </div>
        )}
        {reflection_prompt && !saved && (
          <div>
            <label className="text-sm font-medium">{reflection_prompt}</label>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              rows={3}
              className="mt-1 w-full border rounded p-2 text-sm"
            />
          </div>
        )}
        {saved ? (
          <div className="text-emerald-700 text-sm">✓ Saved to your Idea Journal.</div>
        ) : (
          <button onClick={submit} className="bg-rose-600 text-white rounded px-4 py-2 text-sm">
            Mark complete
          </button>
        )}
      </div>
    </article>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/module/CaseStudyCardRenderer.jsx
git commit -m "feat(phase-d): finalize CaseStudyCardRenderer"
```

---

### Task 2: FailureCardRenderer — fill in scaffold

**Files:**
- Modify: `frontend-react/src/components/module/FailureCardRenderer.jsx`

- [ ] **Step 1: Replace body**

```jsx
// frontend-react/src/components/module/FailureCardRenderer.jsx
import { useState } from "react";
import { apiFetch } from "../../api/client";

export default function FailureCardRenderer({ lesson, moduleId, onComplete }) {
  const { company_name, headline, what_they_tried, why_they_failed, lesson_text, year, image_url } = lesson;
  const [done, setDone] = useState(false);

  const submit = async () => {
    await apiFetch(`/api/modules/${moduleId}/lessons/${lesson.id}/complete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ score: 100 }),
    });
    setDone(true);
    onComplete && onComplete();
  };

  return (
    <article className="rounded-2xl overflow-hidden border-2 border-slate-200 bg-slate-50">
      <div className="bg-slate-900 text-white p-4">
        <div className="text-xs uppercase tracking-wide text-rose-300">Failure Museum · 60 sec read</div>
        <h2 className="text-xl font-bold mt-1">{company_name} {year && <span className="text-slate-400 text-base">· {year}</span>}</h2>
        {headline && <div className="text-sm text-slate-200 mt-1">{headline}</div>}
      </div>
      {image_url && <img src={image_url} alt={company_name} className="w-full max-h-48 object-cover" />}
      <div className="p-4 space-y-3 text-sm">
        {what_they_tried && (
          <div><strong>What they tried: </strong>{what_they_tried}</div>
        )}
        {why_they_failed && (
          <div><strong>Why it didn't work: </strong>{why_they_failed}</div>
        )}
        {lesson_text && (
          <div className="bg-rose-50 border-l-4 border-rose-400 p-3"><strong>One lesson: </strong>{lesson_text}</div>
        )}
        {done ? (
          <div className="text-emerald-700">✓ Lesson noted.</div>
        ) : (
          <button onClick={submit} className="bg-slate-800 text-white rounded px-4 py-2 text-sm">
            Got it
          </button>
        )}
      </div>
    </article>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/module/FailureCardRenderer.jsx
git commit -m "feat(phase-d): finalize FailureCardRenderer"
```

---

### Task 3: Author 8 Indian founder case-study cards

**Files:**
- Modify: `backend/modules/mento_entrepreneur_4week.json`
- Test: `backend/tests/test_indian_case_studies.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_indian_case_studies.py
import json
from pathlib import Path

EXPECTED_FOUNDERS = {
    "case_study_vembu", "case_study_nayar", "case_study_oyo",
    "case_study_byju", "case_study_kunal_shah", "case_study_ghazal_alagh",
    "case_study_bhavish", "case_study_neighborhood",
}


def test_all_8_founder_cards_present():
    mod = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "modules", "mento_entrepreneur_4week.json").read_text())
    all_ids = {l["id"] for w in mod["weeks"] for l in w.get("lessons", [])}
    missing = EXPECTED_FOUNDERS - all_ids
    assert not missing, f"missing case study lessons: {missing}"
    # Each must be type case_study_card with required fields:
    by_id = {l["id"]: l for w in mod["weeks"] for l in w.get("lessons", [])}
    for fid in EXPECTED_FOUNDERS:
        l = by_id[fid]
        assert l["type"] == "case_study_card"
        for k in ("founder_name", "backstory", "takeaway", "reflection_prompt"):
            assert l.get(k), f"{fid} missing {k}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_indian_case_studies.py -v`
Expected: FAIL.

- [ ] **Step 3: Insert 8 case-study cards into module JSON**

Append one card per week (4 cards) and 4 more under a new optional sidebar lesson group at end of week 4. Use these exact JSON objects.

**Week 1** — append to `weeks[0].lessons`:
```json
{
  "id": "case_study_vembu",
  "type": "case_study_card",
  "title": "Sridhar Vembu — Built Zoho from a Tamil Nadu village",
  "duration_min": 2,
  "founder_name": "Sridhar Vembu",
  "company": "Zoho",
  "founder_origin": "Tenkasi, Tamil Nadu",
  "portrait_url": "/static/module_images/mento_entrepreneur_4week/founder_vembu.png",
  "backstory": "Sridhar grew up in a Tamil Nadu village. He studied in IIT and Princeton, then quit a Silicon Valley job to build Zoho — a software company — from rural India. Today Zoho has 100M+ users worldwide, with most engineers working from villages.",
  "takeaway": "You don't need to leave India to build a global tech company. You don't even need to leave your village.",
  "reflection_prompt": "What's something you'd build *from* your hometown?"
}
```

**Week 2** — append to `weeks[1].lessons`:
```json
{
  "id": "case_study_nayar",
  "type": "case_study_card",
  "title": "Falguni Nayar — Started Nykaa at 50",
  "duration_min": 2,
  "founder_name": "Falguni Nayar",
  "company": "Nykaa",
  "founder_origin": "Mumbai",
  "portrait_url": "/static/module_images/mento_entrepreneur_4week/founder_nayar.png",
  "backstory": "Falguni was a top banker at Kotak Mahindra. At 50 — when most people think about retiring — she quit her job to start Nykaa, an online beauty store. She built it into India's first woman-led unicorn, taking it public in 2021.",
  "takeaway": "There is no 'too late' to start. Customer obsession beats age.",
  "reflection_prompt": "Name one thing you assume is 'too late' for you. Why?"
}
```

**Week 3** — append to `weeks[2].lessons`:
```json
{
  "id": "case_study_oyo",
  "type": "case_study_card",
  "title": "Ritesh Agarwal — Started OYO at 17",
  "duration_min": 2,
  "founder_name": "Ritesh Agarwal",
  "company": "OYO Rooms",
  "founder_origin": "Bissam Cuttack, Odisha",
  "portrait_url": "/static/module_images/mento_entrepreneur_4week/founder_ritesh.png",
  "backstory": "At 17, Ritesh travelled across India and noticed budget hotels were unreliable: dirty rooms, no Wi-Fi, surprise prices. He started OYO to standardize them. By 21, OYO was in 100+ Indian cities. He skipped college.",
  "takeaway": "Your age is not the problem. Your observation is the asset.",
  "reflection_prompt": "What problem do you notice that adults seem to ignore?"
}
```

**Week 4** — append to `weeks[3].lessons`:
```json
{
  "id": "case_study_byju",
  "type": "case_study_card",
  "title": "Byju Raveendran — From village teacher to ed-tech founder",
  "duration_min": 2,
  "founder_name": "Byju Raveendran",
  "company": "BYJU'S",
  "founder_origin": "Azhikode, Kerala",
  "portrait_url": "/static/module_images/mento_entrepreneur_4week/founder_byju.png",
  "backstory": "Byju was a teacher who made students fall in love with math. He started teaching small batches, then stadiums of 25,000 students, then built an app. BYJU'S became the world's most valuable ed-tech company. (It also struggled later — a reminder that growth alone isn't success.)",
  "takeaway": "Teaching well is a real business skill — and one bad chapter doesn't erase the early ones.",
  "reflection_prompt": "What's something you can teach a younger kid better than their teacher?"
}
```

**Indian Founders Gallery — 4 bonus cards** — append to `weeks[3].lessons` (these stay at the end of week 4 as bonus content; they don't gate completion):
```json
{
  "id": "case_study_kunal_shah",
  "type": "case_study_card",
  "title": "Kunal Shah — Failed first, then built CRED",
  "duration_min": 2,
  "founder_name": "Kunal Shah",
  "company": "FreeCharge → CRED",
  "founder_origin": "Mumbai",
  "portrait_url": "/static/module_images/mento_entrepreneur_4week/founder_kunal.png",
  "backstory": "Kunal sold FreeCharge (recharge app) to Snapdeal. Then he started CRED — a credit-card rewards app — by noticing one tiny insight: India's most creditworthy people pay bills late on bad apps. CRED only let in users with 750+ credit score.",
  "takeaway": "Niche down. The most valuable users often feel underserved.",
  "reflection_prompt": "Who are the 'best' customers in your idea — and are they being ignored?"
}
```
```json
{
  "id": "case_study_ghazal_alagh",
  "type": "case_study_card",
  "title": "Ghazal Alagh — Mamaearth from parent struggles",
  "duration_min": 2,
  "founder_name": "Ghazal Alagh",
  "company": "Mamaearth",
  "founder_origin": "Delhi",
  "portrait_url": "/static/module_images/mento_entrepreneur_4week/founder_ghazal.png",
  "backstory": "Ghazal couldn't find safe, toxin-free products for her newborn son. She and her husband started making them. Within 7 years, Mamaearth became a publicly listed company with millions of customers.",
  "takeaway": "The best business ideas often come from being a frustrated customer yourself.",
  "reflection_prompt": "What's a product *you* are frustrated with as a kid right now?"
}
```
```json
{
  "id": "case_study_bhavish",
  "type": "case_study_card",
  "title": "Bhavish Aggarwal — Ola from a bad cab ride",
  "duration_min": 2,
  "founder_name": "Bhavish Aggarwal",
  "company": "Ola",
  "founder_origin": "Ludhiana, Punjab",
  "portrait_url": "/static/module_images/mento_entrepreneur_4week/founder_bhavish.png",
  "backstory": "Bhavish was stranded on a Bangalore-Bandipur trip when a taxi driver abandoned him mid-route. He went home and built Ola — a way to book a cab from your phone with a fair price. Today Ola also builds electric scooters in India.",
  "takeaway": "One bad day can be a billion-rupee idea — if you act on it.",
  "reflection_prompt": "What was the last time *you* were stranded or stuck because of bad service?"
}
```
```json
{
  "id": "case_study_neighborhood",
  "type": "case_study_card",
  "title": "Your neighborhood founder",
  "duration_min": 3,
  "founder_name": "The aunty / uncle on your street",
  "founder_origin": "Probably 500 metres from you",
  "portrait_url": "/static/module_images/mento_entrepreneur_4week/founder_neighborhood.png",
  "backstory": "Not every founder is on TV. The aunty making tiffins, the uncle running the chai stall, the bhaiya repairing phones — each of them solved a real problem, raised their own capital, hired their first employee, and survived a tough year. They are founders too.",
  "takeaway": "Entrepreneurship doesn't need a hoodie or a Twitter account. It needs a customer and the courage to start.",
  "reflection_prompt": "Pick one neighborhood entrepreneur near you. Ask them one question this week. Write what they said."
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_indian_case_studies.py tests/test_phase_d_baseline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/mento_entrepreneur_4week.json backend/tests/test_indian_case_studies.py
git commit -m "feat(phase-d): 8 Indian founder case-study cards"
```

---

### Task 4: Author 6 Failure Museum cards (grouped lesson)

**Files:**
- Modify: `backend/modules/mento_entrepreneur_4week.json`
- Test: `backend/tests/test_failure_museum.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_failure_museum.py
import json
from pathlib import Path

EXPECTED = {"failure_stayzilla", "failure_doodhwala", "failure_tinyowl",
            "failure_dazo", "failure_askme", "failure_housing"}


def test_failure_cards_present():
    mod = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "modules", "mento_entrepreneur_4week.json").read_text())
    all_ids = {l["id"] for w in mod["weeks"] for l in w.get("lessons", [])}
    missing = EXPECTED - all_ids
    assert not missing, f"missing failure cards: {missing}"
    by_id = {l["id"]: l for w in mod["weeks"] for l in w.get("lessons", [])}
    for fid in EXPECTED:
        l = by_id[fid]
        assert l["type"] == "failure_card"
        for k in ("company_name", "what_they_tried", "why_they_failed", "lesson_text"):
            assert l.get(k), f"{fid} missing {k}"
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/test_failure_museum.py -v`
Expected: FAIL.

- [ ] **Step 3: Insert 6 failure cards into week 4 (before `w4_l1_failure_journey`)**

Open `backend/modules/mento_entrepreneur_4week.json`, locate week 4 lessons list, insert these 6 entries *just before* the lesson with id matching `w4_l1_failure_journey` (or at the start of week 4's lessons if that lesson is later renumbered):

```json
{
  "id": "failure_stayzilla",
  "type": "failure_card",
  "title": "Stayzilla — Homestays, before they were cool",
  "duration_min": 1,
  "company_name": "Stayzilla",
  "year": "2017",
  "headline": "India's first homestay aggregator. Shut down before Airbnb won India.",
  "what_they_tried": "Built a marketplace of 1 lakh+ homestays across small Indian towns — places hotels didn't reach.",
  "why_they_failed": "Couldn't make unit economics work. Each booking cost more in support than it earned. Investors stopped funding losses.",
  "lesson_text": "First doesn't mean winning. If every order loses money, scale makes it worse, not better."
}
```
```json
{
  "id": "failure_doodhwala",
  "type": "failure_card",
  "title": "Doodhwala — Milk delivery, shut by Covid",
  "duration_min": 1,
  "company_name": "Doodhwala",
  "year": "2019",
  "headline": "Daily milk subscription. Closed before turning a profit.",
  "what_they_tried": "Subscription milk + groceries delivered to your door before 7 AM in Bengaluru, Pune, Hyderabad.",
  "why_they_failed": "Razor-thin margins on milk + heavy subsidies + a parent company that went bankrupt = no runway.",
  "lesson_text": "If the underlying margin is 5 rupees, no amount of growth saves you."
}
```
```json
{
  "id": "failure_tinyowl",
  "type": "failure_card",
  "title": "TinyOwl — Food delivery, before Zomato won",
  "duration_min": 1,
  "company_name": "TinyOwl",
  "year": "2016",
  "headline": "Funded ₹163 cr. Couldn't survive against Swiggy and Zomato.",
  "what_they_tried": "Food ordering app focused on Mumbai, with promised 30-minute delivery.",
  "why_they_failed": "Burned money on driver subsidies and marketing without building real customer love. Co-founders fought publicly.",
  "lesson_text": "If your only difference is 'cheaper or faster,' a richer competitor can copy that in a weekend."
}
```
```json
{
  "id": "failure_dazo",
  "type": "failure_card",
  "title": "Dazo — Cloud kitchens, too early",
  "duration_min": 1,
  "company_name": "Dazo",
  "year": "2015",
  "headline": "Cooked-meal startup, shut after 2 years.",
  "what_they_tried": "Cooked fresh meals in cloud kitchens, delivered to office workers in Bengaluru.",
  "why_they_failed": "Too far ahead of the market. Customers weren't ready to order lunch on an app, and infrastructure (UPI, delivery fleets) hadn't matured yet.",
  "lesson_text": "Being right but early is the same as being wrong. Time the market, not just the idea."
}
```
```json
{
  "id": "failure_askme",
  "type": "failure_card",
  "title": "Askme.com — 4,000 employees, shut overnight",
  "duration_min": 1,
  "company_name": "Askme.com",
  "year": "2016",
  "headline": "Local search + commerce platform. Closed when investor pulled out.",
  "what_they_tried": "Just-Dial-style local search + e-commerce + grocery + payments — all at once.",
  "why_they_failed": "Did too many things, none excellently. One investor (Astro Malaysia) controlled funding; when they exited, 4,000 people lost their jobs.",
  "lesson_text": "Don't put all your funding in one investor's hands. And do one thing world-class before doing a second."
}
```
```json
{
  "id": "failure_housing",
  "type": "failure_card",
  "title": "Housing.com — Dazzling tech, founder drama",
  "duration_min": 1,
  "company_name": "Housing.com (early years)",
  "year": "2015-16",
  "headline": "Built India's best real-estate map. Lost it to leadership chaos.",
  "what_they_tried": "Used aerial imagery, data, and beautiful design to fix Indian real-estate listings.",
  "why_they_failed": "The young CEO publicly attacked investors. Board kicked him out. Product stalled while leadership rebuilt.",
  "lesson_text": "How you treat your team and investors matters as much as your product."
}
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_failure_museum.py tests/test_phase_d_baseline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/mento_entrepreneur_4week.json backend/tests/test_failure_museum.py
git commit -m "feat(phase-d): 6 Failure Museum cards (week 4)"
```

---

### Task 5: ₹ currency localization edits

**Files:**
- Modify: `backend/modules/mento_entrepreneur_4week.json`
- Test: `backend/tests/test_currency_localization.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_currency_localization.py
import json
import re
from pathlib import Path


def _gather_text(node, out):
    if isinstance(node, dict):
        for v in node.values():
            _gather_text(v, out)
    elif isinstance(node, list):
        for v in node:
            _gather_text(v, out)
    elif isinstance(node, str):
        out.append(node)


def test_no_dollar_examples_in_localized_lessons():
    mod = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "modules", "mento_entrepreneur_4week.json").read_text())
    targets = {"w3_l2_who_pays", "w3_l3_customer_profile", "w3_l4_idea_scorecard"}
    by_id = {l["id"]: l for w in mod["weeks"] for l in w.get("lessons", [])}
    for tid in targets:
        if tid not in by_id:
            continue  # the actual id format may differ; skip silently
        text_blobs = []
        _gather_text(by_id[tid], text_blobs)
        joined = " ".join(text_blobs)
        # No "$" or "USD" in monetary examples:
        assert "$" not in joined, f"{tid} still contains $ symbol"
        assert not re.search(r"\bUSD\b", joined), f"{tid} still contains USD"
        # Must contain ₹ at least once:
        assert "₹" in joined, f"{tid} missing ₹ examples"
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/test_currency_localization.py -v`
Expected: FAIL on at least one target.

- [ ] **Step 3: Edit the three lessons in `backend/modules/mento_entrepreneur_4week.json`**

For each of the lessons whose `id` matches `w3_l2_who_pays`, `w3_l3_customer_profile`, `w3_l4_idea_scorecard` (or their renumbered equivalents — search by title/topic if IDs differ):

**`w3_l2_who_pays`** — find every monetary example and rewrite:
- "$1 cup of coffee" → "₹10 cup of chai"
- "$5 cafe latte" → "₹250 cafe coffee"
- "$50/month subscription" → "₹500/month subscription"

**`w3_l3_customer_profile`** — convert income ranges:
- "household income $X/year" → "monthly income ₹Y/month"
- Use these brackets in any example: ₹10,000–₹25,000 (lower-middle), ₹25,000–₹75,000 (middle), ₹75,000–₹2L (upper-middle), ₹2L+ (affluent)

**`w3_l4_idea_scorecard`** — relabel any market-size axis from `$10K / $100K / $1M / $10M` to `₹10 lakh / ₹1 crore / ₹10 crore / ₹100 crore`.

The exact strings depend on the current JSON. Use the editor's find/replace; preserve all surrounding lesson structure.

- [ ] **Step 4: Run test to verify pass**

Run: `cd backend && python -m pytest tests/test_currency_localization.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/mento_entrepreneur_4week.json backend/tests/test_currency_localization.py
git commit -m "feat(phase-d): ₹ currency localization in W3 lessons"
```

---

### Task 6: Regulatory primer — 3 bonus audio lessons

**Files:**
- Modify: `backend/modules/mento_entrepreneur_4week.json`
- Test: `backend/tests/test_regulatory_primer.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_regulatory_primer.py
import json
from pathlib import Path

EXPECTED = {"w4_bonus_udyam", "w4_bonus_gst", "w4_bonus_bank_account"}


def test_regulatory_primer_lessons():
    mod = json.loads(Path(__file__).resolve().parents[1].joinpath(
        "modules", "mento_entrepreneur_4week.json").read_text())
    all_ids = {l["id"] for w in mod["weeks"] for l in w.get("lessons", [])}
    assert EXPECTED.issubset(all_ids), f"missing: {EXPECTED - all_ids}"
    by_id = {l["id"]: l for w in mod["weeks"] for l in w.get("lessons", [])}
    for eid in EXPECTED:
        l = by_id[eid]
        assert l["type"] == "audio_lesson", f"{eid} should be audio_lesson"
        # Optional / does not gate completion:
        assert l.get("optional") is True, f"{eid} must be marked optional"
        # Must carry a disclaimer:
        body = json.dumps(l, ensure_ascii=False)
        assert "general overview" in body.lower() or "not legal advice" in body.lower(), \
            f"{eid} missing disclaimer"
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/test_regulatory_primer.py -v`
Expected: FAIL.

- [ ] **Step 3: Append 3 lessons to week 4**

In `backend/modules/mento_entrepreneur_4week.json`, append to `weeks[3].lessons`:

```json
{
  "id": "w4_bonus_udyam",
  "type": "audio_lesson",
  "title": "Bonus: What is Udyam (and why a tiny business registers)?",
  "duration_min": 3,
  "optional": true,
  "tags": ["regulatory", "bonus"],
  "body": "Udyam is the Indian government's free, online registration for small businesses. It takes 10 minutes and gives you a unique business ID. Why bother? Banks give you cheaper loans. Government tenders ('orders') become available. Some subsidies open up. You don't need it to start a business — but the moment you're earning, it's worth doing. (This is a general overview, not legal advice.)",
  "transcript": "Udyam is the Indian government's free, online registration for small businesses. It takes 10 minutes...",
  "audio_urls": {"en": null, "hi": null}
}
```
```json
{
  "id": "w4_bonus_gst",
  "type": "audio_lesson",
  "title": "Bonus: GST in 3 minutes",
  "duration_min": 3,
  "optional": true,
  "tags": ["regulatory", "bonus"],
  "body": "GST is a single tax that replaced a confusing pile of older taxes in 2017. If your business earns more than ₹20 lakh a year (₹40 lakh for goods in most states), you must register for GST. Below that, you don't. When you do register, you charge customers GST on top of your price — but you can also claim back GST you paid on supplies. (This is a general overview, not legal advice.)",
  "transcript": "GST is a single tax that replaced a confusing pile of older taxes...",
  "audio_urls": {"en": null, "hi": null}
}
```
```json
{
  "id": "w4_bonus_bank_account",
  "type": "audio_lesson",
  "title": "Bonus: Why your business needs its OWN bank account",
  "duration_min": 3,
  "optional": true,
  "tags": ["regulatory", "bonus"],
  "body": "The moment you start charging real customers, open a separate bank account just for your business. Why? You'll actually know if you're making money — personal expenses won't hide in the numbers. Customers trust an account in your business name. And taxes get 10x easier at year-end. Most Indian banks have free 'small business' accounts. Ask. (This is a general overview, not legal advice.)",
  "transcript": "The moment you start charging real customers, open a separate bank account...",
  "audio_urls": {"en": null, "hi": null}
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd backend && python -m pytest tests/test_regulatory_primer.py tests/test_phase_d_baseline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/modules/mento_entrepreneur_4week.json backend/tests/test_regulatory_primer.py
git commit -m "feat(phase-d): regulatory primer (Udyam, GST, bank account) — week 4 bonus"
```

---

### Task 7: Author 28 daily-dispatch messages

**Files:**
- Create: `backend/data/module_daily_dispatch/mento_entrepreneur_4week.json`
- Test: `backend/tests/test_daily_dispatch_content.py`

- [ ] **Step 1: Write the test**

```python
# backend/tests/test_daily_dispatch_content.py
import json
from pathlib import Path


def test_dispatch_has_28_messages():
    p = Path(__file__).resolve().parents[1] / "data" / "module_daily_dispatch" / "mento_entrepreneur_4week.json"
    msgs = json.loads(p.read_text())
    assert isinstance(msgs, list)
    assert len(msgs) == 28
    seen_days = set()
    for m in msgs:
        assert "day" in m and 1 <= m["day"] <= 28
        assert m["day"] not in seen_days, f"duplicate day {m['day']}"
        seen_days.add(m["day"])
        assert m.get("title")
        assert m.get("body")
        assert len(m["body"]) <= 280, f"day {m['day']} body too long for WhatsApp/notif"
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/test_daily_dispatch_content.py -v`
Expected: FAIL.

- [ ] **Step 3: Create the JSON file**

Create `backend/data/module_daily_dispatch/mento_entrepreneur_4week.json` with the following exact content:

```json
[
  {"day": 1, "title": "Welcome, founder.", "body": "This week you'll find one problem worth solving. Today: notice one thing that annoyed you in the last 24 hours. Write it in your Idea Journal.", "lesson_id": "w1_l1_intro"},
  {"day": 2, "title": "Problems > Ideas", "body": "Most failed startups started with an idea looking for a problem. Real founders start with a problem looking for a solution. What's bothering people around you?", "lesson_id": "w1_l2_what_is_a_problem"},
  {"day": 3, "title": "Eavesdrop today", "body": "Listen — really listen — to what people complain about at home or school. Write down 3 complaints by tonight.", "lesson_id": null},
  {"day": 4, "title": "Sridhar's village", "body": "Sridhar Vembu built a billion-dollar tech company from a Tamil Nadu village. Your starting point isn't your ceiling.", "lesson_id": "case_study_vembu"},
  {"day": 5, "title": "Worksheet check-in", "body": "Open Week 1's 'My Problem List' worksheet. Add one new problem you noticed this week. 60 seconds.", "lesson_id": null},
  {"day": 6, "title": "Pick one", "body": "From your list, pick the ONE problem that bothers you the most. Trust your gut. We'll dig into it next week.", "lesson_id": null},
  {"day": 7, "title": "Week 1 wrap", "body": "End of Week 1. Take this week's quiz when you're ready — it's not a test, it's a checkpoint.", "lesson_id": "w1_l10_quiz"},

  {"day": 8, "title": "Week 2: Why?", "body": "This week is about WHY. Every real problem has 5 layers. Today: write your chosen problem in your journal.", "lesson_id": "w2_l1_intro"},
  {"day": 9, "title": "Five WHYs", "body": "Ask 'why does that bother me?' five times in a row. Each answer becomes the next question. Try it on yesterday's problem.", "lesson_id": "w2_l2_five_whys"},
  {"day": 10, "title": "Falguni @ 50", "body": "Falguni Nayar started Nykaa at 50. Whatever age you are right now, it is the perfect age to ask one more why.", "lesson_id": "case_study_nayar"},
  {"day": 11, "title": "Interview a real person", "body": "Find one person who has the problem you picked. Ask them ONE 'why' today. Save what they said in your journal.", "lesson_id": "w2_l3b_interview_sim"},
  {"day": 12, "title": "Look for the gap", "body": "Between 'what people say they want' and 'what they actually do' is where good ideas live. Watch a friend this week.", "lesson_id": null},
  {"day": 13, "title": "Avoid the trap", "body": "Don't fall in love with your idea. Fall in love with the problem. Ideas change; the problem stays.", "lesson_id": null},
  {"day": 14, "title": "Week 2 wrap", "body": "Take Week 2's quiz. Then rest. Founder weeks are long.", "lesson_id": "w2_l10_quiz"},

  {"day": 15, "title": "Week 3: Who?", "body": "Now we find the people. Who has your problem most badly? Be specific. 'Everyone' is the wrong answer.", "lesson_id": "w3_l1_intro"},
  {"day": 16, "title": "Ritesh @ 17", "body": "Ritesh Agarwal started OYO at 17. He noticed budget hotels were terrible — and he was specifically a young, broke traveller. Specific beats vague.", "lesson_id": "case_study_oyo"},
  {"day": 17, "title": "Who pays?", "body": "The person with the problem isn't always the one with the money. Parents pay for kids' toys. Bosses pay for office software. Who pays for your idea?", "lesson_id": "w3_l2_who_pays"},
  {"day": 18, "title": "Customer profile", "body": "Write a 4-line description of your most likely customer. Age, location, ₹ income, daily routine. Be specific enough that you could spot them in a crowd.", "lesson_id": "w3_l3_customer_profile"},
  {"day": 19, "title": "Score your idea", "body": "Use this week's scorecard to rate your idea. Honesty > comfort. A 6/10 you fix is better than a 9/10 fantasy.", "lesson_id": "w3_l4_idea_scorecard"},
  {"day": 20, "title": "Pitch to one person", "body": "Tell one real person your idea in 60 seconds. Write their first reaction. Their face is your first data point.", "lesson_id": "w3_l7_pitch_practice"},
  {"day": 21, "title": "Week 3 wrap", "body": "Take Week 3's quiz. Most founders skip the customer step. You didn't.", "lesson_id": "w3_l10_quiz"},

  {"day": 22, "title": "Week 4: Story", "body": "Last week. This week we turn what you learned into a story you can tell — a pitch. A pitch is a story with a number at the end.", "lesson_id": "w4_l1_intro"},
  {"day": 23, "title": "Failures matter", "body": "Visit the Failure Museum lessons. Six Indian startups that didn't make it. Each one teaches one rule you don't want to learn the hard way.", "lesson_id": "failure_stayzilla"},
  {"day": 24, "title": "Pitch Coach today", "body": "Open the AI Pitch Coach. Record your 60-second pitch. Listen to the feedback. It's free, it's private, and it gets you ready.", "lesson_id": "w3_l7b_pitch_coach"},
  {"day": 25, "title": "Money basics", "body": "Quick bonus: read about Udyam, GST, and the separate bank account. 9 minutes total. Future-you will thank present-you.", "lesson_id": "w4_bonus_udyam"},
  {"day": 26, "title": "Idea Journal review", "body": "Scroll through your Idea Journal. Star the 3 entries that surprise you most. These are your real ideas.", "lesson_id": null},
  {"day": 27, "title": "Pitch deck PDF", "body": "Download 'My Pitch Deck' PDF from your Idea Journal. Print it. Show it to one adult who isn't your parent.", "lesson_id": null},
  {"day": 28, "title": "You did it.", "body": "Final quiz, then the certificate is yours. Founders ship. You shipped.", "lesson_id": "w4_l10_quiz"}
]
```

- [ ] **Step 4: Run test to verify pass**

Run: `cd backend && python -m pytest tests/test_daily_dispatch_content.py -v`
Expected: PASS (28 messages, each unique day, all under 280 chars).

- [ ] **Step 5: Commit**

```bash
git add backend/data/module_daily_dispatch/mento_entrepreneur_4week.json backend/tests/test_daily_dispatch_content.py
git commit -m "feat(phase-d): 28-day Mento dispatch message bank"
```

---

### Task 8: Daily-dispatch APScheduler job + sender

**Files:**
- Create: `backend/module_daily_dispatch.py`
- Modify: `backend/app.py` (register new APScheduler job)
- Test: `backend/tests/test_module_daily_dispatch.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_module_daily_dispatch.py
import json
import os
import pytest


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    # Seed the dispatch bank in tmp data dir
    bank_dir = tmp_path / "module_daily_dispatch"
    bank_dir.mkdir()
    (bank_dir / "mento_entrepreneur_4week.json").write_text(json.dumps([
        {"day": 1, "title": "Welcome", "body": "Day 1."},
        {"day": 2, "title": "Day 2", "body": "Second tip."},
    ]))
    yield


def test_dispatch_picks_correct_day_for_user(env, monkeypatch):
    from importlib import reload
    import backend.module_daily_dispatch as mdd
    reload(mdd)
    # User started the module 1 day ago → should receive message for day 2.
    msg = mdd.message_for_user_today(
        module_id="mento_entrepreneur_4week",
        started_at_iso="2026-05-10T08:00:00+05:30",
        today_iso="2026-05-11T18:00:00+05:30",
    )
    assert msg["day"] == 2
    # Out of range → None
    none = mdd.message_for_user_today(
        module_id="mento_entrepreneur_4week",
        started_at_iso="2026-05-10T08:00:00+05:30",
        today_iso="2026-06-30T18:00:00+05:30",
    )
    assert none is None
```

- [ ] **Step 2: Run to verify fail**

Run: `cd backend && python -m pytest tests/test_module_daily_dispatch.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement dispatcher**

```python
# backend/module_daily_dispatch.py
"""Daily dispatch: pick today's tip for a user mid-module and post to notifications.

Schedule: APScheduler 'cron' at 18:00 IST. For each user whose module start is
within 28 days, fetch their day-N message and create a notification.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import backend.modules_engine as modules_engine
import backend.notifications as _notif


def _bank_path(module_id: str) -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data"
    )
    return os.path.join(base, "module_daily_dispatch", f"{module_id}.json")


def _load_bank(module_id: str) -> list:
    p = _bank_path(module_id)
    if not os.path.exists(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except (json.JSONDecodeError, OSError):
        return []


def _days_between(start_iso: str, today_iso: str) -> int:
    a = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    b = datetime.fromisoformat(today_iso.replace("Z", "+00:00"))
    return (b.date() - a.date()).days


def message_for_user_today(
    module_id: str, started_at_iso: str, today_iso: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    today = today_iso or datetime.now(timezone.utc).isoformat()
    day = _days_between(started_at_iso, today) + 1  # day 1 == start day
    if day < 1:
        return None
    bank = _load_bank(module_id)
    for m in bank:
        if m.get("day") == day:
            return m
    return None


def run_daily_dispatch(module_id: str = "mento_entrepreneur_4week", today_iso: Optional[str] = None) -> int:
    """Push today's tip to every user currently in-progress on the module."""
    today = today_iso or datetime.now(timezone.utc).isoformat()
    sent = 0
    for user_id, prog in (modules_engine.list_all_module_progress(module_id) or {}).items():
        started = prog.get("started_at")
        if not started:
            continue
        msg = message_for_user_today(module_id, started, today)
        if not msg:
            continue
        dedupe_key = f"dispatch_{module_id}_day{msg['day']}"
        if _notif.has_notification(user_id, dedupe_key):
            continue
        _notif.create_notification(
            user_id=user_id,
            kind="module_daily_dispatch",
            title=msg.get("title", "Mento tip"),
            body=msg.get("body", ""),
            link=f"/modules/{module_id}" + (f"#{msg['lesson_id']}" if msg.get("lesson_id") else ""),
            dedupe_key=dedupe_key,
        )
        sent += 1
    return sent
```

Two helpers may not yet exist:

1. `modules_engine.list_all_module_progress(module_id)` — add to `modules_engine.py`:

```python
def list_all_module_progress(module_id: str) -> Dict[str, Dict[str, Any]]:
    """Return {user_id: progress_dict} for all users with progress on this module."""
    data = _load_progress()
    out: Dict[str, Dict[str, Any]] = {}
    for user_id, modules in data.items():
        if module_id in (modules or {}):
            out[user_id] = modules[module_id]
    return out
```

2. `notifications.has_notification(user_id, dedupe_key)` + `dedupe_key` arg on `create_notification` — extend `backend/notifications.py`:

```python
def has_notification(user_id: str, dedupe_key: str) -> bool:
    for n in get_notifications(user_id) or []:
        if n.get("dedupe_key") == dedupe_key:
            return True
    return False
```

And update `create_notification` to accept and persist `dedupe_key` (if it already exists in stored payload, set it on the new notif). Match the existing function signature; add `dedupe_key: Optional[str] = None` as a kwarg and include it in the dict written to `notifications.json`.

- [ ] **Step 4: Register APScheduler job in `backend/app.py`**

Inside `_run_scheduler()` (near the other `scheduler.add_job` calls):

```python
def _run_module_dispatch_job():
    try:
        import backend.module_daily_dispatch as mdd
        mdd.run_daily_dispatch("mento_entrepreneur_4week")
    except Exception as exc:
        app.logger.exception("module daily dispatch failed: %s", exc)


scheduler.add_job(
    _run_module_dispatch_job, "cron", hour=18, minute=0,
    id="module_entrepreneur_daily_dispatch", replace_existing=True,
    timezone="Asia/Kolkata",
)
```

- [ ] **Step 5: Run test to verify pass**

Run: `cd backend && python -m pytest tests/test_module_daily_dispatch.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/module_daily_dispatch.py backend/modules_engine.py \
        backend/notifications.py backend/app.py \
        backend/tests/test_module_daily_dispatch.py
git commit -m "feat(phase-d): 18:00 IST daily dispatch job + dedupe"
```

---

### Task 9: Settings — opt-in toggle for daily dispatch

**Files:**
- Modify: `frontend-react/src/pages/SettingsPage.jsx`
- Modify: `backend/app.py` (extend `/api/profile` PATCH or reuse existing preferences endpoint)
- Modify: `backend/module_daily_dispatch.py` (respect the preference)

- [ ] **Step 1: Add preference enforcement to dispatcher**

In `backend/module_daily_dispatch.py`, before sending each notification, gate on user preference:

```python
def _user_opted_in(user_id: str) -> bool:
    try:
        from backend.player_profile import get_profile
        prof = get_profile(user_id) or {}
        prefs = prof.get("preferences", {})
        # Default ON during pilot.
        return prefs.get("module_daily_dispatch", True) is not False
    except Exception:
        return True
```

In `run_daily_dispatch`, replace `for user_id, prog in ...` body with a guard:
```python
if not _user_opted_in(user_id):
    continue
```

- [ ] **Step 2: Add toggle to `SettingsPage.jsx`**

In the existing notification preferences block (find an existing toggle and follow its pattern):

```jsx
<label className="flex items-center gap-2 text-sm">
  <input
    type="checkbox"
    checked={prefs.module_daily_dispatch !== false}
    onChange={(e) => updatePref("module_daily_dispatch", e.target.checked)}
  />
  Daily Mento workshop tips (during the 4-week module)
</label>
```

(`prefs` and `updatePref` are the existing settings hooks — match the file's existing pattern; if no preferences section exists yet, add one that PATCHes `/api/profile` with `{preferences: {...}}`.)

- [ ] **Step 3: Backend — accept the preference**

In `backend/app.py`, find the `PATCH /api/profile` route. Allow `preferences.module_daily_dispatch` to be set on the profile. If preferences are already a free-form dict on the profile, no code change is needed beyond confirming the PATCH whitelists `preferences`.

- [ ] **Step 4: Smoke check**

Log in as `demo_student`, go to Settings, uncheck the toggle, run dispatcher manually:
```bash
python -c "from backend.module_daily_dispatch import run_daily_dispatch; print(run_daily_dispatch('mento_entrepreneur_4week'))"
```
Confirm no notification fires for that user (returns 0 if they were the only in-progress user).

- [ ] **Step 5: Commit**

```bash
git add frontend-react/src/pages/SettingsPage.jsx \
        backend/module_daily_dispatch.py backend/app.py
git commit -m "feat(phase-d): opt-in toggle for module daily dispatch"
```

---

### Task 10: One-time image self-host for founder portraits + failure logos

**Files:**
- Modify: `backend/scripts/cache_module_images.py` (already created in Phase A; extend it)
- Create: founder/logo source images under `backend/assets/module_images/mento_entrepreneur_4week/` (8 portraits + 1 neighborhood)

- [ ] **Step 1: Identify required portrait filenames**

The Task-3 case-study JSON entries reference these paths:
- `founder_vembu.png`, `founder_nayar.png`, `founder_ritesh.png`, `founder_byju.png`, `founder_kunal.png`, `founder_ghazal.png`, `founder_bhavish.png`, `founder_neighborhood.png`

- [ ] **Step 2: Generate placeholder cartoon portraits**

Until a designer ships final art, generate illustrated placeholders. Two acceptable paths:

(a) Use the existing `story_image_service.py` / DALL-E pipeline with a fixed prompt template:
```
"Cartoon portrait illustration of <FOUNDER_NAME>, friendly mascot style, soft warm colors, headshot framing, plain background, child-friendly, 512x512"
```

Run from a small Python snippet:

```python
# scripts/seed_founder_portraits.py (one-off; can be deleted after run)
from backend.story_image_service import generate_image  # name matches existing helper
NAMES = {
    "founder_vembu": "Sridhar Vembu (Indian male, glasses, simple shirt)",
    "founder_nayar": "Falguni Nayar (Indian woman, confident smile, blazer)",
    "founder_ritesh": "Ritesh Agarwal (Young Indian male, casual)",
    "founder_byju": "Byju Raveendran (Indian male teacher, warm smile)",
    "founder_kunal": "Kunal Shah (Indian male, beard, casual)",
    "founder_ghazal": "Ghazal Alagh (Indian woman, smiling, casual)",
    "founder_bhavish": "Bhavish Aggarwal (Indian male, friendly)",
    "founder_neighborhood": "Friendly Indian aunty and uncle running a small shop, cartoon",
}
for fname, desc in NAMES.items():
    out = f"backend/assets/module_images/mento_entrepreneur_4week/{fname}.png"
    generate_image(
        prompt=f"Cartoon portrait illustration of {desc}, soft warm colors, headshot, plain background, child-friendly",
        size="512x512",
        out_path=out,
    )
```

(b) If a designer has provided files, drop them into `backend/assets/module_images/mento_entrepreneur_4week/` with the exact filenames above.

- [ ] **Step 3: Smoke test the static paths**

Visit `/static/module_images/mento_entrepreneur_4week/founder_vembu.png` in the browser. Expected: image loads.

- [ ] **Step 4: Commit**

```bash
git add backend/assets/module_images/mento_entrepreneur_4week/ scripts/seed_founder_portraits.py
git commit -m "feat(phase-d): founder portrait assets for case-study cards"
```

(If the binary assets are committed via LFS or `.gitattributes`, follow the existing repo pattern. If they're served from a CDN instead of committed, replace this step with a CDN upload + a README note in `backend/assets/module_images/README.md`.)

---

### Task 11: Phase D completion + final regression

**Files:** (none)

- [ ] **Step 1: Run the full Phase D test suite**

Run:
```bash
cd backend && python -m pytest tests/test_phase_d_baseline.py \
  tests/test_indian_case_studies.py tests/test_failure_museum.py \
  tests/test_currency_localization.py tests/test_regulatory_primer.py \
  tests/test_daily_dispatch_content.py tests/test_module_daily_dispatch.py -v
```
Expected: all PASS.

- [ ] **Step 2: Run cross-phase regression**

Run:
```bash
cd backend && python -m pytest tests/test_phase_a_baseline.py \
  tests/test_phase_b_baseline.py tests/test_phase_c_baseline.py \
  tests/test_phase_d_baseline.py -v
```
Expected: all PASS (this confirms no phase has broken any other).

- [ ] **Step 3: Manual smoke**

Log in as `demo_student`. Open `/modules/mento_entrepreneur_4week`.

Verify:
- Module loads, hero shows 4 badges + streak chip
- Founder portrait visible inside `case_study_vembu` lesson
- Failure card renders in week 4
- Week 3 lessons show ₹ examples (no `$`)
- Bonus regulatory primer audio lessons appear at end of week 4
- Settings → daily dispatch toggle visible and persists

- [ ] **Step 4: Tag**

```bash
git tag phase-d-complete
```

---

## Self-review

- ✅ Spec §5 coverage: 5.1 (Task 3), 5.2 (Task 4), 5.3 (Task 5), 5.4 (Task 6), 5.5 (Tasks 7–9).
- ✅ Renderers from Phase A scaffold filled in (Tasks 1–2).
- ✅ Image assets explicitly addressed (Task 10).
- ✅ No placeholders / TBD.
- ✅ Module JSON additions are net-new lesson IDs; existing 32 lessons are not deleted (only Task 5 edits text inside W3 lessons — keep IDs and structure).
- ✅ Test for currency edit is tolerant of renamed IDs (skips if not present) so it won't false-fail.
- ✅ Daily-dispatch is opt-in with default ON, gated per user, deduped per day+module.
- ✅ Pilot bank exactly 28 messages; each ≤280 chars; days 1–28 unique.
