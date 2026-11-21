"""User preferences, stored as JSON in %APPDATA%\\Kestrel."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "Kestrel"
CONFIG_FILE = CONFIG_DIR / "settings.json"


@dataclass
class Settings:
    appearance: str = "Dark"
    accent: str = "Aurora"
    refresh_ms: int = 1000
    start_page: str = "dashboard"
    confirm_actions: bool = True
    auto_update: bool = True
    last_update_check: str = ""
    last_version: str = ""
    pinned_apps: list[dict] = field(default_factory=list)
    custom_apps: list[dict] = field(default_factory=list)
    custom_games: list[dict] = field(default_factory=list)

    @classmethod
    def load(cls) -> Settings:
        try:
            data = json.loads(CONFIG_FILE.read_text("utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in known})

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), "utf-8")

    def reset(self) -> None:
        for f in fields(self):
            setattr(self, f.name, getattr(Settings(), f.name))
        self.save()
