from __future__ import annotations

import customtkinter as ctk

from kestrel import theme
from kestrel.core import shell, startup
from kestrel.core.startup import StartupItem
from kestrel.ui import background
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page


class StartupRow(ctk.CTkFrame):
    def __init__(self, master, item: StartupItem, on_toggle):
        super().__init__(master, fg_color="transparent")
        self.item = item

        w.initial_tile(self, item.display_name, 38).pack(side="left", padx=(0, 14))
        text = ctk.CTkFrame(self, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        w.label(text, item.display_name, 14, "bold").pack(anchor="w")
        command = item.command if len(item.command) < 90 else item.command[:87] + "…"
        w.muted(text, command, 11).pack(anchor="w")

        self.switch = w.switch(self, lambda: on_toggle(self), item.enabled)
        self.switch.pack(side="right")

        target = item.target
        w.icon_button(self, "folder", (lambda: shell.reveal(str(target))) if target else None,
                      state="normal" if target else "disabled").pack(side="right", padx=(0, 8))
        w.Badge(self, item.source, theme.resolve(theme.MUTED)).pack(side="right", padx=(0, 12))


class StartupPage(Page):
    title = "Startup"
    kicker = "Tune"
    subtitle = "Choose what opens when Windows starts. Fewer items means a faster boot."

    def build(self) -> None:
        actions = self.header.actions
        w.button(actions, "Startup folder", lambda: shell.open_target(str(startup.USER_FOLDER)),
                 kind="ghost", width=120).pack(side="left", padx=(0, 8))
        w.button(actions, "Refresh", self.on_show, width=90).pack(side="left")

        self.card = w.Card(self.section(), "Programs")
        self.card.pack(fill="x")
        self.summary = w.Badge(self.card.actions, "…")
        self.summary.pack(side="left", padx=(0, 12))
        w.SearchBox(self.card.actions, self._filter, "Filter programs").pack(side="left")

        tip = w.Card(self.section())
        tip.pack(fill="x")
        row = ctk.CTkFrame(tip.body, fg_color="transparent")
        row.pack(fill="x")
        w.glyph(row, "info", 16).pack(side="left", padx=(0, 12))
        w.muted(row, "Turning something off here doesn't uninstall it — it just won't launch on boot. "
                     "Items marked “all users” need Kestrel running as administrator.", 12,
                wraplength=760).pack(side="left", fill="x")

        self._items: list[StartupItem] = []
        self._query = ""

    def on_show(self) -> None:
        background.run(self, startup.list_items, on_done=self._show)

    def _show(self, items: list[StartupItem]) -> None:
        self._items = items
        enabled = sum(1 for i in items if i.enabled)
        self.summary.set(f"{enabled} on · {len(items) - enabled} off", theme.accent())
        self._render()

    def _filter(self, query: str) -> None:
        self._query = query
        self._render()

    def _render(self) -> None:
        for child in self.card.body.winfo_children():
            child.destroy()
        visible = [i for i in self._items if self._query in f"{i.display_name} {i.command}".lower()]
        if not visible:
            w.EmptyState(self.card.body, "startup", "Nothing here",
                         "No startup programs match." if self._query else "Windows starts clean.").pack(fill="x")
            return
        for index, item in enumerate(visible):
            if index:
                w.divider(self.card.body, pady=8)
            StartupRow(self.card.body, item, self._toggle).pack(fill="x")

    def _toggle(self, row: StartupRow) -> None:
        enabled = bool(row.switch.get())
        try:
            startup.set_enabled(row.item, enabled)
        except OSError as error:
            row.switch.deselect() if enabled else row.switch.select()
            if isinstance(error, PermissionError):
                message = "This one applies to all users — restart Kestrel as administrator to change it."
            else:
                message = f"Couldn't change it: {error}"
            self.app.toast(message, "error")
            return
        state = "will start with Windows" if enabled else "won't start with Windows anymore"
        self.app.toast(f"{row.item.display_name} {state}")
        on = sum(1 for i in self._items if i.enabled)
        self.summary.set(f"{on} on · {len(self._items) - on} off", theme.accent())
