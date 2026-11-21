"""Live graphics card stats. NVIDIA cards report through nvidia-smi, which ships
with the driver; other GPUs simply return None and the UI hides the readout."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from kestrel.core import shell

_QUERY = "name,utilization.gpu,temperature.gpu,memory.used,memory.total,power.draw"


@dataclass(frozen=True)
class GpuStats:
    name: str
    usage: float
    temperature: float | None
    memory_used_mb: float
    memory_total_mb: float
    power_watts: float | None

    @property
    def memory_fraction(self) -> float:
        return self.memory_used_mb / self.memory_total_mb if self.memory_total_mb else 0.0


@lru_cache(maxsize=1)
def _nvidia_smi() -> str | None:
    candidates = [
        shutil.which("nvidia-smi"),
        os.path.expandvars(r"%SystemRoot%\System32\nvidia-smi.exe"),
        os.path.expandvars(r"%ProgramFiles%\NVIDIA Corporation\NVSMI\nvidia-smi.exe"),
    ]
    return next((c for c in candidates if c and Path(c).exists()), None)


def _number(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:  # "[N/A]" or "[Not Supported]"
        return None


def parse(line: str) -> GpuStats | None:
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 6:
        return None
    name, usage, temperature, used, total, power = parts[:6]
    return GpuStats(
        name=name,
        usage=_number(usage) or 0.0,
        temperature=_number(temperature),
        memory_used_mb=_number(used) or 0.0,
        memory_total_mb=_number(total) or 0.0,
        power_watts=_number(power),
    )


def read() -> GpuStats | None:
    """Stats for the first NVIDIA GPU, or None. Spawns a process — call off the UI thread."""
    tool = _nvidia_smi()
    if not tool:
        return None
    try:
        output = shell.run([tool, f"--query-gpu={_QUERY}", "--format=csv,noheader,nounits"], timeout=5).stdout
    except (OSError, TimeoutError):
        return None
    first = output.strip().splitlines()[:1]
    return parse(first[0]) if first else None
