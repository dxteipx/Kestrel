"""One-click maintenance tasks. Every task returns a short, human summary."""

from __future__ import annotations

import ctypes
import os
import re
import subprocess
import time
import winreg
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from kestrel import formatting as fmt
from kestrel.core import shell

_RECENT_SECONDS = 3600  # leave files touched in the last hour alone


# --- Temporary files ----------------------------------------------------------

def temp_folders() -> list[Path]:
    folders = {Path(os.environ.get("TEMP", "")), Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp"}
    return [f for f in folders if f.is_dir()]


def _stale_files(folder: Path):
    cutoff = time.time() - _RECENT_SECONDS
    for root, _dirs, files in os.walk(folder, onerror=lambda _e: None):
        for name in files:
            path = os.path.join(root, name)
            try:
                stat = os.stat(path)
            except OSError:
                continue
            if stat.st_mtime < cutoff:
                yield path, stat.st_size


def measure_temp() -> int:
    return sum(size for folder in temp_folders() for _path, size in _stale_files(folder))


def clean_temp() -> str:
    freed = removed = skipped = 0
    for folder in temp_folders():
        for path, size in list(_stale_files(folder)):
            try:
                os.remove(path)
            except OSError:
                skipped += 1
                continue
            freed += size
            removed += 1
        for root, dirs, _files in os.walk(folder, topdown=False):
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except OSError:
                    pass
    note = f", {skipped:,} in use" if skipped else ""
    return f"Freed {fmt.size(freed)} · {removed:,} files removed{note}"


# --- Recycle Bin --------------------------------------------------------------

class _RecycleBinInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("i64Size", ctypes.c_longlong), ("i64NumItems", ctypes.c_longlong)]


def recycle_bin_size() -> tuple[int, int]:
    info = _RecycleBinInfo(cbSize=ctypes.sizeof(_RecycleBinInfo))
    ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
    return info.i64Size, info.i64NumItems


def empty_recycle_bin() -> str:
    size, count = recycle_bin_size()
    if not count:
        return "Recycle Bin was already empty"
    no_confirm, no_progress, no_sound = 0x1, 0x2, 0x4
    ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, no_confirm | no_progress | no_sound)
    return f"Emptied {count:,} items · {fmt.size(size)}"


# --- Network & shell ----------------------------------------------------------

def flush_dns() -> str:
    result = shell.run(["ipconfig", "/flushdns"])
    if result.returncode != 0:
        raise RuntimeError("Windows refused to flush the DNS cache")
    return "DNS cache flushed"


def restart_explorer() -> str:
    shell.run(["taskkill", "/f", "/im", "explorer.exe"])
    time.sleep(0.6)
    subprocess.Popen(["explorer.exe"])
    return "Windows Explorer restarted"


# --- Gaming -------------------------------------------------------------------

def _set_dword(path: str, name: str, value: int) -> None:
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)


def enable_game_mode() -> str:
    _set_dword(r"Software\Microsoft\GameBar", "AutoGameModeEnabled", 1)
    _set_dword(r"Software\Microsoft\GameBar", "AllowAutoGameMode", 1)
    return "Game Mode is on"


def disable_background_capture() -> str:
    _set_dword(r"System\GameConfigStore", "GameDVR_Enabled", 0)
    _set_dword(r"Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0)
    return "Background recording is off"


# --- Power plans --------------------------------------------------------------

ULTIMATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"
HIGH_PERFORMANCE = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"


@dataclass(frozen=True)
class PowerPlan:
    guid: str
    name: str
    active: bool


def power_plans() -> list[PowerPlan]:
    # powercfg output is localized, so only rely on the GUID, the parentheses and the "*".
    output = shell.run(["powercfg", "/list"]).stdout
    pattern = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s+\((.+?)\)\s*(\*)?", re.I)
    return [PowerPlan(m.group(1).lower(), m.group(2), bool(m.group(3))) for m in pattern.finditer(output)]


def set_power_plan(guid: str) -> str:
    if shell.run(["powercfg", "/setactive", guid]).returncode != 0:
        raise RuntimeError("Could not switch power plan")
    name = next((p.name for p in power_plans() if p.guid == guid), "plan")
    return f"Switched to {name}"


def fastest_power_plan() -> PowerPlan | None:
    plans = {p.guid: p for p in power_plans()}
    return plans.get(ULTIMATE) or plans.get(HIGH_PERFORMANCE)


def game_boost() -> str:
    done = [enable_game_mode(), disable_background_capture(), flush_dns()]
    plan = fastest_power_plan()
    if plan and not plan.active:
        done.append(set_power_plan(plan.guid))
    return " · ".join(done)


# --- Task catalogue -----------------------------------------------------------

@dataclass(frozen=True)
class Task:
    key: str
    title: str
    description: str
    icon: str
    run: Callable[[], str]
    destructive: bool = False


TASKS: list[Task] = [
    Task("temp", "Clear temporary files",
         "Removes leftovers from installers and apps. Files used in the last hour are kept.",
         "delete", clean_temp, destructive=True),
    Task("recycle", "Empty Recycle Bin",
         "Permanently deletes everything currently in the Recycle Bin.",
         "recycle", empty_recycle_bin, destructive=True),
    Task("dns", "Flush DNS cache",
         "Fixes sites that won't load after a network or DNS change.",
         "globe", flush_dns),
    Task("gamemode", "Turn on Game Mode",
         "Lets Windows prioritise the game you're playing over background work.",
         "games", enable_game_mode),
    Task("capture", "Stop background recording",
         "Disables Xbox Game Bar's always-on capture, which costs FPS on weaker PCs.",
         "record", disable_background_capture),
    Task("explorer", "Restart Windows Explorer",
         "Fixes a frozen taskbar, Start menu or desktop without rebooting.",
         "refresh", restart_explorer),
]
