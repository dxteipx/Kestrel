"""Installed drivers and driver updates published through Windows Update."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from kestrel.core import shell


@dataclass(frozen=True)
class Driver:
    device: str
    category: str
    vendor: str
    version: str
    date: str


@dataclass(frozen=True)
class DriverUpdate:
    title: str
    vendor: str
    category: str
    date: str
    size_mb: float


_INSTALLED_SCRIPT = """
Get-CimInstance Win32_PnPSignedDriver |
    Where-Object { $_.DeviceName -and $_.DriverVersion } |
    Select-Object DeviceName, DeviceClass, Manufacturer, DriverVersion,
        @{ n = 'DriverDate'; e = { if ($_.DriverDate) { $_.DriverDate.ToString('yyyy-MM-dd') } } }
"""

_SEARCH_SCRIPT = """
$searcher = (New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher()
$result = $searcher.Search("IsInstalled=0 and Type='Driver'")
@($result.Updates | ForEach-Object {
    [pscustomobject]@{
        Title = $_.Title
        Vendor = $_.DriverManufacturer
        Class = $_.DriverClass
        Date = if ($_.DriverVerDate) { $_.DriverVerDate.ToString('yyyy-MM-dd') } else { '' }
        SizeMB = [math]::Round($_.MaxDownloadSize / 1MB, 1)
    }
})
"""

_INSTALL_SCRIPT = """
$Host.UI.RawUI.WindowTitle = 'Kestrel - Driver updates'
Write-Host ''
Write-Host '  Kestrel is installing driver updates from Windows Update.' -ForegroundColor Cyan
Write-Host '  Keep this window open until it finishes.'
Write-Host ''
$session = New-Object -ComObject Microsoft.Update.Session
$result = $session.CreateUpdateSearcher().Search("IsInstalled=0 and Type='Driver'")
if ($result.Updates.Count -eq 0) {
    Write-Host '  Every driver is already up to date.' -ForegroundColor Green
    Read-Host '  Press Enter to close'
    exit
}
$queue = New-Object -ComObject Microsoft.Update.UpdateColl
foreach ($update in $result.Updates) {
    if ($update.EulaAccepted) {
        Write-Host "  + $($update.Title)"
        [void]$queue.Add($update)
    } else {
        Write-Host "  - Skipped (needs license approval): $($update.Title)" -ForegroundColor Yellow
    }
}
if ($queue.Count -gt 0) {
    Write-Host ''
    Write-Host '  Downloading...'
    $downloader = $session.CreateUpdateDownloader()
    $downloader.Updates = $queue
    [void]$downloader.Download()
    Write-Host '  Installing...'
    $installer = $session.CreateUpdateInstaller()
    $installer.Updates = $queue
    $outcome = $installer.Install()
    Write-Host ''
    Write-Host "  Done. Result code: $($outcome.ResultCode)" -ForegroundColor Green
    if ($outcome.RebootRequired) { Write-Host '  Restart your PC to finish.' -ForegroundColor Yellow }
}
Write-Host ''
Read-Host '  Press Enter to close'
"""


def installed_drivers() -> list[Driver]:
    rows = shell.powershell_json(_INSTALLED_SCRIPT, timeout=90)
    drivers = [
        Driver(
            device=row.get("DeviceName") or "",
            category=row.get("DeviceClass") or "Other",
            vendor=row.get("Manufacturer") or "",
            version=row.get("DriverVersion") or "",
            date=row.get("DriverDate") or "",
        )
        for row in rows
    ]
    drivers.sort(key=lambda d: (d.category.lower(), d.device.lower()))
    return drivers


def available_updates() -> list[DriverUpdate]:
    """Query Windows Update for pending drivers. Can take a minute or two."""
    rows = shell.powershell_json(_SEARCH_SCRIPT, timeout=600)
    return [
        DriverUpdate(
            title=row.get("Title") or "",
            vendor=row.get("Vendor") or "",
            category=row.get("Class") or "",
            date=row.get("Date") or "",
            size_mb=float(row.get("SizeMB") or 0),
        )
        for row in rows
    ]


def _write_script(name: str, body: str) -> Path:
    path = Path(tempfile.gettempdir()) / name
    path.write_text(body, encoding="utf-8-sig")
    return path


def install_updates() -> bool:
    """Open an elevated PowerShell window that downloads and installs every update."""
    script = _write_script("kestrel-driver-update.ps1", _INSTALL_SCRIPT)
    return shell.run_elevated("powershell.exe", f'-NoProfile -ExecutionPolicy Bypass -File "{script}"')


def backup_drivers(destination: str) -> bool:
    """Export every third-party driver package with pnputil (needs elevation)."""
    return shell.run_elevated("cmd.exe", f'/c pnputil /export-driver * "{destination}" & pause')
