# Interactive Widgets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 5 new interactive widgets (StructuredFormInput, SliderRatingInput, ChecklistInput, BrainstormBoardWidget, DrawingCanvasWidget) that enable rich simulation gameplay beyond multiple-choice.

**Architecture:** Three Tier 2 widgets are standalone input components rendered in GamePlayPage before ChoiceSelector, sharing an `onSubmit(payload)` interface. Two Tier 3 widgets register in WidgetRegistry and communicate via `onWidgetResult` callback through InteractiveSceneLayer. Backend extends the `/choose` endpoint decision tree and adds `evaluate_drawing()` in llm.py + a `/upload-drawing` endpoint.

**Tech Stack:** React 18, Framer Motion, Tailwind CSS, HTML5 Canvas API, Flask, Claude Vision API (Anthropic SDK)

**Spec:** `docs/superpowers/specs/2026-04-16-interactive-widgets-design.md`

---

## File Structure

### New Files
| File | Responsibility |
|------|---------------|
| `frontend-react/src/components/game/inputs/StructuredFormInput.jsx` | Multi-field form input (5 WHYs, Pitch Card, etc.) |
| `frontend-react/src/components/game/inputs/SliderRatingInput.jsx` | Labeled sliders + justification textarea + honesty check |
| `frontend-react/src/components/game/inputs/ChecklistInput.jsx` | Checkbox list + reflection textarea |
| `frontend-react/src/components/game/widgets/BrainstormBoardWidget.jsx` | Timed sticky-note brainstorming scene widget |
| `frontend-react/src/components/game/widgets/DrawingCanvasWidget.jsx` | Freehand drawing canvas with tools + Vision API eval |

### Modified Files
| File | Change |
|------|--------|
| `frontend-react/src/pages/GamePlayPage.jsx` | Import input widgets, add `INPUT_WIDGETS` map, `widgetResult` state, `onWidgetResult` callback, attach `widget_data` in submit, handle `drawing_canvas` auto-submit |
| `frontend-react/src/components/game/renderers/SimulationRenderer.jsx` | Accept + pass `onWidgetResult` prop |
| `frontend-react/src/components/game/widgets/InteractiveSceneLayer.jsx` | Accept + pass `onWidgetResult` prop |
| `frontend-react/src/components/game/widgets/WidgetRegistry.js` | Add `brainstorm_board` + `drawing_canvas` entries |
| `frontend-react/src/api/games.js` | Add `uploadDrawing()` function |
| `backend/app.py` | Extend `/choose` decision tree for new input_types + widget_data; add `/upload-drawing` endpoint |
| `backend/llm.py` | Add `evaluate_drawing()` function |

---

## Task 1: StructuredFormInput Component

**Files:**
- Create: `frontend-react/src/components/game/inputs/StructuredFormInput.jsx`

- [ ] **Step 1: Create the inputs directory**

```bash
mkdir -p frontend-react/src/components/game/inputs
```

- [ ] **Step 2: Write StructuredFormInput.jsx**

```jsx
import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';

const StructuredFormInput = ({ config, onSubmit, disabled, colors }) => {
  const fields = config.form_fields || [];
  const [values, setValues] = useState(() =>
    Object.fromEntries(fields.map(f => [f.key, '']))
  );

  const handleFieldChange = (key, text) => {
    setValues(prev => ({ ...prev, [key]: text }));
  };

  const fieldStatus = useMemo(() =>
    fields.map(f => ({
      key: f.key,
      len: (values[f.key] || '').trim().length,
      min: f.min_length || 10,
      max: f.max_length || 500,
      met: (values[f.key] || '').trim().length >= (f.min_length || 10),
    })),
    [fields, values]
  );

  const completedCount = fieldStatus.filter(f => f.met).length;
  const allComplete = completedCount === fields.length;

  const handleSubmit = () => {
    if (!allComplete || disabled) return;

    // Build concatenated free_text: "LABEL: value\nLABEL: value\n..."
    const freeText = fields
      .map(f => `${f.label}: ${(values[f.key] || '').trim()}`)
      .join('\n');

    onSubmit(null, {
      freeText,
      input_type: 'structured_form',
      structured_response: {
        form_type: config.form_title?.toLowerCase().replace(/\s+/g, '_') || 'form',
        fields: { ...values },
        completion_time_ms: Date.now(),
      },
    });
  };

  const bg = colors?.card || '#1E293B';
  const textColor = colors?.text || '#F1F5F9';
  const mutedColor = colors?.textLight || '#94A3B8';
  const primary = colors?.primary || '#6366F1';

  return (
    <div className="rounded-2xl p-5 shadow-lg border" style={{ background: bg, borderColor: `${primary}22` }}>
      {/* Header */}
      {config.form_title && (
        <h3 className="text-lg font-bold mb-1" style={{ color: textColor }}>
          {config.form_title}
        </h3>
      )}
      {config.form_instruction && (
        <p className="text-sm mb-4" style={{ color: mutedColor }}>
          {config.form_instruction}
        </p>
      )}

      {/* Progress bar */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: `${primary}22` }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: primary }}
            animate={{ width: `${(completedCount / fields.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        <span className="text-xs font-medium" style={{ color: mutedColor }}>
          {completedCount}/{fields.length}
        </span>
      </div>

      {/* Fields */}
      <div className="space-y-4">
        {fields.map((field, i) => {
          const status = fieldStatus[i];
          const charColor = status.len === 0
            ? mutedColor
            : status.met
              ? '#10B981'
              : status.len > status.max
                ? '#EF4444'
                : mutedColor;

          return (
            <motion.div
              key={field.key}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.3 }}
            >
              <label className="block text-sm font-semibold mb-1" style={{ color: textColor }}>
                {field.label}
              </label>
              {field.hint && (
                <p className="text-xs mb-1" style={{ color: mutedColor }}>{field.hint}</p>
              )}
              <textarea
                className="w-full rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 transition-all"
                style={{
                  background: `${bg}CC`,
                  color: textColor,
                  borderColor: status.met ? '#10B981' : `${primary}44`,
                  border: '1px solid',
                  focusRingColor: primary,
                }}
                rows={3}
                placeholder={field.placeholder || ''}
                value={values[field.key] || ''}
                onChange={e => handleFieldChange(field.key, e.target.value)}
                maxLength={field.max_length || 500}
                disabled={disabled}
              />
              <div className="flex justify-end mt-1">
                <span className="text-xs" style={{ color: charColor }}>
                  {status.len}/{status.min} min
                </span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Submit */}
      <motion.button
        className="w-full mt-5 py-3 rounded-xl font-bold text-sm transition-all"
        style={{
          background: allComplete && !disabled ? primary : `${primary}44`,
          color: '#FFFFFF',
          cursor: allComplete && !disabled ? 'pointer' : 'not-allowed',
          opacity: allComplete && !disabled ? 1 : 0.5,
        }}
        whileTap={allComplete && !disabled ? { scale: 0.98 } : {}}
        onClick={handleSubmit}
        disabled={!allComplete || disabled}
      >
        Submit
      </motion.button>
    </div>
  );
};

export default StructuredFormInput;
```

- [ ] **Step 3: Verify file created**

```bash
ls -la frontend-react/src/components/game/inputs/StructuredFormInput.jsx
```

Expected: file exists

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/components/game/inputs/StructuredFormInput.jsx
git commit -m "feat: add StructuredFormInput widget for multi-field forms (5 WHYs, Pitch Card)"
```

---

## Task 2: SliderRatingInput Component

**Files:**
- Create: `frontend-react/src/components/game/inputs/SliderRatingInput.jsx`

- [ ] **Step 1: Write SliderRatingInput.jsx**

```jsx
import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';

const SliderRatingInput = ({ config, onSubmit, disabled, colors }) => {
  const sliders = config.sliders || [];
  const [sliderValues, setSliderValues] = useState(() =>
    Object.fromEntries(sliders.map(s => [s.key, s.default || Math.ceil((s.min + s.max) / 2)]))
  );
  const [justification, setJustification] = useState('');

  const totalScore = useMemo(
    () => Object.values(sliderValues).reduce((sum, v) => sum + v, 0),
    [sliderValues]
  );
  const totalMax = config.total_max || sliders.reduce((sum, s) => sum + (s.max || 5), 0);

  const justMinLen = config.justification_min_length || 30;
  const canSubmit = justification.trim().length >= justMinLen && !disabled;

  // Compute direct_deltas from slider values x resource_map
  const computeDirectDeltas = () => {
    const deltas = {};
    sliders.forEach(s => {
      const val = sliderValues[s.key] || 0;
      if (s.resource_map) {
        Object.entries(s.resource_map).forEach(([resource, multiplier]) => {
          deltas[resource] = (deltas[resource] || 0) + val * multiplier;
        });
      }
    });
    return deltas;
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    const directDeltas = computeDirectDeltas();

    // Build free_text: include slider context for LLM
    const highestSlider = sliders.reduce((best, s) =>
      (sliderValues[s.key] || 0) > (sliderValues[best.key] || 0) ? s : best, sliders[0]);
    const freeText = `I gave "${highestSlider.label}" my highest rating (${sliderValues[highestSlider.key]}). ${justification.trim()}`;

    onSubmit(null, {
      freeText,
      input_type: 'slider_rating',
      structured_response: {
        slider_values: { ...sliderValues },
        total_score: totalScore,
        direct_deltas: directDeltas,
        justification: justification.trim(),
        completion_time_ms: Date.now(),
      },
    });
  };

  const bg = colors?.card || '#1E293B';
  const textColor = colors?.text || '#F1F5F9';
  const mutedColor = colors?.textLight || '#94A3B8';
  const primary = colors?.primary || '#6366F1';

  // Total score color bands
  const scoreColor = totalScore >= totalMax * 0.8
    ? '#10B981'
    : totalScore >= totalMax * 0.48
      ? '#F59E0B'
      : '#EF4444';
  const scoreLabel = totalScore >= totalMax * 0.8
    ? 'Strong idea!'
    : totalScore >= totalMax * 0.48
      ? 'Good start, needs work'
      : 'Try a different problem';

  return (
    <div className="rounded-2xl p-5 shadow-lg border" style={{ background: bg, borderColor: `${primary}22` }}>
      {/* Header */}
      {config.rating_title && (
        <h3 className="text-lg font-bold mb-1" style={{ color: textColor }}>{config.rating_title}</h3>
      )}
      {config.rating_instruction && (
        <p className="text-sm mb-4" style={{ color: mutedColor }}>{config.rating_instruction}</p>
      )}

      {/* Sliders */}
      <div className="space-y-5">
        {sliders.map((slider, i) => {
          const val = sliderValues[slider.key] || slider.min || 1;
          const min = slider.min || 1;
          const max = slider.max || 5;
          const pct = ((val - min) / (max - min)) * 100;

          return (
            <motion.div
              key={slider.key}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08, duration: 0.3 }}
            >
              <div className="flex justify-between items-baseline mb-2">
                <span className="text-sm font-semibold" style={{ color: textColor }}>{slider.label}</span>
                <span className="text-lg font-black" style={{ color: primary }}>{val}</span>
              </div>
              <input
                type="range"
                min={min}
                max={max}
                step={1}
                value={val}
                onChange={e => setSliderValues(prev => ({ ...prev, [slider.key]: parseInt(e.target.value) }))}
                className="w-full h-2 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, ${primary} ${pct}%, ${primary}22 ${pct}%)`,
                  accentColor: primary,
                }}
                disabled={disabled}
              />
              <div className="flex justify-between mt-1">
                <span className="text-xs" style={{ color: mutedColor }}>{slider.low_label}</span>
                <span className="text-xs" style={{ color: mutedColor }}>{slider.high_label}</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Total score bar */}
      <div className="mt-5 p-3 rounded-xl" style={{ background: `${primary}11` }}>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-bold" style={{ color: textColor }}>
            {config.total_label || 'Total Score'}
          </span>
          <span className="text-xl font-black" style={{ color: scoreColor }}>
            {totalScore}/{totalMax}
          </span>
        </div>
        <div className="h-3 rounded-full overflow-hidden" style={{ background: `${primary}22` }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: scoreColor }}
            animate={{ width: `${(totalScore / totalMax) * 100}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
        <p className="text-xs mt-1 text-center font-medium" style={{ color: scoreColor }}>
          {scoreLabel}
        </p>
      </div>

      {/* Justification */}
      <div className="mt-5">
        <label className="block text-sm font-semibold mb-2" style={{ color: textColor }}>
          {config.justification_prompt || 'Explain your highest rating'}
        </label>
        <textarea
          className="w-full rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 border transition-all"
          style={{
            background: `${bg}CC`,
            color: textColor,
            borderColor: `${primary}44`,
          }}
          rows={4}
          placeholder="Be specific — what evidence supports your rating?"
          value={justification}
          onChange={e => setJustification(e.target.value)}
          disabled={disabled}
        />
        <div className="flex justify-end mt-1">
          <span className="text-xs" style={{
            color: justification.trim().length >= justMinLen ? '#10B981' : mutedColor
          }}>
            {justification.trim().length}/{justMinLen} min
          </span>
        </div>
      </div>

      {/* Submit */}
      <motion.button
        className="w-full mt-4 py-3 rounded-xl font-bold text-sm transition-all"
        style={{
          background: canSubmit ? primary : `${primary}44`,
          color: '#FFFFFF',
          cursor: canSubmit ? 'pointer' : 'not-allowed',
          opacity: canSubmit ? 1 : 0.5,
        }}
        whileTap={canSubmit ? { scale: 0.98 } : {}}
        onClick={handleSubmit}
        disabled={!canSubmit}
      >
        Submit Scorecard
      </motion.button>
    </div>
  );
};

export default SliderRatingInput;
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/inputs/SliderRatingInput.jsx
git commit -m "feat: add SliderRatingInput widget with honesty-check scoring"
```

---

## Task 3: ChecklistInput Component

**Files:**
- Create: `frontend-react/src/components/game/inputs/ChecklistInput.jsx`

- [ ] **Step 1: Write ChecklistInput.jsx**

```jsx
import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const ChecklistInput = ({ config, onSubmit, disabled, colors }) => {
  const items = config.items || [];
  const minChecked = config.min_checked || 1;
  const reflectionMinLen = config.reflection_min_length || 30;

  const [checked, setChecked] = useState({});
  const [reflection, setReflection] = useState('');

  const checkedCount = Object.values(checked).filter(Boolean).length;
  const showReflection = checkedCount >= minChecked;
  const canSubmit = showReflection && reflection.trim().length >= reflectionMinLen && !disabled;

  const toggleItem = (key) => {
    if (disabled) return;
    setChecked(prev => ({ ...prev, [key]: !prev[key] }));
  };

  // Compute direct_deltas from checked items
  const computeDirectDeltas = () => {
    const deltas = {};
    items.forEach(item => {
      if (checked[item.key]) {
        const dim = item.dimension || 'resilience';
        deltas[dim] = (deltas[dim] || 0) + (item.delta || 2);
      }
    });
    return deltas;
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    const checkedKeys = items.filter(i => checked[i.key]).map(i => i.key);
    const uncheckedKeys = items.filter(i => !checked[i.key]).map(i => i.key);
    const directDeltas = computeDirectDeltas();

    onSubmit(null, {
      freeText: reflection.trim(),
      input_type: 'checklist',
      structured_response: {
        checked_items: checkedKeys,
        unchecked_items: uncheckedKeys,
        checked_count: checkedKeys.length,
        direct_deltas: directDeltas,
        growth_areas: uncheckedKeys,
        reflection: reflection.trim(),
        completion_time_ms: Date.now(),
      },
    });
  };

  const bg = colors?.card || '#1E293B';
  const textColor = colors?.text || '#F1F5F9';
  const mutedColor = colors?.textLight || '#94A3B8';
  const primary = colors?.primary || '#6366F1';

  return (
    <div className="rounded-2xl p-5 shadow-lg border" style={{ background: bg, borderColor: `${primary}22` }}>
      {/* Header */}
      {config.checklist_title && (
        <h3 className="text-lg font-bold mb-1" style={{ color: textColor }}>
          {config.checklist_title}
        </h3>
      )}
      <div className="flex justify-between items-center mb-4">
        {config.checklist_instruction && (
          <p className="text-sm flex-1" style={{ color: mutedColor }}>
            {config.checklist_instruction}
          </p>
        )}
        <span className="text-xs font-medium ml-3 whitespace-nowrap" style={{ color: mutedColor }}>
          {checkedCount}/{items.length}
        </span>
      </div>

      {/* Checklist */}
      <div className="space-y-2">
        {items.map((item, i) => {
          const isChecked = !!checked[item.key];
          return (
            <motion.div
              key={item.key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05, duration: 0.25 }}
              className="flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-all"
              style={{
                background: isChecked ? `${primary}15` : 'transparent',
                border: `1px solid ${isChecked ? primary : `${primary}22`}`,
              }}
              onClick={() => toggleItem(item.key)}
            >
              {/* Custom checkbox */}
              <div
                className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 mt-0.5 transition-all"
                style={{
                  background: isChecked ? primary : 'transparent',
                  border: `2px solid ${isChecked ? primary : mutedColor}`,
                }}
              >
                <AnimatePresence>
                  {isChecked && (
                    <motion.span
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className="text-white text-xs"
                    >
                      ✓
                    </motion.span>
                  )}
                </AnimatePresence>
              </div>
              <span className="text-sm" style={{ color: textColor }}>{item.label}</span>
            </motion.div>
          );
        })}
      </div>

      {/* Reflection (slides in when enough items checked) */}
      <AnimatePresence>
        {showReflection && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
            className="mt-5 overflow-hidden"
          >
            <label className="block text-sm font-semibold mb-2" style={{ color: textColor }}>
              {config.reflection_prompt || 'Reflect on your growth areas'}
            </label>
            <textarea
              className="w-full rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 border transition-all"
              style={{
                background: `${bg}CC`,
                color: textColor,
                borderColor: `${primary}44`,
              }}
              rows={4}
              placeholder="Be specific about what you want to develop and how..."
              value={reflection}
              onChange={e => setReflection(e.target.value)}
              disabled={disabled}
            />
            <div className="flex justify-end mt-1">
              <span className="text-xs" style={{
                color: reflection.trim().length >= reflectionMinLen ? '#10B981' : mutedColor
              }}>
                {reflection.trim().length}/{reflectionMinLen} min
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Submit */}
      <motion.button
        className="w-full mt-4 py-3 rounded-xl font-bold text-sm transition-all"
        style={{
          background: canSubmit ? primary : `${primary}44`,
          color: '#FFFFFF',
          cursor: canSubmit ? 'pointer' : 'not-allowed',
          opacity: canSubmit ? 1 : 0.5,
        }}
        whileTap={canSubmit ? { scale: 0.98 } : {}}
        onClick={handleSubmit}
        disabled={!canSubmit}
      >
        Submit
      </motion.button>
    </div>
  );
};

export default ChecklistInput;
```

- [ ] **Step 2: Commit**

```bash
git add frontend-react/src/components/game/inputs/ChecklistInput.jsx
git commit -m "feat: add ChecklistInput widget with reflection scoring"
```

---

## Task 4: Wire Tier 2 Input Widgets into GamePlayPage

**Files:**
- Modify: `frontend-react/src/pages/GamePlayPage.jsx`

- [ ] **Step 1: Add imports at top of GamePlayPage.jsx**

Add after existing imports (around line 86):

```javascript
import StructuredFormInput from "../components/game/inputs/StructuredFormInput";
import SliderRatingInput from "../components/game/inputs/SliderRatingInput";
import ChecklistInput from "../components/game/inputs/ChecklistInput";
```

And add the input widget map constant (after imports, before component):

```javascript
const INPUT_WIDGETS = {
  structured_form: StructuredFormInput,
  slider_rating: SliderRatingInput,
  checklist: ChecklistInput,
};
```

- [ ] **Step 2: Modify handleChoiceSubmit to handle structured responses**

At line 752, the function currently builds `activeFreeText`. Replace lines 751-758 with:

```javascript
    // Add free_text to metadata if present (handles both free_text and hybrid modes)
    const activeFreeText = freeTextFromChoice || extraData?.freeText || (inputType !== 'multiple_choice' ? freeTextValue : '');
    if (activeFreeText) {
      metadata.free_text = activeFreeText;
    }

    // Attach structured_response and input_type for new widget types
    if (extraData?.structured_response) {
      metadata.structured_response = extraData.structured_response;
    }
    if (extraData?.input_type) {
      metadata.input_type = extraData.input_type;
    }

    // For free_text mode and new input types: submit with null choice_id
    const submitId = (inputType === 'free_text' || INPUT_WIDGETS[inputType]) ? null : choiceId;
```

- [ ] **Step 3: Render input widgets before ChoiceSelector**

At line 2283 (where `<ChoiceSelector` is rendered), wrap it with a conditional that checks for input widgets first. Replace the `<ChoiceSelector ... />` block (lines 2283-2299) with:

```jsx
{INPUT_WIDGETS[currentRound?.input_type] ? (
  (() => {
    const InputWidget = INPUT_WIDGETS[currentRound.input_type];
    return (
      <InputWidget
        config={currentRound}
        onSubmit={handleChoiceSubmit}
        disabled={showOutcome || isSubmitting || isTransitioning}
        colors={mergedColors}
      />
    );
  })()
) : (
  <ChoiceSelector
    choices={currentRound.choices || []}
    onSelect={trackAndSelect}
    onSubmit={handleChoiceSubmit}
    selectedChoice={selectedChoice}
    disabled={showOutcome || isSubmitting || isTransitioning}
    colors={mergedColors}
    density="dense"
    coachHints={currentRound?.coach_hints}
    gameState={gameState}
    inputType={currentRound?.input_type || 'multiple_choice'}
    freeTextValue={freeTextValue}
    onFreeTextChange={setFreeTextValue}
    rubricHints={currentRound?.evaluation_rubric ? Object.values(currentRound.evaluation_rubric) : null}
    minFreeTextLength={currentRound?.min_response_length || 20}
    freeTextPlaceholder={currentRound?.free_text_placeholder || 'Share your thoughts and reasoning here...'}
  />
)}
```

- [ ] **Step 4: Commit**

```bash
git add frontend-react/src/pages/GamePlayPage.jsx
git commit -m "feat: wire Tier 2 input widgets into GamePlayPage rendering and submission"
```

---

## Task 5: Backend — Extend /choose for New Input Types

**Files:**
- Modify: `backend/app.py` (lines 2436-2491)

- [ ] **Step 1: Add new input_type branches in the decision tree**

At line 2436, after `_input_type = prev_round.get("input_type", "multiple_choice")`, and inside the `try:` block starting at line 2437, add new branches BEFORE the existing `if _input_type == "free_text"` check. Replace the entire if/elif chain (lines 2438-2491) with:

```python
        if _input_type in ("structured_form", "slider_rating", "checklist") and free_text:
            # ── Tier 2 widget path: structured input + LLM eval ──────
            _structured = payload.get("structured_response", {})
            _rubric = prev_round.get("evaluation_rubric", {})
            _dims = (
                prev_round.get("scoring_dimensions")
                or list(_rubric.keys())
                or ["strategic_thinking", "risk_tolerance", "delayed_gratification",
                    "adaptability", "resilience", "empathy"]
            )
            _max_delta = int(prev_round.get("max_delta_per_dimension", 12))
            _situation = prev_round.get("situation") or prev_round.get("story") or prev_round.get("title", "")

            # Apply direct_deltas (sliders/checklist) — re-validate from round config
            _validated_deltas = {}
            if _input_type == "slider_rating":
                _sv = _structured.get("slider_values", {})
                for s_cfg in prev_round.get("sliders", []):
                    v = max(s_cfg.get("min", 1), min(s_cfg.get("max", 5), int(_sv.get(s_cfg["key"], 0))))
                    for res, mult in (s_cfg.get("resource_map") or {}).items():
                        _validated_deltas[res] = _validated_deltas.get(res, 0) + v * mult
            elif _input_type == "checklist":
                _ck = set(_structured.get("checked_items", []))
                for item_cfg in prev_round.get("items", []):
                    if item_cfg["key"] in _ck:
                        dim = item_cfg.get("dimension", "resilience")
                        _validated_deltas[dim] = _validated_deltas.get(dim, 0) + item_cfg.get("delta", 2)

            # Apply validated direct deltas to state
            for resource, delta_val in _validated_deltas.items():
                if hasattr(state_obj, resource):
                    setattr(state_obj, resource, getattr(state_obj, resource, 0) + delta_val)
                elif hasattr(state_obj, 'state') and isinstance(state_obj.state, dict):
                    state_obj.state[resource] = state_obj.state.get(resource, 0) + delta_val

            # LLM evaluate the free_text portion
            eval_result = evaluate_free_text_response(
                situation=_situation,
                player_text=free_text,
                scoring_dimensions=_dims,
                evaluation_rubric=_rubric,
                max_delta=_max_delta,
            )

            # Honesty penalty for slider_rating
            if _input_type == "slider_rating":
                _honesty = prev_round.get("honesty_check", {})
                if _honesty.get("enabled"):
                    _sv = _structured.get("slider_values", {})
                    _avg_slider = sum(_sv.values()) / max(len(_sv), 1)
                    _q_threshold = _honesty.get("quality_threshold", 4)
                    _a_threshold = _honesty.get("avg_rating_threshold", 4)
                    if eval_result.get("quality_score", 10) < _q_threshold and _avg_slider > _a_threshold:
                        _penalty = _honesty.get("penalty_multiplier", 0.5)
                        for resource, delta_val in _validated_deltas.items():
                            _reduction = delta_val - int(delta_val * _penalty)
                            if hasattr(state_obj, resource):
                                setattr(state_obj, resource, getattr(state_obj, resource, 0) - _reduction)
                            elif hasattr(state_obj, 'state') and isinstance(state_obj.state, dict):
                                state_obj.state[resource] = state_obj.state.get(resource, 0) - _reduction
                        eval_result["honesty_penalty_applied"] = True

            state_obj, outcome = apply_free_text_response(
                game, state_obj, free_text, eval_result, time_to_decide=time_to_decide
            )
            outcome["free_text_eval"] = eval_result
            outcome["structured_response"] = _structured
            outcome["validated_deltas"] = _validated_deltas

        elif _input_type == "drawing_canvas":
            # ── Drawing canvas path: Vision API eval ──────
            _widget_data = payload.get("widget_data", {})
            _drawing_id = _widget_data.get("drawing_id")
            if _drawing_id:
                import os
                _draw_dir = os.path.join("game_sessions", run_id, "drawings")
                _image_path = os.path.join(_draw_dir, f"{_drawing_id}.png")
                _rubric = prev_round.get("evaluation_rubric") or {}
                # Also check scene_widget props for rubric
                _sw_props = prev_round.get("scene_widget", {}).get("props", {})
                if not _rubric:
                    _rubric = _sw_props.get("evaluation_rubric", {})
                _dims = (
                    prev_round.get("scoring_dimensions")
                    or _sw_props.get("scoring_dimensions")
                    or list(_rubric.keys())
                    or ["creativity", "strategic_thinking"]
                )
                _max_delta = _sw_props.get("max_delta", 10)
                _situation = prev_round.get("situation") or prev_round.get("story") or prev_round.get("title", "")
                if os.path.exists(_image_path):
                    eval_result = evaluate_drawing(
                        situation=_situation,
                        image_path=_image_path,
                        evaluation_rubric=_rubric,
                        scoring_dimensions=_dims,
                        max_delta=_max_delta,
                    )
                else:
                    # Fallback if image missing
                    eval_result = {
                        "dimension_scores": {d: 5 for d in _dims},
                        "dimension_deltas": {d: _max_delta // 2 for d in _dims},
                        "feedback": "Drawing received. Keep practicing your visual thinking!",
                        "quality_score": 5,
                        "skill_tags": _dims[:2],
                        "matched_label": "Visual Thinker",
                        "sentiment_valence": 0.3,
                        "emotional_markers": [],
                        "engagement_level": "medium",
                    }
                state_obj, outcome = apply_free_text_response(
                    game, state_obj, f"[Drawing: {_drawing_id}]", eval_result, time_to_decide=time_to_decide
                )
                outcome["free_text_eval"] = eval_result
                outcome["drawing_eval"] = eval_result
                outcome["widget_data"] = {k: v for k, v in _widget_data.items() if k != "image_base64"}
            else:
                # No drawing submitted — treat as skip
                state_obj, outcome = apply_choice(game, state_obj, choice_id, stress_event=stress_event, time_to_decide=time_to_decide)

        elif _input_type == "free_text" and free_text:
            # ── Free-text path: LLM evaluates the response ──────────────────
            _rubric = prev_round.get("evaluation_rubric", {})
            _dims = (
                prev_round.get("scoring_dimensions")
                or list(_rubric.keys())
                or ["strategic_thinking", "risk_tolerance", "delayed_gratification",
                    "adaptability", "resilience", "empathy"]
            )
            _max_delta = int(prev_round.get("max_delta_per_dimension", 12))
            _situation = prev_round.get("situation") or prev_round.get("story") or prev_round.get("title", "")
            eval_result = evaluate_free_text_response(
                situation=_situation,
                player_text=free_text,
                scoring_dimensions=_dims,
                evaluation_rubric=_rubric,
                max_delta=_max_delta,
            )
            state_obj, outcome = apply_free_text_response(
                game, state_obj, free_text, eval_result, time_to_decide=time_to_decide
            )
            outcome["free_text_eval"] = eval_result
        elif _input_type == "hybrid" and free_text and (choice_id or (isinstance(choice_ids, list) and choice_ids)):
            # ── Hybrid path: apply choice normally, then LLM adjusts dimensions ──
            if isinstance(choice_ids, list) and choice_ids:
                state_obj, outcome = apply_choice(game, state_obj, choice_ids, stress_event=stress_event, time_to_decide=time_to_decide)
            else:
                state_obj, outcome = apply_choice(game, state_obj, choice_id, stress_event=stress_event, time_to_decide=time_to_decide)
            # Small LLM adjustment for reasoning quality (capped at ±4)
            _rubric = prev_round.get("evaluation_rubric", {})
            _dims = (
                prev_round.get("scoring_dimensions")
                or list(_rubric.keys())
                or ["strategic_thinking", "adaptability", "empathy"]
            )
            _situation = prev_round.get("situation") or prev_round.get("story") or prev_round.get("title", "")
            try:
                eval_result = evaluate_free_text_response(
                    situation=_situation,
                    player_text=free_text,
                    scoring_dimensions=_dims,
                    evaluation_rubric=_rubric,
                    max_delta=4,  # small adjustment for reasoning
                )
                from core.effects import apply_delta as _apply_delta
                state_obj = _apply_delta(state_obj, eval_result.get("dimension_deltas", {}))
                outcome["free_text_eval"] = eval_result
                outcome["hybrid_reasoning_feedback"] = eval_result.get("feedback", "")
            except Exception as _he:
                logger.warning(f"Hybrid free-text eval failed: {_he}")
        elif isinstance(choice_ids, list) and choice_ids:
            state_obj, outcome = apply_choice(game, state_obj, choice_ids, stress_event=stress_event, time_to_decide=time_to_decide)
        else:
            state_obj, outcome = apply_choice(game, state_obj, choice_id, stress_event=stress_event, time_to_decide=time_to_decide)

        # ── Widget data from scene widgets (brainstorm_board) ──
        _widget_data = payload.get("widget_data", {})
        if _widget_data.get("widget_type") == "brainstorm_board" and _input_type != "drawing_canvas":
            # Re-validate scoring tier from round config
            _sw_props = prev_round.get("scene_widget", {}).get("props", {})
            _tiers = _sw_props.get("scoring_tiers", [])
            _idea_count = int(_widget_data.get("idea_count", 0))
            _tier_delta = {}
            for tier in _tiers:
                if _idea_count >= tier.get("min_count", 0):
                    _tier_delta = tier.get("delta", {})
                    break
            for resource, delta_val in _tier_delta.items():
                if hasattr(state_obj, resource):
                    setattr(state_obj, resource, getattr(state_obj, resource, 0) + delta_val)
                elif hasattr(state_obj, 'state') and isinstance(state_obj.state, dict):
                    state_obj.state[resource] = state_obj.state.get(resource, 0) + delta_val
            outcome.setdefault("widget_data", {}).update({
                "widget_type": "brainstorm_board",
                "idea_count": _idea_count,
                "best_idea": _widget_data.get("best_idea", ""),
                "ideas": _widget_data.get("ideas", [])[:20],  # cap storage
                "validated_tier_delta": _tier_delta,
            })
```

- [ ] **Step 2: Add the import for evaluate_drawing at the top of app.py**

Find the line where `evaluate_free_text_response` is imported (search for `from llm import`) and add `evaluate_drawing`:

```python
from llm import evaluate_free_text_response, evaluate_drawing
```

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "feat: extend /choose endpoint for structured_form, slider_rating, checklist, drawing_canvas, brainstorm_board"
```

---

## Task 6: Backend — upload-drawing Endpoint

**Files:**
- Modify: `backend/app.py` (add new route)

- [ ] **Step 1: Add the /upload-drawing endpoint**

Add this route near the other `/api/run/` routes in app.py (after the `/choose` endpoint):

```python
@app.route("/api/run/<run_id>/upload-drawing", methods=["POST"])
def upload_drawing(run_id):
    """Upload a drawing PNG from the canvas widget."""
    import base64, os

    # Validate run exists
    state_obj = _RUNS.get(run_id)
    if not state_obj:
        return jsonify({"error": "Run not found"}), 404

    data = request.get_json(force=True)
    image_b64 = data.get("image_base64", "")
    round_id = (data.get("round_id") or "drawing").strip()[:100]

    # Strip data URL prefix if present
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    # Decode and validate
    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        return jsonify({"error": "Invalid base64 image"}), 400

    # Check PNG header
    if not image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
        return jsonify({"error": "Invalid PNG format"}), 400

    # Check size (2MB max)
    if len(image_bytes) > 2 * 1024 * 1024:
        return jsonify({"error": "Image too large (max 2MB)"}), 400

    # Store to disk
    draw_dir = os.path.join("game_sessions", run_id, "drawings")
    os.makedirs(draw_dir, exist_ok=True)
    image_path = os.path.join(draw_dir, f"{round_id}.png")

    with open(image_path, "wb") as f:
        f.write(image_bytes)

    # Generate simple thumbnail (store metadata only — no PIL dependency)
    # The actual thumbnail can be generated on-demand from the PNG later
    thumb_info = {
        "original_size": len(image_bytes),
        "path": image_path,
    }

    logger.info(f"Drawing uploaded: run={run_id}, round={round_id}, size={len(image_bytes)} bytes")

    return jsonify({
        "drawing_id": round_id,
        "status": "uploaded",
        "size_bytes": len(image_bytes),
    })
```

- [ ] **Step 2: Commit**

```bash
git add backend/app.py
git commit -m "feat: add POST /api/run/<id>/upload-drawing endpoint for canvas widget"
```

---

## Task 7: Backend — evaluate_drawing() in llm.py

**Files:**
- Modify: `backend/llm.py` (add function after line 1084)

- [ ] **Step 1: Add evaluate_drawing function**

Insert after line 1084 (end of `evaluate_free_text_response`), before `generate_full_game_json` (line 1086):

```python
def evaluate_drawing(
    situation: str,
    image_path: str,
    evaluation_rubric: dict,
    scoring_dimensions: list,
    max_delta: int = 10,
) -> dict:
    """
    Evaluate a student drawing using Claude Vision API.
    Returns the same structure as evaluate_free_text_response().
    """
    import base64, os

    # ── Build rubric text ────────────────────────────────────
    rubric_lines = []
    for dim in scoring_dimensions:
        hint = evaluation_rubric.get(dim, f"Does the drawing demonstrate {dim.replace('_', ' ')}?")
        rubric_lines.append(f"- {dim}: {hint}")
    rubric_text = "\n".join(rubric_lines)

    prompt_text = (
        f"A Grade 6 student was asked: \"{situation}\"\n\n"
        f"They drew the image below. Evaluate their drawing against these criteria:\n"
        f"{rubric_text}\n\n"
        f"Score each dimension 0-10 (10 = excellent evidence, 5 = moderate, 0 = no evidence).\n"
        f"Consider effort, clarity, logical flow, and creativity — NOT artistic skill.\n"
        f"Provide brief, encouraging coaching feedback (2-3 sentences).\n\n"
        f"Return ONLY valid JSON:\n"
        f'{{"dimension_scores": {{{", ".join(f\'"{d}": <0-10>\' for d in scoring_dimensions)}}}, '
        f'"feedback": "<coaching feedback>", '
        f'"quality_score": <0-10>, '
        f'"skill_tags": [<top 1-3 dimensions>], '
        f'"matched_label": "<3-5 word label>"}}'
    )

    # ── Try Vision API call ──────────────────────────────────
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Drawing not found: {image_path}")

        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        provider = os.environ.get("MODEL_PROVIDER", "anthropic")

        if provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt_text,
                        },
                    ],
                }],
            )
            raw = response.content[0].text
        else:
            # OpenAI-compatible vision
            import openai
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                max_tokens=500,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                        {"type": "text", "text": prompt_text},
                    ],
                }],
            )
            raw = response.choices[0].message.content

        # ── Parse JSON ────────────────────────────────────────
        import json, re
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            result = json.loads(json_match.group())
        else:
            raise ValueError("No JSON in Vision response")

        # Validate and normalize scores
        clean_scores = {}
        for d in scoring_dimensions:
            v = result.get("dimension_scores", {}).get(d, 5)
            clean_scores[d] = max(0, min(10, int(v)))

        deltas = {d: round(v * max_delta / 10) for d, v in clean_scores.items()}

        return {
            "dimension_scores": clean_scores,
            "dimension_deltas": deltas,
            "feedback": result.get("feedback", "Great effort on your drawing!"),
            "matched_label": result.get("matched_label", "Visual Thinker"),
            "quality_score": max(0, min(10, int(result.get("quality_score", 5) or 5))),
            "skill_tags": result.get("skill_tags", list(clean_scores.keys())[:2]),
            "sentiment_valence": 0.5,
            "emotional_markers": [],
            "engagement_level": "high" if sum(clean_scores.values()) / len(clean_scores) > 6 else "medium",
        }

    except Exception as e:
        logger.warning(f"evaluate_drawing failed: {e}")
        # ── Fallback: heuristic scoring from metadata ────────
        fallback_score = 5
        return {
            "dimension_scores": {d: fallback_score for d in scoring_dimensions},
            "dimension_deltas": {d: round(fallback_score * max_delta / 10) for d in scoring_dimensions},
            "feedback": "Great effort on your drawing! The more detail you add, the clearer your idea becomes.",
            "matched_label": "Visual Thinker",
            "quality_score": fallback_score,
            "skill_tags": scoring_dimensions[:2],
            "sentiment_valence": 0.3,
            "emotional_markers": [],
            "engagement_level": "medium",
        }
```

- [ ] **Step 2: Commit**

```bash
git add backend/llm.py
git commit -m "feat: add evaluate_drawing() function with Claude Vision API + fallback"
```

---

## Task 8: BrainstormBoardWidget (Scene Widget)

**Files:**
- Create: `frontend-react/src/components/game/widgets/BrainstormBoardWidget.jsx`
- Modify: `frontend-react/src/components/game/widgets/WidgetRegistry.js`

- [ ] **Step 1: Write BrainstormBoardWidget.jsx**

```jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const BrainstormBoardWidget = ({
  timer_seconds = 300,
  prompt = 'Write as many ideas as possible!',
  min_ideas = 3,
  colors: noteColors = ['#FEF3C7', '#DBEAFE', '#FCE7F3', '#D1FAE5', '#EDE9FE', '#FEE2E2'],
  best_idea_select = true,
  scoring_tiers = [],
  onWidgetResult,
  theme,
}) => {
  const [ideas, setIdeas] = useState([]);
  const [timeLeft, setTimeLeft] = useState(timer_seconds);
  const [phase, setPhase] = useState('brainstorm'); // 'brainstorm' | 'select' | 'done'
  const [bestIdeaIdx, setBestIdeaIdx] = useState(null);
  const [editingIdx, setEditingIdx] = useState(null);
  const timerRef = useRef(null);
  const startTimeRef = useRef(Date.now());
  const inputRefs = useRef({});

  const t = {
    bg: theme?.palette?.card || '#1E293B',
    text: theme?.palette?.text || '#F1F5F9',
    muted: theme?.palette?.textLight || '#94A3B8',
    primary: theme?.palette?.accent || '#6366F1',
  };

  // Timer
  useEffect(() => {
    if (phase !== 'brainstorm') return;
    timerRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          setPhase(best_idea_select ? 'select' : 'done');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [phase, best_idea_select]);

  // Resolve scoring tier
  const resolveTier = useCallback((count) => {
    for (const tier of scoring_tiers) {
      if (count >= (tier.min_count || 0)) return tier.delta || {};
    }
    return {};
  }, [scoring_tiers]);

  // Fire result when done
  useEffect(() => {
    if (phase !== 'done' || !onWidgetResult) return;
    const ideaTexts = ideas.map(i => i.text).filter(t => t.trim());
    const tierDelta = resolveTier(ideaTexts.length);
    onWidgetResult({
      widget_type: 'brainstorm_board',
      ideas: ideaTexts,
      idea_count: ideaTexts.length,
      best_idea: bestIdeaIdx !== null ? ideaTexts[bestIdeaIdx] || '' : '',
      best_idea_index: bestIdeaIdx,
      time_used_seconds: timer_seconds - timeLeft,
      time_limit_seconds: timer_seconds,
      scoring_tier_delta: tierDelta,
    });
  }, [phase]); // eslint-disable-line react-hooks/exhaustive-deps

  const addIdea = () => {
    if (phase !== 'brainstorm') return;
    const colorIdx = ideas.length % noteColors.length;
    const rotation = (Math.random() - 0.5) * 4; // -2 to +2 degrees
    const newIdx = ideas.length;
    setIdeas(prev => [...prev, { text: '', color: noteColors[colorIdx], rotation }]);
    setEditingIdx(newIdx);
    // Focus new input after render
    setTimeout(() => inputRefs.current[newIdx]?.focus(), 50);
  };

  const updateIdea = (idx, text) => {
    setIdeas(prev => prev.map((idea, i) => i === idx ? { ...idea, text } : idea));
  };

  const removeIdea = (idx) => {
    if (phase !== 'brainstorm') return;
    setIdeas(prev => prev.filter((_, i) => i !== idx));
  };

  const handleDoneEarly = () => {
    clearInterval(timerRef.current);
    setPhase(best_idea_select ? 'select' : 'done');
  };

  const confirmBestIdea = () => {
    setPhase('done');
  };

  const mm = String(Math.floor(timeLeft / 60)).padStart(2, '0');
  const ss = String(timeLeft % 60).padStart(2, '0');

  return (
    <div className="rounded-2xl p-4 shadow-lg border" style={{ background: t.bg, borderColor: `${t.primary}22` }}>
      {/* Top bar */}
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold flex-1" style={{ color: t.text }}>{prompt}</p>
        <div className="flex items-center gap-3 ml-3">
          <span className="text-xs font-medium px-2 py-1 rounded-full" style={{ background: `${t.primary}22`, color: t.muted }}>
            {ideas.filter(i => i.text.trim()).length} ideas
          </span>
          {phase === 'brainstorm' && (
            <span
              className={`text-sm font-bold font-mono px-2 py-1 rounded-lg ${timeLeft <= 30 ? 'animate-pulse' : ''}`}
              style={{ color: timeLeft <= 30 ? '#EF4444' : t.text, background: timeLeft <= 30 ? '#EF444422' : `${t.primary}11` }}
            >
              {mm}:{ss}
            </span>
          )}
        </div>
      </div>

      {/* Sticky notes grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 min-h-[200px] max-h-[400px] overflow-y-auto p-1">
        <AnimatePresence>
          {ideas.map((idea, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1, rotate: idea.rotation }}
              exit={{ opacity: 0, scale: 0.5 }}
              className={`relative p-3 rounded-xl shadow-md min-h-[80px] ${phase === 'select' ? 'cursor-pointer' : ''}`}
              style={{
                background: idea.color,
                border: phase === 'select' && bestIdeaIdx === idx ? '3px solid #F59E0B' : '1px solid transparent',
              }}
              onClick={() => phase === 'select' && setBestIdeaIdx(idx)}
            >
              {phase === 'select' && bestIdeaIdx === idx && (
                <span className="absolute -top-2 -right-2 text-lg">⭐</span>
              )}
              {phase === 'brainstorm' && (
                <button
                  className="absolute top-1 right-1 w-5 h-5 rounded-full flex items-center justify-center text-xs opacity-40 hover:opacity-100 transition-opacity"
                  style={{ background: '#00000022', color: '#333' }}
                  onClick={(e) => { e.stopPropagation(); removeIdea(idx); }}
                >
                  ×
                </button>
              )}
              <textarea
                ref={el => inputRefs.current[idx] = el}
                className="w-full bg-transparent text-sm text-gray-800 resize-none focus:outline-none placeholder-gray-500"
                rows={3}
                placeholder="Your idea..."
                value={idea.text}
                onChange={e => updateIdea(idx, e.target.value)}
                disabled={phase !== 'brainstorm'}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    addIdea();
                  }
                }}
              />
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Add button */}
        {phase === 'brainstorm' && (
          <motion.button
            className="rounded-xl border-2 border-dashed min-h-[80px] flex items-center justify-center text-2xl transition-all hover:border-solid"
            style={{ borderColor: `${t.primary}44`, color: t.muted }}
            onClick={addIdea}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            +
          </motion.button>
        )}
      </div>

      {/* Bottom actions */}
      <div className="mt-3 flex justify-between items-center">
        {phase === 'brainstorm' && (
          <button
            className="text-xs px-3 py-1.5 rounded-lg font-medium transition-all"
            style={{ background: `${t.primary}22`, color: t.muted }}
            onClick={handleDoneEarly}
          >
            I'm done early
          </button>
        )}
        {phase === 'select' && (
          <div className="flex items-center gap-3 w-full">
            <p className="text-sm font-semibold flex-1" style={{ color: '#F59E0B' }}>
              ⭐ Pick your BEST idea!
            </p>
            <button
              className="px-4 py-2 rounded-xl font-bold text-sm text-white transition-all"
              style={{
                background: bestIdeaIdx !== null ? t.primary : `${t.primary}44`,
                cursor: bestIdeaIdx !== null ? 'pointer' : 'not-allowed',
              }}
              onClick={confirmBestIdea}
              disabled={bestIdeaIdx === null}
            >
              Confirm
            </button>
          </div>
        )}
        {phase === 'done' && (
          <p className="text-sm font-medium" style={{ color: '#10B981' }}>
            ✓ Brainstorm complete — {ideas.filter(i => i.text.trim()).length} ideas captured
          </p>
        )}
      </div>
    </div>
  );
};

export default BrainstormBoardWidget;
```

- [ ] **Step 2: Register in WidgetRegistry.js**

Add before the closing `};` in `frontend-react/src/components/game/widgets/WidgetRegistry.js` (after line 117):

```javascript
  // ── Interactive input widgets ──────────────────────────────
  brainstorm_board: lazy(() => import('./BrainstormBoardWidget')),
```

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/components/game/widgets/BrainstormBoardWidget.jsx frontend-react/src/components/game/widgets/WidgetRegistry.js
git commit -m "feat: add BrainstormBoardWidget with timed ideation and best-idea selection"
```

---

## Task 9: DrawingCanvasWidget (Scene Widget)

**Files:**
- Create: `frontend-react/src/components/game/widgets/DrawingCanvasWidget.jsx`
- Modify: `frontend-react/src/components/game/widgets/WidgetRegistry.js`

- [ ] **Step 1: Write DrawingCanvasWidget.jsx**

```jsx
import { useState, useRef, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';

// ── Canvas templates ──────────────────────────────────────
const TEMPLATES = {
  three_screens: (ctx, w, h) => {
    const gap = 20;
    const sw = Math.floor((w - gap * 4) / 3);
    const sh = Math.floor(h * 0.85);
    const y = Math.floor((h - sh) / 2);
    ctx.strokeStyle = '#E5E7EB';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    for (let i = 0; i < 3; i++) {
      const x = gap + i * (sw + gap);
      // Phone shape: rounded rect
      const r = 12;
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + sw - r, y);
      ctx.quadraticCurveTo(x + sw, y, x + sw, y + r);
      ctx.lineTo(x + sw, y + sh - r);
      ctx.quadraticCurveTo(x + sw, y + sh, x + sw - r, y + sh);
      ctx.lineTo(x + r, y + sh);
      ctx.quadraticCurveTo(x, y + sh, x, y + sh - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.stroke();
      // Label
      ctx.setLineDash([]);
      ctx.fillStyle = '#D1D5DB';
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(`Screen ${i + 1}`, x + sw / 2, y + sh + 16);
      ctx.setLineDash([6, 4]);
    }
    ctx.setLineDash([]);
  },
  wireframe_grid: (ctx, w, h) => {
    ctx.strokeStyle = '#F3F4F6';
    ctx.lineWidth = 0.5;
    ctx.setLineDash([2, 4]);
    for (let x = 20; x < w; x += 20) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
    }
    for (let y = 20; y < h; y += 20) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
    ctx.setLineDash([]);
  },
  single_page: (ctx, w, h) => {
    ctx.strokeStyle = '#E5E7EB';
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    ctx.strokeRect(20, 20, w - 40, h - 40);
    ctx.setLineDash([]);
  },
  none: () => {},
};

const TOOL_ICONS = {
  pen: '✏️',
  eraser: '🧹',
  shapes: '▢',
  text: 'T',
  undo: '↩',
  clear: '🗑',
};

const DrawingCanvasWidget = ({
  prompt = 'Draw your design',
  canvas_width = 600,
  canvas_height = 400,
  tools: enabledTools = ['pen', 'eraser', 'shapes', 'text', 'undo', 'clear'],
  colors: penColors = ['#000000', '#EF4444', '#3B82F6', '#10B981', '#F59E0B', '#8B5CF6'],
  brush_sizes = [2, 4, 8],
  template = 'none',
  onWidgetResult,
  theme,
}) => {
  const canvasRef = useRef(null);
  const [activeTool, setActiveTool] = useState('pen');
  const [activeColor, setActiveColor] = useState(penColors[0] || '#000000');
  const [brushSize, setBrushSize] = useState(brush_sizes[1] || 4);
  const [shapeType, setShapeType] = useState('rect'); // rect | circle | line
  const [isDrawing, setIsDrawing] = useState(false);
  const [isDone, setIsDone] = useState(false);

  // History for undo
  const historyRef = useRef([]);
  const [strokeCount, setStrokeCount] = useState(0);
  const toolsUsedRef = useRef(new Set());
  const startTimeRef = useRef(Date.now());

  // Current stroke points
  const currentPathRef = useRef([]);
  // Shape start point
  const shapeStartRef = useRef(null);
  // Text placement
  const [textInput, setTextInput] = useState(null); // { x, y } or null

  const t = {
    bg: theme?.palette?.card || '#1E293B',
    text: theme?.palette?.text || '#F1F5F9',
    muted: theme?.palette?.textLight || '#94A3B8',
    primary: theme?.palette?.accent || '#6366F1',
  };

  // Draw template
  const drawTemplate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const tmplFn = TEMPLATES[template] || TEMPLATES.none;
    tmplFn(ctx, canvas.width, canvas.height);
  }, [template]);

  // Redraw all from history
  const redrawAll = useCallback(() => {
    drawTemplate();
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    historyRef.current.forEach(entry => {
      if (entry.type === 'path') {
        ctx.strokeStyle = entry.color;
        ctx.lineWidth = entry.size;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.globalCompositeOperation = entry.eraser ? 'destination-out' : 'source-over';
        ctx.beginPath();
        entry.points.forEach((pt, i) => {
          if (i === 0) ctx.moveTo(pt.x, pt.y);
          else ctx.lineTo(pt.x, pt.y);
        });
        ctx.stroke();
        ctx.globalCompositeOperation = 'source-over';
      } else if (entry.type === 'shape') {
        ctx.strokeStyle = entry.color;
        ctx.lineWidth = entry.size;
        ctx.beginPath();
        if (entry.shape === 'rect') {
          ctx.strokeRect(entry.x, entry.y, entry.w, entry.h);
        } else if (entry.shape === 'circle') {
          const cx = entry.x + entry.w / 2;
          const cy = entry.y + entry.h / 2;
          const rx = Math.abs(entry.w) / 2;
          const ry = Math.abs(entry.h) / 2;
          ctx.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
          ctx.stroke();
        } else if (entry.shape === 'line') {
          ctx.moveTo(entry.x, entry.y);
          ctx.lineTo(entry.x + entry.w, entry.y + entry.h);
          ctx.stroke();
        }
      } else if (entry.type === 'text') {
        ctx.fillStyle = entry.color;
        ctx.font = `${entry.fontSize}px sans-serif`;
        ctx.fillText(entry.text, entry.x, entry.y);
      }
    });
  }, [drawTemplate]);

  // Init canvas
  useEffect(() => {
    drawTemplate();
  }, [drawTemplate]);

  // Get position relative to canvas
  const getPos = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  };

  const handlePointerDown = (e) => {
    if (isDone || activeTool === 'undo' || activeTool === 'clear') return;
    e.preventDefault();
    const pos = getPos(e);

    if (activeTool === 'text') {
      setTextInput(pos);
      return;
    }

    setIsDrawing(true);
    toolsUsedRef.current.add(activeTool);

    if (activeTool === 'shapes') {
      shapeStartRef.current = pos;
    } else {
      // pen or eraser
      currentPathRef.current = [pos];
      const ctx = canvasRef.current.getContext('2d');
      ctx.strokeStyle = activeTool === 'eraser' ? '#FFFFFF' : activeColor;
      ctx.lineWidth = brushSize;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.globalCompositeOperation = activeTool === 'eraser' ? 'destination-out' : 'source-over';
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
    }
  };

  const handlePointerMove = (e) => {
    if (!isDrawing || isDone) return;
    e.preventDefault();
    const pos = getPos(e);

    if (activeTool === 'shapes') {
      // Preview: redraw everything + current shape
      redrawAll();
      const ctx = canvasRef.current.getContext('2d');
      const start = shapeStartRef.current;
      ctx.strokeStyle = activeColor;
      ctx.lineWidth = brushSize;
      const w = pos.x - start.x;
      const h = pos.y - start.y;
      ctx.beginPath();
      if (shapeType === 'rect') ctx.strokeRect(start.x, start.y, w, h);
      else if (shapeType === 'circle') {
        ctx.ellipse(start.x + w / 2, start.y + h / 2, Math.abs(w) / 2, Math.abs(h) / 2, 0, 0, Math.PI * 2);
        ctx.stroke();
      } else {
        ctx.moveTo(start.x, start.y);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
      }
    } else {
      currentPathRef.current.push(pos);
      const ctx = canvasRef.current.getContext('2d');
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
    }
  };

  const handlePointerUp = (e) => {
    if (!isDrawing || isDone) return;
    setIsDrawing(false);

    if (activeTool === 'shapes') {
      const pos = getPos(e);
      const start = shapeStartRef.current;
      historyRef.current.push({
        type: 'shape',
        shape: shapeType,
        x: start.x,
        y: start.y,
        w: pos.x - start.x,
        h: pos.y - start.y,
        color: activeColor,
        size: brushSize,
      });
    } else {
      const ctx = canvasRef.current.getContext('2d');
      ctx.globalCompositeOperation = 'source-over';
      historyRef.current.push({
        type: 'path',
        points: [...currentPathRef.current],
        color: activeColor,
        size: brushSize,
        eraser: activeTool === 'eraser',
      });
    }
    setStrokeCount(prev => prev + 1);
  };

  const handleUndo = () => {
    if (historyRef.current.length === 0) return;
    historyRef.current.pop();
    setStrokeCount(prev => Math.max(0, prev - 1));
    redrawAll();
  };

  const handleClear = () => {
    if (!window.confirm('Clear everything? This can\'t be undone.')) return;
    historyRef.current = [];
    setStrokeCount(0);
    drawTemplate();
  };

  const handleTextSubmit = (text) => {
    if (!textInput || !text.trim()) { setTextInput(null); return; }
    toolsUsedRef.current.add('text');
    const fontSize = brushSize * 4;
    const ctx = canvasRef.current.getContext('2d');
    ctx.fillStyle = activeColor;
    ctx.font = `${fontSize}px sans-serif`;
    ctx.fillText(text, textInput.x, textInput.y);
    historyRef.current.push({
      type: 'text',
      text,
      x: textInput.x,
      y: textInput.y,
      color: activeColor,
      fontSize,
    });
    setStrokeCount(prev => prev + 1);
    setTextInput(null);
  };

  const handleDone = async () => {
    if (isDone || strokeCount < 5) return;
    setIsDone(true);

    const canvas = canvasRef.current;
    const dataUrl = canvas.toDataURL('image/png');
    const timeSpent = Math.round((Date.now() - startTimeRef.current) / 1000);

    if (onWidgetResult) {
      onWidgetResult({
        widget_type: 'drawing_canvas',
        image_base64: dataUrl,
        stroke_count: strokeCount,
        tools_used: [...toolsUsedRef.current],
        time_spent_seconds: timeSpent,
        done: true,
      });
    }
  };

  return (
    <div className="rounded-2xl p-4 shadow-lg border" style={{ background: t.bg, borderColor: `${t.primary}22` }}>
      {/* Prompt */}
      <p className="text-sm font-bold mb-3" style={{ color: t.text }}>{prompt}</p>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {/* Tools */}
        {enabledTools.filter(t => t !== 'undo' && t !== 'clear').map(tool => (
          <button
            key={tool}
            className="px-2 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1"
            style={{
              background: activeTool === tool ? t.primary : `${t.primary}22`,
              color: activeTool === tool ? '#FFF' : t.muted,
            }}
            onClick={() => {
              setActiveTool(tool);
              setTextInput(null);
            }}
            disabled={isDone}
          >
            {TOOL_ICONS[tool]} {tool}
          </button>
        ))}

        {/* Shape sub-selector */}
        {activeTool === 'shapes' && (
          <select
            className="text-xs rounded px-1 py-1"
            style={{ background: `${t.primary}22`, color: t.text }}
            value={shapeType}
            onChange={e => setShapeType(e.target.value)}
          >
            <option value="rect">Rectangle</option>
            <option value="circle">Circle</option>
            <option value="line">Line</option>
          </select>
        )}

        <div className="w-px h-5 mx-1" style={{ background: `${t.primary}33` }} />

        {/* Colors */}
        {penColors.map(color => (
          <button
            key={color}
            className="w-5 h-5 rounded-full transition-all"
            style={{
              background: color,
              boxShadow: activeColor === color ? `0 0 0 2px ${t.bg}, 0 0 0 4px ${color}` : 'none',
            }}
            onClick={() => setActiveColor(color)}
            disabled={isDone}
          />
        ))}

        <div className="w-px h-5 mx-1" style={{ background: `${t.primary}33` }} />

        {/* Brush sizes */}
        {brush_sizes.map(size => (
          <button
            key={size}
            className="flex items-center justify-center w-6 h-6 rounded-full transition-all"
            style={{
              background: brushSize === size ? `${t.primary}44` : 'transparent',
              border: brushSize === size ? `2px solid ${t.primary}` : `1px solid ${t.muted}44`,
            }}
            onClick={() => setBrushSize(size)}
            disabled={isDone}
          >
            <div className="rounded-full bg-current" style={{ width: size + 2, height: size + 2, color: t.text }} />
          </button>
        ))}

        <div className="flex-1" />

        {/* Undo & Clear */}
        {enabledTools.includes('undo') && (
          <button
            className="px-2 py-1 rounded-lg text-xs"
            style={{ background: `${t.primary}22`, color: t.muted }}
            onClick={handleUndo}
            disabled={isDone || historyRef.current.length === 0}
          >
            ↩ Undo
          </button>
        )}
        {enabledTools.includes('clear') && (
          <button
            className="px-2 py-1 rounded-lg text-xs"
            style={{ background: '#EF444422', color: '#EF4444' }}
            onClick={handleClear}
            disabled={isDone}
          >
            🗑 Clear
          </button>
        )}
      </div>

      {/* Canvas */}
      <div className="relative rounded-xl overflow-hidden border" style={{ borderColor: `${t.primary}22` }}>
        <canvas
          ref={canvasRef}
          width={canvas_width}
          height={canvas_height}
          className="w-full bg-white"
          style={{
            cursor: isDone ? 'default' : activeTool === 'text' ? 'text' : activeTool === 'eraser' ? 'cell' : 'crosshair',
            touchAction: 'none',
          }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={() => isDrawing && handlePointerUp({ clientX: 0, clientY: 0, touches: null })}
        />

        {/* Text input overlay */}
        {textInput && (
          <div className="absolute" style={{ left: `${(textInput.x / canvas_width) * 100}%`, top: `${(textInput.y / canvas_height) * 100}%` }}>
            <input
              autoFocus
              className="bg-white border-2 border-blue-400 px-2 py-1 text-sm rounded shadow-lg"
              style={{ color: activeColor }}
              placeholder="Type text..."
              onKeyDown={e => {
                if (e.key === 'Enter') handleTextSubmit(e.target.value);
                if (e.key === 'Escape') setTextInput(null);
              }}
              onBlur={e => handleTextSubmit(e.target.value)}
            />
          </div>
        )}
      </div>

      {/* Done button */}
      <div className="flex justify-between items-center mt-3">
        <span className="text-xs" style={{ color: t.muted }}>
          {strokeCount} stroke{strokeCount !== 1 ? 's' : ''} {strokeCount < 5 && '(min 5 to submit)'}
        </span>
        <motion.button
          className="px-5 py-2 rounded-xl font-bold text-sm text-white transition-all"
          style={{
            background: !isDone && strokeCount >= 5 ? t.primary : `${t.primary}44`,
            cursor: !isDone && strokeCount >= 5 ? 'pointer' : 'not-allowed',
            opacity: !isDone && strokeCount >= 5 ? 1 : 0.5,
          }}
          whileTap={!isDone && strokeCount >= 5 ? { scale: 0.97 } : {}}
          onClick={handleDone}
          disabled={isDone || strokeCount < 5}
        >
          {isDone ? '✓ Submitted' : 'Done Drawing'}
        </motion.button>
      </div>
    </div>
  );
};

export default DrawingCanvasWidget;
```

- [ ] **Step 2: Register in WidgetRegistry.js**

Add after `brainstorm_board` entry:

```javascript
  drawing_canvas: lazy(() => import('./DrawingCanvasWidget')),
```

- [ ] **Step 3: Commit**

```bash
git add frontend-react/src/components/game/widgets/DrawingCanvasWidget.jsx frontend-react/src/components/game/widgets/WidgetRegistry.js
git commit -m "feat: add DrawingCanvasWidget with pen, eraser, shapes, text, undo, templates"
```

---

## Task 10: Wire Scene Widgets — onWidgetResult Callback

**Files:**
- Modify: `frontend-react/src/pages/GamePlayPage.jsx`
- Modify: `frontend-react/src/components/game/renderers/SimulationRenderer.jsx`
- Modify: `frontend-react/src/components/game/widgets/InteractiveSceneLayer.jsx`
- Modify: `frontend-react/src/api/games.js`

- [ ] **Step 1: Add widgetResult state + onWidgetResult callback in GamePlayPage.jsx**

After the `freeTextValue` state declaration (line 396), add:

```javascript
const [widgetResult, setWidgetResult] = useState(null);
```

Add a reset in the round-change effect — find where `setSelectedChoice(null)` is called on round change and add `setWidgetResult(null);` next to it.

- [ ] **Step 2: Handle drawing_canvas auto-submit + widget_data attachment in GamePlayPage.jsx**

After the `widgetResult` state, add an effect for drawing canvas auto-submit:

```javascript
// Auto-submit for drawing_canvas: when widget reports done, upload then submit
useEffect(() => {
  if (!widgetResult || widgetResult.widget_type !== 'drawing_canvas' || !widgetResult.done) return;
  const doUpload = async () => {
    try {
      const { uploadDrawing } = await import('../api/games');
      const uploadRes = await uploadDrawing(runId, {
        image_base64: widgetResult.image_base64,
        round_id: currentRound?.round_id || `round_${currentRound?.round_number || 0}`,
        stroke_count: widgetResult.stroke_count,
        tools_used: widgetResult.tools_used,
        time_spent_seconds: widgetResult.time_spent_seconds,
      });
      // Auto-submit the round with drawing_id
      handleChoiceSubmit(null, {
        input_type: 'drawing_canvas',
        widget_data: {
          widget_type: 'drawing_canvas',
          drawing_id: uploadRes.drawing_id,
          stroke_count: widgetResult.stroke_count,
          tools_used: widgetResult.tools_used,
          time_spent_seconds: widgetResult.time_spent_seconds,
        },
      });
    } catch (err) {
      console.error('Drawing upload failed:', err);
    }
  };
  doUpload();
}, [widgetResult]); // eslint-disable-line react-hooks/exhaustive-deps
```

In `handleChoiceSubmit`, after the `structured_response` attachment block (added in Task 4), add:

```javascript
    // Attach widget_data for scene widgets (brainstorm_board, drawing_canvas)
    if (extraData?.widget_data) {
      metadata.widget_data = extraData.widget_data;
    } else if (widgetResult && widgetResult.widget_type === 'brainstorm_board') {
      metadata.widget_data = widgetResult;
    }
```

Also update the submitId line to include drawing_canvas:

```javascript
    const submitId = (inputType === 'free_text' || inputType === 'drawing_canvas' || INPUT_WIDGETS[inputType]) ? null : choiceId;
```

- [ ] **Step 3: Pass onWidgetResult through SimulationRenderer**

In `SimulationRenderer.jsx`, the component receives props at line 378. It doesn't need to accept `onWidgetResult` explicitly — it can just pass it through. Find the InteractiveSceneLayer render at line 824 and change:

```jsx
<InteractiveSceneLayer widget={currentRound.scene_widget} gameState={state} roundIndex={roundIndex} theme={theme} />
```

to:

```jsx
<InteractiveSceneLayer widget={currentRound.scene_widget} gameState={state} roundIndex={roundIndex} theme={theme} onWidgetResult={onWidgetResult} />
```

The `onWidgetResult` prop needs to come from GamePlayPage. Find where SimulationRenderer is rendered in GamePlayPage.jsx and add the prop. Search for `<SimulationRenderer` and add `onWidgetResult={setWidgetResult}`.

- [ ] **Step 4: Pass onWidgetResult through InteractiveSceneLayer**

In `InteractiveSceneLayer.jsx` at line 109, update the props:

```javascript
const InteractiveSceneLayer = ({ widget, gameState, roundIndex, theme, onWidgetResult }) => {
```

At lines 149-155, add `onWidgetResult` to the widget component:

```jsx
<WidgetComponent
  {...(widget.props || {})}
  interactionMode={interactionMode}
  gameState={gameState}
  roundIndex={roundIndex}
  theme={theme}
  onWidgetResult={onWidgetResult}
/>
```

- [ ] **Step 5: Add uploadDrawing to api/games.js**

Add at the end of `frontend-react/src/api/games.js`:

```javascript
/**
 * Upload a drawing PNG from the canvas widget
 * @param {string} runId - Current run ID
 * @param {object} data - { image_base64, round_id, stroke_count, tools_used, time_spent_seconds }
 */
export const uploadDrawing = async (runId, data) => {
  const response = await apiClient.post(`/api/run/${runId}/upload-drawing`, data);
  return response.data;
};
```

- [ ] **Step 6: Commit**

```bash
git add frontend-react/src/pages/GamePlayPage.jsx frontend-react/src/components/game/renderers/SimulationRenderer.jsx frontend-react/src/components/game/widgets/InteractiveSceneLayer.jsx frontend-react/src/api/games.js
git commit -m "feat: wire onWidgetResult callback through SimulationRenderer + InteractiveSceneLayer + auto-submit for drawing canvas"
```

---

## Task 11: Build & Smoke Test

**Files:** None (verification only)

- [ ] **Step 1: Build the frontend**

```bash
cd frontend-react && npm run build
```

Expected: Build succeeds with no errors. Warnings about unused variables are acceptable.

- [ ] **Step 2: Fix any import/build errors**

If build fails, check:
- Missing imports (framer-motion, react)
- Typos in component names
- Circular dependencies

Fix and rebuild until clean.

- [ ] **Step 3: Verify backend syntax**

```bash
cd backend && python3 -c "import app; print('OK')"
```

Expected: Prints "OK" without syntax errors.

- [ ] **Step 4: Verify llm.py loads**

```bash
cd backend && python3 -c "from llm import evaluate_drawing; print('evaluate_drawing loaded')"
```

Expected: Prints "evaluate_drawing loaded"

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve build and import issues from widget integration"
```

---

## Task 12: Final Verification & Summary Commit

- [ ] **Step 1: Verify all new files exist**

```bash
ls -la frontend-react/src/components/game/inputs/
ls -la frontend-react/src/components/game/widgets/BrainstormBoardWidget.jsx
ls -la frontend-react/src/components/game/widgets/DrawingCanvasWidget.jsx
```

Expected: All 5 new files present.

- [ ] **Step 2: Verify WidgetRegistry has new entries**

```bash
grep -n "brainstorm_board\|drawing_canvas" frontend-react/src/components/game/widgets/WidgetRegistry.js
```

Expected: Both entries found.

- [ ] **Step 3: Verify backend has new branches**

```bash
grep -n "structured_form\|slider_rating\|checklist\|drawing_canvas\|upload-drawing\|evaluate_drawing" backend/app.py | head -10
```

Expected: All new input_type strings and endpoint found.

- [ ] **Step 4: Final build**

```bash
cd frontend-react && npm run build
```

Expected: Clean build, no errors.
