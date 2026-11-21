from __future__ import annotations

import customtkinter as ctk

from kestrel import icons, theme
from kestrel.content.tutorials import GUIDES, Guide
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page

_LEVEL_COLORS = {"Beginner": theme.SUCCESS, "Intermediate": theme.WARNING, "Advanced": theme.DANGER}


class GuideCard(w.Card):
    def __init__(self, master, guide: Guide, number: int, on_open):
        super().__init__(master, padding=2)
        self.expanded = False

        self.head = ctk.CTkFrame(self.body, fg_color="transparent", corner_radius=14, cursor="hand2")
        self.head.pack(fill="x")
        number_label = ctk.CTkLabel(self.head, text=f"{number:02d}", width=40, font=theme.font(20, "bold"),
                                    text_color=theme.FAINT)
        number_label.pack(side="left", padx=(18, 8), pady=16)
        text = ctk.CTkFrame(self.head, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True)
        w.label(text, guide.title, 15, "bold").pack(anchor="w")
        meta = ctk.CTkFrame(text, fg_color="transparent")
        meta.pack(anchor="w", pady=(2, 0))
        w.muted(meta, f"{guide.summary}  ·  {guide.minutes} min").pack(side="left")

        self.chevron = ctk.CTkLabel(self.head, text=icons.get("chevron_down"), font=icons.font(12),
                                    text_color=theme.MUTED, width=30)
        self.chevron.pack(side="right", padx=(0, 18))
        w.Badge(self.head, guide.level, _LEVEL_COLORS.get(guide.level)).pack(side="right", padx=12)
        w.make_hoverable(self.head, "transparent", theme.SURFACE_HI, on_click=self.toggle)

        self.details = ctk.CTkFrame(self.body, fg_color="transparent")
        for index, step in enumerate(guide.steps, start=1):
            row = ctk.CTkFrame(self.details, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=str(index), width=24, height=24, corner_radius=12,
                         fg_color=theme.tint(theme.accent()), text_color=theme.accent(),
                         font=theme.font(11, "bold")).pack(side="left", anchor="n", padx=(0, 12))
            w.label(row, step, 13, wraplength=720).pack(side="left", fill="x")
        if guide.page:
            w.button(self.details, guide.action or "Open", lambda: on_open(guide.page),
                     kind="primary", width=130).pack(anchor="w", pady=(12, 0), padx=(36, 0))

    def toggle(self) -> None:
        self.expanded = not self.expanded
        if self.expanded:
            self.details.pack(fill="x", padx=(66, 24), pady=(0, 20))
        else:
            self.details.pack_forget()
        self.chevron.configure(text=icons.get("chevron_up" if self.expanded else "chevron_down"))


class TutorialsPage(Page):
    title = "Tutorials"
    kicker = "Learn"
    subtitle = "Short, practical guides for getting the most out of your PC."

    def build(self) -> None:
        for number, guide in enumerate(GUIDES, start=1):
            card = GuideCard(self.section(pady=(0, 10)), guide, number, self.app.navigate)
            card.pack(fill="x")
