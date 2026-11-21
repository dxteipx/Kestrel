"""Thin wrappers around processes, PowerShell and the Windows shell."""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys

CREATE_NO_WINDOW = 0x08000000
_UTF8_PREAMBLE = "[Console]::OutputEncoding = [Text.Encoding]::UTF8;"


def run(args: list[str], timeout: float = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


def powershell(script: str, timeout: float = 60) -> str:
    command = [
        "powershell", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass",
        "-Command", _UTF8_PREAMBLE + script,
    ]
    return run(command, timeout).stdout


def powershell_json(script: str, timeout: float = 60) -> list[dict]:
    output = powershell(f"& {{ {script} }} | ConvertTo-Json -Depth 4 -Compress", timeout).strip()
    if not output:
        return []
    data = json.loads(output)
    return data if isinstance(data, list) else [data]


def open_target(target: str) -> None:
    """Open a file, folder, URI or shell verb the way Explorer would."""
    os.startfile(target)


def reveal(path: str) -> None:
    subprocess.Popen(["explorer.exe", f"/select,{path}"])


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except OSError:
        return False


def run_elevated(executable: str, params: str = "") -> bool:
    """Start a process through the UAC prompt. Returns False if the user declined."""
    result = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params, None, 1)
    return result > 32


def relaunch_as_admin() -> bool:
    if getattr(sys, "frozen", False):
        params = subprocess.list2cmdline(sys.argv[1:])
    else:
        params = subprocess.list2cmdline([os.path.abspath(sys.argv[0]), *sys.argv[1:]])
    return run_elevated(sys.executable, params)


def restart_app() -> None:
    if getattr(sys, "frozen", False):
        subprocess.Popen([sys.executable, *sys.argv[1:]])
    else:
        subprocess.Popen([sys.executable, os.path.abspath(sys.argv[0]), *sys.argv[1:]])
