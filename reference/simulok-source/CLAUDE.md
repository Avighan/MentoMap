# Simulok — repo guide for Claude Code and other AI assistants

Read this before changing anything. This repository holds **two separate
products** that happen to share a folder:

| | What it is | Lives in |
|---|---|---|
| **The prototype** | The single-file playable simulation app that sales double-clicks | `index.html` + `assets/` (repo root) |
| **The website** | The public marketing site at **https://simulok.in** | `website/` |

They have different audiences and different rules. Do not mix a change to one
into a commit for the other unless the change genuinely spans both.

---

## Golden rule: the repo is the only way to change the live site

**https://simulok.in is served from this repository. There is no server to log
into, no CMS, no file to edit "on the site".** The only path from an idea to
the live page is:

```
edit files in this repo
      ↓
commit on a branch
      ↓
open a PR into main   (or push to main directly if that is what the human asked for)
      ↓
merge to main
      ↓
.github/workflows/pages.yml runs tools/build-site.sh and deploys to GitHub Pages
      ↓
live at https://simulok.in within ~1 minute
```

This applies to **every** assistant and every tool — Claude Code, Cursor,
ChatGPT, a human with an editor. If someone asks you to "change the website",
that means changing files under `website/` and getting them onto `main`. Never
suggest editing anything outside the repo, and never describe the site as
updatable any other way.

`main` is the live site. Treat a merge to `main` as a publish.

### After you change the website

1. Run `./tools/build-site.sh` and confirm it succeeds.
2. Preview: `cd _site && python3 -m http.server 8000` → <http://localhost:8000>.
3. Commit, push, open a PR. When it merges, check the Actions run went green.

`_site/` is build output and is gitignored. Never commit it.

---

## What the build produces

`tools/build-site.sh` assembles `_site/`:

| Published URL | Comes from |
|---|---|
| `https://simulok.in/` | `website/` (minus its README) |
| `https://simulok.in/platform/` | the root `index.html` + `assets/`, copied verbatim |

`/platform/` exists so the **team** can open a URL and always get whatever is
on `main`, instead of pulling the repo or re-zipping `index.html` + `assets/`
by hand. **It carries no site-visitor use case and must never be linked from
the marketing site** — no nav item, no CTA, no page copy pointing at it. The
site's own call to action stays "Book a live demo," a guided session with the
team; visitors browsing `simulok.in` must never be able to reach the
simulations on their own.

`/platform/` is unlisted, not access-controlled: anyone holding the exact URL
can open it. Keep the link inside the team rather than pasting it anywhere
public (a deck, a public doc, social). If that stops being enough, ask before
adding a gate — do not add one unprompted.

`index.html` is copied, never edited by the build — the file on `main` stays
the single source of truth that also runs standalone (double-click, or the
`index.html` + `assets/` zip).

**Do not delete `website/CNAME`.** It contains `simulok.in` and is what keeps
the custom domain attached on every deploy. Removing it drops the site back to
a `github.io` URL.

---

## Website copy rules

These are deliberate. Keep new copy on the same line.

1. **It is "the platform", never "the demo build" or "the prototype".** The
   site sells the product; a visitor should never learn they are looking at
   this repo's build. "Book a live demo" is the primary call to action and
   means a guided session with the team — not a self-serve walkthrough. Never
   add a link, or publish a URL, that drops a visitor into the simulations
   unaccompanied.
2. **The simulation library is a *sample*, never a fixed catalogue.** No totals
   are rendered anywhere — no "29 simulations", no "N of N" counter. Every
   filtered view ends with a "Your simulation next" card. Adding titles to
   `website/assets/js/catalog.js` must not require a copy change.
3. **No inbox address is published and there is no direct-mail fallback.** The
   contact form is the only route in. Do not add a `mailto:` link.
4. Keep the deck's voice: short declaratives, consequence over adjectives.

`website/assets/js/catalog.js` mirrors `CATALOG_SIMS` in the prototype. When a
simulation is added to `index.html`, add the matching entry there too.

---

## Where contact-form enquiries go

The contact form is the only route in — the site publishes no inbox address and
offers no direct-mail fallback. `website/assets/js/contact.js` supports two
relays; `PROVIDER` at the top picks one and nothing else changes.

| Provider | What it is |
|---|---|
| `formsubmit` | https://formsubmit.co — no account, relays to the address in the endpoint. Kept as a fallback; its address was never activated. |
| `appsscript` | A Google Apps Script web app we own (`tools/contact-form.gs`) — logs every enquiry to a shared Google Sheet and emails it on. **Currently active.** |

Redeploying the script from the Apps Script editor must reuse the existing
deployment (Manage deployments → edit → New version), or the `/exec` URL
changes and `endpoint` has to be updated to match.

Two things that must survive any change of relay:

1. **Delivery is judged on the response body, not the status code.** Both
   relays can answer `200` while refusing the submission — FormSubmit does it
   before its address is activated. A `res.ok` check alone shows the visitor a
   confirmation for an enquiry that was never delivered, which loses the lead
   silently. A misconfigured provider must show the error state too, never a
   confirmation.
2. **Apps Script posts `text/plain`, not `application/json`.** Apps Script web
   apps cannot answer a CORS preflight, and a JSON content type triggers one.
   Posting the same JSON string as `text/plain` is a simple request, so there
   is no preflight. The content type is per-provider for this reason.

FormSubmit's endpoint holds the destination address in clear text and is
therefore scrapeable; its hashed alias (`https://formsubmit.co/ajax/<hash>`,
issued after activation) hides it. Apps Script exposes no address at all.

---

## Editing the prototype

See **`EDITING_WITH_AI.md`** for architecture, sim IDs, engines vs
`SIM_LIBRARY`, size limits and IP rules, and **`TEAM_ONBOARDING.md`** for how
new simulations are built in a personal sandbox file before being merged into
the shared `index.html`.

**IP:** do not copy Harvard Business Publishing text, art, role names or
scenario labels. MacroEcon: The Kalyana Mandate is original work.

---

## More detail

- `website/README.md` — the website's structure, design tokens, form wiring,
  and the DNS records behind the custom domain.
- `README.md` — repo map and how sales runs the prototype.
