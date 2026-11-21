"""Startup programs, toggled the same way Task Manager does it.

Windows keeps the on/off state for each entry under the StartupApproved keys,
so disabling an item here never deletes the original entry.
"""

from __future__ import annotations

import os
import re
import time
import winreg
from dataclasses import dataclass
from pathlib import Path

_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN32 = r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
_APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"
_VIEW = winreg.KEY_WOW64_64KEY

USER_FOLDER = Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"
COMMON_FOLDER = Path(os.environ.get("ProgramData", "")) / r"Microsoft\Windows\Start Menu\Programs\Startup"


@dataclass
class StartupItem:
    name: str
    display_name: str
    command: str
    scope: str            # "user" or "machine"
    approved_key: str     # "Run", "Run32" or "StartupFolder"
    enabled: bool
    file: Path | None = None

    @property
    def hive(self) -> int:
        return winreg.HKEY_CURRENT_USER if self.scope == "user" else winreg.HKEY_LOCAL_MACHINE

    @property
    def source(self) -> str:
        where = "Startup folder" if self.file else "Registry"
        who = "you" if self.scope == "user" else "all users"
        return f"{where} · {who}"

    @property
    def target(self) -> Path | None:
        if self.file:
            return self.file
        command = self.command.strip()
        if command.startswith('"'):
            executable = command[1:].split('"', 1)[0]
        else:
            match = re.match(r"(.+?\.exe)\b", command, re.IGNORECASE)
            executable = match.group(1) if match else command.split(" ", 1)[0]
        path = Path(executable)
        return path if path.exists() else None


def _values(hive: int, path: str) -> list[tuple[str, object]]:
    try:
        key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ | _VIEW)
    except OSError:
        return []
    values = []
    with key:
        index = 0
        while True:
            try:
                name, data, _ = winreg.EnumValue(key, index)
            except OSError:
                break
            values.append((name, data))
            index += 1
    return values


def _approval_states(hive: int, subkey: str) -> dict[str, bool]:
    states = {}
    for name, data in _values(hive, f"{_APPROVED}\\{subkey}"):
        if isinstance(data, bytes) and data:
            states[name] = data[0] % 2 == 0
    return states


def list_items() -> list[StartupItem]:
    items: list[StartupItem] = []

    registry_sources = (
        (winreg.HKEY_CURRENT_USER, "user", _RUN, "Run"),
        (winreg.HKEY_LOCAL_MACHINE, "machine", _RUN, "Run"),
        (winreg.HKEY_LOCAL_MACHINE, "machine", _RUN32, "Run32"),
    )
    for hive, scope, path, approved in registry_sources:
        states = _approval_states(hive, approved)
        for name, data in _values(hive, path):
            if isinstance(data, str) and data.strip():
                items.append(StartupItem(
                    name=name, display_name=name, command=os.path.expandvars(data),
                    scope=scope, approved_key=approved, enabled=states.get(name, True),
                ))

    folder_sources = (
        (USER_FOLDER, winreg.HKEY_CURRENT_USER, "user"),
        (COMMON_FOLDER, winreg.HKEY_LOCAL_MACHINE, "machine"),
    )
    for folder, hive, scope in folder_sources:
        if not folder.is_dir():
            continue
        states = _approval_states(hive, "StartupFolder")
        for entry in folder.iterdir():
            if entry.name.lower() == "desktop.ini" or entry.is_dir():
                continue
            items.append(StartupItem(
                name=entry.name, display_name=entry.stem, command=str(entry),
                scope=scope, approved_key="StartupFolder",
                enabled=states.get(entry.name, True), file=entry,
            ))

    items.sort(key=lambda item: item.display_name.lower())
    return items


def _filetime_now() -> bytes:
    return int((time.time() + 11_644_473_600) * 10_000_000).to_bytes(8, "little")


def set_enabled(item: StartupItem, enabled: bool) -> None:
    """Raises PermissionError for machine-wide items when not elevated."""
    data = b"\x02" + bytes(11) if enabled else b"\x03" + bytes(3) + _filetime_now()
    path = f"{_APPROVED}\\{item.approved_key}"
    with winreg.CreateKeyEx(item.hive, path, 0, winreg.KEY_SET_VALUE | _VIEW) as key:
        winreg.SetValueEx(key, item.name, 0, winreg.REG_BINARY, data)
    item.enabled = enabled
