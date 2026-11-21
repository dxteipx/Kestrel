"""Live metrics and a static hardware profile."""

from __future__ import annotations

import getpass
import os
import platform
import socket
import time
import winreg
from collections import deque
from dataclasses import dataclass
from typing import Any

import psutil

from kestrel import formatting as fmt
from kestrel.core import shell

SYSTEM_DRIVE = os.environ.get("SystemDrive", "C:") + "\\"


@dataclass(frozen=True)
class Snapshot:
    cpu: float
    cpu_per_core: list[float]
    cpu_freq_mhz: float
    ram_percent: float
    ram_used: int
    ram_total: int
    disk_percent: float
    disk_free: int
    disk_total: int
    net_down: float
    net_up: float
    processes: int
    uptime: float
    battery: Any


class SystemMonitor:
    """Samples the machine and keeps a short rolling history for charts."""

    def __init__(self, history: int = 60) -> None:
        self.capacity = history
        self.cpu_history: deque[float] = deque(maxlen=history)
        self.ram_history: deque[float] = deque(maxlen=history)
        self.down_history: deque[float] = deque(maxlen=history)
        self.up_history: deque[float] = deque(maxlen=history)
        self.latest: Snapshot | None = None

        psutil.cpu_percent(percpu=True)
        self._net = psutil.net_io_counters()
        self._net_time = time.monotonic()
        self._boot = psutil.boot_time()

    def sample(self) -> Snapshot:
        per_core = psutil.cpu_percent(percpu=True)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage(SYSTEM_DRIVE)
        freq = psutil.cpu_freq()

        net = psutil.net_io_counters()
        now = time.monotonic()
        elapsed = max(now - self._net_time, 1e-3)
        down = max(net.bytes_recv - self._net.bytes_recv, 0) / elapsed
        up = max(net.bytes_sent - self._net.bytes_sent, 0) / elapsed
        self._net, self._net_time = net, now

        snapshot = Snapshot(
            cpu=sum(per_core) / len(per_core),
            cpu_per_core=per_core,
            cpu_freq_mhz=freq.current if freq else 0.0,
            ram_percent=memory.percent,
            ram_used=memory.used,
            ram_total=memory.total,
            disk_percent=disk.percent,
            disk_free=disk.free,
            disk_total=disk.total,
            net_down=down,
            net_up=up,
            processes=len(psutil.pids()),
            uptime=time.time() - self._boot,
            battery=psutil.sensors_battery(),
        )
        # Fill the history on the first sample so charts start as a full line.
        repeat = self.capacity if self.latest is None else 1
        for _ in range(repeat):
            self.cpu_history.append(snapshot.cpu)
            self.ram_history.append(snapshot.ram_percent)
            self.down_history.append(down)
            self.up_history.append(up)
        self.latest = snapshot
        return snapshot


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    cpu: float
    memory: int


def top_processes(limit: int = 12) -> list[ProcessInfo]:
    """Busiest processes by CPU, then memory. psutil caches Process objects
    between calls, so cpu_percent() returns a real delta from the second call on."""
    cores = psutil.cpu_count() or 1
    rows: list[ProcessInfo] = []
    for proc in psutil.process_iter(["name", "memory_info"]):
        if proc.pid == 0:
            continue
        try:
            cpu = proc.cpu_percent(None) / cores
            memory = proc.info["memory_info"].rss if proc.info["memory_info"] else 0
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        rows.append(ProcessInfo(proc.pid, proc.info["name"] or "?", cpu, memory))
    rows.sort(key=lambda p: (p.cpu, p.memory), reverse=True)
    return rows[:limit]


def end_process(pid: int) -> None:
    psutil.Process(pid).terminate()


@dataclass(frozen=True)
class Disk:
    mount: str
    label: str
    filesystem: str
    used: int
    total: int

    @property
    def fraction(self) -> float:
        return self.used / self.total if self.total else 0.0


def disks() -> list[Disk]:
    result = []
    for part in psutil.disk_partitions(all=False):
        if "cdrom" in part.opts or not part.fstype:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except OSError:
            continue
        result.append(Disk(part.mountpoint, part.device.rstrip("\\"), part.fstype, usage.used, usage.total))
    return result


def _read_reg(path: str, name: str, default: str = "") -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            return str(winreg.QueryValueEx(key, name)[0]).strip()
    except OSError:
        return default


def windows_version() -> str:
    path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    name = _read_reg(path, "ProductName", platform.platform())
    build = _read_reg(path, "CurrentBuild")
    release = _read_reg(path, "DisplayVersion") or _read_reg(path, "ReleaseId")
    if build.isdigit() and int(build) >= 22000:
        name = name.replace("Windows 10", "Windows 11")
    ubr = _read_reg(path, "UBR")
    full_build = f"{build}.{ubr}" if ubr else build
    return " · ".join(part for part in (name, release, f"build {full_build}") if part)


def cpu_name() -> str:
    return _read_reg(
        r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString", platform.processor()
    )


_HARDWARE_SCRIPT = """
$gpu = @(Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name })
$board = Get-CimInstance Win32_BaseBoard | Select-Object -First 1
$bios = Get-CimInstance Win32_BIOS | Select-Object -First 1
$memory = @(Get-CimInstance Win32_PhysicalMemory)
[pscustomobject]@{
    Gpu = $gpu
    Board = "$($board.Manufacturer) $($board.Product)".Trim()
    Bios = "$($bios.Manufacturer) $($bios.SMBIOSBIOSVersion)".Trim()
    MemorySpeed = ($memory | Measure-Object -Property Speed -Maximum).Maximum
    MemorySticks = $memory.Count
}
"""


def hardware_profile() -> list[tuple[str, str]]:
    """Slow (spawns PowerShell) — call it from a worker thread."""
    memory = psutil.virtual_memory()
    freq = psutil.cpu_freq()
    try:
        extra = shell.powershell_json(_HARDWARE_SCRIPT, timeout=30)[0]
    except Exception:
        extra = {}

    ram = fmt.size(memory.total, 0)
    if extra.get("MemorySpeed"):
        ram += f" · {extra['MemorySticks']} module(s) @ {extra['MemorySpeed']} MT/s"

    gpus = extra.get("Gpu") or []
    if isinstance(gpus, str):
        gpus = [gpus]
    physical = [g for g in gpus if not any(word in g for word in ("Virtual", "Basic Display", "Remote"))]
    gpus = physical or gpus

    cores = f"{psutil.cpu_count(logical=False)} cores · {psutil.cpu_count()} threads"
    if freq and freq.max:
        cores += f" · {freq.max / 1000:.2f} GHz"

    return [
        ("Operating system", windows_version()),
        ("Processor", cpu_name()),
        ("Cores", cores),
        ("Memory", ram),
        ("Graphics", ", ".join(gpus) or "Unknown"),
        ("Motherboard", extra.get("Board") or "Unknown"),
        ("BIOS", extra.get("Bios") or "Unknown"),
        ("Device name", socket.gethostname()),
        ("User", getpass.getuser()),
        ("Architecture", platform.machine()),
    ]
