# Simulation Widget Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all 6 identified gaps in simulation game widgets — SVG bugs, loading speed, interactivity depth, missing sliders, loading failures, and image placeholders — making every widget mode a true sandbox simulation with at least one adjustable parameter.

**Architecture:** Extract shared SimulationControls library from existing widget patterns (SliderControl, Callout already exist in 3-44 widgets). Add SVG SafeGuard wrappers. Optimize loading with image prefetch + widget preload + shimmer skeletons. Upgrade all weak modes (tap-to-reveal) to have continuous sliders driving real-time physics/math calculations. Verify with Playwright E2E tests against production.

**Tech Stack:** React 18, Framer Motion, SVG, Playwright, Vite

---

## File Structure

### New Files
```
frontend-react/src/components/game/widgets/controls/
  index.js                    -- Re-exports all shared controls
  SimSlider.jsx               -- Continuous parameter slider (extracted from ForcesMotionWidget)
  SimCallout.jsx              -- Teaching text callout (extracted from 44 widgets)
  SimToggle.jsx               -- On/off toggle with label
  SimSelector.jsx             -- Multi-option picker (replaces discrete tap-to-reveal)
  SimPlayButton.jsx           -- Play/pause/reset animation controls
  SimBadge.jsx                -- Value display pill
  SafeSVG.jsx                 -- SVG element wrappers guarding against undefined attributes

frontend-react/src/components/game/widgets/useWidgetPreload.js  -- Hook: preloads widget chunks on game start

test-widgets-e2e.mjs         -- Playwright E2E test: loads all 13 games, verifies widgets render with controls
```

### Modified Files
```
frontend-react/src/components/game/renderers/SimulationRenderer.jsx
  -- SceneImage: add shimmer skeleton, dynamic label, static fallback image
  -- Add useWidgetPreload hook call

frontend-react/src/components/game/widgets/InteractiveSceneLayer.jsx
  -- Add image prefetch trigger on mount

frontend-react/src/components/game/widgets/CircuitBuilderWidget.jsx    -- Add 6+ sliders (voltage, resistance)
frontend-react/src/components/game/widgets/HeatTransferWidget.jsx      -- Add 6+ sliders (temperature, rate)
frontend-react/src/components/game/widgets/ReactionsLabWidget.jsx      -- Add 5+ sliders (pH, time, ratio)
frontend-react/src/components/game/widgets/EcosystemWidget.jsx         -- Add 5+ sliders (population, energy)
frontend-react/src/components/game/widgets/GeometryBuilderWidget.jsx   -- Add 6+ sliders (angle, dimensions)
frontend-react/src/components/game/widgets/MatterStatesWidget.jsx      -- Add 4+ sliders (temperature, pressure)
frontend-react/src/components/game/widgets/MixturesLabWidget.jsx       -- Add 4+ sliders (concentration, temp)
frontend-react/src/components/game/widgets/WeatherStationWidget.jsx    -- Add 3+ sliders (pressure, rate)
frontend-react/src/components/game/widgets/WaveSimWidget.jsx           -- Add 4+ sliders (wavelength, frequency)
frontend-react/src/components/game/widgets/AtomicModelWidget.jsx       -- Add 4+ sliders (Z, decay rate)
frontend-react/src/components/game/widgets/PressureFluidsWidget.jsx    -- Add 2-3 sliders (polish weak modes)
frontend-react/src/components/game/widgets/OpticsAdvancedWidget.jsx    -- Add 2-3 sliders (polish weak modes)
frontend-react/src/components/game/widgets/PlantGrowthWidget.jsx       -- Add 2-3 sliders (polish weak modes)
```

---

### Task 1: Create Shared SimulationControls Library

**Files:**
- Create: `frontend-react/src/components/game/widgets/controls/SimSlider.jsx`
- Create: `frontend-react/src/components/game/widgets/controls/SimCallout.jsx`
- Create: `frontend-react/src/components/game/widgets/controls/SimToggle.jsx`
- Create: `frontend-react/src/components/game/widgets/controls/SimSelector.jsx`
- Create: `frontend-react/src/components/game/widgets/controls/SimPlayButton.jsx`
- Create: `frontend-react/src/components/game/widgets/controls/SimBadge.jsx`
- Create: `frontend-react/src/components/game/widgets/controls/SafeSVG.jsx`
- Create: `frontend-react/src/components/game/widgets/controls/index.js`

- [ ] **Step 1: Create controls directory and SimSlider**

```jsx
// SimSlider.jsx — Extracted from ForcesMotionWidget's SliderControl
// Shared continuous parameter control for ALL widget modes
import { motion } from 'framer-motion';

const DEFAULTS = {
  bg: '#0F172A',
  text: '#E2E8F0',
  textDim: '#94A3B8',
};

export default function SimSlider({
  label,
  value,
  min = 0,
  max = 100,
  step = 1,
  unit = '',
  color = '#F59E0B',
  onChange,
  disabled = false,
  showValue = true,
  size = 'md', // 'sm' | 'md'
}) {
  const textSize = size === 'sm' ? 'text-[9px]' : 'text-[10px]';
  const labelWidth = size === 'sm' ? 'w-16' : 'w-20';
  const valueWidth = size === 'sm' ? 'w-10' : 'w-14';
  const trackHeight = size === 'sm' ? 'h-1' : 'h-1.5';
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className={`flex items-center gap-2 ${size === 'sm' ? 'mt-0.5' : 'mt-1'}`}>
      <span className={`${textSize} font-bold ${labelWidth} shrink-0`}
        style={{ color: DEFAULTS.textDim }}>{label}</span>
      <div className="flex-1 relative">
        <div className={`w-full ${trackHeight} rounded-full`}
          style={{ background: `${color}20` }}>
          <motion.div className={`${trackHeight} rounded-full`}
            style={{ background: `linear-gradient(to right, ${color}80, ${color})`, width: `${pct}%` }}
            animate={{ width: `${pct}%` }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }} />
        </div>
        <input
          type="range" min={min} max={max} step={step} value={value}
          onChange={e => onChange(Number(e.target.value))}
          disabled={disabled}
          className="absolute inset-0 w-full opacity-0 cursor-pointer"
          style={{ height: '20px', marginTop: '-4px' }}
        />
      </div>
      {showValue && (
        <span className={`${textSize} font-black ${valueWidth} text-right shrink-0`}
          style={{ color: DEFAULTS.text }}>{value}{unit}</span>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create SimCallout**

```jsx
// SimCallout.jsx — Teaching text with icon/color variants
export default function SimCallout({
  emoji = 'info',
  text,
  color = '#F59E0B',
  small = false,
  type = 'info', // 'info' | 'warning' | 'success' | 'formula'
}) {
  const TYPE_COLORS = {
    info: '#3B82F6',
    warning: '#EF4444',
    success: '#10B981',
    formula: '#8B5CF6',
  };
  const c = TYPE_COLORS[type] || color;
  const EMOJI_MAP = {
    info: '\u{1F4A1}', warning: '\u26A0\uFE0F',
    success: '\u2705', formula: '\u{1F4D0}',
  };
  const icon = typeof emoji === 'string' && emoji.length <= 8 ? emoji : EMOJI_MAP[type] || '\u{1F4A1}';

  return (
    <div className={`flex items-start gap-2 rounded-xl px-3 ${small ? 'py-1.5' : 'py-2'} mt-2`}
      style={{ background: c + '15', border: `1px solid ${c}30` }}>
      <span className={small ? 'text-sm' : 'text-base'}>{icon}</span>
      <p className={`${small ? 'text-[10px]' : 'text-[11px]'} leading-relaxed font-medium`}
        style={{ color: '#E2E8F0' }}>{text}</p>
    </div>
  );
}
```

- [ ] **Step 3: Create SimToggle, SimSelector, SimPlayButton, SimBadge**

```jsx
// SimToggle.jsx
import { motion } from 'framer-motion';

export default function SimToggle({ label, value, onLabel = 'ON', offLabel = 'OFF', onChange, color = '#F59E0B' }) {
  return (
    <div className="flex items-center gap-2 mt-1">
      <span className="text-[10px] font-bold w-20 shrink-0" style={{ color: '#94A3B8' }}>{label}</span>
      <button onClick={() => onChange(!value)}
        className="relative w-10 h-5 rounded-full transition-colors"
        style={{ background: value ? color : '#334155' }}>
        <motion.div className="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow"
          animate={{ left: value ? 22 : 2 }}
          transition={{ type: 'spring', stiffness: 400, damping: 25 }} />
      </button>
      <span className="text-[10px] font-bold" style={{ color: value ? color : '#64748B' }}>
        {value ? onLabel : offLabel}
      </span>
    </div>
  );
}
```

```jsx
// SimSelector.jsx — Multi-option picker replacing discrete tap-to-reveal
export default function SimSelector({ options, selected, onChange, columns = 3, color = '#F59E0B' }) {
  return (
    <div className="grid gap-1 mt-1" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
      {options.map(opt => (
        <button key={opt.value} onClick={() => onChange(opt.value)}
          className="px-2 py-1 rounded-lg text-[9px] font-bold transition-all"
          style={{
            background: selected === opt.value ? color + '30' : '#1E293B',
            border: `1px solid ${selected === opt.value ? color : '#334155'}`,
            color: selected === opt.value ? color : '#94A3B8',
          }}>
          {opt.emoji && <span className="mr-1">{opt.emoji}</span>}
          {opt.label}
        </button>
      ))}
    </div>
  );
}
```

```jsx
// SimPlayButton.jsx
export default function SimPlayButton({ playing, onPlay, onPause, onReset, color = '#F59E0B' }) {
  return (
    <div className="flex items-center gap-1 mt-1">
      <button onClick={playing ? onPause : onPlay}
        className="px-3 py-1 rounded-lg text-[10px] font-bold"
        style={{ background: color, color: '#0F172A' }}>
        {playing ? '\u23F8 Pause' : '\u25B6 Play'}
      </button>
      {onReset && (
        <button onClick={onReset}
          className="px-2 py-1 rounded-lg text-[10px] font-bold"
          style={{ background: '#334155', color: '#94A3B8' }}>
          \u21BB Reset
        </button>
      )}
    </div>
  );
}
```

```jsx
// SimBadge.jsx — Value display pill
export default function SimBadge({ label, value, unit = '', color = '#F59E0B', size = 'md' }) {
  const pad = size === 'sm' ? 'px-2 py-0.5' : 'px-3 py-1';
  const text = size === 'sm' ? 'text-[9px]' : 'text-[10px]';
  return (
    <div className={`inline-flex items-center gap-1 ${pad} rounded-lg`}
      style={{ background: color + '20', border: `1px solid ${color}40` }}>
      {label && <span className={`${text} font-medium`} style={{ color: '#94A3B8' }}>{label}</span>}
      <span className={`${text} font-black`} style={{ color }}>{value}{unit}</span>
    </div>
  );
}
```

- [ ] **Step 4: Create SafeSVG wrappers**

```jsx
// SafeSVG.jsx — Guards against undefined SVG attributes
// Prevents console errors: "Expected length, undefined"

export function SafeCircle({ cx, cy, r, ...rest }) {
  if (cx == null || cy == null || r == null || isNaN(cx) || isNaN(cy) || isNaN(r)) return null;
  return <circle cx={cx} cy={cy} r={r} {...rest} />;
}

export function SafeEllipse({ cx, cy, rx, ry, ...rest }) {
  if (cx == null || cy == null || rx == null || ry == null) return null;
  if (isNaN(cx) || isNaN(cy) || isNaN(rx) || isNaN(ry)) return null;
  return <ellipse cx={cx} cy={cy} rx={rx} ry={ry} {...rest} />;
}

export function SafeRect({ x, y, width, height, ...rest }) {
  if (width == null || height == null || isNaN(width) || isNaN(height)) return null;
  return <rect x={x ?? 0} y={y ?? 0} width={width} height={height} {...rest} />;
}

export function SafeLine({ x1, y1, x2, y2, ...rest }) {
  if (x1 == null || y1 == null || x2 == null || y2 == null) return null;
  if (isNaN(x1) || isNaN(y1) || isNaN(x2) || isNaN(y2)) return null;
  return <line x1={x1} y1={y1} x2={x2} y2={y2} {...rest} />;
}

export function SafePath({ d, ...rest }) {
  if (!d || typeof d !== 'string' || d.includes('undefined') || d.includes('NaN')) return null;
  return <path d={d} {...rest} />;
}

// Motion variants (for Framer Motion animated SVG elements)
export function safeAnimate(props) {
  const cleaned = {};
  for (const [key, val] of Object.entries(props)) {
    if (val != null && !isNaN(val) && val !== undefined) {
      cleaned[key] = val;
    }
  }
  return cleaned;
}
```

- [ ] **Step 5: Create index.js re-export**

```js
// index.js
export { default as SimSlider } from './SimSlider';
export { default as SimCallout } from './SimCallout';
export { default as SimToggle } from './SimToggle';
export { default as SimSelector } from './SimSelector';
export { default as SimPlayButton } from './SimPlayButton';
export { default as SimBadge } from './SimBadge';
export { SafeCircle, SafeEllipse, SafeRect, SafeLine, SafePath, safeAnimate } from './SafeSVG';
```

- [ ] **Step 6: Commit**

```bash
git add frontend-react/src/components/game/widgets/controls/
git commit -m "feat: create shared SimulationControls library

Extract SliderControl/Callout patterns from ForcesMotionWidget into
reusable controls. Add SafeSVG wrappers to prevent undefined attribute
errors. Components: SimSlider, SimCallout, SimToggle, SimSelector,
SimPlayButton, SimBadge, SafeSVG."
```

---

### Task 2: Loading Optimization

**Files:**
- Create: `frontend-react/src/components/game/widgets/useWidgetPreload.js`
- Modify: `frontend-react/src/components/game/renderers/SimulationRenderer.jsx` (SceneImage component ~lines 119-160)
- Modify: `frontend-react/src/components/game/widgets/InteractiveSceneLayer.jsx`

- [ ] **Step 1: Create useWidgetPreload hook**

```js
// useWidgetPreload.js — Preloads widget chunks and prefetches images on game start
import { useEffect } from 'react';
import WidgetRegistry from './WidgetRegistry';

export default function useWidgetPreload(gameData, gameId) {
  useEffect(() => {
    if (!gameData?.rounds) return;

    // 1. Preload all widget chunks used in this game
    const widgetTypes = new Set();
    gameData.rounds.forEach(round => {
      const type = round.scene_widget?.type;
      if (type && WidgetRegistry[type]) widgetTypes.add(type);
    });

    // Trigger lazy imports on idle
    if (typeof requestIdleCallback === 'function') {
      requestIdleCallback(() => {
        widgetTypes.forEach(type => {
          try {
            // Access the lazy component to trigger chunk download
            const LazyComponent = WidgetRegistry[type];
            if (LazyComponent && LazyComponent._init) {
              LazyComponent._init(LazyComponent._payload);
            }
          } catch { /* chunk already loaded or loading */ }
        });
      });
    }

    // 2. Prefetch first 3 round images (fire-and-forget)
    const roundsToPreload = gameData.rounds.slice(0, 3);
    roundsToPreload.forEach(round => {
      const roundId = round.round_id || round.id;
      if (roundId && gameId) {
        // Fire and forget — don't await, just warm the cache
        fetch(`/api/games/${gameId}/rounds/${roundId}/story-image`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('auth_token')}` },
        }).catch(() => {});
      }
    });
  }, [gameData, gameId]);
}
```

- [ ] **Step 2: Update SceneImage with shimmer skeleton and dynamic label**

In SimulationRenderer.jsx, find the SceneImage component (around lines 119-160) and update the loading state:

Replace the loading spinner inside SceneImage:
```jsx
// OLD loading state:
{loading && (
  <div className="absolute inset-0 flex items-center justify-center">
    <div className="w-8 h-8 border-2 rounded-full animate-spin" />
  </div>
)}

// NEW shimmer skeleton:
{loading && (
  <div className="absolute inset-0 overflow-hidden rounded-2xl">
    <div className="w-full h-full animate-pulse"
      style={{
        background: 'linear-gradient(90deg, #1a1a2e 25%, #2a2a4e 50%, #1a1a2e 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite',
      }} />
    <style>{`@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }`}</style>
  </div>
)}
```

Replace the hardcoded "The Mento Map" overlay label:
```jsx
// OLD:
<div className="absolute top-3 left-3 ...">The Mento Map</div>

// NEW:
<div className="absolute top-3 left-3 px-3 py-1 rounded-lg text-xs font-bold"
  style={{ background: 'rgba(0,0,0,0.6)', color: loading ? '#FDE68A' : '#fff' }}>
  {loading ? '\u{1F3A8} Painting the scene...' : 'The Mento Map'}
</div>
```

Add static fallback image support — in the useEffect where image URL is set, add fallback before Pollinations:
```jsx
// After the try/catch for getStoryImage, before Pollinations fallback:
// Check for static fallback from game config
if (!cancelled && !url) {
  const staticFallback = gameData?.ai_image_config?.default_scene_image;
  if (staticFallback) {
    setUrl(staticFallback);
    setLoading(false);
    return;
  }
}
```

- [ ] **Step 3: Wire useWidgetPreload in SimulationRenderer**

At the top of the SimulationRenderer component function, add:
```jsx
import useWidgetPreload from '../widgets/useWidgetPreload';

// Inside the component:
useWidgetPreload(gameData, gameId);
```

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/components/game/widgets/useWidgetPreload.js
git add frontend-react/src/components/game/renderers/SimulationRenderer.jsx
git commit -m "perf: add widget preloading + image prefetch + shimmer skeleton

- Preload all widget chunks used in game on idle
- Prefetch first 3 round images on game start
- Replace gray spinner with shimmer skeleton animation
- Dynamic 'Painting the scene...' label during load
- Static fallback image support from game config"
```

---

### Task 3: SVG Bug Fixes — Sweep All Widgets

**Files:** All 13 widget files listed in the File Structure above.

The console errors show `<circle> attribute cx: Expected length, "undefined"` in 10 games. The fix pattern is the same for all:

1. Import SafeSVG components
2. Replace `<circle>` with `<SafeCircle>` (and similarly for ellipse, rect, line, path)
3. OR add `?? 0` fallbacks to dynamic attribute calculations

- [ ] **Step 1: Fix CircuitBuilderWidget SVG errors**

Open `CircuitBuilderWidget.jsx`. Search for all `<motion.circle` and `<circle` with dynamic attributes. The main issue is the ElectronDots pattern where arrays are passed to animate:

```jsx
// Find the electron dots animation pattern and fix:
// BEFORE (broken):
// <motion.circle animate={{ cx: xs, cy: ys }} />
// where xs/ys are arrays

// AFTER (fixed):
// Use individual circles for each electron dot position, or use
// keyframes properly:
{Array.from({ length: count }).map((_, i) => {
  const progress = ((phase + i / count) % 1);
  const idx = Math.floor(progress * (points.length - 1));
  const nextIdx = Math.min(idx + 1, points.length - 1);
  const t = (progress * (points.length - 1)) - idx;
  const cx = (points[idx]?.[0] ?? 0) + ((points[nextIdx]?.[0] ?? 0) - (points[idx]?.[0] ?? 0)) * t;
  const cy = (points[idx]?.[1] ?? 0) + ((points[nextIdx]?.[1] ?? 0) - (points[idx]?.[1] ?? 0)) * t;
  return <circle key={i} cx={cx || 0} cy={cy || 0} r={2} fill="#60A5FA" opacity={active ? 0.8 : 0} />;
})}
```

Also add `?? 0` guards to ALL dynamic SVG attributes in every mode function:
```jsx
// Pattern: anywhere you see dynamic cx, cy, r, x, y, width, height:
// BEFORE:
<circle cx={someCalc} cy={otherCalc} r={radius} />
// AFTER:
<circle cx={someCalc ?? 0} cy={otherCalc ?? 0} r={radius ?? 0} />
```

- [ ] **Step 2: Fix remaining widgets with SVG errors**

Apply the same `?? 0` guard pattern to dynamic SVG attributes in:
- `ReactionsLabWidget.jsx` — fix circle/ellipse attributes in pH scale dots
- `EcosystemWidget.jsx` — fix circle cx/cy in organism positioning
- `SoundWavesWidget.jsx` — fix ellipse rx in wave visualization, circle cx in particle animation
- `KinematicsWidget.jsx` — fix circle cy in waypoint positioning
- `AtomicModelWidget.jsx` — fix circle cx/cy in electron orbit animation
- `OpticsAdvancedWidget.jsx` — fix rect width in lens rendering
- `WeatherStationWidget.jsx` — fix circle r in precipitation particles, rect height/width in barometer

For each file, search for: `cx={`, `cy={`, `r={`, `rx={`, `ry={`, `x1={`, `y1={`, `x2={`, `y2={`, `width={`, `height={`, `d={`

Any that use a variable (not a literal number), add `?? 0` fallback. For `d=` path attributes, wrap in SafePath or add a check: `d={pathStr || 'M0,0'}`.

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/components/game/widgets/*.jsx
git commit -m "fix: guard all dynamic SVG attributes against undefined values

Add ?? 0 fallbacks to cx, cy, r, rx, ry, x, y, width, height
attributes across all 13 widget files. Fix ElectronDots array animation
pattern in CircuitBuilderWidget. Eliminates all 'Expected length, undefined'
console errors."
```

---

### Task 4: Upgrade CircuitBuilderWidget (CRITICAL — 0 sliders currently)

**File:** `frontend-react/src/components/game/widgets/CircuitBuilderWidget.jsx`

Add sliders to 6 modes. Import shared controls at top of file:

```jsx
import { SimSlider, SimCallout, SimBadge, SimToggle } from './controls';
```

- [ ] **Step 1: Upgrade basic_circuit mode — add voltage slider**

Find the `BasicCircuit` (or `basic_circuit`) mode function. Add a voltage slider that controls electron flow speed and bulb brightness:

```jsx
function BasicCircuit() {
  const [voltage, setVoltage] = useState(9);
  const [closed, setClosed] = useState(false);
  const current = closed ? voltage / 100 : 0; // I = V/R, R=100 ohms
  const brightness = Math.min(1, current * 10);
  const electronSpeed = closed ? 0.5 + current * 20 : 0;

  return (
    <>
      <svg viewBox="0 0 400 300" className="w-full rounded-xl" style={{ background: BG }}>
        {/* Battery */}
        <rect x={40} y={110} width={30} height={80} rx={4} fill="#334155" stroke={ACCENT} strokeWidth={1.5} />
        <text x={55} y={105} textAnchor="middle" fill={ACCENT} fontSize={10} fontWeight="bold">+</text>
        <text x={55} y={205} textAnchor="middle" fill="#60A5FA" fontSize={10} fontWeight="bold">-</text>
        <text x={55} y={155} textAnchor="middle" fill={TXT} fontSize={9} fontWeight="bold">{voltage}V</text>

        {/* Wires */}
        <line x1={70} y1={130} x2={200} y2={130} stroke={closed ? ACCENT : '#475569'} strokeWidth={2} />
        <line x1={250} y1={130} x2={340} y2={130} stroke={closed ? ACCENT : '#475569'} strokeWidth={2} />
        <line x1={340} y1={130} x2={340} y2={170} stroke={closed ? ACCENT : '#475569'} strokeWidth={2} />
        <line x1={340} y1={170} x2={70} y2={170} stroke={closed ? ACCENT : '#475569'} strokeWidth={2} />
        <line x1={70} y1={170} x2={40} y2={170} stroke={closed ? ACCENT : '#475569'} strokeWidth={2} />

        {/* Switch */}
        <g onClick={() => setClosed(!closed)} style={{ cursor: 'pointer' }}>
          <circle cx={225} cy={130} r={8} fill={closed ? '#10B981' : '#EF4444'} />
          <text x={225} y={133} textAnchor="middle" fill="white" fontSize={8} fontWeight="bold">
            {closed ? 'ON' : 'OFF'}
          </text>
        </g>

        {/* Bulb — brightness from current */}
        <circle cx={340} cy={150} r={15} fill={`rgba(253, 224, 71, ${brightness})`}
          stroke={ACCENT} strokeWidth={1.5} />
        {brightness > 0.3 && (
          <circle cx={340} cy={150} r={25} fill={`rgba(253, 224, 71, ${brightness * 0.3})`} />
        )}
        <text x={340} y={154} textAnchor="middle" fill={brightness > 0.5 ? '#0F172A' : TXT}
          fontSize={8} fontWeight="bold">
          {brightness > 0.5 ? '\u{1F4A1}' : '\u26AB'}
        </text>

        {/* Electron flow dots */}
        {closed && Array.from({ length: 6 }).map((_, i) => {
          const t = ((Date.now() * electronSpeed / 1000 + i * 0.15) % 1);
          const pathLen = 600; // approximate wire path length
          let cx = 0, cy = 0;
          const pos = t * pathLen;
          if (pos < 200) { cx = 70 + pos * 0.65; cy = 130; }
          else if (pos < 300) { cx = 340; cy = 130 + (pos - 200) * 0.4; }
          else { cx = 340 - (pos - 300) * 0.9; cy = 170; }
          return <circle key={i} cx={cx ?? 0} cy={cy ?? 0} r={2.5} fill="#60A5FA" opacity={0.8} />;
        })}

        {/* Labels */}
        <SimBadge label="Current" value={`${(current * 1000).toFixed(0)}`} unit="mA" color={ACCENT} />
      </svg>

      {/* Controls below SVG */}
      <SimSlider label="Voltage" value={voltage} min={1} max={24} step={0.5} unit="V"
        color={ACCENT} onChange={setVoltage} />
      <SimCallout
        emoji="\u26A1"
        text={closed
          ? `Current = V/R = ${voltage}V / 100\u03A9 = ${(current * 1000).toFixed(0)}mA. ${brightness > 0.7 ? 'Bulb is BRIGHT!' : brightness > 0.3 ? 'Bulb is dim.' : 'Very little current flowing.'}`
          : 'Circuit is OPEN. Click the switch to close it and let current flow!'}
      />
    </>
  );
}
```

- [ ] **Step 2: Upgrade ohms_law mode — add V and R sliders with live I=V/R**

```jsx
function OhmsLaw() {
  const [voltage, setVoltage] = useState(9);
  const [resistance, setResistance] = useState(100);
  const current = resistance > 0 ? voltage / resistance : 0;
  const power = voltage * current;

  return (
    <>
      <svg viewBox="0 0 400 300" className="w-full rounded-xl" style={{ background: BG }}>
        {/* Triangle visualization: V = I × R */}
        <polygon points="200,40 100,220 300,220" fill="none" stroke={ACCENT} strokeWidth={2} />
        <text x={200} y={80} textAnchor="middle" fill={ACCENT} fontSize={18} fontWeight="bold">V</text>
        <text x={140} y={200} textAnchor="middle" fill="#60A5FA" fontSize={18} fontWeight="bold">I</text>
        <text x={260} y={200} textAnchor="middle" fill="#F87171" fontSize={18} fontWeight="bold">R</text>
        <line x1={140} y1={160} x2={260} y2={160} stroke={TXT2} strokeWidth={1} strokeDasharray="4" />

        {/* Live values */}
        <text x={200} y={110} textAnchor="middle" fill={TXT} fontSize={12}>{voltage}V</text>
        <text x={140} y={245} textAnchor="middle" fill={TXT} fontSize={12}>{current.toFixed(3)}A</text>
        <text x={260} y={245} textAnchor="middle" fill={TXT} fontSize={12}>{resistance}\u03A9</text>

        {/* Formula */}
        <text x={200} y={275} textAnchor="middle" fill={ACCENT} fontSize={11} fontWeight="bold">
          I = V/R = {voltage}/{resistance} = {current.toFixed(3)}A
        </text>

        {/* Power badge */}
        <rect x={300} y={40} width={90} height={35} rx={8} fill={ACCENT + '20'} stroke={ACCENT + '40'} />
        <text x={345} y={55} textAnchor="middle" fill={TXT2} fontSize={8}>Power</text>
        <text x={345} y={69} textAnchor="middle" fill={ACCENT} fontSize={11} fontWeight="bold">
          {power.toFixed(2)}W
        </text>
      </svg>

      <SimSlider label="Voltage (V)" value={voltage} min={1} max={24} step={0.5} unit="V"
        color={ACCENT} onChange={setVoltage} />
      <SimSlider label="Resistance (R)" value={resistance} min={10} max={1000} step={10} unit="\u03A9"
        color="#F87171" onChange={setResistance} />
      <SimCallout
        emoji="\u{1F4D0}"
        text={`Ohm's Law: V = I \u00D7 R. With ${voltage}V across ${resistance}\u03A9, current = ${(current * 1000).toFixed(1)}mA. Power dissipated = ${power.toFixed(2)}W.${power > 5 ? ' \u26A0\uFE0F High power! Resistor is getting hot.' : ''}`}
        type="formula"
      />
    </>
  );
}
```

- [ ] **Step 3: Apply same pattern to remaining circuit modes**

Add sliders to these modes following the same pattern:

| Mode | Add | Physics |
|------|-----|---------|
| `series_circuit` | Voltage slider + bulb count selector | V_each = V_total / n, brightness decreases with more bulbs |
| `parallel_circuit` | Voltage slider + branch toggle | I_total = sum(V/R_i), each branch independently bright |
| `voltage_meter` | Voltage slider + resistance selector | Reading = V across component |
| `kirchhoff_law` | Voltage source slider + 2 resistance sliders | KVL: V = V_R1 + V_R2, KCL: I_in = I_out |
| `power_energy` | Voltage + time sliders | E = P * t = V^2/R * t |
| `combined_circuit` | Voltage slider + series/parallel toggle | Combined resistance calculation |

Each mode: `useState` for parameters → physics formula → SVG visualization → `SimSlider` controls → `SimCallout` explanation.

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/components/game/widgets/CircuitBuilderWidget.jsx
git commit -m "feat: upgrade CircuitBuilder with voltage/resistance sliders

All 14 modes now have at least one continuous control. Key upgrades:
- basic_circuit: voltage slider + electron flow animation
- ohms_law: V & R sliders with live I=V/R calculation
- series/parallel: voltage slider showing current distribution
- kirchhoff: multi-slider node voltage verification"
```

---

### Task 5: Upgrade HeatTransferWidget (CRITICAL — 0 sliders)

**File:** `frontend-react/src/components/game/widgets/HeatTransferWidget.jsx`

- [ ] **Step 1: Add sliders to 6 key modes**

Import shared controls, then upgrade these modes:

| Mode | Slider | Physics | Visualization |
|------|--------|---------|---------------|
| `conduction` | Temperature slider (20-200\u00B0C) | Heat flow rate Q = kA(T_hot - T_cold)/L | Animated particles vibrating faster at hot end, color gradient |
| `convection` | Heat source temp slider | Hotter fluid rises faster (v \u221D \u0394T) | Particle speed proportional to temperature |
| `radiation` | Source temp slider | Stefan-Boltzmann: P = \u03C3AT^4 | Wave intensity/color changes with temperature |
| `equilibrium` | Time multiplier slider + initial temp slider | T(t) = T_env + (T_0 - T_env)e^(-kt) | Newton's law of cooling animation |
| `specific_heat` | Heat input slider + substance selector | \u0394T = Q/(mc), different c for water/oil/iron | Three beakers heating at different rates |
| `insulation` | Outside temp slider + wall thickness slider | R-value = thickness/conductivity | Heat loss rate visualization |

Example implementation for `conduction` mode:

```jsx
function Conduction() {
  const [hotTemp, setHotTemp] = useState(100);
  const k = 205; // thermal conductivity of aluminum (W/m\u00B7K)
  const coldTemp = 20;
  const heatFlow = k * (hotTemp - coldTemp) / 100; // simplified Q/t
  const particleSpeed = 0.5 + (hotTemp / 200) * 3;

  return (
    <>
      <svg viewBox="0 0 400 300" className="w-full rounded-xl" style={{ background: BG }}>
        {/* Metal bar gradient */}
        <defs>
          <linearGradient id="heatGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={`hsl(${Math.max(0, 60 - hotTemp * 0.6)}, 90%, 50%)`} />
            <stop offset="100%" stopColor="#3B82F6" />
          </linearGradient>
        </defs>
        <rect x={50} y={120} width={300} height={40} rx={4} fill="url(#heatGrad)" stroke={TXT2} />

        {/* Temperature labels */}
        <text x={50} y={115} fill="#EF4444" fontSize={11} fontWeight="bold">{hotTemp}\u00B0C</text>
        <text x={320} y={115} fill="#3B82F6" fontSize={11} fontWeight="bold">{coldTemp}\u00B0C</text>

        {/* Animated particles */}
        {Array.from({ length: 20 }).map((_, i) => {
          const xBase = 60 + (i % 10) * 30;
          const row = Math.floor(i / 10);
          const yBase = 130 + row * 20;
          const tempAtX = hotTemp - (hotTemp - coldTemp) * ((xBase - 60) / 280);
          const vibration = (tempAtX / 200) * 6;
          return (
            <circle key={i} cx={xBase} cy={yBase} r={3}
              fill={`hsl(${Math.max(0, 60 - tempAtX * 0.6)}, 90%, 60%)`}
              opacity={0.8}>
              <animate attributeName="cx" values={`${xBase - vibration};${xBase + vibration};${xBase - vibration}`}
                dur={`${Math.max(0.1, 1 - tempAtX / 300)}s`} repeatCount="indefinite" />
              <animate attributeName="cy" values={`${yBase - vibration};${yBase + vibration};${yBase - vibration}`}
                dur={`${Math.max(0.1, 1.2 - tempAtX / 300)}s`} repeatCount="indefinite" />
            </circle>
          );
        })}

        {/* Arrow showing heat flow direction */}
        <text x={200} y={185} textAnchor="middle" fill={ACCENT} fontSize={10}>
          Heat flow \u2192 {heatFlow.toFixed(0)} W/m\u00B2
        </text>
        <text x={200} y={30} textAnchor="middle" fill={TXT} fontSize={12} fontWeight="bold">
          Conduction: Heat Through Direct Contact
        </text>
      </svg>

      <SimSlider label="Hot end" value={hotTemp} min={30} max={300} step={5} unit="\u00B0C"
        color="#EF4444" onChange={setHotTemp} />
      <SimCallout
        emoji="\u{1F525}"
        text={`Particles at the hot end (${hotTemp}\u00B0C) vibrate fast and pass energy to cooler neighbors. Heat flows from hot \u2192 cold at ${heatFlow.toFixed(0)} W/m\u00B2. ${hotTemp > 200 ? 'Extreme heat! Particles vibrating intensely.' : 'Notice how particles vibrate more at the hot end.'}`}
      />
    </>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/HeatTransferWidget.jsx
git commit -m "feat: upgrade HeatTransfer with temperature/rate sliders

6 modes upgraded: conduction, convection, radiation, equilibrium,
specific_heat, insulation. Real physics: Q=kA\u0394T/L, Newton cooling,
Stefan-Boltzmann law. Particle animations driven by temperature."
```

---

### Task 6: Upgrade ReactionsLabWidget (CRITICAL — 0 sliders)

**File:** `frontend-react/src/components/game/widgets/ReactionsLabWidget.jsx`

- [ ] **Step 1: Upgrade 5 key modes with continuous controls**

| Mode | Slider | Physics |
|------|--------|---------|
| `ph_scale` | Continuous pH drag slider (0-14) | Color changes based on pH, indicator reactions |
| `reaction_intro` | Temperature slider | Reaction rate \u221D temperature (Arrhenius) |
| `neutralization` | Acid volume slider | Titration: moles acid = moles base at endpoint |
| `rust_corrosion` | Time slider + humidity slider | Corrosion rate = f(moisture, O2) |
| `combustion` | Fuel/air ratio slider | Stoichiometric ratio, incomplete vs complete combustion |

The pH slider is the highest priority — replace discrete dot clicking with continuous slider:

```jsx
function PhScale() {
  const [ph, setPh] = useState(7);
  const substances = [
    { name: 'Battery Acid', ph: 1 },
    { name: 'Lemon Juice', ph: 2.5 },
    { name: 'Vinegar', ph: 3 },
    { name: 'Coffee', ph: 5 },
    { name: 'Milk', ph: 6.5 },
    { name: 'Pure Water', ph: 7 },
    { name: 'Baking Soda', ph: 8.5 },
    { name: 'Soap', ph: 10 },
    { name: 'Bleach', ph: 12.5 },
    { name: 'Drain Cleaner', ph: 14 },
  ];

  const phColor = (p) => {
    if (p < 3) return '#EF4444';
    if (p < 6) return '#F97316';
    if (p < 8) return '#22C55E';
    if (p < 11) return '#3B82F6';
    return '#7C3AED';
  };

  const closest = substances.reduce((a, b) => Math.abs(b.ph - ph) < Math.abs(a.ph - ph) ? b : a);
  const nature = ph < 7 ? 'ACIDIC' : ph > 7 ? 'BASIC (Alkaline)' : 'NEUTRAL';

  return (
    <>
      <svg viewBox="0 0 400 300" className="w-full rounded-xl" style={{ background: BG }}>
        <text x={200} y={25} textAnchor="middle" fill={TXT} fontSize={13} fontWeight="bold">
          The pH Scale
        </text>

        {/* pH bar */}
        <defs>
          <linearGradient id="phGrad">
            <stop offset="0%" stopColor="#EF4444" />
            <stop offset="25%" stopColor="#F97316" />
            <stop offset="50%" stopColor="#22C55E" />
            <stop offset="75%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#7C3AED" />
          </linearGradient>
        </defs>
        <rect x={30} y={50} width={340} height={30} rx={6} fill="url(#phGrad)" opacity={0.8} />

        {/* pH numbers */}
        {Array.from({ length: 15 }).map((_, i) => (
          <text key={i} x={30 + i * (340 / 14)} y={95} textAnchor="middle"
            fill={TXT2} fontSize={8}>{i}</text>
        ))}

        {/* Current pH marker */}
        <g transform={`translate(${30 + (ph / 14) * 340}, 45)`}>
          <polygon points="0,-8 -6,0 6,0" fill={phColor(ph)} />
          <rect x={-20} y={-28} width={40} height={18} rx={4}
            fill={phColor(ph)} />
          <text x={0} y={-15} textAnchor="middle" fill="white" fontSize={10} fontWeight="bold">
            pH {ph.toFixed(1)}
          </text>
        </g>

        {/* Substance dots */}
        {substances.map((s, i) => (
          <g key={i}>
            <circle cx={30 + (s.ph / 14) * 340} cy={65} r={3} fill="white" opacity={0.6} />
            {Math.abs(s.ph - ph) < 0.8 && (
              <text x={30 + (s.ph / 14) * 340} y={120} textAnchor="middle"
                fill={phColor(s.ph)} fontSize={8} fontWeight="bold">
                {s.name}
              </text>
            )}
          </g>
        ))}

        {/* Beaker visualization */}
        <rect x={140} y={140} width={120} height={120} rx={8} fill={phColor(ph) + '30'}
          stroke={phColor(ph)} strokeWidth={2} />
        <text x={200} y={195} textAnchor="middle" fill={phColor(ph)} fontSize={20} fontWeight="bold">
          {nature}
        </text>
        <text x={200} y={215} textAnchor="middle" fill={TXT2} fontSize={9}>
          Closest: {closest.name} (pH {closest.ph})
        </text>
        <text x={200} y={245} textAnchor="middle" fill={TXT2} fontSize={9}>
          H\u207A concentration: 10^(-{ph.toFixed(1)}) mol/L
        </text>
      </svg>

      <SimSlider label="pH Level" value={ph} min={0} max={14} step={0.1} unit=""
        color={phColor(ph)} onChange={setPh} />
      <SimCallout
        emoji="\u{1F9EA}"
        text={`pH ${ph.toFixed(1)} = ${nature}. ${ph < 7 ? 'More H\u207A ions than OH\u207B.' : ph > 7 ? 'More OH\u207B ions than H\u207A.' : 'Equal H\u207A and OH\u207B \u2014 perfectly neutral!'} ${closest.name} has a similar pH of ${closest.ph}.`}
      />
    </>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/ReactionsLabWidget.jsx
git commit -m "feat: upgrade ReactionsLab with pH slider + reaction controls

5 modes upgraded: ph_scale (continuous 0-14 slider), reaction_intro
(temperature), neutralization (titration volume), rust (time+humidity),
combustion (fuel/air ratio). Real chemistry calculations."
```

---

### Task 7: Upgrade EcosystemWidget (CRITICAL — 1 slider)

**File:** `frontend-react/src/components/game/widgets/EcosystemWidget.jsx`

- [ ] **Step 1: Add population/environmental sliders to 5 key modes**

| Mode | Slider | Science |
|------|--------|---------|
| `ecosystem_intro` | Temperature + rainfall sliders | Habitat health = f(temp, rain) |
| `producers_consumers` | Sunlight intensity slider | Producer growth \u221D light, consumer population follows |
| `food_chain` | Producer population slider | Energy cascade: 10% rule up the chain |
| `energy_pyramid` | Base energy input slider | Each level = 10% of below, pyramid resizes |
| `biodiversity` | Habitat area slider | Species-area relationship: S = cA^z |

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/EcosystemWidget.jsx
git commit -m "feat: upgrade Ecosystem with population/environment sliders

5 modes upgraded with continuous controls: temperature+rainfall for
habitat health, sunlight for producer growth, population slider for
food chain cascade, energy input for pyramid, area for biodiversity."
```

---

### Task 8: Upgrade GeometryBuilderWidget (CRITICAL — 1 slider)

**File:** `frontend-react/src/components/game/widgets/GeometryBuilderWidget.jsx`

- [ ] **Step 1: Add dimension/angle sliders to 6 key modes**

| Mode | Slider | Math |
|------|--------|------|
| `angle_types` | Angle drag slider (0-360\u00B0) | Classify: acute/right/obtuse/reflex |
| `area_rectangle` | Width + height sliders | A = w \u00D7 h, perimeter = 2(w+h) |
| `area_triangle` | Base + height sliders | A = \u00BD \u00D7 b \u00D7 h |
| `perimeter_calc` | Side length slider | P = sum of sides |
| `symmetry_lines` | Sides slider (3-8) | Number of lines of symmetry for regular polygon |
| `angle_sum` | Number of sides slider (3-10) | Sum = (n-2) \u00D7 180\u00B0 |

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/GeometryBuilderWidget.jsx
git commit -m "feat: upgrade GeometryBuilder with dimension/angle sliders

6 modes upgraded: angle classifier (0-360), rectangle area (w\u00D7h),
triangle area (\u00BDbh), perimeter, symmetry lines, angle sum formula."
```

---

### Task 9: Upgrade MatterStatesWidget (HIGH — 3 sliders)

**File:** `frontend-react/src/components/game/widgets/MatterStatesWidget.jsx`

- [ ] **Step 1: Add temperature/pressure sliders to 4 weak modes**

| Mode | Slider | Science |
|------|--------|---------|
| `three_states_intro` | Temperature slider | State transitions at melting/boiling points |
| `kinetic_energy` | Temperature slider | KE \u221D T, particle speed visualization |
| `particle_spacing` | Pressure slider | Volume \u221D 1/P (gas), minimal effect on solids |
| `condensation_demo` | Cooling rate slider | Dew point temperature visualization |

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/MatterStatesWidget.jsx
git commit -m "feat: upgrade MatterStates with temperature/pressure sliders

4 modes upgraded: intro (temp-driven state change), kinetic energy
(particle speed), particle spacing (pressure), condensation (cooling rate)."
```

---

### Task 10: Upgrade MixturesLabWidget (HIGH — 2 sliders)

**File:** `frontend-react/src/components/game/widgets/MixturesLabWidget.jsx`

- [ ] **Step 1: Add concentration/temperature sliders to 4 modes**

| Mode | Slider | Science |
|------|--------|---------|
| `saturation_curve` | Temperature slider | Solubility curve: g/100mL vs temperature |
| `evaporation_demo` | Heat input slider | Evaporation rate \u221D temperature |
| `distillation_setup` | Temperature slider | Boiling points separate mixtures |
| `chromatography_demo` | Solvent polarity slider | Rf values change with polarity |

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/MixturesLabWidget.jsx
git commit -m "feat: upgrade MixturesLab with concentration/separation sliders"
```

---

### Task 11: Upgrade WeatherStationWidget (HIGH — 3 sliders)

**File:** `frontend-react/src/components/game/widgets/WeatherStationWidget.jsx`

- [ ] **Step 1: Add sliders to 3 weak modes**

| Mode | Slider | Science |
|------|--------|---------|
| `pressure_systems` | Pressure slider (960-1050 hPa) | High/low pressure classification |
| `water_cycle` | Evaporation rate slider | Cycle speed driven by solar energy |
| `seasons_climate` | Latitude slider + month slider | Day length and temperature patterns |

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/WeatherStationWidget.jsx
git commit -m "feat: upgrade WeatherStation with pressure/cycle/season sliders"
```

---

### Task 12: Upgrade WaveSimWidget (HIGH — 1 slider)

**File:** `frontend-react/src/components/game/widgets/WaveSimWidget.jsx`

- [ ] **Step 1: Add frequency/wavelength sliders to 4 modes**

| Mode | Slider | Science |
|------|--------|---------|
| `light_spectrum` | Wavelength slider (380-750nm) | Color = f(wavelength), visible spectrum |
| `standing_waves` | Frequency slider | Harmonics: n\u00D7f_0, node/antinode visualization |
| `radio_microwave` | Frequency slider (log scale) | EM spectrum bands by frequency |
| `diffraction_demo` | Slit width slider | Diffraction angle \u221D \u03BB/d |

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/WaveSimWidget.jsx
git commit -m "feat: upgrade WaveSim with spectrum/frequency/diffraction sliders"
```

---

### Task 13: Upgrade AtomicModelWidget (HIGH — 1 slider)

**File:** `frontend-react/src/components/game/widgets/AtomicModelWidget.jsx`

- [ ] **Step 1: Add continuous sliders to 4 modes**

| Mode | Slider | Science |
|------|--------|---------|
| `atomic_structure` | Atomic number Z slider (1-20) | Proton/electron count, element name |
| `isotopes` | Mass number A slider | Neutron count = A - Z |
| `nuclear_power` | Control rod slider | Power output = f(rod position) |
| `fission` | Neutron energy slider | Critical energy for chain reaction |

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/AtomicModelWidget.jsx
git commit -m "feat: upgrade AtomicModel with Z slider + power/energy controls"
```

---

### Task 14: Polish Already-Strong Widgets (MEDIUM)

**Files:** PressureFluidsWidget.jsx, OpticsAdvancedWidget.jsx, PlantGrowthWidget.jsx

- [ ] **Step 1: Add sliders to 2-3 weak modes in each**

PressureFluids: modes 8 (buoyancy stability — tilt angle slider), 12 (submarine — ballast slider), 13 (extreme — depth slider)

OpticsAdvanced: modes 10 (eye defects — focal adjustment slider), 12 (spectrometer — grating spacing slider), 13 (interference — slit separation slider)

PlantGrowth: modes 8 (pollination — wind speed slider), 9 (seed dispersal — distance/wind slider), 11 (soil layers — depth slider)

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/widgets/PressureFluidsWidget.jsx
git add frontend-react/src/components/game/widgets/OpticsAdvancedWidget.jsx
git add frontend-react/src/components/game/widgets/PlantGrowthWidget.jsx
git commit -m "feat: polish PressureFluids, Optics, PlantGrowth weak modes"
```

---

### Task 15: Build Frontend and Deploy

**Files:** Build output

- [ ] **Step 1: Build frontend**

```bash
cd /Users/amajumder/Downloads/MentoApp/frontend-react
export PATH=/opt/homebrew/bin:$PATH
npx vite build
```

Expected: Build succeeds with no errors. Check for any import issues from the new controls/ directory.

- [ ] **Step 2: Deploy frontend to server**

```bash
# Clear old assets and deploy
sshpass -p 'qwertY@1432o' ssh -o StrictHostKeyChecking=no root@206.189.143.244 'rm -rf /var/www/mentoapp/frontend/assets/'
sshpass -p 'qwertY@1432o' rsync -avz -e 'ssh -o StrictHostKeyChecking=no' frontend-react/dist/ root@206.189.143.244:/var/www/mentoapp/frontend/
```

- [ ] **Step 3: Verify deployment**

```bash
curl -s https://simulations.mentomap.com | head -c 200
```

Expected: HTML response with React app.

---

### Task 16: E2E Playwright Test Suite

**File:** Create `test-widgets-e2e.mjs`

- [ ] **Step 1: Write comprehensive E2E test**

```js
import { chromium } from 'playwright';
import fs from 'fs';

const BASE = 'https://simulations.mentomap.com';
const GAMES = [
  'g6-chem-reactions', 'g6-chem-matter', 'g6-chem-mixtures',
  'g6-math-fractions', 'g6-math-geometry',
  'g6-phy-forces', 'g6-sci-circuits', 'g6-sci-ecosystem',
  'g6-sci-plants', 'g6-sci-weather',
  'g7-phy-heat', 'g7-phy-sound',
  'g8-phy-pressure', 'g8-phy-waves',
  'g9-phy-kinematics',
  'g10-phy-nuclear', 'g10-phy-optics',
];

async function getToken() {
  const r = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'demo_student', password: 'Mento@2026' }),
  });
  return (await r.json()).token;
}

async function waitForGame(page, timeout = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    const ready = await page.evaluate(() => {
      const h = document.querySelector('h2, h3');
      return h && !document.body.innerText.includes('Loading') && document.querySelectorAll('button').length > 3;
    });
    if (ready) return true;
    await page.waitForTimeout(500);
  }
  return false;
}

(async () => {
  const token = await getToken();
  const browser = await chromium.launch({ headless: true });
  const results = [];
  let passed = 0, failed = 0;

  for (const gameId of GAMES) {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 1200 } });
    const page = await ctx.newPage();
    const errors = [];
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text().substring(0, 150)); });

    try {
      await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 15000 });
      await page.waitForTimeout(1000);
      await page.evaluate(t => {
        localStorage.setItem('auth_token', t);
        localStorage.setItem('user', JSON.stringify({ id: 'demo_student', username: 'demo_student', role: 'student', org_id: 'default' }));
        localStorage.setItem('onboarding_seen', 'true');
      }, token);

      await page.goto(`${BASE}/play/${gameId}`, { waitUntil: 'domcontentloaded', timeout: 20000 });
      await page.waitForTimeout(3000);
      await page.evaluate(() => document.querySelectorAll('.fixed.inset-0.z-50').forEach(e => e.remove()));

      const startBtn = await page.$('button:has-text("Start Game")');
      if (startBtn) await startBtn.click({ force: true });

      const loaded = await waitForGame(page);
      if (!loaded) throw new Error('Game did not load within 15s');

      // Check widget rendering
      const info = await page.evaluate(() => {
        const svg = document.querySelector('svg[viewBox*="400"], svg[viewBox*="300"]');
        const sliders = document.querySelectorAll('input[type="range"]');
        const svgErrors = [];
        if (svg) {
          svg.querySelectorAll('circle, ellipse, rect, line, path').forEach(el => {
            for (const attr of el.attributes) {
              if (attr.value === 'undefined' || attr.value === 'NaN') {
                svgErrors.push(`${el.tagName} ${attr.name}=${attr.value}`);
              }
            }
          });
        }
        return {
          hasWidget: !!svg,
          widgetElements: svg ? svg.querySelectorAll('*').length : 0,
          sliderCount: sliders.length,
          svgErrors,
          choiceCount: document.querySelectorAll('button').length,
        };
      });

      // ASSERTIONS
      const checks = [];
      checks.push({ name: 'Widget renders', pass: info.hasWidget });
      checks.push({ name: 'Widget has content (>10 elements)', pass: info.widgetElements > 10 });
      checks.push({ name: 'Has at least 1 slider', pass: info.sliderCount >= 1 });
      checks.push({ name: 'No SVG undefined errors', pass: info.svgErrors.length === 0 });
      checks.push({ name: 'No console errors', pass: errors.filter(e => e.includes('Expected length')).length === 0 });
      checks.push({ name: 'Choices available', pass: info.choiceCount >= 4 });

      const allPass = checks.every(c => c.pass);
      if (allPass) passed++; else failed++;

      console.log(`${allPass ? '\u2705' : '\u274C'} ${gameId}: widget=${info.widgetElements}els sliders=${info.sliderCount} svgErrors=${info.svgErrors.length} consoleErrors=${errors.length}`);
      checks.filter(c => !c.pass).forEach(c => console.log(`   FAIL: ${c.name}`));

      results.push({ gameId, pass: allPass, checks, info, errors: errors.slice(0, 5) });
    } catch (err) {
      failed++;
      console.log(`\u274C ${gameId}: ${err.message.substring(0, 100)}`);
      results.push({ gameId, pass: false, error: err.message });
    } finally {
      await ctx.close();
    }
  }

  console.log(`\n=== RESULTS: ${passed}/${GAMES.length} passed, ${failed} failed ===`);
  fs.writeFileSync('e2e-results.json', JSON.stringify(results, null, 2));
  await browser.close();
  process.exit(failed > 0 ? 1 : 0);
})();
```

- [ ] **Step 2: Run E2E tests**

```bash
export PATH=/opt/homebrew/bin:$PATH
node test-widgets-e2e.mjs
```

Expected: All 17 games pass with:
- Widget renders with >10 SVG elements
- At least 1 slider per game
- Zero SVG undefined attribute errors
- Zero "Expected length" console errors
- 4+ choice buttons available

- [ ] **Step 3: Fix any failures and re-test**

If any game fails, check the specific error, fix the widget code, rebuild, redeploy, and re-run.

- [ ] **Step 4: Commit test file**

```bash
git add test-widgets-e2e.mjs
git commit -m "test: add Playwright E2E suite for all 17 simulation games

Verifies: widget renders, has sliders, no SVG errors, choices available.
Runs against production server."
```

---

## Execution Notes

- **Widget upgrade tasks (4-14)** can run in PARALLEL since each modifies a different file
- **Task 1** (controls library) must complete FIRST since all widgets import from it
- **Task 2** (loading optimization) is independent of widget upgrades
- **Task 3** (SVG fixes) should be done AS PART of each widget upgrade task
- **Task 15** (build/deploy) must come after all widget tasks
- **Task 16** (E2E tests) must come after deploy
