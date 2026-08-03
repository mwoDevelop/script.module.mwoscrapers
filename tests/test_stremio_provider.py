import json
from pathlib import Path
from urllib.error import URLError

from mwoscrapers.providers.torrents.comet import source as comet_source
from mwoscrapers.providers.torrents.torrentio import source


def _fixture():
    path = Path(__file__).parent / "fixtures" / "stremio_movie.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_movie_url_and_normalized_deduplicated_results(monkeypatch):
    provider = source()
    monkeypatch.setattr(provider, "_request_json", lambda url: _fixture())
    results = provider.sources(
        {
            "imdb": "tt1254207",
            "title": "Big Buck Bunny",
            "year": "2008",
            "aliases": [],
        },
        {},
    )
    assert len(results) == 1
    item = results[0]
    assert item["hash"] == "0123456789abcdef0123456789abcdef01234567"
    assert item["quality"] == "1080p"
    assert item["size"] == 1.25
    assert item["seeders"] == 42
    assert item["url"].startswith("magnet:?xt=urn:btih:")


def test_comet_description_supplies_filename_quality_size_and_seeders(
    monkeypatch,
):
    provider = comet_source()
    monkeypatch.setattr(
        provider,
        "_request_json",
        lambda _url: {
            "streams": [
                {
                    "name": "[TORRENT] Comet 2160p",
                    "description": (
                        "Sintel.2010.2160p.WEB-DL.mkv\n"
                        "size: 3.25 GB\nseeders: 17"
                    ),
                    "infoHash": "0123456789abcdef0123456789abcdef01234567",
                }
            ]
        },
    )

    result = provider.sources({"imdb": "tt1727587"}, {})[0]

    assert result["provider"] == "comet"
    assert result["name"] == "Sintel.2010.2160p.WEB-DL.mkv"
    assert result["quality"] == "4K"
    assert result["size"] == 3.25
    assert result["seeders"] == 17


def test_episode_url():
    provider = source()
    assert provider._stream_url(
        {
            "imdb": "tt1234567",
            "tvshowtitle": "Fixture",
            "season": "2",
            "episode": "3",
        }
    ).endswith("/stream/series/tt1234567:2:3.json")


def test_stremio_provider_does_not_advertise_unimplemented_pack_contract():
    provider = source()

    assert provider.pack_capable is False
    assert not hasattr(provider, "sources_packs")


def test_provider_endpoint_is_an_ocp_extension_point(monkeypatch):
    monkeypatch.setattr(
        "mwoscrapers.providers.torrents.stremio.provider_endpoint",
        lambda name, default: "http://relay.lan:8766/torrentio",
    )
    provider = source()

    assert provider._stream_url(
        {"imdb": "tt1254207"}
    ) == "http://relay.lan:8766/torrentio/stream/movie/tt1254207.json"


def test_invalid_imdb_is_not_requested(monkeypatch):
    provider = source()
    monkeypatch.setattr(
        provider,
        "_request_json",
        lambda url: (_ for _ in ()).throw(AssertionError("network called")),
    )
    assert provider.sources({"imdb": "invalid"}, {}) == []


def test_transport_failure_falls_back_to_public_endpoint(monkeypatch):
    provider = source()
    calls = []
    monkeypatch.setattr(
        provider,
        "_stream_urls",
        lambda _data: ("http://relay.invalid/item", "https://public/item"),
    )

    def request(url):
        calls.append(url)
        if "relay.invalid" in url:
            raise URLError("relay unavailable")
        return _fixture()

    monkeypatch.setattr(provider, "_request_json", request)

    assert len(provider.sources({"imdb": "tt1254207"}, {})) == 1
    assert calls == [
        "http://relay.invalid/item",
        "https://public/item",
    ]


def test_valid_empty_response_does_not_fall_back(monkeypatch):
    provider = source()
    calls = []
    monkeypatch.setattr(
        provider,
        "_stream_urls",
        lambda _data: ("http://relay/item", "https://public/item"),
    )

    def request(url):
        calls.append(url)
        return {"streams": []}

    monkeypatch.setattr(provider, "_request_json", request)

    assert provider.sources({"imdb": "tt1254207"}, {}) == []
    assert calls == ["http://relay/item"]


def test_invalid_contract_falls_back_and_health_fails_only_once(monkeypatch):
    provider = source()
    calls = []
    health_failures = []
    monkeypatch.setattr(
        provider,
        "_stream_urls",
        lambda _data: ("http://relay/item", "https://public/item"),
    )
    monkeypatch.setattr(
        provider,
        "_request_json",
        lambda url: calls.append(url) or {"not_streams": []},
    )
    monkeypatch.setattr(
        "mwoscrapers.providers.torrents.stremio.failure",
        lambda name: health_failures.append(name),
    )

    assert provider.sources({"imdb": "tt1254207"}, {}) == []
    assert calls == ["http://relay/item", "https://public/item"]
    assert health_failures == ["torrentio"]
