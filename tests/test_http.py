import io
import json
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request

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
    response = _Response(b"{}", url)
    monkeypatch.setattr(
        http,
        "build_opener",
        lambda _handler: SimpleNamespace(
            open=lambda _request, timeout: response
        ),
    )
    assert http.read_json(url, 1) == {}

    response = _Response(b"{}", "https://other.example/item")
    with pytest.raises(ValueError, match="cross-origin"):
        http.read_json(url, 1)

    response = _Response(
        json.dumps({"streams": ["x" * 100]}).encode("utf-8"), url
    )
    with pytest.raises(ValueError, match="size limit"):
        http.read_json(url, 1, max_bytes=16)


def test_redirect_handler_rejects_cross_origin_before_following():
    handler = http.SameOriginRedirectHandler()
    request = Request("https://provider.example/start")

    with pytest.raises(HTTPError, match="cross-origin"):
        handler.redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://other.example/private",
        )


def test_redirect_handler_normalizes_default_origin_ports():
    handler = http.SameOriginRedirectHandler()

    redirected = handler.redirect_request(
        Request("https://provider.example/start"),
        None,
        302,
        "Found",
        {},
        "https://provider.example:443/next",
    )

    assert redirected.full_url == "https://provider.example:443/next"
