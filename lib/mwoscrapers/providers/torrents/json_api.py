"""Shared bounded lifecycle for original structured-JSON provider adapters."""

from urllib.error import HTTPError, URLError

from ...contract import validate_result
from ...descriptors import descriptor
from ...health import available, failure, success
from ...http import read_json
from ...normalize import magnet_uri, normalize_btih, quality_from_name
from ...settings import provider_endpoints


class JsonApiSource:
    priority = 1
    pack_capable = False
    hasMovies = True
    hasEpisodes = True
    provider_name = ""
    base_url = ""
    timeout = 8
    max_results = 100

    def __init__(self):
        metadata = descriptor(self.provider_name)
        self.timeout = metadata.timeout_seconds
        self.max_results = metadata.max_results

    def _request_json(self, url):
        return read_json(url, timeout=self.timeout)

    def _result(self, btih, name, seeders=0, size_bytes=0, metadata=""):
        btih = normalize_btih(btih)
        name = str(name or "").strip()
        if not btih or not name:
            return None
        details = str(metadata or name).strip()
        try:
            size = max(float(size_bytes), 0.0) / float(1024**3)
        except (TypeError, ValueError):
            size = 0.0
        try:
            seeders = max(int(seeders), 0)
        except (TypeError, ValueError):
            seeders = 0
        item = {
            "provider": self.provider_name,
            "source": "torrent",
            "seeders": seeders,
            "hash": btih,
            "name": name,
            "name_info": details,
            "quality": quality_from_name(details),
            "language": "en",
            "url": magnet_uri(btih, name),
            "info": details,
            "direct": False,
            "debridonly": True,
            "size": round(size, 3),
        }
        validate_result(item)
        return item

    def _results_for_endpoint(self, endpoint, data):
        raise NotImplementedError

    def sources(self, data, hostDict):
        del hostDict
        if not data or not available(self.provider_name):
            return []
        endpoints = provider_endpoints(self.provider_name, self.base_url)
        for endpoint in endpoints:
            try:
                items = self._results_for_endpoint(endpoint, data)
                normalized = []
                seen = set()
                for item in items:
                    if not item:
                        continue
                    key = (item["hash"], item["name"])
                    if key in seen:
                        continue
                    seen.add(key)
                    normalized.append(item)
                    if self.max_results and len(normalized) >= self.max_results:
                        break
                success(self.provider_name)
                return normalized
            except (
                HTTPError,
                URLError,
                TimeoutError,
                OSError,
                ValueError,
                TypeError,
                KeyError,
            ):
                continue
        if endpoints:
            failure(self.provider_name)
        return []
