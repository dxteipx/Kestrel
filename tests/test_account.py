import time

import pytest

from kestrel.core import account, vault


def test_vault_round_trip_and_hides_the_secret():
    secret = b'{"refresh_token": "rt-123"}'
    sealed = vault.protect(secret)
    assert b"rt-123" not in sealed
    assert vault.unprotect(sealed) == secret


@pytest.mark.parametrize("payload, expected", [
    ({"error": "invalid_grant", "error_description": "Invalid login credentials"}, "Wrong email or password."),
    ({"code": 422, "msg": "User already registered"}, "already an account"),
    ({"error_code": "email_not_confirmed", "msg": "Email not confirmed"}, "Confirm your email"),
    ({"message": "Password should be at least 6 characters."}, "at least 6 characters"),
])
def test_friendly_errors(payload, expected):
    assert expected in account.friendly_error(payload, 400)


def test_unknown_errors_are_passed_through_or_generic():
    assert account.friendly_error({"msg": "something odd happened"}) == "Something odd happened"
    assert "server is having trouble" in account.friendly_error({}, 503)
    assert account.friendly_error({}) == "Something went wrong. Try again."


@pytest.mark.parametrize("email, password", [("not-an-email", "secret123"), ("a@b.co", "123")])
def test_validate_rejects_bad_input(email, password):
    with pytest.raises(account.AuthError):
        account.validate(email, password)


def test_session_from_supabase_response():
    session = account._session({"access_token": "at", "refresh_token": "rt", "expires_in": 3600,
                                "user": {"id": "u1", "email": "alex@example.com"}})
    assert session.email == "alex@example.com"
    assert not session.expired
    assert account.Session("a", "r", time.time() - 10, "u", "e").expired


def test_session_storage_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(account, "SESSION_FILE", tmp_path / "session.bin")
    monkeypatch.setattr(account, "CONFIG_DIR", tmp_path)
    session = account.Session("at", "rt", time.time() + 100, "u1", "alex@example.com")
    account.save(session)
    assert b"alex@example.com" not in (tmp_path / "session.bin").read_bytes()
    assert account.load() == session
    account.clear()
    assert account.load() is None
