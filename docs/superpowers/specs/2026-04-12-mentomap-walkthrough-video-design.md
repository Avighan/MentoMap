# MentoMap Animated Walkthrough Video — Design Spec

## Overview

A 7-minute animated explainer video (Video B) for MentoMap's Middle School Future Skills Curriculum. Follows one student through a real week of learning across the 3 modes: Workshop, Simulation, and Off-Time Play.

**Video A (sizzle reel):** 2-minute overview — completed, see `2026-04-12-mentomap-intro-video-design.md`
**Video B (this spec):** 7-minute detailed walkthrough

---

## Target Audience

School principals and decision-makers who have seen Video A and want to understand what the curriculum actually looks like in practice.

## Core Message

"Here's what a real week with MentoMap looks like — three learning modes, four future-ready subjects, and measurable skill growth your students will love."

## Video Concept: "A Week with MentoMap"

Mento narrates Arjun's journey through one school week:
- **Monday** — Workshop Day (Financial Literacy + Entrepreneurship)
- **Wednesday** — Simulation Day (Negotiation — animated gameplay demo)
- **Saturday** — Off-Time Play (Ethics & Teamwork at home)

The narrative makes the abstract curriculum concrete. Principals see exactly what their students experience.

---

## Characters

Reuse all 4 characters from Video A (same Person class configs, same Mento sprite).

### Mento (Narrator)
- Same image sprite from Video A (`MentoCharacter.png`)
- Role: Narrates Arjun's journey, explains what skills are being built
- Appears in every scene on the left side

### Student Arjun (Protagonist)
- Same Person config as Video A (green shirt, short hair, smaller scale)
- Role: The student we follow through the week
- Expression arc: curious → engaged → excited → proud

### Teacher Priya
- Same Person config as Video A (red saree-inspired, earring)
- Role: Teaches the Monday workshops
- Appears in Scenes 2-3

### Principal Sharma
- Same Person config as Video A (gray hair, glasses, tie)
- Role: Sees the dashboard results at the end
- Appears in Scene 7 only

---

## Brand Palette

Same as Video A:

| Role | Hex |
|------|-----|
| Primary (MentoMap orange) | `#FFB347` |
| Dark | `#E08A1E` |
| Light | `#FFD180` |
| Background dark | `#1a1a2e` |

Additional accent colors for day cards:
- Monday (Workshop): `#66BB6A` (green)
- Wednesday (Simulation): `#4A90D9` (blue)
- Saturday (Off-Time): `#FFA726` (amber)

---

## Background Images

Reuse all 5 backgrounds from Video A. No new images needed.

| Scene | Background | From Video A |
|-------|-----------|-------------|
| 1 (Intro) | School entrance | `school_entrance.jpg` |
| 2-3 (Workshops) | Classroom | `classroom.jpg` |
| 4 (Negotiation demo) | Student room | `student_room.jpg` |
| 5 (Skill results) | Dark overlay on student room | `student_room.jpg` |
| 6 (Ethics at home) | Student room | `student_room.jpg` |
| 7 (Principal dashboard) | Principal's office | `principal_office.jpg` |
| 8 (CTA) | School courtyard | `school_courtyard.jpg` |

---

## Scene Breakdown

### Day Card Transitions

Three animated day cards break the video into chapters. Each is ~5 seconds:
- Calendar page-flip animation (old page peels away, new page slides in)
- Day name in large text with mode subtitle
- Color-coded to the mode (green/blue/amber)
- Particle burst matching the day color

**Day Card 1:** "Monday — Workshop Day" (green, `#66BB6A`)
**Day Card 2:** "Wednesday — Simulation Day" (blue, `#4A90D9`)
**Day Card 3:** "Saturday — Off-Time Play" (amber, `#FFA726`)

---

### Scene 1: "Remember Me?" (~30s)

**Background:** School entrance (`school_entrance.jpg`)
**Darken:** 0.45
**Lighting:** warm

**Characters:**
- Mento: center (`W*0.5, H*0.75`), enters from left with bounce
- Arjun: enters from right after Mento's first line (`W*0.65, H*0.82`, z: 0.45)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "Remember me? Last time I showed you what MentoMap is. Today, let me show you what a real week looks like." | (0.5, 0.25) | center |
| 1 | Arjun | "I'm Arjun, Grade 7. This week we're doing Financial Literacy and Entrepreneurship!" | (0.65, 0.25) | right |
| 2 | Mento | "Let's follow his journey — three days, three learning modes." | (0.35, 0.25) | left |

**Camera:** Start wide, focus Arjun on line 1, wide on line 2
**Effects:** Mento entrance bounce + particle burst. Callback text subtitle: "Continued from: MentoMap Sizzle Reel"

---

### Scene 2: Financial Literacy Workshop (~60s)

**Background:** Classroom (`classroom.jpg`)
**Darken:** 0.50
**Lighting:** warm

**Characters:**
- Mento: left (`W*0.12, H*0.82`, z: 0.5)
- Priya: center-right (`W*0.55, H*0.82`, z: 0.5)
- Arjun: far right (`W*0.78, H*0.82`, z: 0.42) — smaller, student in class

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "It's Monday morning. Teacher Priya has something special for the class." | (0.20, 0.20) | left |
| 1 | Priya | "Today's challenge: You've inherited a lemonade recipe and ₹500. Build a business!" | (0.55, 0.20) | right |
| 2 | Arjun | "We had to pick a location, buy inventory, and set prices — all with real trade-offs!" | (0.75, 0.25) | right |
| 3 | Mento | "Inventory management, pricing strategy, break-even point — real business concepts, learned through play." | (0.20, 0.20) | left |

**Custom Elements — Workshop Props:**

Three floating cards pop in sequentially on the right side (`W*0.82`) as Arjun speaks (line 2):

1. **Location Card** — Icon: 📍, Label: "Location", Detail: "Front Yard vs Park vs Partner Store"
2. **Inventory Card** — Icon: 📦, Label: "Inventory", Detail: "30 cups (₹50) vs 80 cups (₹120)"
3. **Pricing Card** — Icon: 💰, Label: "Pricing", Detail: "Budget ₹8 vs Premium ₹18"

Each card: rounded rect with icon + label + detail text, pops in with elastic easing. Cards have a warm orange glow border.

**Source Game:** Lemonade Empire (`lemonade-empire-enhanced.json`)

**Camera:** Focus Priya on line 1, focus Arjun on line 2, wide on line 3
**Expressions:** Priya: enthusiastic. Arjun: curious → excited.

---

### Scene 3: Entrepreneurship Workshop (~60s)

**Background:** Same classroom (`classroom.jpg`)
**Darken:** 0.50
**Lighting:** warm

**Characters:**
- Mento: left (`W*0.12, H*0.82`, z: 0.5)
- Priya: center (`W*0.45, H*0.82`, z: 0.5)
- Arjun: right (`W*0.72, H*0.82`, z: 0.42)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Priya | "Now the big one — you each have ₹5 lakhs. Pick a startup idea and pitch it!" | (0.48, 0.20) | right |
| 1 | Arjun | "I chose a money management app for teenagers — my aunt confirmed it's a real pain point!" | (0.72, 0.25) | right |
| 2 | Mento | "MVP, burn rate, runway — not just vocabulary, but decisions they have to live with." | (0.20, 0.20) | left |
| 3 | Priya | "Two subjects in one morning — and they don't even realize they're learning!" | (0.48, 0.20) | right |

**Custom Elements — Startup Idea Cards:**

Three cards pop in sequentially at (`W*0.82`) during line 0-1:

1. **FinTech Card** — Icon: 💳, Color: `#4A90D9`, Title: "FinTech", Detail: "Teen money app — Clear customer need"
2. **AgriTech Card** — Icon: 🌾, Color: `#66BB6A`, Title: "AgriTech", Detail: "Farmer marketplace — High impact, hard exec"
3. **HealthTech Card** — Icon: 🧠, Color: `#ce93d8`, Title: "HealthTech", Detail: "AI wellness chatbot — Competitive market"

Card Arjun chose (FinTech) gets a green check overlay + glow when line 1 plays.

**Source Game:** Startup Pitch Battle (`startup_pitch_battle_v1.json`)

**Camera:** Focus Priya on line 0, focus Arjun on line 1, focus Mento on line 2, wide on line 3
**Expressions:** Priya: confident. Arjun: excited.

---

### Scene 4: Negotiation Game Demo (~90s) — HERO SCENE

**Background:** Student room (`student_room.jpg`)
**Darken:** 0.55
**Lighting:** warm with blue tint (simulation feel)

**Characters:**
- Mento: left (`W*0.12, H*0.82`, z: 0.5)
- Arjun: center-left (`W*0.35, H*0.82`, z: 0.48) — looking at the "screen"

**Dialogue (Part 1 — Setup):**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "Wednesday afternoon. Arjun logs into MentoMap for a negotiation simulation." | (0.20, 0.18) | left |
| 1 | Arjun | "This one's called 'The Pocket Money Talk' — I have to convince Amma to raise my allowance from ₹500 to ₹800!" | (0.38, 0.18) | left |

**Custom Element — Game Monitor:**

A large animated game monitor appears at right side (`W*0.55` to `W*0.92`, `H*0.10` to `H*0.75`). Uses `drawMonitor()` pattern from Video A but larger.

**Animated Gameplay Sequence (inside the monitor):**

The gameplay sequence runs during lines 2-5, synchronized with dialogue:

**Step 1 — Scenario Reveal (during line 2):**
Text types onto the monitor screen:
> "It's the 20th of the month and your wallet is empty again. ₹500 just doesn't stretch. School supplies: ₹200. Transport: ₹150. One outing: ₹200. That's ₹550 for basics alone."

**Step 2 — Choice Selection (during line 3):**
Three choice buttons appear on the monitor:
- A) "Present specific expenses — show the budget breakdown"
- B) "Offer to take on responsibilities in return" ← highlighted green (Arjun's pick)
- C) "Ask for a compromise — meet in the middle at ₹650"

Animated cursor hovers over options, clicks B. Choice B highlights with green border + checkmark.

**Step 3 — Score Update (during line 4):**
Skill score badges pop out from the monitor:
- "Empathy +8" (orange badge)
- "Strategic Thinking +5" (green badge)
- "Adaptability +6" (blue badge)

Mini skill radar chart appears below the monitor, axes animate to new values.

**Dialogue (Part 2 — During gameplay):**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 2 | Mento | "Watch — the scenario appears, and Arjun reads the situation." | (0.20, 0.80) | left |
| 3 | Mento | "Three choices. Each one measures different skills. No right or wrong — strategic or impulsive." | (0.20, 0.80) | left |
| 4 | Mento | "Watch his empathy score — offering responsibilities shows maturity." | (0.20, 0.80) | left |
| 5 | Arjun | "Amma actually agreed to ₹700 — and I'm doing the dishes now!" | (0.38, 0.80) | left |

**Source Game:** Negotiation Arena — "The Pocket Money Talk" scenario (`negotiation_game.json`)

**Camera:** Wide shot (zoom 1.0) throughout to show both characters + monitor. Slight zoom on monitor during Steps 1-3.
**Expressions:** Arjun: thinking (lines 0-3) → happy (line 5)

---

### Scene 5: Skill Results (~40s)

**Background:** Student room with heavy darken overlay (results screen feel)
**Darken:** 0.70
**Lighting:** green (brand glow, achievement feel)

**Characters:**
- Mento: left (`W*0.12, H*0.82`, z: 0.5)
- Arjun: center-left (`W*0.35, H*0.82`, z: 0.48)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "After each game, students see exactly how their skills are growing." | (0.20, 0.18) | left |
| 1 | Arjun | "I'm in the top 20% for strategic thinking! And my empathy score jumped 15 points!" | (0.38, 0.18) | left |

**Custom Elements:**

**8-Dimension Skill Radar** — drawn at right side (`W*0.65, H*0.45`), diameter ~300px:
- 8 axes: Strategic Thinking, Risk Tolerance, Delayed Gratification, Adaptability, Resilience, Empathy, Growth Mindset, Self-Awareness
- Axes draw in one by one with labels
- Values fill as animated polygon (grows from center)
- Each axis has its score number that counts up

**Leaderboard Badge** — appears below radar at (`W*0.65, H*0.78`):
- "Top 20% — Strategic Thinking"
- Counter animation (1% → 20%)
- Small confetti burst on reveal

**Camera:** Wide shot. Slight zoom toward radar chart during line 0.
**Expressions:** Arjun: proud

---

### Scene 6: Ethics & Teamwork at Home (~50s)

**Background:** Student room (`student_room.jpg`)
**Darken:** 0.50
**Lighting:** warm (cozy home feel)

**Characters:**
- Mento: left (`W*0.15, H*0.82`, z: 0.5)
- Arjun: right (`W*0.55, H*0.82`, z: 0.45) — at desk, looking at implied tablet

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "Saturday evening. Arjun's playing 'The Ethics Hotline' at home — his school's ethics reporting system needs him." | (0.22, 0.20) | left |
| 1 | Arjun | "A student copied Neha's homework and the teacher blamed Neha! I have the evidence — but do I go to the teacher or the principal?" | (0.58, 0.20) | right |
| 2 | Mento | "No right answer — every choice has trade-offs. That's what builds ethical reasoning." | (0.22, 0.20) | left |
| 3 | Arjun | "My mom thinks I'm just playing games... but I'm learning how to handle real situations!" | (0.58, 0.20) | right |

**Custom Elements — Off-Time Feature Badges:**

Four badges pop in sequentially at (`W*0.82`) during line 3:
1. "🔥 5-day streak" — orange badge
2. "🏆 Friend challenge" — gold badge
3. "🎁 Daily rewards" — purple badge
4. "📱 24/7 access" — blue badge

Each badge pops with elastic easing.

**Source Game:** The Ethics Hotline — "The Copied Homework" scenario (`the-ethics-hotline.json`)

**Camera:** Focus Mento (line 0), focus Arjun (line 1-2), wide (line 3 for badges)
**Expressions:** Arjun: thinking (lines 0-1) → happy (line 3)

---

### Scene 7: The Bigger Picture (~40s)

**Background:** Principal's office (`principal_office.jpg`)
**Darken:** 0.55
**Lighting:** warm

**Characters:**
- Mento: left (`W*0.18, H*0.82`, z: 0.5)
- Sharma: right (`W*0.72, H*0.82`, z: 0.5)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "And here's what principals see — every student, every skill, every month." | (0.25, 0.20) | left |
| 1 | Sharma | "For the first time, I can see my students growing in ways exams never measured." | (0.72, 0.20) | right |
| 2 | Mento | "9 months. 9 subjects. All aligned with NEP 2020. No new teachers needed." | (0.25, 0.20) | left |

**Custom Elements — Dashboard Panels:**

Three animated dashboard panels appear at center (`W*0.35` to `W*0.65`, `H*0.55` to `H*0.75`) during line 0-1:

1. **9-Month Progress Bar** — horizontal bar filling left-to-right, month markers (1-9), current month highlighted
2. **Skill Dimensions Grid** — 8 small bars showing class averages for each dimension, fill with animation
3. **NEP 2020 Badge** — rounded rect with checkmark + "NEP 2020 Aligned", pops in on line 2

**Camera:** Focus Mento (line 0), focus Sharma (line 1), wide (line 2 for badge)
**Expressions:** Sharma: impressed → convinced

---

### Scene 8: CTA — "Start Your Journey" (~20s)

**Background:** School courtyard (`school_courtyard.jpg`)
**Darken:** 0.40 (brightest — triumphant)
**Lighting:** triumph (golden glow)

**Characters:** All four together (same positions as Video A Scene 6):
- Mento: center-front (`W*0.5, H*0.78`, z: 0.6)
- Sharma: left (`W*0.22, H*0.82`, z: 0.5)
- Priya: center-left (`W*0.38, H*0.82`, z: 0.5)
- Arjun: center-right (`W*0.62, H*0.82`, z: 0.45)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "One week. Three modes. Skills that last a lifetime. Start your school's MentoMap journey." | (0.5, 0.18) | center |

**Custom Elements:**
- **Confetti burst** at `t > 0.3`
- **CTA button** at `t > 0.5` — "Adopt MentoMap → mentomap.in"
- **Subtitle bar:** "9 Months. 9 Subjects. Grades 6-8. One Complete Curriculum."

**End card (last 3s):** Same as Video A — fade to black → MentoMap logo + "hello@mentomap.in" + "mentomap.in" + "Future Skills for Every Student"

**Expressions:** All characters: happy/proud
**Camera:** Wide shot, slight zoom to 1.02

---

## New Custom Drawing Functions Required

| Function | Scene | Description |
|----------|-------|-------------|
| `drawDayCard()` | Between scenes | Calendar page-flip animation with day name, mode label, color accent |
| `drawWorkshopCard()` | 2 | Floating card with icon + title + detail text, elastic pop-in |
| `drawStartupCard()` | 3 | Colored card with icon + title + subtitle, green check overlay for selection |
| `drawGameMonitorLarge()` | 4 | Large monitor frame with inner content area for gameplay animation |
| `drawScenarioText()` | 4 | Typewriter text inside monitor (game scenario content) |
| `drawChoiceButtons()` | 4 | 3 choice buttons inside monitor with hover/select animation |
| `drawSkillBadgeFloat()` | 4, 5 | Floating "+N" skill badges that pop out with score changes |
| `drawSkillRadar()` | 5 | 8-axis radar chart with animated polygon fill + axis labels |
| `drawLeaderboardBadge()` | 5 | "Top X%" badge with counter animation |
| `drawOffTimeBadge()` | 6 | Feature badge (streak, challenge, rewards, access) with icon |
| `drawDashboardPanel()` | 7 | Dashboard panels (progress bar, skill grid, NEP badge) |
| `drawProgressBar9Month()` | 7 | Horizontal 9-month progress bar with month markers |

Functions reused from Video A: `drawMento()`, `drawBgImage()`, `drawSceneBg()`, `drawSceneLighting()`, `drawVignette()`, `drawDialogue()`, `drawCTA()`, `drawStatBadges()`, `drawNEPBadge()`, `emitConfetti()`, `emitParticle()`, `emitBurst()`, Person class, camera system, timeline builder.

---

## Audio Strategy

Same as Video A: silent with typewriter speech bubbles. ElevenLabs voiceover added later after both videos are finalized.

---

## Estimated Duration Breakdown

| Scene | Lines | Est. Words | Est. Duration |
|-------|-------|-----------|---------------|
| 1. Intro | 3 | 42 | ~30s |
| Day Card: Monday | — | — | ~5s |
| 2. Financial Literacy | 4 | 45 | ~60s |
| 3. Entrepreneurship | 4 | 48 | ~60s |
| Day Card: Wednesday | — | — | ~5s |
| 4. Negotiation Demo | 6 | 70 | ~90s |
| 5. Skill Results | 2 | 28 | ~40s |
| Day Card: Saturday | — | — | ~5s |
| 6. Ethics at Home | 4 | 55 | ~50s |
| 7. Principal Dashboard | 3 | 35 | ~40s |
| 8. CTA | 1 | 18 | ~20s |
| **Transitions** | — | — | ~10s (8 × ~1.2s) |
| **Total** | **27** | **341** | **~7 min 15s** |

---

## Technical Implementation

### Stack
Same as Video A: single-file HTML5 Canvas, 1920x1080, 60fps, MediaRecorder for WebM capture.

### File Structure
```
video-output/
  walkthrough/
    mentomap_walkthrough.html    # Main video file (single HTML)
    images/                      # Symlink or copy from sizzle-reel/images/
      MentoCharacter.png
      school_entrance.jpg
      principal_office.jpg
      classroom.jpg
      student_room.jpg
      school_courtyard.jpg
    audio/                       # Empty for now
    serve.py                     # Local HTTP server
    record.js                    # Playwright recording script
```

### Recording Pipeline
Same as Video A:
1. `python3 serve.py 8766` in `walkthrough/`
2. `node record.js` (Playwright automated capture)
3. `ffmpeg -y -i mentomap_walkthrough.webm -c:v libx264 -crf 20 -preset medium -movflags +faststart mentomap_walkthrough.mp4`

---

## Out of Scope

- ElevenLabs voiceover — added after video is finalized
- Hindi language version
- Background music track
- Interactive viewer features (click-to-explore)
