"""Small, credential-free relay for provider metadata blocked on VPN exits."""

import json
import os
import re
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UPSTREAMS = {
    "comet": "https://comet.feels.legal",
    "torrentio": "https://torrentio.strem.fun",
}
STREAM_PATH = re.compile(
    r"^/(?P<provider>[a-z0-9_-]+)/stream/"
    r"(?P<media>movie/tt\d+|series/tt\d+:\d+:\d+)\.json$"
)
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class RelayError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def upstream_url(path):
    match = STREAM_PATH.fullmatch(path)
    if not match or match.group("provider") not in UPSTREAMS:
        raise RelayError(404, "unsupported provider path")
    provider = match.group("provider")
    suffix = path[len(provider) + 1 :]
    return UPSTREAMS[provider] + suffix


class ProviderRelay:
    def __init__(
        self,
        timeout=12,
        cache_ttl=300,
        cache_entries=256,
        opener=urlopen,
    ):
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self.cache_entries = cache_entries
        self.opener = opener
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def fetch(self, path):
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(path)
            if cached and cached[0] > now:
                self._cache.move_to_end(path)
                return cached[1]
            if cached:
                del self._cache[path]
        request = Request(
            upstream_url(path),
            headers={
                "Accept": "application/json",
                "User-Agent": "MwoScrapers-Relay/0.1",
            },
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise RelayError(502, "provider returned a non-200 status")
                payload = response.read(MAX_RESPONSE_BYTES + 1)
        except RelayError:
            raise
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise RelayError(502, "provider request failed") from error
        if len(payload) > MAX_RESPONSE_BYTES:
            raise RelayError(502, "provider response exceeded size limit")
        try:
            document = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RelayError(502, "provider response was not JSON") from error
        if not isinstance(document, dict) or not isinstance(
            document.get("streams"), list
        ):
            raise RelayError(502, "provider response violated stream contract")
        with self._lock:
            self._cache[path] = (
                time.monotonic() + self.cache_ttl,
                payload,
            )
            self._cache.move_to_end(path)
            while len(self._cache) > self.cache_entries:
                self._cache.popitem(last=False)
        return payload


class RelayHandler(BaseHTTPRequestHandler):
    relay = ProviderRelay()

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        try:
            payload = self.relay.fetch(self.path)
        except RelayError as error:
            self._json(error.status, {"error": str(error)})
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header(
            "Cache-Control",
            "public, max-age=%d" % self.relay.cache_ttl,
        )
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status, document):
        payload = json.dumps(
            document, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, _format, *_args):
        return


def main():
    host = os.environ.get("MWO_RELAY_HOST", "0.0.0.0")
    port = int(os.environ.get("MWO_RELAY_PORT", "8766"))
    RelayHandler.relay = ProviderRelay(
        timeout=float(os.environ.get("MWO_RELAY_TIMEOUT", "12")),
        cache_ttl=int(os.environ.get("MWO_RELAY_CACHE_TTL", "300")),
        cache_entries=int(os.environ.get("MWO_RELAY_CACHE_ENTRIES", "256")),
    )
    server = ThreadingHTTPServer((host, port), RelayHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
