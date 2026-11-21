"""Reusable building blocks. Pages are assembled from these and nothing else."""

from __future__ import annotations

import tkinter.font as tkfont
from tkinter import ttk
from typing import Callable, Iterable, Sequence

import customtkinter as ctk

from kestrel import icons, theme
from kestrel.ui import art


# --- Buttons ------------------------------------------------------------------

class GradientButton(ctk.CTkLabel):
    """The primary button: a gradient pill rendered as an image, text on top."""

    def __init__(self, master, text: str, command: Callable | None = None, width: int = 0,
                 height: int = 38, state: str = "normal", colors: tuple[str, str] | None = None, **_):
        self._text, self._command, self._state = text, command, state
        self._min_width, self._height = width, height
        self._colors = colors or theme.accent_pair()
        self._font = theme.font(13, "bold")
        self._hover = False
        super().__init__(master, text=text, font=self._font, compound="center", cursor="hand2",
                         fg_color="transparent", text_color=theme.on_accent())
        self._paint()
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Button-1>", self._click)

    def _width(self) -> int:
        return max(self._min_width, self._font.measure(self._text) + 40)

    def _paint(self) -> None:
        width, radius = self._width(), self._height // 2 - 7
        if self._state == "disabled":
            image = art.flat(width, self._height, radius, theme.resolve(theme.SURFACE_HI))
            super().configure(image=image, text_color=theme.FAINT, cursor="arrow")
        else:
            start, end = self._colors
            image = art.tile(width, self._height, radius, start, end, 0.14 if self._hover else 0.0)
            super().configure(image=image, text_color=theme.on_accent(), cursor="hand2")

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._paint()

    def _click(self, _event) -> None:
        if self._state != "disabled" and self._command:
            self._command()

    def configure(self, require_redraw: bool = False, **kwargs) -> None:
        repaint = False
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            repaint = True
        if "text" in kwargs:
            self._text = kwargs["text"]
            repaint = True
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        super().configure(require_redraw=require_redraw, **kwargs)
        if repaint:
            self._paint()


def button(master, text: str, command: Callable | None = None, kind: str = "secondary", width: int = 0, **kwargs):
    if kind == "primary":
        return GradientButton(master, text, command, width=width, **kwargs)
    styles = {
        "secondary": dict(fg_color=theme.SURFACE_HI, hover_color=theme.SURFACE_HOVER, text_color=theme.TEXT),
        "ghost": dict(fg_color="transparent", hover_color=theme.SURFACE_HI, text_color=theme.MUTED),
        "danger": dict(fg_color=theme.tint(theme.DANGER), hover_color=theme.tint(theme.DANGER, 0.24),
                       text_color=theme.DANGER),
    }
    font = theme.font(13, "bold")
    width = width or font.measure(text) + 36
    return ctk.CTkButton(master, text=text, command=command, width=width, height=38, corner_radius=12,
                         font=font, text_color_disabled=theme.FAINT, **styles[kind], **kwargs)


def icon_button(master, glyph_name: str, command: Callable | None = None, size: int = 34, color=None, **kwargs):
    return ctk.CTkButton(
        master, text=icons.get(glyph_name), command=command, width=size, height=size, corner_radius=10,
        fg_color="transparent", hover_color=theme.SURFACE_HI, text_color=color or theme.MUTED,
        font=icons.font(14), **kwargs,
    )


# --- Text ---------------------------------------------------------------------

def label(master, text: str = "", size: int = 13, weight: str = "normal", color=theme.TEXT, **kwargs):
    kwargs.setdefault("anchor", "w")
    kwargs.setdefault("justify", "left")
    return ctk.CTkLabel(master, text=text, font=theme.font(size, weight), text_color=color, **kwargs)


def muted(master, text: str = "", size: int = 12, **kwargs):
    return label(master, text, size=size, color=theme.MUTED, **kwargs)


def heading(master, text: str, size: int = 17, **kwargs):
    kwargs.setdefault("anchor", "w")
    return ctk.CTkLabel(master, text=text, font=theme.display(size), text_color=theme.TEXT, **kwargs)


def eyebrow(master, text: str, **kwargs):
    kwargs.setdefault("anchor", "w")
    color = (theme.blend(theme.accent(), "#000000", 0.8), theme.accent_end())
    return ctk.CTkLabel(master, text=text.upper(), font=theme.font(11, "bold"), text_color=color, **kwargs)


def glyph(master, name: str, size: int = 16, color=None, **kwargs):
    return ctk.CTkLabel(master, text=icons.get(name), font=icons.font(size),
                        text_color=color or theme.accent_end(), **kwargs)


def icon_chip(master, glyph_name: str, size: int = 40, solid: bool = False, colors: tuple[str, str] | None = None):
    """A rounded square with an icon. Solid chips use the gradient, soft ones a tint."""
    start, end = colors or theme.accent_pair()
    if solid:
        return ctk.CTkLabel(master, text=icons.get(glyph_name), image=art.tile(size, size, round(size * 0.32), start, end),
                            compound="center", font=icons.font(round(size * 0.4)), text_color="#ffffff",
                            fg_color="transparent")
    chip = ctk.CTkLabel(master, text=icons.get(glyph_name), width=size, height=size, corner_radius=round(size * 0.32),
                        fg_color=theme.tint(start, 0.12), text_color=theme.blend(start, end, 0.5),
                        font=icons.font(round(size * 0.4)))
    return chip


def initial_tile(master, text: str, size: int = 40):
    """A gradient square with the first letter of a name — art for apps without an icon."""
    palette = list(theme.ACCENTS.values())
    start, end = palette[sum(map(ord, text)) % len(palette)]
    return ctk.CTkLabel(master, text=(text.strip()[:1] or "?").upper(), compound="center", fg_color="transparent",
                        image=art.tile(size, size, round(size * 0.3), start, end), text_color="#ffffff",
                        font=theme.display(round(size * 0.45)))


class Badge(ctk.CTkLabel):
    def __init__(self, master, text: str, color: str | None = None):
        color = color or theme.accent_end()
        super().__init__(master, text=text, font=theme.font(11, "bold"), text_color=color,
                         fg_color=theme.tint(color), corner_radius=8, height=24, padx=10)

    def set(self, text: str, color: str) -> None:
        self.configure(text=text, text_color=color, fg_color=theme.tint(color))


# --- Containers ---------------------------------------------------------------

class Card(ctk.CTkFrame):
    """A rounded surface with an optional title row. Put content in `.body`."""

    def __init__(self, master, title: str | None = None, subtitle: str | None = None,
                 padding: int = 20, **kwargs):
        kwargs.setdefault("fg_color", theme.SURFACE)
        kwargs.setdefault("corner_radius", 18)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", theme.BORDER)
        super().__init__(master, **kwargs)

        self.actions = None
        if title:
            head = ctk.CTkFrame(self, fg_color="transparent")
            head.pack(fill="x", padx=padding, pady=(padding - 2, 0))
            text = ctk.CTkFrame(head, fg_color="transparent")
            text.pack(side="left", fill="x", expand=True)
            heading(text, title, 17).pack(anchor="w")
            if subtitle:
                muted(text, subtitle).pack(anchor="w")
            self.actions = ctk.CTkFrame(head, fg_color="transparent", width=1, height=1)
            self.actions.pack(side="right")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=padding, pady=(14 if title else padding, padding))


class PageHeader(ctk.CTkFrame):
    def __init__(self, master, title: str, subtitle: str = "", kicker: str = ""):
        super().__init__(master, fg_color="transparent")
        text = ctk.CTkFrame(self, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        if kicker:
            eyebrow(text, kicker).pack(anchor="w")
        heading(text, title, 32).pack(anchor="w")
        self.subtitle = muted(text, subtitle, 13)
        self.subtitle.pack(anchor="w", pady=(2, 0))
        self.actions = ctk.CTkFrame(self, fg_color="transparent", width=1, height=1)
        self.actions.pack(side="right", anchor="s")

    def set_subtitle(self, text: str) -> None:
        self.subtitle.configure(text=text)


class EmptyState(ctk.CTkFrame):
    def __init__(self, master, glyph_name: str, title: str, text: str = ""):
        super().__init__(master, fg_color="transparent")
        icon_chip(self, glyph_name, 52).pack(pady=(26, 12))
        heading(self, title, 17, anchor="center").pack()
        if text:
            muted(self, text, 12, anchor="center", justify="center", wraplength=380).pack(pady=(4, 26))


def key_value(master, key: str, value: str = "—", key_width: int = 150):
    row = ctk.CTkFrame(master, fg_color="transparent")
    row.pack(fill="x", pady=4)
    muted(row, key, 12, width=key_width).pack(side="left", anchor="n")
    value_label = label(row, value, 12, "bold", wraplength=420)
    value_label.pack(side="left", fill="x", expand=True)
    return value_label


def divider(master, pady: int = 8):
    line = ctk.CTkFrame(master, height=1, fg_color=theme.BORDER)
    line.pack(fill="x", pady=pady)
    return line


def make_hoverable(frame: ctk.CTkFrame, normal, hover, on_click: Callable | None = None,
                   event: str = "<Button-1>", skip: Sequence = ()) -> None:
    """Highlight a frame while the pointer is anywhere inside it, children included.
    Widgets in `skip` (usually its own buttons) keep their own click handling."""

    def inside() -> bool:
        under = frame.winfo_containing(*frame.winfo_pointerxy())
        return under is not None and str(under).startswith(str(frame))

    def walk(widget):
        yield widget
        for child in widget.winfo_children():
            if child not in skip:
                yield from walk(child)

    def rest_color():
        return normal() if callable(normal) else normal

    for widget in walk(frame):
        widget.bind("<Enter>", lambda _e: frame.configure(fg_color=hover), add="+")
        widget.bind("<Leave>", lambda _e: None if inside() else frame.configure(fg_color=rest_color()), add="+")
        if on_click:
            widget.bind(event, lambda _e: on_click(), add="+")


# --- Live data ----------------------------------------------------------------

class _Resizing(ctk.CTkFrame):
    """A frame that re-renders its image whenever its width changes."""

    def __init__(self, master, height: int):
        super().__init__(master, fg_color="transparent", height=height)
        self.image_label = ctk.CTkLabel(self, text="", fg_color="transparent", width=1, height=height)
        self.image_label.place(x=0, y=0)
        self.width = 0
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event) -> None:
        width = art.logical(event.width)
        if width != self.width and width > 20:
            self.width = width
            self.redraw()

    def redraw(self) -> None:
        raise NotImplementedError


class GradientBar(_Resizing):
    def __init__(self, master, height: int = 6, warn: bool = True):
        super().__init__(master, height)
        self.bar_height = height
        self.fraction = 0.0
        self.warn = warn

    def set(self, fraction: float) -> None:
        fraction = round(max(0.0, min(fraction, 1.0)), 3)
        if fraction != self.fraction:
            self.fraction = fraction
            self.redraw()

    def redraw(self) -> None:
        if self.width:
            start, end = theme.level_pair(self.fraction) if self.warn else theme.accent_pair()
            self.image_label.configure(image=art.bar(self.width, self.bar_height, self.fraction, start, end,
                                                     theme.resolve(theme.SURFACE_HI)))


class Chart(_Resizing):
    def __init__(self, master, height: int, capacity: int, maximum: float | None = 100.0, grid: bool = False,
                 background=theme.SURFACE):
        super().__init__(master, height)
        self.chart_height, self.capacity, self.maximum = height, capacity, maximum
        self.grid_lines, self.background = grid, background
        self.series: list[art.Series] = []

    def plot(self, series: list[art.Series]) -> None:
        self.series = series
        self.redraw()

    def redraw(self) -> None:
        if self.width and self.series:
            grid = theme.blend(theme.resolve(theme.TEXT), theme.resolve(self.background), 0.12) if self.grid_lines else None
            image = art.area_chart(self.width, self.chart_height, self.series, self.capacity,
                                   theme.resolve(self.background), grid, self.maximum)
            self.image_label.configure(image=image)


class Gauge(ctk.CTkLabel):
    """A ring gauge that eases toward each new value."""

    def __init__(self, master, size: int = 104, caption: str = "", background=theme.SURFACE):
        super().__init__(master, text="", fg_color="transparent")
        self.size, self.caption, self.background = size, caption, background
        self.shown = 0.0
        self.target = 0.0
        self._job = None
        self._render(0.0)

    def set(self, fraction: float) -> None:
        self.target = max(0.0, min(fraction, 1.0))
        if self._job is None:
            self._animate(6)

    def _animate(self, steps: int) -> None:
        self._job = None
        if not self.winfo_exists():
            return
        self.shown += (self.target - self.shown) / max(steps, 1)
        self._render(self.shown)
        if steps > 1 and abs(self.target - self.shown) > 0.002:
            self._job = self.after(40, lambda: self._animate(steps - 1))

    def _render(self, fraction: float) -> None:
        start, end = theme.level_pair(self.target)
        image = art.gauge(self.size, fraction, f"{fraction * 100:.0f}%", self.caption, start, end,
                          theme.resolve(self.background), theme.resolve(theme.TEXT), theme.resolve(theme.MUTED),
                          theme.resolve(theme.SURFACE_HI))
        self.configure(image=image)


class GaugeTile(Card):
    def __init__(self, master, title: str, glyph_name: str):
        super().__init__(master, padding=18)
        self.gauge = Gauge(self.body, 104, title.upper())
        self.gauge.pack(side="left")
        text = ctk.CTkFrame(self.body, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=(16, 0))
        icon_chip(text, glyph_name, 30).pack(anchor="w", pady=(0, 10))
        self.primary = label(text, "—", 14, "bold")
        self.primary.pack(anchor="w")
        self.secondary = muted(text, "", 12)
        self.secondary.pack(anchor="w")

    def set_data(self, fraction: float, primary: str, secondary: str) -> None:
        self.gauge.set(fraction)
        self.primary.configure(text=primary)
        self.secondary.configure(text=secondary)


class ChartTile(Card):
    def __init__(self, master, title: str, glyph_name: str, capacity: int):
        super().__init__(master, padding=18)
        head = ctk.CTkFrame(self.body, fg_color="transparent")
        head.pack(fill="x")
        icon_chip(head, glyph_name, 30).pack(side="left")
        muted(head, title.upper(), 11).pack(side="left", padx=(10, 0))
        self.value = heading(self.body, "—", 26)
        self.value.pack(anchor="w", pady=(10, 0))
        self.caption = muted(self.body, " ", 12)
        self.caption.pack(anchor="w")
        self.chart = Chart(self.body, 40, capacity, maximum=None)
        self.chart.pack(fill="x", pady=(6, 0))

    def set_data(self, value: str, caption: str, history: Iterable[float]) -> None:
        self.value.configure(text=value)
        self.caption.configure(text=caption)
        self.chart.plot([(list(history), *theme.accent_pair())])


class UsageBar(ctk.CTkFrame):
    """Label, value and a gradient bar — used for disks, CPU cores and the sidebar."""

    def __init__(self, master, title: str, compact: bool = False):
        super().__init__(master, fg_color="transparent")
        row = ctk.CTkFrame(master=self, fg_color="transparent")
        row.pack(fill="x")
        label(row, title, 11 if compact else 13, "normal" if compact else "bold").pack(side="left")
        self.detail = muted(row, "", 11 if compact else 12)
        self.detail.pack(side="right")
        self.bar = GradientBar(self, 5 if compact else 8)
        self.bar.pack(fill="x", pady=(5, 0))

    def set(self, fraction: float, detail: str) -> None:
        self.bar.set(fraction)
        self.detail.configure(text=detail)


# --- Tables -------------------------------------------------------------------

_TABLE = "Kestrel.Treeview"


def style_tables() -> None:
    """ttk widgets don't follow CustomTkinter's theme, so restyle them by hand."""
    style = ttk.Style()
    style.theme_use("clam")
    surface, text, muted_color = theme.resolve(theme.SURFACE), theme.resolve(theme.TEXT), theme.resolve(theme.MUTED)
    selected = theme.blend(theme.accent(), surface, 0.3)
    row_height = tkfont.Font(family=theme.FONT_FAMILY, size=10).metrics("linespace") + 16

    style.layout(_TABLE, [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure(_TABLE, background=surface, fieldbackground=surface, foreground=text,
                    rowheight=row_height, borderwidth=0, font=(theme.FONT_FAMILY, 10))
    style.map(_TABLE, background=[("selected", selected)], foreground=[("selected", text)])
    style.configure(f"{_TABLE}.Heading", background=surface, foreground=muted_color, relief="flat",
                    borderwidth=0, font=(theme.FONT_FAMILY, 9, "bold"), padding=(6, 10))
    style.map(f"{_TABLE}.Heading", background=[("active", surface)])


class DataTable(ctk.CTkFrame):
    """A Treeview for long lists. Columns are (key, title, width, anchor)."""

    def __init__(self, master, columns: Sequence[tuple[str, str, int, str]], height: int = 10):
        super().__init__(master, fg_color="transparent")
        self.tree = ttk.Treeview(self, columns=[c[0] for c in columns], show="headings",
                                 style=_TABLE, height=height, selectmode="browse")
        for index, (key, title, width, anchor) in enumerate(columns):
            self.tree.heading(key, text=title.upper(), anchor=anchor)
            self.tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=index == 0)
        self.tree.tag_configure("odd", background=theme.resolve(theme.SURFACE))
        self.tree.tag_configure("even", background=theme.blend(theme.resolve(theme.SURFACE_HI),
                                                               theme.resolve(theme.SURFACE), 0.5))

        scrollbar = ctk.CTkScrollbar(self, command=self.tree.yview, button_color=theme.SURFACE_HI,
                                     button_hover_color=theme.FAINT)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<MouseWheel>", self._scroll)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _scroll(self, event) -> str:
        # Keep the wheel inside the table instead of also scrolling the page behind it.
        self.tree.yview_scroll(-2 if event.delta > 0 else 2, "units")
        return "break"

    def set_rows(self, rows: Sequence[tuple[str, Sequence]]) -> None:
        """Rows are (id, values). Existing rows are updated in place, so the
        selection and scroll position survive a refresh."""
        wanted = {row_id for row_id, _ in rows}
        for row_id in self.tree.get_children():
            if row_id not in wanted:
                self.tree.delete(row_id)
        for index, (row_id, values) in enumerate(rows):
            tag = ("even",) if index % 2 else ("odd",)
            if self.tree.exists(row_id):
                self.tree.item(row_id, values=list(values), tags=tag)
                self.tree.move(row_id, "", index)
            else:
                self.tree.insert("", index, iid=row_id, values=list(values), tags=tag)

    def selected(self) -> str | None:
        selection = self.tree.selection()
        return selection[0] if selection else None


class SearchBox(ctk.CTkEntry):
    def __init__(self, master, on_change: Callable[[str], None], placeholder: str = "Search",
                 width: int = 240, delay: int = 160):
        super().__init__(master, width=width, height=38, corner_radius=12, placeholder_text=placeholder,
                         fg_color=theme.SURFACE_HI, border_color=theme.SURFACE_HI, border_width=1,
                         text_color=theme.TEXT, placeholder_text_color=theme.FAINT, font=theme.font(13))
        self._on_change, self._delay, self._job = on_change, delay, None
        self.bind("<KeyRelease>", self._schedule)
        self.bind("<FocusIn>", lambda _e: self.configure(border_color=theme.accent()))
        self.bind("<FocusOut>", lambda _e: self.configure(border_color=theme.SURFACE_HI))

    def _schedule(self, _event=None) -> None:
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(self._delay, lambda: self._on_change(self.get().strip().lower()))


def switch(master, command: Callable, on: bool):
    widget = ctk.CTkSwitch(master, text="", width=46, switch_width=42, switch_height=22, command=command,
                           progress_color=theme.accent(), button_color="#ffffff", button_hover_color="#f2f2f7",
                           fg_color=("#d3d6e4", "#262a3a"))
    if on:
        widget.select()
    return widget


def option_menu(master, values: list[str], current: str, command: Callable, width: int = 220):
    menu = ctk.CTkOptionMenu(
        master, values=values, width=width, height=38, corner_radius=12, font=theme.font(13),
        fg_color=theme.SURFACE_HI, button_color=theme.SURFACE_HI, button_hover_color=theme.SURFACE_HOVER,
        text_color=theme.TEXT, dropdown_font=theme.font(13), dropdown_fg_color=theme.SURFACE,
        dropdown_hover_color=theme.SURFACE_HI, dropdown_text_color=theme.TEXT, command=command,
    )
    menu.set(current)
    return menu


# --- Dialogs ------------------------------------------------------------------

def confirm(master, title: str, message: str, action: str = "Continue", danger: bool = False) -> bool:
    root = master.winfo_toplevel()
    dialog = ctk.CTkToplevel(root)
    dialog.withdraw()
    dialog.title(title)
    dialog.resizable(False, False)
    dialog.configure(fg_color=theme.SURFACE)
    dialog.transient(root)
    answer = {"value": False}

    def close(value: bool) -> None:
        answer["value"] = value
        dialog.grab_release()
        dialog.destroy()

    frame = ctk.CTkFrame(dialog, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=28, pady=24)
    colors = (theme.WARNING, theme.DANGER) if danger else None
    icon_chip(frame, "warning" if danger else "info", 44, solid=True, colors=colors).pack(anchor="w")
    heading(frame, title, 20).pack(anchor="w", pady=(14, 4))
    muted(frame, message, 13, wraplength=400).pack(anchor="w")

    buttons = ctk.CTkFrame(frame, fg_color="transparent")
    buttons.pack(fill="x", pady=(24, 0))
    GradientButton(buttons, action, lambda: close(True),
                   colors=(theme.DANGER, theme.WARNING) if danger else None).pack(side="right")
    button(buttons, "Cancel", lambda: close(False), kind="ghost").pack(side="right", padx=(0, 8))

    dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
    dialog.bind("<Escape>", lambda _e: close(False))
    dialog.bind("<Return>", lambda _e: close(True))

    dialog.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - dialog.winfo_reqwidth()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - dialog.winfo_reqheight()) // 3
    dialog.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    dialog.deiconify()
    dialog.after(60, lambda: (dialog.lift(), dialog.focus_force(), dialog.grab_set()))
    root.wait_window(dialog)
    return answer["value"]
