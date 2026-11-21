"""Accounts through Supabase Auth, using its REST API directly (no extra dependencies).

The session (access + refresh token) is stored encrypted with DPAPI in
%APPDATA%\\Kestrel\\session.bin, so other Windows users can't read it.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

from kestrel import __version__, cloud
from kestrel.config import CONFIG_DIR
from kestrel.core import vault

SESSION_FILE = CONFIG_DIR / "session.bin"
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 6


class AuthError(Exception):
    """A message that's safe to show to the user as-is."""


@dataclass(frozen=True)
class Session:
    access_token: str
    refresh_token: str
    expires_at: float
    user_id: str
    email: str

    @property
    def expired(self) -> bool:
        return time.time() > self.expires_at - 60


def configured() -> bool:
    return bool(cloud.SUPABASE_URL and cloud.SUPABASE_ANON_KEY)


# --- Errors -------------------------------------------------------------------

_FRIENDLY = (
    ("invalid login credentials", "Wrong email or password."),
    ("email not confirmed", "Confirm your email first — check your inbox for the link."),
    ("user already registered", "There's already an account with this email. Try signing in."),
    ("already been registered", "There's already an account with this email. Try signing in."),
    ("password should be at least", f"Use a password with at least {MIN_PASSWORD} characters."),
    ("weak password", "That password is too easy to guess. Try a longer one."),
    ("rate limit", "Too many attempts. Wait a minute and try again."),
    ("invalid refresh token", "Your session expired. Sign in again."),
    ("refresh token not found", "Your session expired. Sign in again."),
    ("signups not allowed", "New accounts are turned off right now."),
)


def friendly_error(payload: dict | None, status: int = 0) -> str:
    payload = payload or {}
    raw = str(payload.get("error_description") or payload.get("msg") or payload.get("message")
              or payload.get("error") or "")
    lowered = raw.lower()
    for needle, message in _FRIENDLY:
        if needle in lowered:
            return message
    if status >= 500:
        return "The account server is having trouble. Try again in a moment."
    return raw[:1].upper() + raw[1:] if raw else "Something went wrong. Try again."


# --- REST ---------------------------------------------------------------------

def _request(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    if not configured():
        raise AuthError("Accounts aren't set up in this version of Kestrel.")
    headers = {
        "apikey": cloud.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
        "User-Agent": f"Kestrel/{__version__}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(cloud.SUPABASE_URL.rstrip("/") + path, data=data, headers=headers,
                                     method=method)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            text = response.read().decode() or "{}"
            return json.loads(text)
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read().decode() or "{}")
        except ValueError:
            payload = {}
        raise AuthError(friendly_error(payload, error.code)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise AuthError("Couldn't reach the account server. Check your internet connection.") from None


def _session(data: dict) -> Session:
    user = data.get("user") or {}
    return Session(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=time.time() + float(data.get("expires_in", 3600)),
        user_id=user.get("id", ""),
        email=user.get("email", ""),
    )


def validate(email: str, password: str) -> None:
    if not EMAIL.match(email):
        raise AuthError("Enter a valid email address.")
    if len(password) < MIN_PASSWORD:
        raise AuthError(f"Use a password with at least {MIN_PASSWORD} characters.")


def sign_in(email: str, password: str) -> Session:
    validate(email, password)
    return _session(_request("POST", "/auth/v1/token?grant_type=password",
                             {"email": email, "password": password}))


def sign_up(email: str, password: str) -> Session | None:
    """Returns a session, or None when the project asks users to confirm their email first."""
    validate(email, password)
    data = _request("POST", "/auth/v1/signup", {"email": email, "password": password})
    return _session(data) if data.get("access_token") else None


def refresh(session: Session) -> Session:
    return _session(_request("POST", "/auth/v1/token?grant_type=refresh_token",
                             {"refresh_token": session.refresh_token}))


def send_password_reset(email: str) -> None:
    if not EMAIL.match(email):
        raise AuthError("Type your email above first, then tap “Forgot password?” again.")
    _request("POST", "/auth/v1/recover", {"email": email})


def sign_out(session: Session) -> None:
    try:
        _request("POST", "/auth/v1/logout", {}, token=session.access_token)
    except AuthError:
        pass  # the local session is removed either way


# --- Local storage ------------------------------------------------------------

def save(session: Session) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_FILE.write_bytes(vault.protect(json.dumps(asdict(session)).encode()))


def load() -> Session | None:
    try:
        return Session(**json.loads(vault.unprotect(SESSION_FILE.read_bytes())))
    except (OSError, ValueError, TypeError):
        return None


def clear() -> None:
    SESSION_FILE.unlink(missing_ok=True)
