import sys
from types import SimpleNamespace
from xml.etree import ElementTree

from mwoscrapers.settings import provider_endpoint, provider_endpoints


def test_endpoint_defaults_are_nonempty_valid_urls():
    root = ElementTree.parse("resources/settings.xml").getroot()
    defaults = {
        setting.attrib["id"]: setting.findtext("default")
        for setting in root.findall(".//setting")
        if setting.attrib["id"].endswith(".endpoint")
    }

    assert defaults == {
        "provider.comet.endpoint": "https://comet.feels.legal",
        "provider.eztv.endpoint": "https://eztvx.to",
        "provider.mediafusion.endpoint": "https://mediafusionfortheweebs.midnightignite.me",
        "provider.piratebay.endpoint": "https://apibay.org",
        "provider.torz.endpoint": "https://stremthru.elfhosted.com/stremio/torz",
        "provider.torrentio.endpoint": "https://torrentio.strem.fun",
    }


def test_provider_endpoint_accepts_lan_relay(monkeypatch):
    addon = SimpleNamespace(
        getSetting=lambda _key: "http://192.168.1.39:18766/torrentio/"
    )
    monkeypatch.setitem(
        sys.modules,
        "xbmcaddon",
        SimpleNamespace(Addon=lambda _addon_id: addon),
    )

    assert provider_endpoint(
        "torrentio", "https://torrentio.strem.fun"
    ) == "http://192.168.1.39:18766/torrentio"
    assert provider_endpoints(
        "torrentio", "https://torrentio.strem.fun"
    ) == (
        "http://192.168.1.39:18766/torrentio",
        "https://torrentio.strem.fun",
    )


def test_provider_endpoint_rejects_credentials_query_and_invalid_scheme(
    monkeypatch,
):
    configured = iter(
        (
            "http://user:pass@relay.lan/torrentio",
            "http://relay.lan/torrentio?upstream=evil",
            "file:///tmp/provider",
        )
    )
    addon = SimpleNamespace(getSetting=lambda _key: next(configured))
    monkeypatch.setitem(
        sys.modules,
        "xbmcaddon",
        SimpleNamespace(Addon=lambda _addon_id: addon),
    )
    default = "https://torrentio.strem.fun"

    assert provider_endpoint("torrentio", default) == default
    assert provider_endpoint("torrentio", default) == default
    assert provider_endpoint("torrentio", default) == default


def test_provider_endpoints_deduplicate_the_public_default(monkeypatch):
    addon = SimpleNamespace(
        getSetting=lambda _key: "https://torrentio.strem.fun/"
    )
    monkeypatch.setitem(
        sys.modules,
        "xbmcaddon",
        SimpleNamespace(Addon=lambda _addon_id: addon),
    )

    assert provider_endpoints(
        "torrentio", "https://torrentio.strem.fun"
    ) == ("https://torrentio.strem.fun",)
