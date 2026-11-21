from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from kestrel import theme
from kestrel.core import launcher
from kestrel.core.launcher import AppEntry
from kestrel.ui import background
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page

_RENDER_LIMIT = 80


class AppsPage(Page):
    title = "Apps"
    kicker = "Library"
    subtitle = "Everything installed on this PC, plus the Windows tools you keep looking for."

    def build(self) -> None:
        actions = self.header.actions
        w.SearchBox(actions, self._filter, "Search apps", width=260).pack(side="left", padx=(0, 8))
        w.button(actions, "Add app", self._add_custom, kind="primary").pack(side="left")

        tools = w.Card(self.section(), "Windows tools")
        tools.pack(fill="x")
        grid = tools.body
        grid.grid_columnconfigure(tuple(range(5)), weight=1, uniform="tools")
        for index, tool in enumerate(launcher.WINDOWS_TOOLS):
            w.button(grid, tool.name, lambda t=tool: self._launch(t)).grid(
                row=index // 5, column=index % 5, sticky="ew", padx=4, pady=4)

        self.list_card = w.Card(self.section(), "All apps")
        self.list_card.pack(fill="x")
        self.count = w.muted(self.list_card.actions, "Loading…")
        self.count.pack()

        self._apps: list[AppEntry] = []
        self._query = ""
        self._loaded = False

    def on_show(self) -> None:
        if not self._loaded:
            self._loaded = True
            background.run(self, launcher.installed_apps, on_done=self._show)
        else:
            self._render()

    def _show(self, apps: list[AppEntry]) -> None:
        self._apps = apps
        self._render()

    def _filter(self, query: str) -> None:
        self._query = query
        self._render()

    @property
    def _pinned_targets(self) -> set[str]:
        return {entry["target"] for entry in self.app.settings.pinned_apps}

    def _all(self) -> list[AppEntry]:
        custom = [AppEntry.from_dict(d) for d in self.app.settings.custom_apps]
        pinned = self._pinned_targets
        apps = custom + self._apps
        return sorted(apps, key=lambda a: (a.target not in pinned, a.name.lower()))

    def _render(self) -> None:
        body = self.list_card.body
        for child in body.winfo_children():
            child.destroy()

        matches = [a for a in self._all() if self._query in a.name.lower()]
        shown = matches[:_RENDER_LIMIT]
        total = len(self._apps) + len(self.app.settings.custom_apps)
        self.count.configure(text=f"{len(matches)} of {total}")

        if not shown:
            w.EmptyState(body, "search", "No apps found", "Try a shorter search.").pack(fill="x")
            return

        pinned = self._pinned_targets
        custom = {d["target"] for d in self.app.settings.custom_apps}
        for app in shown:
            self._row(body, app, app.target in pinned, app.target in custom).pack(fill="x", pady=2)
        if len(matches) > len(shown):
            w.muted(body, f"Showing the first {len(shown)} — search to narrow it down.").pack(anchor="w", pady=8)

    def _row(self, master, app: AppEntry, pinned: bool, custom: bool) -> ctk.CTkFrame:
        row = ctk.CTkFrame(master, fg_color="transparent", corner_radius=9, cursor="hand2")
        w.initial_tile(row, app.name, 32).pack(side="left", padx=(8, 12), pady=6)
        w.label(row, app.name, 13).pack(side="left", fill="x", expand=True)

        buttons = []
        if custom:
            buttons.append(w.icon_button(row, "delete", lambda: self._remove_custom(app)))
        buttons.append(w.icon_button(row, "unpin" if pinned else "pin", lambda: self._toggle_pin(app),
                                     color=theme.accent() if pinned else None))
        buttons.append(w.icon_button(row, "open", lambda: self._launch(app)))
        for index, btn in enumerate(buttons):
            btn.pack(side="right", padx=(0, 6 if index == 0 else 0))

        w.make_hoverable(row, "transparent", theme.SURFACE_HI, on_click=lambda: self._launch(app),
                         event="<Double-Button-1>", skip=buttons)
        return row

    # --- Actions ----------------------------------------------------------

    def _launch(self, app: AppEntry) -> None:
        try:
            launcher.launch(app)
        except OSError as error:
            self.app.toast(f"Couldn't open {app.name}: {error.strerror or error}", "error")
            return
        self.app.toast(f"Opening {app.name}…", "info")

    def _toggle_pin(self, app: AppEntry) -> None:
        settings = self.app.settings
        if app.target in self._pinned_targets:
            settings.pinned_apps = [d for d in settings.pinned_apps if d["target"] != app.target]
            self.app.toast(f"Unpinned {app.name}")
        else:
            settings.pinned_apps.append(app.to_dict())
            self.app.toast(f"Pinned {app.name} to the dashboard")
        settings.save()
        self._render()

    def _add_custom(self) -> None:
        path = filedialog.askopenfilename(
            title="Pick a program",
            filetypes=[("Programs", "*.exe *.lnk *.bat *.cmd"), ("All files", "*.*")],
        )
        if not path:
            return
        entry = AppEntry(Path(path).stem, path)
        self.app.settings.custom_apps.append(entry.to_dict())
        self.app.settings.save()
        self.app.toast(f"Added {entry.name}")
        self._render()

    def _remove_custom(self, app: AppEntry) -> None:
        settings = self.app.settings
        settings.custom_apps = [d for d in settings.custom_apps if d["target"] != app.target]
        settings.pinned_apps = [d for d in settings.pinned_apps if d["target"] != app.target]
        settings.save()
        self._render()
