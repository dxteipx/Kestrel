"""The main window: sidebar, page host, live refresh loop and toasts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

import customtkinter as ctk

from kestrel import __app_name__, __version__, icons, theme
from kestrel.log import logger
from kestrel.config import CONFIG_DIR, Settings
from kestrel.core import shell, updater
from kestrel.core.system import SystemMonitor
from kestrel.ui import art, background, pages
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page
from kestrel.ui.sidebar import Sidebar

NAVIGATION = [
    ("Overview", [
        ("dashboard", "Dashboard", "dashboard", pages.DashboardPage),
        ("system", "System & stats", "system", pages.SystemPage),
    ]),
    ("Tune", [
        ("optimizer", "Optimizer", "optimizer", pages.OptimizerPage),
        ("drivers", "Drivers", "drivers", pages.DriversPage),
        ("startup", "Startup", "startup", pages.StartupPage),
    ]),
    ("Library", [
        ("apps", "Apps", "apps", pages.AppsPage),
        ("games", "Games", "games", pages.GamesPage),
    ]),
]
FOOTER = [
    ("tutorials", "Tutorials", "tutorials", pages.TutorialsPage),
    ("settings", "Settings", "settings", pages.SettingsPage),
]
_ALL = [entry for _, entries in NAVIGATION for entry in entries] + FOOTER
PAGE_TYPES: dict[str, type[Page]] = {key: cls for key, _, _, cls in _ALL}
PAGE_TITLES: dict[str, str] = {key: title for key, title, _, _ in _ALL}
UPDATE_INTERVAL_MS = 60 * 60 * 1000


class KestrelApp(ctk.CTk):
    def __init__(self) -> None:
        self.settings = Settings.load()
        ctk.set_appearance_mode(self.settings.appearance)
        theme.set_accent(self.settings.accent)
        super().__init__(fg_color=theme.BG)
        self.attributes("-alpha", 0.0)

        icons.detect(self)
        theme.detect_fonts(self)
        art.set_scale(ctk.ScalingTracker.get_window_scaling(self))
        self.is_admin = shell.is_admin()
        self.monitor = SystemMonitor()
        self.page_titles = PAGE_TITLES

        self.title(__app_name__)
        self.geometry("1360x860")
        self.minsize(1140, 720)

        self._pages: dict[str, Page] = {}
        self._current_key: str | None = None
        self._toast: ctk.CTkFrame | None = None
        self._toast_job: str | None = None
        self._updating = False

        for index, key in enumerate(PAGE_TYPES, start=1):
            if index <= 9:
                self.bind(f"<Control-Key-{index}>", lambda _e, k=key: self.navigate(k))

        start = self.settings.start_page if self.settings.start_page in PAGE_TYPES else "dashboard"
        self._build(start)
        self.after(200, self._tick)
        self.after(60, self._fade_in)
        self.after(20_000, self._scheduled_update_check)
        self.after(1200, self._announce_update)

    def report_callback_exception(self, kind, error, trace) -> None:
        """Any error inside a Tk callback ends up here instead of a silent console."""
        logger.error("Error in the interface", exc_info=(kind, error, trace))
        try:
            self.toast("Something went wrong. Details were saved to the log (Settings → Open log).", "error")
        except Exception:
            pass

    def _announce_update(self) -> None:
        previous = self.settings.last_version
        if previous != __version__:
            self.settings.last_version = __version__
            self.settings.save()
            if previous:
                self.toast(f"Kestrel was updated to {__version__}. See Settings → Updates for what's new.", "info")

    # --- Layout -----------------------------------------------------------

    def _build(self, page: str) -> None:
        """(Re)create the whole interface. Used at start and after theme changes."""
        for child in self.winfo_children():
            if not isinstance(child, ctk.CTkToplevel):
                child.destroy()
        self._pages.clear()
        self._current_key = None
        self._toast = None
        self.configure(fg_color=theme.BG)
        w.style_tables()
        self._set_icon()

        self.sidebar = Sidebar(
            self,
            groups=[(group, [(k, t, g) for k, t, g, _ in entries]) for group, entries in NAVIGATION],
            footer_items=[(k, t, g) for k, t, g, _ in FOOTER],
            on_select=self.navigate,
            is_admin=self.is_admin,
        )
        self.sidebar.pack(side="left", fill="y")
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)
        self.navigate(page)

    def _set_icon(self) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            path = CONFIG_DIR / "kestrel.ico"
            art.write_icon(path, *theme.accent_pair())
            self.iconbitmap(str(path))
        except OSError:
            pass

    def _fade_in(self, alpha: float = 0.0) -> None:
        alpha = min(alpha + 0.12, 1.0)
        self.attributes("-alpha", alpha)
        if alpha < 1.0:
            self.after(16, lambda: self._fade_in(alpha))

    # --- Navigation -------------------------------------------------------

    @property
    def current(self) -> Page | None:
        return self._pages.get(self._current_key) if self._current_key else None

    def navigate(self, key: str) -> None:
        page = self._pages.get(key)
        if page is None:
            page = PAGE_TYPES[key](self.content, self)
            self._pages[key] = page
        if self.current is not page:
            if self.current is not None:
                self.current.pack_forget()
            page.pack(fill="both", expand=True)
            self._current_key = key
        self.sidebar.set_active(key)
        page.on_show()
        if self.monitor.latest:
            page.on_tick(self.monitor.latest)

    def _tick(self) -> None:
        snapshot = self.monitor.sample()
        try:
            self.sidebar.on_tick(snapshot)
            if self.current is not None:
                self.current.on_tick(snapshot)
        finally:
            self.after(self.settings.refresh_ms, self._tick)

    # --- Feedback ---------------------------------------------------------

    def toast(self, message: str, kind: str = "success") -> None:
        if self._toast is not None and self._toast.winfo_exists():
            self._toast.destroy()
        if self._toast_job:
            self.after_cancel(self._toast_job)

        colors = {
            "success": (theme.SUCCESS, "#2dd4bf"),
            "error": (theme.DANGER, theme.WARNING),
            "info": theme.accent_pair(),
        }[kind]
        glyph_name = {"success": "check", "error": "warning", "info": "info"}[kind]

        toast = ctk.CTkFrame(self.content, fg_color=theme.SURFACE, corner_radius=16,
                             border_width=1, border_color=theme.BORDER)
        w.icon_chip(toast, glyph_name, 30, solid=True, colors=colors).pack(side="left", padx=(14, 12), pady=12)
        w.label(toast, message, 13, wraplength=440).pack(side="left", padx=(0, 20), pady=12)
        toast.place(relx=1.0, rely=1.0, x=-28, y=-28, anchor="se")
        toast.lift()
        self._toast = toast
        self._toast_job = self.after(4200 if kind == "error" else 3200, toast.destroy)

    def confirm(self, title: str, message: str, action: str = "Continue", danger: bool = False) -> bool:
        if not danger and not self.settings.confirm_actions:
            return True
        return w.confirm(self, title, message, action, danger)

    def perform(self, work: Callable[[], Any], on_done: Callable[[Any], None] | None = None) -> None:
        """Run a task in the background and report its result (a string) as a toast."""

        def done(result: Any) -> None:
            if isinstance(result, str) and result:
                self.toast(result)
            if on_done:
                on_done(result)

        def failed(error: Exception) -> None:
            logger.warning("Task failed: %s", error, exc_info=error)
            if isinstance(error, PermissionError):
                self.toast("That needs administrator rights. Restart Kestrel as admin from Settings.", "error")
            else:
                self.toast(f"Something went wrong: {error}", "error")

        background.run(self, work, on_done=done, on_error=failed)

    # --- Updates ----------------------------------------------------------

    def _scheduled_update_check(self) -> None:
        if self.settings.auto_update:
            self.check_for_updates(manual=False)
        self.after(UPDATE_INTERVAL_MS, self._scheduled_update_check)

    def check_for_updates(self, manual: bool = True, on_status: Callable[[str], None] | None = None) -> None:
        """Look for a newer release; install it when found (always when asked, or if auto-update is on)."""
        status = on_status or (lambda _text: None)
        if self._updating:
            return
        status("Checking for updates…")

        def done(release: updater.Release | None) -> None:
            self.settings.last_update_check = datetime.now().strftime("%d %b %Y, %H:%M")
            self.settings.save()
            if release is None:
                status(f"You're on the latest version. Last checked {self.settings.last_update_check}.")
                if manual:
                    self.toast("Kestrel is up to date")
                return
            status(f"Kestrel {release.version} is available.")
            if manual or self.settings.auto_update:
                self.install_update(release, status)

        def failed(error: Exception) -> None:
            logger.warning("Update check failed: %s", error)
            status("Couldn't reach GitHub. Check your connection and try again.")
            if manual:
                self.toast(f"Update check failed: {error}", "error")

        background.run(self, updater.check, on_done=done, on_error=failed)

    def install_update(self, release: updater.Release, status: Callable[[str], None]) -> None:
        if not updater.can_self_update():
            status(f"Kestrel {release.version} is out. You're running from source, so pull the latest code.")
            self.toast(f"Kestrel {release.version} is available on GitHub", "info")
            return
        if not release.installer_url:
            status(f"Kestrel {release.version} is out, but its installer isn't uploaded yet.")
            return

        self._updating = True
        status(f"Downloading Kestrel {release.version}…")
        self.toast(f"Updating to Kestrel {release.version} — it will reopen by itself.", "info")

        def downloaded(installer) -> None:
            updater.launch_installer(installer)
            self.after(400, self.destroy)

        def failed(error: Exception) -> None:
            self._updating = False
            logger.error("Update download failed: %s", error)
            status(f"Download failed: {error}")
            self.toast(f"Update failed: {error}", "error")

        background.run(self, updater.download, release, on_done=downloaded, on_error=failed)

    # --- Preferences ------------------------------------------------------

    def set_appearance(self, mode: str) -> None:
        self.settings.appearance = mode
        self.settings.save()
        ctk.set_appearance_mode(mode)
        self.after(30, lambda: self._build(self._current_key or "settings"))

    def set_accent(self, name: str) -> None:
        self.settings.accent = name
        self.settings.save()
        theme.set_accent(name)
        self.after(30, lambda: self._build(self._current_key or "settings"))

    def restart(self) -> None:
        shell.restart_app()
        self.destroy()
