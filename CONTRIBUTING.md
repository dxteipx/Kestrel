# Contributing to Kestrel

Thanks for wanting to help! Bug reports, ideas and pull requests are all welcome.

## Running from source

```bash
git clone https://github.com/dxteipx/Kestrel.git
cd kestrel
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Kestrel is Windows-only (10 and 11) and needs Python 3.10 or newer.

## How the code is laid out

- `kestrel/core` talks to Windows — processes, registry, PowerShell. **No UI code here.**
- `kestrel/ui` is the interface. Pages live in `kestrel/ui/pages`, one file each, built from the pieces in `widgets.py`.
- `kestrel/ui/art.py` draws every gradient, gauge and chart with Pillow. Pass it resolved hex colors, never `(light, dark)` pairs.
- Anything slow (PowerShell, disk scans) goes through `kestrel.ui.background.run` so the window never freezes.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Logic in `kestrel/core` should come with a test when it parses or decides something (see `tests/`).

## Pull requests

1. Keep each PR focused on one thing.
2. Match the existing style: type hints, short functions, no commented-out code.
3. Anything that changes the system (deletes files, edits the registry) must ask first through `app.confirm`, and must be reversible where possible.
4. If the change is visible, add a before/after screenshot.
5. Add a line to `CHANGELOG.md` under an **Unreleased** heading.

## Building the installer

```bash
pip install pyinstaller
python packaging/build.py
```

The result is `dist/Kestrel-Setup-<version>.exe`. Pushing a tag like `v1.0.1` builds it on GitHub Actions and attaches it to a release automatically.

## Translations

Interface text is in English. Tutorial content lives in `kestrel/content/tutorials.py` as plain data — a good first contribution if you'd like Kestrel in your language.
