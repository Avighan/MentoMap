# Editing the Simulok demo with AI (Cursor / ChatGPT)

**Audience:** you + any AI assistant (Cursor, ChatGPT, Claude, etc.) updating the Simulok sales/demo prototype.

Read this file first before changing the demo. Also read **`TEAM_ONBOARDING.md`** — new simulations are built in a **personal sandbox file**, then merged into main `index.html` only after review.

> **Changing the public website (https://simulok.in) instead?** That is a
> different product with different rules — see **`CLAUDE.md`** and
> **`website/README.md`**. Short version: the site is built from `website/` in
> this repo and deployed by GitHub Actions on every merge to `main`. There is
> no server to edit. Edit files → commit → PR → merge → live in about a minute.

Prefer small, targeted edits. After changes: sync → smoke-test → commit → push.

---

## How sales runs the demo (standalone)

**Yes — sales can still run it without installing anything.** Double-click **`index.html`** in Chrome or Edge.

**Best handoff:** zip **`index.html` + `assets/`** together (keep them in the same folder after unzip). Do not send `index.html` alone.

1. Zip **`index.html`** and the **`assets/`** folder from the same parent directory.
2. Sales unzips, then double-clicks **`index.html`** (Chrome or Edge recommended).

That is the whole runtime: no npm, no server, no login backend.

| What they need | Why |
|----------------|-----|
| `index.html` | The full app (UI + all simulation logic) |
| `assets/` (`assets/sim/*.jpg`) | Catalog cards and briefing hero images |

If someone only copies `index.html` and leaves `assets/` behind, the sims still play, but catalog and briefing images will be missing.

Demo login: **Continue as Demo User** or **Instructor / Admin**. Sign out clears the in-memory session.

---

## What to edit (and what not to)

### Commit these (public runnable demo)

| Path | Role |
|------|------|
| **`index.html`** (repo root) | Single-file app: HTML + CSS + JS |
| **`assets/sim/*.jpg`** | Catalog / briefing images |
| **`README.md`** | How to open the demo |
| **`EDITING_WITH_AI.md`** | This guide |
| **`TEAM_ONBOARDING.md`** | How humans + AI tools add sims via sandbox files |
| **`.gitignore`** | Keeps local Docs/App out of GitHub |

### Local only (gitignored — do not push unless asked)

| Path | Role |
|------|------|
| `App/Inventory Simulation Prototype/` | Working copy of the HTML + assets |
| `Docs/` | Source scripts (docx/pdf) |
| `_gen/` | Temporary generation scripts |

### Size rule

Keep **`index.html` under ~1 MB**. Put images in `assets/sim/` as compressed JPGs (~50–120 KB each), not as huge base64 blobs inside the HTML.

---

## Sync before every GitHub push

If you edited the App working copy:

```powershell
Copy-Item "App\Inventory Simulation Prototype\index.html" -Destination "index.html" -Force
New-Item -ItemType Directory -Force -Path "assets\sim" | Out-Null
Copy-Item "App\Inventory Simulation Prototype\assets\sim\*" -Destination "assets\sim\" -Force
```

Then commit and push only the runnable files (see GitHub section).

---

## Architecture map (do not break)

```
Login (Participant | Instructor)
  → Participant: Catalog (Graduates / Schools / Corporates / Specialisation / All)
       → Briefing → Rounds (+ Mumbai events only for mumbai) → Results → Catalog
  → Instructor: Console (roster + settings) ↔ Catalog / Preview simulation
Sign out → Login (clears in-memory state)
```

### Two ways sims are stored

1. **Legacy dedicated engines** (special code paths — edit carefully):
   - `mumbai` — The Mumbai Manufacturer (rounds + crisis events)
   - `lemonade` — Lemonade Stand (**Schools only**)
   - `finance` — Summer Money Challenge
   - `bazaar` — The Great Indian Bazaar
   - `k2-ascent` — **K2 — The Savage Mountain** (hot-seat team engine — **not** `SIM_LIBRARY`)
   - `heliogrid` — **HelioGrid — Choose Your Customer** (B2B STP quarterly engine — **not** `SIM_LIBRARY`)
   - `macroecon` — **MacroEcon: The Kalyana Mandate** (seven-year fiscal-policy engine — **not** `SIM_LIBRARY`)

2. **`SIM_LIBRARY`** — data-driven sims (preferred for new MCQ-style titles).  
   The shared engine uses: `initialState`, `roundConfigs`, `kpiKeys`, `score`, `briefing`, `resultsLedgerRows`, etc.

**K2 note:** Do **not** route `k2-ascent` through `SIM_LIBRARY` or the 7×4 MCQ loop. It uses `k2Sim`, `k2InitialState()`, and `k2RenderPlay()` (lobby → private briefs → votes → resolve → dashboard). Original IP-safe content only — do not copy HBSP Everest V3 text, art, or role names.

**HelioGrid note:** Do **not** route `heliogrid` through `SIM_LIBRARY`. It uses `hgSim`, `hgInitialState()`, and `hgRenderPlay()` (Pulse / Analyze / Decide tabs, positioning map, quarterly levers). Original IP-safe content only — do not copy HBSP Managing Segments and Customers text, segment letters A–D, motion-capture product, or UI copy.

**MacroEcon note:** Do **not** route `macroecon` through `SIM_LIBRARY`. It uses `meSim`, `meInitialState()`, and `meRenderPlay()` (Pulse / Analyze / Decide tabs, yearly levers). Original IP-safe content only — do **not** copy HBSP Econland text, art, role names, or scenario labels.

### Key symbols in `index.html`

| Symbol | Purpose |
|--------|---------|
| `CATALOG_SIMS` | Cards in the library UI |
| `SIM_LIBRARY` | Playable data for the 20 library sims |
| `cloneState` / `getActiveRoundConfigs` / `getKpiKeys` / `maxRounds` | Engine switchboard |
| `calculateScore` / `renderBriefing` / `renderResults` / `renderRound` | Play + scoring UI |
| `progressHtml` / `roundInsightTabs` / `conditionCardsHtml` / `KPI_GLOSSARY` | Shared stage map + Conditions/Parameters tabs on every round |
| `getActiveSimTitle` / `updateSimChrome` | Puts the running sim name in the briefing / play / results top bar |
| `isSimInLibrary(id)` | True when sim comes from `SIM_LIBRARY` |

---

## Current playable catalog

| Segment | IDs |
|---------|-----|
| **Graduates** | `mumbai`, `dealcraft`, `brand-wars`, `founders-forge`, `blue-ocean`, `capital-storm`, `k2-ascent`, `heliogrid`, `macroecon` |
| **Schools** | `lemonade`, `finance`, `bazaar`, `fraction-market`, `prob-carnival`, `lab-protocol`, `eco-balance`, `forces-play`, `macroecon` |
| **Corporates** | `pharma-batch`, `pharma-medaffairs`, `auto-launch`, `auto-dealer`, `fmcg-promo`, `k2-ascent`, `heliogrid` |
| **Specialisation** | `invogrid`, `indas-peak`, `kavericirp`, `tplex`, `sutracode` |

**Product rule:** Lemonade Stand stays **Schools-only**. Do not add `graduates` to its `segments` unless the product owner asks.

**Specialisation rule:** CA sims use fictional clients and firms only. Do **not** impersonate ICAI exams, copy ICAI study material, or use ICAI logos. Position as ICAI New Scheme–aligned practice labs.

---

## Copy-paste prompts for AI

### Change branding / login only
```
Open index.html. Update the login screen only.
Keep platform-level messaging (no per-sim stats).
Title must say "User Login". Keep Participant vs Instructor tabs.
Do not break navigation or the simulation engine.
```

### Move a sim between catalogs
```
In index.html, update CATALOG_SIMS (and SIM_LIBRARY.segments if it is a library sim).
segments is an array, e.g. ['schools'] or ['graduates'].
Lemonade must remain Schools-only unless I explicitly say otherwise.
Keep available: true and image paths working.
```

### Edit one legacy sim (mumbai / lemonade / finance / bazaar / k2-ascent / heliogrid / macroecon)
```
In index.html, find the correct config:
- mumbai → roundConfigs / eventConfigs
- lemonade → lemonadeRoundConfigs (+ crisis/growth choice pools)
- finance → financeRoundConfigs
- bazaar → bazaarRoundConfigs
- k2-ascent → k2Sim + k2Render* functions (hot-seat flow)
- heliogrid → hgSim + hgRenderPlay() (Pulse / Analyze / Decide, positioning map)
- macroecon → meSim + meRenderPlay() (Pulse / Analyze / Decide, yearly fiscal levers)
Update Round X as follows: …
Keep choice shape: id, label, description, effects, strategic_type, feedback, learning.
Do not rename effect keys unless you also update scoring and KPI display.
For K2: edit roles, injections in k2ResolveRound(), debrief in k2Sim.debrief — no HBSP Everest copy.
For HelioGrid: edit hgSim segments/features and hgResolveQuarter() — no HBSP Managing Segments copy.
For MacroEcon: edit meSim.years / meResolveYear() — no HBSP Econland copy.
```

### New simulation in a sandbox file (default for team members)
```
Read EDITING_WITH_AI.md and TEAM_ONBOARDING.md first.

Do NOT edit the shared index.html until I say this sim is approved.

1. Copy index.html to index-<myname>.html if that file does not exist.
2. Add the new simulation only in index-<myname>.html.
3. Add assets/sim/<id>.jpg.
4. Prefer SIM_LIBRARY (7 rounds × 4 choices) unless I ask for a special engine.
5. Keep original content — no HBSP verbatim text.
6. Smoke-test by opening index-<myname>.html.

When I later say "promote to main", port the sim into index.html (CATALOG_SIMS + engine),
update README.md and EDITING_WITH_AI.md catalog lines, and do not break other sims.
```

### Edit or add a SIM_LIBRARY sim
```
In index.html, update SIM_LIBRARY['<id>'].
Keep: segments, image, title, description, meta, constraints:'school', maxRounds,
briefing, kpiKeys, initialState, score, resultsLedgerRows, roundConfigs.
Standard new sims: 7 rounds × 4 choices.
Also update/add the matching CATALOG_SIMS card (available:true).
Add assets/sim/<id>.jpg if new.
Keep text short so the file stays under ~1MB.
```

### Change scoring / results copy
```
For library sims: edit SIM_LIBRARY[id].score and resultsLedgerRows / resultsReflection.
For legacy sims: edit calculateScore() branch and renderResults() ledger for that activeSimId.
Keep grade bars + profile + cash/value chart working.
```

### UI / animations / images
```
CSS motion lives in the “Aesthetic motion” block.
Catalog cards: .sim-card / .sim-card-media. Briefings: .brief-hero.
Round play uses a shared stage board (`progressHtml`) plus tabs:
Situation | Conditions | Parameters | Round data.
The running sim name is centered in the briefing/play/results top bar (`updateSimChrome`).
Do not remove roundInsightTabs / conditionCardsHtml when editing a sim.
Images: compress JPG under assets/sim/, reference with relative paths.
Respect prefers-reduced-motion.
```

### Instructor console
```
Update Instructor Console UI and in-memory instructorRoster / instructorConfig.
cfg-sim options rebuild from CATALOG_SIMS at page load — do not hardcode a long static list.
This prototype does not persist to a server.
```

---

## SIM_LIBRARY entry checklist (new sim)

Minimum fields:

```js
'<id>': {
  segments: ['graduates' | 'schools' | 'corporates' | 'specialisation'],
  featured: true,
  available: true,
  image: 'assets/sim/<id>.jpg',
  title: '...',
  description: '...',
  meta: ['...', '7 rounds', '...'],
  constraints: 'school',
  maxRounds: 7,
  briefing: { eyebrow, title, heroImage, heroAlt, narrative, quote, profile, steps, rules },
  kpiKeys: [{ key, label }, ...],  // usually cash, reputation, skills, energy, integrity
  initialState: { cash, reputation, skills, energy, integrity, current_round: 1,
                  decisionHistory: [], eventHistory: [], strategic_choices: [], cashHistory: [start] },
  score: { categories: [...], grades: [...], profileName, profileBlurb },
  resultsEyebrow, resultsLedgerTitle, chartLabel, profileEyebrow,
  resultsLedgerRows: [{ key, label, format: 'money'|'round' }, ...],
  resultsReflection: 'HTML fragment with Reflect questions',
  roundConfigs: { 1: { title, narrative, choices: [4] }, /* ... through 7 */ }
}
```

Choice shape:

```js
{ id, label, description, effects, strategic_type, feedback,
  learning: { key_concept, principle, application, trade_offs } }
```

Also add a matching **`CATALOG_SIMS`** card with the same `id`, `segments`, `image`, `title`, `description`, `meta`, `featured`, `available: true`.

---

## Smoke-test checklist (after any edit)

1. Open root `index.html` in the browser.
2. Demo User → **Graduates**: Lemonade is **not** listed; start one library sim → play 2 rounds.
3. **Schools**: Lemonade is listed; start one maths/science sim → play 1–2 rounds.
4. **Corporates**: start one Pharma/Auto/FMCG sim → play 1–2 rounds.
5. **Specialisation**: start InvoGrid → play 1–2 rounds; confirm CA KPI labels load.
6. Finish or restart → Back to dashboard → Sign out.
7. Instructor preview: pick a library sim → Preview as participant.

---

## Rules for safe AI edits

1. **No** localStorage / sessionStorage unless product owner asks.  
2. **No** npm / React / backend in this prototype.  
3. Keep footer: `Prototype — Simulok.ai`.  
4. Briefings explain **how it works / rules / steps** — not long learning-objective lists.  
5. Prefer editing **`SIM_LIBRARY`** for new titles instead of copying Mumbai/Lemonade engine code.  
6. Before GitHub upload: sync App → root; do **not** commit `Docs/`, `App/`, or `_gen/`.

---

## GitHub (commit + push)

```powershell
git add index.html assets README.md EDITING_WITH_AI.md .gitignore
git status
git commit -m "Describe why the demo changed."
git push origin main
```

Repo: https://github.com/sumeetonline90/simulok

Do not force-push `main` unless the product owner explicitly asks.
