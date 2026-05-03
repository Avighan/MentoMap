# Module Quiz Item Bank — Schema & IRT Design

## Overview

Quiz lessons in MentoApp modules support an optional **item bank** alongside
(or instead of) the legacy fixed `questions` list. When a bank is present the
backend uses a naive **Rasch IRT (Item Response Theory)** model to select
questions whose difficulty matches the student's current estimated ability
level (theta).

---

## Lesson JSON Schema

```jsonc
{
  "lesson_id": "week1_quiz",
  "type": "quiz",              // or "assessment"
  "title": "Week 1 Check-In",
  "pass_threshold": 0.7,       // ratio required to mark lesson complete (default 0.6)
  "quiz": {
    "n_questions_per_attempt": 5,   // how many questions to serve per attempt (default 5)

    // ── Option A: Static legacy list (no IRT) ────────────────────────────────
    "questions": [
      { "id": "q1", "text": "What is the difference between revenue and profit?" }
    ],

    // ── Option B: IRT item bank (replaces / supersedes questions[]) ──────────
    "bank": [
      {
        "id": "q_easy_1",        // REQUIRED — unique within lesson
        "difficulty": -1.5,      // Rasch b-parameter; range [-3, 3]
        "text": "What does MVP stand for?",
        "options": [             // optional — multiple-choice
          { "id": "a", "text": "Minimum Viable Product", "correct": true },
          { "id": "b", "text": "Maximum Value Proposition" }
        ],
        "explanation": "MVP = Minimum Viable Product — the simplest version of a product that lets you learn."
      },
      {
        "id": "q_medium_1",
        "difficulty": 0.0,
        "text": "Why would a founder pivot their business model?",
        "type": "freetext"       // optional — 'mcq' (default) | 'freetext' | 'ranking'
      },
      {
        "id": "q_hard_1",
        "difficulty": 2.0,
        "text": "Compare the CAC payback periods of SaaS vs marketplace models."
      }
    ]
  }
}
```

### Difficulty scale

| Range     | Interpretation                              |
|-----------|---------------------------------------------|
| -3 to -2  | Very easy — recall / definition              |
| -2 to -1  | Easy — single-concept understanding          |
| -1 to  0  | Below-average — application in context       |
|  0 to +1  | Average — multi-step reasoning               |
| +1 to +2  | Hard — synthesis / evaluation                |
| +2 to +3  | Very hard — expert-level analysis            |

---

## Per-User Progress Fields

Two new fields are added to the module progress record
(`backend/data/module_progress.json`) by `_empty_progress()`:

```jsonc
{
  "quiz_theta": {
    // lesson_id → float ability estimate, clamped to [-3.0, 3.0]
    "week1_quiz": 0.3
  },
  "quiz_seen_ids": {
    // lesson_id → list of question IDs already shown (capped at 100)
    "week1_quiz": ["q_easy_1", "q_medium_1"]
  }
}
```

Both default to `{}` for existing users — backward-compatible.

---

## Question Selection Algorithm (`select_quiz_questions_irt`)

```python
select_quiz_questions_irt(lesson, prog, n=5) -> list[dict]
```

1. If `quiz.bank` is absent or empty, return `quiz.questions[:n]` (legacy
   fallback — no IRT).
2. Sort `bank` by `|difficulty - theta|` ascending (closest first).
3. Separate into **fresh** (not in `quiz_seen_ids`) and **already-seen**.
4. Take up to `n` fresh items; pad with seen items if the fresh pool is
   smaller than `n`.
5. Return the selected list.

---

## Theta Update Algorithm (`update_quiz_theta`)

```python
update_quiz_theta(prog, lesson_id, items_correct, items_total, seen_ids=[]) -> prog
```

Naive Rasch update applied after every quiz attempt (pass **or** fail):

```
delta = (items_correct / items_total - 0.5) * 1.0
theta_new = clamp(theta_old + delta, -3.0, 3.0)
```

Examples:

| Score | delta  | Effect                      |
|-------|--------|-----------------------------|
| 5/5   | +0.50  | Strong mastery — harder Qs  |
| 4/5   | +0.30  | Good — slightly harder      |
| 3/5   | +0.10  | Near-neutral                |
| 2/5   | -0.10  | Below average — easier Qs  |
| 0/5   | -0.50  | Struggling — much easier   |

The `seen_ids` list is appended to `prog["quiz_seen_ids"][lesson_id]` and
capped at 100 entries (oldest evicted first).

---

## API Endpoint

### `GET /api/modules/<module_id>/lessons/<lesson_id>/quiz-questions`

Returns IRT-selected questions for the authenticated user.

**Auth:** Bearer JWT required.

**Response 200:**

```jsonc
{
  "questions": [ /* question dicts from the bank or legacy list */ ],
  "n": 5,          // number of questions returned
  "theta": 0.3     // current ability estimate for this lesson
}
```

**Error responses:**

| Code | Condition                                |
|------|------------------------------------------|
| 400  | Lesson type is not `quiz` or `assessment`|
| 401  | Missing or invalid JWT                   |
| 404  | Module or lesson not found               |
| 500  | Unexpected server error                  |

---

## Integration Notes

- `update_quiz_theta` is called automatically inside `complete_lesson` for
  `quiz` / `assessment` lessons after the quiz record is persisted.
- The client should pass `seen_ids: ["q1", "q2"]` (the IDs of questions shown
  during the attempt) in the `/complete` request body for accurate tracking.
  If absent, the backend derives `seen_ids` from `answers.keys()`.
- Modules that use the legacy `quiz.questions[]` array continue to work
  without modification; the IRT machinery is skipped when no `bank` is
  present.
