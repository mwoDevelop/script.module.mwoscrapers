"""Original adapter for the public Stremio-compatible stream JSON contract."""

import re
from urllib.error import HTTPError, URLError

from ...contract import validate_result
from ...descriptors import descriptor
from ...health import available, failure, success
from ...http import read_json
from ...normalize import magnet_uri, normalize_btih, quality_from_name, size_gib_from_name
from ...settings import provider_endpoint, provider_endpoints


class StremioSource:
    priority = 1
    # The Stremio stream contract exposes candidates for one concrete movie or
    # episode. It does not implement Umbrella's separate ``sources_packs``
    # capability. Advertising pack support makes Umbrella launch redundant
    # season/show workers which contend on its provider cache before being
    # rejected at the downstream capability boundary.
    pack_capable = False
    hasMovies = True
    hasEpisodes = True
    provider_name = ""
    base_url = ""
    timeout = 8
    max_results = None

    def __init__(self):
        metadata = descriptor(self.provider_name)
        self.timeout = metadata.timeout_seconds
        self.max_results = metadata.max_results

    def _endpoint_base(self, endpoint):
        return endpoint.rstrip("/")

    def _request_headers(self):
        return {}

    def _stream_url(self, data):
        imdb = str(data.get("imdb") or "").strip()
        if not re.fullmatch(r"tt\d+", imdb):
            return None
        base_url = self._endpoint_base(
            provider_endpoint(self.provider_name, self.base_url)
        )
        if "tvshowtitle" in data:
            return "%s/stream/series/%s:%s:%s.json" % (
                base_url,
                imdb,
                int(data["season"]),
                int(data["episode"]),
            )
        return "%s/stream/movie/%s.json" % (base_url, imdb)

    def _stream_urls(self, data):
        imdb = str(data.get("imdb") or "").strip()
        if not re.fullmatch(r"tt\d+", imdb):
            return ()
        if "tvshowtitle" in data:
            path = "/stream/series/%s:%s:%s.json" % (
                imdb,
                int(data["season"]),
                int(data["episode"]),
            )
        else:
            path = "/stream/movie/%s.json" % imdb
        return tuple(
            self._endpoint_base(endpoint) + path
            for endpoint in provider_endpoints(
                self.provider_name,
                self.base_url,
            )
        )

    def _request_json(self, url):
        return read_json(
            url,
            timeout=self.timeout,
            headers=self._request_headers(),
        )

    def _normalize_stream(self, stream):
        title = str(stream.get("title") or "").strip()
        provider_name = str(stream.get("name") or "").strip()
        description = str(stream.get("description") or "").strip()
        name = title or (
            description.splitlines()[0].strip()
            if description
            else provider_name
        )
        metadata = "\n".join(
            value
            for value in (title, provider_name, description)
            if value
        )
        btih = normalize_btih(
            stream.get("infoHash")
            or stream.get("url")
            or stream.get("behaviorHints", {}).get("bingeGroup")
        )
        if not btih or not name:
            return None
        seeders_match = re.search(
            r"(?:👤|seeders?[: ]+)\s*(\d+)",
            metadata,
            re.IGNORECASE,
        )
        item = {
            "provider": self.provider_name,
            "source": "torrent",
            "seeders": int(seeders_match.group(1)) if seeders_match else 0,
            "hash": btih,
            "name": name.splitlines()[0],
            "name_info": metadata.replace("\n", " | "),
            "quality": quality_from_name(metadata),
            "language": "en",
            "url": magnet_uri(btih, name.splitlines()[0]),
            "info": metadata.replace("\n", " | "),
            "direct": False,
            "debridonly": True,
            "size": size_gib_from_name(metadata),
        }
        validate_result(item)
        return item

    def sources(self, data, hostDict):
        del hostDict
        if not data or not available(self.provider_name):
            return []
        try:
            urls = self._stream_urls(data)
        except (ValueError, TypeError, KeyError):
            return []
        for url in urls:
            try:
                payload = self._request_json(url)
                if not isinstance(payload, dict) or not isinstance(
                    payload.get("streams"), list
                ):
                    raise ValueError("provider violated stream contract")
                normalized = []
                seen = set()
                for stream in payload["streams"]:
                    if not isinstance(stream, dict):
                        continue
                    item = self._normalize_stream(stream)
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
        if urls:
            failure(self.provider_name)
        return []
