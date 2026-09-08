# Simulok Prototype — Team Development Guide

Welcome to the Simulok.ai prototype. This guide is for **anyone** who will build simulations — including if you use **Cursor, Claude, ChatGPT, or another AI coding tool**.

**Team:** Ganesh, Sumeet, Anup  
**Repo:** https://github.com/sumeetonline90/simulok

**How we add simulations:** each person builds in **their own file**. When it looks good, we copy that sim into the **main** `index.html` (the file that holds the full catalog for sales demos).

---

## Step 1 — Get the repo

Clone or download:

**https://github.com/sumeetonline90/simulok**

| File | Why you need it |
|------|------------------|
| `index.html` | The live demo — all current simulations in one file. Double-click in Chrome/Edge. |
| `assets/sim/` | Catalog and briefing images. Keep this folder next to `index.html`. |
| `EDITING_WITH_AI.md` | **Give this to your AI first.** Architecture, sim IDs, what is safe to edit, IP rules. |
| `README.md` | How to open the demo and how to zip it for sales. |
| `TEAM_ONBOARDING.md` | This file. |

If you do not use git yet: **Code → Download ZIP** on GitHub.

---

## Step 2 — GitHub access

1. Create an account at [github.com](https://github.com/join) if you need one.
2. Send your GitHub username to Sumeet (sumeetonline90@gmail.com).
3. Accept the collaborator invite, then:

```
git clone https://github.com/sumeetonline90/simulok.git
```

---

## Step 3 — Open in Cursor / Claude and scan (do this first)

You do **not** need to learn the whole `index.html` by hand. Point your AI at the repo and let it scan.

### Cursor
1. **File → Open Folder** on the cloned `simulok` folder.
2. Open a new Agent/Chat.
3. Paste the starter prompt below.

### Claude (Claude Code, Cowork, or Claude.ai with the folder)
1. Open the `simulok` folder as the project.
2. Paste the same starter prompt.

### ChatGPT / other tools
Attach or `@` these files first: `EDITING_WITH_AI.md`, `TEAM_ONBOARDING.md`, `README.md`, then `index.html`.

### Starter prompt (copy-paste)

```
Scan this Simulok repo before writing any code.

Read first:
1. EDITING_WITH_AI.md — architecture, sim IDs, engines vs SIM_LIBRARY, IP rules
2. TEAM_ONBOARDING.md — we build new sims in a personal file, not main index.html
3. README.md — how the demo runs (index.html + assets/)

Then tell me:
- How simulations are stored (CATALOG_SIMS, SIM_LIBRARY, dedicated engines)
- Which file I should create for my sandbox copy
- The checklist for a new playable sim

Do not edit index.html on main until I say the sandbox sim is approved.
Do not copy Harvard Business Publishing text, role names, or proprietary challenges.
```

After that scan, describe the simulation you want in plain language (audience, topic, number of rounds, Graduates / Schools / Corporates / Specialisation).

---

## Step 4 — Build in your own file (sandbox)

**Do not put a brand-new simulation straight into the shared `index.html`.** That file is the sales catalog. Two people editing it at once will overwrite each other.

### Recommended sandbox

1. Copy the running demo so you have a private playground:

```
copy index.html index-YOURNAME.html
```

Example: `index-ganesh.html`, `index-anup.html`.

2. Ask your AI to add **your** new simulation only inside `index-YOURNAME.html` (catalog card, briefing, rounds, scoring, image under `assets/sim/`).

3. Open **`index-YOURNAME.html`** in Chrome/Edge to test. Keep `assets/` in the same folder.

4. Optional: also use a git branch (`ganesh-dev`) so your sandbox file can be pushed without touching `main`’s catalog.

### What “done” looks like in the sandbox

- The sim starts from the catalog, plays through all rounds, and reaches results.
- Images load (`assets/sim/<id>.jpg`).
- It follows `EDITING_WITH_AI.md` (size under ~1 MB, original content, correct catalog segment).

---

## Step 5 — Promote into the main catalog (only when it is good)

When Sumeet (or the reviewer) agrees the sandbox sim is ready:

1. Ask your AI to **port** that sim from `index-YOURNAME.html` into **`index.html`**:
   - Add a `CATALOG_SIMS` card (`available: true`)
   - Add `SIM_LIBRARY` data **or** a dedicated engine (like K2 / HelioGrid) if it is not a 7×4 MCQ
   - Copy the image into `assets/sim/`
   - Update `README.md` and `EDITING_WITH_AI.md` catalog lists
2. Smoke-test the **main** `index.html` (login → catalog → your sim → one full run). Other sims must still start.
3. Open a Pull Request into `main`, or ask Sumeet to merge.

Until that merge, sales keeps using the current `index.html` on `main`.

---

## Step 6 — Small edits to an existing sim

If you are only changing copy, a KPI, or a bug in a sim that is **already** on `main`:

- Use a **branch** (`git checkout -b yourname-fix-x`).
- Still have the AI read `EDITING_WITH_AI.md` first.
- Do not rewrite unrelated sims in the same PR.

---

## Quick reference

| Item | Path |
|------|------|
| Sales / demo catalog | `index.html` |
| Your work-in-progress | `index-YOURNAME.html` |
| AI playbook | `EDITING_WITH_AI.md` |
| Images | `assets/sim/` |
| Repo | https://github.com/sumeetonline90/simulok |
| Access | Sumeet — sumeetonline90@gmail.com |

**Rule:** sandbox file first → review → then merge into main `index.html`.
