import sys
from types import SimpleNamespace

from mwoscrapers.settings import provider_endpoint


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
