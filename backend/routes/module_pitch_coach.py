"""Pitch Coach route.

POST /api/modules/<module_id>/lessons/<lesson_id>/pitch-coach
  Multipart upload: field name "audio" (webm/mp3/wav).
  Auth required (@require_auth).
  Usage capped: 3 runs per user/module via modules_engine.check_and_increment_usage.

GET /static/audio/pitch_coach_replies/<filename>
  Serves the synthesized coaching reply mp3 from disk.
"""
from pathlib import Path
import re
import uuid

from flask import Blueprint, jsonify, request, send_from_directory

from services.pitch_coach import transcribe, score_transcript, voice_reply_for
from modules_engine import check_and_increment_usage, UsageLimitExceeded
from auth import require_auth

bp = Blueprint("module_pitch_coach", __name__)

# Absolute, CWD-independent path under backend/
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPLY_DIR = _BACKEND_ROOT / "assets" / "audio" / "pitch_coach_replies"
REPLY_DIR.mkdir(parents=True, exist_ok=True)

# Path-traversal guard: only allow simple hex-named mp3s we wrote ourselves.
_REPLY_FILENAME_RE = re.compile(r"^[a-f0-9]{32}\.mp3$")

_MIN_AUDIO_BYTES = 1000  # ~ <0.5s of compressed audio — clearly empty


@bp.post("/api/modules/<module_id>/lessons/<lesson_id>/pitch-coach")
@require_auth
def pitch_coach(module_id, lesson_id):
    user = request.current_user
    user_id = user.get("user_id")
    if not user_id:
        return jsonify({"error": "auth_required"}), 401

    try:
        check_and_increment_usage(user_id, module_id, "pitch_coach_runs", limit=3)
    except UsageLimitExceeded:
        return jsonify({
            "error": "cap_reached",
            "message": "You've used all 3 pitch-coach runs for this module.",
        }), 429

    if "audio" not in request.files:
        return jsonify({"error": "missing_audio"}), 400

    upload = request.files["audio"]
    blob = upload.read()
    if len(blob) < _MIN_AUDIO_BYTES:
        return jsonify({"error": "audio_too_short"}), 400

    try:
        transcript = transcribe(blob, filename=upload.filename or "pitch.webm")
    except Exception as exc:
        return jsonify({"error": "stt_failed", "detail": str(exc)}), 502

    try:
        score = score_transcript(transcript)
    except Exception as exc:
        return jsonify({"error": "scoring_failed", "detail": str(exc)}), 502

    try:
        reply_mp3 = voice_reply_for(score)
    except Exception as exc:
        return jsonify({"error": "tts_failed", "detail": str(exc)}), 502

    reply_id = f"{uuid.uuid4().hex}.mp3"
    reply_path = REPLY_DIR / reply_id
    tmp = reply_path.with_suffix(".tmp")
    tmp.write_bytes(reply_mp3)
    tmp.replace(reply_path)  # atomic on POSIX
    reply_url = f"/static/audio/pitch_coach_replies/{reply_id}"

    return jsonify({
        "transcript": transcript,
        "scores": score.scores,
        "strengths": score.strengths,
        "improvements": score.improvements,
        "summary": score.summary,
        "voice_reply_url": reply_url,
    })


@bp.get("/static/audio/pitch_coach_replies/<filename>")
def serve_reply(filename):
    # Reject anything that isn't a normal uuid-hex mp3 we'd have written.
    if not _REPLY_FILENAME_RE.match(filename):
        return jsonify({"error": "invalid_filename"}), 400
    return send_from_directory(REPLY_DIR, filename, mimetype="audio/mpeg")
