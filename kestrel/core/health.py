"""A single 0–100 score that sums up how the PC is doing, plus what to fix first."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from kestrel import formatting as fmt
from kestrel.core.system import SYSTEM_DRIVE, Snapshot

_GB = 1024 ** 3


@dataclass(frozen=True)
class Health:
    score: int
    label: str
    tips: list[str]


def evaluate(snapshot: Snapshot, cpu_history: Iterable[float], temp_bytes: int | None = None,
             startup_enabled: int | None = None) -> Health:
    score = 100.0
    tips: list[tuple[float, str]] = []

    history = list(cpu_history) or [snapshot.cpu]
    cpu = sum(history) / len(history)
    if cpu > 70:
        penalty = (cpu - 70) * 0.6
        score -= penalty
        tips.append((penalty, f"CPU has averaged {cpu:.0f}% — check Top processes on the System page."))

    if snapshot.ram_percent > 70:
        penalty = (snapshot.ram_percent - 70) * 0.8
        score -= penalty
        tips.append((penalty, f"Memory is at {snapshot.ram_percent:.0f}%. Closing a few apps will help."))

    if snapshot.disk_percent > 80:
        penalty = (snapshot.disk_percent - 80) * 1.2
        score -= penalty
        drive = SYSTEM_DRIVE.rstrip("\\")
        tips.append((penalty, f"Drive {drive} is {snapshot.disk_percent:.0f}% full — time for a cleanup."))

    if temp_bytes is not None and temp_bytes > _GB:
        penalty = 6 if temp_bytes < 5 * _GB else 10
        score -= penalty
        tips.append((penalty, f"{fmt.size(temp_bytes)} of temporary files can be cleared."))

    if startup_enabled is not None and startup_enabled > 8:
        penalty = min((startup_enabled - 8) * 1.5, 10)
        score -= penalty
        tips.append((penalty, f"{startup_enabled} apps launch with Windows. Trimming them speeds up boot."))

    final = max(0, min(100, round(score)))
    if final >= 85:
        label = "Excellent"
    elif final >= 70:
        label = "Good"
    elif final >= 50:
        label = "Fair"
    else:
        label = "Struggling"
    return Health(final, label, [text for _, text in sorted(tips, reverse=True)])
