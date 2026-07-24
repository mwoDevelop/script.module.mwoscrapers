"""Original adapter for the public Stremio-compatible stream JSON contract."""

import re

import requests

from ...contract import validate_result
from ...health import available, failure, success
from ...normalize import magnet_uri, normalize_btih, quality_from_name, size_gib_from_name


class StremioSource:
    priority = 1
    pack_capable = True
    hasMovies = True
    hasEpisodes = True
    provider_name = ""
    base_url = ""
    timeout = 8

    def _stream_url(self, data):
        imdb = str(data.get("imdb") or "").strip()
        if not re.fullmatch(r"tt\d+", imdb):
            return None
        if "tvshowtitle" in data:
            return "%s/stream/series/%s:%s:%s.json" % (
                self.base_url.rstrip("/"),
                imdb,
                int(data["season"]),
                int(data["episode"]),
            )
        return "%s/stream/movie/%s.json" % (self.base_url.rstrip("/"), imdb)

    def _request_json(self, url):
        response = requests.get(
            url,
            timeout=self.timeout,
            headers={"User-Agent": "MwoScrapers/0.1"},
        )
        response.raise_for_status()
        return response.json()

    def _normalize_stream(self, stream):
        name = str(stream.get("title") or stream.get("name") or "").strip()
        btih = normalize_btih(
            stream.get("infoHash")
            or stream.get("url")
            or stream.get("behaviorHints", {}).get("bingeGroup")
        )
        if not btih or not name:
            return None
        seeders_match = re.search(r"(?:👤|seeders?[: ]+)\s*(\d+)", name, re.IGNORECASE)
        item = {
            "provider": self.provider_name,
            "source": "torrent",
            "seeders": int(seeders_match.group(1)) if seeders_match else 0,
            "hash": btih,
            "name": name.splitlines()[0],
            "name_info": name.replace("\n", " | "),
            "quality": quality_from_name(name),
            "language": "en",
            "url": magnet_uri(btih, name.splitlines()[0]),
            "info": name.replace("\n", " | "),
            "direct": False,
            "debridonly": True,
            "size": size_gib_from_name(name),
        }
        validate_result(item)
        return item

    def sources(self, data, hostDict):
        del hostDict
        if not data or not available(self.provider_name):
            return []
        try:
            url = self._stream_url(data)
            if not url:
                return []
            payload = self._request_json(url)
            normalized = []
            seen = set()
            for stream in payload.get("streams", []):
                item = self._normalize_stream(stream)
                if not item:
                    continue
                key = (item["hash"], item["name"])
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(item)
            success(self.provider_name)
            return normalized
        except (requests.RequestException, ValueError, TypeError, KeyError):
            failure(self.provider_name)
            return []
