"""Bounded JSON transport shared by provider adapters."""

import json
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def _origin(url):
    parsed = urlsplit(url)
    return parsed.scheme.lower(), parsed.hostname, parsed.port


def read_json(url, timeout, headers=None, max_bytes=MAX_RESPONSE_BYTES):
    request_headers = {"User-Agent": "MwoScrapers/0.2"}
    request_headers.update(headers or {})
    request = Request(url, headers=request_headers)
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise HTTPError(
                url,
                response.status,
                "unexpected status",
                response.headers,
                None,
            )
        if _origin(response.geturl()) != _origin(url):
            raise ValueError("cross-origin provider redirect rejected")
        declared = response.headers.get("Content-Length")
        if declared and int(declared) > max_bytes:
            raise ValueError("provider response exceeds size limit")
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError("provider response exceeds size limit")
    return json.loads(payload.decode("utf-8"))

