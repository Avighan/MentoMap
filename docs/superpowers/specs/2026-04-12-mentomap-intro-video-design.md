# MentoMap Animated Intro Video — Design Spec

## Overview

Two animated explainer videos for MentoMap's Middle School Future Skills Curriculum, targeting school principals and decision-makers. Built using the HTML5 Canvas Animated Video Production Framework.

**Video A (this spec):** Sizzle reel — 2-3 minute overview
**Video B (future spec):** Detailed walkthrough — 4-5 minutes

This spec covers **Video A** only.

---

## Target Audience

School principals and decision-makers considering adopting MentoMap's 9-month curriculum for Grades 6-8.

## Core Message

"Adopt the full 9-month future skills curriculum — workshops, simulations, and off-time learning — aligned with NEP 2020."

## Video Concept: "The Tour"

Mento (the mascot) acts as a **host and interviewer**, walking the viewer through different school environments. In each scene, Mento asks a question and a character (Principal, Teacher, or Student) answers with a key point about MentoMap.

---

## Characters

### Mento (Host)
- **Rendering:** Image sprite loaded from `MentoCharacter.jpeg`
- **Size:** ~70-80px wide on canvas, scaled proportionally
- **Position:** Typically left side of screen
- **Visual treatment:** Orange drop-shadow/glow underneath to ground in scene
- **Speech bubble border:** `#FFB347` (orange)
- **Role:** Asks questions, introduces scenes, hosts the tour

### Principal Sharma (Male, ~50s)
- **Rendering:** Framework `Person` class (canvas-drawn)
- **Appearance:**
  - `skin: '#c49464'`
  - `hairColor: '#555555'` (gray)
  - `hairStyle: 'short'`
  - `shirtColor: '#1a365d'` (dark suit)
  - `pantsColor: '#1a1a3e'`
  - `hasGlasses: true`, `glassesStyle: 'rect'`
  - `hasCollar: true`, `hasTie: true`, `tieColor: '#8B0000'`
  - `accentColor: '#4A90D9'` (professional blue)
  - `female: false`
- **Expression arc:** stressed → curious → impressed → convinced

### Teacher Priya (Female, ~30s)
- **Rendering:** Framework `Person` class
- **Appearance:**
  - `skin: '#d4a574'`
  - `hairColor: '#1a1a2e'`
  - `hairStyle: 'long'`
  - `shirtColor: '#C62828'` (red, saree-inspired)
  - `pantsColor: '#8B1A1A'`
  - `accentColor: '#E57373'` (warm red)
  - `female: true`
  - `hasEarring: true`
- **Expression arc:** enthusiastic → confident → proud

### Student Arjun (Male, ~13)
- **Rendering:** Framework `Person` class, smaller scale (lower Z depth ~0.42 or reduced CHAR_SCALE)
- **Appearance:**
  - `skin: '#c49464'`
  - `hairColor: '#1a1a2e'`
  - `hairStyle: 'short'`
  - `shirtColor: '#2E7D32'` (green, school uniform)
  - `pantsColor: '#1a1a3e'`
  - `accentColor: '#66BB6A'` (bright green)
  - `female: false`
- **Expression arc:** bored → curious → excited → happy

---

## Brand Palette

| Role | Color | Hex |
|------|-------|-----|
| Primary (MentoMap orange) | Brand accent, UI, Mento glow | `#FFB347` |
| Dark | Darker shade for gradients | `#E08A1E` |
| Light | Glow, highlights | `#FFD180` |
| Background dark | Canvas clear color | `#1a1a2e` |

---

## Visual Style

- **Tone:** Warm and playful
- **Backgrounds:** Illustrated/cartoon school settings (AI-generated images matching Mento's warm orange aesthetic)
- **Character style:** Framework's canvas-drawn cartoon characters (Person class)
- **Speech bubbles:** Dark background (`rgba(8,14,10,.95)`) with character accent color border, typewriter text reveal
- **Effects:** Floating particles (warm orange/yellow), confetti on CTA, sequential pop-in animations for info panels

---

## Scene Breakdown

### Scene 1: "Meet Mento" (~20s)

**Background:** Illustrated school entrance — gate with "MentoMap School" sign, trees, warm sunny sky, welcoming path
**Darken:** 0.45 (lighter — bright and inviting)
**Lighting:** warm

**Characters:**
- Mento: center (`W*0.5, H*0.75`), enters from left with bounce animation

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "What if your school could teach the skills no textbook covers?" | (0.5, 0.25) | center |
| 1 | Mento | "I'm Mento — let me show you something that will change how your students learn." | (0.5, 0.25) | center |

**Camera:** Start wide, slow zoom to 1.02 on Mento
**Effects:** Particle burst on Mento entrance, ambient floating sparkles (warm orange)
**Subtitle:** "MentoMap — Future Skills Curriculum for Grades 6, 7 & 8"

---

### Scene 2: "The Principal's Problem" (~25s)

**Background:** Illustrated principal's office — wooden desk, bookshelf, window with trees, certificates/photos on wall
**Darken:** 0.55
**Lighting:** warm

**Characters:**
- Mento: left (`W*0.18, H*0.82`, z: 0.5)
- Principal Sharma: right (`W*0.72, H*0.82`, z: 0.5)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "Principal Sharma, what's the biggest challenge you face?" | (0.25, 0.25) | left |
| 1 | Sharma | "Our students ace exams... but struggle with teamwork, decisions, and communication." | (0.72, 0.25) | right |
| 2 | Mento | "What if there was a curriculum designed exactly for that?" | (0.25, 0.25) | left |

**Expressions:**
- Sharma: stressed (line 0-1) → curious (line 2)
- Camera: focus Mento (line 0), focus Sharma (line 1), focus Mento (line 2)

---

### Scene 3: "The 3-Mode Solution" (~30s)

**Background:** Illustrated classroom — rows of desks, chalkboard, colorful posters on walls, open windows
**Darken:** 0.50
**Lighting:** warm

**Characters:**
- Mento: left (`W*0.15, H*0.82`, z: 0.5)
- Teacher Priya: center-right (`W*0.55, H*0.82`, z: 0.5)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "Teacher Priya, how does MentoMap work in your classroom?" | (0.22, 0.25) | left |
| 1 | Priya | "Every month has 3 modes — physical workshops with real materials..." | (0.58, 0.25) | right |
| 2 | Priya | "...digital simulations where students play and learn on the platform..." | (0.58, 0.25) | right |
| 3 | Priya | "...and off-time games they play at home for practice and competition!" | (0.58, 0.25) | right |

**Custom Elements:**
Three floating icon panels appear sequentially on the right side (`W*0.82`) as Priya speaks each line:
1. Line 1 → Workshop icon panel (cards/hands icon + "Workshops" label)
2. Line 2 → Simulation icon panel (game controller icon + "Simulations" label)
3. Line 3 → Home icon panel (house icon + "Off-Time Play" label)

Each panel pops in with elastic easing.

**Expressions:** Priya: enthusiastic throughout
**Camera:** Wide shot (zoom 1.0) to fit characters + floating icons

---

### Scene 4: "9 Subjects, 3 Grades" (~25s)

**Background:** Same classroom, darker overlay focused on chalkboard area
**Darken:** 0.65
**Lighting:** green (brand glow)

**Characters:**
- Mento: left (`W*0.12, H*0.82`, z: 0.5)
- Priya: background right (`W*0.85, H*0.82`, z: 0.35) — smaller, supporting

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "9 future-ready subjects across Grades 6, 7, and 8..." | (0.20, 0.20) | left |
| 1 | Mento | "All aligned with NEP 2020. No new teachers needed — just the curriculum and our platform." | (0.20, 0.20) | left |

**Custom Elements:**

**Subject Grid (3x3)** — drawn on the chalkboard area (`W*0.35` to `W*0.75`, `H*0.15` to `H*0.65`):

| Col 1 | Col 2 | Col 3 |
|-------|-------|-------|
| Financial Literacy | Entrepreneurship | Negotiation |
| AI & Technology | Leadership | Storytelling |
| Marketing | Critical Thinking | Ethics & Teamwork |

Each cell: icon (emoji rendered as text) + subject name below. Cells pop in sequentially (top-left to bottom-right) with particle burst per cell. Timing: 1 cell per ~1.5s during line 0.

**NEP 2020 Badge** — appears on line 1: rounded rect with checkmark + "NEP 2020 Aligned", positioned bottom-right of the grid.

**Camera:** Zoom 1.0, slight pan to center the grid

---

### Scene 5: "The Student Experience" (~25s)

**Background:** Illustrated computer lab or student's room — desk with monitor, colorful posters, books, warm lighting
**Darken:** 0.50
**Lighting:** warm

**Characters:**
- Mento: left (`W*0.15, H*0.82`, z: 0.5)
- Student Arjun: right (`W*0.55, H*0.82`, z: 0.45) — slightly smaller (younger)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "Arjun, what's it like playing a MentoMap simulation?" | (0.22, 0.25) | left |
| 1 | Arjun | "I ran a startup with just Rs 5,000 — had to make real decisions every round!" | (0.58, 0.25) | right |
| 2 | Arjun | "My strategic thinking score went up, and I beat my friend on the leaderboard!" | (0.58, 0.25) | right |

**Custom Elements:**

**Mini game UI mockup** — appears on line 1 at right side (`W*0.72, H*0.35`):
- Simplified game frame showing a scenario title + 3 choice buttons
- Monitor/screen style (using `drawMonitor` pattern)
- Subtle animated glow

**Stat badges** — appear on line 2 using `drawStatBadges()`:
- "8 Dimensions" | "79+ Games" | "24/7 Access"
- Positioned at `(W*0.5, H*0.72)`, pop in sequentially with elastic easing

**Expressions:** Arjun: curious (line 0) → excited (line 1-2)
**Camera:** Focus Mento (line 0), focus Arjun (line 1), wide (line 2 for stat badges)

---

### Scene 6: "CTA — Adopt the Curriculum" (~15s)

**Background:** Illustrated school courtyard — school building in background, open sky, golden hour warm lighting, trees
**Darken:** 0.40 (lightest — triumphant feel)
**Lighting:** triumph (golden glow)

**Characters:** All four together:
- Mento: center-front (`W*0.5, H*0.78`, z: 0.6) — foreground, largest
- Sharma: left (`W*0.22, H*0.82`, z: 0.5)
- Priya: center-left (`W*0.38, H*0.82`, z: 0.5)
- Arjun: center-right (`W*0.62, H*0.82`, z: 0.45)

**Dialogue:**
| # | Speaker | Text | Bubble Pos | Side |
|---|---------|------|-----------|------|
| 0 | Mento | "Ready to build future-ready students?" | (0.5, 0.18) | center |

**Custom Elements:**
- **Confetti burst** at `t > 0.3` — `emitConfetti(W/2, H*0.3, 40)`
- **CTA button** at `t > 0.5` — "Adopt MentoMap → mentomap.in" using `drawCTA()`
- **Subtitle bar:** "9 Months. 9 Subjects. Grades 6-8. One Complete Curriculum."

**Expressions:** All characters: happy/proud
**Camera:** Wide shot (zoom 1.0), slight zoom to 1.02 at end

**End card (last 3s):** Fade to black → MentoMap logo + "hello@mentomap.in" + "mentomap.in"

---

## Background Images Required

| # | Scene | Description | Filename |
|---|-------|-------------|----------|
| 1 | Scene 1 | School entrance — gate, trees, sunny sky, welcoming | `school_entrance.jpg` |
| 2 | Scene 2 | Principal's office — desk, bookshelf, certificates | `principal_office.jpg` |
| 3 | Scenes 3-4 | Classroom — desks, chalkboard, colorful walls | `classroom.jpg` |
| 4 | Scene 5 | Computer lab / student room — desk, monitor, posters | `student_room.jpg` |
| 5 | Scene 6 | School courtyard — golden hour, building, open sky | `school_courtyard.jpg` |

All images: **1920x1080 minimum**, illustrated/cartoon style matching Mento's warm orange aesthetic. AI-generated recommended.

---

## Audio Strategy

**Phase 1 (current):** No voiceover — video is silent with animated speech bubbles and typewriter text. Timeline pacing uses word-count estimation: `duration = max((wordCount + 1) / 2.7 + 0.25, 2.0)` seconds per line.

**Phase 2 (after finalization):** Generate ElevenLabs MP3s per dialogue line. Save as `audio/scene{N}_{L}.mp3`. Update `AUDIO_DURS` dictionary. All audio hooks are pre-wired in the template.

---

## Technical Implementation

### Stack
- Single-file HTML5 (self-contained)
- HTML5 Canvas 2D rendering at 1920x1080
- requestAnimationFrame at 60fps
- MediaRecorder API for in-browser WebM capture
- FFmpeg for WebM → MP4 conversion

### Key Components
1. **Mento sprite:** Loaded via `new Image()` from `MentoCharacter.jpeg`, drawn with `drawImage()` at calculated position/scale, with orange glow shadow
2. **Human characters:** 3 `Person` class instances with configured appearances
3. **Backgrounds:** 5 JPG images loaded via `loadBg()`, drawn with `drawBgImage()` + darken overlay
4. **Subject grid:** Custom `drawSubjectGrid()` function — 3x3 cells with emoji icons + labels, sequential pop-in
5. **3-mode icons:** Custom `drawModeIcons()` — 3 floating panels with icons + labels
6. **Game mockup:** Custom `drawGameMockup()` — simplified monitor with scenario + choices
7. **Stat badges:** Framework's `drawStatBadges()` with MentoMap data
8. **CTA button:** Framework's `drawCTA()` with brand styling
9. **NEP badge:** Custom `drawNEPBadge()` — rounded rect with checkmark

### File Structure
```
video-output/
  sizzle-reel/
    mentomap_sizzle.html      # Main video file (single HTML)
    images/
      MentoCharacter.jpeg     # Mento mascot sprite (copied)
      school_entrance.jpg     # Scene 1 background
      principal_office.jpg    # Scene 2 background
      classroom.jpg           # Scene 3-4 background
      student_room.jpg        # Scene 5 background
      school_courtyard.jpg    # Scene 6 background
    audio/                    # Empty for now — ElevenLabs MP3s later
    record.js                 # Playwright recording script
```

### Recording Pipeline
1. `python3 -m http.server 8765` in `sizzle-reel/`
2. Open in Chrome, click start overlay
3. Use in-browser Record button → downloads WebM
4. `ffmpeg -y -i output.webm -c:v libx264 -crf 20 -preset medium -c:a aac -b:a 192k -movflags +faststart mentomap_sizzle.mp4`

---

## Estimated Duration Breakdown

| Scene | Lines | Est. Words | Est. Duration |
|-------|-------|-----------|---------------|
| 1. Meet Mento | 2 | 32 | ~18s |
| 2. Principal's Problem | 3 | 35 | ~22s |
| 3. 3-Mode Solution | 4 | 42 | ~28s |
| 4. 9 Subjects | 2 | 30 | ~22s |
| 5. Student Experience | 3 | 38 | ~24s |
| 6. CTA | 1 | 7 | ~15s (with effects buffer) |
| **Transitions** | — | — | ~7s (6 × ~1.2s) |
| **Total** | **15** | **184** | **~2 min 16s** |

Within the 2-3 minute target.

---

## Out of Scope (for this spec)

- Video B (4-5 min detailed walkthrough) — separate spec after Video A is complete
- ElevenLabs voiceover — added after video is finalized
- Hindi language version
- Background music track
