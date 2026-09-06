"""Authentication: JWT session tokens (PyJWT) + bcrypt password hashing.

Users are stored as JSON at `data/users.json` (same persistence style as
the rest of the backend — see `modules_engine.py`). Passwords are never
stored or logged in plaintext; only bcrypt hashes are persisted.

`JWT_SECRET_KEY` (falling back to `SECRET_KEY`) is read from the
environment, matching the convention already documented in
`docs/RUNNING_LOCALLY.md`. If neither is set, a random secret is
generated for this process only — tokens won't survive a restart, but the
app still boots and no hardcoded secret ever ships in source.
"""
import json
import logging
import os
import secrets
import threading
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt
from flask import jsonify, request

logger = logging.getLogger(__name__)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _data_dir() -> str:
    base = os.environ.get("MENTO_DATA_DIR") or os.path.join(_THIS_DIR, "data")
    os.makedirs(base, exist_ok=True)
    return base


def _users_path() -> str:
    return os.path.join(_data_dir(), "users.json")


def _blacklist_path() -> str:
    return os.path.join(_data_dir(), "token_blacklist.json")


_LOCK = threading.Lock()

_JWT_SECRET_ENV = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
if not _JWT_SECRET_ENV:
    logger.warning(
        "JWT_SECRET_KEY / SECRET_KEY not set — using a random per-process secret. "
        "Tokens will not remain valid across restarts. Set JWT_SECRET_KEY for "
        "production."
    )
    _JWT_SECRET_ENV = secrets.token_hex(32)
elif _JWT_SECRET_ENV in ("dev-secret", "dev-secret-change-me", "dev-secret-key-for-testing"):
    logger.warning("Using a default/example JWT secret — do not use this value in production!")

JWT_SECRET = _JWT_SECRET_ENV
JWT_ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = int(os.environ.get("JWT_TOKEN_TTL_SECONDS", str(24 * 3600)))
OTP_TTL_SECONDS = 900
VALID_ROLES = ("student", "teacher", "parent", "trainer", "hr", "admin", "school_admin", "dev")


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------

def _load_users() -> Dict[str, dict]:
    path = _users_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: Dict[str, dict]) -> None:
    path = _users_path()
    tmp_path = path + ".tmp"
    with _LOCK:
        with open(tmp_path, "w") as f:
            json.dump(users, f, indent=2)
        os.replace(tmp_path, path)


def _load_blacklist() -> list:
    path = _blacklist_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_blacklist(tokens: list) -> None:
    path = _blacklist_path()
    tmp_path = path + ".tmp"
    with _LOCK:
        with open(tmp_path, "w") as f:
            json.dump(tokens, f)
        os.replace(tmp_path, path)


def _public_user(record: dict) -> dict:
    return {
        "id": record["id"],
        "username": record["username"],
        "role": record["role"],
        "org_id": record.get("org_id", "default"),
    }


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _check_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def generate_token(user_id: str, username: str, role: str, org_id: str = "default") -> str:
    now = datetime.utcnow()
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "org_id": org_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=TOKEN_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    if token in _load_blacklist():
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    return payload


def get_token_from_request() -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):].strip()
    return request.args.get("token")


def blacklist_token(token: str) -> None:
    if not token:
        return
    tokens = _load_blacklist()
    # Opportunistically drop entries that have already expired so the file
    # doesn't grow without bound.
    still_valid = []
    for t in tokens:
        try:
            jwt.decode(t, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            still_valid.append(t)
        except jwt.ExpiredSignatureError:
            continue
        except jwt.InvalidTokenError:
            continue
    if token not in still_valid:
        still_valid.append(token)
    _save_blacklist(still_valid)


# ---------------------------------------------------------------------------
# Registration / authentication
# ---------------------------------------------------------------------------

def register_user(username: str, password: str, role: str = "student",
                   org_id: str = "default") -> Tuple[Optional[dict], str]:
    username = (username or "").strip()
    if not username or not password:
        return None, "Username and password required"
    if len(password) < 6:
        return None, "Password must be at least 6 characters"
    if role not in VALID_ROLES:
        role = "student"

    users = _load_users()
    if username.lower() in users:
        return None, "Username already exists"

    user_id = uuid.uuid4().hex
    record = {
        "id": user_id,
        "username": username,
        "password_hash": _hash_password(password),
        "role": role,
        "org_id": org_id or "default",
        "created_at": datetime.now().isoformat(),
    }
    users[username.lower()] = record
    _save_users(users)

    token = generate_token(user_id, username, role, record["org_id"])
    return _public_user(record), token


def authenticate_user(username: str, password: str) -> Tuple[Optional[dict], str]:
    username = (username or "").strip()
    users = _load_users()
    record = users.get(username.lower())
    if not record or not _check_password(password, record.get("password_hash", "")):
        return None, "Invalid username or password"

    token = generate_token(record["id"], record["username"], record["role"], record.get("org_id", "default"))
    return _public_user(record), token


def change_password(username: str, old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
    if not new_password or len(new_password) < 6:
        return False, "New password must be at least 6 characters"
    users = _load_users()
    record = users.get((username or "").strip().lower())
    if not record or not _check_password(old_password, record.get("password_hash", "")):
        return False, "Old password is incorrect"
    record["password_hash"] = _hash_password(new_password)
    users[username.strip().lower()] = record
    _save_users(users)
    return True, None


def generate_reset_otp(username: str) -> Tuple[Optional[str], Optional[str]]:
    users = _load_users()
    key = (username or "").strip().lower()
    record = users.get(key)
    if not record:
        return None, "User not found"
    otp = f"{secrets.randbelow(1_000_000):06d}"
    record["reset_otp"] = otp
    record["reset_otp_expires"] = (datetime.now() + timedelta(seconds=OTP_TTL_SECONDS)).isoformat()
    users[key] = record
    _save_users(users)
    return otp, None


def reset_password_with_otp(username: str, otp: str, new_password: str) -> Tuple[bool, Optional[str]]:
    if not new_password or len(new_password) < 6:
        return False, "New password must be at least 6 characters"
    users = _load_users()
    key = (username or "").strip().lower()
    record = users.get(key)
    if not record or not record.get("reset_otp"):
        return False, "Invalid or expired code"
    if record["reset_otp"] != (otp or "").strip():
        return False, "Invalid or expired code"
    try:
        expires = datetime.fromisoformat(record.get("reset_otp_expires", ""))
    except ValueError:
        return False, "Invalid or expired code"
    if datetime.now() > expires:
        return False, "Invalid or expired code"

    record["password_hash"] = _hash_password(new_password)
    record.pop("reset_otp", None)
    record.pop("reset_otp_expires", None)
    users[key] = record
    _save_users(users)
    return True, None


# ---------------------------------------------------------------------------
# Route decorators
# ---------------------------------------------------------------------------

def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = get_token_from_request()
        user = verify_token(token) if token else None
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return wrapper


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = get_token_from_request()
        user = verify_token(token) if token else None
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
        if user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        request.current_user = user
        return f(*args, **kwargs)
    return wrapper


def require_admin_or_school_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = get_token_from_request()
        user = verify_token(token) if token else None
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 401
        if user.get("role") not in ("admin", "school_admin"):
            return jsonify({"error": "Admin access required"}), 403
        request.current_user = user
        return f(*args, **kwargs)
    return wrapper
