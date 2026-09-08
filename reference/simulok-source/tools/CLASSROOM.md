# Classroom Sheet recorder — setup

Same-day confidence layer for Mumbai Manufacturer, both Zara titles, and Zenith Appliances. Demo User still works with no Sheet.

**Owner master guide (all roles, links, ops):** [`../classroom/guide/owner/index.html`](../classroom/guide/owner/index.html) — published at `/platform/classroom/guide/owner/` after Pages deploy. Bookmark for yourself; do not share with students.

**Faculty / student how-to (with screenshots):** instructor → [`../classroom/guide/instructor/`](../classroom/guide/instructor/); student → [`../classroom/guide/student/`](../classroom/guide/student/). The hub at `/platform/classroom/guide/` intentionally does not list guides.

## 1. Create the Sheet (you)

1. Create a Google Spreadsheet named **Simulok Classroom**.
2. Rename the first tab to **Roster**.
3. Paste the contents of [`classroom-roster-sample.csv`](classroom-roster-sample.csv) into Roster (File → Import, or copy-paste). Keep the header row.
4. Add an empty tab named **Sessions** (or let the script create it on first open).

Default codes in the sample:

| ID | Password | Role |
|---|---|---|
| `FACULTY` | `faculty-demo` | instructor |
| `MBA01`…`MBA60` | see CSV | student |

Change passwords before a real class.

## 2. Deploy Apps Script (you)

1. In the Sheet: **Extensions → Apps Script**.
2. Delete the stub. Paste [`classroom-session.gs`](classroom-session.gs). Save.
3. **Deploy → New deployment → Web app**
   - Execute as: **Me**
   - Who has access: **Anyone**
4. Authorise (unverified app warning — continue; it is your script).
5. Copy the `/exec` URL.

Redeploy later: Manage deployments → edit existing → Version: **New version** (keep the same URL).

## 3. Wire the prototype (repo)

1. Open [`../assets/js/classroom.js`](../assets/js/classroom.js).
2. Set `ENDPOINT` to the `/exec` URL.
3. Reload `index.html` (or `/platform/` after deploy).

Do **not** put the `/exec` URL on the marketing site or in a public deck.

## 4. Run a sitting

1. Instructor tab → sign in as `FACULTY` / `faculty-demo`.
2. **Open session** → pick Mumbai / Zara / Zara-new / Zenith.
3. Click **Live dashboard** (full-screen page) — or stay on the Instructor Console: **Live class scores** refreshes every few seconds.
4. Students open the unlisted platform URL → Participant → enter **Student ID**, **Your name**, and password.
5. Click any student score (console or dashboard) for the report card and round-by-round KPIs.
6. Faculty may **refresh** without signing in again (login in `localStorage` until Sign out).
7. Past sittings: session dropdown on the Instructor Console or dashboard.
8. **Reset runs** on a selected sitting clears that tab’s logs so every student may complete once again. Or Close → Open for a new `Sess_*` (keeps old history).
9. Each student may complete **once** per session until reset or a new sitting.
10. Next cohort without wiping history: **Close session**, then **Open session** → `Sess_A2`.

**Links (share carefully)**

- Platform (students + faculty): https://simulok.in/platform/
- Student guide (students only): https://simulok.in/platform/classroom/guide/student/
- Instructor guide (faculty only — do not send to students): https://simulok.in/platform/classroom/guide/instructor/
- Dashboard preview (faculty): https://simulok.in/platform/classroom/dashboard.html?demo=1

Sheet / Apps Script / roster setup stays in this file for the ops team. It is not published on the classroom guide pages.

Zenith opens under `cost-accounting/zenith-appliances.html` (also at `/platform/cost-accounting/` after Pages deploy).

**Important:** after editing `classroom-session.gs`, redeploy: Manage deployments → edit → **New version** (keep the same `/exec` URL).
