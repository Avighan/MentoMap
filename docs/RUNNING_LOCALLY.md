# Running MentoMap locally (restore-missing-core-modules branch)

This has been validated end-to-end by actually installing dependencies,
booting both sides, registering a user, logging in, and playing a pilot
game to completion through the real HTTP routes — not by guessing from
file names. **Both the backend and the frontend now boot from a fresh
clone of this branch.** The 28 local Python modules `backend/app.py`
imports at module level (`storage.py`, `engine.py`, `auth.py`, `wallet.py`,
and the rest — see git history on this branch for the full list) have
all been restored, along with the frontend's Vite/React bootstrap files
and several deeper transitive gaps discovered while making the app
actually run (see the branch's commit log for the definitive list and
the call-site evidence behind each one).

## Backend

### Install + boot

```bash
cd backend
pip install flask flask_cors python-dotenv flask-limiter PyJWT bcrypt requests \
            openai cffi pytest pytest-cov reportlab Pillow

export SECRET_KEY="dev-secret-change-me"        # Flask session signing
export JWT_SECRET_KEY="dev-secret-change-me"    # falls back to SECRET_KEY; app.py warns if left at a default value
export FLASK_ENV="development"

python3 app.py
# -> http://localhost:5001, health check at GET /health
```

`reportlab` and `Pillow` are additional dependencies beyond the original
list above — `idea_journal_pdf.py` and `share_card.py` (pre-existing,
not part of this restoration) import them, and their tests fail without
them installed.

### Other env vars app.py reads

```bash
export SENTRY_DSN=""                             # optional, error tracking
export OPENAI_API_KEY=""                          # optional — AI-graded features (llm.py) and
                                                   # DALL-E story images (services/story_image_service.py)
                                                   # fall back to a heuristic grader / pollinations.ai
                                                   # keyless image API respectively when unset
export ELEVENLABS_VOICE_EN="21m00Tcm4TlvDq8ikWAM"  # optional, TTS voice id, has a default
export MENTO_DATA_DIR=""                          # optional, overrides where JSON data files live (defaults to backend/data)
```

### Verified proof (real commands, real output)

```bash
$ curl -s http://localhost:5001/health
{"games": 243, "service": "mentoapp-backend", "status": "ok"}

$ curl -s -X POST http://localhost:5001/api/auth/register \
    -H 'Content-Type: application/json' \
    -d '{"username":"proofuser","password":"testpass123","role":"student"}'
# -> 201, {"user": {...}, "token": "eyJ..."}

$ curl -s -X POST http://localhost:5001/api/run/start \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d '{"game_id":"dealcraft"}'
# -> 200, {"run_id": "...", "game_data": {"rounds": [...7 rounds...]}, ...}

$ curl -s -X POST http://localhost:5001/api/run/$RUN_ID/dealcraft/choose \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
    -d '{"round_id":"round_1","choice_id":"map_interests"}'
# -> 200, {"success": true, "state": {...}}
# (repeated for all 7 rounds)

$ curl -s -X POST http://localhost:5001/api/run/$RUN_ID/complete \
    -H "Authorization: Bearer $TOKEN"
# -> 200, {"success": true, "summary": {"score": 88.66, "band": "A", "label": "Strategic negotiator", ...}}
```

The same sequence works for `mumbai_manufacturer` (`/choose` + an
auto-scheduled crisis-event `event_choice_id` on some rounds) and
`heliogrid` (`/quarter` with a multi-lever `action` body) — see
`backend/routes/grader_routes.py`.

### Tests

```bash
cd backend  # or repo root; conftest.py handles both
python3 -m pytest tests/ -q
# 835 passed, 3 skipped, 0 failed
```

## Frontend

### Install + boot

```bash
cd frontend-react
npm ci
npm run dev
# -> http://localhost:5173 (real 200, not a 404 — index.html/vite.config.js/
#    main.jsx/App.jsx are all committed now)
```

`vite.config.js` proxies `/api/*` to `http://localhost:5001` in dev, matching
the relative-path convention every `src/api/*.js` client already uses (see
`src/api/client.js`) — run the backend first, or requests from the UI will
fail against nothing.

### What's actually wired up

- **Login/register** (`src/pages/LoginPage.jsx`) — real calls to
  `POST /api/auth/login` / `/register`, JWT stored and attached as
  `Authorization: Bearer <token>` on every subsequent request
  (`src/contexts/AuthContext.jsx`, `src/api/client.js`).
- **Games catalog** (`src/pages/GamesCatalogPage.jsx`) — real
  `GET /api/games` listing.
- **Playing a pilot game** (`src/pages/PilotGamePlayPage.jsx`, route
  `/play/:gameId`) — starts a run and plays it through to completion for
  `dealcraft`, `mumbai_manufacturer`, and `heliogrid` via
  `routes/grader_routes.py`'s dedicated endpoints.

**Known gap, left deliberately unfixed:** the pre-existing
`src/pages/GamePlayPage.jsx` (the legacy generic-engine play screen most
non-pilot games would use) depends on roughly 50 further
components/contexts/API clients that were never committed either
(`GameContext`, `ThemeContext`, and a long tail under
`components/game/*` and `components/features/*`) — a much larger gap
than this pass's bootstrap-files scope. It is not wired into `App.jsx`;
navigating `/play/<a non-pilot game id>` shows an honest "not wired into
the rebuilt UI yet" message instead of a blank page or a crash.

### Tests

```bash
cd frontend-react
npm run test -- --run
# Test Files  1 failed | 28 passed (29)
# Tests  130 passed (130)
```

The one failing suite (`src/tests/aspirational/StockMarketGame.test.jsx`
— its own directory name signals this) fails to resolve
`components/game/onboarding/OnboardingFlow.jsx`, a component that was
never committed. Pre-existing and unrelated to this restoration; the
130 actual test cases across the other 28 files all pass.

```bash
npm run build   # vite build — succeeds (one non-fatal "chunk larger than
                # 500kB" warning, not an error)
```
