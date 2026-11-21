from __future__ import annotations

import getpass
import socket
from datetime import datetime

import customtkinter as ctk

from kestrel import formatting as fmt
from kestrel import theme
from kestrel.core import health, launcher, optimizer, startup
from kestrel.core.system import SYSTEM_DRIVE, Snapshot
from kestrel.ui import art, background
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page

_HERO_HEIGHT = 210


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 5:
        return "Up late"
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


class Hero(ctk.CTkFrame):
    """The banner at the top: greeting on the left, aurora and health ring on the right."""

    def __init__(self, master, page: DashboardPage):
        super().__init__(master, fg_color="transparent", height=_HERO_HEIGHT)
        self.background = ctk.CTkLabel(self, text="", fg_color="transparent")
        self.background.place(x=0, y=0)
        self.width = 0
        self.score, self.label = 100, "Excellent"

        content = ctk.CTkFrame(self, fg_color=theme.SURFACE, bg_color=theme.SURFACE, corner_radius=0)
        content.place(x=32, rely=0.5, anchor="w")
        w.eyebrow(content, f"{socket.gethostname()}  ·  Overview").pack(anchor="w")
        w.heading(content, f"{_greeting()}, {getpass.getuser()}", 34).pack(anchor="w", pady=(2, 0))
        self.subtitle = w.muted(content, "Checking how your PC is doing…", 13, wraplength=460)
        self.subtitle.pack(anchor="w", pady=(2, 16))
        buttons = ctk.CTkFrame(content, fg_color="transparent")
        buttons.pack(anchor="w")
        w.button(buttons, "Quick clean", page.quick_clean, kind="primary").pack(side="left")
        w.button(buttons, "Game boost", page.boost).pack(side="left", padx=(10, 0))

        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event) -> None:
        width = art.logical(event.width)
        if width != self.width and width > 200:
            self.width = width
            self.redraw()

    def set_health(self, result: health.Health) -> None:
        tip = result.tips[0] if result.tips else "Everything looks healthy. Nothing needs your attention."
        self.subtitle.configure(text=tip)
        if (result.score, result.label) != (self.score, self.label):
            self.score, self.label = result.score, result.label
            self.redraw()

    def redraw(self) -> None:
        if not self.width:
            return
        start, end = theme.accent_pair()
        image = art.hero(self.width, _HERO_HEIGHT, self.score, self.label, start, end,
                         theme.resolve(theme.SURFACE), theme.resolve(theme.BORDER), theme.is_dark())
        self.background.configure(image=image)


class DashboardPage(Page):
    title = "Dashboard"
    show_header = False

    def build(self) -> None:
        self.hero = Hero(self.section(pady=(10, 18)), self)
        self.hero.pack(fill="x")

        capacity = self.app.monitor.capacity
        tiles = self.section()
        tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="tiles")
        self.cpu = w.GaugeTile(tiles, "CPU", "cpu")
        self.ram = w.GaugeTile(tiles, "Memory", "memory")
        self.disk = w.GaugeTile(tiles, f"Disk {SYSTEM_DRIVE.rstrip(chr(92))}", "disk")
        self.net = w.ChartTile(tiles, "Network", "network", capacity)
        for column, tile in enumerate((self.cpu, self.ram, self.disk, self.net)):
            tile.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 9, 0))

        middle = self.section()
        middle.grid_columnconfigure(0, weight=5, uniform="mid")
        middle.grid_columnconfigure(1, weight=3, uniform="mid")
        self._activity(middle).grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        self._glance(middle).grid(row=0, column=1, sticky="nsew", padx=(9, 0))

        lower = self.section(pady=(0, 28))
        lower.grid_columnconfigure(0, weight=5, uniform="low")
        lower.grid_columnconfigure(1, weight=3, uniform="low")
        self._quick_actions(lower).grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        self.pinned_card = w.Card(lower, "Pinned", "Your favourite apps")
        self.pinned_card.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        w.button(self.pinned_card.actions, "Browse", lambda: self.app.navigate("apps"), kind="ghost").pack()

        self._temp_bytes: int | None = None
        self._startup_enabled: int | None = None

    # --- Sections ---------------------------------------------------------

    def _activity(self, master) -> w.Card:
        card = w.Card(master, "Activity", "Last minute of processor and memory use")
        legend = card.actions
        for name, color in (("CPU", theme.accent()), ("Memory", theme.accent_end())):
            ctk.CTkLabel(legend, text="", width=8, height=8, corner_radius=4, fg_color=color).pack(side="left")
            w.muted(legend, name, 12).pack(side="left", padx=(6, 14))
        self.activity = w.Chart(card.body, 170, self.app.monitor.capacity, maximum=100, grid=True)
        self.activity.pack(fill="x")
        return card

    def _glance(self, master) -> w.Card:
        card = w.Card(master, "At a glance")
        self.glance = {
            "uptime": w.key_value(card.body, "Uptime", key_width=110),
            "processes": w.key_value(card.body, "Processes", key_width=110),
            "power": w.key_value(card.body, "Power", key_width=110),
            "temp": w.key_value(card.body, "Temp files", "Measuring…", 110),
            "startup": w.key_value(card.body, "Startup apps", "Counting…", 110),
            "health": w.key_value(card.body, "Health", "—", 110),
        }
        return card

    def _quick_actions(self, master) -> w.Card:
        card = w.Card(master, "Quick actions", "Common fixes, one click away")
        grid = card.body
        grid.grid_columnconfigure((0, 1, 2), weight=1, uniform="qa")
        actions = [
            ("delete", "Clean temp files", "Free wasted space", self.quick_clean),
            ("globe", "Flush DNS", "Fix pages that won't load", lambda: self.app.perform(optimizer.flush_dns)),
            ("games", "Game boost", "Max power, no capture", self.boost),
            ("drivers", "Check drivers", "Look for updates", lambda: self.app.navigate("drivers")),
            ("startup", "Startup apps", "Speed up boot", lambda: self.app.navigate("startup")),
            ("task", "Task Manager", "See what's running", lambda: launcher.launch(launcher.WINDOWS_TOOLS[0])),
        ]
        for index, (glyph_name, title, hint, command) in enumerate(actions):
            tile = ctk.CTkFrame(grid, fg_color=theme.SURFACE_HI, corner_radius=14, cursor="hand2")
            tile.grid(row=index // 3, column=index % 3, sticky="nsew", padx=5, pady=5)
            w.icon_chip(tile, glyph_name, 38, solid=True).pack(anchor="w", padx=14, pady=(14, 10))
            w.label(tile, title, 13, "bold").pack(anchor="w", padx=14)
            w.muted(tile, hint, 11).pack(anchor="w", padx=14, pady=(0, 14))
            w.make_hoverable(tile, theme.SURFACE_HI, theme.SURFACE_HOVER, on_click=command)
        return card

    # --- Behaviour --------------------------------------------------------

    def on_show(self) -> None:
        self._render_pinned()
        background.run(self, optimizer.measure_temp, on_done=self._show_temp)
        background.run(self, startup.list_items, on_done=self._show_startup)

    def _show_temp(self, size: int) -> None:
        self._temp_bytes = size
        self.glance["temp"].configure(text=f"{fmt.size(size)} to clear")

    def _show_startup(self, items) -> None:
        self._startup_enabled = sum(1 for item in items if item.enabled)
        self.glance["startup"].configure(text=f"{self._startup_enabled} of {len(items)} enabled")

    def _render_pinned(self) -> None:
        for child in self.pinned_card.body.winfo_children():
            child.destroy()
        pinned = [launcher.AppEntry.from_dict(d) for d in self.app.settings.pinned_apps]
        if not pinned:
            w.muted(self.pinned_card.body, "Nothing pinned yet. Open Apps and tap the pin next to anything "
                                           "you use often.", wraplength=300).pack(anchor="w")
            return
        for app in pinned[:6]:
            row = ctk.CTkFrame(self.pinned_card.body, fg_color="transparent", corner_radius=12, cursor="hand2")
            row.pack(fill="x", pady=2)
            w.initial_tile(row, app.name, 30).pack(side="left", padx=(6, 10), pady=6)
            w.label(row, app.name, 13).pack(side="left")
            w.make_hoverable(row, "transparent", theme.SURFACE_HI, on_click=lambda a=app: launcher.launch(a))

    def quick_clean(self) -> None:
        if self.app.confirm("Clean temporary files?", "Old files in your Temp folders will be deleted. "
                                                      "Anything used in the last hour is left alone.", "Clean"):
            self.app.perform(optimizer.clean_temp, on_done=lambda _r: self.on_show())

    def boost(self) -> None:
        if self.app.confirm("Boost for gaming?", "Turns on Game Mode, stops background recording, flushes DNS "
                                                 "and switches to the fastest power plan available.", "Boost"):
            self.app.perform(optimizer.game_boost)

    def on_tick(self, snap: Snapshot) -> None:
        monitor = self.app.monitor
        freq = f"{snap.cpu_freq_mhz / 1000:.2f} GHz" if snap.cpu_freq_mhz else "Processor"
        self.cpu.set_data(snap.cpu / 100, freq, f"{len(snap.cpu_per_core)} threads")
        self.ram.set_data(snap.ram_percent / 100, fmt.size(snap.ram_used),
                          f"of {fmt.size(snap.ram_total, 0)}")
        self.disk.set_data(snap.disk_percent / 100, f"{fmt.size(snap.disk_free)} free",
                           f"of {fmt.size(snap.disk_total, 0)}")
        self.net.set_data(fmt.rate(snap.net_down), f"↑ {fmt.rate(snap.net_up)} upload", monitor.down_history)

        start, end = theme.accent_pair()
        self.activity.plot([
            (list(monitor.ram_history), end, theme.blend(end, "#ffffff", 0.35)),
            (list(monitor.cpu_history), start, theme.blend(start, end, 0.5)),
        ])

        result = health.evaluate(snap, monitor.cpu_history, self._temp_bytes, self._startup_enabled)
        self.hero.set_health(result)
        self.glance["health"].configure(text=f"{result.score} / 100 · {result.label}")
        self.glance["uptime"].configure(text=fmt.duration(snap.uptime))
        self.glance["processes"].configure(text=f"{snap.processes:,} running")
        battery = snap.battery
        if battery is None:
            self.glance["power"].configure(text="Plugged in")
        else:
            state = "charging" if battery.power_plugged else "on battery"
            self.glance["power"].configure(text=f"{battery.percent:.0f}% · {state}")
