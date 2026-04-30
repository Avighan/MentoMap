# Animation Capabilities Demo — Design Spec

## Overview

A standalone HTML file that demonstrates advanced web animation capabilities through 6 scroll-through sections. Zero external dependencies or assets — everything is generated with code. Dark theme (deep navy/charcoal) background.

**File:** `animation-demo.html` (root of MentoApp)
**Tech:** Pure HTML + CSS + SVG + Canvas 2D + Web Audio API
**Target:** Modern browsers (Chrome, Firefox, Safari, Edge)

---

## Page Structure

Vertical scroll layout. Each section fills the viewport (100vh). Sticky top nav with section links. Smooth scroll-snap between sections.

### Section 1: Hero — Kinetic Typography

**Purpose:** Demonstrate CSS animation and DOM-based motion graphics.

- Title "Animation Capabilities" with staggered letter-by-letter fade-in
- Each letter has a continuous floating animation (translateY sine wave via CSS keyframes with varied delays)
- Individual letter hover: bounce + color change transition
- Background: slowly drifting geometric shapes (SVG circles, triangles) with CSS animation, parallax offset on scroll
- Subtitle types itself out character by character (JS-driven typewriter effect, ~50ms per character)
- Pulsing "scroll down" chevron indicator at bottom

### Section 2: SVG Rigging — Geometric Creature

**Purpose:** Demonstrate bone-based character rigging with SVG transform chains.

**Creature anatomy (all SVG):**
- Body: large central ellipse (~120x80)
- Head: circle (~50r) connected via neck joint (transform-origin at base of head)
- Arms (2): 3-segment chains (upper arm -> forearm -> hand), each a rounded rectangle, connected via transform-origin at joint points
- Legs (2): same 3-segment chain structure
- Eyes (2): smaller circles inside head, position driven by mouse cursor tracking (JS mousemove -> calculate angle -> translate eyes)
- Tail: SVG `<path>` bezier curve, 4 control points animated with sinusoidal wave (JS animates `d` attribute)

**Rigging system:**
- Each joint is an SVG `<g>` with `transform-origin` set at the joint point
- Parent-child nesting creates the bone hierarchy (rotating a shoulder rotates the entire arm chain)
- Animations are CSS keyframes applied to the joint `<g>` elements

**3 toggle-able animation states (buttons):**
1. **Idle:** gentle scale pulse on body (breathing), subtle arm/leg sway (small rotation oscillation)
2. **Wave:** right arm upper segment rotates -90deg, forearm oscillates +/-20deg (waving)
3. **Dance:** body translateY bounce (rhythmic), arms alternate up/down rotation, legs alternate lift

### Section 3: Lip-Sync — Audio-Driven Animation

**Purpose:** Demonstrate real-time audio analysis driving SVG morph targets.

**Two input modes (toggle buttons):**
- **Mic mode:** `navigator.mediaDevices.getUserMedia({audio: true})` captures mic input
- **Demo mode:** Web Audio API oscillators generate a short rhythmic melody (no external files). Pattern: alternating sine waves at 220Hz, 330Hz, 440Hz with amplitude envelope.

**Audio processing pipeline:**
1. Audio source -> `AnalyserNode` (fftSize: 256)
2. `getByteFrequencyData()` on each animation frame
3. Extract volume: average of frequency bins 0-20 (low/mid range)
4. Extract dominant frequency: bin with highest magnitude
5. Beat detection: volume > threshold (dynamically calibrated to 1.5x rolling average)

**Visual outputs:**
- **Mouth shape:** 5 SVG paths (closed / slightly-open / half-open / wide-open / O-shape). Volume level (0-255) maps to shape index (0-4). Smooth transition between shapes via SVG path morphing (interpolate `d` attribute control points).
- **Mouth width:** Dominant frequency maps to scaleX on mouth (low freq = wide 1.3x, high freq = narrow 0.7x)
- **Body pulse:** On beat detection, creature body scales to 1.1x then springs back (CSS transition 200ms ease-out)
- **Color rings:** On beat, spawn an SVG circle at creature center that scales up + fades out (ring radiates outward)
- **Waveform visualizer:** Canvas element below creature. Draws `getByteTimeDomainData()` as a green oscilloscope line on dark background, updating each frame.

The creature from Section 2 is reused here (same SVG structure) with the lip-sync layer added.

### Section 4: Frame-by-Frame — Canvas Sprite Animation

**Purpose:** Demonstrate procedural frame-by-frame animation on Canvas 2D.

**Morphing shape sequence:**
circle -> square -> triangle -> star (5-point) -> hexagon -> circle (loop)

Each shape is defined as a set of vertices (polar coordinates). Morphing interpolates between vertex sets using linear interpolation over N frames per transition.

**Rendering (Canvas 2D):**
- Current frame: draw shape with `fill` and `stroke`
- Motion trail: previous 5 frames drawn at decreasing opacity (0.6, 0.4, 0.3, 0.2, 0.1) and slightly smaller scale
- Color: hue rotates continuously (hsl, +2 degrees per frame)
- Frame rate: renders at selected FPS using `setTimeout` within `requestAnimationFrame` (not tied to display refresh)
- Classic animation feel: 12fps default gives that hand-drawn stutter

**Controls (HTML buttons/slider below canvas):**
- Play/Pause toggle button
- Frame scrubber: `<input type="range">` that lets user drag through the full animation timeline
- FPS selector: 3 buttons for 6fps / 12fps / 24fps, active state highlighted

**Rendering details:**
- Canvas size: 600x400 (CSS scaled to fit section)
- Shape centered in canvas
- Shape size: ~100px radius
- Frames per transition: 24 (so at 12fps, each morph takes 2 seconds)
- Total unique frames: 6 transitions x 24 frames = 144 frames (loop)

### Section 5: Particle System — Canvas Physics

**Purpose:** Demonstrate canvas-based physics simulation and interactive particles.

**Particle properties:**
```
{
  x, y,           // position
  vx, vy,         // velocity
  ax, ay,         // acceleration (ay = gravity)
  lifetime,       // frames remaining
  maxLifetime,    // for opacity calculation
  size,           // radius
  color,          // hsl string
  type,           // 'spark' | 'confetti' | 'bubble'
  rotation,       // for confetti tumble
  rotationSpeed   // for confetti
}
```

**Particle types (toggle via button):**
1. **Sparks:** size 2-4px, high initial velocity (random direction), gravity 0.1, friction 0.98, lifetime 60-120 frames. Render: circle + velocity trail (line from current pos to pos - velocity*3).
2. **Confetti:** size 6-10px, moderate velocity upward + spread, gravity 0.05, friction 0.99, lifetime 120-180 frames. Render: rotated rectangle, rotation increases each frame.
3. **Bubbles:** size 8-15px, low velocity upward, gravity -0.02 (float up), friction 0.995, lifetime 150-200 frames. Render: circle with highlight arc, wobble (sinusoidal x offset). At end of life: scale to 0 over 10 frames (pop).

**Interactions:**
- **Click/tap:** Spawn burst of 50-100 particles at click position with random velocities in all directions
- **Mouse proximity:** Toggle between attract/repel mode (button). Within 150px radius of cursor, apply force toward/away from cursor position. Force magnitude: inversely proportional to distance.
- **Connections:** Each frame, for all particle pairs within 100px, draw a line with opacity proportional to (100 - distance) / 100. Capped at checking nearest 50 particles per particle for performance.

**Ambient particles:** 30 particles spawned on load, drifting slowly (velocity 0.2-0.5), long lifetime (600+ frames), respawn when dead. These provide a baseline constellation effect.

**Canvas:** Full section width x height. `requestAnimationFrame` loop. Clear with semi-transparent black (rgba 0,0,0,0.1) for natural trail fade, or full clear depending on particle type.

### Section 6: Combined Finale

**Purpose:** All capabilities playing simultaneously on one screen.

**Layout:** Full viewport canvas + SVG overlay.

**Elements:**
- **Center:** Rigged geometric creature from Section 2, in dance state
- **Audio:** Web Audio oscillators playing a simple 4-beat rhythm loop (kick: 80Hz sine 100ms, snare: noise burst 50ms, hi-hat: high sine 800Hz 30ms). Auto-plays when section scrolls into view.
- **Lip-sync:** Creature mouth driven by the rhythm audio (same pipeline as Section 3)
- **Orbiting shapes:** 4 morphing shapes from Section 4, placed at 90-degree intervals, orbiting the creature at radius ~200px. Each at a different point in the morph cycle.
- **Particles:** Emitted from creature's hand positions on each beat. Spark type, burst of 20 particles per hand per beat.
- **Kinetic text:** Words "Rigging", "Lip-Sync", "Particles", "Frame-by-Frame" positioned at cardinal points. Each word fades in, floats for 2 seconds, fades out, cycles to next position. CSS animation.
- **Mouse interaction:** Cursor position affects particle flow (attraction) and creature eye tracking simultaneously.

**Footer text:** "All generated with code. Zero external assets." — fades in at bottom of section.

---

## Technical Constraints

- **Single HTML file:** All CSS in `<style>`, all JS in `<script>`, all SVG inline
- **Zero external dependencies:** No CDN links, no images, no audio files, no fonts beyond system defaults
- **Performance target:** 60fps on modern hardware. Particle count capped at 500 active. Canvas operations use `requestAnimationFrame`.
- **Responsive:** Sections scale to viewport. Canvas elements resize on window resize. SVG uses viewBox for scaling.
- **Accessibility:** Sections have ARIA labels. Reduced-motion media query disables non-essential animations. Audio requires user interaction to start (browser autoplay policy).
- **Browser support:** Chrome 90+, Firefox 90+, Safari 15+, Edge 90+

---

## File Size Estimate

~15-20KB uncompressed HTML. No external assets. Should load instantly.
