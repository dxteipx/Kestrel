"""Keep Kestrel to a single window. A second launch focuses the first one instead."""

from __future__ import annotations

import ctypes
import time
from ctypes import wintypes

_MUTEX_NAME = "dxteipx.kestrel.single-instance"
_ERROR_ALREADY_EXISTS = 183
_SW_RESTORE = 9

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
_kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
_user32 = ctypes.WinDLL("user32")

_handle: int | None = None


def acquire(wait: float = 0.0) -> bool:
    """Claim the single-instance lock. `wait` gives a restarting instance time to exit."""
    global _handle
    deadline = time.monotonic() + wait
    while True:
        handle = _kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        if handle and ctypes.get_last_error() != _ERROR_ALREADY_EXISTS:
            _handle = handle  # held until the process exits
            return True
        if handle:
            _kernel32.CloseHandle(handle)
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.25)


def focus_existing(title: str = "Kestrel") -> None:
    window = _user32.FindWindowW(None, title)
    if window:
        _user32.ShowWindow(window, _SW_RESTORE)
        _user32.SetForegroundWindow(window)
