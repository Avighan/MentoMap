"""Interview Sim routes.

GET   /api/modules/<module_id>/lessons/<lesson_id>/interview-sim/personas
POST  /api/modules/<module_id>/lessons/<lesson_id>/interview-sim/start
POST  /api/modules/<module_id>/lessons/<lesson_id>/interview-sim/turn
POST  /api/modules/<module_id>/lessons/<lesson_id>/interview-sim/end
GET   /static/audio/interview_sim_replies/<filename>

Caps (per module, per user):
  - 3 personas (start)
  - 15 turns (turn)
"""
from pathlib import Path
import re
import uuid

from flask import Blueprint, jsonify, request, send_from_directory

from services.interview_sim import (
    start_conversation,
    take_turn,
    end_conversation,
    _load,
)
from services.pitch_coach import transcribe  # reuse Whisper wrapper
from services.conversation_persona_engine import list_personas
from modules_engine import check_and_increment_usage, UsageLimitExceeded
from auth import require_auth

bp = Blueprint("module_interview_sim", __name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPLY_DIR = _BACKEND_ROOT / "assets" / "audio" / "interview_sim_replies"
REPLY_DIR.mkdir(parents=True, exist_ok=True)

# Only allow simple uuid-hex .mp3 names we wrote ourselves.
_REPLY_FILENAME_RE = re.compile(r"^[a-f0-9]{32}\.mp3$")

_MIN_AUDIO_BYTES = 1000  # ~0.5s of compressed audio


@bp.get("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/personas")
def personas(module_id, lesson_id):
    items = [
        {"persona_id": p["persona_id"], "display_name": p.get("display_name", p["persona_id"])}
        for p in list_personas("entrepreneur")
    ]
    return jsonify({"personas": items})


@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/start")
@require_auth
def start(module_id, lesson_id):
    user_id = request.current_user.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    try:
        check_and_increment_usage(user_id, module_id, "interview_sim_personas", limit=3)
    except UsageLimitExceeded:
        return jsonify({
            "error": "cap_reached",
            "message": "You've used all 3 personas for this module.",
        }), 429
    body = request.get_json(silent=True) or {}
    persona_id = body.get("persona_id")
    if not persona_id:
        return jsonify({"error": "missing_persona_id"}), 400
    try:
        state = start_conversation(user_id, module_id, persona_id)
    except FileNotFoundError:
        return jsonify({"error": "unknown_persona", "persona_id": persona_id}), 404
    return jsonify({
        "conv_id": state.conv_id,
        "persona": {
            "persona_id": state.persona["persona_id"],
            "display_name": state.persona.get("display_name"),
        },
    })


@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/turn")
@require_auth
def turn(module_id, lesson_id):
    user_id = request.current_user.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401
    try:
        check_and_increment_usage(user_id, module_id, "interview_sim_turns", limit=15)
    except UsageLimitExceeded:
        return jsonify({
            "error": "cap_reached",
            "message": "You've used all 15 turns for this module.",
        }), 429
    conv_id = request.form.get("conv_id")
    if not conv_id or "audio" not in request.files:
        return jsonify({"error": "missing_args"}), 400
    upload = request.files["audio"]
    blob = upload.read()
    if len(blob) < _MIN_AUDIO_BYTES:
        return jsonify({"error": "audio_too_short"}), 400
    try:
        user_text = transcribe(blob, filename=upload.filename or "turn.webm")
    except Exception as exc:
        return jsonify({"error": "stt_failed", "detail": str(exc)}), 502
    try:
        state, reply_text, reply_audio = take_turn(conv_id, user_text)
    except FileNotFoundError:
        return jsonify({"error": "unknown_conv"}), 404
    except Exception as exc:
        return jsonify({"error": "turn_failed", "detail": str(exc)}), 502

    reply_id = f"{uuid.uuid4().hex}.mp3"
    reply_path = REPLY_DIR / reply_id
    tmp = reply_path.with_suffix(".tmp")
    tmp.write_bytes(reply_audio)
    tmp.replace(reply_path)

    user_turn_count = sum(1 for t in state.turns if t.get("role") == "user")
    return jsonify({
        "user_text": user_text,
        "persona_text": reply_text,
        "persona_audio_url": f"/static/audio/interview_sim_replies/{reply_id}",
        "turn_count": user_turn_count,
    })


@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/interview-sim/end")
@require_auth
def end(module_id, lesson_id):
    body = request.get_json(silent=True) or {}
    conv_id = body.get("conv_id")
    if not conv_id:
        return jsonify({"error": "missing_conv_id"}), 400
    try:
        state = _load(conv_id)
    except FileNotFoundError:
        return jsonify({"error": "unknown_conv"}), 404
    return jsonify(end_conversation(state))


@bp.get("/static/audio/interview_sim_replies/<filename>")
def serve_reply(filename):
    if not _REPLY_FILENAME_RE.match(filename):
        return jsonify({"error": "invalid_filename"}), 400
    return send_from_directory(REPLY_DIR, filename, mimetype="audio/mpeg")
