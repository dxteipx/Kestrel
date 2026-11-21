"""Finding and launching installed apps, games and game launchers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import winreg
from dataclasses import dataclass
from pathlib import Path

from kestrel.core import shell

_NOISE = (
    "uninstall", "readme", "read me", "release notes", "documentation", "website",
    "license", "manual", "changelog", "help", "support", "what's new",
)


@dataclass(frozen=True)
class AppEntry:
    name: str
    target: str
    kind: str = "path"  # "path" for files/URIs, "shell" for AppsFolder IDs

    def to_dict(self) -> dict:
        return {"name": self.name, "target": self.target, "kind": self.kind}

    @classmethod
    def from_dict(cls, data: dict) -> AppEntry:
        return cls(data["name"], data["target"], data.get("kind", "path"))


def launch(app: AppEntry) -> None:
    if app.kind == "shell":
        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app.target}"])
    else:
        shell.open_target(app.target)


def _is_noise(name: str) -> bool:
    lowered = name.lower()
    return any(word in lowered for word in _NOISE)


def installed_apps() -> list[AppEntry]:
    """Everything in the Start menu, including Microsoft Store apps."""
    try:
        rows = shell.powershell_json("Get-StartApps | Select-Object Name, AppID", timeout=30)
    except Exception:
        rows = []

    apps: dict[str, AppEntry] = {}
    for row in rows:
        name, app_id = row.get("Name"), row.get("AppID")
        if name and app_id and not _is_noise(name):
            apps.setdefault(name.lower(), AppEntry(name, app_id, "shell"))

    if not apps:
        for app in _scan_start_menu():
            apps.setdefault(app.name.lower(), app)

    return sorted(apps.values(), key=lambda a: a.name.lower())


def _scan_start_menu() -> list[AppEntry]:
    roots = [
        Path(os.environ.get("ProgramData", "")) / r"Microsoft\Windows\Start Menu\Programs",
        Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
    ]
    found = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.suffix.lower() in (".lnk", ".url") and "Startup" not in path.parts and not _is_noise(path.stem):
                found.append(AppEntry(path.stem, str(path)))
    return found


WINDOWS_TOOLS: list[AppEntry] = [
    AppEntry("Task Manager", "taskmgr"),
    AppEntry("Device Manager", "devmgmt.msc"),
    AppEntry("Control Panel", "control"),
    AppEntry("Services", "services.msc"),
    AppEntry("Disk Cleanup", "cleanmgr"),
    AppEntry("Event Viewer", "eventvwr.msc"),
    AppEntry("Registry Editor", "regedit"),
    AppEntry("Command Prompt", "cmd"),
    AppEntry("PowerShell", "powershell"),
    AppEntry("Windows Settings", "ms-settings:"),
    AppEntry("Uninstall programs", "appwiz.cpl"),
    AppEntry("Network connections", "ncpa.cpl"),
]


# --- Games ------------------------------------------------------------------

@dataclass(frozen=True)
class Game:
    name: str
    source: str
    target: str
    removable: bool = False


_STEAM_SKIP = re.compile(r"redistributable|steamworks|proton|steam linux runtime|soundtrack|dedicated server", re.I)


def _steam_root() -> Path | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            path = Path(winreg.QueryValueEx(key, "SteamPath")[0])
    except OSError:
        return None
    return path if path.is_dir() else None


def _vdf_value(text: str, key: str) -> str | None:
    match = re.search(rf'"{key}"\s+"([^"]*)"', text, re.IGNORECASE)
    return match.group(1) if match else None


def steam_games() -> list[Game]:
    root = _steam_root()
    if not root:
        return []

    libraries = {root}
    library_file = root / "steamapps" / "libraryfolders.vdf"
    if library_file.exists():
        text = library_file.read_text("utf-8", errors="ignore")
        libraries.update(Path(p.replace("\\\\", "\\")) for p in re.findall(r'"path"\s+"([^"]+)"', text))

    games: dict[str, Game] = {}
    for library in libraries:
        for manifest in (library / "steamapps").glob("appmanifest_*.acf"):
            text = manifest.read_text("utf-8", errors="ignore")
            app_id, name = _vdf_value(text, "appid"), _vdf_value(text, "name")
            if app_id and name and not _STEAM_SKIP.search(name):
                games[app_id] = Game(name, "Steam", f"steam://rungameid/{app_id}")
    return list(games.values())


def epic_games() -> list[Game]:
    manifests = Path(os.environ.get("ProgramData", "")) / r"Epic\EpicGamesLauncher\Data\Manifests"
    if not manifests.is_dir():
        return []
    games = []
    for item in manifests.glob("*.item"):
        try:
            data = json.loads(item.read_text("utf-8"))
        except (OSError, ValueError):
            continue
        if not data.get("bIsApplication", True):
            continue
        app_name = data.get("AppName")
        namespace, catalog = data.get("CatalogNamespace"), data.get("CatalogItemId")
        if not (app_name and data.get("DisplayName")):
            continue
        app_ref = f"{namespace}%3A{catalog}%3A{app_name}" if namespace and catalog else app_name
        games.append(Game(
            data["DisplayName"], "Epic",
            f"com.epicgames.launcher://apps/{app_ref}?action=launch&silent=true",
        ))
    return games


def custom_games(entries: list[dict]) -> list[Game]:
    return [Game(e["name"], "Custom", e["target"], removable=True) for e in entries if e.get("target")]


def all_games(custom: list[dict]) -> list[Game]:
    games = steam_games() + epic_games() + custom_games(custom)
    return sorted(games, key=lambda g: g.name.lower())


def launch_game(game: Game) -> None:
    shell.open_target(game.target)


_LAUNCHERS = {
    "Steam": [r"%ProgramFiles(x86)%\Steam\steam.exe"],
    "Epic Games": [r"%ProgramFiles(x86)%\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe",
                   r"%ProgramFiles%\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"],
    "Battle.net": [r"%ProgramFiles(x86)%\Battle.net\Battle.net Launcher.exe"],
    "EA app": [r"%ProgramFiles%\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe"],
    "Ubisoft Connect": [r"%ProgramFiles(x86)%\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe"],
    "GOG Galaxy": [r"%ProgramFiles(x86)%\GOG Galaxy\GalaxyClient.exe"],
    "Riot Client": [r"C:\Riot Games\Riot Client\RiotClientServices.exe"],
    "Xbox": [],
}


def launchers() -> list[AppEntry]:
    found = []
    steam = _steam_root()
    for name, candidates in _LAUNCHERS.items():
        if name == "Steam" and steam and (steam / "steam.exe").exists():
            found.append(AppEntry(name, str(steam / "steam.exe")))
            continue
        if name == "Xbox":
            found.append(AppEntry(name, "xbox:"))
            continue
        for candidate in candidates:
            path = os.path.expandvars(candidate)
            if os.path.exists(path):
                found.append(AppEntry(name, path))
                break
    return found
