from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from kestrel import theme
from kestrel.core import launcher, optimizer
from kestrel.core.launcher import AppEntry, Game
from kestrel.ui import art, background
from kestrel.ui import widgets as w
from kestrel.ui.pages.base import Page

_CARD_WIDTH = 232
_COVER = (_CARD_WIDTH - 20, 120)
_SOURCE_COLORS = {"Steam": "#60a5fa", "Epic": "#c4b5fd", "Custom": "#34d399"}


class GameCard(ctk.CTkFrame):
    def __init__(self, master, game: Game, on_play, on_remove):
        super().__init__(master, fg_color=theme.SURFACE_HI, corner_radius=18, width=_CARD_WIDTH)
        palette = list(theme.ACCENTS.values())
        start, end = palette[sum(map(ord, game.name)) % len(palette)]
        cover = art.cover(*_COVER, game.name, start, end, theme.resolve(theme.SURFACE))
        ctk.CTkLabel(self, text="", image=cover, fg_color="transparent").pack(padx=10, pady=(10, 0))

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=14, pady=(12, 14))
        title_row = ctk.CTkFrame(info, fg_color="transparent")
        title_row.pack(fill="x")
        name = game.name if len(game.name) <= 24 else game.name[:22] + "…"
        w.label(title_row, name, 14, "bold").pack(side="left")
        if game.removable:
            w.icon_button(title_row, "close", lambda: on_remove(game), size=26).pack(side="right")

        bottom = ctk.CTkFrame(info, fg_color="transparent")
        bottom.pack(fill="x", pady=(10, 0))
        w.Badge(bottom, game.source, _SOURCE_COLORS.get(game.source)).pack(side="left")
        w.button(bottom, "Play", lambda: on_play(game), kind="primary", width=84, height=34).pack(side="right")


class GamesPage(Page):
    title = "Games"
    kicker = "Library"
    subtitle = "Your Steam, Epic and hand-picked games in one place."

    def build(self) -> None:
        actions = self.header.actions
        w.button(actions, "Game boost", self._boost, width=110).pack(side="left", padx=(0, 8))
        w.button(actions, "Add game", self._add, kind="primary").pack(side="left")

        self.launchers_card = w.Card(self.section(), "Launchers")
        self.launchers_card.pack(fill="x")

        self.library = w.Card(self.section(), "Library")
        self.library.pack(fill="x")
        self.count = w.muted(self.library.actions, "Scanning…")
        self.count.pack(side="left", padx=(0, 12))
        w.SearchBox(self.library.actions, self._filter, "Search games", width=200).pack(side="left")

        self._games: list[Game] = []
        self._query = ""

    def on_show(self) -> None:
        background.run(self, launcher.launchers, on_done=self._show_launchers)
        self._scan()

    def _scan(self) -> None:
        background.run(self, launcher.all_games, self.app.settings.custom_games, on_done=self._show_games)

    def _show_launchers(self, found: list[AppEntry]) -> None:
        body = self.launchers_card.body
        for child in body.winfo_children():
            child.destroy()
        if not found:
            w.muted(body, "No game launchers found.").pack(anchor="w")
            return
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")
        for entry in found:
            w.button(row, entry.name, lambda e=entry: self._open_launcher(e), width=0).pack(side="left", padx=(0, 8))

    def _show_games(self, games: list[Game]) -> None:
        self._games = games
        self._render()

    def _filter(self, query: str) -> None:
        self._query = query
        self._render()

    def _render(self) -> None:
        body = self.library.body
        for child in body.winfo_children():
            child.destroy()
        games = [g for g in self._games if self._query in g.name.lower()]
        self.count.configure(text=f"{len(games)} game{'s' if len(games) != 1 else ''}")

        if not games:
            w.EmptyState(body, "games", "No games yet",
                         "Install something on Steam or Epic, or press “Add game” to pick any .exe.").pack(fill="x")
            return

        columns = max(1, (art.logical(body.winfo_width()) or 980) // (_CARD_WIDTH + 12))
        grid = ctk.CTkFrame(body, fg_color="transparent")
        grid.pack(anchor="w")
        for index, game in enumerate(games):
            card = GameCard(grid, game, self._play, self._remove)
            card.grid(row=index // columns, column=index % columns, padx=(0, 12), pady=(0, 12), sticky="n")

    # --- Actions ----------------------------------------------------------

    def _play(self, game: Game) -> None:
        try:
            launcher.launch_game(game)
        except OSError as error:
            self.app.toast(f"Couldn't start {game.name}: {error.strerror or error}", "error")
            return
        self.app.toast(f"Launching {game.name}…", "info")

    def _open_launcher(self, entry: AppEntry) -> None:
        try:
            launcher.launch(entry)
        except OSError as error:
            self.app.toast(f"Couldn't open {entry.name}: {error.strerror or error}", "error")

    def _add(self) -> None:
        path = filedialog.askopenfilename(title="Pick a game",
                                          filetypes=[("Games", "*.exe *.lnk *.url"), ("All files", "*.*")])
        if not path:
            return
        name = Path(path).stem
        self.app.settings.custom_games.append({"name": name, "target": path})
        self.app.settings.save()
        self.app.toast(f"Added {name}")
        self._scan()

    def _remove(self, game: Game) -> None:
        settings = self.app.settings
        settings.custom_games = [g for g in settings.custom_games if g.get("target") != game.target]
        settings.save()
        self._scan()

    def _boost(self) -> None:
        if self.app.confirm("Boost for gaming?", "Turns on Game Mode, stops background recording, flushes DNS "
                                                 "and switches to the fastest power plan available.", "Boost"):
            self.app.perform(optimizer.game_boost)
