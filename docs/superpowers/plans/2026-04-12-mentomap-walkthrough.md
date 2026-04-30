# MentoMap Walkthrough Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 7-minute animated walkthrough video (Video B) following student Arjun through a week of MentoMap learning, using real game content from the platform.

**Architecture:** Single-file HTML5 Canvas application reusing Video A's framework (Person class, dialogue system, camera, particles). Copy the framework from `video-output/sizzle-reel/mentomap_sizzle.html`, strip Video A's scenes, and build 8 new scenes + 3 day card transitions with 12 new custom drawing functions.

**Tech Stack:** HTML5 Canvas 2D, vanilla JavaScript, MediaRecorder API, Playwright for recording, FFmpeg for conversion.

**Spec:** `docs/superpowers/specs/2026-04-12-mentomap-walkthrough-video-design.md`

---

## File Structure

```
video-output/
  walkthrough/
    mentomap_walkthrough.html    # Main video file (single HTML, ~2200 lines)
    images/                      # Copied from sizzle-reel/images/
      MentoCharacter.png
      school_entrance.jpg
      principal_office.jpg
      classroom.jpg
      student_room.jpg
      school_courtyard.jpg
    serve.py                     # Local HTTP server (port 8766)
    record.js                    # Playwright recording script
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `video-output/walkthrough/serve.py`
- Create: `video-output/walkthrough/record.js`
- Modify: `.claude/launch.json`
- Copy: `video-output/sizzle-reel/images/*` → `video-output/walkthrough/images/`

- [ ] **Step 1: Create directory and copy images**

```bash
mkdir -p video-output/walkthrough/images
cp video-output/sizzle-reel/images/MentoCharacter.png video-output/walkthrough/images/
cp video-output/sizzle-reel/images/school_entrance.jpg video-output/walkthrough/images/
cp video-output/sizzle-reel/images/principal_office.jpg video-output/walkthrough/images/
cp video-output/sizzle-reel/images/classroom.jpg video-output/walkthrough/images/
cp video-output/sizzle-reel/images/student_room.jpg video-output/walkthrough/images/
cp video-output/sizzle-reel/images/school_courtyard.jpg video-output/walkthrough/images/
```

- [ ] **Step 2: Create serve.py**

```python
import http.server
import os
import sys

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
os.chdir(os.path.dirname(os.path.abspath(__file__)))
handler = http.server.SimpleHTTPRequestHandler
with http.server.HTTPServer(("", port), handler) as httpd:
    print(f"Serving on port {port}")
    httpd.serve_forever()
```

- [ ] **Step 3: Create record.js**

```javascript
const { chromium } = require('playwright');
const path = require('path');

const URL = 'http://localhost:8766/mentomap_walkthrough.html';
const WEBM_FILE = path.join(__dirname, 'mentomap_walkthrough.webm');

(async () => {
  const browser = await chromium.launch({
    headless: false,
    args: [
      '--autoplay-policy=no-user-gesture-required',
      '--use-fake-ui-for-media-stream',
      '--window-size=1920,1080',
    ],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    acceptDownloads: true,
  });

  const page = await context.newPage();
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  const overlay = page.locator('#startOverlay');
  if (await overlay.isVisible()) await overlay.click();
  await page.waitForTimeout(1000);

  await page.evaluate(() => { playing = false; });
  await page.waitForTimeout(500);
  await page.locator('#recBtn').click();
  await page.waitForTimeout(1000);

  const download = await page.waitForEvent('download', { timeout: 600000 });
  await download.saveAs(WEBM_FILE);

  await browser.close();

  console.log('Recording saved to: ' + WEBM_FILE);
  console.log('Convert to MP4:');
  console.log('  ffmpeg -y -i mentomap_walkthrough.webm -c:v libx264 -crf 20 -preset medium -movflags +faststart mentomap_walkthrough.mp4');
})();
```

- [ ] **Step 4: Update launch.json**

Add to the `configurations` array in `.claude/launch.json`:

```json
{
  "name": "walkthrough-preview",
  "runtimeExecutable": "/opt/homebrew/bin/python3",
  "runtimeArgs": ["/Users/amajumder/Downloads/MentoApp/video-output/walkthrough/serve.py", "8766"],
  "port": 8766
}
```

- [ ] **Step 5: Commit**

```bash
git add video-output/walkthrough/serve.py video-output/walkthrough/record.js .claude/launch.json
git commit -m "feat: scaffold walkthrough video project (Video B)"
```

---

### Task 2: Base HTML Framework (Copy from Video A)

**Files:**
- Create: `video-output/walkthrough/mentomap_walkthrough.html`
- Reference: `video-output/sizzle-reel/mentomap_sizzle.html`

This task copies the reusable framework from Video A and strips the scene-specific code. The resulting file is a working skeleton that renders a dark canvas with characters but no scenes.

- [ ] **Step 1: Copy Video A HTML as starting point**

```bash
cp video-output/sizzle-reel/mentomap_sizzle.html video-output/walkthrough/mentomap_walkthrough.html
```

- [ ] **Step 2: Update the start overlay text**

Replace the overlay content:
- Title: change `"MentoMap"` → `"MentoMap"`
- Tagline: change `"Future Skills Curriculum — Sizzle Reel"` → `"A Week with MentoMap — Detailed Walkthrough"`
- Subtitle: change any reference to "sizzle" → "walkthrough"

- [ ] **Step 3: Remove Video A scene-specific code**

Delete the following sections entirely (they will be replaced in later tasks):

1. **Video A's custom element functions** — `drawModeIcon()`, `drawSubjectGrid()`, `drawGameMockup()`, `drawStatBadges()`, `drawNEPBadge()`. Keep `drawCTA()` (reused in Scene 8).
2. **Video A's scene draw functions** — `drawScene1()` through `drawScene6()` and the `sceneDraws` array.
3. **Video A's timeline definitions** — all the `s1d`, `s2d`, etc. dialogue arrays and their `buildTimeline()` calls.
4. **Video A's scene data arrays** — `sceneTimelines`, `sceneTitles`, `sceneDurs`, `sceneStarts`, `TOTAL`.
5. **Video A's subtitle definitions** — `sceneSubtitles` array.

Leave placeholder comments where the removed code was:
```javascript
// ===== CUSTOM DRAWING FUNCTIONS (Tasks 3-6) =====

// ===== SCENE TIMELINES (Tasks 7-10) =====

// ===== SCENE DRAW FUNCTIONS (Tasks 7-9) =====

// ===== SCENE ASSEMBLY (Task 10) =====
```

- [ ] **Step 4: Update recording filename**

In `startRecording()`, change the download filename:
```javascript
a.download = 'mentomap_walkthrough.webm';
```

- [ ] **Step 5: Verify the skeleton loads**

Run: `python3 video-output/walkthrough/serve.py 8766`
Open: `http://localhost:8766/mentomap_walkthrough.html`
Expected: Dark canvas with start overlay showing "A Week with MentoMap". Clicking start shows a dark canvas (no scenes yet).

- [ ] **Step 6: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: walkthrough base framework from Video A skeleton"
```

---

### Task 3: Day Card Drawing Function

**Files:**
- Modify: `video-output/walkthrough/mentomap_walkthrough.html` (custom drawing functions section)

- [ ] **Step 1: Add drawDayCard function**

Insert at the `// ===== CUSTOM DRAWING FUNCTIONS` placeholder:

```javascript
// ===== CUSTOM DRAWING FUNCTIONS =====

function drawDayCard(c, dayText, modeText, color, t) {
  // t: 0→1 animation progress
  // Calendar page-flip: old page peels away, new slides in
  const flipT = clamp(t * 2.5, 0, 1);
  const contentT = clamp((t - 0.3) * 2, 0, 1);

  // Dark overlay background
  c.fillStyle = '#1a1a2e';
  c.fillRect(0, 0, W, H);

  // Calendar card
  const cardW = 500, cardH = 280;
  const cx = W / 2, cy = H / 2;

  // Card shadow
  c.save();
  c.shadowColor = 'rgba(0,0,0,0.5)';
  c.shadowBlur = 30;
  c.shadowOffsetY = 10;

  // Page flip animation — card slides up from bottom
  const slideY = (1 - ease.out(flipT)) * 200;
  const cardAlpha = ease.out(clamp(flipT * 2, 0, 1));
  c.globalAlpha = cardAlpha;

  // Card body
  c.fillStyle = '#22223a';
  rr(c, cx - cardW/2, cy - cardH/2 + slideY, cardW, cardH, 16);
  c.fill();

  // Top color strip (like calendar header)
  c.fillStyle = color;
  rr(c, cx - cardW/2, cy - cardH/2 + slideY, cardW, 60, 16);
  c.fill();
  // Cover bottom corners of header
  c.fillStyle = color;
  c.fillRect(cx - cardW/2, cy - cardH/2 + slideY + 44, cardW, 16);

  c.restore();

  // Day text
  if (contentT > 0) {
    c.globalAlpha = ease.out(contentT);
    c.textAlign = 'center';

    // Day name (large)
    c.font = 'bold 48px "Segoe UI"';
    c.fillStyle = '#ffffff';
    c.fillText(dayText, cx, cy + slideY + 10);

    // Mode subtitle
    c.font = '22px "Segoe UI"';
    c.fillStyle = hexRGBA(color, 0.9);
    c.fillText(modeText, cx, cy + slideY + 48);

    c.textAlign = 'left';
    c.globalAlpha = 1;
  }

  // Particle burst matching day color
  if (t > 0.2 && t < 0.25) {
    emitBurst(cx, cy, 15, 2, 60, 3, color, 'glow', 0.01);
  }
}
```

- [ ] **Step 2: Verify day card renders**

Temporarily add a test in the main loop or a test scene. Open the preview and confirm a calendar card with colored header, day text, and subtitle renders correctly.

- [ ] **Step 3: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: add drawDayCard() for chapter transitions"
```

---

### Task 4: Workshop & Startup Card Functions

**Files:**
- Modify: `video-output/walkthrough/mentomap_walkthrough.html`

- [ ] **Step 1: Add drawWorkshopCard function**

```javascript
function drawWorkshopCard(c, x, y, icon, label, detail, t) {
  // Floating card with icon + label + detail, elastic pop-in
  const s = ease.elastic(clamp(t * 1.5, 0, 1));
  if (s < 0.01) return;

  c.save();
  c.translate(x, y);
  c.scale(s, s);

  const w = 160, h = 90;

  // Card glow
  c.shadowColor = hexRGBA(NV, 0.4);
  c.shadowBlur = 12;

  // Card background
  c.fillStyle = 'rgba(30,30,50,0.92)';
  rr(c, -w/2, -h/2, w, h, 10);
  c.fill();

  // Border
  c.strokeStyle = hexRGBA(NV, 0.5);
  c.lineWidth = 1.5;
  rr(c, -w/2, -h/2, w, h, 10);
  c.stroke();

  c.shadowBlur = 0;

  // Icon
  c.font = '28px "Segoe UI Emoji", "Apple Color Emoji"';
  c.textAlign = 'center';
  c.fillText(icon, 0, -14);

  // Label
  c.font = 'bold 13px "Segoe UI"';
  c.fillStyle = NV;
  c.fillText(label, 0, 8);

  // Detail
  c.font = '10px "Segoe UI"';
  c.fillStyle = '#888';
  const lines = detail.split('\n');
  lines.forEach((line, i) => {
    c.fillText(line, 0, 24 + i * 13);
  });

  c.textAlign = 'left';
  c.restore();
}

function drawStartupCard(c, x, y, icon, title, detail, color, t, selected) {
  // Colored card with icon + title + subtitle, green check for selection
  const s = ease.elastic(clamp(t * 1.5, 0, 1));
  if (s < 0.01) return;

  c.save();
  c.translate(x, y);
  c.scale(s, s);

  const w = 150, h = 90;

  // Glow
  c.shadowColor = hexRGBA(color, 0.3);
  c.shadowBlur = 10;

  // Background
  c.fillStyle = hexRGBA(color, 0.08);
  rr(c, -w/2, -h/2, w, h, 10);
  c.fill();

  // Border
  c.strokeStyle = hexRGBA(color, selected ? 0.8 : 0.3);
  c.lineWidth = selected ? 2 : 1;
  rr(c, -w/2, -h/2, w, h, 10);
  c.stroke();

  c.shadowBlur = 0;

  // Icon
  c.font = '24px "Segoe UI Emoji", "Apple Color Emoji"';
  c.textAlign = 'center';
  c.fillText(icon, 0, -16);

  // Title
  c.font = 'bold 13px "Segoe UI"';
  c.fillStyle = color;
  c.fillText(title, 0, 4);

  // Detail
  c.font = '10px "Segoe UI"';
  c.fillStyle = '#888';
  c.fillText(detail, 0, 20);

  // Green check if selected
  if (selected) {
    c.font = 'bold 18px "Segoe UI"';
    c.fillStyle = '#66BB6A';
    c.fillText('✓', w/2 - 16, -h/2 + 18);
  }

  c.textAlign = 'left';
  c.restore();
}
```

- [ ] **Step 2: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: add drawWorkshopCard() and drawStartupCard()"
```

---

### Task 5: Game Monitor & Gameplay Animation Functions

**Files:**
- Modify: `video-output/walkthrough/mentomap_walkthrough.html`

- [ ] **Step 1: Add game monitor and gameplay functions**

```javascript
function drawGameMonitorLarge(c, x, y, w, h, t) {
  // Large monitor frame for gameplay demo
  const fadeIn = clamp(t * 3, 0, 1);
  if (fadeIn < 0.01) return;
  c.save();
  c.globalAlpha = fadeIn;

  // Monitor shadow
  c.shadowColor = 'rgba(0,0,0,0.4)';
  c.shadowBlur = 20;

  // Outer frame
  c.fillStyle = '#181828';
  rr(c, x, y, w, h, 12);
  c.fill();

  // Screen border
  c.strokeStyle = hexRGBA(NV, 0.3);
  c.lineWidth = 2;
  rr(c, x, y, w, h, 12);
  c.stroke();

  c.shadowBlur = 0;

  // Inner screen
  const pad = 8;
  c.fillStyle = 'rgba(10,10,20,0.95)';
  rr(c, x + pad, y + pad, w - pad*2, h - pad*2, 8);
  c.fill();

  // Title bar
  c.fillStyle = 'rgba(255,179,71,0.1)';
  c.fillRect(x + pad, y + pad, w - pad*2, 28);
  c.font = 'bold 12px "Segoe UI"';
  c.fillStyle = NV;
  c.textAlign = 'left';
  c.fillText('🤝 Negotiation Arena — The Pocket Money Talk', x + pad + 10, y + pad + 19);

  // Scan line effect
  const scanY = (Date.now() / 30) % (h - pad*2);
  c.fillStyle = 'rgba(255,255,255,0.02)';
  c.fillRect(x + pad, y + pad + scanY, w - pad*2, 2);

  c.restore();
  // Return inner screen bounds for content drawing
  return { ix: x + pad + 6, iy: y + pad + 34, iw: w - pad*2 - 12, ih: h - pad*2 - 40 };
}

function drawScenarioText(c, x, y, maxW, text, revealPct) {
  // Typewriter text inside game monitor
  if (revealPct <= 0) return;
  const revealed = text.substring(0, Math.floor(text.length * clamp(revealPct, 0, 1)));
  c.font = '14px "Segoe UI"';
  c.fillStyle = '#cccccc';
  c.textAlign = 'left';
  const lines = wordWrap(revealed, maxW, c.font);
  lines.forEach((line, i) => {
    c.fillText(line, x, y + i * 20);
  });
  // Blinking cursor
  if (revealPct < 1 && Math.floor(Date.now() / 500) % 2 === 0) {
    const lastLine = lines[lines.length - 1] || '';
    const cursorX = x + c.measureText(lastLine).width + 2;
    const cursorY = y + (lines.length - 1) * 20;
    c.fillStyle = NV;
    c.fillRect(cursorX, cursorY - 12, 2, 14);
  }
}

function drawChoiceButtons(c, x, y, w, choices, selectedIdx, t) {
  // 3 choice buttons with hover/select animation
  // choices: array of {label, text}
  // selectedIdx: -1 for none, 0-2 for selected
  const btnH = 36, gap = 8;
  choices.forEach((ch, i) => {
    const btnT = clamp((t - i * 0.15) * 3, 0, 1);
    if (btnT <= 0) return;
    const by = y + i * (btnH + gap);
    const isSelected = (i === selectedIdx);

    c.save();
    c.globalAlpha = ease.out(btnT);

    // Button background
    c.fillStyle = isSelected ? 'rgba(102,187,106,0.15)' : 'rgba(255,255,255,0.04)';
    rr(c, x, by, w, btnH, 6);
    c.fill();

    // Border
    c.strokeStyle = isSelected ? 'rgba(102,187,106,0.6)' : 'rgba(255,255,255,0.1)';
    c.lineWidth = isSelected ? 2 : 1;
    rr(c, x, by, w, btnH, 6);
    c.stroke();

    // Label
    c.font = isSelected ? 'bold 12px "Segoe UI"' : '12px "Segoe UI"';
    c.fillStyle = isSelected ? '#66BB6A' : '#aaa';
    c.textAlign = 'left';
    c.fillText(ch.label + ') ' + ch.text, x + 12, by + 22);

    // Checkmark
    if (isSelected) {
      c.font = 'bold 16px "Segoe UI"';
      c.fillStyle = '#66BB6A';
      c.textAlign = 'right';
      c.fillText('✓', x + w - 10, by + 24);
    }

    c.textAlign = 'left';
    c.restore();
  });
}

function drawSkillBadgeFloat(c, x, y, text, color, t) {
  // Floating "+N" skill badge that pops out
  const s = ease.elastic(clamp(t * 2, 0, 1));
  const fadeOut = t > 0.7 ? 1 - (t - 0.7) / 0.3 : 1;
  if (s < 0.01 || fadeOut <= 0) return;

  c.save();
  c.globalAlpha = fadeOut;
  c.translate(x, y - (1 - fadeOut) * 20);
  c.scale(s, s);

  // Badge background
  c.fillStyle = hexRGBA(color, 0.15);
  const tw = c.measureText(text).width;
  rr(c, -tw/2 - 12, -14, tw + 24, 28, 14);
  c.fill();

  // Border
  c.strokeStyle = hexRGBA(color, 0.4);
  c.lineWidth = 1;
  rr(c, -tw/2 - 12, -14, tw + 24, 28, 14);
  c.stroke();

  // Text
  c.font = 'bold 13px "Segoe UI"';
  c.fillStyle = color;
  c.textAlign = 'center';
  c.fillText(text, 0, 5);

  c.textAlign = 'left';
  c.restore();
}
```

- [ ] **Step 2: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: add game monitor, scenario text, choice buttons, skill badge functions"
```

---

### Task 6: Skill Radar, Leaderboard, Off-Time & Dashboard Functions

**Files:**
- Modify: `video-output/walkthrough/mentomap_walkthrough.html`

- [ ] **Step 1: Add skill radar chart function**

```javascript
function drawSkillRadar(c, cx, cy, radius, dimensions, values, t) {
  // 8-axis radar chart with animated polygon fill
  // dimensions: array of {name, value} (0-100)
  // values: animated fill (0→1)
  // t: overall animation progress
  const n = dimensions.length;
  const angleStep = (PI * 2) / n;
  const startAngle = -PI / 2;

  // Draw axes and labels
  c.save();
  for (let i = 0; i < n; i++) {
    const axisT = clamp((t - i * 0.08) * 3, 0, 1);
    if (axisT <= 0) continue;
    const angle = startAngle + i * angleStep;
    const ex = cx + Math.cos(angle) * radius;
    const ey = cy + Math.sin(angle) * radius;

    // Axis line
    c.globalAlpha = axisT * 0.3;
    c.strokeStyle = '#555';
    c.lineWidth = 1;
    c.beginPath();
    c.moveTo(cx, cy);
    c.lineTo(cx + (ex - cx) * axisT, cy + (ey - cy) * axisT);
    c.stroke();

    // Label
    c.globalAlpha = axisT;
    c.font = '10px "Segoe UI"';
    c.fillStyle = '#aaa';
    c.textAlign = 'center';
    const lx = cx + Math.cos(angle) * (radius + 20);
    const ly = cy + Math.sin(angle) * (radius + 20);
    c.fillText(dimensions[i].name, lx, ly + 4);

    // Score number
    const score = Math.round(dimensions[i].value * clamp(t * 2 - 0.3, 0, 1));
    c.font = 'bold 11px "Segoe UI"';
    c.fillStyle = NV;
    const sx = cx + Math.cos(angle) * (radius + 36);
    const sy = cy + Math.sin(angle) * (radius + 36);
    c.fillText(score, sx, sy + 4);
  }

  // Draw value polygon
  const polyT = clamp((t - 0.3) * 2, 0, 1);
  if (polyT > 0) {
    // Fill polygon
    c.globalAlpha = polyT * 0.25;
    c.fillStyle = NV;
    c.beginPath();
    for (let i = 0; i < n; i++) {
      const angle = startAngle + i * angleStep;
      const v = (dimensions[i].value / 100) * radius * polyT;
      const px = cx + Math.cos(angle) * v;
      const py = cy + Math.sin(angle) * v;
      if (i === 0) c.moveTo(px, py); else c.lineTo(px, py);
    }
    c.closePath();
    c.fill();

    // Stroke polygon
    c.globalAlpha = polyT * 0.8;
    c.strokeStyle = NV;
    c.lineWidth = 2;
    c.stroke();

    // Dots at vertices
    c.fillStyle = NV;
    for (let i = 0; i < n; i++) {
      const angle = startAngle + i * angleStep;
      const v = (dimensions[i].value / 100) * radius * polyT;
      const px = cx + Math.cos(angle) * v;
      const py = cy + Math.sin(angle) * v;
      c.globalAlpha = polyT;
      c.beginPath();
      c.arc(px, py, 3, 0, PI * 2);
      c.fill();
    }
  }

  c.restore();
}

function drawLeaderboardBadge(c, cx, cy, text, pct, t) {
  // "Top X%" badge with counter animation
  const s = ease.elastic(clamp(t * 2, 0, 1));
  if (s < 0.01) return;

  c.save();
  c.translate(cx, cy);
  c.scale(s, s);

  // Badge background
  const w = 220, h = 50;
  c.fillStyle = 'rgba(255,179,71,0.1)';
  rr(c, -w/2, -h/2, w, h, 25);
  c.fill();
  c.strokeStyle = hexRGBA(NV, 0.5);
  c.lineWidth = 2;
  rr(c, -w/2, -h/2, w, h, 25);
  c.stroke();

  // Trophy icon
  c.font = '22px "Segoe UI Emoji"';
  c.textAlign = 'center';
  c.fillText('🏆', -w/2 + 28, 8);

  // Counter text
  const displayPct = Math.round(pct * clamp(t * 3, 0, 1));
  c.font = 'bold 16px "Segoe UI"';
  c.fillStyle = NV;
  c.fillText('Top ' + displayPct + '%', 10, 6);

  // Label
  c.font = '11px "Segoe UI"';
  c.fillStyle = '#888';
  c.fillText(text, 10, 22);

  c.textAlign = 'left';
  c.restore();
}

function drawOffTimeBadge(c, x, y, icon, text, color, t) {
  // Feature badge with icon for off-time features
  const s = ease.elastic(clamp(t * 2, 0, 1));
  if (s < 0.01) return;

  c.save();
  c.translate(x, y);
  c.scale(s, s);

  c.fillStyle = hexRGBA(color, 0.12);
  const tw = 130;
  rr(c, -tw/2, -14, tw, 28, 14);
  c.fill();

  c.font = '13px "Segoe UI"';
  c.fillStyle = color;
  c.textAlign = 'center';
  c.fillText(icon + ' ' + text, 0, 5);

  c.textAlign = 'left';
  c.restore();
}

function drawDashboardPanel(c, x, y, w, h, type, t) {
  // Dashboard panel (progress bar, skill grid, NEP badge)
  const fadeIn = ease.out(clamp(t * 2, 0, 1));
  if (fadeIn < 0.01) return;

  c.save();
  c.globalAlpha = fadeIn;

  // Panel background
  c.fillStyle = 'rgba(20,20,40,0.9)';
  rr(c, x, y, w, h, 8);
  c.fill();
  c.strokeStyle = 'rgba(255,255,255,0.1)';
  c.lineWidth = 1;
  rr(c, x, y, w, h, 8);
  c.stroke();

  if (type === 'progress9month') {
    // 9-month progress bar
    c.font = 'bold 11px "Segoe UI"';
    c.fillStyle = '#888';
    c.textAlign = 'left';
    c.fillText('9-Month Progress', x + 10, y + 18);

    const barX = x + 10, barY = y + 28, barW = w - 20, barH = 12;
    c.fillStyle = 'rgba(255,255,255,0.06)';
    rr(c, barX, barY, barW, barH, 6);
    c.fill();

    // Filled portion (animate to month 3)
    const fillW = barW * (3/9) * clamp(t * 2 - 0.3, 0, 1);
    if (fillW > 0) {
      c.fillStyle = NV;
      rr(c, barX, barY, fillW, barH, 6);
      c.fill();
    }

    // Month markers
    c.font = '9px "Segoe UI"';
    c.textAlign = 'center';
    for (let m = 1; m <= 9; m++) {
      const mx = barX + barW * (m / 9) - barW / 18;
      c.fillStyle = m <= 3 ? NV : '#555';
      c.fillText(m, mx, barY + barH + 12);
    }
  } else if (type === 'skillgrid') {
    // 8 small bars for skill dimensions
    const dims = ['Strategic', 'Risk', 'Delayed G.', 'Adapt.', 'Resilience', 'Empathy', 'Growth', 'Self-Aware'];
    const vals = [72, 58, 65, 70, 55, 78, 62, 60];
    const bh = 8, gap = 3;
    c.font = '9px "Segoe UI"';
    dims.forEach((d, i) => {
      const by = y + 8 + i * (bh + gap);
      c.fillStyle = '#666';
      c.textAlign = 'left';
      c.fillText(d, x + 6, by + bh);
      // Bar track
      const bx = x + 65, bw = w - 80;
      c.fillStyle = 'rgba(255,255,255,0.05)';
      c.fillRect(bx, by, bw, bh);
      // Bar fill
      const fillW = bw * (vals[i] / 100) * clamp(t * 2 - i * 0.05, 0, 1);
      c.fillStyle = hexRGBA(NV, 0.6);
      c.fillRect(bx, by, fillW, bh);
    });
  } else if (type === 'nep') {
    // NEP 2020 badge
    c.font = 'bold 14px "Segoe UI"';
    c.fillStyle = '#66BB6A';
    c.textAlign = 'center';
    c.fillText('✓ NEP 2020 Aligned', x + w/2, y + h/2 + 5);
  }

  c.textAlign = 'left';
  c.restore();
}
```

- [ ] **Step 2: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: add skill radar, leaderboard, off-time badges, dashboard panels"
```

---

### Task 7: Scenes 1-3 (Intro + Monday Workshops)

**Files:**
- Modify: `video-output/walkthrough/mentomap_walkthrough.html`

- [ ] **Step 1: Add Scene 1 — Intro**

Insert at the `// ===== SCENE DRAW FUNCTIONS` placeholder:

```javascript
// ===== SCENE DRAW FUNCTIONS =====

function drawScene1(c, t, elapsed, timeline) {
  // "Remember Me?" — School entrance, Mento + Arjun
  drawBgImage(c, bgImgs[0]); // school_entrance
  drawSceneBg(c, 0.45);
  drawSceneLighting(c, 'warm');

  // Mento enters from left with bounce
  const mentoEnterT = clamp(t * 4, 0, 1);
  mento.goto(W * 0.5, H * 0.75, t < 0.01, 0.5);
  mento.op = ease.out(mentoEnterT);
  mento.update();
  drawMento(c);

  // Arjun enters from right after line 0
  const arjunEnterT = clamp((t - 0.15) * 4, 0, 1);
  arjun.goto(W * 0.65, H * 0.82, t < 0.15, 0.45);
  arjun.op = ease.out(arjunEnterT);
  arjun.expr = 'happy';
  arjun.update();
  sortAndDrawChars(c, [arjun]);

  // Particle burst on Mento entrance
  if (t > 0.02 && t < 0.05) {
    emitBurst(W * 0.5, H * 0.7, 12, 2, 60, 3, NV, 'glow', 0.01);
  }

  // Camera
  if (elapsed < timeline[0]?.endSec) camera.focusOn(0, 0, 1.0);
  else if (timeline[1] && elapsed < timeline[1].endSec) camera.focusOn(W * 0.1, 0, 1.02);
  else camera.focusOn(0, 0, 1.0);

  // Subtitle
  if (t > 0.1) showSubtitle('Continued from: MentoMap Sizzle Reel');
}
```

- [ ] **Step 2: Add Scene 2 — Financial Literacy Workshop**

```javascript
function drawScene2(c, t, elapsed, timeline) {
  // Financial Literacy Workshop — Classroom
  drawBgImage(c, bgImgs[2]); // classroom
  drawSceneBg(c, 0.50);
  drawSceneLighting(c, 'warm');

  // Characters
  mento.goto(W * 0.12, H * 0.82, t < 0.01, 0.5);
  mento.update();
  drawMento(c);

  priya.goto(W * 0.55, H * 0.82, t < 0.01, 0.5);
  priya.expr = 'confident';
  priya.update();

  arjun.goto(W * 0.78, H * 0.82, t < 0.01, 0.42);
  arjun.expr = elapsed > (timeline[1]?.endSec || 999) ? 'happy' : 'neutral';
  arjun.update();

  sortAndDrawChars(c, [priya, arjun]);

  // Workshop prop cards — pop in during line 2
  const line2Start = timeline[2]?.startSec || 999;
  const cardBaseT = (elapsed - line2Start) / 3;
  drawWorkshopCard(c, W * 0.82, H * 0.22, '📍', 'Location', 'Front Yard vs Park\nvs Partner Store', clamp(cardBaseT, 0, 1));
  drawWorkshopCard(c, W * 0.82, H * 0.42, '📦', 'Inventory', '30 cups (₹50) vs\n80 cups (₹120)', clamp(cardBaseT - 0.3, 0, 1));
  drawWorkshopCard(c, W * 0.82, H * 0.62, '💰', 'Pricing', 'Budget ₹8 vs\nPremium ₹18', clamp(cardBaseT - 0.6, 0, 1));

  // Camera focus
  if (timeline[0] && elapsed < timeline[0].endSec) camera.focusOn(0, 0, 1.0);
  else if (timeline[1] && elapsed < timeline[1].endSec) camera.focusOn(W * 0.05, 0, 1.02);
  else if (timeline[2] && elapsed < timeline[2].endSec) camera.focusOn(W * 0.15, 0, 1.01);
  else camera.focusOn(0, 0, 1.0);

  if (t > 0.1) showSubtitle('💰 Financial Literacy — Workshop Mode');
}
```

- [ ] **Step 3: Add Scene 3 — Entrepreneurship Workshop**

```javascript
function drawScene3(c, t, elapsed, timeline) {
  // Entrepreneurship Workshop — Same classroom
  drawBgImage(c, bgImgs[2]); // classroom
  drawSceneBg(c, 0.50);
  drawSceneLighting(c, 'warm');

  // Characters
  mento.goto(W * 0.12, H * 0.82, t < 0.01, 0.5);
  mento.update();
  drawMento(c);

  priya.goto(W * 0.45, H * 0.82, t < 0.01, 0.5);
  priya.expr = 'confident';
  priya.update();

  arjun.goto(W * 0.72, H * 0.82, t < 0.01, 0.42);
  arjun.expr = elapsed > (timeline[0]?.endSec || 999) ? 'happy' : 'neutral';
  arjun.update();

  sortAndDrawChars(c, [priya, arjun]);

  // Startup idea cards — pop in during line 0-1
  const line0Start = timeline[0]?.startSec || 0;
  const cardBaseT = (elapsed - line0Start) / 4;
  const selectedT = timeline[1] ? clamp((elapsed - timeline[1].startSec) / 1, 0, 1) : 0;

  drawStartupCard(c, W * 0.84, H * 0.20, '💳', 'FinTech', 'Teen money app', '#4A90D9', clamp(cardBaseT, 0, 1), selectedT > 0.5);
  drawStartupCard(c, W * 0.84, H * 0.40, '🌾', 'AgriTech', 'Farmer marketplace', '#66BB6A', clamp(cardBaseT - 0.3, 0, 1), false);
  drawStartupCard(c, W * 0.84, H * 0.60, '🧠', 'HealthTech', 'AI wellness chatbot', '#ce93d8', clamp(cardBaseT - 0.6, 0, 1), false);

  // Camera
  if (timeline[0] && elapsed < timeline[0].endSec) camera.focusOn(W * 0.05, 0, 1.02);
  else if (timeline[1] && elapsed < timeline[1].endSec) camera.focusOn(W * 0.1, 0, 1.01);
  else if (timeline[2] && elapsed < timeline[2].endSec) camera.focusOn(-W * 0.05, 0, 1.0);
  else camera.focusOn(0, 0, 1.0);

  if (t > 0.1) showSubtitle('🚀 Entrepreneurship — Workshop Mode');
}
```

- [ ] **Step 4: Add sortAndDrawChars helper** (if not already present from Video A)

```javascript
function sortAndDrawChars(c, chars) {
  chars.sort((a, b) => a.z - b.z);
  chars.forEach(ch => ch.draw(c));
}
```

- [ ] **Step 5: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: add Scenes 1-3 (Intro + Monday workshops)"
```

---

### Task 8: Scene 4 — Negotiation Hero Scene

**Files:**
- Modify: `video-output/walkthrough/mentomap_walkthrough.html`

- [ ] **Step 1: Add Scene 4 — Negotiation Game Demo**

This is the longest and most complex scene (~90s). It has two phases: setup dialogue (lines 0-1) and animated gameplay (lines 2-5).

```javascript
function drawScene4(c, t, elapsed, timeline) {
  // Negotiation Game Demo — HERO SCENE
  drawBgImage(c, bgImgs[3]); // student_room
  drawSceneBg(c, 0.55);
  drawSceneLighting(c, 'warm');

  // Blue tint for simulation feel
  c.fillStyle = 'rgba(40,60,120,0.08)';
  c.fillRect(0, 0, W, H);

  // Characters
  mento.goto(W * 0.12, H * 0.82, t < 0.01, 0.5);
  mento.update();
  drawMento(c);

  arjun.goto(W * 0.35, H * 0.82, t < 0.01, 0.48);
  arjun.expr = elapsed > (timeline[4]?.startSec || 999) ? 'happy' : 'thinking';
  arjun.update();
  sortAndDrawChars(c, [arjun]);

  // Game monitor — appears after line 1
  const line1End = timeline[1]?.endSec || 10;
  const monitorT = clamp((elapsed - line1End + 1) / 2, 0, 1);
  const monX = W * 0.52, monY = H * 0.08, monW = W * 0.42, monH = H * 0.68;
  const inner = drawGameMonitorLarge(c, monX, monY, monW, monH, monitorT);

  if (inner && monitorT > 0.3) {
    // STEP 1: Scenario text (during line 2)
    const line2Start = timeline[2]?.startSec || 20;
    const scenarioT = clamp((elapsed - line2Start) / 6, 0, 1);
    const scenarioText = "It's the 20th of the month and your wallet is empty again. ₹500 just doesn't stretch. School supplies: ₹200. Transport: ₹150. One outing: ₹200. That's ₹550 for basics alone.";
    drawScenarioText(c, inner.ix, inner.iy + 8, inner.iw, scenarioText, scenarioT);

    // STEP 2: Choice buttons (during line 3)
    const line3Start = timeline[3]?.startSec || 30;
    const choiceT = clamp((elapsed - line3Start) / 4, 0, 1);
    const choices = [
      { label: 'A', text: 'Present specific expenses — show the budget' },
      { label: 'B', text: 'Offer to take on responsibilities in return' },
      { label: 'C', text: 'Ask for a compromise — meet at ₹650' }
    ];
    const selectT = clamp((elapsed - line3Start - 2.5) / 0.5, 0, 1);
    const selectedIdx = selectT > 0.5 ? 1 : -1;
    drawChoiceButtons(c, inner.ix, inner.iy + inner.ih * 0.45, inner.iw - 10, choices, selectedIdx, choiceT);

    // Animated cursor hovering (before selection)
    if (choiceT > 0.3 && selectedIdx < 0) {
      const cursorX = inner.ix + inner.iw * 0.4 + Math.sin(elapsed * 2) * 30;
      const cursorY = inner.iy + inner.ih * 0.55 + Math.cos(elapsed * 1.5) * 15;
      c.font = '16px "Segoe UI"';
      c.fillStyle = '#fff';
      c.fillText('👆', cursorX, cursorY);
    }

    // STEP 3: Skill score badges (during line 4)
    const line4Start = timeline[4]?.startSec || 40;
    const badgeT = clamp((elapsed - line4Start) / 3, 0, 1);
    drawSkillBadgeFloat(c, monX + monW * 0.2, monY - 15, 'Empathy +8', NV, clamp(badgeT, 0, 1));
    drawSkillBadgeFloat(c, monX + monW * 0.5, monY - 25, 'Strategic Thinking +5', '#66BB6A', clamp(badgeT - 0.15, 0, 1));
    drawSkillBadgeFloat(c, monX + monW * 0.8, monY - 15, 'Adaptability +6', '#4A90D9', clamp(badgeT - 0.3, 0, 1));
  }

  // Camera — wide throughout, slight zoom on monitor during gameplay
  if (elapsed > line1End) camera.focusOn(W * 0.08, -H * 0.02, 1.02);
  else camera.focusOn(0, 0, 1.0);

  if (t > 0.05) showSubtitle('🤝 Negotiation — Simulation Mode');
}
```

- [ ] **Step 2: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: add Scene 4 (Negotiation hero scene with animated gameplay)"
```

---

### Task 9: Scenes 5-8 (Results, Ethics, Dashboard, CTA)

**Files:**
- Modify: `video-output/walkthrough/mentomap_walkthrough.html`

- [ ] **Step 1: Add Scene 5 — Skill Results**

```javascript
function drawScene5(c, t, elapsed, timeline) {
  // Skill Results screen
  drawBgImage(c, bgImgs[3]); // student_room
  drawSceneBg(c, 0.70);
  drawSceneLighting(c, 'green');

  // Characters
  mento.goto(W * 0.12, H * 0.82, t < 0.01, 0.5);
  mento.update();
  drawMento(c);

  arjun.goto(W * 0.35, H * 0.82, t < 0.01, 0.48);
  arjun.expr = 'proud';
  arjun.update();
  sortAndDrawChars(c, [arjun]);

  // 8-Dimension Skill Radar
  const radarDims = [
    { name: 'Strategic', value: 72 },
    { name: 'Risk', value: 58 },
    { name: 'Delayed Grat.', value: 65 },
    { name: 'Adaptability', value: 70 },
    { name: 'Resilience', value: 55 },
    { name: 'Empathy', value: 78 },
    { name: 'Growth', value: 62 },
    { name: 'Self-Aware', value: 60 }
  ];
  drawSkillRadar(c, W * 0.68, H * 0.40, 120, radarDims, 1, clamp(t * 2, 0, 1));

  // Leaderboard badge
  const line1Start = timeline[1]?.startSec || 5;
  const badgeT = clamp((elapsed - line1Start) / 2, 0, 1);
  drawLeaderboardBadge(c, W * 0.68, H * 0.78, 'Strategic Thinking', 20, badgeT);

  // Confetti on badge reveal
  if (badgeT > 0.3 && badgeT < 0.35) {
    emitConfetti(W * 0.68, H * 0.75, 15);
  }

  camera.focusOn(0, 0, 1.0);
  if (t > 0.05) showSubtitle('📊 8 Future-Ready Skill Dimensions');
}
```

- [ ] **Step 2: Add Scene 6 — Ethics at Home**

```javascript
function drawScene6(c, t, elapsed, timeline) {
  // Ethics & Teamwork at Home
  drawBgImage(c, bgImgs[3]); // student_room
  drawSceneBg(c, 0.50);
  drawSceneLighting(c, 'warm');

  // Characters
  mento.goto(W * 0.15, H * 0.82, t < 0.01, 0.5);
  mento.update();
  drawMento(c);

  arjun.goto(W * 0.55, H * 0.82, t < 0.01, 0.45);
  arjun.expr = elapsed > (timeline[2]?.startSec || 999) ? 'happy' : 'thinking';
  arjun.update();
  sortAndDrawChars(c, [arjun]);

  // Off-time feature badges — pop in during line 3
  const line3Start = timeline[3]?.startSec || 20;
  const badgeBaseT = (elapsed - line3Start) / 3;
  drawOffTimeBadge(c, W * 0.82, H * 0.20, '🔥', '5-day streak', '#FFA726', clamp(badgeBaseT, 0, 1));
  drawOffTimeBadge(c, W * 0.82, H * 0.32, '🏆', 'Friend challenge', '#FFD700', clamp(badgeBaseT - 0.2, 0, 1));
  drawOffTimeBadge(c, W * 0.82, H * 0.44, '🎁', 'Daily rewards', '#ce93d8', clamp(badgeBaseT - 0.4, 0, 1));
  drawOffTimeBadge(c, W * 0.82, H * 0.56, '📱', '24/7 access', '#4A90D9', clamp(badgeBaseT - 0.6, 0, 1));

  // Camera
  if (timeline[0] && elapsed < timeline[0].endSec) camera.focusOn(0, 0, 1.0);
  else if (timeline[1] && elapsed < timeline[1].endSec) camera.focusOn(W * 0.05, 0, 1.02);
  else camera.focusOn(0, 0, 1.0);

  if (t > 0.1) showSubtitle('⚖️ Ethics & Teamwork — Off-Time Play');
}
```

- [ ] **Step 3: Add Scene 7 — Principal Dashboard**

```javascript
function drawScene7(c, t, elapsed, timeline) {
  // The Bigger Picture — Principal's office
  drawBgImage(c, bgImgs[1]); // principal_office
  drawSceneBg(c, 0.55);
  drawSceneLighting(c, 'warm');

  // Characters
  mento.goto(W * 0.18, H * 0.82, t < 0.01, 0.5);
  mento.update();
  drawMento(c);

  sharma.goto(W * 0.72, H * 0.82, t < 0.01, 0.5);
  sharma.expr = elapsed > (timeline[0]?.endSec || 999) ? 'happy' : 'neutral';
  sharma.update();
  sortAndDrawChars(c, [sharma]);

  // Dashboard panels — appear during line 0-1
  const line0Start = timeline[0]?.startSec || 0;
  const panelT = (elapsed - line0Start) / 6;
  drawDashboardPanel(c, W * 0.35, H * 0.55, W * 0.30, 55, 'progress9month', clamp(panelT, 0, 1));
  drawDashboardPanel(c, W * 0.35, H * 0.62, W * 0.30, 95, 'skillgrid', clamp(panelT - 0.2, 0, 1));

  // NEP badge — appears on line 2
  const line2Start = timeline[2]?.startSec || 15;
  const nepT = clamp((elapsed - line2Start) / 2, 0, 1);
  drawDashboardPanel(c, W * 0.42, H * 0.82, 150, 35, 'nep', nepT);

  // Camera
  if (timeline[0] && elapsed < timeline[0].endSec) camera.focusOn(0, 0, 1.0);
  else if (timeline[1] && elapsed < timeline[1].endSec) camera.focusOn(W * 0.08, 0, 1.02);
  else camera.focusOn(0, 0, 1.0);

  if (t > 0.1) showSubtitle('📊 Principal Dashboard — Track Every Skill');
}
```

- [ ] **Step 4: Add Scene 8 — CTA**

```javascript
function drawScene8(c, t, elapsed, timeline) {
  // CTA — All characters together
  drawBgImage(c, bgImgs[4]); // school_courtyard
  drawSceneBg(c, 0.40);
  drawSceneLighting(c, 'triumph');

  // All 4 characters
  mento.goto(W * 0.5, H * 0.78, t < 0.01, 0.6);
  mento.update();
  drawMento(c);

  sharma.goto(W * 0.22, H * 0.82, t < 0.01, 0.5);
  sharma.expr = 'proud';
  sharma.update();

  priya.goto(W * 0.38, H * 0.82, t < 0.01, 0.5);
  priya.expr = 'happy';
  priya.update();

  arjun.goto(W * 0.62, H * 0.82, t < 0.01, 0.45);
  arjun.expr = 'happy';
  arjun.update();

  sortAndDrawChars(c, [sharma, priya, arjun]);

  // Confetti
  if (t > 0.3 && t < 0.5 && Math.random() < 0.15) {
    emitConfetti(W / 2, H * 0.3, 3);
  }

  // CTA button
  if (t > 0.5) {
    drawCTA(c, W / 2, H * 0.55, 'Adopt MentoMap \u2192 mentomap.in', ss(0.5, 0.7, t));
  }

  if (t > 0.4) showSubtitle('9 Months. 9 Subjects. Grades 6\u20148. One Complete Curriculum.');

  // End card
  if (t > 0.8) {
    const fadeT = ss(0.8, 1.0, t);
    c.fillStyle = `rgba(0,0,0,${Math.min(fadeT * 1.8, 0.97)})`;
    c.fillRect(0, 0, W, H);
    if (fadeT > 0.3 && Math.random() < 0.08) {
      emitParticle(Math.random() * W, -5, (Math.random()-0.5)*0.3, 0.4 + Math.random()*0.5, 200, 1.5, '#FFD180', 'glow', 0.01);
    }
    if (fadeT > 0.3) {
      c.globalAlpha = Math.min((fadeT - 0.3) * 1.5, 1);
      if (mentoLoaded) {
        const mentoEndW = 60;
        const mentoEndH = (mentoImg.height / mentoImg.width) * mentoEndW;
        c.drawImage(mentoImg, W/2 - mentoEndW/2, H/2 - 75 - mentoEndH, mentoEndW, mentoEndH);
      }
      c.font = 'bold 42px "Segoe UI"';
      c.fillStyle = '#FFB347';
      c.textAlign = 'center';
      c.fillText('MentoMap', W/2, H/2 - 20);
      c.font = '18px "Segoe UI"';
      c.fillStyle = '#cc9960';
      c.fillText('hello@mentomap.in  \u00B7  mentomap.in', W/2, H/2 + 20);
      c.font = '15px "Segoe UI"';
      c.fillStyle = '#9a8060';
      c.fillText('Future Skills for Every Student', W/2, H/2 + 48);
      c.textAlign = 'left';
      c.globalAlpha = 1;
    }
  }

  camera.focusOn(0, 0, t > 0.5 ? 1.02 : 1.0);
}
```

- [ ] **Step 5: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: add Scenes 5-8 (Results, Ethics, Dashboard, CTA)"
```

---

### Task 10: Day Card Scenes + Timeline Assembly + Main Loop

**Files:**
- Modify: `video-output/walkthrough/mentomap_walkthrough.html`

- [ ] **Step 1: Add day card scene wrappers**

Day cards are treated as mini-scenes (5 seconds each) in the scene array:

```javascript
function drawDayCardMonday(c, t, elapsed, timeline) {
  drawDayCard(c, 'Monday', 'Workshop Day', '#66BB6A', t);
}
function drawDayCardWednesday(c, t, elapsed, timeline) {
  drawDayCard(c, 'Wednesday', 'Simulation Day', '#4A90D9', t);
}
function drawDayCardSaturday(c, t, elapsed, timeline) {
  drawDayCard(c, 'Saturday', 'Off-Time Play', '#FFA726', t);
}
```

- [ ] **Step 2: Define all scene timelines**

Insert at the `// ===== SCENE TIMELINES` placeholder:

```javascript
// ===== SCENE TIMELINES =====

// Day card scenes have no dialogue — empty timelines
const dayCardTimeline = [];

// Scene 1: Intro
const s1d = buildTimeline([
  { char: mento, charName: 'Mento', text: "Remember me? Last time I showed you what MentoMap is. Today, let me show you what a real week looks like.", bubbleX: 0.5, bubbleY: 0.25, side: 'center' },
  { char: arjun, charName: 'Arjun', text: "I'm Arjun, Grade 7. This week we're doing Financial Literacy and Entrepreneurship!", bubbleX: 0.65, bubbleY: 0.25, side: 'right' },
  { char: mento, charName: 'Mento', text: "Let's follow his journey \u2014 three days, three learning modes.", bubbleX: 0.35, bubbleY: 0.25, side: 'left' }
]);

// Scene 2: Financial Literacy
const s2d = buildTimeline([
  { char: mento, charName: 'Mento', text: "It's Monday morning. Teacher Priya has something special for the class.", bubbleX: 0.20, bubbleY: 0.20, side: 'left' },
  { char: priya, charName: 'Priya', text: "Today's challenge: You've inherited a lemonade recipe and \u20B9500. Build a business!", bubbleX: 0.55, bubbleY: 0.20, side: 'right' },
  { char: arjun, charName: 'Arjun', text: "We had to pick a location, buy inventory, and set prices \u2014 all with real trade-offs!", bubbleX: 0.75, bubbleY: 0.25, side: 'right' },
  { char: mento, charName: 'Mento', text: "Inventory management, pricing strategy, break-even point \u2014 real business concepts, learned through play.", bubbleX: 0.20, bubbleY: 0.20, side: 'left' }
]);

// Scene 3: Entrepreneurship
const s3d = buildTimeline([
  { char: priya, charName: 'Priya', text: "Now the big one \u2014 you each have \u20B95 lakhs. Pick a startup idea and pitch it!", bubbleX: 0.48, bubbleY: 0.20, side: 'right' },
  { char: arjun, charName: 'Arjun', text: "I chose a money management app for teenagers \u2014 my aunt confirmed it's a real pain point!", bubbleX: 0.72, bubbleY: 0.25, side: 'right' },
  { char: mento, charName: 'Mento', text: "MVP, burn rate, runway \u2014 not just vocabulary, but decisions they have to live with.", bubbleX: 0.20, bubbleY: 0.20, side: 'left' },
  { char: priya, charName: 'Priya', text: "Two subjects in one morning \u2014 and they don't even realize they're learning!", bubbleX: 0.48, bubbleY: 0.20, side: 'right' }
]);

// Scene 4: Negotiation (hero — extra buffer for gameplay animation)
const s4d = buildTimeline([
  { char: mento, charName: 'Mento', text: "Wednesday afternoon. Arjun logs into MentoMap for a negotiation simulation.", bubbleX: 0.20, bubbleY: 0.18, side: 'left' },
  { char: arjun, charName: 'Arjun', text: "This one's called 'The Pocket Money Talk' \u2014 I have to convince Amma to raise my allowance from \u20B9500 to \u20B9800!", bubbleX: 0.38, bubbleY: 0.18, side: 'left' },
  { char: mento, charName: 'Mento', text: "Watch \u2014 the scenario appears, and Arjun reads the situation.", bubbleX: 0.20, bubbleY: 0.80, side: 'left' },
  { char: mento, charName: 'Mento', text: "Three choices. Each one measures different skills. No right or wrong \u2014 strategic or impulsive.", bubbleX: 0.20, bubbleY: 0.80, side: 'left' },
  { char: mento, charName: 'Mento', text: "Watch his empathy score \u2014 offering responsibilities shows maturity.", bubbleX: 0.20, bubbleY: 0.80, side: 'left' },
  { char: arjun, charName: 'Arjun', text: "Amma actually agreed to \u20B9700 \u2014 and I'm doing the dishes now!", bubbleX: 0.38, bubbleY: 0.80, side: 'left' }
]);

// Scene 5: Skill Results
const s5d = buildTimeline([
  { char: mento, charName: 'Mento', text: "After each game, students see exactly how their skills are growing.", bubbleX: 0.20, bubbleY: 0.18, side: 'left' },
  { char: arjun, charName: 'Arjun', text: "I'm in the top 20% for strategic thinking! And my empathy score jumped 15 points!", bubbleX: 0.38, bubbleY: 0.18, side: 'left' }
]);

// Scene 6: Ethics at Home
const s6d = buildTimeline([
  { char: mento, charName: 'Mento', text: "Saturday evening. Arjun's playing 'The Ethics Hotline' at home \u2014 his school's ethics reporting system needs him.", bubbleX: 0.22, bubbleY: 0.20, side: 'left' },
  { char: arjun, charName: 'Arjun', text: "A student copied Neha's homework and the teacher blamed Neha! I have the evidence \u2014 but do I go to the teacher or the principal?", bubbleX: 0.58, bubbleY: 0.20, side: 'right' },
  { char: mento, charName: 'Mento', text: "No right answer \u2014 every choice has trade-offs. That's what builds ethical reasoning.", bubbleX: 0.22, bubbleY: 0.20, side: 'left' },
  { char: arjun, charName: 'Arjun', text: "My mom thinks I'm just playing games... but I'm learning how to handle real situations!", bubbleX: 0.58, bubbleY: 0.20, side: 'right' }
]);

// Scene 7: Principal Dashboard
const s7d = buildTimeline([
  { char: mento, charName: 'Mento', text: "And here's what principals see \u2014 every student, every skill, every month.", bubbleX: 0.25, bubbleY: 0.20, side: 'left' },
  { char: sharma, charName: 'Sharma', text: "For the first time, I can see my students growing in ways exams never measured.", bubbleX: 0.72, bubbleY: 0.20, side: 'right' },
  { char: mento, charName: 'Mento', text: "9 months. 9 subjects. All aligned with NEP 2020. No new teachers needed.", bubbleX: 0.25, bubbleY: 0.20, side: 'left' }
]);

// Scene 8: CTA
const s8d = buildTimeline([
  { char: mento, charName: 'Mento', text: "One week. Three modes. Skills that last a lifetime. Start your school's MentoMap journey.", bubbleX: 0.5, bubbleY: 0.18, side: 'center' }
]);
```

- [ ] **Step 3: Assemble scene arrays**

```javascript
// ===== SCENE ASSEMBLY =====

const DAY_CARD_DUR = 5;
const sceneTimelines = [s1d, dayCardTimeline, s2d, s3d, dayCardTimeline, s4d, s5d, dayCardTimeline, s6d, s7d, s8d];
const sceneDraws = [drawScene1, drawDayCardMonday, drawScene2, drawScene3, drawDayCardWednesday, drawScene4, drawScene5, drawDayCardSaturday, drawScene6, drawScene7, drawScene8];
const sceneTitles = ['Remember Me?', 'Monday', 'Financial Literacy', 'Entrepreneurship', 'Wednesday', 'Negotiation Demo', 'Skill Results', 'Saturday', 'Ethics at Home', 'Principal Dashboard', 'Start Your Journey'];

// Scene 4 (negotiation, index 5) gets extra buffer for gameplay animation
const sceneDurs = sceneTimelines.map((tl, i) => {
  if (i === 1 || i === 4 || i === 7) return DAY_CARD_DUR; // Day cards
  if (i === 5) return sceneDuration(tl, 5); // Hero scene extra buffer
  return sceneDuration(tl, 1.5);
});

const sceneStarts = [];
let cumTime = 0;
for (let i = 0; i < sceneDurs.length; i++) {
  sceneStarts.push(cumTime);
  cumTime += sceneDurs[i];
}
const TOTAL = cumTime;

const sceneSubtitles = ['', '', '', '', '', '', '', '', '', '', ''];
```

- [ ] **Step 4: Update main loop for day card scenes**

In the main loop, the fadeOut transition skip for the last scene needs to use the correct index (10 instead of 5):

```javascript
// Scene-level fadeOut: skip for last scene (Scene 8 = index 10) which has its own end card
if (elapsed > fadeOutStart && sceneIdx < sceneDraws.length - 1) {
```

Also update the global end fade:
```javascript
if (filmTime > TOTAL - 3 && sceneIdx < sceneDraws.length - 1) {
```

- [ ] **Step 5: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: add timelines, scene assembly, and day card wrappers"
```

---

### Task 11: Visual Test + Record Video

**Files:**
- No new files created

- [ ] **Step 1: Start preview server and visually verify all scenes**

```bash
/opt/homebrew/bin/python3 video-output/walkthrough/serve.py 8766
```

Open `http://localhost:8766/mentomap_walkthrough.html` and verify:
1. Start overlay shows "A Week with MentoMap"
2. Scene 1: Mento + Arjun at school entrance, dialogue plays
3. Day card: "Monday — Workshop Day" with green header
4. Scene 2: Classroom, workshop cards pop in with lemonade data
5. Scene 3: Startup idea cards, FinTech gets green check
6. Day card: "Wednesday — Simulation Day" with blue header
7. Scene 4: Game monitor appears, scenario text types, choices appear, Arjun selects B, skill badges pop
8. Scene 5: Skill radar fills in, leaderboard badge with confetti
9. Day card: "Saturday — Off-Time Play" with amber header
10. Scene 6: Ethics scenario, off-time feature badges
11. Scene 7: Dashboard panels with progress bar and skill grid
12. Scene 8: All characters, confetti, CTA, end card
13. Transitions between all scenes are smooth cross-fades
14. Total duration is approximately 7 minutes

- [ ] **Step 2: Fix any visual issues found during testing**

Common issues to check:
- Character positions don't overlap with custom elements
- Dialogue bubbles are readable and don't clip off-screen
- Day cards don't get cut off by scene transitions
- Game monitor in Scene 4 has enough space for all content
- End card appears without being covered by fade overlays

- [ ] **Step 3: Record the video**

```bash
cd video-output/walkthrough
export PATH="/opt/homebrew/bin:$PATH"
node record.js
```

Expected: `mentomap_walkthrough.webm` saved (~7 min video).

- [ ] **Step 4: Convert to MP4**

```bash
/opt/homebrew/bin/ffmpeg -y -i mentomap_walkthrough.webm -c:v libx264 -crf 20 -preset medium -movflags +faststart mentomap_walkthrough.mp4
```

Expected: `mentomap_walkthrough.mp4` (~15-25MB, 1920x1080, ~7 min).

- [ ] **Step 5: Verify MP4 properties**

```bash
/opt/homebrew/bin/ffprobe -v quiet -show_format -show_streams mentomap_walkthrough.mp4 2>&1 | grep -E 'duration|width|height|codec_name'
```

Expected: `width=1920`, `height=1080`, `codec_name=h264`, `duration=~435` (7:15).

- [ ] **Step 6: Commit**

```bash
git add video-output/walkthrough/mentomap_walkthrough.html
git commit -m "feat: complete walkthrough video (Video B) — tested and recorded"
```

---

## Self-Review

**Spec coverage:**
- Scene 1 (Intro): ✅ Task 7
- Day card transitions: ✅ Tasks 3, 10
- Scene 2 (Financial Literacy): ✅ Task 7 (with Lemonade Empire data)
- Scene 3 (Entrepreneurship): ✅ Task 7 (with Startup Pitch Battle data)
- Scene 4 (Negotiation hero): ✅ Task 8 (with Pocket Money Talk data, animated gameplay)
- Scene 5 (Skill results): ✅ Task 9 (with 8-dim radar + leaderboard)
- Scene 6 (Ethics at home): ✅ Task 9 (with Ethics Hotline data + off-time badges)
- Scene 7 (Principal dashboard): ✅ Task 9 (with progress bar + skill grid + NEP badge)
- Scene 8 (CTA + end card): ✅ Task 9
- All 12 new custom drawing functions: ✅ Tasks 3-6
- Recording pipeline: ✅ Tasks 1, 11
- Framework reuse from Video A: ✅ Task 2

**Placeholder scan:** No TBDs, TODOs, or placeholders found. All code is complete.

**Type consistency:** Function names match between definition (Tasks 3-6) and usage (Tasks 7-9): `drawDayCard`, `drawWorkshopCard`, `drawStartupCard`, `drawGameMonitorLarge`, `drawScenarioText`, `drawChoiceButtons`, `drawSkillBadgeFloat`, `drawSkillRadar`, `drawLeaderboardBadge`, `drawOffTimeBadge`, `drawDashboardPanel`. All parameter orders are consistent.
