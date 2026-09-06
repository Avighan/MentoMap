"""Real unit tests for backend/auth.py, restored on this branch."""
import pytest


@pytest.fixture
def auth_mod(monkeypatch, tmp_path):
    # auth.py's user/blacklist paths are recomputed on every call via
    # _data_dir() (see idea_journal.py's identical convention elsewhere in
    # this codebase), so monkeypatching MENTO_DATA_DIR for the life of the
    # test is enough — no reload() needed, and none wanted: reloading would
    # mutate the one shared `auth` module object every other test file's
    # `import auth`/`from auth import JWT_SECRET` also sees for the rest of
    # the pytest session, not just this test.
    monkeypatch.setenv("MENTO_DATA_DIR", str(tmp_path))
    import auth
    yield auth


def test_register_then_authenticate(auth_mod):
    user, token = auth_mod.register_user("alice", "correcthorse", "student", "default")
    assert user["username"] == "alice"
    assert user["role"] == "student"
    assert token

    ok_user, ok_token = auth_mod.authenticate_user("alice", "correcthorse")
    assert ok_user["id"] == user["id"]
    assert ok_token


def test_authenticate_rejects_wrong_password(auth_mod):
    auth_mod.register_user("bob", "correcthorse", "student", "default")
    user, err = auth_mod.authenticate_user("bob", "wrong-password")
    assert user is None
    assert "Invalid" in err


def test_duplicate_username_rejected(auth_mod):
    auth_mod.register_user("carol", "correcthorse")
    user, err = auth_mod.register_user("carol", "anotherpassword")
    assert user is None
    assert "already exists" in err


def test_passwords_are_hashed_not_plaintext(auth_mod):
    auth_mod.register_user("dave", "correcthorse")
    users = auth_mod._load_users()
    record = users["dave"]
    assert record["password_hash"] != "correcthorse"
    assert record["password_hash"].startswith("$2b$")  # bcrypt hash prefix


def test_verify_token_roundtrip_and_tamper(auth_mod):
    _, token = auth_mod.register_user("erin", "correcthorse")
    payload = auth_mod.verify_token(token)
    assert payload["username"] == "erin"

    assert auth_mod.verify_token(token + "tampered") is None
    assert auth_mod.verify_token(None) is None


def test_blacklisted_token_no_longer_verifies(auth_mod):
    _, token = auth_mod.register_user("frank", "correcthorse")
    assert auth_mod.verify_token(token) is not None
    auth_mod.blacklist_token(token)
    assert auth_mod.verify_token(token) is None


def test_change_password_requires_correct_old_password(auth_mod):
    auth_mod.register_user("grace", "correcthorse")
    ok, err = auth_mod.change_password("grace", "wrong-old", "newpassword123")
    assert ok is False

    ok, err = auth_mod.change_password("grace", "correcthorse", "newpassword123")
    assert ok is True
    user, _ = auth_mod.authenticate_user("grace", "newpassword123")
    assert user is not None


def test_reset_otp_flow(auth_mod):
    auth_mod.register_user("heidi", "correcthorse")
    otp, err = auth_mod.generate_reset_otp("heidi")
    assert otp and len(otp) == 6

    ok, err = auth_mod.reset_password_with_otp("heidi", "000000", "brandnewpass1")
    assert ok is False  # wrong OTP

    ok, err = auth_mod.reset_password_with_otp("heidi", otp, "brandnewpass1")
    assert ok is True
    user, _ = auth_mod.authenticate_user("heidi", "brandnewpass1")
    assert user is not None


def test_get_user_by_username_matches_id_or_username(auth_mod):
    user, _ = auth_mod.register_user("ivan", "correcthorse")
    by_username = auth_mod.get_user_by_username("ivan")
    by_id = auth_mod.get_user_by_username(user["id"])
    assert by_username["id"] == user["id"]
    assert by_id["id"] == user["id"]
    assert auth_mod.get_user_by_username("nobody") is None
