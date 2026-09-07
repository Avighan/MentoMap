# Simulok.ai — public website

The marketing site for Simulok.ai. Plain HTML, CSS and vanilla JS — no build
step, no framework, no dependencies. Everything in this folder is published as
the root of the GitHub Pages site.

```
website/
  index.html            one-page site: problem → scale → solution → formats →
                        measurement → benefits → showcase → library → team → CTA
  contact.html          "Get in touch" form page
  assets/
    css/site.css        the whole design system (tokens at the top)
    js/site.js          nav, reveals, count-ups, tabs, the live decision widget,
                        the skill-map radar, the cohort heat map, library filters
    js/contact.js       form validation + delivery (see "Making the form live")
    js/catalog.js       the simulations shown in the library section
    img/                showcase images (copied from ../assets/sim/)
    favicon.svg
```

## Looking at it locally

Open `website/index.html` in Chrome or Edge — the whole site works from the
file system. Public pages must not link to the walkthrough build; faculty
reach a live run through a booked session.

To see it exactly as it will be published:

```bash
./tools/build-site.sh          # writes _site/
cd _site && python3 -m http.server 8000
```

Then open <http://localhost:8000> — and <http://localhost:8000/platform/> for
the team-only prototype link (see below).

## How it gets published

`.github/workflows/pages.yml` runs `tools/build-site.sh` on every push to
`main` and deploys the result to GitHub Pages. The build assembles:

| Published path | Comes from |
|---|---|
| `/` | `website/` |
| `/platform/` | the root `index.html` + `assets/`, copied verbatim |

`/platform/` is for the **team only**, not for site visitors: nothing on
`simulok.in` links to it, so it never shows up while browsing the marketing
site. It exists so the team always has a URL to the exact build on `main`,
without pulling the repo or re-zipping `index.html` + `assets/` each time
something changes. It is unlisted, not access-controlled — anyone holding the
exact URL can open it, so keep the link inside the team rather than posting it
anywhere public. The marketing site's own call to action stays "Book a live
demo," a guided session with the team.

**Language:** to a visitor this is *the platform*, never "the demo" or "the
prototype" — the site sells the product, not this repo's build. The one
exception is "Live demo" as a next step on the contact form, which means a
guided session with the team. Keep new copy on that line.

**One-time setup:** repo → *Settings* → *Pages* → *Source: GitHub Actions*.
The repo is private and Pages is served from a paid GitHub plan, so the source
stays private while the published site is public.

## The custom domain

The site is served from **https://simulok.in**, registered at GoDaddy. Two
things hold that together — both must stay in place:

1. **`website/CNAME`** in this repo, containing the single line `simulok.in`.
   `tools/build-site.sh` copies the whole `website/` folder, so it lands in
   every deploy and keeps the domain attached. **Do not delete it** — without
   it the site falls back to a `github.io` URL on the next publish.
2. **DNS at GoDaddy** (Domain → DNS → DNS Records) pointing the apex at
   GitHub Pages:

   | Type | Name | Value | TTL |
   |---|---|---|---|
   | A | `@` | `185.199.108.153` | 600 |
   | A | `@` | `185.199.109.153` | 600 |
   | A | `@` | `185.199.110.153` | 600 |
   | A | `@` | `185.199.111.153` | 600 |
   | CNAME | `www` | `sumeetonline90.github.io.` | 1 hour |

   The GoDaddy default `A @ → Parked` must be replaced, and the default
   `CNAME www → simulok.in.` must be repointed as above. Leave the `NS`, `SOA`,
   `_domainconnect` and `_dmarc` records alone. Check the **Forwarding** tab is
   empty — a forwarding rule overrides these records.

   Optional IPv6, same `@` name: `2606:50c0:8000::153`, `8001::153`,
   `8002::153`, `8003::153` as `AAAA` records.

Then in *Settings* → *Pages*, set **Custom domain** to `simulok.in`, wait for
the DNS check to pass, and tick **Enforce HTTPS** once GitHub has issued the
certificate (usually a few minutes, occasionally up to an hour).

### If the domain ever changes

Three edits, one commit: the hostname in `website/CNAME`, the
`<link rel="canonical">` and `og:url` tags in `website/index.html` and
`website/contact.html`, and the DNS records above. Everything else on the page
is a relative path and needs no change.

### Note on `ivldsp.me`

A custom domain set on a *user site* (`sumeetonline90/sumeetonline90.github.io`)
is inherited by every project site on the account, which is why this site
briefly served from `ivldsp.me/simulok/`. A project site with its own `CNAME`
overrides that inheritance, so `website/CNAME` settles it for this repo
regardless of what the user site does.

## Where contact-form enquiries go

`PROVIDER` at the top of `assets/js/contact.js` selects the relay. Switching is
a one-line change; everything else — payload, validation, success copy — is
shared.

### `formsubmit` — fallback, not active

Relays to `sumeetonline90@gmail.com` via https://formsubmit.co. No account.
Needs a one-time activation click on an email FormSubmit sends to that address;
until then it answers `200` with `{"success":"false"}` and the form correctly
shows an error rather than a confirmation.

The endpoint contains the destination address in clear text, so it is visible
in the deployed JS and scrapeable. FormSubmit's hashed alias
(`https://formsubmit.co/ajax/<hash>`) is a drop-in replacement that hides it.

### `appsscript` — active

A Google Apps Script web app we own — see **`tools/contact-form.gs`**, whose
header carries the full deploy steps. It:

- appends every enquiry to a **Google Sheet**, which is the shared record the
  team works from — share the Sheet, not the script, and teammates need no
  access to this repo or the website;
- emails the enquiry to `NOTIFY` with the sender set as `Reply-To`, so replying
  goes straight to the prospect;
- exposes no address in the website's source, and puts no third party in the
  path.

Editing the script means redeploying it from the Apps Script editor —
**Deploy → Manage deployments → edit the existing one → Version: New version**.
Creating a *new* deployment instead issues a different `/exec` URL, and
`endpoint` in `contact.js` must then be updated to match or enquiries stop
arriving.

### Two invariants

1. **Delivery is judged on the response body, not the status code.** Both
   relays can answer `200` while refusing the submission. Checking only
   `res.ok` shows a confirmation for an enquiry that was never delivered.
2. **Apps Script posts `text/plain`.** It cannot answer a CORS preflight, and
   `application/json` triggers one. The same JSON string sent as `text/plain`
   is a simple request, so no preflight happens.

Fields sent: `intent`, `name`, `email`, `organisation`, `role`, `segment`,
`cohort_size`, `message`, `consent`, `page`, `submitted_at`. The honeypot
(`company_website`) is stripped before sending.

## Editing content

- **Copy** lives directly in `index.html` — it tracks the Simulok.ai deck
  section for section, so keep the two in step when the deck changes.
- **Simulation library**: `assets/js/catalog.js` mirrors `CATALOG_SIMS` in the
  demo prototype. When a simulation is added to the prototype, add the same
  `id / seg / title / desc / meta` entry here. The section is deliberately
  framed as a *sample* of a growing library — no totals are shown anywhere, and
  every filtered view ends with a "your simulation next" card. Keep it that way
  when adding titles.
- **Colours, type, spacing**: the `:root` block at the top of `site.css`. The
  palette is the deck's — navy canvas, teal signal.
- **Showcase images**: drop a JPG into `assets/img/` and point a `.shot` at it.

## Deliberate constraints

- No framework and no bundler, so anyone on the team can edit a file and push.
- No analytics or third-party scripts; the only external request is Google
  Fonts.
- `prefers-reduced-motion` is respected — every animation collapses.
- Tested down to 390 px wide.
