from kestrel.core import launcher

MANIFEST = '''
"AppState"
{
    "appid"     "730"
    "name"      "Counter-Strike 2"
    "installdir" "Counter-Strike Global Offensive"
}
'''


def test_reads_values_from_steam_manifests():
    assert launcher._vdf_value(MANIFEST, "appid") == "730"
    assert launcher._vdf_value(MANIFEST, "name") == "Counter-Strike 2"
    assert launcher._vdf_value(MANIFEST, "missing") is None


def test_skips_tools_that_are_not_games():
    assert launcher._STEAM_SKIP.search("Steamworks Common Redistributables")
    assert not launcher._STEAM_SKIP.search("Counter-Strike 2")


def test_custom_games_are_removable():
    games = launcher.custom_games([{"name": "My Game", "target": r"C:\Games\game.exe"}, {"name": "Broken"}])
    assert [g.name for g in games] == ["My Game"]
    assert games[0].removable and games[0].source == "Custom"


def test_hides_uninstallers_and_readmes():
    assert launcher._is_noise("Uninstall Discord")
    assert launcher._is_noise("Readme")
    assert not launcher._is_noise("Discord")
