"""
Modules Engine — multi-user, multi-tenant guided learning courses.

A "module" is a structured, multi-week curriculum (e.g. the Mento Entrepreneurship
4-week handbook). It groups together lessons, worksheets, reflections and game
sessions in a sequence that students progress through.

Module content lives as JSON in `backend/modules/*.json`.
Per-user progress + worksheet answers live in `backend/data/module_progress.json`.
Cohort assignments live in `backend/data/module_cohort_assignments.json`.

This module is intentionally dependency-free (just stdlib + project files) so it
can be imported from `app.py` without circular imports.
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------- Paths ----------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.join(_THIS_DIR, "modules")
DATA_DIR = os.path.join(_THIS_DIR, "data")
PROGRESS_FILE = os.path.join(DATA_DIR, "module_progress.json")
COHORT_ASSIGN_FILE = os.path.join(DATA_DIR, "module_cohort_assignments.json")

# Lock for concurrent writes (multi-user safe within one process).
_FILE_LOCK = threading.Lock()

# In-memory cache of module JSON. Refreshed on file mtime change.
_MODULE_CACHE: Dict[str, Dict[str, Any]] = {}
_MODULE_CACHE_MTIME: Dict[str, float] = {}


# ---------- Generic JSON helpers ----------

def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _safe_load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read %s: %s. Using default.", path, e)
        return default


def _safe_write_json(path: str, data: Any) -> None:
    _ensure_data_dir()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- Module catalogue ----------

def _scan_modules() -> List[str]:
    if not os.path.isdir(MODULES_DIR):
        return []
    return sorted(
        f[:-5] for f in os.listdir(MODULES_DIR)
        if f.endswith(".json") and not f.startswith("_")
    )


def _load_module_from_disk(module_id: str) -> Optional[Dict[str, Any]]:
    fpath = os.path.join(MODULES_DIR, f"{module_id}.json")
    if not os.path.exists(fpath):
        return None
    try:
        mtime = os.path.getmtime(fpath)
        cached = _MODULE_CACHE.get(module_id)
        if cached and _MODULE_CACHE_MTIME.get(module_id) == mtime:
            return cached
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        _MODULE_CACHE[module_id] = data
        _MODULE_CACHE_MTIME[module_id] = mtime
        return data
    except Exception as e:
        logger.error("Failed to load module %s: %s", module_id, e)
        return None


def get_module(module_id: str) -> Optional[Dict[str, Any]]:
    """Return the full module JSON, or None if not found."""
    return _load_module_from_disk(module_id)


def list_modules(
    org_id: Optional[str] = None,
    grade: Optional[str] = None,
    include_full: bool = False,
) -> List[Dict[str, Any]]:
    """
    Return summary cards for all available modules. Filters:
      - org_id: future use; for now all modules visible to all orgs unless the
                module declares `org_ids` to scope visibility.
      - grade: numeric grade as a string ('6', '7', '8'); modules with a
               `target_grade` range like '6-9' include this grade.
    """
    summaries: List[Dict[str, Any]] = []
    for mid in _scan_modules():
        m = _load_module_from_disk(mid)
        if not m:
            continue

        # Org scoping (optional, additive)
        m_orgs = m.get("org_ids")
        if m_orgs and org_id and org_id not in m_orgs:
            continue

        # Grade filter
        if grade:
            tg = str(m.get("target_grade", "")).strip()
            if tg:
                if "-" in tg:
                    try:
                        lo, hi = (int(x) for x in tg.split("-", 1))
                        if not (lo <= int(grade) <= hi):
                            continue
                    except ValueError:
                        pass
                elif tg != str(grade):
                    continue

        if include_full:
            summaries.append(m)
        else:
            summaries.append({
                "module_id": m.get("module_id", mid),
                "title": m.get("title"),
                "subtitle": m.get("subtitle"),
                "description": m.get("description"),
                "tagline": m.get("tagline"),
                "icon": m.get("icon"),
                "cover_color": m.get("cover_color"),
                "duration_weeks": m.get("duration_weeks"),
                "estimated_minutes_per_week": m.get("estimated_minutes_per_week"),
                "total_lessons": m.get("total_lessons") or sum(
                    len(w.get("lessons", [])) for w in m.get("weeks", [])
                ),
                "target_grade": m.get("target_grade"),
                "target_age_min": m.get("target_age_min"),
                "target_age_max": m.get("target_age_max"),
                "difficulty": m.get("difficulty"),
                "target_skills": m.get("target_skills", []),
                "tags": m.get("tags", []),
                "nep_stage": m.get("nep_stage"),
                "nep_competencies": m.get("nep_competencies", []),
                "outline": m.get("outline", []),
                "multi_user": m.get("multi_user", True),
                "cohort_compatible": m.get("cohort_compatible", True),
                "available_languages": m.get("available_languages", ["en"]),
            })
    return summaries


# ---------- Per-user progress ----------

def _load_progress() -> Dict[str, Any]:
    return _safe_load_json(PROGRESS_FILE, {"users": {}})


def _save_progress(data: Dict[str, Any]) -> None:
    _safe_write_json(PROGRESS_FILE, data)


def _empty_progress(module_id: str) -> Dict[str, Any]:
    return {
        "module_id": module_id,
        "started_at": _now_iso(),
        "last_active_at": _now_iso(),
        "completed_at": None,
        "current_week_id": None,
        "current_lesson_id": None,
        "completed_lesson_ids": [],
        "worksheets": {},      # lesson_id -> {answers, saved_at}
        "reflections": {},     # lesson_id -> {answers, saved_at}
        "quizzes": {},         # lesson_id -> {answers, score, max_score, passed, attempts, saved_at}
        "game_runs": {},       # lesson_id -> [run_id]
        "lesson_meta": {},     # lesson_id -> {time_spent_seconds}
        "field_missions": {},  # lesson_id -> {entries: [...], submitted_at}
        "rubrics": {},         # lesson_id -> {score, strengths, improvements, dim_signals}
        "quiz_theta": {},      # lesson_id -> float  (Rasch ability estimate, clamped to [-3, 3])
        "quiz_seen_ids": {},   # lesson_id -> list[str]  (question IDs already shown, capped at 100)
    }


def _is_week_unlocked(prog: Dict[str, Any], module: Dict[str, Any], week_id: str) -> bool:
    """A week is unlocked iff every required lesson in all PRIOR weeks is completed.

    Week 1 is always unlocked. If the module declares progression='free',
    every week is unlocked. If a quiz lesson exists in a prior week and was
    not passed, that prior week counts as incomplete.
    """
    if (module.get("progression") or "linear").lower() == "free":
        return True
    weeks = module.get("weeks", [])
    if not weeks or week_id == weeks[0].get("week_id"):
        return True
    completed = set(prog.get("completed_lesson_ids", []) or [])
    quizzes = prog.get("quizzes") or {}
    for w in weeks:
        if w.get("week_id") == week_id:
            return True
        for l in w.get("lessons", []) or []:
            if l.get("optional"):
                continue
            lid = l.get("lesson_id")
            if lid not in completed:
                return False
            # Quiz lessons must also be passed
            if l.get("type") in ("quiz", "assessment"):
                q = quizzes.get(lid) or {}
                if not q.get("passed", False):
                    return False
    return True


def _is_lesson_unlocked(prog: Dict[str, Any], module: Dict[str, Any], lesson_id: str) -> bool:
    """A lesson is unlocked iff its containing week is unlocked."""
    for w in module.get("weeks", []):
        for l in w.get("lessons", []) or []:
            if l.get("lesson_id") == lesson_id:
                return _is_week_unlocked(prog, module, w.get("week_id"))
    return False


def get_user_progress(user_id: str, module_id: str) -> Dict[str, Any]:
    """Return progress object for a user+module. Empty (not started) if absent."""
    data = _load_progress()
    user_block = data.get("users", {}).get(str(user_id), {})
    return user_block.get(module_id, _empty_progress(module_id))


def list_user_modules(user_id: str) -> Dict[str, Dict[str, Any]]:
    """All progress for a single user, keyed by module_id."""
    data = _load_progress()
    return data.get("users", {}).get(str(user_id), {})


def start_module(user_id: str, module_id: str) -> Dict[str, Any]:
    """Initialize progress on first start. Idempotent."""
    module = get_module(module_id)
    if not module:
        raise ValueError(f"Module not found: {module_id}")

    with _FILE_LOCK:
        data = _load_progress()
        users = data.setdefault("users", {})
        user_block = users.setdefault(str(user_id), {})
        if module_id in user_block:
            user_block[module_id]["last_active_at"] = _now_iso()
        else:
            prog = _empty_progress(module_id)
            weeks = module.get("weeks", [])
            if weeks and weeks[0].get("lessons"):
                prog["current_week_id"] = weeks[0]["week_id"]
                prog["current_lesson_id"] = weeks[0]["lessons"][0]["lesson_id"]
            user_block[module_id] = prog
        _save_progress(data)
        return user_block[module_id]


def _flatten_lessons(module: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return [(week_id, lesson_obj), ...] in display order."""
    out: List[Dict[str, Any]] = []
    for week in module.get("weeks", []):
        wid = week.get("week_id")
        for lesson in week.get("lessons", []):
            l = dict(lesson)
            l["week_id"] = wid
            out.append(l)
    return out


def _next_lesson(module: Dict[str, Any], current_lesson_id: Optional[str]) -> Optional[Dict[str, Any]]:
    flat = _flatten_lessons(module)
    if not flat:
        return None
    if current_lesson_id is None:
        return flat[0]
    for i, l in enumerate(flat):
        if l["lesson_id"] == current_lesson_id and i + 1 < len(flat):
            return flat[i + 1]
    return None


# ---------- IRT / Rasch quiz item bank ----------

def select_quiz_questions_irt(
    lesson: Dict[str, Any],
    prog: Dict[str, Any],
    n: int = 5,
) -> List[Dict[str, Any]]:
    """Select *n* questions from lesson.quiz.bank at difficulty closest to the
    player's current theta (Rasch ability estimate).

    Falls back to the legacy ``lesson.quiz.questions`` list when no bank is
    present so that existing modules continue to work without modification.

    Args:
        lesson: Lesson dict (must carry ``lesson_id``).
        prog:   Per-user module progress dict.
        n:      Number of questions to return.

    Returns:
        A list of question dicts, length ≤ n.
    """
    quiz = lesson.get("quiz", {}) or {}
    bank: List[Dict[str, Any]] = quiz.get("bank") or []
    if not bank:
        # Legacy fallback
        return (quiz.get("questions") or [])[:n]

    # Standardise on lesson_id — same key used by complete_lesson and
    # update_quiz_theta — to avoid theta read/write mismatch.
    lid = lesson.get("lesson_id") or ""

    theta: float = (prog.get("quiz_theta") or {}).get(lid, 0.0)

    # Sort bank by absolute distance from theta.
    bank_sorted = sorted(bank, key=lambda q: abs((q.get("difficulty") or 0.0) - theta))

    seen: set = set((prog.get("quiz_seen_ids") or {}).get(lid, []))

    fresh = [q for q in bank_sorted if q.get("id") not in seen][:n]
    if len(fresh) < n:
        # Pad with already-seen items when the fresh pool is exhausted.
        already_seen = [q for q in bank_sorted if q.get("id") in seen]
        fresh = fresh + already_seen[: n - len(fresh)]

    return fresh


def update_quiz_theta(
    prog: Dict[str, Any],
    lesson_id: str,
    items_correct: int,
    items_total: int,
    seen_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Naive Rasch theta update: shift by (pct_correct - 0.5) × 1.0 per attempt.

    At 80% correct the delta is +0.3; at 40% correct it is -0.1, etc.
    The estimate is clamped to [-3.0, 3.0].

    Also persists *seen_ids* (the question IDs shown this attempt) so that
    ``select_quiz_questions_irt`` can deprioritise already-seen items.
    The seen list is capped at 100 entries (oldest evicted first) to avoid
    unbounded growth.

    Args:
        prog:          Per-user module progress dict (mutated in place).
        lesson_id:     Lesson identifier string.
        items_correct: Number of correct answers in this attempt.
        items_total:   Total number of questions attempted.
        seen_ids:      List of question IDs presented this attempt (optional).

    Returns:
        The mutated *prog* dict.
    """
    if items_total == 0:
        return prog

    pct = items_correct / items_total
    delta = (pct - 0.5) * 1.0  # ±0.5 for 100 % or 0 % correct

    th = prog.setdefault("quiz_theta", {})
    th[lesson_id] = max(-3.0, min(3.0, th.get(lesson_id, 0.0) + delta))

    # Persist seen question IDs.
    if seen_ids:
        seen_map = prog.setdefault("quiz_seen_ids", {})
        existing: List[str] = list(seen_map.get(lesson_id, []))
        for qid in seen_ids:
            if qid not in existing:
                existing.append(qid)
        # Cap at 100 entries — evict oldest.
        seen_map[lesson_id] = existing[-100:]

    return prog


def complete_lesson(
    user_id: str,
    module_id: str,
    lesson_id: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Mark a lesson complete. `payload` may include:
      - answers: dict of worksheet/reflection answers
      - run_id: a game session id (for type=game lessons)
      - time_spent_seconds: int

    Idempotent: completing twice doesn't double-record.
    """
    module = get_module(module_id)
    if not module:
        raise ValueError(f"Module not found: {module_id}")

    # Validate lesson exists
    lesson = None
    for w in module.get("weeks", []):
        for l in w.get("lessons", []):
            if l.get("lesson_id") == lesson_id:
                lesson = l
                break
        if lesson:
            break
    if not lesson:
        raise ValueError(f"Lesson not found in module: {lesson_id}")

    payload = payload or {}

    with _FILE_LOCK:
        data = _load_progress()
        users = data.setdefault("users", {})
        user_block = users.setdefault(str(user_id), {})
        prog = user_block.get(module_id) or _empty_progress(module_id)

        # Enforce week gating: prior weeks' required lessons must be complete.
        if not _is_lesson_unlocked(prog, module, lesson_id):
            raise PermissionError(
                "This lesson is locked. Finish the previous week first."
            )

        ltype = lesson.get("type")

        # Quiz / assessment lessons require a passing score before they can be
        # marked complete. The client must send {answers, score, max_score, passed}.
        if ltype in ("quiz", "assessment"):
            qrec = prog.setdefault("quizzes", {}).get(lesson_id, {})
            attempts = int(qrec.get("attempts", 0)) + 1
            score = float(payload.get("score", 0) or 0)
            max_score = float(payload.get("max_score", 0) or 0)
            pass_threshold = float(lesson.get("pass_threshold") or lesson.get("schema", {}).get("pass_threshold") or 0.6)
            ratio = (score / max_score) if max_score else 0.0
            passed = bool(payload.get("passed")) or ratio >= pass_threshold
            prog["quizzes"][lesson_id] = {
                "answers": payload.get("answers") or {},
                "score": score,
                "max_score": max_score,
                "ratio": round(ratio, 3),
                "pass_threshold": pass_threshold,
                "passed": passed,
                "attempts": attempts,
                "saved_at": _now_iso(),
            }
            # IRT theta update — runs on every attempt (pass or fail) so the
            # difficulty calibration improves even when the student retries.
            # round() so partial-credit float scores (e.g. 4.5/5) don't
            # silently truncate and skew the calibration pessimistically.
            _items_correct = round(score) if max_score else 0
            _items_total = round(max_score) if max_score else 0
            _seen_ids = (
                payload.get("seen_ids")
                or list((payload.get("answers") or {}).keys())
            )
            update_quiz_theta(
                prog, lesson_id,
                items_correct=_items_correct,
                items_total=_items_total,
                seen_ids=_seen_ids,
            )
            if not passed:
                # Save attempt but DO NOT mark complete or advance.
                prog["last_active_at"] = _now_iso()
                user_block[module_id] = prog
                _save_progress(data)
                return prog

        prog["last_active_at"] = _now_iso()
        if lesson_id not in prog["completed_lesson_ids"]:
            prog["completed_lesson_ids"].append(lesson_id)

        # Persist payload
        if "answers" in payload and ltype not in ("quiz", "assessment"):
            if ltype == "reflection":
                prog["reflections"][lesson_id] = {
                    "answers": payload["answers"],
                    "saved_at": _now_iso(),
                }
            else:
                prog["worksheets"][lesson_id] = {
                    "answers": payload["answers"],
                    "saved_at": _now_iso(),
                }
        if "run_id" in payload and payload["run_id"]:
            runs = prog["game_runs"].setdefault(lesson_id, [])
            if payload["run_id"] not in runs:
                runs.append(payload["run_id"])
        if "time_spent_seconds" in payload:
            meta = prog["lesson_meta"].setdefault(lesson_id, {})
            meta["time_spent_seconds"] = (
                meta.get("time_spent_seconds", 0) + int(payload["time_spent_seconds"] or 0)
            )

        # Advance pointer to the next lesson
        nxt = _next_lesson(module, lesson_id)
        if nxt is None:
            prog["completed_at"] = prog.get("completed_at") or _now_iso()
            prog["current_week_id"] = None
            prog["current_lesson_id"] = None
        else:
            prog["current_week_id"] = nxt["week_id"]
            prog["current_lesson_id"] = nxt["lesson_id"]

        # Optional lessons must not gate completion: if every REQUIRED lesson
        # is done, mark the module complete even if bonus lessons remain.
        if not prog.get("completed_at"):
            flat_all = []
            for w in module.get("weeks", []):
                flat_all.extend(w.get("lessons", []) or [])
            required_ids = [l.get("lesson_id") for l in flat_all if not l.get("optional")]
            done_set = set(prog.get("completed_lesson_ids", []))
            if required_ids and all(rid in done_set for rid in required_ids):
                prog["completed_at"] = _now_iso()

        user_block[module_id] = prog
        _save_progress(data)
        return prog


def persist_rubric(
    user_id: str,
    module_id: str,
    lesson_id: str,
    rubric_result: Dict[str, Any],
) -> None:
    """Persist a rubric grading result into prog['rubrics'][lesson_id]."""
    with _FILE_LOCK:
        data = _load_progress()
        users = data.setdefault("users", {})
        user_block = users.setdefault(str(user_id), {})
        prog = user_block.get(module_id) or _empty_progress(module_id)
        prog.setdefault("rubrics", {})[lesson_id] = rubric_result
        prog["last_active_at"] = _now_iso()
        user_block[module_id] = prog
        _save_progress(data)


def save_worksheet(
    user_id: str,
    module_id: str,
    lesson_id: str,
    answers: Dict[str, Any],
) -> Dict[str, Any]:
    """Save worksheet answers WITHOUT marking the lesson complete (autosave)."""
    with _FILE_LOCK:
        data = _load_progress()
        users = data.setdefault("users", {})
        user_block = users.setdefault(str(user_id), {})
        prog = user_block.get(module_id) or _empty_progress(module_id)
        prog["worksheets"][lesson_id] = {
            "answers": answers,
            "saved_at": _now_iso(),
        }
        prog["last_active_at"] = _now_iso()
        user_block[module_id] = prog
        _save_progress(data)
        return prog["worksheets"][lesson_id]


def add_field_mission_entry(
    user_id: str,
    module_id: str,
    lesson_id: str,
    entry: Dict[str, Any],
) -> Dict[str, Any]:
    """Append one capture (text/photo/voice) to a field_mission lesson.

    `entry` is a free-form dict — typically {complaint, person, frequency,
    capture_type, photo_url|voice_url|note}. The function adds an `entry_id`
    and `created_at` and returns the full lesson record (for client preview).
    """
    if not isinstance(entry, dict):
        raise ValueError("entry must be an object")

    with _FILE_LOCK:
        data = _load_progress()
        users = data.setdefault("users", {})
        user_block = users.setdefault(str(user_id), {})
        prog = user_block.get(module_id) or _empty_progress(module_id)
        fm = prog.setdefault("field_missions", {})
        record = fm.get(lesson_id) or {"entries": [], "submitted_at": None}
        entries = record.setdefault("entries", [])

        # entry_id is monotonic per-lesson
        next_idx = len(entries) + 1
        entry_id = f"{lesson_id}-e{next_idx}"
        clean = dict(entry)
        clean["entry_id"] = entry_id
        clean["created_at"] = _now_iso()
        entries.append(clean)

        fm[lesson_id] = record
        prog["last_active_at"] = _now_iso()
        user_block[module_id] = prog
        _save_progress(data)
        return record


def remove_field_mission_entry(
    user_id: str,
    module_id: str,
    lesson_id: str,
    entry_id: str,
) -> Dict[str, Any]:
    """Delete a single capture by entry_id. Returns the updated lesson record."""
    with _FILE_LOCK:
        data = _load_progress()
        user_block = data.get("users", {}).get(str(user_id), {})
        prog = user_block.get(module_id)
        if not prog:
            return {"entries": [], "submitted_at": None}
        record = prog.get("field_missions", {}).get(lesson_id)
        if not record:
            return {"entries": [], "submitted_at": None}
        record["entries"] = [
            e for e in record.get("entries", [])
            if e.get("entry_id") != entry_id
        ]
        prog["field_missions"][lesson_id] = record
        prog["last_active_at"] = _now_iso()
        _save_progress(data)
        return record


def get_field_mission_record(
    user_id: str,
    module_id: str,
    lesson_id: str,
) -> Dict[str, Any]:
    """Read the current capture set for a lesson (no mutation)."""
    data = _load_progress()
    user_block = data.get("users", {}).get(str(user_id), {})
    prog = user_block.get(module_id) or {}
    rec = (prog.get("field_missions") or {}).get(lesson_id) or {"entries": [], "submitted_at": None}
    return rec


def get_field_mission_entries_for_user(
    user_id: str,
    module_id: str,
) -> List[Dict[str, Any]]:
    """All field_mission entries across every lesson in a module — useful for
    pre-loading the Week 4 Complaint Detective game with the student's own
    captures as 'case files'.
    """
    data = _load_progress()
    user_block = data.get("users", {}).get(str(user_id), {})
    prog = user_block.get(module_id) or {}
    all_entries: List[Dict[str, Any]] = []
    for lesson_id, rec in (prog.get("field_missions") or {}).items():
        for e in rec.get("entries", []):
            row = dict(e)
            row["source_lesson_id"] = lesson_id
            all_entries.append(row)
    return all_entries


def compute_progress_summary(prog: Dict[str, Any], module: Dict[str, Any]) -> Dict[str, Any]:
    """Add %complete and current week/lesson display info.

    Optional lessons (lesson.optional == True) are excluded from the required
    count so they don't gate module completion, but they remain visible and
    completable for bonus XP.
    """
    flat = _flatten_lessons(module)
    total = len(flat) or 1
    required_lessons = [l for l in flat if not l.get("optional")]
    required_total = len(required_lessons) or 1
    completed_ids = set(prog.get("completed_lesson_ids", []))
    done = len(completed_ids)
    required_done = sum(1 for l in required_lessons if l.get("lesson_id") in completed_ids)
    # Percent reflects required progress (so bonus lessons don't dilute it).
    pct = round(100.0 * required_done / required_total)

    cur_week = None
    cur_lesson = None
    for w in module.get("weeks", []):
        if w.get("week_id") == prog.get("current_week_id"):
            cur_week = {"week_id": w.get("week_id"), "number": w.get("number"), "title": w.get("title")}
            for l in w.get("lessons", []):
                if l.get("lesson_id") == prog.get("current_lesson_id"):
                    cur_lesson = {"lesson_id": l.get("lesson_id"), "type": l.get("type"), "title": l.get("title")}
                    break
            break

    # Per-week / per-lesson unlock state for the UI.
    progression = (module.get("progression") or "linear").lower()
    quizzes = prog.get("quizzes") or {}
    week_states = []
    for w in module.get("weeks", []) or []:
        wid = w.get("week_id")
        unlocked = _is_week_unlocked(prog, module, wid)
        lessons_in_week = w.get("lessons", []) or []
        req_in_week = [l for l in lessons_in_week if not l.get("optional")]
        done_in_week = sum(1 for l in req_in_week if l.get("lesson_id") in completed_ids)
        # quiz lessons must also be passed for the week to be "complete"
        quiz_ok = all(
            (l.get("type") not in ("quiz", "assessment"))
            or (quizzes.get(l.get("lesson_id"), {}).get("passed", False))
            for l in req_in_week
        )
        wk_complete = bool(req_in_week) and done_in_week == len(req_in_week) and quiz_ok
        week_states.append({
            "week_id": wid,
            "number": w.get("number"),
            "title": w.get("title"),
            "unlocked": unlocked,
            "completed": wk_complete,
            "lessons_completed": done_in_week,
            "lessons_required": len(req_in_week),
        })

    return {
        "module_id": prog.get("module_id"),
        "completed": prog.get("completed_at") is not None,
        "started_at": prog.get("started_at"),
        "completed_at": prog.get("completed_at"),
        "last_active_at": prog.get("last_active_at"),
        "lessons_completed": done,
        "lessons_total": total,
        "required_completed": required_done,
        "required_total": required_total,
        "percent_complete": pct,
        "current_week": cur_week,
        "current_lesson": cur_lesson,
        "completed_lesson_ids": prog.get("completed_lesson_ids", []),
        "has_certificate": prog.get("completed_at") is not None,
        "progression": progression,
        "weeks": week_states,
    }


# ---------- Composite v2: 5-channel scoring (Task 13 — P0 plan) ----------

# Channel weights chosen to favor anchored game performance + quizzes (the two
# strongest signals of skill demonstration), with rubric and reflection as
# qualitative supports and time_on_task as a small floor of effort credit.
_COMPOSITE_V2_WEIGHTS: Dict[str, float] = {
    "quiz_avg": 0.25,
    "rubric_avg": 0.20,
    "reflection_depth": 0.15,
    "anchored_game_dim_avg": 0.30,
    "time_on_task": 0.10,
}


def _avg_quiz_score(prog: Dict[str, Any]) -> Optional[int]:
    """Mean of quiz `ratio` values (0-1) across attempted quizzes, scaled to 0-100."""
    quizzes = prog.get("quizzes") or {}
    ratios = []
    for q in quizzes.values():
        if not isinstance(q, dict):
            continue
        r = q.get("ratio")
        if r is None and q.get("max_score"):
            try:
                r = float(q.get("score") or 0) / float(q["max_score"])
            except (TypeError, ValueError, ZeroDivisionError):
                r = None
        if r is None:
            continue
        try:
            ratios.append(max(0.0, min(1.0, float(r))))
        except (TypeError, ValueError):
            continue
    if not ratios:
        return None
    return int(round(sum(ratios) / len(ratios) * 100))


def _avg_rubric_score(prog: Dict[str, Any]) -> Optional[int]:
    """Mean of LLM-graded rubric scores (0-100) attached to worksheets."""
    worksheets = prog.get("worksheets") or {}
    scores = []
    for w in worksheets.values():
        if not isinstance(w, dict):
            continue
        rubric = w.get("rubric") or {}
        s = rubric.get("score")
        if s is None:
            continue
        try:
            scores.append(max(0, min(100, int(s))))
        except (TypeError, ValueError):
            continue
    if not scores:
        return None
    return int(round(sum(scores) / len(scores)))


def _avg_reflection_depth(prog: Dict[str, Any]) -> Optional[int]:
    """Heuristic depth score 0-100 for reflection answers.

    Uses a length-based proxy clipped at 60 words = 100. Rationale: longer
    reflections strongly correlate with depth in our pilot data and don't
    require an extra LLM call. Replace with a graded `rubric.score` if the
    reflection-grader Task 11 result has been attached.
    """
    reflections = prog.get("reflections") or {}
    scores = []
    for r in reflections.values():
        if not isinstance(r, dict):
            continue
        # Prefer attached LLM grade if present
        rubric = r.get("rubric") or r.get("graded") or {}
        if isinstance(rubric, dict) and rubric.get("score") is not None:
            try:
                scores.append(max(0, min(100, int(rubric["score"]))))
                continue
            except (TypeError, ValueError):
                pass
        # Fallback: length proxy
        answers = r.get("answers") or {}
        if isinstance(answers, dict):
            text = " ".join(str(v) for v in answers.values() if v)
        else:
            text = str(answers or "")
        words = len(text.split())
        depth = max(0, min(100, int((words / 60.0) * 100)))
        scores.append(depth)
    if not scores:
        return None
    return int(round(sum(scores) / len(scores)))


def _avg_anchored_game_dim(prog: Dict[str, Any]) -> Optional[int]:
    """Mean of all anchored-game per-dim scores attached to lesson runs.

    Expects shape: prog['anchored_game_dim_avg'][lesson_id] = {dim: score, ...}
    where each score is 0-100.
    """
    anchor = prog.get("anchored_game_dim_avg") or {}
    flat = []
    for per_lesson in anchor.values():
        if not isinstance(per_lesson, dict):
            continue
        for v in per_lesson.values():
            try:
                flat.append(max(0, min(100, int(v))))
            except (TypeError, ValueError):
                continue
    if not flat:
        return None
    return int(round(sum(flat) / len(flat)))


def _normalize_time_on_task(prog: Dict[str, Any], module: Dict[str, Any]) -> Optional[int]:
    """Ratio of actual time-on-task vs expected, clipped to [0, 100].

    Expected time pulled from `module.expected_time_minutes`; falls back to
    20 min/lesson if not declared. Going OVER expected does not earn extra credit.
    """
    meta = prog.get("lesson_meta") or {}
    total_seconds = 0
    for v in meta.values():
        if isinstance(v, dict):
            try:
                total_seconds += int(v.get("time_spent_seconds") or 0)
            except (TypeError, ValueError):
                continue
    if total_seconds <= 0:
        return None
    expected_min = module.get("expected_time_minutes")
    if not expected_min:
        # 20 min per non-optional lesson default
        n_lessons = sum(
            1 for w in (module.get("weeks") or []) for l in (w.get("lessons") or [])
            if not l.get("optional")
        )
        expected_min = max(20, n_lessons * 20)
    ratio = total_seconds / max(1, expected_min * 60)
    return int(round(max(0.0, min(1.0, ratio)) * 100))


def _compute_dim_delta(prog: Dict[str, Any]) -> Dict[str, int]:
    """Return per-dimension delta = current - baseline.

    Reads `prog['dim_current']` and `prog['dim_baseline']`. Missing baseline for
    a dim defaults to 50 (population average). Missing current returns no entry.
    """
    baseline = prog.get("dim_baseline") or {}
    current = prog.get("dim_current") or {}
    out = {}
    for dim, cur in current.items():
        try:
            cur_v = max(0, min(100, int(cur)))
        except (TypeError, ValueError):
            continue
        try:
            base_v = max(0, min(100, int(baseline.get(dim, 50))))
        except (TypeError, ValueError):
            base_v = 50
        out[dim] = cur_v - base_v
    return out


def compute_module_composite_v2(
    prog: Dict[str, Any],
    module: Dict[str, Any],
) -> Dict[str, Any]:
    """5-channel composite: quiz_avg, rubric_avg, reflection_depth, anchored_game_dim_avg, time_on_task.

    Plus per-dimension delta from start of module to now. Channels with no
    data return None and are excluded from the weighted score (the weight is
    redistributed proportionally over present channels).
    """
    channels = {
        "quiz_avg": _avg_quiz_score(prog),
        "rubric_avg": _avg_rubric_score(prog),
        "reflection_depth": _avg_reflection_depth(prog),
        "anchored_game_dim_avg": _avg_anchored_game_dim(prog),
        "time_on_task": _normalize_time_on_task(prog, module),
    }
    weights = dict(_COMPOSITE_V2_WEIGHTS)

    # Renormalize weights over channels that have data so missing channels
    # don't artificially deflate the composite score.
    present = {k: v for k, v in channels.items() if v is not None}
    if present:
        total_w = sum(weights[k] for k in present)
        if total_w > 0:
            composite = sum(present[k] * (weights[k] / total_w) for k in present)
        else:
            composite = 0
    else:
        composite = 0

    return {
        "score": int(round(max(0, min(100, composite)))),
        "channels": channels,
        "weights": weights,
        "per_dim_delta": _compute_dim_delta(prog),
    }


# ---------- Cohort assignments (teacher-led, multi-user) ----------

def _load_cohort_assignments() -> Dict[str, Any]:
    return _safe_load_json(COHORT_ASSIGN_FILE, {"assignments": []})


def _save_cohort_assignments(data: Dict[str, Any]) -> None:
    _safe_write_json(COHORT_ASSIGN_FILE, data)


def assign_module_to_cohort(
    cohort_id: str,
    module_id: str,
    assigned_by: str,
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Assign a module to a whole cohort. Idempotent on (cohort_id, module_id)."""
    if not get_module(module_id):
        raise ValueError(f"Module not found: {module_id}")

    with _FILE_LOCK:
        data = _load_cohort_assignments()
        existing = next(
            (a for a in data["assignments"]
             if a.get("cohort_id") == cohort_id and a.get("module_id") == module_id),
            None,
        )
        if existing:
            existing["start_date"] = start_date or existing.get("start_date")
            existing["due_date"] = due_date or existing.get("due_date")
            existing["updated_at"] = _now_iso()
            _save_cohort_assignments(data)
            return existing

        record = {
            "cohort_id": cohort_id,
            "module_id": module_id,
            "assigned_by": assigned_by,
            "assigned_at": _now_iso(),
            "start_date": start_date,
            "due_date": due_date,
            "updated_at": _now_iso(),
        }
        data["assignments"].append(record)
        _save_cohort_assignments(data)
        return record


def unassign_module_from_cohort(cohort_id: str, module_id: str) -> bool:
    with _FILE_LOCK:
        data = _load_cohort_assignments()
        before = len(data["assignments"])
        data["assignments"] = [
            a for a in data["assignments"]
            if not (a.get("cohort_id") == cohort_id and a.get("module_id") == module_id)
        ]
        changed = len(data["assignments"]) != before
        if changed:
            _save_cohort_assignments(data)
        return changed


def list_cohort_assignments(cohort_id: str) -> List[Dict[str, Any]]:
    data = _load_cohort_assignments()
    return [a for a in data.get("assignments", []) if a.get("cohort_id") == cohort_id]


def list_user_cohort_modules(student_user_id: str, cohorts_for_user: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Given a student's cohorts (passed in by the caller — keeps this module
    decoupled from cohort storage), return the list of modules assigned via
    those cohorts. Each item: {module_id, cohort_id, cohort_name, due_date}.
    """
    data = _load_cohort_assignments()
    out: List[Dict[str, Any]] = []
    cohort_index = {str(c.get("id")): c for c in (cohorts_for_user or [])}
    for a in data.get("assignments", []):
        cid = str(a.get("cohort_id"))
        if cid in cohort_index:
            out.append({
                "module_id": a.get("module_id"),
                "cohort_id": cid,
                "cohort_name": cohort_index[cid].get("name"),
                "start_date": a.get("start_date"),
                "due_date": a.get("due_date"),
            })
    return out


def get_cohort_progress(cohort_id: str, module_id: str, student_user_ids: List[str]) -> Dict[str, Any]:
    """
    Aggregate cohort-level progress for a teacher view.
    Caller passes student user IDs (already resolved against cohort storage).
    Returns per-student rows + cohort-wide percentages.
    """
    module = get_module(module_id)
    if not module:
        raise ValueError(f"Module not found: {module_id}")

    flat = _flatten_lessons(module)
    total_lessons = len(flat) or 1

    progress_data = _load_progress()
    rows = []
    sum_pct = 0
    completed_count = 0
    for sid in student_user_ids:
        p = progress_data.get("users", {}).get(str(sid), {}).get(module_id)
        if not p:
            rows.append({
                "user_id": str(sid),
                "started": False,
                "completed": False,
                "lessons_completed": 0,
                "lessons_total": total_lessons,
                "percent_complete": 0,
                "current_lesson_id": None,
                "last_active_at": None,
            })
            continue
        done = len(p.get("completed_lesson_ids", []))
        pct = round(100.0 * done / total_lessons)
        sum_pct += pct
        if p.get("completed_at"):
            completed_count += 1
        rows.append({
            "user_id": str(sid),
            "started": True,
            "completed": p.get("completed_at") is not None,
            "lessons_completed": done,
            "lessons_total": total_lessons,
            "percent_complete": pct,
            "current_lesson_id": p.get("current_lesson_id"),
            "last_active_at": p.get("last_active_at"),
        })

    n = max(1, len(student_user_ids))
    return {
        "cohort_id": cohort_id,
        "module_id": module_id,
        "module_title": module.get("title"),
        "students_total": len(student_user_ids),
        "students_started": sum(1 for r in rows if r["started"]),
        "students_completed": completed_count,
        "average_percent": round(sum_pct / n) if rows else 0,
        "rows": rows,
    }
