# Changelog

All notable changes to Kestrel are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-11-21

### Added
- **Graphics card stats** for NVIDIA GPUs: live load, video memory, temperature and power on the System page, plus load and temperature on the dashboard.
- **Connection test** on the Games page: ping, jitter and packet loss to Cloudflare, Google and Quad9.
- **Create a restore point** in the Optimizer, as a safety net before big changes.
- **Clear browser caches** for Chrome, Edge, Brave, Opera GX and Firefox — logins and history are kept.
- **Start Kestrel with Windows** switch in Settings.
- **Error log** with an "Open log" button in Settings, so bug reports come with details.
- A notice after Kestrel updates itself.
- "Uninstall programs" and "Network connections" in the Windows tools.
- New tutorial: *A safety net before big changes*.
- Unit tests, run on every push.

### Changed
- Opening Kestrel twice now brings the existing window to the front instead of starting a second copy.

## [1.0.0] — 2026-11-21

First public release.

### Added
- **Dashboard** with a health score, live CPU / memory / storage gauges, network and activity charts, quick actions and pinned apps.
- **System & stats**: hardware profile (copyable), drives, per-core load and top processes with End task.
- **Optimizer**: temp file cleanup, Recycle Bin, DNS flush, Game Mode, background recording, Explorer restart and power plans.
- **Drivers**: installed driver list, updates from Windows Update, one-click install and driver backup.
- **Startup**: turn startup programs on or off without deleting them.
- **Apps** and **Games**: searchable launcher with Store apps, Windows tools, Steam and Epic libraries, launchers and custom entries.
- **Tutorials** that link straight to the right page.
- **Settings**: light / dark theme, six gradient accents applied live, refresh rate, start page and admin restart.
- **Automatic updates** from GitHub Releases: checked every hour while Kestrel is open, installed silently, then Kestrel reopens. Can be turned off in Settings.
- Per-user **installer** with shortcuts, start-with-Windows option and an uninstaller registered in Settings → Apps.

[1.1.0]: https://github.com/dxteipx/Kestrel/releases/tag/v1.1.0
[1.0.0]: https://github.com/dxteipx/Kestrel/releases/tag/v1.0.0
