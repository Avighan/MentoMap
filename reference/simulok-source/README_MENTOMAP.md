# Simulok source (reference copy)

This is a permanent, read-only reference copy of the Simulok source
(`sumeetonline90/simulok`, private repo), added at the user's request so
it's available to every future session working on this repo — not just
this one — without needing repo access re-granted each time.

**Do not modify anything under this directory.** It's a snapshot for
comparison, not code MentoMap runs. If Simulok changes upstream, replace
this whole directory with a fresh copy rather than hand-editing it.

## Why it's here

Several MentoMap games (Dealcraft, The Mumbai Manufacturer, HelioGrid, and
others — see `docs/SIMULOK_TO_MENTOMAP_MIGRATION_PLAN.md` at the repo
root) were ported from Simulok's game catalog. The backend logic ports
were faithful, but the frontend rebuild (this repo's `frontend-react/`
was missing its bootstrap files entirely and had to be reconstructed)
initially used plain placeholder styling with no reference to how these
games actually looked and played in Simulok. This copy exists so that
gap can be closed properly instead of guessed at.

## Where to look

- `index.html` — the ~29,000-line monolithic client app. Contains the
  `SIM_LIBRARY`-style JSON config for most games (search for a game's
  `"id"` key, e.g. `"id": "dealcraft"`) plus the actual round-choice
  engine, KPI dashboard rendering, and settlement math (e.g.
  `resolveMumbaiSettlement()` for the Mumbai Manufacturer).
- `assets/sim/` — cover art for each simulation.
- `website/` — the separate marketing site (simulok.in), not the app
  itself.
- `classroom/` — the classroom/instructor console, a separate concern
  from individual gameplay.

## Known gap

This snapshot has a full, playable implementation of Dealcraft and The
Mumbai Manufacturer, but HelioGrid only appears as a catalog teaser
entry (title/description/meta for the discovery page) — no game engine
or UI for it exists in this copy. Its real lever schema (list price,
per-segment discounts, per-segment sales allocation, headcount, comms
spend, R&D spend) is defined in MentoMap's own
`backend/games/heliogrid_engine.py` and `backend/games/heliogrid.json`,
which is the authoritative source for what UI it needs — there is
nothing further to port from Simulok for this one.
