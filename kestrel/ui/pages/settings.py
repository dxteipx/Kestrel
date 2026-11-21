from __future__ import annotations

import webbrowser

import customtkinter as ctk

from kestrel import __app_name__, __author__, __repo__, __version__, icons, theme
from kestrel.config import CONFIG_DIR
from kestrel.core import shell
from kestrel.ui import art
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page

_REFRESH_RATES = {"Fast (0.5 s)": 500, "Normal (1 s)": 1000, "Relaxed (2 s)": 2000, "Battery saver (5 s)": 5000}


def _setting_row(master, title: str, description: str) -> ctk.CTkFrame:
    """A labelled row; returns the frame on the right where the control goes."""
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(fill="x", pady=8)
    text = ctk.CTkFrame(row, fg_color="transparent")
    text.pack(side="left", fill="x", expand=True)
    w.label(text, title, 13, "bold").pack(anchor="w")
    w.muted(text, description, 12, wraplength=520).pack(anchor="w")
    control = ctk.CTkFrame(row, fg_color="transparent")
    control.pack(side="right")
    return control


def _option_menu(master, values, current, command, width=200):
    menu = ctk.CTkOptionMenu(
        master, values=values, width=width, height=34, corner_radius=9, font=theme.font(13),
        fg_color=theme.SURFACE_HI, button_color=theme.SURFACE_HI, button_hover_color=theme.BORDER,
        text_color=theme.TEXT, dropdown_font=theme.font(13), command=command,
    )
    menu.set(current)
    return menu


class SettingsPage(Page):
    title = "Settings"
    kicker = "Preferences"
    subtitle = "Make Kestrel yours."

    def build(self) -> None:
        settings = self.app.settings

        look = w.Card(self.section(), "Appearance")
        look.pack(fill="x")
        theme_control = _setting_row(look.body, "Theme", "Follow Windows, or pick light or dark.")
        mode = ctk.CTkSegmentedButton(
            theme_control, values=["Light", "Dark", "System"], command=self.app.set_appearance,
            font=theme.font(13), height=34, corner_radius=9, selected_color=theme.accent(),
            selected_hover_color=theme.accent_hover(), unselected_color=theme.SURFACE_HI,
            unselected_hover_color=theme.BORDER, fg_color=theme.SURFACE_HI, text_color=theme.TEXT,
        )
        mode.set(settings.appearance)
        mode.pack()

        w.divider(look.body)
        accent_control = _setting_row(look.body, "Accent color", "Gradient used for buttons, gauges and charts. Applies instantly.")
        for name, (start, end) in theme.ACCENTS.items():
            selected = name == settings.accent
            swatch = ctk.CTkLabel(accent_control, text=icons.get("check") if selected else "", compound="center",
                                  image=art.tile(32, 32, 16, start, end), text_color="#ffffff",
                                  font=icons.font(13), cursor="hand2", fg_color="transparent")
            swatch.pack(side="left", padx=4)
            swatch.bind("<Button-1>", lambda _e, n=name: self._set_accent(n))

        behaviour = w.Card(self.section(), "Behaviour")
        behaviour.pack(fill="x")
        refresh_name = next((k for k, v in _REFRESH_RATES.items() if v == settings.refresh_ms), "Normal (1 s)")
        _option_menu(_setting_row(behaviour.body, "Refresh rate", "How often live stats update."),
                     list(_REFRESH_RATES), refresh_name, self._set_refresh).pack()

        w.divider(behaviour.body)
        titles = {title: key for key, title in self.app.page_titles.items()}
        _option_menu(_setting_row(behaviour.body, "Open on", "The page Kestrel shows when it starts."),
                     list(titles), self.app.page_titles.get(settings.start_page, "Dashboard"),
                     lambda title: self._save(start_page=titles[title])).pack()

        w.divider(behaviour.body)
        confirm = w.switch(
            _setting_row(behaviour.body, "Ask before running tasks",
                         "Destructive actions like emptying the Recycle Bin always ask."),
            lambda: self._save(confirm_actions=bool(confirm.get())), settings.confirm_actions,
        )
        confirm.pack()

        self._updates_card()

        access = w.Card(self.section(), "Permissions & data")
        access.pack(fill="x")
        admin_control = _setting_row(
            access.body, "Administrator mode",
            "Needed to change startup items for all users and to clean the Windows Temp folder.",
        )
        if self.app.is_admin:
            w.Badge(admin_control, "Running as administrator", theme.SUCCESS).pack()
        else:
            w.button(admin_control, "Restart as admin", self._elevate, width=150).pack()

        w.divider(access.body)
        data_control = _setting_row(access.body, "Your settings",
                                    f"Stored in {CONFIG_DIR}. Pinned apps and custom games live here too.")
        w.button(data_control, "Open folder", self._open_config, kind="ghost", width=110).pack(side="left")
        w.button(data_control, "Reset", self._reset, kind="danger", width=80).pack(side="left", padx=(8, 0))

        self._about()

    def _updates_card(self) -> None:
        settings = self.app.settings
        card = w.Card(self.section(), "Updates")
        card.pack(fill="x")

        row = ctk.CTkFrame(card.body, fg_color="transparent")
        row.pack(fill="x", pady=(0, 4))
        w.icon_chip(row, "download", 44, solid=True).pack(side="left")
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=14)
        w.label(text, f"Kestrel {__version__}", 14, "bold").pack(anchor="w")
        last = settings.last_update_check
        self.update_status = w.muted(text, f"Last checked {last}." if last else "Not checked yet.", 12,
                                     wraplength=480)
        self.update_status.pack(anchor="w")
        w.button(row, "Check for updates", self._check_updates, kind="primary", width=160).pack(side="right")

        w.divider(card.body)
        w.switch(
            _setting_row(card.body, "Install updates automatically",
                         "Checks every hour while Kestrel is open. New versions download and install by "
                         "themselves, then Kestrel reopens."),
            lambda: self._save(auto_update=not self.app.settings.auto_update), settings.auto_update,
        ).pack()

    def _check_updates(self) -> None:
        def show(text: str) -> None:
            if self.update_status.winfo_exists():
                self.update_status.configure(text=text)

        self.app.check_for_updates(manual=True, on_status=show)

    def _about(self) -> None:
        about = w.Card(self.section(pady=(0, 28)))
        about.pack(fill="x")
        row = ctk.CTkFrame(about.body, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="K", width=56, height=56, corner_radius=16, fg_color=theme.accent(),
                     text_color="#ffffff", font=theme.font(26, "bold")).pack(side="left")
        text = ctk.CTkFrame(row, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=16)
        w.label(text, f"{__app_name__} {__version__}", 18, "bold").pack(anchor="w")
        w.muted(text, f"Designed and built by {__author__}. Free and open source under the MIT License.",
                13).pack(anchor="w")
        w.muted(text, "Made with Python, CustomTkinter, psutil and Pillow.", 12).pack(anchor="w", pady=(2, 0))
        w.button(row, "Report an issue", lambda: webbrowser.open(f"{__repo__}/issues"), kind="ghost",
                 width=130).pack(side="right")
        w.button(row, "GitHub", lambda: webbrowser.open(__repo__), kind="primary").pack(side="right", padx=8)

    # --- Actions ----------------------------------------------------------

    def _save(self, **changes) -> None:
        for key, value in changes.items():
            setattr(self.app.settings, key, value)
        self.app.settings.save()

    def _set_refresh(self, name: str) -> None:
        self._save(refresh_ms=_REFRESH_RATES[name])

    def _set_accent(self, name: str) -> None:
        if name != self.app.settings.accent:
            self.app.set_accent(name)

    def _elevate(self) -> None:
        if shell.relaunch_as_admin():
            self.app.destroy()
        else:
            self.app.toast("Windows didn't grant administrator rights.", "error")

    def _open_config(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        shell.open_target(str(CONFIG_DIR))

    def _reset(self) -> None:
        if self.app.confirm("Reset all settings?", "Theme, pinned apps and custom games will be cleared. "
                                                   "Kestrel restarts afterwards.", "Reset", danger=True):
            self.app.settings.reset()
            self.app.restart()
