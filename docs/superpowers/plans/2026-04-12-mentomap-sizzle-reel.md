# MentoMap Sizzle Reel Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 2-3 minute animated explainer video for MentoMap's curriculum, rendered as a single-file HTML5 Canvas application following the Animated Video Production Framework.

**Architecture:** Single HTML file containing all CSS, HTML, and JavaScript. Canvas 2D renders cartoon characters (Person class), the Mento mascot (image sprite), illustrated backgrounds (loaded JPGs), speech bubbles with typewriter text, and particle effects. 6 scenes played sequentially with fade transitions. In-browser MediaRecorder captures WebM for export.

**Tech Stack:** HTML5 Canvas 2D, Web Audio API (pre-wired for future ElevenLabs), MediaRecorder API, requestAnimationFrame, Playwright (recording automation)

**Spec:** `docs/superpowers/specs/2026-04-12-mentomap-intro-video-design.md`
**Framework Reference:** `Animated_Video_Production_Framework.md`
**Mento Asset:** `MentoCharacter.jpeg`

---

## File Structure

```
video-output/sizzle-reel/
  mentomap_sizzle.html          # Complete single-file video application
  images/
    MentoCharacter.jpeg         # Mento mascot sprite (copied from project root)
    school_entrance.jpg         # Scene 1 BG (placeholder → replace with AI-generated)
    principal_office.jpg        # Scene 2 BG
    classroom.jpg               # Scene 3-4 BG
    student_room.jpg            # Scene 5 BG
    school_courtyard.jpg        # Scene 6 BG
  audio/                        # Empty — ElevenLabs MP3s added later
  record.js                     # Playwright automated recording script
```

All video logic lives in `mentomap_sizzle.html`. Background images start as canvas-generated placeholders (drawn and exported to JPG via a helper script), replaceable with AI-generated art later.

---

### Task 1: Project Scaffolding

**Files:**
- Create: `video-output/sizzle-reel/images/` (directory)
- Create: `video-output/sizzle-reel/audio/` (directory)
- Copy: `MentoCharacter.jpeg` → `video-output/sizzle-reel/images/MentoCharacter.jpeg`
- Create: `video-output/sizzle-reel/generate_placeholders.html` (helper to generate placeholder BGs)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p /Users/amajumder/Downloads/MentoApp/video-output/sizzle-reel/images
mkdir -p /Users/amajumder/Downloads/MentoApp/video-output/sizzle-reel/audio
```

- [ ] **Step 2: Copy Mento asset**

```bash
cp /Users/amajumder/Downloads/MentoApp/MentoCharacter.jpeg /Users/amajumder/Downloads/MentoApp/video-output/sizzle-reel/images/MentoCharacter.jpeg
```

- [ ] **Step 3: Create placeholder background generator**

Create `video-output/sizzle-reel/generate_placeholders.html` — a helper page that draws 5 illustrated-style placeholder backgrounds on canvases and provides download links. Each background uses warm gradients, simple geometric shapes (rectangles for desks/shelves, circles for trees/sun), and text labels so scenes are testable before real art is ready.

The file draws these 5 backgrounds at 1920x1080:
1. **school_entrance.jpg** — blue sky gradient, green ground, orange building rectangle, "MentoMap School" text, tree circles, sun circle
2. **principal_office.jpg** — warm brown gradient, desk rectangle, bookshelf rectangles, window rectangle with sky, certificate rectangles
3. **classroom.jpg** — cream walls, green chalkboard rectangle, desk rows, window rectangles, colorful poster rectangles
4. **student_room.jpg** — warm gradient, desk rectangle, monitor rectangle with glow, book rectangles, poster circles
5. **school_courtyard.jpg** — golden hour gradient (orange/yellow sky), building silhouette, tree circles, ground

Each canvas has a "Download" button that saves as JPG. Page instructions: "Open this file in Chrome, click each Download button, save to the images/ folder."

- [ ] **Step 4: Open the generator in a browser and save all 5 placeholder images**

Open `generate_placeholders.html` in Chrome. Click each download button. Save files to `video-output/sizzle-reel/images/` with the exact filenames:
- `school_entrance.jpg`
- `principal_office.jpg`
- `classroom.jpg`
- `student_room.jpg`
- `school_courtyard.jpg`

- [ ] **Step 5: Verify all files exist**

```bash
ls -la /Users/amajumder/Downloads/MentoApp/video-output/sizzle-reel/images/
```

Expected: 6 files (MentoCharacter.jpeg + 5 placeholder JPGs)

---

### Task 2: HTML Skeleton + CSS + Canvas Setup

**Files:**
- Create: `video-output/sizzle-reel/mentomap_sizzle.html`

This task creates the HTML file with: DOCTYPE, CSS (UI bar, subtitle, letterbox, start overlay), canvas element, UI controls, and start overlay. No JavaScript yet — just the visual shell.

- [ ] **Step 1: Create the HTML file with full CSS and DOM structure**

Create `video-output/sizzle-reel/mentomap_sizzle.html` with:
- `<title>MentoMap — Future Skills Curriculum</title>`
- CSS from framework template Section 15 with brand colors replaced:
  - `BRAND_PRIMARY` → `#FFB347`
  - `BRAND_DARK` → `#E08A1E`
  - `BRAND_LIGHT` → `#FFD180`
  - `BRAND_R,BRAND_G,BRAND_B` → `255,179,71`
  - Button text color: `#FFD180` instead of `#a0c060`
- Canvas element `<canvas id="c"></canvas>`
- Subtitle div `<div id="sub"></div>`
- Letterbox bars (top + bottom)
- Start overlay with:
  - Organization: "MENTOMAP"
  - Title: "Future Skills Curriculum"
  - Tagline: "Grades 6, 7 & 8 — Workshops, Simulations, Off-Time Learning"
  - Play button circle + "Click to Play"
- UI controls bar: play/pause, progress bar, time label, scene label, voice toggle, restart, record button
- Empty `<script>` tag ready for JavaScript

- [ ] **Step 2: Verify in browser**

Open the HTML file in Chrome. Expected: black page with the start overlay showing "MENTOMAP" / "Future Skills Curriculum" / play button in orange theme. UI bar visible at bottom.

---

### Task 3: Core Engine Utilities

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (add to `<script>`)

Add all core utility functions inside the `<script>` tag.

- [ ] **Step 1: Add canvas setup + brand constants**

```javascript
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
let W, H;
function resize() { W = cv.width = innerWidth; H = cv.height = innerHeight; }
resize(); addEventListener('resize', resize);

const NV = '#FFB347', NVD = '#E08A1E', NVL = '#FFD180';
const CHAR_SCALE = 3.5;
```

- [ ] **Step 2: Add math/easing utilities**

```javascript
function clamp(v, mn, mx) { return Math.max(mn, Math.min(mx, v)); }
function lerp(a, b, t) { return a + (b - a) * t; }
function ss(a, b, t) { return clamp((t - a) / (b - a), 0, 1); }
function hexRGBA(hex, a) {
  const r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return `rgba(${r},${g},${b},${a})`;
}
function rr(c, x, y, w, h, r) {
  c.beginPath();
  c.moveTo(x+r, y);
  c.lineTo(x+w-r, y); c.quadraticCurveTo(x+w, y, x+w, y+r);
  c.lineTo(x+w, y+h-r); c.quadraticCurveTo(x+w, y+h, x+w-r, y+h);
  c.lineTo(x+r, y+h); c.quadraticCurveTo(x, y+h, x, y+h-r);
  c.lineTo(x, y+r); c.quadraticCurveTo(x, y, x+r, y);
  c.closePath();
}
const ease = {
  out: t => 1 - Math.pow(1 - t, 3),
  inOut: t => t < 0.5 ? 4*t*t*t : 1 - Math.pow(-2*t+2,3)/2,
  elastic: t => {
    if (t === 0 || t === 1) return t;
    return Math.pow(2, -10*t) * Math.sin((t - 0.075) * (2*Math.PI) / 0.3) + 1;
  }
};
```

- [ ] **Step 3: Add word-wrap utility for speech bubbles**

```javascript
function wordWrap(text, maxW, font) {
  ctx.font = font;
  const words = text.split(' ');
  const lines = [];
  let line = '';
  for (const w of words) {
    const test = line ? line + ' ' + w : w;
    if (ctx.measureText(test).width > maxW && line) {
      lines.push(line);
      line = w;
    } else {
      line = test;
    }
  }
  if (line) lines.push(line);
  return lines;
}
```

- [ ] **Step 4: Verify — open in browser, check console for no errors**

Open in Chrome with DevTools console. Expected: no errors. Canvas fills the screen black.

---

### Task 4: Camera System + Background System

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Add camera system**

Add the complete camera object from framework Section 7.1 — `focusOn()`, `reset()`, `shake()`, `update()`, `apply()`, `restore()` methods. Use lerp rate 0.04 for smooth movement.

- [ ] **Step 2: Add background image loading system**

```javascript
const bgImgs = {};
function loadBg(key, url) {
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.src = url;
  img.onload = () => { bgImgs[key] = img; };
  img.onerror = () => console.warn('BG not found: ' + url);
}

// Preload all scene backgrounds
loadBg('entrance', 'images/school_entrance.jpg');
loadBg('office', 'images/principal_office.jpg');
loadBg('classroom', 'images/classroom.jpg');
loadBg('studentroom', 'images/student_room.jpg');
loadBg('courtyard', 'images/school_courtyard.jpg');
```

- [ ] **Step 3: Add background rendering functions**

Add `drawBgImage(c, key, darken, yShift)` from framework Section 4.2 — cover-fit image to canvas with darken overlay.

Add `drawSceneBg(c, type, floorPct)` from framework Section 4.3 — draws background image + ground plane gradient + floor line.

Add `drawStars(c)` — simple ambient particle dots (random positions, small white dots with low opacity).

- [ ] **Step 4: Add lighting and vignette functions**

Add `drawSceneLighting(c, type, t)` from framework Section 4.4 — supports 'warm', 'cool', 'green', 'triumph' types. Modify brand color references from `#76B900` to `#FFB347` (MentoMap orange).

Add `drawVignette(c, intensity)` from framework Section 4.5.

- [ ] **Step 5: Verify — temporarily draw a background in a test loop**

Add temporary test code at bottom of script:
```javascript
// TEMP TEST — remove later
function testDraw() {
  ctx.clearRect(0, 0, W, H);
  drawSceneBg(ctx, 'entrance', 0.82);
  drawSceneLighting(ctx, 'warm', 1);
  requestAnimationFrame(testDraw);
}
requestAnimationFrame(testDraw);
```

Open in browser. Expected: school entrance background with warm lighting visible. Remove test code after verifying.

---

### Task 5: Particle System + Transition System

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Add particle pool system**

Add from framework Section 8.1-8.2:
- `MAX_PARTICLES = 400` pool array
- `emitParticle()` function
- `emitBurst()` function
- `emitConfetti()` function — modify colors to include MentoMap orange: `['#FFB347','#FFD180','#ff6b6b','#ffd93d','#6bcb77','#4d96ff']`

- [ ] **Step 2: Add particle update and draw functions**

```javascript
function updateParticles(dt) {
  for (const p of particles) {
    if (p.life <= 0) continue;
    p.life--;
    p.x += p.vx;
    p.y += p.vy;
    p.vy += p.gravity;
    p.rotation += p.rotSpeed;
    p.alpha = p.life / p.maxLife;
  }
}

function drawParticles(c) {
  for (const p of particles) {
    if (p.life <= 0) continue;
    c.globalAlpha = p.alpha * 0.8;
    c.fillStyle = p.color;
    if (p.type === 'dot') {
      c.beginPath(); c.arc(p.x, p.y, p.size, 0, Math.PI*2); c.fill();
    } else if (p.type === 'glow') {
      const g = c.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size*3);
      g.addColorStop(0, p.color); g.addColorStop(1, 'rgba(0,0,0,0)');
      c.fillStyle = g;
      c.fillRect(p.x - p.size*3, p.y - p.size*3, p.size*6, p.size*6);
    } else if (p.type === 'rect') {
      c.save(); c.translate(p.x, p.y); c.rotate(p.rotation);
      c.fillRect(-p.size, -p.size/2, p.size*2, p.size);
      c.restore();
    } else if (p.type === 'data') {
      c.font = (p.size*4) + 'px monospace';
      c.fillText(Math.random() < 0.5 ? '0' : '1', p.x, p.y);
    }
    c.globalAlpha = 1;
  }
}
```

- [ ] **Step 3: Add transition system**

```javascript
const FADE = 1.2;
const prevCanvas = document.createElement('canvas');

function capturePrevFrame() {
  prevCanvas.width = W;
  prevCanvas.height = H;
  prevCanvas.getContext('2d').drawImage(cv, 0, 0);
}
```

---

### Task 6: Person Class (Character Renderer)

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

This is the largest single component. The Person class draws cartoon-style characters with animated eyes, mouths, hair, clothing, and accessories.

- [ ] **Step 1: Add Person class constructor + movement + expression methods**

Add the Person class with:
- Constructor from framework Section 5.1 (all appearance properties, position/movement state, animation state)
- `goto(x, y, instant, z)` method from Section 5.2
- `stepForward()`, `stepBack()`, `stepCenter()` depth presets
- `setExpr(e)` expression setter with smooth transition
- `update()` method from Section 5.3 (position lerp, breathing, talking, expression transition, eye gaze, blink state machine)

- [ ] **Step 2: Add Person draw method — body parts**

Add the `draw(c)` method to Person class. This is the core visual renderer. Drawing order (bottom to top from feet anchor):

1. **Shadow** — dark ellipse on ground at foot position
2. **Shoes** — two ellipses with specular highlight
3. **Pants** — two lines with stroke
4. **Torso** — quadratic curve shape with gradient fill, collar line if `hasCollar`, tie if `hasTie`, badge circle if `hasBadge`
5. **Arms** — default pose: two curved lines hanging at sides. Support poses: 'default', 'pointing'
6. **Head** — circle with 3D gradient (lighter top-left), specular highlight, rim light
7. **Hair** — style-dependent: 'short' (arc on top), 'long' (curves down sides for female), 'curly' (bumpy arc), 'slick' (flat arc), 'side' (asymmetric)
8. **Ears** — small circles on sides of head
9. **Eyes** — expression-dependent ovals/arcs. Blink state controls eye height. Gaze shifts pupil position. Expressions: neutral (normal ovals), happy (upward arcs), thinking (squinted), stressed (wide+small pupils), serious (narrow), surprised (very large), worried (wide), confident (curved up), proud (curved up+blush), relieved (curved up+blush)
10. **Eyebrows** — expression-dependent lines/arcs above eyes
11. **Mouth** — when talking: ellipse sized by `mouthAmp` for lip-sync. When silent: expression-dependent (line, smile arc, tight line, open O, wavy)
12. **Nose** — small curve/line
13. **Glasses** — if `hasGlasses`: 'rect' (two rectangles + bridge) or 'round' (two circles + bridge)
14. **Beard** — if `hasBeard`: arc below mouth
15. **Earring** — if `hasEarring`: small circle below ear
16. **Name label** — character name rendered below feet, fixed size, clamped to viewport

All measurements relative to `CHAR_SCALE * zScale * this.sc`. Anchor point is at feet (`this.x, this.y`), character grows upward.

Key scaling: `zScale = 0.75 + this.z * 0.5`, applied to all measurements. `zAlpha = 0.7 + this.z * 0.3` for depth-based opacity.

Breathing animation: torso/head bob via `Math.sin(this.breathe) * 1.5`.

- [ ] **Step 3: Add Z-sorted character renderer**

```javascript
function drawCharsSorted(c, chars) {
  const sorted = [...chars].sort((a, b) => a.z - b.z);
  sorted.forEach(ch => { ch.update(); ch.draw(c); });
}
```

- [ ] **Step 4: Verify — create a test Person and draw it**

Temporary test:
```javascript
const testChar = new Person({
  name: 'Test', role: 'Tester', skin: '#d4a574', hairColor: '#1a1a2e',
  hairStyle: 'short', shirtColor: '#2a5a8c', accentColor: '#4a9eff'
});
testChar.goto(W/2, H*0.82, true, 0.5);
// In test draw loop: drawCharsSorted(ctx, [testChar]);
```

Open in browser. Expected: cartoon character visible on background. Remove test code after verifying.

---

### Task 7: Dialogue System

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Add speech bubble renderer**

Add `drawDialogue(c, x, y, speaker, text, maxW, color, alpha, tailSide, revealPct, scalePop)` from framework Section 6.1.

Key customizations for MentoMap:
- Bubble background gradient: `rgba(15,10,5,.93)` to `rgba(8,5,3,.93)` (warmer dark tone)
- Inner glow uses character accent color
- Font: `'20px "Segoe UI"'` for dialogue text
- Speaker name font: `'bold 17px "Segoe UI"'`
- Text color: `#f0e8d8` (warm cream instead of green-tinted)
- Blinking cursor in accent color

- [ ] **Step 2: Add subtitle bar functions**

```javascript
const sub = document.getElementById('sub');
function showSubtitle(text) { sub.textContent = text; sub.classList.add('on'); }
function hideSubtitle() { sub.classList.remove('on'); }
```

- [ ] **Step 3: Verify — draw a test speech bubble**

Temporary test in draw loop:
```javascript
drawDialogue(ctx, W*0.5, H*0.3, 'Mento', 'What if your school could teach skills no textbook covers?', 380, '#FFB347', 1, 'center', 0.7, 1);
```

Open in browser. Expected: dark speech bubble with orange border, typewriter text partially revealed. Remove test code.

---

### Task 8: Mento Sprite System

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Add Mento image loader**

```javascript
const mentoImg = new Image();
mentoImg.crossOrigin = 'anonymous';
mentoImg.src = 'images/MentoCharacter.jpeg';
let mentoLoaded = false;
mentoImg.onload = () => { mentoLoaded = true; };
```

- [ ] **Step 2: Add Mento draw function**

```javascript
// Mento state (mirrors Person interface for positioning)
const mento = {
  x: 0, tx: 0, y: 0, ty: 0, z: 0.5, tz: 0.5, sc: 1, op: 1, talking: false,
  name: 'Mento', accentColor: '#FFB347',
  goto(x, y, instant, z) {
    this.tx = x; this.ty = y;
    if (z !== undefined) this.tz = z;
    if (instant) { this.x = x; this.y = y; this.z = z || this.z; }
  },
  update() {
    this.x += (this.tx - this.x) * 0.06;
    this.y += (this.ty - this.y) * 0.06;
    this.z += (this.tz - this.z) * 0.06;
  }
};

function drawMento(c) {
  if (!mentoLoaded) return;
  mento.update();

  const zScale = 0.75 + mento.z * 0.5;
  const baseW = 140 * zScale * mento.sc;
  const baseH = (mentoImg.height / mentoImg.width) * baseW;

  const dx = mento.x - baseW / 2;
  const dy = mento.y - baseH;

  // Orange glow shadow underneath
  c.save();
  c.globalAlpha = 0.3 * mento.op;
  const glow = c.createRadialGradient(mento.x, mento.y, 0, mento.x, mento.y, baseW * 0.6);
  glow.addColorStop(0, '#FFB347');
  glow.addColorStop(1, 'rgba(255,179,71,0)');
  c.fillStyle = glow;
  c.fillRect(mento.x - baseW, mento.y - 10, baseW * 2, 20);

  // Floating bob animation
  c.globalAlpha = mento.op;
  const bob = Math.sin(Date.now() / 600) * 4;
  c.drawImage(mentoImg, dx, dy + bob, baseW, baseH);
  c.restore();

  // Name label
  c.font = 'bold 13px "Segoe UI"';
  c.fillStyle = '#FFB347';
  c.textAlign = 'center';
  c.fillText('Mento', mento.x, mento.y + 14);
  c.textAlign = 'left';
}
```

- [ ] **Step 3: Verify — draw Mento on a background**

Temporary test:
```javascript
mento.goto(W*0.3, H*0.82, true, 0.5);
// In draw loop: drawMento(ctx);
```

Expected: Mento mascot visible on scene, floating gently, orange glow underneath, "Mento" label below.

---

### Task 9: Character Instances + Timeline Builder

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Create character instances**

```javascript
const sharma = new Person({
  name: 'Principal Sharma', role: 'Principal',
  skin: '#c49464', hairColor: '#555555', hairStyle: 'short',
  shirtColor: '#1a365d', pantsColor: '#1a1a3e',
  hasGlasses: true, glassesStyle: 'rect',
  hasCollar: true, hasTie: true, tieColor: '#8B0000',
  accentColor: '#4A90D9', female: false
});

const priya = new Person({
  name: 'Teacher Priya', role: 'Teacher',
  skin: '#d4a574', hairColor: '#1a1a2e', hairStyle: 'long',
  shirtColor: '#C62828', pantsColor: '#8B1A1A',
  accentColor: '#E57373', female: true, hasEarring: true
});

const arjun = new Person({
  name: 'Arjun', role: 'Student',
  skin: '#c49464', hairColor: '#1a1a2e', hairStyle: 'short',
  shirtColor: '#2E7D32', pantsColor: '#1a1a3e',
  accentColor: '#66BB6A', female: false
});

const allChars = [sharma, priya, arjun];
```

- [ ] **Step 2: Add timeline builder**

```javascript
// Audio duration registry — empty for now, filled when ElevenLabs audio is added
const AUDIO_DURS = {};
const SCENE_LINE_COUNT = [2, 3, 4, 2, 3, 1]; // Lines per scene

let _btScene = 0;

function buildTimeline(lines, bufferStart, gap) {
  _btScene++;
  bufferStart = bufferStart || 0.6;
  gap = gap || 0.2;
  let t = bufferStart;
  return lines.map((l, i) => {
    const key = `${_btScene}_${i}`;
    const words = l.text.split(' ').length;
    const dur = AUDIO_DURS[key] || Math.max((words + 1) / 2.7 + 0.25, 2.0);
    const entry = {
      char: l.char, charName: l.charName, text: l.text,
      bubbleX: l.bubbleX, bubbleY: l.bubbleY, side: l.side,
      startSec: t, durSec: dur, endSec: t + dur
    };
    t += dur + gap;
    return entry;
  });
}

function sceneDuration(timeline, extraBuffer) {
  if (!timeline.length) return extraBuffer || 4;
  const last = timeline[timeline.length - 1];
  return last.endSec + (extraBuffer || 1.5);
}
```

- [ ] **Step 3: Build all 6 scene dialogue timelines**

```javascript
_btScene = 0;

// Scene 1: Meet Mento
const s1d = buildTimeline([
  { char: mento, charName: 'Mento', text: "What if your school could teach the skills no textbook covers?",
    bubbleX: 0.5, bubbleY: 0.25, side: 'center' },
  { char: mento, charName: 'Mento', text: "I'm Mento \u2014 let me show you something that will change how your students learn.",
    bubbleX: 0.5, bubbleY: 0.25, side: 'center' },
]);

// Scene 2: Principal's Problem
const s2d = buildTimeline([
  { char: mento, charName: 'Mento', text: "Principal Sharma, what's the biggest challenge you face?",
    bubbleX: 0.25, bubbleY: 0.25, side: 'left' },
  { char: sharma, charName: 'Principal Sharma', text: "Our students ace exams... but struggle with teamwork, decisions, and communication.",
    bubbleX: 0.72, bubbleY: 0.25, side: 'right' },
  { char: mento, charName: 'Mento', text: "What if there was a curriculum designed exactly for that?",
    bubbleX: 0.25, bubbleY: 0.25, side: 'left' },
]);

// Scene 3: 3-Mode Solution
const s3d = buildTimeline([
  { char: mento, charName: 'Mento', text: "Teacher Priya, how does MentoMap work in your classroom?",
    bubbleX: 0.22, bubbleY: 0.25, side: 'left' },
  { char: priya, charName: 'Teacher Priya', text: "Every month has 3 modes \u2014 physical workshops with real materials...",
    bubbleX: 0.58, bubbleY: 0.25, side: 'right' },
  { char: priya, charName: 'Teacher Priya', text: "...digital simulations where students play and learn on the platform...",
    bubbleX: 0.58, bubbleY: 0.25, side: 'right' },
  { char: priya, charName: 'Teacher Priya', text: "...and off-time games they play at home for practice and competition!",
    bubbleX: 0.58, bubbleY: 0.25, side: 'right' },
]);

// Scene 4: 9 Subjects
const s4d = buildTimeline([
  { char: mento, charName: 'Mento', text: "9 future-ready subjects across Grades 6, 7, and 8...",
    bubbleX: 0.20, bubbleY: 0.20, side: 'left' },
  { char: mento, charName: 'Mento', text: "All aligned with NEP 2020. No new teachers needed \u2014 just the curriculum and our platform.",
    bubbleX: 0.20, bubbleY: 0.20, side: 'left' },
]);

// Scene 5: Student Experience
const s5d = buildTimeline([
  { char: mento, charName: 'Mento', text: "Arjun, what's it like playing a MentoMap simulation?",
    bubbleX: 0.22, bubbleY: 0.25, side: 'left' },
  { char: arjun, charName: 'Arjun', text: "I ran a startup with just Rs 5,000 \u2014 had to make real decisions every round!",
    bubbleX: 0.58, bubbleY: 0.25, side: 'right' },
  { char: arjun, charName: 'Arjun', text: "My strategic thinking score went up, and I beat my friend on the leaderboard!",
    bubbleX: 0.58, bubbleY: 0.25, side: 'right' },
]);

// Scene 6: CTA
const s6d = buildTimeline([
  { char: mento, charName: 'Mento', text: "Ready to build future-ready students?",
    bubbleX: 0.5, bubbleY: 0.18, side: 'center' },
], 0.6, 0.2);

const sceneTimelines = [s1d, s2d, s3d, s4d, s5d, s6d];
const sceneTitles = [
  'Meet Mento', "The Principal's Problem", 'The 3-Mode Solution',
  '9 Subjects, 3 Grades', 'The Student Experience', 'Adopt the Curriculum'
];
const sceneSubtitles = [
  'MentoMap \u2014 Future Skills Curriculum for Grades 6, 7 & 8',
  '', '', '', '',
  '9 Months. 9 Subjects. Grades 6\u20148. One Complete Curriculum.'
];

const sceneDurs = [
  sceneDuration(s1d),
  sceneDuration(s2d),
  sceneDuration(s3d),
  sceneDuration(s4d),
  sceneDuration(s5d),
  sceneDuration(s6d, 8),  // Extra buffer for finale effects
];

const sceneStarts = [0];
for (let i = 1; i < sceneDurs.length; i++)
  sceneStarts.push(sceneStarts[i-1] + sceneDurs[i-1]);
const TOTAL = sceneStarts[sceneStarts.length-1] + sceneDurs[sceneDurs.length-1];
```

---

### Task 10: Custom Scene Elements

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Add 3-mode floating icon panels**

```javascript
function drawModeIcon(c, x, y, icon, label, scale) {
  const s = scale || 1;
  c.save();
  c.translate(x, y);
  c.scale(s, s);

  // Panel background
  c.fillStyle = 'rgba(255,179,71,0.1)';
  rr(c, -50, -30, 100, 60, 12);
  c.fill();
  c.strokeStyle = 'rgba(255,179,71,0.4)';
  c.lineWidth = 1.5;
  c.stroke();

  // Icon
  c.font = '28px sans-serif';
  c.textAlign = 'center';
  c.fillStyle = '#FFB347';
  c.fillText(icon, 0, 5);

  // Label
  c.font = 'bold 11px "Segoe UI"';
  c.fillStyle = '#FFD180';
  c.fillText(label, 0, 25);

  c.textAlign = 'left';
  c.restore();
}

function drawModeIcons(c, t, timeline) {
  // Three icons appear sequentially as Priya speaks lines 1-3
  const icons = [
    { icon: '\uD83C\uDFAD', label: 'Workshops', line: 1 },    // theater masks
    { icon: '\uD83C\uDFAE', label: 'Simulations', line: 2 },  // game controller
    { icon: '\uD83C\uDFE0', label: 'Off-Time Play', line: 3 } // house
  ];
  const baseX = W * 0.85;
  const baseY = H * 0.25;
  const spacing = 90;

  icons.forEach((item, i) => {
    if (!timeline[item.line]) return;
    const lineStart = timeline[item.line].startSec;
    const appear = ss(lineStart, lineStart + 0.5, t);
    if (appear <= 0) return;
    const pop = ease.elastic(appear);
    drawModeIcon(c, baseX, baseY + i * spacing, item.icon, item.label, pop);
  });
}
```

- [ ] **Step 2: Add subject grid (3x3)**

```javascript
const SUBJECTS = [
  { icon: '\uD83D\uDCB0', name: 'Financial\nLiteracy' },
  { icon: '\uD83D\uDE80', name: 'Entrepre-\nneurship' },
  { icon: '\uD83E\uDD1D', name: 'Negotiation' },
  { icon: '\uD83E\uDD16', name: 'AI &\nTechnology' },
  { icon: '\uD83D\uDC51', name: 'Leadership' },
  { icon: '\uD83D\uDCD6', name: 'Storytelling' },
  { icon: '\uD83D\uDCE2', name: 'Marketing' },
  { icon: '\uD83D\uDD0D', name: 'Critical\nThinking' },
  { icon: '\u2696\uFE0F', name: 'Ethics &\nTeamwork' },
];

function drawSubjectGrid(c, cx, cy, cellW, cellH, revealCount) {
  const cols = 3, rows = 3;
  const totalW = cols * cellW + (cols - 1) * 12;
  const totalH = rows * cellH + (rows - 1) * 12;
  const startX = cx - totalW / 2;
  const startY = cy - totalH / 2;

  for (let i = 0; i < Math.min(revealCount, 9); i++) {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = startX + col * (cellW + 12);
    const y = startY + row * (cellH + 12);

    // Cell background
    c.fillStyle = 'rgba(255,179,71,0.08)';
    rr(c, x, y, cellW, cellH, 8);
    c.fill();
    c.strokeStyle = 'rgba(255,179,71,0.25)';
    c.lineWidth = 1;
    c.stroke();

    // Icon
    c.font = '32px sans-serif';
    c.textAlign = 'center';
    c.fillStyle = '#FFB347';
    c.fillText(SUBJECTS[i].icon, x + cellW/2, y + 35);

    // Name (supports newlines)
    c.font = 'bold 12px "Segoe UI"';
    c.fillStyle = '#FFD180';
    const lines = SUBJECTS[i].name.split('\n');
    lines.forEach((line, li) => {
      c.fillText(line, x + cellW/2, y + 55 + li * 14);
    });
    c.textAlign = 'left';
  }
}
```

- [ ] **Step 3: Add NEP 2020 badge**

```javascript
function drawNEPBadge(c, x, y, scale) {
  c.save();
  c.translate(x, y);
  c.scale(scale, scale);

  // Badge background
  c.fillStyle = 'rgba(76,175,80,0.15)';
  rr(c, -90, -20, 180, 40, 20);
  c.fill();
  c.strokeStyle = 'rgba(76,175,80,0.6)';
  c.lineWidth = 1.5;
  c.stroke();

  // Checkmark
  c.font = '18px sans-serif';
  c.textAlign = 'center';
  c.fillStyle = '#4CAF50';
  c.fillText('\u2713', -60, 6);

  // Text
  c.font = 'bold 14px "Segoe UI"';
  c.fillStyle = '#a5d6a7';
  c.fillText('NEP 2020 Aligned', 10, 6);

  c.textAlign = 'left';
  c.restore();
}
```

- [ ] **Step 4: Add game mockup monitor**

```javascript
function drawGameMockup(c, x, y, scale, revealPct) {
  c.save();
  c.translate(x, y);
  c.scale(scale, scale);

  const mw = 260, mh = 200;

  // Monitor frame
  c.shadowColor = '#FFB347';
  c.shadowBlur = 10;
  c.fillStyle = '#0a0f0a';
  rr(c, -mw/2, -mh/2, mw, mh, 10);
  c.fill();
  c.shadowBlur = 0;

  c.strokeStyle = 'rgba(255,179,71,0.3)';
  c.lineWidth = 1.5;
  c.stroke();

  // Header bar
  c.fillStyle = 'rgba(255,179,71,0.1)';
  c.fillRect(-mw/2 + 4, -mh/2 + 4, mw - 8, 24);
  c.font = 'bold 10px "Segoe UI"';
  c.fillStyle = '#FFB347';
  c.fillText('The 6-Week Startup Sprint', -mw/2 + 12, -mh/2 + 19);

  if (revealPct > 0.3) {
    // Scenario text
    c.font = '11px "Segoe UI"';
    c.fillStyle = '#d0c8b8';
    c.fillText('Week 3: A competitor launches a', -mw/2 + 12, -mh/2 + 50);
    c.fillText('similar product. What do you do?', -mw/2 + 12, -mh/2 + 64);
  }

  if (revealPct > 0.5) {
    // Choice buttons
    const choices = ['Pivot to a new feature', 'Double down on marketing', 'Cut prices to compete'];
    choices.forEach((ch, i) => {
      const by = -mh/2 + 82 + i * 30;
      c.fillStyle = i === 0 ? 'rgba(255,179,71,0.15)' : 'rgba(255,255,255,0.05)';
      rr(c, -mw/2 + 10, by, mw - 20, 24, 6);
      c.fill();
      c.strokeStyle = i === 0 ? 'rgba(255,179,71,0.4)' : 'rgba(255,255,255,0.1)';
      c.lineWidth = 1;
      c.stroke();
      c.font = '11px "Segoe UI"';
      c.fillStyle = i === 0 ? '#FFD180' : '#888';
      c.fillText(ch, -mw/2 + 20, by + 16);
    });
  }

  c.restore();
}
```

- [ ] **Step 5: Add stat badges + CTA button**

```javascript
function drawStatBadges(c, cx, cy, badges, t) {
  const spacing = 160;
  const startX = cx - (badges.length - 1) * spacing / 2;

  badges.forEach((badge, i) => {
    const bx = startX + i * spacing;
    const pop = ease.elastic(clamp((t - i * 0.15) * 3, 0, 1));
    if (pop <= 0) return;

    c.save();
    c.translate(bx, cy);
    c.scale(pop, pop);

    // Circle background
    c.beginPath();
    c.arc(0, 0, 42, 0, Math.PI * 2);
    c.fillStyle = 'rgba(255,179,71,0.1)';
    c.fill();
    c.strokeStyle = 'rgba(255,179,71,0.5)';
    c.lineWidth = 2;
    c.stroke();

    // Value
    c.font = 'bold 20px "Segoe UI"';
    c.fillStyle = '#FFB347';
    c.textAlign = 'center';
    c.fillText(badge.value, 0, 6);

    // Label
    c.font = '10px "Segoe UI"';
    c.fillStyle = '#cc9960';
    c.fillText(badge.label, 0, 56);

    c.textAlign = 'left';
    c.restore();
  });
}

function drawCTA(c, cx, cy, text, t) {
  const pop = ease.elastic(clamp(t * 2, 0, 1));
  if (pop <= 0) return;
  c.save();
  c.translate(cx, cy);
  c.scale(pop, pop);

  c.font = 'bold 18px "Segoe UI"';
  const tw = c.measureText(text).width + 60;
  const th = 52;

  c.shadowColor = '#FFB347';
  c.shadowBlur = 25;
  c.fillStyle = 'rgba(255,179,71,0.15)';
  rr(c, -tw/2, -th/2, tw, th, th/2);
  c.fill();

  c.strokeStyle = '#FFB347';
  c.lineWidth = 2;
  c.stroke();
  c.shadowBlur = 0;

  c.fillStyle = '#FFD180';
  c.textAlign = 'center';
  c.fillText(text, 0, 6);

  c.textAlign = 'left';
  c.restore();
}
```

---

### Task 11: Scene Draw Functions

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Add Scene 1 — Meet Mento**

```javascript
function drawScene1(c, t, elapsed, timeline) {
  drawSceneBg(c, 'entrance', 0.45);
  drawSceneLighting(c, 'warm', t);

  // Mento enters from left with bounce
  const enterX = lerp(W * -0.1, W * 0.5, ease.out(clamp(t * 3, 0, 1)));
  mento.goto(enterX, H * 0.75, false, 0.55);

  // Particle burst on entrance
  if (t > 0.05 && t < 0.08) {
    emitBurst(W * 0.5, H * 0.7, 15, 3, 50, 2, '#FFB347', 'glow', 0);
  }

  // Ambient sparkles
  if (Math.random() < 0.04) {
    emitParticle(Math.random() * W, H + 5, (Math.random()-0.5)*0.3, -(0.3+Math.random()*0.4), 180, 1.5, '#FFD180', 'glow', 0);
  }

  // Camera: slow zoom on Mento
  camera.focusOn(0, H * 0.08, lerp(1.0, 1.02, t));

  drawMento(c);

  // Subtitle
  if (t < 0.1) showSubtitle(sceneSubtitles[0]);
  else if (t > 0.9) hideSubtitle();
}
```

- [ ] **Step 2: Add Scene 2 — Principal's Problem**

```javascript
function drawScene2(c, t, elapsed, timeline) {
  drawSceneBg(c, 'office', 0.55);
  drawSceneLighting(c, 'warm', t);

  mento.goto(W * 0.18, H * 0.82, false, 0.5);
  sharma.goto(W * 0.72, H * 0.82, false, 0.5);

  // Expressions
  if (timeline[2] && elapsed >= timeline[2].startSec) {
    sharma.setExpr('thinking');
  } else {
    sharma.setExpr('stressed');
  }

  // Camera follows speaker
  if (timeline[0] && elapsed < timeline[0].endSec) {
    camera.focusOn(W * 0.18 - W/2, H * 0.10, 1.02);
  } else if (timeline[1] && elapsed < timeline[1].endSec) {
    camera.focusOn(W * 0.72 - W/2, H * 0.10, 1.02);
  } else {
    camera.focusOn(W * 0.18 - W/2, H * 0.10, 1.02);
  }

  drawMento(c);
  drawCharsSorted(c, [sharma]);
}
```

- [ ] **Step 3: Add Scene 3 — 3-Mode Solution**

```javascript
function drawScene3(c, t, elapsed, timeline) {
  drawSceneBg(c, 'classroom', 0.50);
  drawSceneLighting(c, 'warm', t);

  mento.goto(W * 0.15, H * 0.82, false, 0.5);
  priya.goto(W * 0.50, H * 0.82, false, 0.5);
  priya.setExpr('happy');

  // Camera: wide shot
  camera.focusOn(0, H * 0.05, 1.0);

  drawMento(c);
  drawCharsSorted(c, [priya]);

  // 3-mode floating icons appear with each line
  drawModeIcons(c, elapsed, timeline);
}
```

- [ ] **Step 4: Add Scene 4 — 9 Subjects**

```javascript
function drawScene4(c, t, elapsed, timeline) {
  drawSceneBg(c, 'classroom', 0.65);
  drawSceneLighting(c, 'green', t);

  mento.goto(W * 0.12, H * 0.82, false, 0.5);
  priya.goto(W * 0.88, H * 0.82, false, 0.35);

  camera.focusOn(0, H * 0.04, 1.0);

  drawMento(c);
  drawCharsSorted(c, [priya]);

  // Subject grid — cells pop in sequentially during line 0
  if (timeline[0]) {
    const gridStart = timeline[0].startSec;
    const elapsed2 = elapsed - gridStart;
    const revealCount = Math.min(9, Math.floor(elapsed2 / 0.8) + 1);
    if (elapsed >= gridStart) {
      drawSubjectGrid(c, W * 0.52, H * 0.42, 100, 75, revealCount);

      // Particle burst per new cell
      if (revealCount > 0 && elapsed2 % 0.8 < 0.05) {
        const col = (revealCount - 1) % 3;
        const row = Math.floor((revealCount - 1) / 3);
        const gx = W * 0.52 - 150 + col * 112 + 50;
        const gy = H * 0.42 - 112 + row * 87 + 37;
        emitBurst(gx, gy, 6, 2, 30, 1.5, '#FFB347', 'glow', 0);
      }
    }
  }

  // NEP 2020 badge appears on line 1
  if (timeline[1] && elapsed >= timeline[1].startSec) {
    const nepT = ss(timeline[1].startSec, timeline[1].startSec + 0.5, elapsed);
    drawNEPBadge(c, W * 0.52, H * 0.78, ease.elastic(nepT));
  }
}
```

- [ ] **Step 5: Add Scene 5 — Student Experience**

```javascript
function drawScene5(c, t, elapsed, timeline) {
  drawSceneBg(c, 'studentroom', 0.50);
  drawSceneLighting(c, 'warm', t);

  mento.goto(W * 0.15, H * 0.82, false, 0.5);
  arjun.goto(W * 0.50, H * 0.82, false, 0.45);

  // Expressions
  if (timeline[0] && elapsed < timeline[0].endSec) {
    arjun.setExpr('thinking');
  } else {
    arjun.setExpr('happy');
  }

  // Camera
  if (timeline[0] && elapsed < timeline[0].endSec) {
    camera.focusOn(W * 0.15 - W/2, H * 0.10, 1.02);
  } else if (timeline[1] && elapsed < timeline[1].endSec) {
    camera.focusOn(W * 0.50 - W/2, H * 0.10, 1.02);
  } else {
    camera.focusOn(0, H * 0.05, 1.0);
  }

  drawMento(c);
  drawCharsSorted(c, [arjun]);

  // Game mockup appears on line 1
  if (timeline[1] && elapsed >= timeline[1].startSec) {
    const mockT = ss(timeline[1].startSec, timeline[1].endSec, elapsed);
    drawGameMockup(c, W * 0.78, H * 0.38, ease.elastic(clamp(mockT * 3, 0, 1)), mockT);
  }

  // Stat badges appear on line 2
  if (timeline[2] && elapsed >= timeline[2].startSec) {
    const badgeT = ss(timeline[2].startSec, timeline[2].startSec + 2, elapsed);
    drawStatBadges(c, W * 0.5, H * 0.72,
      [{ value: '8', label: 'Dimensions' }, { value: '79+', label: 'Games' }, { value: '24/7', label: 'Access' }],
      badgeT
    );
  }
}
```

- [ ] **Step 6: Add Scene 6 — CTA**

```javascript
function drawScene6(c, t, elapsed, timeline) {
  drawSceneBg(c, 'courtyard', 0.40);
  drawSceneLighting(c, 'triumph', t);

  // All characters together
  mento.goto(W * 0.50, H * 0.75, false, 0.6);
  sharma.goto(W * 0.22, H * 0.82, false, 0.5);
  priya.goto(W * 0.38, H * 0.82, false, 0.5);
  arjun.goto(W * 0.62, H * 0.82, false, 0.45);

  sharma.setExpr('proud');
  priya.setExpr('proud');
  arjun.setExpr('happy');

  camera.focusOn(0, H * 0.05, lerp(1.0, 1.02, t));

  drawMento(c);
  drawCharsSorted(c, [sharma, priya, arjun]);

  // Confetti burst
  if (t > 0.3 && t < 0.35) {
    emitConfetti(W / 2, H * 0.3, 40);
  }

  // CTA button
  if (t > 0.5) {
    drawCTA(c, W / 2, H * 0.55, 'Adopt MentoMap \u2192 mentomap.in', ss(0.5, 0.7, t));
  }

  // Subtitle
  if (t > 0.4) showSubtitle(sceneSubtitles[5]);

  // End card: fade to black with logo text
  if (t > 0.8) {
    const fadeT = ss(0.8, 1.0, t);
    c.fillStyle = `rgba(0,0,0,${fadeT * 0.9})`;
    c.fillRect(0, 0, W, H);

    if (fadeT > 0.5) {
      c.globalAlpha = (fadeT - 0.5) * 2;
      c.font = 'bold 42px "Segoe UI"';
      c.fillStyle = '#FFB347';
      c.textAlign = 'center';
      c.fillText('MentoMap', W/2, H/2 - 20);
      c.font = '18px "Segoe UI"';
      c.fillStyle = '#cc9960';
      c.fillText('hello@mentomap.in  \u00B7  mentomap.in', W/2, H/2 + 20);
      c.textAlign = 'left';
      c.globalAlpha = 1;
    }
  }
}

const sceneDraws = [drawScene1, drawScene2, drawScene3, drawScene4, drawScene5, drawScene6];
```

---

### Task 12: Main Animation Loop

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Add playback state variables**

```javascript
let filmTime = 0;
let playing = false;
let lastFrame = performance.now();
let lastSceneIdx = -1;
let voiceOn = false;
let audioAmplitude = 0;
let isRecording = false;

// Reset all characters' talking state
function resetAllCharTalking() {
  mento.talking = false;
  allChars.forEach(ch => { ch.talking = false; });
}
```

- [ ] **Step 2: Add dialogue rendering function**

```javascript
function renderDialogues(c, elapsed, timeline, sceneIdx) {
  // Reset all talking
  resetAllCharTalking();

  const maxBubbleWidth = 380;

  for (let i = 0; i < timeline.length; i++) {
    const d = timeline[i];
    if (elapsed >= d.startSec && elapsed < d.endSec + 0.5) {
      const lineT = (elapsed - d.startSec) / d.durSec;
      const revealPct = clamp(lineT * 1.15, 0, 1);
      const fadeOut = elapsed > d.endSec ? 1 - (elapsed - d.endSec) / 0.5 : 1;
      const scalePop = clamp((elapsed - d.startSec) * 4, 0, 1);

      drawDialogue(c,
        d.bubbleX * W, d.bubbleY * H,
        d.charName, d.text,
        maxBubbleWidth, d.char.accentColor || '#FFB347',
        fadeOut, d.side, revealPct, scalePop
      );

      // Set talking state for lip-sync
      if (elapsed < d.endSec) {
        d.char.talking = true;
      }
    }
  }
}
```

- [ ] **Step 3: Add main animation loop**

```javascript
function mainLoop(now) {
  requestAnimationFrame(mainLoop);

  const dt = Math.min((now - lastFrame) / 1000, 0.05);
  lastFrame = now;

  if (playing) filmTime += dt;

  // Clear
  ctx.clearRect(0, 0, W, H);

  // Determine current scene
  let sceneIdx = -1;
  for (let i = sceneStarts.length - 1; i >= 0; i--) {
    if (filmTime >= sceneStarts[i]) { sceneIdx = i; break; }
  }

  if (sceneIdx >= 0 && sceneIdx < sceneDraws.length) {
    const sDur = sceneDurs[sceneIdx];
    const elapsed = filmTime - sceneStarts[sceneIdx];
    const t = clamp(elapsed / sDur, 0, 1);
    const timeline = sceneTimelines[sceneIdx];

    // Scene transition
    if (sceneIdx !== lastSceneIdx) {
      capturePrevFrame();
      camera.reset();
      resetAllCharTalking();
      hideSubtitle();
      lastSceneIdx = sceneIdx;
    }

    // Camera transform
    camera.update(dt);
    camera.apply(ctx);

    // Draw scene
    sceneDraws[sceneIdx](ctx, t, elapsed, timeline);

    // Draw particles
    drawParticles(ctx);

    // Restore camera
    camera.restore(ctx);

    // Update particles
    updateParticles(dt);

    // Fade in/out transitions
    const fadeIn = Math.min(FADE, sDur * 0.12);
    if (elapsed < fadeIn) {
      ctx.fillStyle = `rgba(0,0,0,${1 - ease.out(elapsed / fadeIn)})`;
      ctx.fillRect(0, 0, W, H);
    }
    const fadeOutStart = sDur - fadeIn;
    if (elapsed > fadeOutStart) {
      ctx.fillStyle = `rgba(0,0,0,${ease.inOut((elapsed - fadeOutStart) / fadeIn)})`;
      ctx.fillRect(0, 0, W, H);
    }

    // Dialogue bubbles (on top of everything)
    renderDialogues(ctx, elapsed, timeline, sceneIdx);

    // Update scene label
    const scnEl = document.getElementById('scn');
    if (scnEl) scnEl.textContent = sceneTitles[sceneIdx] || '';
  }

  // End-of-film fade
  if (filmTime > TOTAL - 3) {
    const fade = (filmTime - (TOTAL - 3)) / 3;
    ctx.fillStyle = `rgba(0,0,0,${fade})`;
    ctx.fillRect(0, 0, W, H);
  }

  // Progress bar
  const pb = document.getElementById('pb');
  if (pb) pb.style.width = (filmTime / TOTAL * 100) + '%';

  // Time label
  const tl = document.getElementById('tl');
  if (tl) {
    const m = Math.floor(filmTime / 60);
    const s = Math.floor(filmTime % 60);
    tl.textContent = m + ':' + (s < 10 ? '0' : '') + s;
  }

  // Auto-stop recording at end
  if (isRecording && filmTime >= TOTAL + 2.5) {
    stopRecording();
  }
}
```

---

### Task 13: UI Controls + Recording + Start Overlay

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (append to `<script>`)

- [ ] **Step 1: Add play/pause, restart, voice toggle**

```javascript
// Play/Pause
document.getElementById('pp').onclick = () => {
  playing = !playing;
  document.getElementById('pp').innerHTML = playing ? '&#10074;&#10074;' : '&#9654;';
};

// Restart
document.getElementById('rb').onclick = () => {
  filmTime = 0;
  lastSceneIdx = -1;
  playing = true;
  document.getElementById('pp').innerHTML = '&#10074;&#10074;';
};

// Voice toggle (pre-wired for future audio)
document.getElementById('vb').onclick = () => {
  voiceOn = !voiceOn;
  document.getElementById('vb').innerHTML = voiceOn ? '&#128264;' : '&#128263;';
};

// Progress bar seek
document.getElementById('pw').onclick = (e) => {
  const rect = e.target.getBoundingClientRect();
  const pct = (e.clientX - rect.left) / rect.width;
  filmTime = pct * TOTAL;
  lastSceneIdx = -1;
};
```

- [ ] **Step 2: Add recording system**

```javascript
let mediaRecorder, recordedChunks = [];

function startRecording() {
  recordedChunks = [];

  const canvasStream = cv.captureStream(30);
  const combined = new MediaStream([...canvasStream.getVideoTracks()]);

  mediaRecorder = new MediaRecorder(combined, {
    videoBitsPerSecond: 8000000,
    mimeType: 'video/webm;codecs=vp9'
  });

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) recordedChunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    const blob = new Blob(recordedChunks, { type: 'video/webm' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mentomap_sizzle.webm';
    a.click();
    isRecording = false;
    document.getElementById('recBtn').style.color = '';
  };

  mediaRecorder.start(1000);
  isRecording = true;
  document.getElementById('recBtn').style.color = '#ff4444';

  // Restart from beginning
  filmTime = 0;
  lastSceneIdx = -1;
  playing = true;
  document.getElementById('pp').innerHTML = '&#10074;&#10074;';
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
}

document.getElementById('recBtn').onclick = () => {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
};
```

- [ ] **Step 3: Add start overlay click handler**

```javascript
document.getElementById('startOverlay').onclick = function() {
  this.style.opacity = '0';
  setTimeout(() => { this.style.display = 'none'; }, 600);
  playing = true;
  document.getElementById('pp').innerHTML = '&#10074;&#10074;';
  requestAnimationFrame(mainLoop);
};
```

---

### Task 14: Placeholder Background Generator

**Files:**
- Create: `video-output/sizzle-reel/generate_placeholders.html`

- [ ] **Step 1: Create the placeholder generator page**

This is a utility HTML page (not part of the video) that generates 5 placeholder background images using Canvas 2D. Each image is 1920x1080 with:

1. **school_entrance.jpg**: Light blue sky gradient → green ground. Orange rectangle building with "MentoMap School" text. Two green circle trees on sides. Yellow circle sun with glow. White cloud shapes. Brown path leading to building entrance.

2. **principal_office.jpg**: Warm brown/cream gradient walls. Dark brown desk rectangle at bottom. Brown bookshelf rectangles on right wall. Light blue window rectangle with curtain lines. Small gold certificate rectangles on wall. Desk lamp shape.

3. **classroom.jpg**: Cream wall gradient. Dark green chalkboard rectangle (40% width, centered). Three rows of brown desk rectangles. Two blue window rectangles. Colorful poster rectangles (red, yellow, green) on side walls.

4. **student_room.jpg**: Warm yellow/cream gradient. Brown desk rectangle. Blue-gray monitor rectangle with subtle glow. Small book rectangles. Colorful poster circles. Warm lamp glow from corner.

5. **school_courtyard.jpg**: Orange/golden gradient sky (golden hour). Dark building silhouette rectangle. Green tree circles. Brown ground. Warm sun glow in upper right.

Each canvas has a download button that triggers `canvas.toBlob()` → download as JPG.

- [ ] **Step 2: Open the generator and download all 5 images**

Open `generate_placeholders.html` in Chrome. Click each "Download" button. Save all 5 images to `video-output/sizzle-reel/images/`.

---

### Task 15: Playwright Recording Script

**Files:**
- Create: `video-output/sizzle-reel/record.js`

- [ ] **Step 1: Create Playwright recording script**

```javascript
// record.js — Automated video recording
// Usage: npx playwright test record.js
// Requires: npm install playwright

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const URL = 'http://localhost:8765/mentomap_sizzle.html';
const WEBM_FILE = path.join(__dirname, 'mentomap_sizzle.webm');

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

  // Click start overlay
  const overlay = page.locator('#startOverlay');
  if (await overlay.isVisible()) await overlay.click();
  await page.waitForTimeout(1000);

  // Pause, then start recording
  await page.evaluate(() => { playing = false; });
  await page.waitForTimeout(500);
  await page.locator('#recBtn').click();
  await page.waitForTimeout(1000);

  // Wait for download
  const download = await page.waitForEvent('download', { timeout: 300000 });
  await download.saveAs(WEBM_FILE);

  await browser.close();

  console.log('Recording saved to: ' + WEBM_FILE);
  console.log('Convert to MP4: ffmpeg -y -i mentomap_sizzle.webm -c:v libx264 -crf 20 -preset medium -movflags +faststart mentomap_sizzle.mp4');
})();
```

---

### Task 16: Integration Test + Polish

**Files:**
- Modify: `video-output/sizzle-reel/mentomap_sizzle.html` (adjustments)

- [ ] **Step 1: Start local server and open in browser**

```bash
cd /Users/amajumder/Downloads/MentoApp/video-output/sizzle-reel
/opt/homebrew/bin/python3 -m http.server 8765
```

Open `http://localhost:8765/mentomap_sizzle.html` in Chrome.

- [ ] **Step 2: Verify start overlay**

Expected: Black screen with "MENTOMAP" / "Future Skills Curriculum" / play button in orange. Click it.

- [ ] **Step 3: Verify Scene 1 (Meet Mento)**

Expected: School entrance background. Mento sprite slides in from left, bounces to center. Two speech bubbles appear sequentially with typewriter text. Orange particle sparkles.

- [ ] **Step 4: Verify Scene 2 (Principal's Problem)**

Expected: Office background. Mento left, Sharma right (glasses, tie, dark suit). Camera pans between speakers. Sharma expression: stressed → curious.

- [ ] **Step 5: Verify Scene 3 (3-Mode Solution)**

Expected: Classroom background. Mento left, Priya center-right (red outfit, long hair, earring). Three floating mode icon panels pop in on the right as Priya speaks each line.

- [ ] **Step 6: Verify Scene 4 (9 Subjects)**

Expected: Darker classroom. Subject grid appears on chalkboard area — 9 cells pop in sequentially with particle bursts. NEP 2020 badge appears below grid on second line.

- [ ] **Step 7: Verify Scene 5 (Student Experience)**

Expected: Student room background. Arjun (green shirt, shorter). Game mockup monitor appears on right. Stat badges pop in at bottom.

- [ ] **Step 8: Verify Scene 6 (CTA)**

Expected: Courtyard golden hour. All 4 characters together. Confetti burst. CTA button "Adopt MentoMap" fades in. End card: fade to black with MentoMap logo and contact info.

- [ ] **Step 9: Verify UI controls**

Test: play/pause button, progress bar seek (click to jump), restart button, record button (starts recording, downloads WebM when film ends).

- [ ] **Step 10: Fix any visual issues found during testing**

Common adjustments:
- Character positions if clipping or overlapping
- Bubble positions if obscuring characters
- Grid cell sizes if too small/large
- Timing if scenes feel too fast/slow
- Camera zoom if heads are clipped (keep ≤1.03)

---

## Self-Review Checklist

Spec coverage:
- [x] All 6 scenes from spec are implemented (Tasks 11)
- [x] All 4 characters defined with exact spec appearances (Task 9)
- [x] Brand palette matches spec: #FFB347/#E08A1E/#FFD180 (Task 3)
- [x] Mento as image sprite with orange glow (Task 8)
- [x] Subject grid 3x3 with sequential pop-in (Task 10)
- [x] Mode icons (Workshop/Simulation/Off-Time) (Task 10)
- [x] Game mockup monitor (Task 10)
- [x] Stat badges (8 Dimensions, 79+ Games, 24/7 Access) (Task 10)
- [x] NEP 2020 badge (Task 10)
- [x] CTA button with confetti (Task 10, 11)
- [x] End card with logo + contact (Task 11 Scene 6)
- [x] Recording pipeline (Task 13, 15)
- [x] Placeholder backgrounds (Task 14)
- [x] File structure matches spec (Task 1)
- [x] Audio hooks pre-wired (AUDIO_DURS dict, SCENE_LINE_COUNT) (Task 9)

No placeholders found. Type consistency verified across tasks.
