from __future__ import annotations

import psutil

from kestrel import formatting as fmt
from kestrel.core import system
from kestrel.core.system import Snapshot
from kestrel.ui import background
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page


class SystemPage(Page):
    title = "System & stats"
    kicker = "Overview"
    subtitle = "Your hardware, storage and what's using it."

    def build(self) -> None:
        w.button(self.header.actions, "Copy specs", self._copy_specs).pack()

        top = self.section()
        top.grid_columnconfigure(0, weight=3, uniform="top")
        top.grid_columnconfigure(1, weight=2, uniform="top")

        hardware = w.Card(top, "Hardware")
        hardware.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.hardware_body = hardware.body
        w.muted(self.hardware_body, "Reading your hardware…").pack(anchor="w")
        self._profile: list[tuple[str, str]] = []

        storage = w.Card(top, "Storage")
        storage.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        for disk in system.disks():
            bar = w.UsageBar(storage.body, f"{disk.label}  ·  {disk.filesystem}")
            bar.set(disk.fraction, f"{fmt.size(disk.total - disk.used)} free of {fmt.size(disk.total, 0)}")
            bar.pack(fill="x", pady=(0, 14))

        cores = w.Card(self.section(), "Processor load", "Per logical core")
        cores.pack(fill="x")
        cores.body.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="cores")
        self.core_bars = []
        for index in range(psutil.cpu_count() or 1):
            bar = w.UsageBar(cores.body, f"Core {index}", compact=True)
            bar.grid(row=index // 4, column=index % 4, sticky="ew", padx=8, pady=6)
            self.core_bars.append(bar)

        processes = w.Card(self.section(), "Top processes", "Sorted by CPU, refreshed every two seconds")
        processes.pack(fill="x")
        w.button(processes.actions, "End task", self._end_task, kind="danger").pack()
        self.table = w.DataTable(processes.body, [
            ("name", "Name", 300, "w"),
            ("pid", "PID", 90, "e"),
            ("cpu", "CPU", 90, "e"),
            ("memory", "Memory", 120, "e"),
        ], height=12)
        self.table.pack(fill="both", expand=True)

        self._tick_count = 0
        self._busy = False

    def on_show(self) -> None:
        if not self._profile:
            background.run(self, system.hardware_profile, on_done=self._show_profile)
        self._refresh_processes()

    def _show_profile(self, profile: list[tuple[str, str]]) -> None:
        self._profile = profile
        for child in self.hardware_body.winfo_children():
            child.destroy()
        for key, value in profile:
            w.key_value(self.hardware_body, key, value)

    def _copy_specs(self) -> None:
        if not self._profile:
            self.app.toast("Still reading your hardware — try again in a second.", "info")
            return
        text = "\n".join(f"{key}: {value}" for key, value in self._profile)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.app.toast("Specs copied to clipboard")

    def _refresh_processes(self) -> None:
        if self._busy:
            return
        self._busy = True

        def show(rows) -> None:
            self._busy = False
            self.table.set_rows([
                (str(p.pid), (p.name, p.pid, f"{p.cpu:.1f}%", fmt.size(p.memory))) for p in rows
            ])

        def failed(_error) -> None:
            self._busy = False

        background.run(self, system.top_processes, 30, on_done=show, on_error=failed)

    def _end_task(self) -> None:
        pid = self.table.selected()
        if not pid:
            self.app.toast("Pick a process in the list first.", "info")
            return
        name = self.table.tree.item(pid, "values")[0]
        if self.app.confirm(f"End {name}?", "Unsaved work in this program will be lost.", "End task", danger=True):
            self.app.perform(lambda: system.end_process(int(pid)) or f"Ended {name}",
                             on_done=lambda _r: self._refresh_processes())

    def on_tick(self, snap: Snapshot) -> None:
        for bar, value in zip(self.core_bars, snap.cpu_per_core):
            bar.set(value / 100, fmt.percent(value))
        self._tick_count += 1
        if self._tick_count * self.app.settings.refresh_ms >= 2000:
            self._tick_count = 0
            self._refresh_processes()
