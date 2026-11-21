from __future__ import annotations

import customtkinter as ctk

from kestrel import formatting as fmt
from kestrel import theme
from kestrel.core import optimizer, shell
from kestrel.core.optimizer import Task
from kestrel.ui import background
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page


class TaskRow(ctk.CTkFrame):
    def __init__(self, master, task: Task, on_run):
        super().__init__(master, fg_color="transparent")
        self.task = task
        self.selected = ctk.BooleanVar(value=not task.destructive)

        ctk.CTkCheckBox(self, text="", variable=self.selected, width=22, checkbox_width=20, checkbox_height=20,
                        corner_radius=6, border_width=2, fg_color=theme.accent(), hover_color=theme.accent_hover(),
                        border_color=theme.FAINT).pack(side="left", padx=(0, 12))
        icon_box = ctk.CTkFrame(self, width=40, height=40, corner_radius=10, fg_color=theme.SURFACE_HI)
        icon_box.pack(side="left")
        icon_box.pack_propagate(False)
        w.glyph(icon_box, task.icon, 16).pack(expand=True)

        text = ctk.CTkFrame(self, fg_color="transparent")
        text.pack(side="left", fill="x", expand=True, padx=14)
        w.label(text, task.title, 14, "bold").pack(anchor="w")
        self.description = w.muted(text, task.description, 12, wraplength=560)
        self.description.pack(anchor="w")

        self.run_button = w.button(self, "Run", lambda: on_run(self), width=76)
        self.run_button.pack(side="right")
        self.status = w.Badge(self, "Ready", theme.resolve(theme.MUTED))
        self.status.pack(side="right", padx=12)

    def set_status(self, text: str, color: str) -> None:
        self.status.set(text, color)


class OptimizerPage(Page):
    title = "Optimizer"
    kicker = "Tune"
    subtitle = "Clean up, free space and get a little more speed out of Windows."

    def build(self) -> None:
        w.button(self.header.actions, "Run selected", self._run_selected, kind="primary", width=130).pack()

        tasks_card = w.Card(self.section(), "Maintenance", "Tick what you want, or run tasks one at a time")
        tasks_card.pack(fill="x")
        self.rows: list[TaskRow] = []
        for index, task in enumerate(optimizer.TASKS):
            if index:
                w.divider(tasks_card.body, pady=12)
            row = TaskRow(tasks_card.body, task, self._run_row)
            row.pack(fill="x")
            self.rows.append(row)

        power = w.Card(self.section(), "Power plan",
                       "High performance keeps clocks up for gaming; Balanced saves energy and heat")
        power.pack(fill="x")
        line = ctk.CTkFrame(power.body, fg_color="transparent")
        line.pack(fill="x")
        self.plan_menu = ctk.CTkOptionMenu(
            line, values=["Loading…"], width=280, height=34, corner_radius=9, font=theme.font(13),
            fg_color=theme.SURFACE_HI, button_color=theme.SURFACE_HI, button_hover_color=theme.BORDER,
            text_color=theme.TEXT, dropdown_font=theme.font(13), command=self._choose_plan,
        )
        self.plan_menu.pack(side="left")
        w.button(line, "Power options", lambda: shell.open_target("powercfg.cpl"),
                 kind="ghost", width=120).pack(side="left", padx=10)
        self._plans: list[optimizer.PowerPlan] = []

    def on_show(self) -> None:
        background.run(self, optimizer.measure_temp, on_done=self._show_temp_size)
        background.run(self, optimizer.recycle_bin_size, on_done=self._show_bin_size)
        background.run(self, optimizer.power_plans, on_done=self._show_plans)

    def _row(self, key: str) -> TaskRow:
        return next(row for row in self.rows if row.task.key == key)

    def _show_temp_size(self, size: int) -> None:
        self._row("temp").set_status(f"{fmt.size(size)} to free", theme.accent())

    def _show_bin_size(self, info: tuple[int, int]) -> None:
        size, count = info
        row = self._row("recycle")
        if count:
            row.set_status(f"{count:,} items · {fmt.size(size)}", theme.accent())
        else:
            row.set_status("Empty", theme.resolve(theme.MUTED))

    def _show_plans(self, plans: list[optimizer.PowerPlan]) -> None:
        self._plans = plans
        if not plans:
            self.plan_menu.configure(values=["Unavailable"])
            self.plan_menu.set("Unavailable")
            return
        self.plan_menu.configure(values=[p.name for p in plans])
        active = next((p for p in plans if p.active), plans[0])
        self.plan_menu.set(active.name)

    def _choose_plan(self, name: str) -> None:
        plan = next((p for p in self._plans if p.name == name), None)
        if plan:
            self.app.perform(lambda: optimizer.set_power_plan(plan.guid))

    # --- Running tasks ----------------------------------------------------

    def _run_row(self, row: TaskRow) -> None:
        if row.task.destructive and not self.app.confirm(
            f"{row.task.title}?", f"{row.task.description} This can't be undone.", "Run it", danger=True
        ):
            return
        self._execute([row])

    def _run_selected(self) -> None:
        chosen = [row for row in self.rows if row.selected.get()]
        if not chosen:
            self.app.toast("Tick at least one task first.", "info")
            return
        if any(row.task.destructive for row in chosen):
            names = ", ".join(row.task.title.lower() for row in chosen if row.task.destructive)
            if not self.app.confirm("Run selected tasks?", f"This will {names}. That can't be undone.",
                                    "Run tasks", danger=True):
                return
        self._execute(chosen)

    def _execute(self, rows: list[TaskRow]) -> None:
        for row in rows:
            row.set_status("Running…", theme.WARNING)
            row.run_button.configure(state="disabled")

            def done(message: str, row=row) -> None:
                row.set_status("Done", theme.SUCCESS)
                row.run_button.configure(state="normal")
                self.app.toast(message)
                if row.task.key in ("temp", "recycle"):
                    self.after(400, self.on_show)

            def failed(error: Exception, row=row) -> None:
                row.set_status("Failed", theme.DANGER)
                row.run_button.configure(state="normal")
                self.app.toast(f"{row.task.title}: {error}", "error")

            background.run(self, row.task.run, on_done=done, on_error=failed)
