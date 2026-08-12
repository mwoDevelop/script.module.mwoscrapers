from pathlib import Path
from xml.etree import ElementTree

from mwoscrapers.descriptors import PROVIDER_DESCRIPTORS
from mwoscrapers.settings import DEFAULTS


def test_descriptors_settings_and_provenance_are_in_sync():
    names = [item.name for item in PROVIDER_DESCRIPTORS]
    assert len(names) == len(set(names))

    root = ElementTree.parse("resources/settings.xml").getroot()
    setting_ids = {
        node.attrib["id"].removeprefix("provider.")
        for node in root.findall(".//setting[@type='boolean']")
    }
    assert setting_ids == set(names)
    assert set(DEFAULTS) == {"provider.%s" % name for name in names}
    assert all(item.status == "qualified" for item in PROVIDER_DESCRIPTORS)
    assert all(item.enabled_by_default for item in PROVIDER_DESCRIPTORS)
    assert all(item.timeout_seconds > 0 for item in PROVIDER_DESCRIPTORS)
    assert all(item.max_results > 0 for item in PROVIDER_DESCRIPTORS)

    provenance = Path("resources/provider-provenance.yml").read_text(
        encoding="utf-8"
    )
    for name in names:
        assert "  %s:\n" % name in provenance
