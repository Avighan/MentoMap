# Interactive Widgets for Simulation Games — Design Spec

**Date:** 2026-04-16
**Status:** Draft
**Scope:** 5 new widgets (3 input-type + 2 scene widgets) for entrepreneurship and general simulation games

---

## 1. Overview

### Problem
MentoApp simulations currently support three input modes: `multiple_choice`, `free_text`, and `hybrid`. The MentoMap Entrepreneurship Handbook requires richer interaction patterns — structured multi-field forms (5 WHYs, Pitch Cards), self-assessment sliders with honesty checks, reflective checklists, brainstorming boards, and freehand drawing with AI vision evaluation. These patterns are also reusable across all simulation games, not just entrepreneurship.

### Solution
Build 5 new widgets split across two architectural integration points:

| Widget | Type | Integration Point | Scoring Model |
|--------|------|-------------------|---------------|
| StructuredFormInput | Tier 2 | Input type (replaces choices) | Concatenated fields → single LLM eval via existing `evaluate_free_text_response()` |
| SliderRatingInput | Tier 2 | Input type (replaces choices) | Sliders → direct state deltas + free-text honesty check → LLM eval with penalty |
| ChecklistInput | Tier 2 | Input type (replaces choices) | Checked items → small per-dimension deltas + reflection → LLM eval |
| BrainstormBoardWidget | Tier 3 | Scene widget (WidgetRegistry) | Idea count → tiered creativity delta, attached to next choice submission |
| DrawingCanvasWidget | Tier 3 | Scene widget (WidgetRegistry) | PNG export → Claude Vision API → dimension scoring |

### Architecture: Approach 3 — "Input Types + Scene Widgets"

**Input-type widgets** (StructuredFormInput, SliderRatingInput, ChecklistInput) are standalone React components rendered in GamePlayPage when `input_type` matches. They share a common `onSubmit(payload)` interface and feed into the existing `/api/run/<id>/choose` endpoint.

**Scene widgets** (BrainstormBoardWidget, DrawingCanvasWidget) are WidgetRegistry entries rendered via InteractiveSceneLayer. They communicate results to GamePlayPage via an `onWidgetResult` callback, which attaches data to the next choice submission as metadata.

---

## 2. Tier 2: Input-Type Widgets

### 2.1 Shared Interface

All three input-type widgets share this contract:

**Props:**
```typescript
interface InputWidgetProps {
  config: object;           // Round JSON config (fields, sliders, items, etc.)
  onSubmit: (payload: InputPayload) => void;  // Called when student submits
  disabled: boolean;        // True while processing/transitioning
  colors: ThemeColors;      // App theme palette
}

interface InputPayload {
  choice_id: null;                    // Always null for input-type widgets
  free_text: string;                  // Concatenated text for LLM evaluation
  input_type: string;                 // "structured_form" | "slider_rating" | "checklist"
  structured_response: object;        // Widget-specific structured data
}
```

**File locations:**
- `frontend-react/src/components/game/inputs/StructuredFormInput.jsx`
- `frontend-react/src/components/game/inputs/SliderRatingInput.jsx`
- `frontend-react/src/components/game/inputs/ChecklistInput.jsx`

**GamePlayPage rendering logic:**
```javascript
const INPUT_WIDGETS = {
  structured_form: StructuredFormInput,
  slider_rating: SliderRatingInput,
  checklist: ChecklistInput,
};

// In render:
const InputWidget = INPUT_WIDGETS[inputType];
if (InputWidget) {
  return <InputWidget config={currentRound} onSubmit={handleChoiceSubmit} disabled={isSubmitting} colors={mergedColors} />;
}
// else: fall through to existing ChoiceSelector
```

**Backend processing:**
All three submit through the existing `POST /api/run/<id>/choose` endpoint. The `free_text` field contains the concatenated text for LLM evaluation. The `structured_response` field contains raw widget data, stored in `choice_history` for the post-game report.

New `input_type` values recognized by the backend: `"structured_form"`, `"slider_rating"`, `"checklist"`. All three route to the existing `evaluate_free_text_response()` path, with these additions:

- `structured_response` is saved in `choice_history` alongside existing fields
- `slider_rating` and `checklist` may include `direct_deltas` — resource changes applied before LLM evaluation
- `slider_rating` includes honesty penalty logic (see Section 2.3)

---

### 2.2 StructuredFormInput

**Purpose:** Renders a multi-field form where each field has a label, placeholder, optional hint, and minimum character length. Used for 5 WHYs, Pitch Cards, Customer Personas, etc.

**Round JSON config:**
```json
{
  "input_type": "structured_form",
  "form_title": "The Five WHYs",
  "form_instruction": "Dig into your problem by asking WHY five times. Each answer should go deeper than the last.",
  "form_fields": [
    {
      "key": "why1",
      "label": "WHY #1",
      "placeholder": "Why does this problem exist?",
      "hint": "Start with the obvious reason",
      "min_length": 15,
      "max_length": 200
    },
    {
      "key": "why2",
      "label": "WHY #2",
      "placeholder": "Why is that?",
      "min_length": 15,
      "max_length": 200
    },
    {
      "key": "why3",
      "label": "WHY #3",
      "placeholder": "And why is THAT?",
      "min_length": 15,
      "max_length": 200
    },
    {
      "key": "why4",
      "label": "WHY #4",
      "placeholder": "Go deeper...",
      "min_length": 10,
      "max_length": 200
    },
    {
      "key": "why5",
      "label": "WHY #5",
      "placeholder": "What's the REAL root cause?",
      "hint": "This should reveal the deeper problem",
      "min_length": 10,
      "max_length": 200
    }
  ],
  "evaluation_rubric": {
    "strategic_thinking": "Each WHY digs deeper than the previous — not restating the same problem",
    "creativity": "Final WHY reveals a non-obvious root cause"
  },
  "scoring_dimensions": ["strategic_thinking", "creativity"]
}
```

**UI specification:**
- Card container with `form_title` as heading and `form_instruction` as subtitle
- Vertical stack of form fields, each rendered as:
  - Label (bold, left-aligned)
  - Hint text (small, muted, below label — only if `hint` provided)
  - Textarea (3 rows, auto-expanding, themed border)
  - Character counter (right-aligned, muted → green when min met → red near max)
- Progress indicator: "3/5 fields complete" with a segmented bar
- Submit button: enabled when ALL fields meet `min_length`, disabled otherwise
- Animated field entrance: fields slide in sequentially (staggered 100ms via Framer Motion)

**Submission:**
```json
{
  "choice_id": null,
  "free_text": "WHY #1: School bags have no compartments for stationery.\nWHY #2: Bag makers designed bags as simple containers, not organizers.\nWHY #3: Nobody asked students what they actually need in a bag.\nWHY #4: The bag industry focuses on durability and style, not function.\nWHY #5: School bags are designed with ZERO thought for daily student workflows!",
  "input_type": "structured_form",
  "structured_response": {
    "form_type": "five_whys",
    "fields": {
      "why1": "School bags have no compartments for stationery.",
      "why2": "Bag makers designed bags as simple containers, not organizers.",
      "why3": "Nobody asked students what they actually need in a bag.",
      "why4": "The bag industry focuses on durability and style, not function.",
      "why5": "School bags are designed with ZERO thought for daily student workflows!"
    },
    "completion_time_ms": 142000
  }
}
```

The `free_text` field is constructed by the frontend as: each field prefixed with its label, joined by `\n`. This goes straight to `evaluate_free_text_response()`.

**Other form templates this supports:**
- **Pitch Card:** 6 fields (App Name, Problem, Solution, Customer, Differentiator, 30-Second Pitch)
- **Customer Persona:** 5 fields (Name, Problem, Feelings, Current Solution, Wish)
- **PAUSE Framework:** 5 fields (Pause, Analyse, Extract, Adjust, Act)
- **Failure Journal:** 4 fields (What I tried, What happened, What I learned, What I'll do differently)

All use the same component with different `form_fields` config.

---

### 2.3 SliderRatingInput

**Purpose:** Renders labeled sliders (configurable 1-N scale) with a companion free-text justification. Sliders produce direct resource deltas. The justification is LLM-evaluated, with a honesty penalty if ratings and reasoning don't align.

**Round JSON config:**
```json
{
  "input_type": "slider_rating",
  "rating_title": "Your Idea Scorecard",
  "rating_instruction": "Rate your idea honestly on each dimension. Then explain your highest rating.",
  "sliders": [
    {
      "key": "pain_real",
      "label": "The problem is REAL and painful",
      "low_label": "Not real",
      "high_label": "Very painful",
      "min": 1,
      "max": 5,
      "default": 3,
      "resource_map": { "problem_depth": 3 }
    },
    {
      "key": "solution_fixes",
      "label": "My solution actually FIXES it",
      "low_label": "Doesn't fix",
      "high_label": "Fixes perfectly",
      "min": 1,
      "max": 5,
      "default": 3,
      "resource_map": { "idea_quality": 3 }
    },
    {
      "key": "enough_people",
      "label": "Enough people HAVE this problem",
      "low_label": "Just me",
      "high_label": "Millions",
      "min": 1,
      "max": 5,
      "default": 3,
      "resource_map": { "market_size": 3 }
    },
    {
      "key": "different",
      "label": "My solution is DIFFERENT from others",
      "low_label": "Same as others",
      "high_label": "Completely unique",
      "min": 1,
      "max": 5,
      "default": 3,
      "resource_map": { "idea_quality": 2 }
    },
    {
      "key": "excited",
      "label": "I am EXCITED to work on this",
      "low_label": "Meh",
      "high_label": "Super excited!",
      "min": 1,
      "max": 5,
      "default": 3,
      "resource_map": { "confidence": 3 }
    }
  ],
  "total_label": "Idea Score",
  "total_max": 25,
  "justification_prompt": "Explain why you gave your highest rating. What evidence supports it?",
  "justification_min_length": 30,
  "evaluation_rubric": {
    "strategic_thinking": "Justification shows real evidence, not wishful thinking",
    "ethical_reasoning": "Honest self-assessment — ratings match the reasoning"
  },
  "honesty_check": {
    "enabled": true,
    "quality_threshold": 4,
    "avg_rating_threshold": 4,
    "penalty_multiplier": 0.5
  }
}
```

**UI specification:**
- Card container with title and instruction
- Each slider rendered as:
  - Label text (bold)
  - Horizontal slider track with animated thumb (themed color)
  - Low label (left) and high label (right) below the track
  - Current value displayed on/above the thumb
- Running total bar at bottom: animated fill showing sum / `total_max`, with color bands:
  - 20-25: green ("Strong idea!")
  - 12-19: amber ("Good start, needs work")
  - Under 12: red ("Try a different problem")
- Below sliders: justification textarea with `justification_prompt`
- Character counter on textarea
- Submit button: enabled when justification meets `justification_min_length`

**Scoring flow (backend):**

1. **Direct slider deltas:** For each slider, `value × resource_map[resource]` added to state.
   Example: `pain_real = 4`, `resource_map = { problem_depth: 3 }` → `problem_depth += 12`

2. **LLM evaluation:** `justification` text sent to `evaluate_free_text_response()` with the round's rubric. Returns dimension_deltas, quality_score, feedback.

3. **Honesty penalty check:** If `honesty_check.enabled` AND `quality_score < quality_threshold` (LLM thinks justification is weak, scale 0-10) AND average slider value > `avg_rating_threshold`:
   - All slider direct deltas are multiplied by `penalty_multiplier` (0.5)
   - Additional feedback: "Your ratings were high but your explanation didn't fully support them. Try to be more specific about your evidence."

**Submission:**
```json
{
  "choice_id": null,
  "free_text": "I gave 'The problem is REAL and painful' my highest rating (5) because every single day I see Mrs. Sharma and other elderly neighbors struggling to get medicine. Three aunties in my colony have the same problem and none of them can use delivery apps.",
  "input_type": "slider_rating",
  "structured_response": {
    "slider_values": {
      "pain_real": 5,
      "solution_fixes": 4,
      "enough_people": 4,
      "different": 3,
      "excited": 5
    },
    "total_score": 21,
    "direct_deltas": {
      "problem_depth": 15,
      "idea_quality": 18,
      "market_size": 12,
      "confidence": 15
    },
    "justification": "I gave 'The problem is REAL and painful' my highest rating...",
    "completion_time_ms": 95000
  }
}
```

---

### 2.4 ChecklistInput

**Purpose:** Renders a checkbox list where each item maps to a dimension. After interacting, a reflection textarea appears. Checked items produce small direct deltas; the reflection is LLM-evaluated.

**Round JSON config:**
```json
{
  "input_type": "checklist",
  "checklist_title": "The Resilience Checklist",
  "checklist_instruction": "Tick the ones you already have. Then reflect on the one you most want to build.",
  "items": [
    { "key": "dont_give_up", "label": "I don't give up when things get hard the first time", "dimension": "resilience", "delta": 2 },
    { "key": "ask_help", "label": "I ask for help when I am stuck instead of staying stuck", "dimension": "empathy", "delta": 2 },
    { "key": "feedback_useful", "label": "I see feedback as useful information, not personal attacks", "dimension": "adaptability", "delta": 2 },
    { "key": "new_approaches", "label": "I try new approaches when my first one doesn't work", "dimension": "creativity", "delta": 2 },
    { "key": "small_progress", "label": "I celebrate small progress, not just big wins", "dimension": "delayed_gratification", "delta": 2 },
    { "key": "growth_effort", "label": "I believe that my abilities can grow with effort and practice", "dimension": "resilience", "delta": 2 },
    { "key": "keep_going", "label": "I keep going even when others don't believe in my idea yet", "dimension": "risk_tolerance", "delta": 3 },
    { "key": "learn_others", "label": "I learn from other people's mistakes, not just my own", "dimension": "strategic_thinking", "delta": 2 }
  ],
  "min_checked": 1,
  "reflection_prompt": "Which unchecked item do you most want to develop? Why, and what's one thing you could do this week to start?",
  "reflection_min_length": 30,
  "evaluation_rubric": {
    "resilience": "Shows genuine self-awareness about growth areas",
    "adaptability": "Proposes a concrete, actionable step — not vague intentions"
  },
  "scoring_dimensions": ["resilience", "adaptability"]
}
```

**UI specification:**
- Card container with title and instruction
- Checkbox list, each item rendered as:
  - Custom styled checkbox (rounded, themed accent color, animated check mark)
  - Label text beside checkbox
  - Subtle dimension badge (small pill, e.g., "resilience") — optional, shown if game is in assessment mode
- Progress counter: "5/8 checked" (top right, muted)
- After at least `min_checked` items are checked, the reflection section slides in (Framer Motion):
  - Reflection prompt text
  - Textarea (4 rows, themed border)
  - Character counter
- Submit button: enabled when `min_checked` met AND reflection meets `reflection_min_length`

**Scoring flow (backend):**

1. **Direct checkbox deltas:** For each checked item, add `delta` to its `dimension`.
   Example: checking "dont_give_up" → `resilience += 2`, checking "keep_going" → `risk_tolerance += 3`

2. **LLM evaluation:** Reflection text sent to `evaluate_free_text_response()`. Returns dimension_deltas, quality_score, feedback.

3. **Growth areas stored:** Unchecked item keys stored in `choice_history` as `growth_areas` array for the post-game report.

**Submission:**
```json
{
  "choice_id": null,
  "free_text": "The item I most want to develop is 'I see feedback as useful information, not personal attacks.' I often feel defensive when someone criticizes my work. This week, I will try asking one follow-up question whenever I get feedback instead of immediately reacting.",
  "input_type": "checklist",
  "structured_response": {
    "checked_items": ["dont_give_up", "ask_help", "new_approaches", "small_progress", "keep_going"],
    "unchecked_items": ["feedback_useful", "growth_effort", "learn_others"],
    "checked_count": 5,
    "direct_deltas": {
      "resilience": 2,
      "empathy": 2,
      "creativity": 2,
      "delayed_gratification": 2,
      "risk_tolerance": 3
    },
    "growth_areas": ["feedback_useful", "growth_effort", "learn_others"],
    "reflection": "The item I most want to develop is...",
    "completion_time_ms": 78000
  }
}
```

---

## 3. Tier 3: Scene Widgets

### 3.1 Shared Integration Pattern

Scene widgets communicate with GamePlayPage through a new `onWidgetResult` callback:

**Data flow:**
```
Round JSON
  └── scene_widget: { type, interaction_mode, props }
        │
SimulationRenderer
  └── InteractiveSceneLayer
        └── WidgetComponent (from WidgetRegistry)
              │ calls onWidgetResult(result)
              ▼
GamePlayPage
  └── widgetResult state
        │ attached to next handleChoiceSubmit call
        ▼
Backend /api/run/<id>/choose
  └── widget_data field in request body
        │ processed alongside choice/free_text
        ▼
  scoring_tier_delta applied (brainstorm) OR evaluate_drawing() called (canvas)
```

**GamePlayPage changes:**
- New state: `const [widgetResult, setWidgetResult] = useState(null)`
- `onWidgetResult` callback passed through SimulationRenderer → InteractiveSceneLayer → widget
- In `handleChoiceSubmit`: if `widgetResult` exists, merge into submission payload as `widget_data`
- After submission response received: `setWidgetResult(null)`
- Reset `widgetResult` on round change

**InteractiveSceneLayer changes:**
- Accept new prop: `onWidgetResult`
- Pass to widget component: `<WidgetComponent {...widget.props} onWidgetResult={onWidgetResult} ... />`

**SimulationRenderer changes:**
- Accept `onWidgetResult` prop from GamePlayPage
- Pass through to InteractiveSceneLayer

**Backend `/choose` endpoint changes:**
- Accept optional `widget_data` field in request body
- If `widget_data.widget_type === "brainstorm_board"`: apply `scoring_tier_delta` additively to state
- If `widget_data.widget_type === "drawing_canvas"`: call `evaluate_drawing()`, apply dimension_deltas
- Store `widget_data` in `choice_history` (excluding `image_base64` — use `drawing_id` reference)

---

### 3.2 BrainstormBoardWidget

**Purpose:** A timed sticky-note brainstorming canvas. Students create idea cards within a countdown. Idea count determines a creativity delta tier. Student selects their "best idea." Results attached to the next choice submission.

**File:** `frontend-react/src/components/game/widgets/BrainstormBoardWidget.jsx`
**Registration:** `brainstorm_board: lazy(() => import('./BrainstormBoardWidget'))` in WidgetRegistry.js

**Round JSON config:**
```json
{
  "scene_widget": {
    "type": "brainstorm_board",
    "interaction_mode": "active",
    "props": {
      "timer_seconds": 300,
      "prompt": "Write as many ideas as possible! Good, bad, crazy — ALL of them!",
      "min_ideas": 3,
      "colors": ["#FEF3C7", "#DBEAFE", "#FCE7F3", "#D1FAE5", "#EDE9FE", "#FEE2E2"],
      "best_idea_select": true,
      "scoring_tiers": [
        { "min_count": 8, "delta": { "creativity_points": 15, "confidence": 5 } },
        { "min_count": 5, "delta": { "creativity_points": 10, "confidence": 3 } },
        { "min_count": 3, "delta": { "creativity_points": 6 } },
        { "min_count": 0, "delta": { "creativity_points": 2 } }
      ]
    }
  },
  "choices": [
    { "id": "source_frustration", "label": "A. From YOUR frustration", "delta": { "creativity_points": 5 }, "skill_tags": ["creativity"] },
    { "id": "source_complaints", "label": "B. From complaints you heard", "delta": { "empathy": 5 }, "skill_tags": ["empathy"] },
    { "id": "source_combine", "label": "C. By combining two things", "delta": { "strategic_thinking": 5 }, "skill_tags": ["strategic_thinking"] },
    { "id": "source_ignored", "label": "D. Who is being ignored?", "delta": { "empathy": 8 }, "skill_tags": ["empathy", "ethical_reasoning"] }
  ]
}
```

**UI specification:**

**Layout:**
- Top bar: Timer (MM:SS countdown, animated, pulses red at 30s) | Prompt text | Idea counter ("6 ideas")
- Center: Scrollable grid area (CSS grid, 2-3 columns responsive) containing sticky note cards
- Each sticky note:
  - Randomly assigned color from `colors` array
  - Editable text area (click to edit, auto-focus on creation)
  - Delete button (small X, top-right, appears on hover)
  - Subtle shadow and slight random rotation (-2 to +2 degrees) for organic feel
- Add button: "+" card at the end of the grid (dashed border, click to add new note)
- Keyboard: Enter on a note creates a new note below it

**Timer behavior:**
- Starts when widget mounts (round loads)
- At 30 seconds: timer text turns red, gentle pulse animation
- At 0: "add note" button disables, existing notes remain editable for 10 seconds, then all editing locks
- "I'm done early" button available at any time (pauses timer, moves to best-idea selection)

**Best idea selection (when `best_idea_select: true`):**
- After timer ends (or early stop): overlay message "Pick your BEST idea!"
- All notes become selectable (click to select, gold border + star icon)
- Only one can be selected at a time
- "Confirm" button appears after selection

**Widget result (onWidgetResult callback):**
```json
{
  "widget_type": "brainstorm_board",
  "ideas": ["Pre-order food app", "Digital textbooks", "Smart labels", "Book tracker", "Modular bag", "Drainage tiles", "Solar water heater", "Homework reminder bot"],
  "idea_count": 8,
  "best_idea": "Pre-order food app",
  "best_idea_index": 0,
  "time_used_seconds": 240,
  "time_limit_seconds": 300,
  "scoring_tier_delta": { "creativity_points": 15, "confidence": 5 }
}
```

**Scoring tier resolution:**
Tiers are evaluated top-to-bottom. First tier where `idea_count >= min_count` is selected. The `scoring_tier_delta` is applied additively to the state when the student submits their normal A/B/C/D choice for the round.

---

### 3.3 DrawingCanvasWidget

**Purpose:** A freehand drawing canvas with basic tools. When done, the canvas exports as PNG, uploads to the backend, and gets evaluated by Claude Vision API against a rubric.

**File:** `frontend-react/src/components/game/widgets/DrawingCanvasWidget.jsx`
**Registration:** `drawing_canvas: lazy(() => import('./DrawingCanvasWidget'))` in WidgetRegistry.js

**Round JSON config:**
```json
{
  "scene_widget": {
    "type": "drawing_canvas",
    "interaction_mode": "active",
    "props": {
      "prompt": "Draw your 3 app screens: Home, Place Order, Confirmation",
      "canvas_width": 600,
      "canvas_height": 400,
      "tools": ["pen", "eraser", "shapes", "text", "undo", "clear"],
      "colors": ["#000000", "#EF4444", "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6", "#EC4899"],
      "brush_sizes": [2, 4, 8],
      "template": "three_screens",
      "evaluation_rubric": {
        "strategic_thinking": "Screens show a logical user flow — home leads to action, action leads to confirmation",
        "creativity": "Design shows original thinking, not just copying the example",
        "empathy": "UI considers the end user's needs — clear labels, simple navigation"
      },
      "max_delta": 10,
      "scoring_dimensions": ["strategic_thinking", "creativity", "empathy"]
    }
  },
  "input_type": "drawing_canvas"
}
```

**Dual integration note:** DrawingCanvasWidget is unique — it renders as a scene widget (via WidgetRegistry in the scene panel) but submits as an input type (no A/B/C/D choices). When `input_type` is `"drawing_canvas"`, GamePlayPage:
1. Hides ChoiceSelector entirely (no choices to show)
2. Renders the drawing canvas via InteractiveSceneLayer as usual
3. When the widget calls `onWidgetResult` with `{ done: true, drawing_id }`, GamePlayPage auto-submits via `handleChoiceSubmit(null, { widget_data })` — no student click needed beyond "Done Drawing"

**Canvas templates:**
- `three_screens`: 3 phone-shaped outlines (rounded rects) drawn as light gray guides, labeled "Screen 1", "Screen 2", "Screen 3"
- `single_page`: simple border with title area guide
- `wireframe_grid`: dotted grid (20px spacing) for structured layout
- `none`: completely blank white canvas

**Tools specification:**

| Tool | Icon | Behavior |
|------|------|----------|
| Pen | Pencil icon | Freehand strokes. Color and brush size selectable. Default tool. |
| Eraser | Eraser icon | Removes strokes by drawing with white (composite). Size selectable. |
| Shapes | Square/circle icon | Click-drag to draw rectangle, circle, or line. Dropdown to select shape type. Outlined, not filled. |
| Text | T icon | Click canvas to place insertion point. Input overlay appears for typing. Font size = current brush size × 4. |
| Undo | Arrow-left icon | Removes last stroke/shape/text from history stack. Up to 50 steps. |
| Clear | Trash icon | Clears entire canvas. Confirmation dialog: "Clear everything? This can't be undone." Redraws template if one exists. |

**UI specification:**

**Layout:**
- Top: Prompt text (bold)
- Toolbar (horizontal, below prompt):
  - Tool buttons (icon + label, active state highlighted)
  - Color picker strip (small circles, active has ring)
  - Brush size toggle (3 circles of increasing size, active has ring)
- Center: HTML5 `<canvas>` element
  - White background with template guides drawn in #E5E7EB
  - Touch support for tablet/mobile (pointer events)
  - Cursor changes per tool (crosshair for pen, circle for eraser, cross for shapes)
- Bottom: "Done Drawing" button (primary themed, disabled until at least 5 strokes made)

**Canvas implementation:**
- HTML5 Canvas 2D API
- Stroke history stored as array of objects: `{ type: 'path'|'shape'|'text', points: [], color, size, ... }`
- Undo pops from history and redraws all remaining strokes
- Template guides drawn first (not part of history, preserved on clear)
- Responsive: canvas scales to container width, maintains aspect ratio
- Export: `canvas.toDataURL('image/png')` at full resolution

**Upload and evaluation flow:**

1. Student clicks "Done Drawing"
2. Frontend exports canvas to PNG base64
3. Frontend calls `POST /api/run/<run_id>/upload-drawing`:
   ```json
   {
     "image_base64": "data:image/png;base64,...",
     "round_id": "round_8",
     "stroke_count": 47,
     "tools_used": ["pen", "shapes", "text"],
     "time_spent_seconds": 180
   }
   ```
4. Backend stores PNG to `game_sessions/<run_id>/drawings/<round_id>.png`
5. Backend generates thumbnail (200px wide) for storage in choice_history
6. Backend returns `{ "drawing_id": "<round_id>", "status": "uploaded" }`
7. Frontend auto-submits the round via `/choose`:
   ```json
   {
     "choice_id": null,
     "input_type": "drawing_canvas",
     "widget_data": {
       "widget_type": "drawing_canvas",
       "drawing_id": "<round_id>",
       "stroke_count": 47,
       "tools_used": ["pen", "shapes", "text"],
       "time_spent_seconds": 180
     }
   }
   ```
8. Backend loads the PNG from disk, calls `evaluate_drawing()`
9. Results (dimension_deltas, feedback, quality_score) returned in response

**Backend: New endpoint — `POST /api/run/<run_id>/upload-drawing`**
```python
@app.route('/api/run/<run_id>/upload-drawing', methods=['POST'])
def upload_drawing(run_id):
    # Validate run exists and is active
    # Extract image_base64 from request
    # Decode base64, validate it's a valid PNG (check header bytes)
    # Save to game_sessions/<run_id>/drawings/<round_id>.png
    # Generate 200px-wide thumbnail, save as <round_id>_thumb.png
    # Return { drawing_id, status: "uploaded" }
```

**Backend: New function — `evaluate_drawing()` in llm.py**
```python
def evaluate_drawing(
    situation: str,
    image_path: str,
    evaluation_rubric: dict,
    scoring_dimensions: list,
    max_delta: int = 10,
) -> dict:
    """
    Sends drawing image to Claude Vision API for evaluation.

    Returns same structure as evaluate_free_text_response():
    {
        "dimension_scores": { "strategic_thinking": 7, ... },
        "dimension_deltas": { "strategic_thinking": 7, ... },
        "feedback": "Your app screens show a clear user flow...",
        "quality_score": 7,
        "skill_tags": ["strategic_thinking", "empathy"],
        "matched_label": "Thoughtful Designer",
        "sentiment_valence": 0.6,
        "engagement_level": "high"
    }
    """
    # Read image from disk
    # Build Claude API message with image content block + text rubric
    # Parse structured JSON response
    # Scale scores to max_delta
    # Return standardized eval dict
```

**Vision API prompt:**
```
A Grade 6 student was asked: "{situation}"

They drew the image below. Evaluate their drawing against these criteria:
{for dim, hint in rubric: "- {dim}: {hint}"}

Score each dimension 0-10 (10 = excellent evidence, 5 = moderate, 0 = no evidence).
Consider effort, clarity, logical flow, and creativity — not artistic skill.
Provide brief, encouraging coaching feedback (2-3 sentences).
Return JSON: { "dimension_scores": {...}, "feedback": "...", "quality_score": N, "skill_tags": [...], "matched_label": "..." }
```

**Fallback (if Vision API unavailable):**
- Score based on metadata: stroke_count > 20 → quality 6, > 10 → quality 4, else → quality 3
- Dimension scores derived from tool diversity (used shapes + text = higher strategic_thinking)
- Generic feedback: "Great effort on your drawing! The more detail you add, the clearer your idea becomes."

---

## 4. Backend Changes Summary

### 4.1 app.py — `/api/run/<id>/choose` modifications

**New input_type handling** (added to existing decision tree at ~line 2435):

```python
if _input_type in ("structured_form", "slider_rating", "checklist"):
    _free_text = data.get("free_text", "")
    _structured = data.get("structured_response", {})

    # For slider_rating and checklist: apply direct_deltas first
    if _structured.get("direct_deltas"):
        for resource, delta_val in _structured["direct_deltas"].items():
            state.apply_delta(resource, delta_val)

    # LLM evaluate the free_text portion
    _eval = evaluate_free_text_response(
        situation=_round.get("situation") or _round.get("story_text", ""),
        player_text=_free_text,
        scoring_dimensions=_dims,
        evaluation_rubric=_rubric,
        max_delta=_round.get("max_delta_per_dimension", 12)
    )

    # Honesty penalty for slider_rating
    if _input_type == "slider_rating":
        _honesty = _round.get("honesty_check", {})
        if _honesty.get("enabled"):
            _avg_slider = sum(_structured.get("slider_values", {}).values()) / max(len(_structured.get("slider_values", {})), 1)
            if _eval.get("quality_score", 10) < _honesty.get("quality_threshold", 4) and _avg_slider > _honesty.get("avg_rating_threshold", 4):
                _penalty = _honesty.get("penalty_multiplier", 0.5)
                for resource, delta_val in _structured.get("direct_deltas", {}).items():
                    _reduction = delta_val - int(delta_val * _penalty)
                    state.apply_delta(resource, -_reduction)
                _eval["honesty_penalty_applied"] = True

    # Apply LLM dimension deltas
    new_state, outcome = apply_free_text_response(game, state, _free_text, _eval)

    # Store structured_response in choice_history
    outcome["structured_response"] = _structured

elif _input_type == "drawing_canvas":
    _widget_data = data.get("widget_data", {})
    _drawing_id = _widget_data.get("drawing_id")

    if _drawing_id:
        _image_path = f"game_sessions/{run_id}/drawings/{_drawing_id}.png"
        _eval = evaluate_drawing(
            situation=_round.get("situation") or _round.get("story_text", ""),
            image_path=_image_path,
            evaluation_rubric=_rubric,
            scoring_dimensions=_dims,
            max_delta=_round.get("max_delta_per_dimension", 10)
        )
        new_state, outcome = apply_free_text_response(game, state, f"[Drawing: {_drawing_id}]", _eval)
        outcome["drawing_eval"] = _eval
        outcome["widget_data"] = {k: v for k, v in _widget_data.items() if k != "image_base64"}
```

**Widget data from scene widgets (brainstorm_board):**
```python
# After normal choice processing, check for widget_data
_widget_data = data.get("widget_data", {})
if _widget_data.get("widget_type") == "brainstorm_board":
    _tier_delta = _widget_data.get("scoring_tier_delta", {})
    for resource, delta_val in _tier_delta.items():
        state.apply_delta(resource, delta_val)
    # Store in choice_history
    outcome.setdefault("widget_data", {}).update(_widget_data)
```

### 4.2 app.py — New endpoint: `POST /api/run/<id>/upload-drawing`

- Accepts `image_base64`, `round_id`, `stroke_count`, `tools_used`, `time_spent_seconds`
- Validates run exists and is active
- Decodes base64, validates PNG header
- Max image size: 2MB
- Stores to `game_sessions/<run_id>/drawings/<round_id>.png`
- Generates 200px-wide thumbnail
- Returns `{ drawing_id, status: "uploaded" }`

### 4.3 llm.py — New function: `evaluate_drawing()`

- Accepts situation, image_path, evaluation_rubric, scoring_dimensions, max_delta
- Reads image from disk, converts to base64 for Claude Vision API
- Sends as image content block with evaluation prompt
- Parses JSON response, scales scores to max_delta
- Returns same structure as `evaluate_free_text_response()`
- Fallback scoring based on metadata if Vision API unavailable

### 4.4 No changes to core/rounds.py

`apply_free_text_response()` already handles the output format from both `evaluate_free_text_response()` and the new `evaluate_drawing()` since they return identical structures.

---

## 5. Frontend Changes Summary

### 5.1 New files

| File | Purpose |
|------|---------|
| `src/components/game/inputs/StructuredFormInput.jsx` | Multi-field form input widget |
| `src/components/game/inputs/SliderRatingInput.jsx` | Slider ratings + justification widget |
| `src/components/game/inputs/ChecklistInput.jsx` | Checkbox list + reflection widget |
| `src/components/game/widgets/BrainstormBoardWidget.jsx` | Timed sticky-note brainstorming |
| `src/components/game/widgets/DrawingCanvasWidget.jsx` | Freehand drawing canvas with tools |

### 5.2 Modified files

| File | Change |
|------|--------|
| `src/pages/GamePlayPage.jsx` | Import input widgets, add `INPUT_WIDGETS` map, render based on `input_type`. Add `widgetResult` state and `onWidgetResult` callback. Attach `widget_data` in `handleChoiceSubmit`. Handle `drawing_canvas` auto-submit after upload. |
| `src/components/game/renderers/SimulationRenderer.jsx` | Accept and pass `onWidgetResult` prop to InteractiveSceneLayer |
| `src/components/game/widgets/InteractiveSceneLayer.jsx` | Accept and pass `onWidgetResult` prop to widget component |
| `src/components/game/widgets/WidgetRegistry.js` | Add 2 entries: `brainstorm_board`, `drawing_canvas` |
| `src/api/game.js` (or new `src/api/drawing.js`) | Add `uploadDrawing(runId, data)` API function |

### 5.3 No changes to ChoiceSelector.jsx

The existing component remains untouched. New input types are handled before ChoiceSelector renders.

---

## 6. Data Storage & Post-Game Report

### What gets stored in choice_history per round:

**structured_form:**
```json
{
  "round": 5,
  "choice_id": "__free_text__",
  "input_type": "structured_form",
  "free_text": "WHY #1: ...\nWHY #2: ...",
  "structured_response": { "form_type": "five_whys", "fields": { ... } },
  "matched_label": "Deep Thinker",
  "quality_score": 8,
  "skill_tags": ["strategic_thinking"],
  "completion_time_ms": 142000
}
```

**slider_rating:**
```json
{
  "round": 7,
  "choice_id": "__free_text__",
  "input_type": "slider_rating",
  "structured_response": { "slider_values": { ... }, "total_score": 21, "justification": "..." },
  "honesty_penalty_applied": false,
  "quality_score": 7,
  "skill_tags": ["strategic_thinking", "ethical_reasoning"]
}
```

**checklist:**
```json
{
  "round": 10,
  "choice_id": "__free_text__",
  "input_type": "checklist",
  "structured_response": { "checked_items": [...], "growth_areas": [...], "reflection": "..." },
  "quality_score": 6,
  "skill_tags": ["resilience"]
}
```

**brainstorm_board (attached to choice):**
```json
{
  "round": 6,
  "choice_id": "source_frustration",
  "widget_data": { "widget_type": "brainstorm_board", "ideas": [...], "idea_count": 8, "best_idea": "..." },
  "skill_tags": ["creativity"]
}
```

**drawing_canvas:**
```json
{
  "round": 8,
  "choice_id": "__free_text__",
  "input_type": "drawing_canvas",
  "drawing_id": "round_8",
  "drawing_thumbnail": "base64_of_200px_thumb",
  "drawing_eval": { "dimension_scores": {...}, "feedback": "..." },
  "quality_score": 7,
  "stroke_count": 47,
  "tools_used": ["pen", "shapes", "text"]
}
```

**PostGameInsights** can use `structured_response`, `growth_areas`, `best_idea`, and `drawing_thumbnail` to render richer post-game summaries. This is a future enhancement — not part of this spec.

---

## 7. Constraints & Edge Cases

- **LLM unavailable:** All widgets have fallback scoring. Structured form/checklist/slider use midpoint scores. Drawing uses stroke-count heuristic. Brainstorm board uses counting only (no LLM needed).
- **Drawing too large:** Max 2MB PNG upload. Canvas resolution capped at 1200x800 actual pixels regardless of display scaling.
- **Empty submissions:** All widgets enforce minimums before enabling submit (min_length for text, min_checked for checklist, min 5 strokes for drawing, min_ideas for brainstorm).
- **Mobile:** All widgets must be touch-friendly. Drawing canvas supports pointer events. Brainstorm notes support tap-to-edit. Sliders support touch drag.
- **Backward compatibility:** Games that don't use these new `input_type` values are completely unaffected. The new code paths only activate when `input_type` matches a new widget type.
- **Timer persistence:** If student navigates away during a brainstorm timer and comes back, the timer resets. Ideas already created are lost. This is acceptable for the MVP.
- **Client-side delta tampering:** Slider direct_deltas, checklist direct_deltas, and brainstorm scoring_tier_delta are computed on the frontend for responsiveness. The backend MUST re-validate these before applying: re-compute slider deltas from `slider_values` × `resource_map` (from round JSON), re-compute checklist deltas from `checked_items` × item config, and re-resolve brainstorm tier from `idea_count` against `scoring_tiers`. Never trust frontend-computed deltas blindly.
- **Drawing canvas without choices:** When `input_type` is `"drawing_canvas"`, the round has no `choices` array. GamePlayPage must handle this gracefully — hide ChoiceSelector, show only the scene widget, and auto-submit when `onWidgetResult` fires with `done: true`.
