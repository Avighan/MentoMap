# Animation Capabilities Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone HTML file demonstrating web animation capabilities — SVG rigging, audio-driven lip-sync, frame-by-frame canvas animation, particle physics, and kinetic typography — with zero external dependencies.

**Architecture:** Single HTML file with inline CSS + JS. 6 full-viewport scroll sections, each showcasing one capability. SVG for vector-based character rigging, Canvas 2D for particles and frame-by-frame rendering, Web Audio API for audio analysis and synthesis. A combined finale section ties all capabilities together.

**Tech Stack:** Pure HTML5, CSS3, SVG, Canvas 2D, Web Audio API. No libraries, no CDN, no external assets.

---

## File Structure

- **Create:** `animation-demo.html` (project root) — the single standalone demo file

That's it. One file. All CSS in `<style>`, all JS in `<script>`, all SVG inline.

---

### Task 1: HTML Skeleton + Navigation + Dark Theme

**Files:**
- Create: `animation-demo.html`

- [ ] **Step 1: Create the base HTML file with 6 sections and sticky nav**

Create `animation-demo.html` in the project root with this content:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Animation Capabilities Demo</title>
<style>
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg: #0a0e1a;
  --bg-section: #0f1424;
  --text: #e0e6f0;
  --accent1: #6c63ff;
  --accent2: #00d4aa;
  --accent3: #ff6b9d;
  --accent4: #ffd93d;
  --accent5: #4ecdc4;
  --nav-bg: rgba(10, 14, 26, 0.9);
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; }
}

html { scroll-behavior: smooth; }
body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif; overflow-x: hidden; }

/* Sticky Nav */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  background: var(--nav-bg); backdrop-filter: blur(10px);
  display: flex; justify-content: center; gap: 8px; padding: 12px 16px;
  border-bottom: 1px solid rgba(108, 99, 255, 0.2);
}
nav a {
  color: var(--text); text-decoration: none; font-size: 13px; padding: 6px 14px;
  border-radius: 20px; transition: all 0.3s ease; opacity: 0.7;
}
nav a:hover, nav a.active { opacity: 1; background: rgba(108, 99, 255, 0.2); color: var(--accent1); }

/* Sections */
.section {
  min-height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 80px 40px 40px; position: relative; overflow: hidden;
}
.section-title {
  font-size: 14px; text-transform: uppercase; letter-spacing: 3px; color: var(--accent1);
  margin-bottom: 12px; opacity: 0.7;
}
.section-heading {
  font-size: 32px; font-weight: 700; margin-bottom: 24px; text-align: center;
}

/* Control buttons */
.controls { display: flex; gap: 8px; margin: 16px 0; flex-wrap: wrap; justify-content: center; }
.btn {
  padding: 8px 18px; border: 1px solid rgba(108, 99, 255, 0.4); background: rgba(108, 99, 255, 0.1);
  color: var(--text); border-radius: 20px; cursor: pointer; font-size: 13px; transition: all 0.3s ease;
}
.btn:hover { background: rgba(108, 99, 255, 0.3); }
.btn.active { background: var(--accent1); color: #fff; border-color: var(--accent1); }
</style>
</head>
<body>

<nav id="mainNav">
  <a href="#hero">Hero</a>
  <a href="#rigging">Rigging</a>
  <a href="#lipsync">Lip-Sync</a>
  <a href="#framebframe">Frame-by-Frame</a>
  <a href="#particles">Particles</a>
  <a href="#finale">Finale</a>
</nav>

<section class="section" id="hero" aria-label="Kinetic Typography Demo">
  <!-- Task 2 content -->
</section>

<section class="section" id="rigging" aria-label="SVG Character Rigging Demo">
  <!-- Task 3 content -->
</section>

<section class="section" id="lipsync" aria-label="Audio-Driven Lip Sync Demo">
  <!-- Task 4 content -->
</section>

<section class="section" id="framebframe" aria-label="Frame-by-Frame Animation Demo">
  <!-- Task 5 content -->
</section>

<section class="section" id="particles" aria-label="Particle Physics Demo">
  <!-- Task 6 content -->
</section>

<section class="section" id="finale" aria-label="Combined Animation Finale">
  <!-- Task 7 content -->
</section>

<script>
// Active nav link on scroll
const sections = document.querySelectorAll('.section');
const navLinks = document.querySelectorAll('#mainNav a');
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      navLinks.forEach(l => l.classList.remove('active'));
      const link = document.querySelector(`#mainNav a[href="#${entry.target.id}"]`);
      if (link) link.classList.add('active');
    }
  });
}, { threshold: 0.5 });
sections.forEach(s => observer.observe(s));
</script>
</body>
</html>
```

- [ ] **Step 2: Open in browser and verify**

Run: `open /Users/amajumder/Downloads/MentoApp/animation-demo.html`

Expected: Dark page with 6 full-height sections, sticky nav at top, nav highlights on scroll.

- [ ] **Step 3: Commit**

```bash
git add animation-demo.html
git commit -m "feat: add animation demo skeleton with nav and dark theme"
```

---

### Task 2: Hero Section — Kinetic Typography

**Files:**
- Modify: `animation-demo.html` — hero section HTML + CSS + JS

- [ ] **Step 1: Add hero section HTML content**

Replace `<!-- Task 2 content -->` inside the `#hero` section with:

```html
<div class="hero-bg" id="heroBg"></div>
<h1 class="hero-title" id="heroTitle"></h1>
<p class="hero-subtitle" id="heroSubtitle"></p>
<div class="scroll-indicator" id="scrollIndicator">
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M7 13l5 5 5-5M7 6l5 5 5-5"/>
  </svg>
  <span>Scroll Down</span>
</div>
```

- [ ] **Step 2: Add hero CSS**

Add inside `<style>`, after the `.btn.active` rule:

```css
/* Hero Section */
.hero-bg { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
.hero-bg-shape {
  position: absolute; opacity: 0.08; border-radius: 50%;
}
.hero-bg-shape.triangle { border-radius: 0; width: 0; height: 0; background: none !important; }

@keyframes float-shape {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-30px) rotate(180deg); }
}

.hero-title {
  font-size: clamp(36px, 6vw, 72px); font-weight: 800; text-align: center;
  display: flex; flex-wrap: wrap; justify-content: center; gap: 0; z-index: 1;
}
.hero-letter {
  display: inline-block; opacity: 0; transform: translateY(30px);
  animation: letter-in 0.5s forwards, letter-float 3s ease-in-out infinite;
  cursor: default; transition: color 0.2s;
}
.hero-letter.space { width: 0.3em; }
.hero-letter:hover { color: var(--accent2); transform: translateY(-5px) scale(1.1); }

@keyframes letter-in {
  to { opacity: 1; transform: translateY(0); }
}
@keyframes letter-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.hero-subtitle {
  font-size: 18px; opacity: 0.6; margin-top: 16px; z-index: 1;
  min-height: 1.5em; font-family: monospace;
}
.hero-subtitle .cursor { animation: blink 0.7s step-end infinite; }
@keyframes blink { 50% { opacity: 0; } }

.scroll-indicator {
  position: absolute; bottom: 40px; display: flex; flex-direction: column; align-items: center;
  gap: 8px; opacity: 0.4; animation: pulse-down 2s ease-in-out infinite; z-index: 1;
  font-size: 12px; letter-spacing: 2px; text-transform: uppercase;
}
@keyframes pulse-down { 0%, 100% { transform: translateY(0); opacity: 0.4; } 50% { transform: translateY(8px); opacity: 0.8; } }
```

- [ ] **Step 3: Add hero JS**

Add inside `<script>`, after the nav observer code:

```javascript
// === HERO: Kinetic Typography ===
(function initHero() {
  const title = 'Animation Capabilities';
  const titleEl = document.getElementById('heroTitle');
  const colors = ['#6c63ff', '#00d4aa', '#ff6b9d', '#ffd93d', '#4ecdc4'];

  title.split('').forEach((char, i) => {
    const span = document.createElement('span');
    span.className = 'hero-letter' + (char === ' ' ? ' space' : '');
    span.textContent = char === ' ' ? '\u00A0' : char;
    span.style.animationDelay = `${i * 0.05}s, ${i * 0.15}s`;
    span.style.color = colors[i % colors.length];
    titleEl.appendChild(span);
  });

  // Typewriter subtitle
  const subtitleEl = document.getElementById('heroSubtitle');
  const subtitleText = 'SVG Rigging | Lip-Sync | Frame-by-Frame | Particles | All in Code';
  let si = 0;
  subtitleEl.innerHTML = '<span class="cursor">|</span>';
  function typeNext() {
    if (si < subtitleText.length) {
      subtitleEl.innerHTML = subtitleText.slice(0, si + 1) + '<span class="cursor">|</span>';
      si++;
      setTimeout(typeNext, 50);
    }
  }
  setTimeout(typeNext, title.length * 50 + 500);

  // Background floating shapes
  const bg = document.getElementById('heroBg');
  for (let i = 0; i < 15; i++) {
    const shape = document.createElement('div');
    shape.className = 'hero-bg-shape';
    const size = 40 + Math.random() * 120;
    shape.style.width = size + 'px';
    shape.style.height = size + 'px';
    shape.style.left = Math.random() * 100 + '%';
    shape.style.top = Math.random() * 100 + '%';
    shape.style.background = colors[i % colors.length];
    shape.style.animation = `float-shape ${6 + Math.random() * 8}s ease-in-out infinite`;
    shape.style.animationDelay = `${Math.random() * -10}s`;
    bg.appendChild(shape);
  }
})();
```

- [ ] **Step 4: Open in browser and verify**

Run: `open /Users/amajumder/Downloads/MentoApp/animation-demo.html`

Expected: Colorful letters animate in one by one, float gently. Subtitle types out. Background shapes drift. Scroll indicator pulses.

- [ ] **Step 5: Commit**

```bash
git add animation-demo.html
git commit -m "feat: add hero section with kinetic typography and typewriter"
```

---

### Task 3: SVG Rigging — Geometric Creature

**Files:**
- Modify: `animation-demo.html` — rigging section HTML + CSS + JS

- [ ] **Step 1: Add rigging section HTML**

Replace `<!-- Task 3 content -->` inside the `#rigging` section with:

```html
<p class="section-title">Capability 01</p>
<h2 class="section-heading">SVG Character Rigging</h2>
<svg id="creatureSvg" viewBox="0 0 400 400" width="350" height="350" style="overflow:visible">
  <defs>
    <radialGradient id="bodyGrad" cx="50%" cy="40%"><stop offset="0%" stop-color="#7c74ff"/><stop offset="100%" stop-color="#4a42cc"/></radialGradient>
    <radialGradient id="headGrad" cx="50%" cy="40%"><stop offset="0%" stop-color="#8efa9e"/><stop offset="100%" stop-color="#3cc05c"/></radialGradient>
    <radialGradient id="limbGrad" cx="50%" cy="30%"><stop offset="0%" stop-color="#ff8fb0"/><stop offset="100%" stop-color="#e0456b"/></radialGradient>
  </defs>
  <!-- Tail -->
  <path id="creatureTail" d="M200,280 Q160,310 130,290 Q100,270 80,300" stroke="#ffd93d" stroke-width="6" fill="none" stroke-linecap="round"/>
  <!-- Left Leg -->
  <g id="leftLegUpper" style="transform-origin:170px 300px">
    <g id="leftLegLower" style="transform-origin:170px 340px">
      <rect x="162" y="340" width="16" height="35" rx="8" fill="url(#limbGrad)"/>
      <circle cx="170" cy="378" r="10" fill="#ff6b9d"/>
    </g>
    <rect x="162" y="300" width="16" height="45" rx="8" fill="url(#limbGrad)"/>
  </g>
  <!-- Right Leg -->
  <g id="rightLegUpper" style="transform-origin:230px 300px">
    <g id="rightLegLower" style="transform-origin:230px 340px">
      <rect x="222" y="340" width="16" height="35" rx="8" fill="url(#limbGrad)"/>
      <circle cx="230" cy="378" r="10" fill="#ff6b9d"/>
    </g>
    <rect x="222" y="300" width="16" height="45" rx="8" fill="url(#limbGrad)"/>
  </g>
  <!-- Body -->
  <g id="creatureBody" style="transform-origin:200px 250px">
    <ellipse cx="200" cy="250" rx="60" ry="45" fill="url(#bodyGrad)"/>
    <!-- Left Arm -->
    <g id="leftArmUpper" style="transform-origin:140px 235px">
      <rect x="108" y="229" width="35" height="14" rx="7" fill="url(#limbGrad)"/>
      <g id="leftArmLower" style="transform-origin:108px 235px">
        <rect x="78" y="229" width="32" height="12" rx="6" fill="url(#limbGrad)"/>
        <circle id="leftHand" cx="78" cy="235" r="8" fill="#ff6b9d"/>
      </g>
    </g>
    <!-- Right Arm -->
    <g id="rightArmUpper" style="transform-origin:260px 235px">
      <rect x="258" y="229" width="35" height="14" rx="7" fill="url(#limbGrad)"/>
      <g id="rightArmLower" style="transform-origin:293px 235px">
        <rect x="291" y="229" width="32" height="12" rx="6" fill="url(#limbGrad)"/>
        <circle id="rightHand" cx="323" cy="235" r="8" fill="#ff6b9d"/>
      </g>
    </g>
    <!-- Neck + Head -->
    <g id="creatureNeck" style="transform-origin:200px 210px">
      <rect x="193" y="195" width="14" height="20" rx="7" fill="#6c63ff"/>
      <g id="creatureHead" style="transform-origin:200px 170px">
        <circle cx="200" cy="165" r="38" fill="url(#headGrad)"/>
        <!-- Eyes -->
        <g id="eyeLeft"><circle cx="185" cy="158" r="8" fill="white"/><circle id="pupilLeft" cx="185" cy="158" r="4" fill="#1a1a2e"/></g>
        <g id="eyeRight"><circle cx="215" cy="158" r="8" fill="white"/><circle id="pupilRight" cx="215" cy="158" r="4" fill="#1a1a2e"/></g>
        <!-- Mouth (5 shapes, only one visible at a time) -->
        <g id="mouthGroup">
          <ellipse id="mouth0" cx="200" cy="180" rx="8" ry="2" fill="#1a1a2e"/>
          <ellipse id="mouth1" cx="200" cy="180" rx="9" ry="4" fill="#1a1a2e" style="display:none"/>
          <ellipse id="mouth2" cx="200" cy="180" rx="10" ry="7" fill="#1a1a2e" style="display:none"/>
          <ellipse id="mouth3" cx="200" cy="180" rx="11" ry="10" fill="#1a1a2e" style="display:none"/>
          <ellipse id="mouth4" cx="200" cy="180" rx="8" ry="11" fill="#1a1a2e" style="display:none"/>
        </g>
      </g>
    </g>
  </g>
</svg>
<div class="controls">
  <button class="btn active" onclick="setCreatureState('idle')">Idle</button>
  <button class="btn" onclick="setCreatureState('wave')">Wave</button>
  <button class="btn" onclick="setCreatureState('dance')">Dance</button>
</div>
```

- [ ] **Step 2: Add rigging JS**

Add inside `<script>`:

```javascript
// === RIGGING: Geometric Creature ===
let creatureState = 'idle';
let creatureTime = 0;
const creatureEls = {};

function initCreature() {
  const ids = ['creatureBody','creatureHead','creatureNeck','creatureTail',
    'leftArmUpper','leftArmLower','rightArmUpper','rightArmLower',
    'leftLegUpper','leftLegLower','rightLegUpper','rightLegLower',
    'pupilLeft','pupilRight','leftHand','rightHand'];
  ids.forEach(id => creatureEls[id] = document.getElementById(id));
}

function setCreatureState(state) {
  creatureState = state;
  document.querySelectorAll('#rigging .btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
}

function updateCreature(t) {
  creatureTime = t;
  const s = Math.sin;
  const c = Math.cos;

  if (creatureState === 'idle') {
    creatureEls.creatureBody.style.transform = `scaleY(${1 + s(t * 2) * 0.02})`;
    creatureEls.leftArmUpper.style.transform = `rotate(${s(t * 1.5) * 5}deg)`;
    creatureEls.rightArmUpper.style.transform = `rotate(${s(t * 1.5 + 1) * 5}deg)`;
    creatureEls.leftLegUpper.style.transform = `rotate(${s(t * 1.2) * 3}deg)`;
    creatureEls.rightLegUpper.style.transform = `rotate(${s(t * 1.2 + 1.5) * 3}deg)`;
    creatureEls.creatureHead.style.transform = `rotate(${s(t * 0.8) * 3}deg)`;
  } else if (creatureState === 'wave') {
    creatureEls.creatureBody.style.transform = `scaleY(${1 + s(t * 2) * 0.02})`;
    creatureEls.leftArmUpper.style.transform = `rotate(${s(t * 1.5) * 5}deg)`;
    creatureEls.rightArmUpper.style.transform = `rotate(-90deg)`;
    creatureEls.rightArmLower.style.transform = `rotate(${s(t * 6) * 25}deg)`;
    creatureEls.leftLegUpper.style.transform = `rotate(${s(t) * 3}deg)`;
    creatureEls.rightLegUpper.style.transform = `rotate(${s(t + 1) * 3}deg)`;
    creatureEls.creatureHead.style.transform = `rotate(${s(t * 2) * 5}deg)`;
  } else if (creatureState === 'dance') {
    const bounce = Math.abs(s(t * 4)) * 15;
    creatureEls.creatureBody.style.transform = `translateY(${-bounce}px) scaleY(${1 + s(t * 8) * 0.05})`;
    creatureEls.leftArmUpper.style.transform = `rotate(${s(t * 4) * 45}deg)`;
    creatureEls.rightArmUpper.style.transform = `rotate(${s(t * 4 + Math.PI) * 45}deg)`;
    creatureEls.leftArmLower.style.transform = `rotate(${s(t * 6) * 20}deg)`;
    creatureEls.rightArmLower.style.transform = `rotate(${s(t * 6 + 1) * 20}deg)`;
    creatureEls.leftLegUpper.style.transform = `rotate(${s(t * 4) * 15}deg)`;
    creatureEls.rightLegUpper.style.transform = `rotate(${s(t * 4 + Math.PI) * 15}deg)`;
    creatureEls.creatureHead.style.transform = `rotate(${s(t * 4) * 8}deg) translateY(${-bounce * 0.3}px)`;
  }

  // Tail wave
  const tw1 = 130 + s(t * 3) * 30;
  const tw2 = 100 + c(t * 3) * 20;
  const tw3 = 80 + s(t * 3 + 1) * 25;
  creatureEls.creatureTail.setAttribute('d', `M200,280 Q160,${310 + s(t*2)*10} ${tw1},${290 + c(t*2.5)*15} Q${tw2},${270 + s(t*3)*10} ${tw3},${300 + c(t*2)*15}`);
}

// Eye tracking
document.addEventListener('mousemove', (e) => {
  const svg = document.getElementById('creatureSvg');
  if (!svg) return;
  const rect = svg.getBoundingClientRect();
  const svgX = (e.clientX - rect.left) / rect.width * 400;
  const svgY = (e.clientY - rect.top) / rect.height * 400;

  [['pupilLeft', 185, 158], ['pupilRight', 215, 158]].forEach(([id, cx, cy]) => {
    const dx = svgX - cx, dy = svgY - cy;
    const dist = Math.min(Math.sqrt(dx*dx + dy*dy), 4);
    const angle = Math.atan2(dy, dx);
    const el = document.getElementById(id);
    if (el) { el.setAttribute('cx', cx + Math.cos(angle) * dist); el.setAttribute('cy', cy + Math.sin(angle) * dist); }
  });
});

initCreature();
```

- [ ] **Step 3: Open in browser and verify**

Expected: Colorful geometric creature with idle breathing. Click "Wave" — right arm waves. Click "Dance" — full body bounce. Eyes follow mouse cursor. Tail waves continuously.

- [ ] **Step 4: Commit**

```bash
git add animation-demo.html
git commit -m "feat: add SVG rigged geometric creature with idle/wave/dance states"
```

---

### Task 4: Lip-Sync — Audio-Driven Animation

**Files:**
- Modify: `animation-demo.html` — lipsync section HTML + JS

- [ ] **Step 1: Add lip-sync section HTML**

Replace `<!-- Task 4 content -->` inside the `#lipsync` section with:

```html
<p class="section-title">Capability 02</p>
<h2 class="section-heading">Audio-Driven Lip-Sync</h2>
<svg id="lipsyncCreature" viewBox="0 0 400 300" width="300" height="225" style="overflow:visible">
  <!-- Simplified creature: head + body + mouth -->
  <g id="lsBody" style="transform-origin:200px 200px">
    <ellipse cx="200" cy="200" rx="50" ry="38" fill="url(#bodyGrad)"/>
    <g id="lsHead" style="transform-origin:200px 140px">
      <circle cx="200" cy="135" r="35" fill="url(#headGrad)"/>
      <circle cx="188" cy="128" r="6" fill="white"/><circle id="lsPupilL" cx="188" cy="128" r="3" fill="#1a1a2e"/>
      <circle cx="212" cy="128" r="6" fill="white"/><circle id="lsPupilR" cx="212" cy="128" r="3" fill="#1a1a2e"/>
      <ellipse id="lsMouth" cx="200" cy="150" rx="8" ry="2" fill="#1a1a2e"/>
    </g>
  </g>
  <!-- Beat rings container -->
  <g id="beatRings"></g>
</svg>
<canvas id="waveformCanvas" width="500" height="80" style="border-radius:8px;margin-top:12px;background:rgba(0,0,0,0.3);max-width:90vw"></canvas>
<div class="controls">
  <button class="btn active" id="btnDemoAudio" onclick="startDemoAudio()">Demo Audio</button>
  <button class="btn" id="btnMicAudio" onclick="startMicAudio()">Use Microphone</button>
  <button class="btn" onclick="stopLipsyncAudio()">Stop</button>
</div>
<p style="font-size:12px;opacity:0.4;margin-top:8px">Volume drives mouth openness | Frequency drives mouth width | Beats trigger body pulse</p>
```

- [ ] **Step 2: Add lip-sync JS**

Add inside `<script>`:

```javascript
// === LIP-SYNC: Audio-Driven ===
let lsAudioCtx = null;
let lsAnalyser = null;
let lsFreqData = null;
let lsTimeData = null;
let lsSource = null;
let lsActive = false;
let lsRollingAvg = 50;
const LS_BEAT_THRESHOLD = 1.5;

function ensureAudioCtx() {
  if (!lsAudioCtx) {
    lsAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    lsAnalyser = lsAudioCtx.createAnalyser();
    lsAnalyser.fftSize = 256;
    lsFreqData = new Uint8Array(lsAnalyser.frequencyBinCount);
    lsTimeData = new Uint8Array(lsAnalyser.fftSize);
    lsAnalyser.connect(lsAudioCtx.destination);
  }
  if (lsAudioCtx.state === 'suspended') lsAudioCtx.resume();
}

function startDemoAudio() {
  ensureAudioCtx();
  stopLipsyncSource();
  lsActive = true;

  // Create a rhythmic melody with oscillators
  const notes = [220, 330, 440, 330, 220, 0, 440, 330];
  let noteIndex = 0;
  const gain = lsAudioCtx.createGain();
  gain.gain.value = 0.3;
  gain.connect(lsAnalyser);

  function playNote() {
    if (!lsActive) return;
    const freq = notes[noteIndex % notes.length];
    noteIndex++;
    if (freq > 0) {
      const osc = lsAudioCtx.createOscillator();
      osc.type = 'sine';
      osc.frequency.value = freq;
      const noteGain = lsAudioCtx.createGain();
      noteGain.gain.setValueAtTime(0.3, lsAudioCtx.currentTime);
      noteGain.gain.exponentialRampToValueAtTime(0.001, lsAudioCtx.currentTime + 0.3);
      osc.connect(noteGain);
      noteGain.connect(gain);
      osc.start();
      osc.stop(lsAudioCtx.currentTime + 0.35);
    }
    lsSource = setTimeout(playNote, 300);
  }
  playNote();
  document.getElementById('btnDemoAudio').classList.add('active');
  document.getElementById('btnMicAudio').classList.remove('active');
}

async function startMicAudio() {
  ensureAudioCtx();
  stopLipsyncSource();
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const micSource = lsAudioCtx.createMediaStreamSource(stream);
    micSource.connect(lsAnalyser);
    lsSource = { stream, micSource };
    lsActive = true;
    document.getElementById('btnMicAudio').classList.add('active');
    document.getElementById('btnDemoAudio').classList.remove('active');
  } catch (e) {
    alert('Microphone access denied. Try Demo Audio instead.');
  }
}

function stopLipsyncSource() {
  lsActive = false;
  if (typeof lsSource === 'number') clearTimeout(lsSource);
  else if (lsSource && lsSource.stream) {
    lsSource.stream.getTracks().forEach(t => t.stop());
    lsSource.micSource.disconnect();
  }
  lsSource = null;
}

function stopLipsyncAudio() {
  stopLipsyncSource();
  document.getElementById('btnDemoAudio').classList.remove('active');
  document.getElementById('btnMicAudio').classList.remove('active');
}

function updateLipsync() {
  if (!lsAnalyser || !lsActive) return;
  lsAnalyser.getByteFrequencyData(lsFreqData);
  lsAnalyser.getByteTimeDomainData(lsTimeData);

  // Volume: average of bins 0-20
  let vol = 0;
  for (let i = 0; i < 20; i++) vol += lsFreqData[i];
  vol /= 20;

  // Dominant frequency bin
  let maxBin = 0, maxVal = 0;
  for (let i = 0; i < lsFreqData.length; i++) {
    if (lsFreqData[i] > maxVal) { maxVal = lsFreqData[i]; maxBin = i; }
  }
  const freqRatio = maxBin / lsFreqData.length; // 0=low, 1=high

  // Beat detection
  lsRollingAvg = lsRollingAvg * 0.95 + vol * 0.05;
  const isBeat = vol > lsRollingAvg * LS_BEAT_THRESHOLD && vol > 30;

  // Mouth shape
  const mouth = document.getElementById('lsMouth');
  const mouthOpen = Math.min(vol / 255 * 15, 14); // ry: 2 to 14
  const mouthWidth = 8 + (1 - freqRatio) * 6; // rx: 8 to 14 (low=wide)
  mouth.setAttribute('ry', Math.max(2, mouthOpen));
  mouth.setAttribute('rx', mouthWidth);

  // Body pulse on beat
  const lsBody = document.getElementById('lsBody');
  if (isBeat) {
    lsBody.style.transform = 'scale(1.08)';
    lsBody.style.transition = 'transform 0.1s ease-out';
    // Spawn beat ring
    const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    ring.setAttribute('cx', 200); ring.setAttribute('cy', 170);
    ring.setAttribute('r', 40); ring.setAttribute('fill', 'none');
    ring.setAttribute('stroke', '#6c63ff'); ring.setAttribute('stroke-width', 2);
    ring.setAttribute('opacity', 0.6);
    document.getElementById('beatRings').appendChild(ring);
    let ringR = 40, ringO = 0.6;
    const expandRing = () => {
      ringR += 3; ringO -= 0.015;
      if (ringO <= 0) { ring.remove(); return; }
      ring.setAttribute('r', ringR); ring.setAttribute('opacity', ringO);
      requestAnimationFrame(expandRing);
    };
    requestAnimationFrame(expandRing);
    setTimeout(() => { lsBody.style.transform = 'scale(1)'; }, 100);
  }

  // Waveform
  const wCanvas = document.getElementById('waveformCanvas');
  const wCtx = wCanvas.getContext('2d');
  wCtx.fillStyle = 'rgba(0,0,0,0.3)';
  wCtx.fillRect(0, 0, wCanvas.width, wCanvas.height);
  wCtx.strokeStyle = '#00d4aa';
  wCtx.lineWidth = 2;
  wCtx.beginPath();
  const sliceW = wCanvas.width / lsTimeData.length;
  for (let i = 0; i < lsTimeData.length; i++) {
    const y = (lsTimeData[i] / 255) * wCanvas.height;
    i === 0 ? wCtx.moveTo(0, y) : wCtx.lineTo(i * sliceW, y);
  }
  wCtx.stroke();
}
```

- [ ] **Step 3: Open in browser and verify**

Expected: Creature with mouth. Click "Demo Audio" — hear melody, mouth opens/closes with volume, body pulses on beats, color rings radiate, waveform draws below. "Use Microphone" requests mic access and reacts to voice.

- [ ] **Step 4: Commit**

```bash
git add animation-demo.html
git commit -m "feat: add audio-driven lip-sync with beat detection and waveform"
```

---

### Task 5: Frame-by-Frame — Canvas Sprite Animation

**Files:**
- Modify: `animation-demo.html` — framebframe section HTML + CSS + JS

- [ ] **Step 1: Add frame-by-frame section HTML**

Replace `<!-- Task 5 content -->` inside the `#framebframe` section with:

```html
<p class="section-title">Capability 03</p>
<h2 class="section-heading">Frame-by-Frame Animation</h2>
<canvas id="frameCanvas" width="500" height="400" style="border-radius:12px;background:#080c16;max-width:90vw"></canvas>
<div class="controls">
  <button class="btn active" id="btnPlayPause" onclick="toggleFramePlay()">Pause</button>
  <button class="btn" onclick="setFrameFPS(6)">6 FPS</button>
  <button class="btn active" onclick="setFrameFPS(12)">12 FPS</button>
  <button class="btn" onclick="setFrameFPS(24)">24 FPS</button>
</div>
<div style="margin-top:8px;display:flex;align-items:center;gap:12px;width:90%;max-width:500px">
  <span style="font-size:12px;opacity:0.5">Frame</span>
  <input type="range" id="frameScrubber" min="0" max="143" value="0" style="flex:1;accent-color:#6c63ff" oninput="scrubFrame(this.value)">
  <span id="frameCounter" style="font-size:12px;opacity:0.5;min-width:50px">0 / 144</span>
</div>
```

- [ ] **Step 2: Add frame-by-frame JS**

Add inside `<script>`:

```javascript
// === FRAME-BY-FRAME: Morphing Shapes ===
const fbfCanvas = document.getElementById('frameCanvas');
const fbfCtx = fbfCanvas.getContext('2d');
let fbfPlaying = true;
let fbfFPS = 12;
let fbfFrame = 0;
let fbfLastFrameTime = 0;
const FBF_FRAMES_PER_TRANSITION = 24;
const FBF_TRAIL_COUNT = 5;

// Define shapes as polar vertices (angle, radius) normalized to unit circle
// All shapes use 60 points for smooth morphing
function shapeVertices(type, numPoints) {
  const pts = [];
  for (let i = 0; i < numPoints; i++) {
    const angle = (i / numPoints) * Math.PI * 2;
    let r = 1;
    if (type === 'circle') {
      r = 1;
    } else if (type === 'square') {
      // Square in polar
      const a = angle % (Math.PI / 2);
      r = 1 / Math.max(Math.abs(Math.cos(a)), Math.abs(Math.sin(a))) * 0.8;
    } else if (type === 'triangle') {
      const a = (angle + Math.PI / 2) % (Math.PI * 2 / 3);
      r = 0.7 / Math.cos(a - Math.PI / 3);
      r = Math.max(0.3, Math.min(r, 1.2));
    } else if (type === 'star') {
      r = (i % 2 === 0) ? 1 : 0.45;
    } else if (type === 'hexagon') {
      const a = angle % (Math.PI / 3);
      r = 0.9 / Math.cos(a - Math.PI / 6);
      r = Math.max(0.3, Math.min(r, 1.1));
    }
    pts.push({ angle, r });
  }
  return pts;
}

const FBF_SHAPES = ['circle', 'square', 'triangle', 'star', 'hexagon', 'circle'];
const FBF_VERTICES = FBF_SHAPES.map(s => shapeVertices(s, 60));
const FBF_TOTAL_FRAMES = (FBF_SHAPES.length - 1) * FBF_FRAMES_PER_TRANSITION;

function getFrameVertices(frame) {
  const transitionIndex = Math.floor(frame / FBF_FRAMES_PER_TRANSITION);
  const t = (frame % FBF_FRAMES_PER_TRANSITION) / FBF_FRAMES_PER_TRANSITION;
  const fromIdx = Math.min(transitionIndex, FBF_VERTICES.length - 2);
  const toIdx = fromIdx + 1;
  const from = FBF_VERTICES[fromIdx];
  const to = FBF_VERTICES[toIdx];
  return from.map((fv, i) => ({
    angle: fv.angle,
    r: fv.r + (to[i].r - fv.r) * t
  }));
}

function drawShape(ctx, cx, cy, radius, vertices, alpha, scale) {
  ctx.globalAlpha = alpha;
  ctx.beginPath();
  vertices.forEach((v, i) => {
    const x = cx + Math.cos(v.angle) * v.r * radius * scale;
    const y = cy + Math.sin(v.angle) * v.r * radius * scale;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.closePath();
}

function renderFrameByFrame() {
  const W = fbfCanvas.width, H = fbfCanvas.height;
  const cx = W / 2, cy = H / 2, radius = 100;
  fbfCtx.clearRect(0, 0, W, H);

  const hue = (fbfFrame * 2) % 360;

  // Draw trail (previous frames)
  for (let t = FBF_TRAIL_COUNT; t >= 1; t--) {
    const trailFrame = ((fbfFrame - t) + FBF_TOTAL_FRAMES) % FBF_TOTAL_FRAMES;
    const verts = getFrameVertices(trailFrame);
    const trailAlpha = (FBF_TRAIL_COUNT - t + 1) / (FBF_TRAIL_COUNT + 2) * 0.5;
    const trailScale = 1 - t * 0.03;
    const trailHue = (trailFrame * 2) % 360;
    drawShape(fbfCtx, cx, cy, radius, verts, trailAlpha, trailScale);
    fbfCtx.fillStyle = `hsla(${trailHue}, 70%, 60%, ${trailAlpha})`;
    fbfCtx.fill();
  }

  // Draw current frame
  const verts = getFrameVertices(fbfFrame);
  drawShape(fbfCtx, cx, cy, radius, verts, 1, 1);
  fbfCtx.fillStyle = `hsl(${hue}, 70%, 60%)`;
  fbfCtx.fill();
  fbfCtx.strokeStyle = `hsl(${hue}, 80%, 75%)`;
  fbfCtx.lineWidth = 2;
  fbfCtx.globalAlpha = 1;
  fbfCtx.stroke();

  // Update scrubber
  document.getElementById('frameScrubber').value = fbfFrame;
  document.getElementById('frameCounter').textContent = `${fbfFrame} / ${FBF_TOTAL_FRAMES}`;
}

function toggleFramePlay() {
  fbfPlaying = !fbfPlaying;
  document.getElementById('btnPlayPause').textContent = fbfPlaying ? 'Pause' : 'Play';
  document.getElementById('btnPlayPause').classList.toggle('active', fbfPlaying);
}

function setFrameFPS(fps) {
  fbfFPS = fps;
  document.querySelectorAll('#framebframe .btn').forEach(b => {
    if (b.textContent.includes('FPS')) b.classList.toggle('active', b.textContent === fps + ' FPS');
  });
}

function scrubFrame(val) {
  fbfFrame = parseInt(val);
  renderFrameByFrame();
}

function fbfTick(timestamp) {
  if (fbfPlaying) {
    const interval = 1000 / fbfFPS;
    if (timestamp - fbfLastFrameTime >= interval) {
      fbfFrame = (fbfFrame + 1) % FBF_TOTAL_FRAMES;
      renderFrameByFrame();
      fbfLastFrameTime = timestamp;
    }
  }
  requestAnimationFrame(fbfTick);
}
renderFrameByFrame();
requestAnimationFrame(fbfTick);
```

- [ ] **Step 3: Open in browser and verify**

Expected: Morphing shape cycles through circle->square->triangle->star->hexagon->circle with color trail. Play/pause works. FPS buttons change speed visibly. Frame scrubber lets you drag through timeline.

- [ ] **Step 4: Commit**

```bash
git add animation-demo.html
git commit -m "feat: add frame-by-frame morphing shape animation with scrubber"
```

---

### Task 6: Particle System — Canvas Physics

**Files:**
- Modify: `animation-demo.html` — particles section HTML + JS

- [ ] **Step 1: Add particle section HTML**

Replace `<!-- Task 6 content -->` inside the `#particles` section with:

```html
<p class="section-title">Capability 04</p>
<h2 class="section-heading">Particle Physics System</h2>
<canvas id="particleCanvas" style="border-radius:12px;background:#080c16;cursor:crosshair;max-width:95vw;max-height:60vh"></canvas>
<div class="controls">
  <button class="btn active" onclick="setParticleType('spark')">Sparks</button>
  <button class="btn" onclick="setParticleType('confetti')">Confetti</button>
  <button class="btn" onclick="setParticleType('bubble')">Bubbles</button>
  <span style="opacity:0.3;margin:0 4px">|</span>
  <button class="btn" id="btnAttract" onclick="toggleParticleForce()">Attract</button>
</div>
<p style="font-size:12px;opacity:0.4;margin-top:8px">Click anywhere to spawn particles | Move mouse to interact</p>
```

- [ ] **Step 2: Add particle system JS**

Add inside `<script>`:

```javascript
// === PARTICLES: Canvas Physics ===
const pCanvas = document.getElementById('particleCanvas');
const pCtx = pCanvas.getContext('2d');
let particles = [];
let particleType = 'spark';
let particleForceMode = 'attract'; // 'attract' or 'repel'
let pMouseX = 0, pMouseY = 0;
const MAX_PARTICLES = 500;

function resizeParticleCanvas() {
  const section = document.getElementById('particles');
  pCanvas.width = Math.min(section.clientWidth - 40, 900);
  pCanvas.height = Math.min(window.innerHeight * 0.55, 500);
}
resizeParticleCanvas();
window.addEventListener('resize', resizeParticleCanvas);

function createParticle(x, y, type, isAmbient) {
  const angle = Math.random() * Math.PI * 2;
  const speed = isAmbient ? 0.2 + Math.random() * 0.3 : 2 + Math.random() * 5;
  const base = {
    x, y,
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed * (type === 'bubble' ? -1 : 1),
    lifetime: 0,
    rotation: 0,
    rotationSpeed: (Math.random() - 0.5) * 0.2,
    type
  };

  if (type === 'spark') {
    base.size = 2 + Math.random() * 2;
    base.maxLifetime = isAmbient ? 600 + Math.random() * 300 : 60 + Math.random() * 60;
    base.color = `hsl(${30 + Math.random() * 30}, 100%, ${60 + Math.random() * 30}%)`;
    base.ax = 0; base.ay = isAmbient ? 0 : 0.1;
    base.friction = 0.98;
  } else if (type === 'confetti') {
    base.size = 6 + Math.random() * 4;
    base.maxLifetime = isAmbient ? 600 : 120 + Math.random() * 60;
    base.color = `hsl(${Math.random() * 360}, 80%, 65%)`;
    base.vy = isAmbient ? base.vy : -(2 + Math.random() * 3);
    base.ax = 0; base.ay = isAmbient ? 0 : 0.05;
    base.friction = 0.99;
  } else { // bubble
    base.size = 8 + Math.random() * 7;
    base.maxLifetime = isAmbient ? 600 : 150 + Math.random() * 50;
    base.vy = -(0.5 + Math.random() * 1.5);
    base.ax = 0; base.ay = isAmbient ? 0 : -0.02;
    base.friction = 0.995;
    base.color = `hsla(${180 + Math.random() * 40}, 70%, 65%, 0.6)`;
  }
  base.isAmbient = isAmbient;
  return base;
}

function setParticleType(type) {
  particleType = type;
  document.querySelectorAll('#particles .btn').forEach(b => {
    if (['Sparks','Confetti','Bubbles'].includes(b.textContent))
      b.classList.toggle('active', b.textContent.toLowerCase().startsWith(type));
  });
}

function toggleParticleForce() {
  particleForceMode = particleForceMode === 'attract' ? 'repel' : 'attract';
  const btn = document.getElementById('btnAttract');
  btn.textContent = particleForceMode === 'attract' ? 'Attract' : 'Repel';
}

// Spawn ambient particles
for (let i = 0; i < 30; i++) {
  particles.push(createParticle(
    Math.random() * pCanvas.width,
    Math.random() * pCanvas.height,
    ['spark', 'confetti', 'bubble'][i % 3],
    true
  ));
}

pCanvas.addEventListener('click', (e) => {
  const rect = pCanvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) * (pCanvas.width / rect.width);
  const y = (e.clientY - rect.top) * (pCanvas.height / rect.height);
  const count = 50 + Math.floor(Math.random() * 50);
  for (let i = 0; i < count && particles.length < MAX_PARTICLES; i++) {
    particles.push(createParticle(x, y, particleType, false));
  }
});

pCanvas.addEventListener('mousemove', (e) => {
  const rect = pCanvas.getBoundingClientRect();
  pMouseX = (e.clientX - rect.left) * (pCanvas.width / rect.width);
  pMouseY = (e.clientY - rect.top) * (pCanvas.height / rect.height);
});

function updateParticles() {
  const W = pCanvas.width, H = pCanvas.height;
  pCtx.fillStyle = 'rgba(8, 12, 22, 0.15)';
  pCtx.fillRect(0, 0, W, H);

  // Update and draw particles
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.lifetime++;

    // Kill expired (respawn ambient)
    if (p.lifetime >= p.maxLifetime) {
      if (p.isAmbient) {
        particles[i] = createParticle(Math.random() * W, Math.random() * H, p.type, true);
        continue;
      } else {
        particles.splice(i, 1);
        continue;
      }
    }

    // Mouse force
    const dx = pMouseX - p.x, dy = pMouseY - p.y;
    const dist = Math.sqrt(dx * dx + dy * dy);
    if (dist < 150 && dist > 1) {
      const force = (150 - dist) / 150 * 0.5;
      const dir = particleForceMode === 'attract' ? 1 : -1;
      p.vx += (dx / dist) * force * dir;
      p.vy += (dy / dist) * force * dir;
    }

    // Physics
    p.vx += p.ax; p.vy += p.ay;
    p.vx *= p.friction; p.vy *= p.friction;
    p.x += p.vx; p.y += p.vy;
    p.rotation += p.rotationSpeed;

    // Wrap ambient particles
    if (p.isAmbient) {
      if (p.x < -20) p.x = W + 20;
      if (p.x > W + 20) p.x = -20;
      if (p.y < -20) p.y = H + 20;
      if (p.y > H + 20) p.y = -20;
    }

    const lifeRatio = 1 - p.lifetime / p.maxLifetime;

    // Draw based on type
    pCtx.globalAlpha = lifeRatio;
    if (p.type === 'spark') {
      pCtx.fillStyle = p.color;
      pCtx.beginPath();
      pCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      pCtx.fill();
      // Velocity trail
      pCtx.strokeStyle = p.color;
      pCtx.lineWidth = 1;
      pCtx.beginPath();
      pCtx.moveTo(p.x, p.y);
      pCtx.lineTo(p.x - p.vx * 3, p.y - p.vy * 3);
      pCtx.stroke();
    } else if (p.type === 'confetti') {
      pCtx.save();
      pCtx.translate(p.x, p.y);
      pCtx.rotate(p.rotation);
      pCtx.fillStyle = p.color;
      pCtx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
      pCtx.restore();
    } else { // bubble
      const wobble = Math.sin(p.lifetime * 0.1) * 3;
      const bx = p.x + wobble;
      // Pop at end of life
      const popScale = p.lifetime > p.maxLifetime - 10 ? (p.maxLifetime - p.lifetime) / 10 : 1;
      pCtx.strokeStyle = p.color;
      pCtx.lineWidth = 1.5;
      pCtx.beginPath();
      pCtx.arc(bx, p.y, p.size * popScale, 0, Math.PI * 2);
      pCtx.stroke();
      // Highlight
      pCtx.beginPath();
      pCtx.arc(bx - p.size * 0.3, p.y - p.size * 0.3, p.size * 0.2 * popScale, 0, Math.PI * 2);
      pCtx.fillStyle = 'rgba(255,255,255,0.4)';
      pCtx.fill();
    }
  }

  // Connections (constellation effect) — only among nearby ambient particles
  pCtx.globalAlpha = 1;
  const ambientParticles = particles.filter(p => p.isAmbient);
  for (let i = 0; i < ambientParticles.length; i++) {
    for (let j = i + 1; j < ambientParticles.length; j++) {
      const a = ambientParticles[i], b = ambientParticles[j];
      const d = Math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2);
      if (d < 100) {
        pCtx.strokeStyle = `rgba(108, 99, 255, ${(100 - d) / 100 * 0.3})`;
        pCtx.lineWidth = 0.5;
        pCtx.beginPath();
        pCtx.moveTo(a.x, a.y);
        pCtx.lineTo(b.x, b.y);
        pCtx.stroke();
      }
    }
  }
}
```

- [ ] **Step 3: Open in browser and verify**

Expected: Ambient particles drift with constellation lines. Click spawns burst of current type. Sparks have trails, confetti tumbles, bubbles wobble and pop. Mouse attracts/repels. Toggle between types and force modes.

- [ ] **Step 4: Commit**

```bash
git add animation-demo.html
git commit -m "feat: add particle physics system with 3 types and mouse interaction"
```

---

### Task 7: Combined Finale + Main Animation Loop

**Files:**
- Modify: `animation-demo.html` — finale section HTML + JS + main loop

- [ ] **Step 1: Add finale section HTML**

Replace `<!-- Task 7 content -->` inside the `#finale` section with:

```html
<p class="section-title">All Together</p>
<h2 class="section-heading">Combined Finale</h2>
<div id="finaleContainer" style="position:relative;width:600px;max-width:95vw;height:500px">
  <canvas id="finaleCanvas" style="position:absolute;inset:0;width:100%;height:100%;border-radius:12px;background:#080c16"></canvas>
  <svg id="finaleSvg" viewBox="0 0 600 500" style="position:absolute;inset:0;width:100%;height:100%;overflow:visible" xmlns="http://www.w3.org/2000/svg">
    <!-- Finale creature (inline copy, centered at 300,250) -->
    <g id="finCreature" style="transform-origin:300px 250px">
      <path id="finTail" d="M300,290 Q270,320 240,300 Q210,280 190,310" stroke="#ffd93d" stroke-width="5" fill="none" stroke-linecap="round"/>
      <g id="finBody" style="transform-origin:300px 260px">
        <ellipse cx="300" cy="260" rx="45" ry="35" fill="url(#bodyGrad)"/>
        <g id="finLeftArm" style="transform-origin:255px 250px">
          <rect x="225" y="244" width="32" height="12" rx="6" fill="url(#limbGrad)"/>
          <circle id="finLeftHand" cx="225" cy="250" r="7" fill="#ff6b9d"/>
        </g>
        <g id="finRightArm" style="transform-origin:345px 250px">
          <rect x="343" y="244" width="32" height="12" rx="6" fill="url(#limbGrad)"/>
          <circle id="finRightHand" cx="375" cy="250" r="7" fill="#ff6b9d"/>
        </g>
      </g>
      <g id="finHead" style="transform-origin:300px 200px">
        <circle cx="300" cy="195" r="30" fill="url(#headGrad)"/>
        <circle cx="290" cy="188" r="5" fill="white"/><circle id="finPupilL" cx="290" cy="188" r="2.5" fill="#1a1a2e"/>
        <circle cx="310" cy="188" r="5" fill="white"/><circle id="finPupilR" cx="310" cy="188" r="2.5" fill="#1a1a2e"/>
        <ellipse id="finMouth" cx="300" cy="208" rx="7" ry="2" fill="#1a1a2e"/>
      </g>
    </g>
    <g id="finBeatRings"></g>
    <!-- Kinetic text -->
    <text id="finText0" x="300" y="60" text-anchor="middle" fill="#6c63ff" font-size="18" font-weight="700" opacity="0">Rigging</text>
    <text id="finText1" x="520" y="260" text-anchor="middle" fill="#00d4aa" font-size="18" font-weight="700" opacity="0">Lip-Sync</text>
    <text id="finText2" x="300" y="460" text-anchor="middle" fill="#ff6b9d" font-size="18" font-weight="700" opacity="0">Particles</text>
    <text id="finText3" x="80" y="260" text-anchor="middle" fill="#ffd93d" font-size="18" font-weight="700" opacity="0">Frame-by-Frame</text>
  </svg>
</div>
<div class="controls">
  <button class="btn" id="btnFinaleStart" onclick="startFinale()">Start Finale</button>
</div>
<p style="font-size:16px;opacity:0.5;margin-top:24px;text-align:center;max-width:500px">All generated with code. Zero external assets.</p>
```

- [ ] **Step 2: Add finale JS and main animation loop**

Add inside `<script>`:

```javascript
// === FINALE: Combined ===
let finaleActive = false;
let finaleAudioCtx = null;
let finaleAnalyser = null;
let finaleFreqData = null;
let finaleParticles = [];
let finaleTime = 0;
let finaleNoteTimeout = null;

function startFinale() {
  if (finaleActive) { stopFinale(); return; }
  finaleActive = true;
  document.getElementById('btnFinaleStart').textContent = 'Stop Finale';
  document.getElementById('btnFinaleStart').classList.add('active');

  // Set up canvas
  const container = document.getElementById('finaleContainer');
  const fCanvas = document.getElementById('finaleCanvas');
  fCanvas.width = container.clientWidth;
  fCanvas.height = container.clientHeight;

  // Audio: rhythmic beat loop
  finaleAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
  finaleAnalyser = finaleAudioCtx.createAnalyser();
  finaleAnalyser.fftSize = 256;
  finaleFreqData = new Uint8Array(finaleAnalyser.frequencyBinCount);
  finaleAnalyser.connect(finaleAudioCtx.destination);

  const gain = finaleAudioCtx.createGain();
  gain.gain.value = 0.2;
  gain.connect(finaleAnalyser);

  const beatPattern = [
    { freq: 80, dur: 0.1, type: 'sine' },     // kick
    { freq: 0, dur: 0.15, type: 'sine' },      // rest
    { freq: 800, dur: 0.03, type: 'sine' },    // hi-hat
    { freq: 0, dur: 0.12, type: 'sine' },      // rest
    { freq: 200, dur: 0.05, type: 'triangle' }, // snare-ish
    { freq: 0, dur: 0.15, type: 'sine' },
    { freq: 800, dur: 0.03, type: 'sine' },
    { freq: 0, dur: 0.12, type: 'sine' },
  ];
  let beatIdx = 0;

  function playBeat() {
    if (!finaleActive) return;
    const beat = beatPattern[beatIdx % beatPattern.length];
    beatIdx++;
    if (beat.freq > 0) {
      const osc = finaleAudioCtx.createOscillator();
      osc.type = beat.type;
      osc.frequency.value = beat.freq;
      const g = finaleAudioCtx.createGain();
      g.gain.setValueAtTime(0.3, finaleAudioCtx.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, finaleAudioCtx.currentTime + beat.dur);
      osc.connect(g); g.connect(gain);
      osc.start(); osc.stop(finaleAudioCtx.currentTime + beat.dur + 0.05);
    }
    finaleNoteTimeout = setTimeout(playBeat, beat.dur * 1000 + 50);
  }
  playBeat();
}

function stopFinale() {
  finaleActive = false;
  if (finaleNoteTimeout) clearTimeout(finaleNoteTimeout);
  if (finaleAudioCtx) finaleAudioCtx.close();
  finaleAudioCtx = null;
  document.getElementById('btnFinaleStart').textContent = 'Start Finale';
  document.getElementById('btnFinaleStart').classList.remove('active');
}

function updateFinale(t) {
  if (!finaleActive) return;
  finaleTime = t;
  const fCanvas = document.getElementById('finaleCanvas');
  const fCtx = fCanvas.getContext('2d');
  const W = fCanvas.width, H = fCanvas.height;

  fCtx.fillStyle = 'rgba(8, 12, 22, 0.2)';
  fCtx.fillRect(0, 0, W, H);

  // Audio analysis
  let vol = 0;
  if (finaleAnalyser) {
    finaleAnalyser.getByteFrequencyData(finaleFreqData);
    for (let i = 0; i < 20; i++) vol += finaleFreqData[i];
    vol /= 20;
  }
  const isBeat = vol > 40;

  // Dance the creature
  const s = Math.sin;
  const bounce = Math.abs(s(t * 4)) * 12;
  const body = document.getElementById('finBody');
  const head = document.getElementById('finHead');
  const lArm = document.getElementById('finLeftArm');
  const rArm = document.getElementById('finRightArm');
  if (body) body.style.transform = `translateY(${-bounce}px) scaleY(${1 + s(t * 8) * 0.04})`;
  if (head) head.style.transform = `rotate(${s(t * 4) * 6}deg) translateY(${-bounce * 0.3}px)`;
  if (lArm) lArm.style.transform = `rotate(${s(t * 4) * 40}deg)`;
  if (rArm) rArm.style.transform = `rotate(${s(t * 4 + Math.PI) * 40}deg)`;

  // Lip-sync mouth
  const mouth = document.getElementById('finMouth');
  if (mouth) {
    mouth.setAttribute('ry', Math.max(2, vol / 255 * 12));
    mouth.setAttribute('rx', 7 + (1 - vol / 255) * 4);
  }

  // Body pulse on beat
  const creature = document.getElementById('finCreature');
  if (isBeat && creature) {
    creature.style.transform = `scale(${1 + vol / 500})`;
    setTimeout(() => { if (creature) creature.style.transform = 'scale(1)'; }, 100);

    // Beat ring
    const ring = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    ring.setAttribute('cx', 300); ring.setAttribute('cy', 230);
    ring.setAttribute('r', 35); ring.setAttribute('fill', 'none');
    ring.setAttribute('stroke', '#6c63ff'); ring.setAttribute('stroke-width', 1.5);
    ring.setAttribute('opacity', 0.5);
    const ringsEl = document.getElementById('finBeatRings');
    if (ringsEl && ringsEl.children.length < 10) {
      ringsEl.appendChild(ring);
      let rr = 35, ro = 0.5;
      const exp = () => { rr += 2.5; ro -= 0.012; if (ro <= 0) { ring.remove(); return; } ring.setAttribute('r', rr); ring.setAttribute('opacity', ro); requestAnimationFrame(exp); };
      requestAnimationFrame(exp);
    }

    // Emit particles from hands
    const lh = document.getElementById('finLeftHand');
    const rh = document.getElementById('finRightHand');
    const svgRect = document.getElementById('finaleSvg').getBoundingClientRect();
    const cRect = document.getElementById('finaleContainer').getBoundingClientRect();
    const scaleX = W / cRect.width;
    const scaleY = H / cRect.height;

    for (let hand of [lh, rh]) {
      if (!hand) continue;
      const hx = parseFloat(hand.getAttribute('cx')) / 600 * W;
      const hy = parseFloat(hand.getAttribute('cy')) / 500 * H;
      for (let i = 0; i < 8; i++) {
        const angle = Math.random() * Math.PI * 2;
        const speed = 1 + Math.random() * 3;
        finaleParticles.push({
          x: hx, y: hy,
          vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed,
          life: 0, maxLife: 40 + Math.random() * 30,
          size: 1.5 + Math.random() * 2,
          hue: Math.random() * 360
        });
      }
    }
  }

  // Update finale particles
  for (let i = finaleParticles.length - 1; i >= 0; i--) {
    const p = finaleParticles[i];
    p.life++;
    if (p.life > p.maxLife) { finaleParticles.splice(i, 1); continue; }
    p.vy += 0.05;
    p.vx *= 0.98; p.vy *= 0.98;
    p.x += p.vx; p.y += p.vy;
    const alpha = 1 - p.life / p.maxLife;
    fCtx.globalAlpha = alpha;
    fCtx.fillStyle = `hsl(${p.hue}, 80%, 65%)`;
    fCtx.beginPath();
    fCtx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    fCtx.fill();
    // trail
    fCtx.strokeStyle = `hsl(${p.hue}, 80%, 65%)`;
    fCtx.lineWidth = 0.8;
    fCtx.beginPath();
    fCtx.moveTo(p.x, p.y);
    fCtx.lineTo(p.x - p.vx * 2, p.y - p.vy * 2);
    fCtx.stroke();
  }
  if (finaleParticles.length > 200) finaleParticles.splice(0, finaleParticles.length - 200);
  fCtx.globalAlpha = 1;

  // Orbiting morphing shapes
  for (let i = 0; i < 4; i++) {
    const orbitAngle = t * 0.8 + (i * Math.PI / 2);
    const ox = W / 2 + Math.cos(orbitAngle) * Math.min(W, H) * 0.3;
    const oy = H / 2 + Math.sin(orbitAngle) * Math.min(W, H) * 0.25;
    const frame = (Math.floor(t * 12) + i * 30) % FBF_TOTAL_FRAMES;
    const verts = getFrameVertices(frame);
    const hue = (frame * 2 + i * 90) % 360;
    drawShape(fCtx, ox, oy, 25, verts, 0.7, 1);
    fCtx.fillStyle = `hsl(${hue}, 70%, 60%)`;
    fCtx.fill();
  }

  // Kinetic text cycling
  const texts = ['finText0', 'finText1', 'finText2', 'finText3'];
  const cycleTime = 2; // seconds per position
  const textIdx = Math.floor(t / cycleTime) % 4;
  texts.forEach((id, i) => {
    const el = document.getElementById(id);
    if (!el) return;
    const offset = (i - textIdx + 4) % 4;
    const fadeIn = offset === 0 ? Math.min((t % cycleTime) / 0.3, 1) : 0;
    const fadeOut = offset === 0 && (t % cycleTime) > cycleTime - 0.3 ? (cycleTime - (t % cycleTime)) / 0.3 : (offset === 0 ? 1 : 0);
    el.setAttribute('opacity', Math.min(fadeIn, fadeOut));
  });
}

// === MAIN ANIMATION LOOP ===
let globalTime = 0;
function mainLoop(timestamp) {
  globalTime = timestamp / 1000;

  // Creature rigging (Section 2)
  updateCreature(globalTime);

  // Lip-sync (Section 3)
  updateLipsync();

  // Particles (Section 5)
  updateParticles();

  // Finale (Section 6)
  updateFinale(globalTime);

  requestAnimationFrame(mainLoop);
}
requestAnimationFrame(mainLoop);
```

- [ ] **Step 3: Open in browser and verify**

Expected: Click "Start Finale" — hear rhythmic beats, creature dances, mouth syncs to audio, particles emit from hands on beats, 4 morphing shapes orbit, text labels cycle in/out. All other sections still work independently. Mouse affects particle flow.

- [ ] **Step 4: Commit**

```bash
git add animation-demo.html
git commit -m "feat: add combined finale section and main animation loop"
```

---

### Task 8: Final Polish + Verification

**Files:**
- Modify: `animation-demo.html` — scroll IntersectionObserver for autoplay, responsive tweaks

- [ ] **Step 1: Add scroll-triggered autoplay for lip-sync section**

Add at the end of the `<script>`, after the main loop:

```javascript
// Auto-start/stop sections based on visibility
const sectionObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    // Auto-start finale when scrolled into view
    if (entry.target.id === 'finale' && entry.isIntersecting && !finaleActive) {
      startFinale();
    }
    if (entry.target.id === 'finale' && !entry.isIntersecting && finaleActive) {
      stopFinale();
    }
  });
}, { threshold: 0.5 });
sectionObserver.observe(document.getElementById('finale'));
```

- [ ] **Step 2: Add responsive CSS for mobile**

Add at end of `<style>`:

```css
@media (max-width: 640px) {
  nav { gap: 2px; padding: 8px; }
  nav a { font-size: 11px; padding: 4px 8px; }
  .section { padding: 70px 16px 24px; }
  .section-heading { font-size: 24px; }
  .hero-title { font-size: 28px !important; }
  .controls { gap: 4px; }
  .btn { padding: 6px 12px; font-size: 11px; }
}
```

- [ ] **Step 3: Open in browser, test all sections top to bottom**

Verify:
1. Hero: letters animate in, typewriter runs, shapes float, scroll indicator pulses
2. Rigging: creature breathes in idle, wave/dance buttons work, eyes follow mouse, tail waves
3. Lip-sync: demo audio plays melody, mouth opens/closes, body pulses on beats, waveform renders
4. Frame-by-frame: shape morphs cycle, play/pause works, FPS buttons change speed, scrubber works
5. Particles: click spawns bursts, 3 types look distinct, attract/repel works, constellation lines visible
6. Finale: auto-starts on scroll, beats play, creature dances + lip-syncs, orbiting shapes, hand particles, cycling text

- [ ] **Step 4: Final commit**

```bash
git add animation-demo.html
git commit -m "feat: add scroll autoplay, responsive styles, polish animation demo"
```
