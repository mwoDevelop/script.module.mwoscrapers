import io
import json

import pytest
from mwoscrapers import http


class _Response:
    status = 200

    def __init__(self, payload, url, headers=None):
        self._payload = payload
        self._url = url
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return self._url

    def read(self, size):
        return io.BytesIO(self._payload).read(size)


def test_read_json_is_bounded_and_rejects_cross_origin_redirect(monkeypatch):
    url = "https://provider.example/stream/movie/tt1.json"
    monkeypatch.setattr(
        http,
        "urlopen",
        lambda _request, timeout: _Response(b"{}", url),
    )
    assert http.read_json(url, 1) == {}

    monkeypatch.setattr(
        http,
        "urlopen",
        lambda _request, timeout: _Response(b"{}", "https://other.example/item"),
    )
    with pytest.raises(ValueError, match="cross-origin"):
        http.read_json(url, 1)

    payload = json.dumps({"streams": ["x" * 100]}).encode("utf-8")
    monkeypatch.setattr(
        http,
        "urlopen",
        lambda _request, timeout: _Response(payload, url),
    )
    with pytest.raises(ValueError, match="size limit"):
        http.read_json(url, 1, max_bytes=16)
