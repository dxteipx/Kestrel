"""Sign in with Google, Discord or GitHub through Supabase, the desktop way.

1. Kestrel opens the browser on Supabase's /authorize page with a PKCE challenge.
2. The user signs in with the provider; Supabase sends the browser back to a tiny
   server Kestrel runs on 127.0.0.1 with a one-time code.
3. Kestrel exchanges that code (plus the secret PKCE verifier) for a session.

The provider's client ID and secret are configured in Supabase, not here.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse

from kestrel import cloud
from kestrel.core import account
from kestrel.core.account import AuthError, Session

PROVIDER_NAMES = {"google": "Google", "discord": "Discord", "github": "GitHub"}

_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>Kestrel</title><style>
body{{margin:0;height:100vh;display:grid;place-items:center;background:#07080d;color:#eef0ff;
font-family:"Segoe UI",system-ui,sans-serif}}
.card{{text-align:center;padding:48px 56px;border-radius:24px;background:#0f1119;border:1px solid #1a1e2b}}
.mark{{width:56px;height:56px;border-radius:16px;margin:0 auto 20px;
background:linear-gradient(135deg,#8b5cf6,#22d3ee)}}
h1{{margin:0 0 8px;font-size:24px}} p{{margin:0;color:#8a90a8}}
</style></head><body><div class="card"><div class="mark"></div><h1>{title}</h1><p>{text}</p></div></body></html>"""


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def authorize_url(provider: str, challenge: str) -> str:
    query = urlencode({
        "provider": provider,
        "redirect_to": cloud.OAUTH_REDIRECT_URL,
        "code_challenge": challenge,
        "code_challenge_method": "s256",
    })
    return f"{cloud.SUPABASE_URL.rstrip('/')}/auth/v1/authorize?{query}"


class _Callback(BaseHTTPRequestHandler):
    result: dict[str, str] = {}

    def log_message(self, *_args) -> None:
        pass

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path != urlparse(cloud.OAUTH_REDIRECT_URL).path:
            self.send_response(404)
            self.end_headers()
            return
        params = {key: values[0] for key, values in parse_qs(url.query).items()}
        type(self).result = params
        if "code" in params:
            page = _PAGE.format(title="You're signed in", text="You can close this tab and go back to Kestrel.")
        else:
            page = _PAGE.format(title="Sign-in didn't finish", text="Go back to Kestrel and try again.")
        body = page.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def sign_in(provider: str, cancelled: threading.Event | None = None, timeout: float = 300,
            open_browser: Callable[[str], object] | None = None) -> Session:
    """Blocks until the browser comes back, the user cancels, or `timeout` passes.
    Run it on a worker thread."""
    if not account.configured():
        raise AuthError("Accounts aren't set up in this version of Kestrel.")
    verifier, challenge = pkce_pair()

    try:
        server = HTTPServer(("127.0.0.1", cloud.OAUTH_REDIRECT_PORT), _Callback)
    except OSError:
        raise AuthError("Another app is using Kestrel's sign-in port. Close it and try again.") from None
    server.timeout = 0.5
    _Callback.result = {}

    try:
        (open_browser or webbrowser.open)(authorize_url(provider, challenge))
        deadline = time.monotonic() + timeout
        while not _Callback.result:
            if cancelled is not None and cancelled.is_set():
                raise AuthError("Sign-in was cancelled.")
            if time.monotonic() > deadline:
                raise AuthError("Sign-in timed out. Try again.")
            server.handle_request()
    finally:
        server.server_close()

    result = _Callback.result
    if "code" not in result:
        reason = result.get("error_description") or result.get("error") or "unknown error"
        raise AuthError(f"{PROVIDER_NAMES.get(provider, provider)} sign-in failed: {reason.replace('+', ' ')}")

    data = account._request("POST", "/auth/v1/token?grant_type=pkce",
                            {"auth_code": result["code"], "code_verifier": verifier})
    return account._session(data)
