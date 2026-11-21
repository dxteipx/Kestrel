"""Human-friendly formatting for sizes, rates and durations."""

from __future__ import annotations

_UNITS = ("B", "KB", "MB", "GB", "TB")


def size(num_bytes: float, precision: int = 1) -> str:
    value = float(num_bytes)
    for unit in _UNITS:
        if abs(value) < 1024 or unit == _UNITS[-1]:
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.{precision}f} {unit}"
        value /= 1024
    return f"{value:.{precision}f} TB"


def rate(bytes_per_second: float) -> str:
    return f"{size(bytes_per_second)}/s"


def duration(seconds: float) -> str:
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes = seconds // 60
    if days:
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def percent(value: float) -> str:
    return f"{value:.0f}%"
