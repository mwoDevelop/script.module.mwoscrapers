import pytest
from mwoscrapers.providers.torrents.eztv import source as eztv_source
from mwoscrapers.providers.torrents.piratebay import (
    _title_matches,
)
from mwoscrapers.providers.torrents.piratebay import (
    source as piratebay_source,
)

HASH = "0123456789abcdef0123456789abcdef01234567"


@pytest.mark.parametrize(
    ("release_name", "requested_title"),
    (
        ("Pokemon.2023.1080p", "Pokémon"),
        ("Amelie.2001.1080p", "Amélie"),
        ("Aeon.Flux.2005.1080p", "Æon Flux"),
        ("Lodz.2023.1080p", "Łódź"),
        ("東京物語.1953.1080p", "東京物語"),
    ),
)
def test_piratebay_title_matching_removes_combining_marks(
    release_name, requested_title
):
    assert _title_matches(release_name, requested_title)


def test_eztv_returns_only_exact_episode_and_uses_leading_imdb_zero(monkeypatch):
    provider = eztv_source()
    calls = []

    def request(url):
        calls.append(url)
        return {
            "torrents_count": 2,
            "torrents": [
                {
                    "episode": "1",
                    "filename": "Fixture.S01E01.1080p.mkv",
                    "hash": HASH,
                    "season": "1",
                    "seeds": 12,
                    "size_bytes": str(2 * 1024**3),
                },
                {
                    "episode": "2",
                    "filename": "Fixture.S01E02.1080p.mkv",
                    "hash": "1" * 40,
                    "season": "1",
                    "seeds": 99,
                    "size_bytes": "1",
                },
            ],
        }

    monkeypatch.setattr(provider, "_request_json", request)
    results = provider.sources(
        {
            "imdb": "tt0903747",
            "tvshowtitle": "Fixture",
            "season": 1,
            "episode": 1,
        },
        {},
    )

    assert len(results) == 1
    assert results[0]["hash"] == HASH
    assert results[0]["quality"] == "1080p"
    assert results[0]["size"] == 2.0
    assert "imdb_id=0903747" in calls[0]


def test_eztv_uses_strict_filename_fallback_for_missing_episode_fields(
    monkeypatch,
):
    provider = eztv_source()
    monkeypatch.setattr(
        provider,
        "_request_json",
        lambda _url: {
            "torrents_count": 2,
            "torrents": [
                {
                    "filename": "Fixture.S01E01.1080p.mkv",
                    "hash": HASH,
                    "seeds": 12,
                    "size_bytes": "100",
                },
                {
                    "filename": "Fixture.S01E10.1080p.mkv",
                    "hash": "1" * 40,
                    "seeds": 99,
                    "size_bytes": "100",
                },
            ],
        },
    )

    results = provider.sources(
        {
            "imdb": "tt0903747",
            "tvshowtitle": "Fixture",
            "season": 1,
            "episode": 1,
        },
        {},
    )

    assert [item["hash"] for item in results] == [HASH]


def test_eztv_is_episode_only_and_checks_bounded_outer_pages(monkeypatch):
    provider = eztv_source()
    pages = []

    def request(url):
        page = int(url.rsplit("page=", 1)[1])
        pages.append(page)
        torrents = []
        if page == 10:
            torrents = [
                {
                    "episode": "1",
                    "filename": "Fixture.S01E01.720p.mkv",
                    "hash": HASH,
                    "season": "1",
                    "seeds": 1,
                    "size_bytes": "100",
                }
            ]
        return {"torrents_count": 1000, "torrents": torrents}

    monkeypatch.setattr(provider, "_request_json", request)
    assert provider.sources({"imdb": "tt1", "title": "Movie"}, {}) == []
    results = provider.sources(
        {
            "imdb": "tt0903747",
            "tvshowtitle": "Fixture",
            "season": 1,
            "episode": 1,
        },
        {},
    )
    assert len(results) == 1
    assert pages == [1, 10]


def test_eztv_page_order_reaches_middle_before_bounded_limit(monkeypatch):
    provider = eztv_source()
    pages = []

    def request(url):
        page = int(url.rsplit("page=", 1)[1])
        pages.append(page)
        torrents = []
        if page == 5:
            torrents = [
                {
                    "episode": "1",
                    "filename": "Fixture.S01E01.720p.mkv",
                    "hash": HASH,
                    "season": "1",
                    "seeds": 1,
                    "size_bytes": "100",
                }
            ]
        return {"torrents_count": 1000, "torrents": torrents}

    monkeypatch.setattr(provider, "_request_json", request)
    results = provider.sources(
        {
            "imdb": "tt0903747",
            "tvshowtitle": "Fixture",
            "season": 1,
            "episode": 1,
        },
        {},
    )

    assert len(results) == 1
    assert pages == [1, 10, 5]


def test_piratebay_movie_rejects_wrong_imdb_and_title(monkeypatch):
    provider = piratebay_source()
    monkeypatch.setattr(
        provider,
        "_request_json",
        lambda _url: [
            {
                "id": "1",
                "imdb": "tt0133093",
                "info_hash": HASH,
                "name": "The.Matrix.1999.1080p",
                "seeders": "42",
                "size": str(3 * 1024**3),
            },
            {
                "id": "2",
                "imdb": "tt9999999",
                "info_hash": "1" * 40,
                "name": "The.Matrix.1999.1080p",
                "seeders": "100",
                "size": "1",
            },
            {
                "id": "3",
                "imdb": "tt0133093",
                "info_hash": "2" * 40,
                "name": "Wrong.Movie.1999.1080p",
                "seeders": "100",
                "size": "1",
            },
        ],
    )
    result = provider.sources(
        {"imdb": "tt0133093", "title": "The Matrix", "year": 1999},
        {},
    )
    assert len(result) == 1
    assert result[0]["seeders"] == 42
    assert result[0]["size"] == 3.0


def test_piratebay_episode_requires_exact_show_and_episode(monkeypatch):
    provider = piratebay_source()
    monkeypatch.setattr(
        provider,
        "_request_json",
        lambda _url: [
            {
                "id": "1",
                "imdb": "tt0903747",
                "info_hash": HASH,
                "name": "Breaking.Bad.S01E01.720p",
                "seeders": "4",
                "size": "100",
            },
            {
                "id": "2",
                "imdb": "tt0903747",
                "info_hash": "1" * 40,
                "name": "Breaking.Bad.S01E10.720p",
                "seeders": "4",
                "size": "100",
            },
            {
                "id": "3",
                "imdb": "tt0903747",
                "info_hash": "2" * 40,
                "name": "Another.Show.S01E01.720p",
                "seeders": "4",
                "size": "100",
            },
        ],
    )
    result = provider.sources(
        {
            "imdb": "tt0903747",
            "tvshowtitle": "Breaking Bad",
            "season": 1,
            "episode": 1,
        },
        {},
    )
    assert len(result) == 1
    assert result[0]["hash"] == HASH
