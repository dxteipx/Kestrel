from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from kestrel import theme
from kestrel.core.system import Snapshot
from kestrel.ui import widgets as w

if TYPE_CHECKING:
    from kestrel.app import KestrelApp


class Page(ctk.CTkFrame):
    """A screen in the app. Subclasses fill `self.body` in `build()`.

    Pages are created the first time they're opened and then kept alive, so
    `on_show` is the place for anything that should refresh on each visit.
    """

    title = ""
    subtitle = ""
    kicker = ""
    show_header = True

    def __init__(self, master, app: KestrelApp):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.body = ctk.CTkScrollableFrame(
            self, fg_color="transparent", scrollbar_button_color=theme.SURFACE_HI,
            scrollbar_button_hover_color=theme.FAINT,
        )
        self.body.pack(fill="both", expand=True, padx=(26, 6), pady=(20, 0))

        self.header = w.PageHeader(self.body, self.title, self.subtitle, self.kicker)
        if self.show_header:
            self.header.pack(fill="x", padx=(6, 16), pady=(10, 24))
        self.build()

    def section(self, **pack) -> ctk.CTkFrame:
        """A transparent row inside the page body with consistent margins."""
        frame = ctk.CTkFrame(self.body, fg_color="transparent")
        pack.setdefault("fill", "x")
        pack.setdefault("pady", (0, 18))
        frame.pack(padx=(6, 16), **pack)
        return frame

    def build(self) -> None:
        raise NotImplementedError

    def on_show(self) -> None:
        pass

    def on_tick(self, snapshot: Snapshot) -> None:
        pass
