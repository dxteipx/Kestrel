"""Encrypt small secrets with Windows DPAPI, so only this Windows user can read them."""

from __future__ import annotations

import ctypes
from ctypes import wintypes

_CRYPTPROTECT_UI_FORBIDDEN = 0x1
_ENTROPY = b"dxteipx.kestrel"


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes) -> tuple[_Blob, ctypes.Array]:
    buffer = ctypes.create_string_buffer(data, len(data))
    return _Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def _run(function, data: bytes) -> bytes:
    source, _keep = _blob(data)
    entropy, _keep_entropy = _blob(_ENTROPY)
    result = _Blob()
    if not function(ctypes.byref(source), None, ctypes.byref(entropy), None, None,
                    _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(result)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)


def protect(data: bytes) -> bytes:
    return _run(ctypes.windll.crypt32.CryptProtectData, data)


def unprotect(data: bytes) -> bytes:
    return _run(ctypes.windll.crypt32.CryptUnprotectData, data)
