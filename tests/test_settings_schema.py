from pathlib import Path
from xml.etree import ElementTree


def test_boolean_settings_have_kodi_controls_and_defaults():
    root = ElementTree.parse(Path("resources/settings.xml")).getroot()
    settings = root.findall(".//setting[@type='boolean']")
    assert {setting.attrib["id"] for setting in settings} == {
        "provider.torrentio",
        "provider.comet",
    }
    for setting in settings:
        assert setting.find("./control[@type='toggle']") is not None
        assert setting.find("./default") is not None
