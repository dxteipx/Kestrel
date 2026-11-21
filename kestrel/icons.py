"""Glyphs from the icon font that ships with Windows 10 and 11."""

from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk

_FAMILIES = ("Segoe Fluent Icons", "Segoe MDL2 Assets")
_family: str | None = None

GLYPHS = {
    "dashboard": "",
    "system": "",
    "optimizer": "",
    "drivers": "",
    "startup": "",
    "apps": "",
    "games": "",
    "tutorials": "",
    "settings": "",
    "cpu": "",
    "memory": "",
    "disk": "",
    "network": "",
    "battery": "",
    "clock": "",
    "search": "",
    "refresh": "",
    "add": "",
    "delete": "",
    "recycle": "",
    "close": "",
    "pin": "",
    "unpin": "",
    "folder": "",
    "open": "",
    "play": "",
    "check": "",
    "info": "",
    "warning": "",
    "shield": "",
    "globe": "",
    "record": "",
    "copy": "",
    "download": "",
    "save": "",
    "heart": "",
    "chevron_down": "",
    "chevron_up": "",
    "chevron_right": "",
    "rocket": "",
    "task": "",
}

_FALLBACK = {
    "chevron_down": "▾", "chevron_up": "▴", "chevron_right": "›",
    "close": "×", "add": "+", "check": "✓", "play": "▶",
}


def detect(root) -> None:
    global _family
    available = set(tkfont.families(root))
    _family = next((name for name in _FAMILIES if name in available), None)


def get(name: str) -> str:
    if _family:
        return GLYPHS.get(name, "")
    return _FALLBACK.get(name, "")


def font(size: int = 16) -> ctk.CTkFont:
    return ctk.CTkFont(family=_family or "Segoe UI Symbol", size=size)
