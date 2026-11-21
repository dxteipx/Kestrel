from kestrel.core import updater


def test_parse_version_ignores_prefix_and_suffix():
    assert updater.parse_version("v1.2.3") == (1, 2, 3)
    assert updater.parse_version("1.10") == (1, 10)
    assert updater.parse_version("v2.0.0-beta") == (2, 0, 0)


def test_versions_compare_numerically(monkeypatch):
    monkeypatch.setattr(updater, "__version__", "1.9.0")
    assert updater.is_newer("1.10.0")
    assert not updater.is_newer("1.9.0")
    assert not updater.is_newer("v1.8.9")


def test_api_url_points_at_the_repository():
    assert updater.API_URL.startswith("https://api.github.com/repos/dxteipx/")
    assert updater.API_URL.endswith("/releases/latest")
