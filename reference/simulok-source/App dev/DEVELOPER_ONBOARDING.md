# Simulok — Developer onboarding brief

**Also available as Word:** `App dev/DEVELOPER_ONBOARDING.docx` (same content — share this file with developers before they have repo access).

**Audience:** App / simulation developers joining the build  
**Owner:** Sumeet · Fourtains / Simulok  
**Purpose:** How we specify each simulation, how to try the live prototype, how to get code access, and how classroom scoring works.

---

## 1. How we specify a simulation (start with Zara BM)

Each new simulation is handed to engineering as a **folder of design artefacts**, not only a verbal brief. We will keep adding titles the same way.

For **Zara — Business Model & Globalization**, open:

`App dev/Zara-BM-Strategy-Simulator/`

(or the zip: `App dev/Zara BM Strategy Simulator - Snehal Mam-20260907T110755Z-1-001.zip`)

| Document | File | What you use it for |
|----------|------|---------------------|
| **Round-by-round script** | `Zara-Round-Script.docx` | Narrative, decisions, outcomes, and flow for every round |
| **Low-level design (LLD)** | `Zara-BM-Globalization-LLD ver 1.docx` | Structure, state, scoring logic, and implementation detail |
| **UI / prototype guide** | `Zara-Prototype-Guide.docx` | Screens, interaction, and look-and-feel targets |
| **Student handbook** | `Zara-BM-Globalization-Student-Handbook.pdf` | What the learner experiences — use this as the “what the sim feels like” reference |

**Working rule:** before coding a new title, get (or create) this same quartet — script, LLD, UI guide, learner-facing handbook — then implement in a personal sandbox file and merge into the shared catalog when ready (see `TEAM_ONBOARDING.md` and `EDITING_WITH_AI.md` once you have repo access).

The playable Zara BM title in the prototype is **`zara-new`** (“Zara — Business Model & Globalization”). There is also a separate Fast-Fashion Zara title (`zara`) — do not mix them up.

---

## 2. Try the live platform (Demo User / Demo Instructor)

No Google Sheet or roster required for a walkthrough.

| | |
|--|--|
| **Platform** | https://simulok.in/platform/ |
| **Marketing site** (not the sims) | https://simulok.in/ |

**How to showcase**

1. Open https://simulok.in/platform/
2. **Participant** tab → **Continue as Demo User** — browse the catalog and open simulations (including both Zara titles).
3. **Instructor / Admin** tab → **Continue as Demo Instructor** — see the instructor console (session controls are for classroom/Sheet mode; demo still shows the console layout).

**Focus for this brief:** open **Zara — Business Model & Globalization** as Demo User and walk a few rounds so you match the handbook + prototype guide to the live UI.

Optional classroom score preview (sample data, no login):  
https://simulok.in/platform/classroom/dashboard.html?demo=1

---

## 3. GitHub — request access to the code

| | |
|--|--|
| **Repository** | **https://github.com/sumeetonline90/simulok** |
| **Short name** | `sumeetonline90/simulok` |

**Access**

1. Create a GitHub account if you do not have one: https://github.com/join  
2. Email your **GitHub username** to Sumeet (`sumeetonline90@gmail.com`) and ask to be added as a collaborator on `sumeetonline90/simulok`.  
3. Accept the invite, then:

```bash
git clone https://github.com/sumeetonline90/simulok.git
```

Primary files once inside: `index.html` (catalog + sims), `assets/`, `EDITING_WITH_AI.md`, `TEAM_ONBOARDING.md`, `CLAUDE.md`.

---

## 4. Classroom guides — how sims run and how scores are captured

Classroom mode is the confidence layer used in a live class: faculty opens a session, students sign in with ID + name + password, rounds and completions go to a Google Sheet, and the instructor dashboard shows leaderboard + report cards.

| Guide | URL | Who |
|-------|-----|-----|
| **Student guide** | https://simulok.in/platform/classroom/guide/student/ | Share with learners only |
| **Instructor guide** | https://simulok.in/platform/classroom/guide/instructor/ | Faculty / product — **do not** send to students |

**What developers should take from these**

- Students play the **assigned** sim once per sitting (unless faculty resets or opens a new session).
- Each round can log KPIs (e.g. stores, profit, revenue, share for Zara) into the session Sheet tab.
- On finish, a completion / report card is written; the instructor dashboard shows grade, score mix, highlights, and round-by-round detail.
- Backend for that layer: `tools/classroom-session.gs` + client `assets/js/classroom.js` (read after you have repo access). Ops setup notes: `tools/CLASSROOM.md` (internal).

Sample classroom login (only when a faculty session is open): instructor `FACULTY` / `faculty-demo`; students `MBA01`… from the roster CSV in the repo.

---

## Quick checklist for a new developer

1. Read the four Zara BM documents in `App dev/Zara-BM-Strategy-Simulator/`.  
2. Walk the platform as **Demo User** and open **Zara — Business Model & Globalization**.  
3. Skim the **instructor** classroom guide and the **dashboard demo** link.  
4. Request collaborator access to **`sumeetonline90/simulok`**.  
5. After access: read `TEAM_ONBOARDING.md` + `EDITING_WITH_AI.md`, then build in a personal sandbox file.

---

*Simulok.ai · Fourtains — developer brief*
