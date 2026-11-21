"""Cover art for the Games page.

Steam: the wide header image, from Steam's CDN, falling back to the copy the
Steam client keeps in its library cache. Epic: the landscape key art listed in
the Epic launcher's local catalog cache. Everything is cached in
%APPDATA%\\Kestrel\\covers so each image is only fetched once.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

from PIL import Image

from kestrel import __version__
from kestrel.config import CONFIG_DIR
from kestrel.core import launcher
from kestrel.core.launcher import Game

COVERS_DIR = CONFIG_DIR / "covers"
_STEAM_URLS = (
    "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{id}/header.jpg",
    "https://cdn.akamai.steamstatic.com/steam/apps/{id}/header.jpg",
)
_STEAM_LOCAL = ("header.jpg", "library_hero.jpg", "library_600x900.jpg")
_EPIC_CATALOG = Path(os.environ.get("ProgramData", "")) / r"Epic\EpicGamesLauncher\Data\Catalog\catcache.bin"
_EPIC_TYPES = ("DieselGameBox", "OfferImageWide", "Featured", "DieselGameBoxTall", "Thumbnail")


def _valid_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except (OSError, SyntaxError):
        return False


def _download(url: str, target: Path) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": f"Kestrel/{__version__}"})
    partial = target.with_suffix(".part")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            partial.write_bytes(response.read())
    except (urllib.error.URLError, TimeoutError, OSError):
        partial.unlink(missing_ok=True)
        return False
    if not _valid_image(partial):
        partial.unlink(missing_ok=True)
        return False
    partial.replace(target)
    return True


def _steam_store_header(app_id: str) -> str | None:
    """Newer games keep their header under a hashed path; the store API knows it."""
    url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&filters=basic"
    request = urllib.request.Request(url, headers={"User-Agent": f"Kestrel/{__version__}"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    details = (data.get(app_id) or {}).get("data") or {}
    return details.get("header_image")


def _steam_local(app_id: str) -> Path | None:
    root = launcher._steam_root()
    if not root:
        return None
    folder = root / "appcache" / "librarycache" / app_id
    for name in _STEAM_LOCAL:
        if (folder / name).is_file():
            return folder / name
    # Newer Steam clients name files by hash: pick the widest landscape picture.
    best, best_area = None, 0
    for candidate in folder.glob("*.jpg") if folder.is_dir() else ():
        try:
            with Image.open(candidate) as image:
                width, height = image.size
        except OSError:
            continue
        if width > height and width * height > best_area:
            best, best_area = candidate, width * height
    return best


@lru_cache(maxsize=1)
def _epic_images() -> dict[str, dict[str, str]]:
    """Catalog item id → {image type: url}, read from the Epic launcher's cache."""
    try:
        items = json.loads(base64.b64decode(_EPIC_CATALOG.read_bytes()))
    except (OSError, ValueError):
        return {}
    return {item["id"]: {image["type"]: image["url"] for image in item.get("keyImages", []) if image.get("url")}
            for item in items if isinstance(item, dict) and item.get("id")}


def epic_image_url(catalog_id: str) -> str | None:
    images = _epic_images().get(catalog_id, {})
    return next((images[kind] for kind in _EPIC_TYPES if kind in images), None)


def cover(game: Game) -> Path | None:
    """A local image file for the game, downloading it once if needed. Slow — call off the UI thread."""
    if not game.art_id:
        return None
    store, _, identifier = game.art_id.partition(":")
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    cached = COVERS_DIR / f"{store}_{identifier}.jpg"
    if cached.is_file():
        return cached

    if store == "steam":
        if any(_download(url.format(id=identifier), cached) for url in _STEAM_URLS):
            return cached
        header = _steam_store_header(identifier)
        if header and _download(header, cached):
            return cached
        return _steam_local(identifier)
    if store == "epic":
        url = epic_image_url(identifier)
        if url and _download(url, cached):
            return cached
    return None
