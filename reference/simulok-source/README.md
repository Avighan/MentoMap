# Simulok.ai — Demo Prototype

Interactive business simulation demo for sales and internal walkthroughs.

> **Looking for the public website?** It is live at <https://simulok.in>, built
> from [`website/`](website/) in this repo and deployed automatically on every
> merge to `main`. See [`CLAUDE.md`](CLAUDE.md) for the edit-and-publish flow
> and [`website/README.md`](website/README.md) for the site itself.
> The prototype below is also republished at <https://simulok.in/platform/> for
> the team — that link is unlisted, not linked from any page on the site, and
> visitors browsing the site are still routed to a booked demo, not into the
> simulations.

## Send to sales (how to run)

**No install.** Sales can double-click **`index.html`** in Chrome or Edge.

**Best handoff:** zip **`index.html` + `assets/`** together and send the zip. After unzipping, keep those two in the **same folder** — catalog and briefing images live in `assets/sim/`.

If you send **only `index.html`**, the simulations still play, but catalog cards and briefing images will be missing.

That is all. There is no app to install, no password server, and no setup.

### If double-click does not open the browser

- Right-click `index.html` → **Open with** → Chrome or Edge  
- Or drag `index.html` into an open Chrome/Edge window

## What’s in the demo

**Graduates**
- The Mumbai Manufacturer
- Dealcraft (Negotiation)
- Brand Wars (Marketing)
- Founders' Forge (Startup)
- Blue Ocean Sprint (Strategic innovation)
- Capital Storm (Corporate finance)
- K2 — The Savage Mountain (Team leadership · hot-seat)
- HelioGrid — Choose Your Customer (B2B marketing · STP)
- MacroEcon: The Kalyana Mandate (fiscal + monetary policy · 7 years)

**Schools**
- Lemonade Stand
- Summer Money Challenge
- The Great Indian Bazaar
- Fraction Market · Probability Carnival (Maths)
- Lab Protocol · Ecosystem Balance · Forces in Play (Science)
- MacroEcon: The Kalyana Mandate (fiscal + monetary policy · 7 years)

**Corporates (employee L&D)**
- HelioGrid — Choose Your Customer (B2B marketing · STP)
- K2 — The Savage Mountain (Leadership & teams · hot-seat)
- Batch Release Call · Med Affairs Crossroads (Pharma)
- Launch Gate · Dealer Alignment (Automotive)
- Promo War Room (FMCG)

**Specialisation (Chartered Accountancy · ICAI-aligned)**
- InvoGrid — The ITC Mandate (GST · ITC · notices)
- IndAS Peak — The Statutory Close (Ind AS · listed close)
- KaveriCIRP — 330 Days (IBC · insolvency)
- TPlex — The Arm's-Length File (Transfer pricing · international tax)
- SutraCode — The Independence Test (Audit · ethics · SAs)

Original cases aligned to ICAI New Scheme competencies — **not** an ICAI product or official exam.

## Demo tips

- Click **Continue as Demo User** (participant) or switch to **Instructor / Admin**.
- Use **Sign out** in the top-right menu to return to login.

## Editing with AI

See **`EDITING_WITH_AI.md`** for safe prompts, sim IDs, and sync steps before push.

**IP:** MacroEcon: The Kalyana Mandate is original. Do **not** copy HBSP Econland text, art, role names, or scenario labels.

Building a new simulation? See **`TEAM_ONBOARDING.md`**: scan the repo with Cursor/Claude, work in `index-YOURNAME.html`, then merge into main `index.html` after review.

## Note

This is a **prototype** for demos. Nothing is saved to a real server; refresh or sign-out clears the session.

## Repository map

| Path | What it is |
|------|------------|
| `index.html` | The demo prototype — all simulations in one file. Double-click in Chrome/Edge. |
| `assets/sim/` | Catalog and briefing images for the prototype. |
| `website/` | The public marketing site (GitHub Pages). |
| `tools/build-site.sh` | Assembles `_site/` = website at `/`, team-only prototype link at `/platform/`. |
| `.github/workflows/pages.yml` | Builds and deploys the site on every push to `main`. |
| `website/CNAME` | Binds the site to `simulok.in`. Do not delete. |
| `CLAUDE.md` | Repo guide for Claude Code / Cursor / any AI assistant. |
| `EDITING_WITH_AI.md` | AI playbook for editing the prototype. |
| `TEAM_ONBOARDING.md` | How the team builds new simulations. |
