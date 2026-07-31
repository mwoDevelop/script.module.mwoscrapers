import json

import pytest

from relay.mwoscrapers_relay.server import (
    MAX_RESPONSE_BYTES,
    ProviderRelay,
    RelayError,
    upstream_url,
)


class Response:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, limit):
        return self.payload[:limit]


def test_only_fixed_provider_stream_paths_are_allowed():
    assert upstream_url(
        "/torrentio/stream/movie/tt1727587.json"
    ) == "https://torrentio.strem.fun/stream/movie/tt1727587.json"
    assert upstream_url(
        "/comet/stream/series/tt0903747:1:1.json"
    ) == "https://comet.feels.legal/stream/series/tt0903747:1:1.json"

    for path in (
        "/torrentio/configure",
        "/torrentio/stream/movie/not-imdb.json",
        "/https://example.com/stream/movie/tt1727587.json",
        "/unknown/stream/movie/tt1727587.json",
    ):
        with pytest.raises(RelayError) as error:
            upstream_url(path)
        assert error.value.status == 404


def test_relay_validates_contract_and_caches_response():
    payload = json.dumps({"streams": []}).encode()
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        return Response(payload)

    relay = ProviderRelay(timeout=3, cache_ttl=60, opener=opener)
    path = "/torrentio/stream/movie/tt1727587.json"

    assert relay.fetch(path) == payload
    assert relay.fetch(path) == payload
    assert calls == [
        ("https://torrentio.strem.fun/stream/movie/tt1727587.json", 3)
    ]


def test_relay_cache_has_a_hard_entry_limit():
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        return Response(json.dumps({"streams": []}).encode())

    relay = ProviderRelay(cache_entries=1, opener=opener)
    first = "/torrentio/stream/movie/tt1727587.json"
    second = "/torrentio/stream/movie/tt1254207.json"

    relay.fetch(first)
    relay.fetch(second)
    relay.fetch(first)

    assert len(relay._cache) == 1
    assert len(calls) == 3


@pytest.mark.parametrize(
    "payload",
    (
        b"not-json",
        json.dumps([]).encode(),
        json.dumps({"streams": "not-a-list"}).encode(),
        b"x" * (MAX_RESPONSE_BYTES + 1),
    ),
)
def test_relay_rejects_unsafe_or_invalid_responses(payload):
    relay = ProviderRelay(opener=lambda *_args, **_kwargs: Response(payload))

    with pytest.raises(RelayError) as error:
        relay.fetch("/torrentio/stream/movie/tt1727587.json")

    assert error.value.status == 502
