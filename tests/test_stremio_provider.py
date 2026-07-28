import json
from pathlib import Path

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
