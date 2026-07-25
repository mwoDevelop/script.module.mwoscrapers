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


def test_settings_use_localized_numeric_labels():
    root = ElementTree.parse(Path("resources/settings.xml")).getroot()
    labeled_nodes = root.findall(".//*[@label]")
    assert labeled_nodes
    assert all(node.attrib["label"].isdigit() for node in labeled_nodes)

    strings = Path(
        "resources/language/resource.language.en_gb/strings.po"
    ).read_text(encoding="utf-8")
    for node in labeled_nodes:
        assert f'msgctxt "#{node.attrib["label"]}"' in strings
