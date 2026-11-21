import base64
import json

from kestrel.core import artwork


def test_epic_image_prefers_wide_key_art(tmp_path, monkeypatch):
    catalog = [{"id": "abc", "keyImages": [
        {"type": "Thumbnail", "url": "https://example.com/thumb.jpg"},
        {"type": "DieselGameBox", "url": "https://example.com/wide.jpg"},
    ]}]
    cache = tmp_path / "catcache.bin"
    cache.write_bytes(base64.b64encode(json.dumps(catalog).encode()))
    monkeypatch.setattr(artwork, "_EPIC_CATALOG", cache)
    artwork._epic_images.cache_clear()
    assert artwork.epic_image_url("abc") == "https://example.com/wide.jpg"
    assert artwork.epic_image_url("missing") is None
    artwork._epic_images.cache_clear()


def test_games_without_art_id_have_no_cover():
    from kestrel.core.launcher import Game
    assert artwork.cover(Game("My Game", "Custom", r"C:\game.exe")) is None
