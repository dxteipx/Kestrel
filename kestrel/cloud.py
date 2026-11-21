"""Supabase project settings.

Fill these in with your project's values (Supabase → Project Settings → API).
Both are meant to be public: the anon / publishable key only allows what your
Row Level Security rules allow. Never put the service_role / secret key here.

Leave them empty and Kestrel simply runs without accounts.
For local testing you can also set KESTREL_SUPABASE_URL and KESTREL_SUPABASE_KEY.
"""

import os

SUPABASE_URL = os.environ.get("KESTREL_SUPABASE_URL", "https://eaiqnyrebkdaojxsweog.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("KESTREL_SUPABASE_KEY", "sb_publishable_xTqH6suTOlwd3KYwH_EkcQ_HfV8TIO3")

# True: the app can't be used without signing in. False: users may skip it.
REQUIRE_ACCOUNT = False

# "Continue with …" buttons on the sign-in screen. List only the providers you've
# turned on in Supabase (Authentication → Sign In / Providers) — their client ID and
# secret live there, never in this file. Supported here: google, discord, github.
OAUTH_PROVIDERS: tuple[str, ...] = ("google", "discord", "github")

# The browser sends people back to Kestrel on this local address after they sign in.
# Add it to Supabase → Authentication → URL Configuration → Redirect URLs.
OAUTH_REDIRECT_PORT = 53682
OAUTH_REDIRECT_URL = f"http://127.0.0.1:{OAUTH_REDIRECT_PORT}/callback"
