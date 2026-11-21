"""Left navigation rail."""

from __future__ import annotations

from typing import Callable, Sequence

import customtkinter as ctk

from kestrel import __author__, __version__, icons, theme
from kestrel import formatting as fmt
from kestrel.core.system import Snapshot
from kestrel.ui import art
from kestrel.ui import widgets as w

Entry = tuple[str, str, str]


class NavItem(ctk.CTkFrame):
    def __init__(self, master, key: str, title: str, glyph_name: str, on_select: Callable[[str], None]):
        super().__init__(master, fg_color="transparent", corner_radius=12, height=38, cursor="hand2")
        self.key = key
        self._active = False

        self.indicator = ctk.CTkLabel(self, text="", width=4, height=20, fg_color="transparent")
        self.indicator.pack(side="left", padx=(2, 0))
        self.icon = ctk.CTkLabel(self, text=icons.get(glyph_name), font=icons.font(15), width=22,
                                 text_color=theme.MUTED)
        self.icon.pack(side="left", padx=(10, 12))
        self.text = ctk.CTkLabel(self, text=title, font=theme.font(13), text_color=theme.MUTED, anchor="w")
        self.text.pack(side="left", fill="x", expand=True, pady=7)

        w.make_hoverable(self, lambda: theme.SURFACE_HI if self._active else "transparent", theme.SURFACE_HI,
                         on_click=lambda: on_select(self.key))

    def set_active(self, active: bool) -> None:
        self._active = active
        self.configure(fg_color=theme.SURFACE_HI if active else "transparent")
        start, end = theme.accent_pair()
        self.indicator.configure(image=art.tile(4, 20, 2, start, end) if active else art.blank(4, 20))
        self.icon.configure(text_color=theme.accent_end() if active else theme.MUTED)
        self.text.configure(text_color=theme.TEXT if active else theme.MUTED,
                            font=theme.font(13, "bold" if active else "normal"))


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, groups: Sequence[tuple[str, Sequence[Entry]]], footer_items: Sequence[Entry],
                 on_select: Callable[[str], None], is_admin: bool = False):
        super().__init__(master, fg_color=theme.SIDEBAR, corner_radius=0, width=248)
        self.pack_propagate(False)
        self.items: dict[str, NavItem] = {}

        self._brand().pack(fill="x", padx=20, pady=(22, 12))

        for group, entries in groups:
            w.label(self, group.upper(), 10, "bold", color=theme.FAINT).pack(fill="x", padx=26, pady=(10, 2))
            for key, title, glyph_name in entries:
                self._add(self, key, title, glyph_name, on_select).pack(fill="x", padx=12, pady=1)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=12, pady=(0, 16))
        for key, title, glyph_name in footer_items:
            self._add(footer, key, title, glyph_name, on_select).pack(fill="x", pady=1)

        live = ctk.CTkFrame(footer, fg_color=theme.SURFACE, corner_radius=14, border_width=1,
                            border_color=theme.BORDER)
        live.pack(fill="x", pady=(10, 0))
        inner = ctk.CTkFrame(live, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)
        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x", pady=(0, 6))
        dot = ctk.CTkLabel(head, text="", width=8, height=8, corner_radius=4, fg_color=theme.SUCCESS)
        dot.pack(side="left")
        w.label(head, "Live", 11, "bold").pack(side="left", padx=(6, 0))
        w.muted(head, "Admin" if is_admin else "Standard", 11).pack(side="right")
        self.cpu = w.UsageBar(inner, "CPU", compact=True)
        self.cpu.pack(fill="x", pady=(0, 4))
        self.ram = w.UsageBar(inner, "Memory", compact=True)
        self.ram.pack(fill="x")

        w.muted(footer, f"v{__version__}  ·  crafted by {__author__}", 11).pack(anchor="w", padx=12, pady=(10, 0))

    def _brand(self) -> ctk.CTkFrame:
        brand = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(brand, text="", image=art.logo(38, *theme.accent_pair())).pack(side="left")
        text = ctk.CTkFrame(brand, fg_color="transparent")
        text.pack(side="left", padx=(12, 0))
        w.heading(text, "Kestrel", 20).pack(anchor="w")
        w.muted(text, "PC control center", 11).pack(anchor="w")
        return brand

    def _add(self, master, key: str, title: str, glyph_name: str, on_select) -> NavItem:
        item = NavItem(master, key, title, glyph_name, on_select)
        self.items[key] = item
        return item

    def set_active(self, key: str) -> None:
        for item_key, item in self.items.items():
            item.set_active(item_key == key)

    def on_tick(self, snap: Snapshot) -> None:
        self.cpu.set(snap.cpu / 100, fmt.percent(snap.cpu))
        self.ram.set(snap.ram_percent / 100, fmt.percent(snap.ram_percent))
