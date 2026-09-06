# Running MentoMap locally (phase1-pilot-games branch)

This was validated by actually installing dependencies and trying to boot
both sides on this branch, not by guessing from file names. **Bottom line:
neither the backend nor the frontend currently boots from a fresh clone of
this branch** — both are missing bootstrap/entrypoint files that have never
been committed to this repository, on any branch. This doc gives the exact
commands to reproduce that, plus what to run once those files exist.

## Backend

### What actually works

```bash
cd backend
pip install flask flask_cors python-dotenv flask-limiter PyJWT bcrypt requests \
            openai cffi pytest pytest-cov
python3 -c "import app"
```

The install succeeds. The import fails, immediately, with:

```
ModuleNotFoundError: No module named 'storage'
```

`backend/app.py` imports the following local modules at module level, in
this order. **None of them exist in the repo — `git log --all` shows zero
commits ever touching any of these paths, on any branch** — so this isn't
something the scoring-registry work broke; the app has apparently never
been importable from this checkout:

```
storage.py            storage_interface.py   engine.py
adaptive_engine.py     mento_score.py         game_visibility.py
game_ratings.py        admin.py               auth.py
game_storage.py        crafting_engine.py     tech_tree_engine.py
rng_engine.py           template_engine.py     dialogue_engine.py
rpg_engine.py           wallet.py              learning_analytics.py
audio_negotiation_engine.py
engines/multiplayer_engine.py
engines/realtime_multiplayer_engine.py
engines/sim_ux_enrichment.py
```

I did not try to fabricate these (auth, wallet/payments, the core game
engine, admin) — that's substantial proprietary logic, not something safe
to reconstruct by guessing from call sites in a 28k-line `app.py`. If you
have these files from elsewhere (another checkout, a private layer that
didn't make it into this repo), drop them into `backend/` and
`backend/engines/` and the app should import.

### Env vars app.py actually reads (for when the above is resolved)

```bash
export SECRET_KEY="dev-secret-change-me"        # Flask session signing; random+ephemeral if unset
export JWT_SECRET_KEY="dev-secret-change-me"     # falls back to SECRET_KEY; app.py warns if left at a default value
export FLASK_ENV="development"
export SENTRY_DSN=""                             # optional, error tracking
export OPENAI_API_KEY=""                          # optional, only needed for AI-graded features (llm.py)
export ELEVENLABS_VOICE_EN="21m00Tcm4TlvDq8ikWAM"  # optional, TTS voice id, has a default
export MENTO_DATA_DIR=""                          # optional, overrides where JSON data files live (defaults to backend/data)
```

### Command + port (once the modules above exist)

```bash
cd backend
python3 app.py
# -> http://localhost:5001, health check at GET /health or GET /api/health
```

## Frontend

### What actually works

```bash
cd frontend-react
npm ci
npm run test -- --run   # vitest — this genuinely runs, see Step 1 results
```

### What's missing to actually serve the app

```bash
npx vite --port 5173
# starts fine (no vite.config.js needed — Vite's defaults are enough)
curl http://localhost:5173/
# -> HTTP 404, because there is no index.html at the project root
```

Vite serves `index.html` as the SPA entry point in dev mode; without it
there's nothing to render. Also missing, and referenced by existing
components (so the app would still fail to build even with an index.html
added back):

```
frontend-react/vite.config.js
frontend-react/index.html
frontend-react/src/main.jsx
frontend-react/src/App.jsx
frontend-react/src/hooks/useEngagementSystem.js
frontend-react/src/hooks/useSoundscape.js
frontend-react/src/components/game/BoardGameExtras.jsx   (FloatingDeltaLayer, StreakBanner)
```

The first four are the standard Vite/React bootstrap (safe, generic
boilerplate — happy to add if useful) — the hooks and `BoardGameExtras`
are a gamification/engagement layer (streak banners, floating score
deltas, screen shake) that I did not try to invent, same reasoning as the
backend engine/auth modules: it's product-specific interaction design, not
something to guess at.

One related file I *did* add since it's pure framework wiring with no
design decisions (see Step 1): `frontend-react/src/i18n.js`, which wires
up `frontend-react/src/locales/{en,hi}.json` via `react-i18next`. Once
`main.jsx` exists, have it `import "./i18n"` once at startup so
`useTranslation()` calls across the app pick up a real i18next instance
instead of running in the degraded no-instance state they're in today.

### Command + port (once the files above exist)

```bash
cd frontend-react
npm ci
npm run dev   # vite, defaults to http://localhost:5173
# or, matching .claude/launch.json's "frontend-local" config:
npx vite --port 5173
```

If the backend is running separately, the frontend will need an API base
URL. No `VITE_API_*` env var is read anywhere in the current `src/`
tree (nothing came up searching for `import.meta.env` against an API
base), so once `src/api/` files exist check them directly for the actual
base-URL convention rather than assuming one.

## Summary: exact command sequence

```bash
# Backend — installs fine, import fails on missing local modules (see above)
cd backend
pip install flask flask_cors python-dotenv flask-limiter PyJWT bcrypt requests openai cffi pytest
python3 -c "import app"        # ModuleNotFoundError: No module named 'storage'
# once storage.py + the other 21 listed modules exist:
export SECRET_KEY="dev-secret-change-me"
export JWT_SECRET_KEY="dev-secret-change-me"
python3 app.py                 # http://localhost:5001, GET /health

# Frontend — installs and tests fine, dev server 404s on missing index.html
cd frontend-react
npm ci
npm run test -- --run          # vitest suite genuinely runs
npx vite --port 5173 &
curl http://localhost:5173/    # 404 — no index.html
# once vite.config.js / index.html / main.jsx / App.jsx / the hooks above exist:
npm run dev                    # http://localhost:5173
```
