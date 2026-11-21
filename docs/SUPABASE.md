# Connecting Kestrel to Supabase

Kestrel's accounts use [Supabase Auth](https://supabase.com/docs/guides/auth). It's free for small projects
and Kestrel talks to it directly over its REST API — no extra Python packages.

Without these steps Kestrel still works: the sign-in screen just doesn't appear.

## 1. Create the project

1. Sign up at [supabase.com](https://supabase.com) and click **New project**.
2. Name it `kestrel`, choose a strong database password (save it somewhere safe) and the region closest to you.
3. Wait a minute while the project is created.

## 2. Turn on email sign-in

1. Open **Authentication → Sign In / Providers**.
2. Make sure **Email** is enabled.
3. **Confirm email** — on (recommended) means new users must click a link before signing in.
   Kestrel handles both cases.

## 3. Set where email links go

1. Open **Authentication → URL Configuration**.
2. Set **Site URL** to your project page, e.g. `https://github.com/dxteipx/Kestrel`.
   Confirmation and password-reset emails send people there after they click the link.

## 4. Copy the keys into Kestrel

1. Open **Project Settings → API Keys** (older dashboards: **Project Settings → API**).
2. Copy the **Project URL** and the **anon / publishable** key.
3. Paste them into [`kestrel/cloud.py`](../kestrel/cloud.py):

```python
SUPABASE_URL = os.environ.get("KESTREL_SUPABASE_URL", "https://YOUR-PROJECT.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("KESTREL_SUPABASE_KEY", "YOUR-ANON-OR-PUBLISHABLE-KEY")
```

> **Only ever use the anon / publishable key.** It's designed to ship inside apps.
> The **service_role / secret** key gives full access to your database — never put it in Kestrel or on GitHub.

Set `REQUIRE_ACCOUNT = True` in the same file if the app shouldn't be usable without signing in.

## 5. Try it

Run `python main.py`. The sign-in screen shows on first launch; after signing in, the account appears in
**Settings → Account**, where you can also sign out.

New users show up in Supabase under **Authentication → Users**.

## 6. Sign in with GitHub, Google or Discord (optional)

The provider's **Client ID and Client Secret go into Supabase, never into Kestrel.** Kestrel only shows the
"Continue with …" buttons listed in `OAUTH_PROVIDERS` in `kestrel/cloud.py`.

**First, in Supabase:**

1. **Authentication → Sign In / Providers → (provider)** — copy the **Callback URL** it shows.
   It looks like `https://YOUR-PROJECT.supabase.co/auth/v1/callback`.
2. **Authentication → URL Configuration → Redirect URLs → Add URL:** `http://127.0.0.1:53682/callback`
   (that's where the browser hands the result back to Kestrel).

**GitHub** — [github.com/settings/developers](https://github.com/settings/developers) → **OAuth Apps → New OAuth App**
- Application name: `Kestrel` · Homepage URL: `https://github.com/dxteipx/Kestrel`
- Authorization callback URL: the Supabase **Callback URL** from step 1
- **Register application** → copy the **Client ID** → **Generate a new client secret** → copy it
- Paste both into Supabase's GitHub provider and turn it on.

**Discord** — [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application**
- **OAuth2** → copy the **Client ID**, **Reset Secret** to get the **Client Secret**
- **OAuth2 → Redirects → Add Redirect:** the Supabase **Callback URL**
- Paste both into Supabase's Discord provider and turn it on.

**Google** — [console.cloud.google.com](https://console.cloud.google.com) → create a project
- **Google Auth Platform → Branding**: fill in the app name and support email (the consent screen)
- **Clients → Create client → Web application**
- **Authorized redirect URIs:** the Supabase **Callback URL**
- Copy the **Client ID** and **Client secret** into Supabase's Google provider and turn it on.

Remove any provider you didn't set up from `OAUTH_PROVIDERS`, otherwise its button opens an error page.

## 7. Trusted PCs (no sign-in needed)

With `REQUIRE_ACCOUNT = True`, everyone has to sign in — except on PCs listed in `OWNER_DEVICES` in
`kestrel/cloud.py`. A PC is recognised by its NVIDIA graphics card's unique ID, but only a one-way
fingerprint of it is stored, so the real ID never ends up on GitHub.

To trust a PC, run this on it and add the printed line to `OWNER_DEVICES`:

```bash
python -m kestrel.core.device
```

This only skips the sign-in screen on that PC. It doesn't give access to anyone's account or data.

## How it works

| Piece | Where |
| --- | --- |
| Sign in, sign up, refresh, password reset, sign out | `kestrel/core/account.py` |
| Session stored encrypted with Windows DPAPI | `%APPDATA%\Kestrel\session.bin` via `kestrel/core/vault.py` |
| Sign-in screen | `kestrel/ui/login.py` |
| GitHub / Google / Discord sign-in (PKCE + local callback) | `kestrel/core/oauth.py` |
| Account card | Settings page |

The session is refreshed in the background on every launch, so users stay signed in. If they're offline,
the saved session is kept until they're back.

## Next step: syncing settings

Signing in is the foundation. To sync settings (theme, pinned apps, custom games) between PCs, create a
`profiles` table with a JSON column and a Row Level Security policy so each user can only read and write
their own row:

```sql
create table public.profiles (
  id uuid primary key references auth.users on delete cascade,
  settings jsonb not null default '{}',
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users manage their own profile"
  on public.profiles for all
  using (auth.uid() = id)
  with check (auth.uid() = id);
```
