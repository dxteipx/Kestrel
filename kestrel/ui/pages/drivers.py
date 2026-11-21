from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from kestrel import theme
from kestrel.core import drivers, shell
from kestrel.core.drivers import Driver, DriverUpdate
from kestrel.ui import background
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page


class DriversPage(Page):
    title = "Drivers"
    kicker = "Tune"
    subtitle = "Find driver updates on Windows Update, install them and keep a backup."

    def build(self) -> None:
        actions = self.header.actions
        w.button(actions, "Device Manager", lambda: shell.open_target("devmgmt.msc"), kind="ghost",
                 width=130).pack(side="left", padx=(0, 8))
        w.button(actions, "Back up drivers", self._backup, width=130).pack(side="left", padx=(0, 8))
        self.scan_button = w.button(actions, "Check for updates", self._scan, kind="primary", width=150)
        self.scan_button.pack(side="left")

        updates = w.Card(self.section(), "Available updates", "Straight from Microsoft's driver catalogue")
        updates.pack(fill="x")
        self.install_button = w.button(updates.actions, "Install all", self._install, kind="primary",
                                       state="disabled")
        self.install_button.pack(side="left")
        self.status = w.Badge(updates.actions, "Not checked yet", theme.resolve(theme.MUTED))
        self.status.pack(side="left", padx=(0, 10), before=self.install_button)
        self.updates_body = ctk.CTkFrame(updates.body, fg_color="transparent")
        self.updates_body.pack(fill="x")
        w.muted(self.updates_body, "Press “Check for updates” to search. It usually takes under a minute.").pack(
            anchor="w")
        self._updates: list[DriverUpdate] = []

        installed = w.Card(self.section(fill="both", expand=True), "Installed drivers")
        installed.pack(fill="both", expand=True)
        self.count = w.muted(installed.actions, "Loading…")
        self.count.pack(side="left", padx=(0, 12))
        w.SearchBox(installed.actions, self._filter, "Filter drivers").pack(side="left")
        self.table = w.DataTable(installed.body, [
            ("device", "Device", 320, "w"),
            ("category", "Type", 140, "w"),
            ("vendor", "Vendor", 180, "w"),
            ("version", "Version", 140, "w"),
            ("date", "Date", 100, "w"),
        ], height=14)
        self.table.pack(fill="both", expand=True)
        self._drivers: list[Driver] = []
        self._loaded = False

    def on_show(self) -> None:
        if not self._loaded:
            self._loaded = True
            background.run(self, drivers.installed_drivers, on_done=self._show_installed,
                           on_error=lambda e: self.count.configure(text="Couldn't read drivers"))

    def _show_installed(self, items: list[Driver]) -> None:
        self._drivers = items
        self._filter("")

    def _filter(self, query: str) -> None:
        matches = [d for d in self._drivers
                   if not query or query in f"{d.device} {d.category} {d.vendor}".lower()]
        self.table.set_rows([
            (str(index), (d.device, d.category, d.vendor, d.version, d.date)) for index, d in enumerate(matches)
        ])
        self.count.configure(text=f"{len(matches)} of {len(self._drivers)}")

    # --- Updates ----------------------------------------------------------

    def _scan(self) -> None:
        self.scan_button.configure(state="disabled", text="Checking…")
        self.status.set("Searching Windows Update", theme.WARNING)
        background.run(self, drivers.available_updates, on_done=self._show_updates, on_error=self._scan_failed)

    def _scan_failed(self, error: Exception) -> None:
        self.scan_button.configure(state="normal", text="Check for updates")
        self.status.set("Check failed", theme.DANGER)
        self.app.toast(f"Windows Update didn't respond: {error}", "error")

    def _show_updates(self, updates: list[DriverUpdate]) -> None:
        self._updates = updates
        self.scan_button.configure(state="normal", text="Check again")
        for child in self.updates_body.winfo_children():
            child.destroy()

        if not updates:
            self.status.set("Up to date", theme.SUCCESS)
            self.install_button.configure(state="disabled")
            w.EmptyState(self.updates_body, "check", "Every driver is up to date",
                         "Windows Update has nothing newer for your hardware right now.").pack(fill="x")
            return

        self.status.set(f"{len(updates)} available", theme.accent())
        self.install_button.configure(state="normal")
        for index, update in enumerate(updates):
            if index:
                w.divider(self.updates_body, pady=6)
            row = ctk.CTkFrame(self.updates_body, fg_color="transparent")
            row.pack(fill="x")
            w.glyph(row, "download", 15).pack(side="left", padx=(0, 12))
            text = ctk.CTkFrame(row, fg_color="transparent")
            text.pack(side="left", fill="x", expand=True)
            w.label(text, update.title, 13, "bold", wraplength=640).pack(anchor="w")
            details = " · ".join(p for p in (update.vendor, update.category, update.date) if p)
            w.muted(text, details).pack(anchor="w")
            if update.size_mb:
                w.muted(row, f"{update.size_mb:g} MB").pack(side="right")

    def _install(self) -> None:
        count = len(self._updates)
        if not self.app.confirm(
            "Install driver updates?",
            f"{count} update(s) will be downloaded and installed in a separate window. Windows will ask for "
            "permission, and you may need to restart afterwards. Backing up your drivers first is a good idea.",
            "Install",
        ):
            return
        if drivers.install_updates():
            self.app.toast("Installer opened — follow the progress in the new window.", "info")
        else:
            self.app.toast("Installation was cancelled.", "error")

    def _backup(self) -> None:
        folder = filedialog.askdirectory(title="Choose where to save the driver backup")
        if not folder:
            return
        if drivers.backup_drivers(folder):
            self.app.toast("Backing up drivers in a new window…", "info")
        else:
            self.app.toast("Backup was cancelled.", "error")
