"""Palette and typography. Colors are (light, dark) pairs, as CustomTkinter expects."""

from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk

FONT_FAMILY = "Segoe UI"
DISPLAY_FAMILY = "Segoe UI Semibold"
_DISPLAY_CANDIDATES = ("Bahnschrift SemiBold", "Segoe UI Semibold")

BG = ("#f5f6fb", "#07080d")
SIDEBAR = ("#eceef6", "#0a0b12")
SURFACE = ("#ffffff", "#0f1119")
SURFACE_HI = ("#f0f1f8", "#161925")
SURFACE_HOVER = ("#e6e8f2", "#1d2131")
BORDER = ("#e2e4ef", "#1a1e2b")
TEXT = ("#12131c", "#eef0ff")
MUTED = ("#626882", "#8a90a8")
FAINT = ("#a5aac0", "#4b5166")

SUCCESS = "#34d399"
WARNING = "#fbbf24"
DANGER = "#f87171"
DANGER_HOVER = "#ef5d5d"

# Every accent is a two-stop gradient.
ACCENTS: dict[str, tuple[str, str]] = {
    "Aurora": ("#8b5cf6", "#22d3ee"),
    "Bloom": ("#f472b6", "#a78bfa"),
    "Ice": ("#60a5fa", "#c4b5fd"),
    "Mint": ("#34d399", "#2dd4bf"),
    "Lime": ("#a3e635", "#22c55e"),
    "Sunset": ("#fb7185", "#fbbf24"),
}
DEFAULT_ACCENT = "Aurora"
WARNING_GRADIENT = ("#fbbf24", "#f87171")

_accent = ACCENTS[DEFAULT_ACCENT]


def set_accent(name: str) -> None:
    global _accent
    _accent = ACCENTS.get(name, ACCENTS[DEFAULT_ACCENT])


def accent() -> str:
    return _accent[0]


def accent_end() -> str:
    return _accent[1]


def accent_pair() -> tuple[str, str]:
    return _accent


def accent_hover() -> str:
    return blend(_accent[0], "#000000", 0.85)


def on_accent() -> str:
    """Text color that stays readable on top of the accent gradient."""
    r, g, b = _rgb(blend(_accent[0], _accent[1], 0.5))
    return "#0b0c12" if (0.299 * r + 0.587 * g + 0.114 * b) > 165 else "#ffffff"


def detect_fonts(root) -> None:
    global DISPLAY_FAMILY
    available = set(tkfont.families(root))
    DISPLAY_FAMILY = next((name for name in _DISPLAY_CANDIDATES if name in available), FONT_FAMILY)


def is_dark() -> bool:
    return ctk.get_appearance_mode() == "Dark"


def resolve(color: str | tuple[str, str]) -> str:
    """Pick the right half of a (light, dark) pair for plain Tk and Pillow drawing."""
    if isinstance(color, (tuple, list)):
        return color[1] if is_dark() else color[0]
    return color


def _rgb(color: str) -> tuple[int, int, int]:
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def blend(foreground: str, background: str, amount: float) -> str:
    fg, bg = _rgb(foreground), _rgb(background)
    mixed = [round(b + (f - b) * amount) for f, b in zip(fg, bg)]
    return "#" + "".join(f"{c:02x}" for c in mixed)


def tint(color: str, amount: float = 0.14) -> tuple[str, str]:
    """A soft background version of `color` for both light and dark surfaces."""
    return blend(color, SURFACE[0], amount), blend(color, SURFACE[1], amount + 0.06)


def level_pair(fraction: float) -> tuple[str, str]:
    return WARNING_GRADIENT if fraction >= 0.85 else _accent


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def display(size: int = 28) -> ctk.CTkFont:
    return ctk.CTkFont(family=DISPLAY_FAMILY, size=size)
