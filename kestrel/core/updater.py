"""Self-updates from GitHub Releases.

A release is "newer" when its tag (v1.2.0) beats __version__. Updating means
downloading the release's Kestrel-Setup-*.exe and running it with --update:
the installer waits for Kestrel to close, installs over it and reopens it.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from kestrel import __repo__, __version__

_REPO = re.sub(r"^https://github\.com/", "", __repo__).strip("/")
API_URL = f"https://api.github.com/repos/{_REPO}/releases/latest"
_HEADERS = {"User-Agent": f"Kestrel/{__version__}", "Accept": "application/vnd.github+json"}
DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "kestrel-update"


@dataclass(frozen=True)
class Release:
    version: str
    page: str
    installer_url: str
    installer_name: str
    installer_size: int


def parse_version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3]) or (0,)


def is_newer(version: str) -> bool:
    return parse_version(version) > parse_version(__version__)


def can_self_update() -> bool:
    """Only the installed build can replace itself; from source, use git pull."""
    return bool(getattr(sys, "frozen", False))


def latest_release() -> Release | None:
    """The latest published release, or None if there isn't one yet."""
    request = urllib.request.Request(API_URL, headers=_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise

    installer = next(
        (asset for asset in data.get("assets", [])
         if asset.get("name", "").lower().endswith(".exe") and "setup" in asset["name"].lower()),
        None,
    )
    return Release(
        version=data.get("tag_name", "").lstrip("v"),
        page=data.get("html_url", __repo__),
        installer_url=installer["browser_download_url"] if installer else "",
        installer_name=installer["name"] if installer else "",
        installer_size=installer.get("size", 0) if installer else 0,
    )


def check() -> Release | None:
    """A release newer than the running version, or None if Kestrel is up to date."""
    release = latest_release()
    return release if release and is_newer(release.version) else None


def download(release: Release, progress: Callable[[float], None] | None = None) -> Path:
    if not release.installer_url.startswith("https://github.com/"):
        raise RuntimeError("The release doesn't include an installer.")
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = DOWNLOAD_DIR / release.installer_name
    partial = target.with_suffix(".part")

    request = urllib.request.Request(release.installer_url, headers={"User-Agent": _HEADERS["User-Agent"]})
    with urllib.request.urlopen(request, timeout=30) as response, partial.open("wb") as file:
        total = int(response.headers.get("Content-Length") or release.installer_size or 0)
        received = 0
        while chunk := response.read(256 * 1024):
            file.write(chunk)
            received += len(chunk)
            if progress and total:
                progress(received / total)

    if release.installer_size and partial.stat().st_size != release.installer_size:
        partial.unlink(missing_ok=True)
        raise RuntimeError("The download was incomplete. Try again.")
    partial.replace(target)
    return target


def launch_installer(installer: Path) -> None:
    subprocess.Popen([str(installer), "--update"], cwd=str(installer.parent),
                     creationflags=subprocess.DETACHED_PROCESS)
