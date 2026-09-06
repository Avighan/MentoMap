"""
Course Engine — teacher-authored courses (LMS): CRUD, cohort enrollment,
student progress tracking, gradebook, and certificate generation.

Persistence follows this codebase's standard pattern (see modules_engine.py,
storage.py): plain JSON files under `backend/data/` (or `MENTO_DATA_DIR` if
set), a threading.Lock around writes, and mtime-based in-memory caching.

Three files, three concerns:
  - courses.json:            {course_id: course}
  - course_enrollments.json: {"<course_id>::<student_id>": enrollment}
  - course_progress.json:    {"<course_id>::<student_id>": progress}
"""

import io
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("MENTO_DATA_DIR") or os.path.join(_THIS_DIR, "data")
COURSES_FILE = os.path.join(DATA_DIR, "courses.json")
ENROLLMENTS_FILE = os.path.join(DATA_DIR, "course_enrollments.json")
PROGRESS_FILE = os.path.join(DATA_DIR, "course_progress.json")

_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}
_CACHE_MTIME: Dict[str, float] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enrollment_key(course_id: str, student_id: str) -> str:
    return f"{course_id}::{student_id}"


# ---------- generic JSON store helpers (mirrors modules_engine.py) ----------

def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _load(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        mtime = os.path.getmtime(path)
        if path in _CACHE and _CACHE_MTIME.get(path) == mtime:
            return _CACHE[path]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CACHE[path] = data
        _CACHE_MTIME[path] = mtime
        return data
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read %s: %s. Using default.", path, e)
        return default


def _save(path: str, data: Any) -> None:
    _ensure_data_dir()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)
    _CACHE[path] = data
    _CACHE_MTIME[path] = os.path.getmtime(path)


def _load_courses() -> Dict[str, Any]:
    return _load(COURSES_FILE, {})


def _load_enrollments() -> Dict[str, Any]:
    return _load(ENROLLMENTS_FILE, {})


def _load_progress() -> Dict[str, Any]:
    return _load(PROGRESS_FILE, {})


# ---------- course structure helpers ----------

def _normalize_sections(sections: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    out = []
    for si, section in enumerate(sections or []):
        sec = dict(section)
        sec.setdefault("id", f"section-{si + 1}")
        items = []
        for ii, item in enumerate(sec.get("items") or []):
            it = dict(item)
            it.setdefault("id", f"{sec['id']}-item-{ii + 1}")
            it.setdefault("required", True)
            items.append(it)
        sec["items"] = items
        out.append(sec)
    return out


def _all_items(course: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [item for section in course.get("sections", []) for item in section.get("items", [])]


def _required_item_ids(course: Dict[str, Any]) -> List[str]:
    return [it["id"] for it in _all_items(course) if it.get("required", True)]


# ---------- Teacher: CRUD ----------

def create_course(teacher_id: str, org_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    course_id = uuid.uuid4().hex[:12]
    now = _now_iso()
    course = {
        "id": course_id,
        "teacher_id": teacher_id,
        "org_id": org_id,
        "title": data.get("title", "Untitled Course"),
        "subject": data.get("subject", ""),
        "grade_level": data.get("grade_level", ""),
        "description": data.get("description", ""),
        "thumbnail_emoji": data.get("thumbnail_emoji", "📚"),
        "learning_outcomes": data.get("learning_outcomes", []) or [],
        "pass_threshold": data.get("pass_threshold", 60),
        "sections": _normalize_sections(data.get("sections")),
        "curriculum_template_id": data.get("curriculum_template_id"),
        "published": False,
        "published_at": None,
        "created_at": now,
        "updated_at": now,
    }
    with _LOCK:
        courses = _load_courses()
        courses[course_id] = course
        _save(COURSES_FILE, courses)
    return course


def list_courses_by_teacher(teacher_id: str) -> List[Dict[str, Any]]:
    courses = _load_courses()
    out = [c for c in courses.values() if c.get("teacher_id") == teacher_id]
    out.sort(key=lambda c: c.get("created_at", ""), reverse=True)
    return out


def get_course(course_id: str) -> Optional[Dict[str, Any]]:
    return _load_courses().get(course_id)


_UPDATABLE_FIELDS = (
    "title", "subject", "grade_level", "description", "thumbnail_emoji",
    "learning_outcomes", "pass_threshold", "sections",
)


def update_course(course_id: str, teacher_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with _LOCK:
        courses = _load_courses()
        course = courses.get(course_id)
        if not course or course.get("teacher_id") != teacher_id:
            return None
        for field in _UPDATABLE_FIELDS:
            if field in data:
                course[field] = _normalize_sections(data[field]) if field == "sections" else data[field]
        course["updated_at"] = _now_iso()
        courses[course_id] = course
        _save(COURSES_FILE, courses)
        return course


def delete_course(course_id: str, teacher_id: str) -> bool:
    with _LOCK:
        courses = _load_courses()
        course = courses.get(course_id)
        if not course or course.get("teacher_id") != teacher_id:
            return False
        del courses[course_id]
        _save(COURSES_FILE, courses)

        enrollments = _load_enrollments()
        progress = _load_progress()
        prefix = f"{course_id}::"
        changed_e = changed_p = False
        for key in [k for k in enrollments if k.startswith(prefix)]:
            del enrollments[key]
            changed_e = True
        for key in [k for k in progress if k.startswith(prefix)]:
            del progress[key]
            changed_p = True
        if changed_e:
            _save(ENROLLMENTS_FILE, enrollments)
        if changed_p:
            _save(PROGRESS_FILE, progress)
        return True


def publish_course(course_id: str, teacher_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        courses = _load_courses()
        course = courses.get(course_id)
        if not course or course.get("teacher_id") != teacher_id:
            return None
        course["published"] = True
        course["published_at"] = _now_iso()
        course["updated_at"] = _now_iso()
        courses[course_id] = course
        _save(COURSES_FILE, courses)
        return course


# ---------- Teacher: enrollment ----------

def enroll_cohort(course_id: str, student_ids: List[str], enrolled_by: str) -> Dict[str, Any]:
    now = _now_iso()
    newly_enrolled: List[str] = []
    already_enrolled: List[str] = []
    with _LOCK:
        enrollments = _load_enrollments()
        for sid in student_ids:
            sid = str(sid)
            key = _enrollment_key(course_id, sid)
            if key in enrollments:
                already_enrolled.append(sid)
                continue
            enrollments[key] = {
                "course_id": course_id,
                "student_id": sid,
                "enrolled_by": enrolled_by,
                "enrolled_at": now,
                "completed": False,
                "completed_at": None,
                "percent_complete": 0,
                "final_grade": None,
                "feedback": None,
            }
            newly_enrolled.append(sid)
        _save(ENROLLMENTS_FILE, enrollments)
    return {
        "course_id": course_id,
        "enrolled": newly_enrolled,
        "already_enrolled": already_enrolled,
        "total_enrolled": len(newly_enrolled) + len(already_enrolled),
    }


def unenroll_student(course_id: str, student_id: str) -> bool:
    key = _enrollment_key(course_id, str(student_id))
    with _LOCK:
        enrollments = _load_enrollments()
        progress = _load_progress()
        found = key in enrollments
        if found:
            del enrollments[key]
            _save(ENROLLMENTS_FILE, enrollments)
        if key in progress:
            del progress[key]
            _save(PROGRESS_FILE, progress)
        return found


def list_course_enrollments(course_id: str) -> List[Dict[str, Any]]:
    enrollments = _load_enrollments()
    prefix = f"{course_id}::"
    out = [e for k, e in enrollments.items() if k.startswith(prefix)]
    out.sort(key=lambda e: e.get("enrolled_at", ""))
    return out


# ---------- Teacher: gradebook ----------

def get_course_gradebook(course_id: str) -> Dict[str, Any]:
    course = get_course(course_id) or {}
    required_ids = _required_item_ids(course)
    total_required = len(required_ids) or 1
    progress_store = _load_progress()

    rows = []
    for enr in list_course_enrollments(course_id):
        sid = enr["student_id"]
        prog = progress_store.get(_enrollment_key(course_id, sid), {})
        completions = prog.get("item_completions", {})
        completed_count = sum(1 for iid in required_ids if completions.get(iid, {}).get("completed"))
        rows.append({
            "student_id": sid,
            "enrolled_at": enr.get("enrolled_at"),
            "items_completed": completed_count,
            "items_total": total_required,
            "percent_complete": round(100 * completed_count / total_required),
            "completed": enr.get("completed", False),
            "completed_at": enr.get("completed_at"),
            "final_grade": enr.get("final_grade"),
            "feedback": enr.get("feedback"),
        })

    return {
        "course_id": course_id,
        "course_title": course.get("title", ""),
        "pass_threshold": course.get("pass_threshold", 60),
        "rows": rows,
    }


def set_final_grade(course_id: str, student_id: str, grade: str, feedback: str = "") -> bool:
    key = _enrollment_key(course_id, str(student_id))
    with _LOCK:
        enrollments = _load_enrollments()
        enr = enrollments.get(key)
        if not enr:
            return False
        enr["final_grade"] = grade
        enr["feedback"] = feedback
        enr["graded_at"] = _now_iso()
        enrollments[key] = enr
        _save(ENROLLMENTS_FILE, enrollments)
        return True


# ---------- Student: enrollment & progress ----------

def get_enrollment(course_id: str, student_id: str) -> Optional[Dict[str, Any]]:
    return _load_enrollments().get(_enrollment_key(course_id, str(student_id)))


def list_student_enrollments(student_id: str) -> List[Dict[str, Any]]:
    enrollments = _load_enrollments()
    courses = _load_courses()
    suffix = f"::{student_id}"
    out = []
    for key, enr in enrollments.items():
        if not key.endswith(suffix):
            continue
        course = courses.get(enr["course_id"])
        if not course:
            continue
        merged = dict(enr)
        merged.update({
            "title": course.get("title"),
            "subject": course.get("subject"),
            "grade_level": course.get("grade_level"),
            "thumbnail_emoji": course.get("thumbnail_emoji"),
            "description": course.get("description"),
        })
        out.append(merged)
    out.sort(key=lambda e: e.get("enrolled_at", ""), reverse=True)
    return out


def get_student_progress(course_id: str, student_id: str) -> Dict[str, Any]:
    course = get_course(course_id) or {}
    required_ids = _required_item_ids(course)
    total_required = len(required_ids) or 1
    key = _enrollment_key(course_id, str(student_id))
    prog = _load_progress().get(key) or {"course_id": course_id, "student_id": str(student_id), "item_completions": {}}
    completions = prog.get("item_completions", {})
    completed_count = sum(1 for iid in required_ids if completions.get(iid, {}).get("completed"))
    return {
        "course_id": course_id,
        "student_id": str(student_id),
        "item_completions": completions,
        "items_completed": completed_count,
        "items_total": total_required,
        "percent_complete": round(100 * completed_count / total_required),
    }


def mark_item_complete(
    course_id: str,
    student_id: str,
    item_id: str,
    score: Optional[float] = None,
    game_run_id: Optional[str] = None,
    quiz_answers: Optional[Any] = None,
) -> Dict[str, Any]:
    student_id = str(student_id)
    key = _enrollment_key(course_id, student_id)
    with _LOCK:
        progress_store = _load_progress()
        prog = progress_store.get(key) or {"course_id": course_id, "student_id": student_id, "item_completions": {}}
        prog["item_completions"][item_id] = {
            "completed": True,
            "score": score,
            "game_run_id": game_run_id,
            "quiz_answers": quiz_answers,
            "completed_at": _now_iso(),
        }
        progress_store[key] = prog
        _save(PROGRESS_FILE, progress_store)

        course = get_course(course_id) or {}
        required_ids = _required_item_ids(course)
        total_required = len(required_ids) or 1
        completions = prog["item_completions"]
        completed_count = sum(1 for iid in required_ids if completions.get(iid, {}).get("completed"))
        percent_complete = round(100 * completed_count / total_required)
        all_done = bool(required_ids) and completed_count >= total_required

        enrollments = _load_enrollments()
        enr = enrollments.get(key)
        if enr is not None:
            enr["percent_complete"] = percent_complete
            if all_done and not enr.get("completed"):
                enr["completed"] = True
                enr["completed_at"] = _now_iso()
            enrollments[key] = enr
            _save(ENROLLMENTS_FILE, enrollments)

    return {
        "course_id": course_id,
        "student_id": student_id,
        "item_completions": completions,
        "items_completed": completed_count,
        "items_total": total_required,
        "percent_complete": percent_complete,
        "completed": all_done,
    }


# ---------- Certificates ----------
# Hand-rolled minimal single-page PDF (stdlib only — no reportlab dependency
# here, unlike certificate.py's game-run certificates).

def _pdf_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _build_minimal_pdf(lines: List[Any]) -> bytes:
    """`lines`: list of (text, font_size, y) tuples, drawn on one A4-ish page."""
    content_ops = ["BT", "/F1 24 Tf"]
    stream_parts = []
    for text, size, y in lines:
        stream_parts.append(f"BT /F1 {size} Tf 60 {y} Td ({_pdf_escape(text)}) Tj ET")
    stream = "\n".join(stream_parts).encode("latin-1", errors="replace")

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                    b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{i} 0 obj\n".encode("latin-1"))
        buf.write(obj)
        buf.write(b"\nendobj\n")
    xref_start = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode("latin-1"))
    buf.write(b"trailer\n")
    buf.write(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("latin-1"))
    buf.write(b"startxref\n")
    buf.write(f"{xref_start}\n".encode("latin-1"))
    buf.write(b"%%EOF")
    return buf.getvalue()


def generate_certificate_pdf(course_id: str, student_id: str, student_name: str, org_name: str) -> bytes:
    course = get_course(course_id)
    if not course:
        raise ValueError(f"Course not found: {course_id}")
    enr = get_enrollment(course_id, student_id) or {}
    completed_at = enr.get("completed_at") or _now_iso()
    try:
        date_str = datetime.fromisoformat(completed_at.replace("Z", "+00:00")).strftime("%B %d, %Y")
    except ValueError:
        date_str = completed_at

    lines = [
        (org_name, 16, 760),
        ("Certificate of Completion", 26, 690),
        ("This certifies that", 14, 630),
        (student_name, 22, 590),
        ("has successfully completed the course", 14, 550),
        (course.get("title", "Untitled Course"), 20, 510),
        (f"Completed on {date_str}", 12, 460),
        (f"Certificate ID: {course_id}-{student_id}"[:80], 9, 420),
    ]
    return _build_minimal_pdf(lines)
