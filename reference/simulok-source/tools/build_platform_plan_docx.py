# -*- coding: utf-8 -*-
"""Generate Simulok platform development plan as a Word document."""
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Cm, Inches, Pt, RGBColor

NAVY = RGBColor(0x0A, 0x25, 0x40)
TEAL = RGBColor(0x0D, 0x7A, 0x6B)
MUTED = RGBColor(0x4A, 0x5C, 0x6A)
BLACK = RGBColor(0x1A, 0x1A, 0x1A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEADER_BG = "0A2540"
ROW_ALT = "F4F8F7"
HEADER_TEAL = "0D7A6B"

OUT = Path(__file__).resolve().parents[1] / "Simulok-Platform-Development-Plan.docx"


def set_run(run, *, size=11, bold=False, color=BLACK, font="Calibri"):
    run.font.name = font
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = color


def add_para(doc, text, *, size=11, bold=False, color=BLACK, space_after=8, space_before=0, align=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.line_spacing = 1.15
    if align:
        p.alignment = align
    run = p.add_run(text)
    set_run(run, size=size, bold=bold, color=color)
    return p


def shade_cell(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def set_cell_border(cell):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "C5D0D5")
        tcBorders.append(el)
    tcPr.append(tcBorders)


def fill_cell(cell, text, *, bold=False, color=BLACK, size=10, fill=None, center=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    set_run(run, size=size, bold=bold, color=color)
    set_cell_border(cell)
    if fill:
        shade_cell(cell, fill)


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for i, h in enumerate(headers):
        fill_cell(table.rows[0].cells[i], h, bold=True, color=WHITE, size=10, fill=HEADER_BG)
    for r_i, row in enumerate(rows):
        bg = ROW_ALT if r_i % 2 else "FFFFFF"
        for c_i, val in enumerate(row):
            fill_cell(table.rows[r_i + 1].cells[c_i], val, size=10, fill=bg)
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    return table


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = NAVY if level == 1 else TEAL
        run.font.name = "Calibri"
    p.paragraph_format.space_before = Pt(16 if level == 1 else 12)
    p.paragraph_format.space_after = Pt(8)
    return p


def bullet(doc, text, *, bold_prefix=None):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    if bold_prefix:
        r = p.add_run(bold_prefix)
        set_run(r, bold=True, size=11)
        r2 = p.add_run(text)
        set_run(r2, size=11)
    else:
        r = p.add_run(text)
        set_run(r, size=11)
    return p


def build():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)

    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = fp.add_run("Simulok.ai  ·  Confidential  ·  Platform development plan  ·  Cursor Start (India)")
    set_run(r, size=8, color=MUTED)

    # Title
    add_para(doc, "SIMULOK.AI", size=12, bold=True, color=TEAL, space_after=2, align=WD_ALIGN_PARAGRAPH.LEFT)
    add_para(
        doc,
        "Browser portal — development plan, timeline and costs",
        size=26,
        bold=True,
        color=NAVY,
        space_after=6,
    )
    add_para(
        doc,
        "Phase 1: go to market with 6 MBA simulations  ·  then keep adding  ·  Cursor Start (India)  ·  AWS, minimum cost",
        size=12,
        color=MUTED,
        space_after=4,
    )
    add_para(
        doc,
        f"Prepared {date.today().strftime('%d %B %Y')}  |  Audience: founders and delivery  |  Domain: simulok.in",
        size=10,
        color=MUTED,
        space_after=14,
    )

    add_para(
        doc,
        "This note is a delivery plan, not a vendor quote. Rupee figures use India engineering rates. Dollar figures are AWS list-price bands in ap-south-1 (Mumbai). Cursor seats are Cursor Start (India): ₹649 per month per person, tax-inclusive. Actual invoices will vary with usage, concurrent classrooms, and who does the work.",
        size=11,
        space_after=12,
    )

    heading(doc, "1. What we are developing", 1)
    add_para(
        doc,
        "Simulok.ai is building a browser-based learning portal — not another marketing page and not a zip file. Professors, students and college admins sign in with credentials, see only what their institution is entitled to, play simulations, and keep a record of judgement (attempts, scores, debriefs). The public site at simulok.in continues to sell the idea. The product lives at app.simulok.in.",
        size=11,
    )
    add_para(
        doc,
        "Today the playable library is a single-file prototype: strong pedagogy, no real accounts, no persistence, no college tenancy. Phase 1 replaces that shell with a multi-tenant application and goes to market with 6 simulations — one of each format, chosen for MBA classrooms (operations, strategy, negotiations, marketing). The rest of the library is not a launch blocker. After the first college is live, adding a title is mounting a new script onto the same shell. That is how we start earning without waiting to finish every pack.",
        size=11,
    )
    add_para(doc, "What the portal must do on day one", size=12, bold=True, color=NAVY, space_after=6)
    bullet(doc, "Student: log in, see assigned simulations, play, finish, view personal history and feedback.")
    bullet(doc, "Professor / faculty: import a roster, create a cohort, assign a sim (with dates), watch who has started / finished, export scores, run a multiplayer session (join codes, timers, force-advance).")
    bullet(doc, "Institution admin: create the college, entitle which simulations that college may use, manage users.")
    bullet(doc, "Simulok operator: publish a new simulation pack and enable it per college without redeploying the whole app.")
    add_para(doc, "What we are explicitly not building in Phase 1", size=12, bold=True, color=NAVY, space_after=6)
    bullet(doc, "Mobile apps, LTI/SCORM, payments, AI tutor, unique UI per simulation, or inventing new engine maths (that is in the script).")

    heading(doc, "2. Team size, roles, and how we work", 1)
    add_para(
        doc,
        "Core delivery team is three people, all in India, all on Cursor Start. Two write production code. The third owns product, scripts and the pilot classroom. That is enough for Phase 1 if scripts and the shared UI stay as assumed.",
        size=11,
    )
    add_table(
        doc,
        ["Seat", "Role", "Accountability", "Cursor Start"],
        [
            ["1", "Developer — platform", "Auth, tenancy, faculty/admin consoles, AWS, CI/CD, security reviews", "Yes — ₹649/mo"],
            ["2", "Developer — simulations", "Pack schema, mount the 6 launch titles, shared round/results UI, multiplayer + universe-lite, then a steady add-a-sim cadence", "Yes — ₹649/mo"],
            ["3", "Founder / domain lead", "Freeze the 6-title MBA mix, script quality, Friday demo, Week-9 live class, first paying college", "Yes — ₹649/mo (Plan mode, review, pack QA)"],
        ],
    )
    add_para(
        doc,
        "How the two developers split work: they do not both sit on the same file. Platform developer unblocks login and faculty every week. Simulations developer unblocks packs. Friday: 30-minute demo of something a professor could click, not a slide.",
        size=11,
    )
    bullet(doc, "No separate UI designer or QA hire in Phase 1. Shared shell + Cursor-generated tests + founder playtest against the script.")
    bullet(doc, "No agency. Cursor Start is the acceleration layer, not a substitute for the Week-9 live class.")
    bullet(doc, "After go-live, the simulations developer’s main job is adding titles. Platform stays on tenancy, sessions, and the first college.")

    heading(doc, "3. Cursor Start (India) — how it changes the plan", 1)
    add_para(
        doc,
        "Every seat uses Cursor Start, the India plan at ₹649 per month tax-inclusive (UPI or Indian cards; Indian phone verification). It includes agentic coding (Agent, Plan, Ask), Cursor models (Grok 4.6 / 4.5, Composer 2.5), Cloud Agents, and a larger usage pool than the free Hobby plan. It is not Cursor Pro: third-party frontier models and on-demand spend past the pool are out of scope. If a seat exhausts the monthly pool, that person switches to Composer for mechanical pack work or we pause non-critical agents until the next cycle — we do not assume Pro upgrades in this budget.",
        size=11,
    )
    add_para(doc, "What Cursor Start is used for (every week)", size=12, bold=True, color=NAVY, space_after=6)
    bullet(doc, "Plan mode: break a script into a pack checklist before any code.")
    bullet(doc, "Agent mode: generate CDK, API handlers, pack JSON from a script, golden tests, faculty CSV import.")
    bullet(doc, "Cloud Agents: overnight PRs for mechanical MCQ extraction while the human reviews scoring.")
    bullet(doc, "Founder: Ask/Plan on a pack diff — “does this match section 4 of the script?” — without writing production code.")
    add_para(doc, "What AI does not shorten", size=12, bold=True, color=NAVY, space_after=6)
    bullet(doc, "A real classroom (late joiners, Wi-Fi, the bell). That week stays on the calendar.")
    bullet(doc, "Multiplayer session lifecycle (timers, rejoin, force-advance). Cursor writes the first draft; humans debug live.")
    bullet(doc, "DNS/TLS waits, college timetables, and founder sign-off against the script.")

    heading(doc, "4. Working assumptions (locked)", 1)
    bullet(doc, "The simulation script is ready before engineering starts on that title (narrative, rounds, options, effects, KPIs, scoring, debrief).")
    bullet(doc, "Formulas, scoring and engine maths are in the script. Developers implement and wire them; they do not invent pedagogy or models.")
    bullet(doc, "UI follows the existing Simulok shell. No per-simulation custom interface.")
    bullet(doc, "All three seats on Cursor Start (India) for the whole build. No Cursor Pro in the budget.")
    bullet(doc, "v1 is browser-only. Three product roles: student, professor/faculty, institution admin.")
    bullet(doc, "Marketing site (simulok.in) stays separate. Portal host: app.simulok.in.")
    bullet(doc, "Phase 1 is 6 titles in market, not a finished catalogue. Remaining scripts ship after the first college is live.")
    bullet(doc, "The current prototype remains the offline sales pack for titles not yet on the portal. After week 3, new live titles are packs, not growth of index.html.")

    heading(doc, "5. Go-to-market mix — 6 simulations, then keep adding", 1)
    add_para(
        doc,
        "Do not wait for a 15-title catalogue before the first college can pay. Phase 1 ships 6 titles that prove every format a professor will ask for, mapped to MBA courses we can sell this semester. Day-1 revenue comes from those six. The next titles (HelioGrid, DashMart, MacroEcon, Lemonade, school MCQs, a second multiplayer, …) are a post-launch cadence, not a launch gate.",
        size=11,
    )
    add_para(doc, "The six (founder may swap a title; do not drop a format)", size=12, bold=True, color=NAVY, space_after=6)
    add_table(
        doc,
        ["#", "Title", "Format", "MBA course it sells into"],
        [
            ["1", "Dealcraft", "Scenario / MCQ", "Negotiations"],
            ["2", "Brand Wars", "Scenario / MCQ", "Marketing"],
            ["3", "The Mumbai Manufacturer", "1-player engine", "Operations Management"],
            ["4", "Zara — The Fast-Fashion Reckoning", "1-player engine", "Strategic Innovation / Strategy"],
            ["5", "K2 — The Savage Mountain", "Multiplayer / hot-seat", "Leadership & teams (networked + keep single-device hot-seat)"],
            ["6", "Universe-lite (shared market)", "Universe-lite", "Competitive strategy — N teams, one market, facilitator controls"],
        ],
    )
    add_para(
        doc,
        "That is 2 MCQ + 2 one-player + 1 multiplayer + 1 universe = 6. Four MBA topics on the table (negotiations, marketing, operations, strategy) plus leadership and a competitive-market slot. If the founder prefers HelioGrid (STP / marketing) instead of Brand Wars, swap — keep one of each format.",
        size=11,
    )
    add_para(doc, "If the calendar slips", size=12, bold=True, color=NAVY, space_after=6)
    bullet(doc, "Cut first: universe-lite (launch 5: still one MCQ, one 1-player, one multiplayer).")
    bullet(doc, "Cut second: the second MCQ (Brand Wars). Keep Dealcraft.")
    bullet(doc, "Do not cut: K2 session lifecycle, tenancy, or the live classroom pilot.")
    add_para(
        doc,
        "After go-live, a new MCQ is about 1 day and a new 1-player about 2–3 days (script in hand, Cursor Start, shared UI). That is how the catalogue grows while invoices are already going out.",
        size=11,
        bold=True,
    )

    heading(doc, "6. Week-wise development plan and timeline", 1)
    add_para(
        doc,
        "A 15-title Phase 1 with Cursor Start was 13 weeks. Going to market with 6 titles does not remove multiplayer or the live class, so this is not an 8-week plan. What it does remove is four extra MCQ packs and four extra 1-player ports. Recommended clock: 11 weeks from Week 1 to launch. Kickoff (Week 0) is 3–5 days before that. Quote 13 weeks only as the multiplayer slip buffer. An aggressive 10-week path exists if load-test shares the last week with launch hardening.",
        size=11,
    )

    heading(doc, "6.1 Why 11 weeks (and where it cannot go lower)", 2)
    add_table(
        doc,
        ["Work", "15-title / 13-week plan", "6-title GTM / 11-week plan", "Why"],
        [
            ["MCQ packs", "6 titles, 1 week", "2 titles, inside the faculty week", "Faculty console is the work. Two MCQs are a Cursor overnight, not a second week."],
            ["1-player engines + profiles", "6 engines (2 weeks) + 1 week profiles", "2 engines + profiles in 1 week (Week 4)", "Mumbai + Zara only. Shared UI still built once. Platform does profiles in parallel."],
            ["Faculty console", "Week 3", "Week 3 (unchanged)", "CSV, cohorts, entitlements do not shrink with fewer titles."],
            ["Multiplayer", "3 weeks (2 titles)", "3 weeks (K2 only)", "Classroom lifecycle is not a typing problem. Second MP title moves post-launch."],
            ["Universe-lite", "1 week", "1 week (Week 8)", "Still the format proof. Cut it only if we accept a 5-title launch."],
            ["Live class", "1 week (untouchable)", "1 week, Week 9 (untouchable)", "Needs a real timetable. This is how we know we can charge."],
            ["Load + harden + launch", "2 weeks", "2 weeks (10 load, 11 launch)", "First college still needs a restore rehearsal."],
        ],
    )
    add_para(
        doc,
        "Commit to colleges: 11 weeks to a paying portal with 6 MBA titles. Do not quote 6 weeks: that is login + MCQ without classroom-safe multiplayer. The time we save vs a 15-title launch is spent in market, adding HelioGrid and the next title, not in a longer build.",
        size=11,
        bold=True,
    )

    heading(doc, "6.2 Summary Gantt (11 weeks)", 2)
    add_table(
        doc,
        ["Weeks", "Phase", "Exit criterion (done when…)"],
        [
            ["1–2", "Walking skeleton", "A professor and a student can log in, finish Dealcraft, and see a saved attempt."],
            ["3", "Faculty + 2nd MCQ", "CSV roster, assign, due dates; Dealcraft and Brand Wars playable."],
            ["4", "1-player + profiles", "Mumbai Manufacturer and Zara match their scripts; faculty can see who has not finished."],
            ["5–7", "Multiplayer", "K2 runs with join codes, timers, rejoin, professor force-advance."],
            ["8", "Universe-lite", "N teams share one market resolver; leaderboard; facilitator controls."],
            ["9", "Live class gate", "One real MBA class, 40–80 students, professor-led. Defects from that day are the backlog."],
            ["10", "Scale and safety", "Load test 200 real / 800 synthetic; backup restore rehearsed."],
            ["11", "Harden and launch", "Docs, 3 short faculty videos, first college entitled to the 6 titles on app.simulok.in."],
        ],
    )

    heading(doc, "6.3 How each role uses Cursor Start, week by week", 2)
    add_table(
        doc,
        ["Weeks", "Developer — platform (Cursor)", "Developer — simulations (Cursor)", "Founder (Cursor Plan / Ask)"],
        [
            ["1–2", "Agent: CDK, Cognito, tenancy filters, CI", "Agent: pack schema + Dealcraft from script", "Plan: walking-skeleton checklist; sign off login UX"],
            ["3", "Agent: CSV roster, assignments, entitlements", "Agent: Brand Wars pack + golden tests", "Ask: spot-check both MCQ scores vs script"],
            ["4", "Agent: profile/history APIs, faculty CSV, version pinning", "Agent: Mumbai + Zara engines; shared round UI once", "Play both 1-player titles against the script"],
            ["5–7", "Agent: WebSocket, session row locking, timers", "Agent: K2 pack roles; hot-seat fallback", "Run a 5-person K2 dry rehearsal"],
            ["8", "Agent: scheduled tick Lambda", "Agent: market resolver from script", "Two-team playtest"],
            ["9", "On-call, defect fixes", "On-call, scoring mismatches", "In the classroom; owns the defect list"],
            ["10–11", "Agent: load scripts, alarms, runbook", "Agent: freeze the 6 packs; start the post-launch backlog (HelioGrid first)", "Faculty videos; go-live; first invoice conversation"],
        ],
    )

    heading(doc, "6.4 Week-by-week detail (11-week clock)", 2)

    weeks = [
        (
            "Week 0 — Kickoff (3–5 days before the 11-week clock)",
            [
                "Create AWS Organization accounts: dev and prod. MFA on root and IAM. Budget alerts at USD 50 and USD 200.",
                "Subscribe all three seats to Cursor Start (India), ₹649/month each, UPI mandate. Verify Indian phone numbers.",
                "Create the monorepo: apps/web, apps/api, packages/engine-sdk, packs/. Marketing site stays in the existing repo.",
                "Founder uses Cursor Plan to lock the pack contract (manifest.json, content.json, optional engine.js) with the two developers in the same session.",
                "Freeze the six launch titles (Dealcraft, Brand Wars, Mumbai Manufacturer, Zara, K2, universe-lite). Everything else is the post-launch backlog — HelioGrid first.",
                "Freeze the prototype as v0 for sales of titles not yet on the portal. After week 3, no new live title is added only inside index.html.",
                "Point app.simulok.in DNS and start the ACM certificate. Do this early; DNS waits are idle time later.",
                "Book the Week-9 pilot class with a named MBA professor and date (ops, strategy, negotiations or marketing — match the six).",
            ],
            "Kickoff complete when: AWS budgets live, three Cursor Start seats active, empty portal deploys to dev, pack schema merged, six-title list frozen, pilot date on a calendar.",
        ),
        (
            "Weeks 1–2 — Walking skeleton",
            [
                "CDK: S3 + CloudFront (SPA), HTTP API + one Lambda, RDS Postgres db.t4g.micro (single-AZ), Cognito user pool.",
                "Roles: student, faculty, admin. Institution (college) as tenant. Every data row carries institution_id.",
                "Login page (your UI, Cognito behind it). Users mirrored in Postgres by cognito_sub.",
                "Catalog reads the simulation registry. Entitlements table: which college may see which sim.",
                "Dealcraft pack extracted from the script. Student plays end-to-end. Attempt saved.",
                "CI: GitHub Actions → deploy to dev on merge. No production secrets in the repo.",
            ],
            "Done when: two browsers, two roles, Dealcraft, one saved score in Postgres.",
        ),
        (
            "Week 3 — Faculty console and Brand Wars",
            [
                "Faculty: create cohort, CSV import roster, assign a simulation version, open/due times. Agent generates the CRUD; human reviews institution_id on every query.",
                "Admin: create institution, toggle entitlements per simulation (the “enable access” step after a pack is published).",
                "Content pipeline: validate:pack, local preview, CI publish pack to S3. Assignment pins sim_version_id so a later v2 cannot change a live class.",
                "Brand Wars pack from the script. Two MBA MCQs live: negotiations and marketing.",
                "Student can only see assigned sims, not the post-launch backlog.",
            ],
            "Done when: a faculty member can onboard a 40-person cohort without engineering help, and Dealcraft + Brand Wars are playable.",
        ),
        (
            "Week 4 — Two 1-player engines + profiles (script-driven, shared UI)",
            [
                "Shared round UI once: briefing, round narrative, choices, KPI bar, results/debrief. Same chrome as the prototype; Cursor scaffolds from the existing HTML.",
                "Mumbai Manufacturer (operations) and Zara (strategic innovation): Agent implements state, applyAction / resolveRound, and score 1:1 with each script.",
                "Golden tests: scripted paths must produce the script’s KPIs and grade. Founder playtests both titles.",
                "Server recomputes score (client can preview; server is authoritative).",
                "In parallel (platform): student profile, attempt history, faculty progress view, CSV export.",
            ],
            "Done when: both 1-player sims match their scripts, attempts persist, and a professor can answer “who has not finished Mumbai Manufacturer?” in under a minute.",
        ),
        (
            "Weeks 5–7 — Multiplayer (K2 only; not compressed)",
            [
                "Session lobby: faculty creates a session, join code, role assignment (or self-pick where the script allows). Cursor drafts the API; humans test with five laptops.",
                "WebSocket transport with HTTP polling fallback. Server holds session state in Postgres (not in Lambda memory).",
                "Round barrier: all roles submit (or timer fires with script default). Professor can force-advance when the bell is in six minutes.",
                "Rejoin after laptop close. Idempotent submit so double-click does not double-apply.",
                "K2: networked mode plus keep single-device hot-seat so a dead campus network does not cancel the class.",
                "A second multiplayer title is post-launch — reuse this lobby; do not build it in Phase 1.",
            ],
            "Done when: 5 people on 5 machines complete a K2 run, one disconnects and rejoins, professor force-resolves a round.",
        ),
        (
            "Week 8 — Universe-lite (script has the market; one playtest)",
            [
                "One shared market resolver as specified in the script. N teams, scheduled tick (Lambda), leaderboard. Agent implements the tick from the script’s tables.",
                "Facilitator: pause tick, inject a scripted shock if the script defines one, end the run.",
                "Deterministic seeded RNG and an append-only action log so “the market scored us wrong” can be replayed.",
                "Smallest honest universe. Do not expand to regulators/investors in Phase 1. If this week is at risk, launch the other five and add universe as the first post-launch pack after HelioGrid.",
            ],
            "Done when: two teams see each other’s market effect on the next tick, on the script’s rules.",
        ),
        (
            "Week 9 — Live class (non-negotiable; not shortened by Cursor)",
            [
                "One MBA course, 40–80 students, professor in the room. Use a 1-player title plus K2 or universe-lite if the timetable allows.",
                "On-call engineer. Defect log same day. Fix join, timer, Wi-Fi, and scoring mismatches against the script first. Cursor drafts the patches; humans deploy.",
                "If this week is skipped, you do not have a launch; you have a staging environment — and you are not yet earning.",
            ],
            "Done when: the professor would run it again next semester without an engineer in the room, and would consider paying.",
        ),
        (
            "Week 10 — Load, backup, timetable warm-up",
            [
                "Load test: 200 concurrent on a 1-player assignment; 800 synthetic peak. Cursor writes the k6/Artillery scripts; humans watch Postgres CPU.",
                "Schedule warm-up 20 minutes before a booked session (9:00 a.m. login spike). Drop provisioned concurrency after class.",
                "Automated snapshots, point-in-time recovery, restore rehearsal. No production maintenance during Indian college hours.",
                "CloudWatch alarms: 5xx, DB CPU, disk, Cognito errors. Log retention 14 days.",
            ],
            "Done when: restore from backup has been done once on purpose, and the load test report is in the repo.",
        ),
        (
            "Week 11 — Harden, launch, start the add-a-sim cadence",
            [
                "Accessibility pass on login, catalog, round, results. Faculty one-pager + three short videos (assign, run MP, read results).",
                "Production cutover on app.simulok.in. First college entitled to the six titles. WAF optional at first paying college.",
                "Launch checklist: 6 packs published, entitlements documented, support mailbox, runbook.",
                "Simulations developer starts HelioGrid (next 1-player, marketing / STP) the same week as go-live so the catalogue does not freeze the day invoices start.",
            ],
            "Done when: a new college can be created by admin, entitled to the six, a cohort can start without a code deploy, and HelioGrid is on the board as the next pack.",
        ),
    ]

    for title, items, done in weeks:
        heading(doc, title, 3)
        for it in items:
            bullet(doc, it)
        add_para(doc, done, size=11, bold=True, color=TEAL, space_before=4, space_after=10)

    heading(doc, "6.5 If the calendar slips", 2)
    bullet(doc, "Cut first: universe-lite (launch 5: still one of MCQ, 1-player, multiplayer).")
    bullet(doc, "Cut second: Brand Wars (keep Dealcraft).")
    bullet(doc, "Do not cut: Week-9 live class, K2 session lifecycle, tenancy, assignment version pinning, server-side scoring.")
    add_para(
        doc,
        "A login catalog of Dealcraft + Brand Wars + Mumbai + Zara can be in a professor’s hands around week 4. Classroom-safe K2 is why the recommended plan is 11 weeks, not 6. Quote 13 weeks only as the multiplayer slip buffer. Time not spent porting the other nine titles is spent in market.",
        size=11,
    )

    heading(doc, "7. Costs", 1)
    add_para(
        doc,
        "Two different bills. One-time is people (and a little AWS while you build). Recurring is AWS plus optional engineering to keep adding titles — that second bill is the point of going live at 6 titles instead of 15. Infra does not replace salaries after launch unless founders operate the library themselves.",
        size=11,
    )

    heading(doc, "7.1 One-time cost to launch Phase 1 (6 simulations, then add)", 2)
    add_para(doc, "People — 11 weeks (plus a short Week 0), India, all seats on Cursor Start", size=12, bold=True, color=NAVY, space_after=6)
    add_table(
        doc,
        ["Line item", "Lean (founder + 1 hire)", "Two hired mid/senior + founder", "Notes"],
        [
            ["Engineering (11 weeks)", "₹5.5 – 10 lakh", "₹11 – 19.5 lakh", "Fully loaded. Shorter than a 15-title / 13-week build because four MCQ and four 1-player ports moved post-launch."],
            ["Cursor Start (India), 3 seats × 3 months", "₹5,850", "₹5,850", "3 × ₹649 × 3 = ₹5,841. Tax-inclusive. Not Pro."],
            ["AWS during build (3 months)", "₹6,000 – 12,000", "₹6,000 – 12,000", "~USD 25–45 / month on the cheap stack."],
            ["Domain, SSL, misc.", "₹5,000 – 15,000", "₹5,000 – 15,000", "app.simulok.in; ACM itself is free on CloudFront."],
            ["Content / formula invention", "₹0", "₹0", "Excluded: scripts already contain maths and scoring."],
            ["Custom UI per simulation", "₹0", "₹0", "Excluded: shared Simulok shell."],
            ["Total one-time (recommended)", "₹6 – 10.5 lakh", "₹11.5 – 20 lakh", "Use the two-hire band if the founder is not coding daily."],
        ],
    )
    add_para(
        doc,
        "Budget slide (single number, two developers + founder, India, Cursor Start): approximately ₹15–17 lakh one-time to go live with 6 MBA simulations. The 15-title catalogue is not in this number — those titles are the post-launch add-a-sim cadence (see §8), paid for by the first college invoices and a part-time engineer, not by delaying launch.",
        size=11,
        bold=True,
    )
    add_para(
        doc,
        "An agency doing the same scope is typically ₹40–70 lakh. That is optional, not required, if two engineers plus Cursor are available.",
        size=11,
    )
    add_para(doc, "What this one-time number pays for", size=12, bold=True, color=NAVY, space_after=6)
    bullet(doc, "Auth, institutions, cohorts, entitlements, assignment, attempt store, profiles.")
    bullet(doc, "Shared play UI (briefing / round / results) used by the six and every title added later.")
    bullet(doc, "Mounting 6 scripts as versioned packs (2 MCQ + 2 1-player + K2 + universe-lite).")
    bullet(doc, "Multiplayer session lifecycle and universe-lite market tick — built once, reused for later MP/universe titles.")
    bullet(doc, "Dev and prod AWS, CI/CD, backup rehearsal, Week-9 pilot support.")
    add_para(doc, "What it does not pay for", size=12, bold=True, color=NAVY, space_after=6)
    bullet(doc, "Writing pedagogical scripts (assumed available for the six; later titles need their scripts before the pack week).")
    bullet(doc, "The remaining library (HelioGrid, DashMart, MacroEcon, Lemonade, school MCQs, second MP, …) — those are §8, after go-live.")
    bullet(doc, "Inventing new engines or unique UIs per title.")
    bullet(doc, "LTI, payments, mobile apps, white-label, 24/7 SLA, second region.")

    heading(doc, "7.2 Recurring monthly infrastructure cost (AWS)", 2)
    add_para(
        doc,
        "Stack: CloudFront + S3, Lambda + HTTP API, API Gateway WebSockets, RDS Postgres, Cognito, CloudWatch (14-day logs). No NAT Gateway, no load balancer, no Kubernetes, no Aurora in Phase 1. Region: ap-south-1.",
        size=11,
    )
    add_table(
        doc,
        ["AWS line", "Idle / tiny", "1 college, ~80 concurrent", "10 colleges, ~800 concurrent peak"],
        [
            ["Lambda + HTTP API", "USD 0–3", "USD 6–15", "USD 50–120"],
            ["WebSocket API", "USD 0", "USD 1–5", "USD 5–25"],
            ["RDS Postgres + storage/backups", "USD 12–18 (t4g.micro)", "USD 28–35 (t4g.small)", "USD 60–90 (t4g.medium)"],
            ["RDS Proxy", "Skip", "USD 12 (add if connections spike)", "USD 12–25"],
            ["S3 + CloudFront", "USD 1–3", "USD 3–8", "USD 15–40"],
            ["Cognito", "USD 0", "USD 0–10", "USD 0–80"],
            ["CloudWatch, Secrets, Route 53", "USD 3–6", "USD 6–12", "USD 25–45"],
            ["WAF (from first paying SLA)", "—", "USD 8–12", "USD 15–25"],
            ["Total USD / month", "USD 25–45", "USD 75–130", "USD 250–500"],
            ["Total INR / month (approx.)", "₹2,000 – 4,000", "₹6,500 – 11,000", "₹21,000 – 43,000"],
        ],
    )
    add_para(
        doc,
        "At first college, plan ₹7,000–11,000 per month for AWS. The bill is dominated by Postgres, not per-student clicks. Multi-AZ (high availability) roughly doubles the database line — add it when a college contract has an SLA, not on day one.",
        size=11,
    )
    add_para(
        doc,
        "Cognito’s always-free tier covers a large student list at the beginning; cost appears when monthly active users grow. Confirm current AWS list prices at the time of purchase.",
        size=11,
    )

    heading(doc, "7.3 Recurring people cost (optional, after launch)", 2)
    add_table(
        doc,
        ["Operating mode", "Monthly", "When to choose it"],
        [
            ["Founders + Cursor Start only", "₹1,950 tools (3 seats) + AWS", "Few new titles; you mount packs yourself."],
            ["Part-time engineer (~0.3 FTE)", "₹40,000 – 80,000 + Cursor + AWS", "A few new titles per month plus faculty support."],
            ["Full-time engineer", "₹1.5 – 2.5 lakh + Cursor + AWS", "Library growing every month and several live colleges."],
        ],
    )
    add_para(
        doc,
        "Recommended Day-1 after launch: AWS (₹7–11k) + part-time engineer on Cursor Start. That person exists to add HelioGrid, DashMart, MacroEcon and the next MBA topic — not to babysit a frozen catalogue.",
        size=11,
        bold=True,
    )

    heading(doc, "7.4 Cost snapshot for a budget slide", 2)
    add_table(
        doc,
        ["", "Amount", "Cadence"],
        [
            ["Go live with 6 MBA simulations", "₹11.5 – 20 lakh (plan ₹15–17 lakh)", "One-time, 11 weeks"],
            ["Cursor Start (India), 3 seats", "₹1,947 / month (₹5,850 over 3 months)", "Every month during build"],
            ["AWS — first college", "₹7,000 – 11,000", "Every month"],
            ["AWS — tenth college (peak class time)", "₹21,000 – 43,000", "Every month"],
            ["Add one more MCQ / 1-player sim (see §8)", "₹3,000 – 20,000 loaded", "Per title, after go-live"],
        ],
    )

    heading(doc, "8. Adding one simulation after the platform is ready", 1)
    add_para(
        doc,
        "This is the product after Week 11. Phase 1 got a college paying on 6 titles. Every title after that is a content-mount job: same shell, same APIs, same faculty console. No new AWS account, no new screens, no redeploy of unrelated colleges. Suggested first four: HelioGrid (marketing / STP), DashMart (operations), MacroEcon, then the next negotiations or finance MCQ.",
        size=11,
    )

    heading(doc, "8.1 What “platform ready” means (the gate)", 2)
    add_para(doc, "Do not start a new title until these exist. If they do, engineering on a new sim is pack work only.", size=11)
    bullet(doc, "Shared play UI: briefing → round → choices → KPI bar → results / debrief. No per-sim layout.")
    bullet(doc, "Pack contract frozen: manifest.json, content.json, optional engine.js, JSON schema, validate:pack.")
    bullet(doc, "CI publishes a pack to S3 as sim_id @ version. Assignment pins that version.")
    bullet(doc, "Admin entitlements (which college may see which sim) and faculty assign (which cohort plays it).")
    bullet(doc, "Student attempt store and server-side scoring already work for the six launch titles.")
    bullet(doc, "Cursor Start on the simulations seat. Founder reviews against the script, not against taste.")

    heading(doc, "8.2 Effort at a glance (script in hand, Cursor Start)", 2)
    add_para(
        doc,
        "Loaded rate: ₹8,000–12,000 per developer-day (use ₹10,000/day to plan). AWS does not move in a meaningful way for one extra pack (a few KB on S3). Founder time is review, not coding.",
        size=11,
    )
    add_table(
        doc,
        ["Type", "Wall-clock", "Developer effort", "Founder / domain", "Engineering cost", "What the developer actually does"],
        [
            ["MCQ (e.g. next negotiations case)", "1 working day", "0.3–0.5 day", "1–2 hours playtest", "₹3,000 – 6,000", "Map script → content.json; validator; golden paths; publish."],
            ["1-player (e.g. HelioGrid)", "2–3 days", "1–1.5 days", "Half a day playtest", "₹8,000 – 20,000", "Wire script maths into the standard engine interface. No new screens."],
            ["Multiplayer (second title after K2)", "4–7 days", "2–4 days", "5-person dry run", "₹16,000 – 48,000", "Roles + barrier config from the script. Reuse K2 lobby. Humans test join/rejoin."],
            ["Universe (second shared market)", "8–12 days + playtest", "5–8 days", "Two-team playtest", "₹40,000 – 1.0 lakh", "Market tick from the script; leaderboard; facilitator shocks if specified."],
        ],
    )
    add_para(
        doc,
        "Steady-state for Simulok (mostly MCQ and 1-player): about one new title a week including founder review. A month of part-time engineering after launch is 3–4 MBA titles, not a new project. Infra stays the first-college AWS bill.",
        size=11,
        bold=True,
    )

    heading(doc, "8.3 Script gate — stop here if this is missing", 2)
    add_para(doc, "The developer does not invent pedagogy. If the script lacks any of the following, send it back to domain. Do not start a pack.", size=11)
    bullet(doc, "Audience and course (e.g. MBA Operations, 45–60 min).")
    bullet(doc, "Rounds (or questions): order, briefing text, choices the student sees.")
    bullet(doc, "Effects of each choice on state / KPIs (tables or formulas — in the script).")
    bullet(doc, "Scoring / grade weights and the debrief the student reads at the end.")
    bullet(doc, "If multiplayer: roles, hidden vs shared information, what “all submitted” means, timer default.")
    bullet(doc, "If universe: how the shared market ticks, what each team submits, how the leaderboard is ranked.")
    bullet(doc, "2–5 golden paths: “if the student always picks A then B, score must be X.”")

    heading(doc, "8.4 Seven steps — every new title", 2)
    add_para(doc, "1. Script gate. Domain delivers the script. Founder ticks §8.3. If anything is blank, the title is not in engineering this week.", size=11, space_after=4)
    add_para(doc, "2. Pack from template. Developer copies packs/_template/ (or the closest live pack of the same format). Names the folder sim_id (e.g. heliogrid). Fills manifest: title, format, version, course tags, duration.", size=11, space_after=4)
    add_para(doc, "3. Cursor Plan. Paste the script. Ask for a section-by-section checklist mapped to content.json keys (and engine methods if not MCQ). Human accepts or edits the checklist before Agent writes files.", size=11, space_after=4)
    add_para(doc, "4. Agent implements 1:1. content.json holds narrative, options, tables. engine.js (1-player / MP / universe only) implements state, applyAction / resolveRound, score — copied from the script, not invented. Shared UI is not forked.", size=11, space_after=4)
    add_para(doc, "5. Validator + golden tests. npm run validate:pack — schema must pass. Then 5–10 scripted play paths must produce the script’s KPIs and grade. Failures are almost always mapping errors. Fix mapping; do not “tune” the model.", size=11, space_after=4)
    add_para(doc, "6. Publish a version. CI uploads sim_id @ v1 to S3. Nothing about Dealcraft or Mumbai changes. Live classes stay on the version they were assigned. A later v2 cannot alter a mid-semester cohort.", size=11, space_after=4)
    add_para(doc, "7. Entitle, assign, play, enable. Admin toggles the new sim for the college. Faculty assigns a test cohort (or themselves). Founder plays once against the script. If green, faculty assigns the real cohort. Students only see what they are assigned.", size=11, space_after=10)
    add_para(
        doc,
        "Who is in the loop: simulations developer (does the pack), founder/domain (script + playtest), admin (entitle), faculty (assign). Platform developer is not required unless the title needs a new control the shell does not have — and that is out of policy.",
        size=11,
        bold=True,
    )

    heading(doc, "8.5 Worked example A — add one MCQ (1 day)", 2)
    add_table(
        doc,
        ["When", "Activity", "Owner", "Effort"],
        [
            ["Morning, hour 1", "Script gate. Confirm questions, options, scores, debrief.", "Domain", "30–45 min"],
            ["Hours 2–4", "Cursor Plan + Agent: content.json from the script. Run validate:pack.", "Developer + Cursor", "2–3 hr"],
            ["Hour 5", "Golden-check 5 question paths. Fix any score mismatch.", "Developer", "1 hr"],
            ["Hour 6", "CI publish v1. Admin entitles one college. Faculty assigns a test group.", "Dev + Admin", "30–45 min"],
            ["Hour 7", "Founder plays the MCQ once. If green, enable the real cohort.", "Domain", "30–45 min"],
        ],
    )
    add_para(doc, "Cost: about ₹3,000–6,000. Calendar: same working day if the script arrived before 10:00.", size=11, bold=True)

    heading(doc, "8.6 Worked example B — add one 1-player (HelioGrid-class, 3 days)", 2)
    add_table(
        doc,
        ["When", "Activity", "Owner", "Effort"],
        [
            ["Day 0", "Script received. Confirm rounds, options, effects, KPIs, score weights, debrief, 5 golden paths.", "Domain", "1–2 hr"],
            ["Day 1", "Pack folder + manifest. Cursor Plan checklist. Agent fills content and engine methods 1:1 with script sections. Shared round UI — no new screens.", "Developer + Cursor", "1 day"],
            ["Day 2", "Golden tests for 5–10 scripted paths. Fix mapping errors. Server-side score matches the script.", "Developer", "0.5–1 day"],
            ["Day 3 morning", "Publish v1 to S3. Admin entitles the college. Faculty assigns a test cohort (or the founder).", "Dev + Admin", "1–2 hr"],
            ["Day 3 afternoon", "Founder plays a full run against the script (Ask on the pack diff). If green, enable the real cohort.", "Domain", "2–3 hr"],
        ],
    )
    add_para(doc, "Cost: about ₹8,000–20,000. Infra does not materially move. This is the default add after launch (HelioGrid first).", size=11, bold=True)

    heading(doc, "8.7 Worked example C — add a second multiplayer or universe", 2)
    bullet(doc, "Multiplayer: Days 1–2 same as 1-player (pack + engine from script). Days 3–7 are classroom QA on the existing K2 lobby — join code, timer, rejoin, force-advance with the new roles. Do not build a second lobby.")
    bullet(doc, "Universe: Weeks, not days. Tick Lambda and leaderboard already exist from Phase 1. New work is the script’s market rules + one two-team playtest. Do not add regulators or extra factions.")
    add_para(doc, "Cost: MP ₹16,000–48,000; universe ₹40,000–1.0 lakh plus the playtest. Still cheaper than delaying Phase 1 to include them.", size=11)

    heading(doc, "8.8 What would make a new sim expensive again (avoid these)", 2)
    bullet(doc, "A unique screen layout or new control type not in the shared shell — that is a platform change, not an add-a-sim.")
    bullet(doc, "Maths missing or contradictory in the script (engineering then becomes modelling). Send it back.")
    bullet(doc, "Realtime twitch interaction (the platform is turn-based).")
    bullet(doc, "Changing another sim’s live version instead of publishing a new version.")
    bullet(doc, "Waiting to batch ten titles before publishing. Publish v1 of HelioGrid the week it is green; the next title starts the next Monday.")
    add_para(
        doc,
        "If the script is complete and the UI stays on the shell, none of those should apply. Adding one simulation is then days, not a project.",
        size=11,
    )

    heading(doc, "9. Risks that still consume calendar (even with scripts, shared UI, and Cursor Start)", 1)
    bullet(doc, "Classroom lifecycle: late join, laptop close, one team blocking others, professor needs to skip ahead — this is Weeks 5–7, independent of pedagogy and of Cursor.")
    bullet(doc, "Campus Wi-Fi: keep hot-seat fallback on every multiplayer title.")
    bullet(doc, "9:00 a.m. login spike: warm Lambdas from the timetable.")
    bullet(doc, "Single-AZ Postgres during a graded class: snapshots + rehearsed restore; Multi-AZ when an SLA exists.")
    bullet(doc, "Content still needs a named reviewer against the script, or scoring disputes land in WhatsApp.")
    bullet(doc, "Cursor Start usage pool: if a seat exhausts the month, switch that seat to Composer for mechanical packs; do not silently assume a Pro upgrade.")
    bullet(doc, "Waiting for a 15-title catalogue before the first invoice. Phase 1 is 6 titles on purpose.")
    bullet(doc, "Week-9 live class cannot be AI-shortened. Book the professor now.")

    heading(doc, "10. Decisions to take this week", 1)
    add_para(doc, "1. Freeze the 6-title MBA mix (Dealcraft, Brand Wars, Mumbai Manufacturer, Zara, K2, universe-lite) or swap a title — do not drop a format.", size=11, space_after=4)
    add_para(doc, "2. Confirm team shape: three seats as in §2 (two developers + founder). That is the ₹15–17 lakh band.", size=11, space_after=4)
    add_para(doc, "3. Put all three people on Cursor Start (India) at ₹649/month. Do not budget Cursor Pro.", size=11, space_after=4)
    add_para(doc, "4. Create AWS dev/prod, budgets, MFA.", size=11, space_after=4)
    add_para(doc, "5. Reserve app.simulok.in and start TLS.", size=11, space_after=4)
    add_para(doc, "6. Put a real Week-9 MBA classroom on the calendar (named professor, date, 40–80 students).", size=11, space_after=4)
    add_para(doc, "7. Name the first four post-launch titles (suggested: HelioGrid, DashMart, MacroEcon, next MCQ) so adding starts the week you go live.", size=11, space_after=12)

    add_para(
        doc,
        "End of document. Phase 1 is a 6-title go-to-market, not a finished catalogue. This plan assumes scripts, a shared UI, and Cursor Start (India) on every seat. Changing those assumptions (new formulas, unique UI, LTI, a mobile app, Cursor Pro, or waiting for 15 titles) reopens both calendar and cost.",
        size=10,
        color=MUTED,
        space_after=0,
    )

    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
