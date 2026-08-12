"""Pirate Bay API adapter with strict title and episode filtering."""

import re
import unicodedata
from urllib.parse import urlencode

from .json_api import JsonApiSource


def _normalized_title(value):
    decomposed = unicodedata.normalize("NFKD", str(value or "")).casefold()
    decomposed = "".join(
        character
        for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(re.findall(r"[a-z0-9]+", decomposed))


def _title_matches(name, title):
    haystack = " %s " % _normalized_title(name)
    needle = " %s " % _normalized_title(title)
    return len(needle.strip()) >= 2 and needle in haystack


def _episode_matches(name, season, episode):
    season = int(season)
    episode = int(episode)
    patterns = (
        r"(?<![a-z0-9])s0*%d[\W_]*e0*%d(?!\d)" % (season, episode),
        r"(?<![a-z0-9])0*%dx0*%d(?!\d)" % (season, episode),
    )
    lowered = str(name or "").casefold()
    return any(re.search(pattern, lowered) for pattern in patterns)


class source(JsonApiSource):
    provider_name = "piratebay"
    base_url = "https://apibay.org"

    def _query_url(self, endpoint, query, category):
        return "%s/q.php?%s" % (
            endpoint.rstrip("/"),
            urlencode({"q": query, "cat": category}),
        )

    @staticmethod
    def _imdb_matches(item, imdb):
        observed = str(item.get("imdb") or "").strip().casefold()
        if not observed or observed == "0":
            return None
        return observed == imdb.casefold()

    def _movie_matches(self, item, data):
        name = item.get("name")
        imdb_match = self._imdb_matches(item, str(data.get("imdb") or ""))
        if imdb_match is False:
            return False
        if not _title_matches(name, data.get("title")):
            return False
        year = str(data.get("year") or "").strip()
        if imdb_match is True:
            return True
        return not year or re.search(r"(?<!\d)%s(?!\d)" % re.escape(year), str(name))

    def _episode_item_matches(self, item, data):
        name = item.get("name")
        imdb_match = self._imdb_matches(item, str(data.get("imdb") or ""))
        if imdb_match is False:
            return False
        return _title_matches(name, data.get("tvshowtitle")) and _episode_matches(
            name,
            data["season"],
            data["episode"],
        )

    def _results_for_endpoint(self, endpoint, data):
        if "tvshowtitle" in data:
            title = str(data.get("tvshowtitle") or "").strip()
            if not title:
                return []
            query = "%s S%02dE%02d" % (
                title,
                int(data["season"]),
                int(data["episode"]),
            )
            category = 205
            matcher = self._episode_item_matches
        else:
            title = str(data.get("title") or "").strip()
            if not title:
                return []
            query = " ".join(
                value for value in (title, str(data.get("year") or "").strip()) if value
            )
            category = 200
            matcher = self._movie_matches
        payload = self._request_json(self._query_url(endpoint, query, category))
        if not isinstance(payload, list):
            raise ValueError("Pirate Bay API violated JSON contract")
        results = []
        for item in payload:
            if (
                not isinstance(item, dict)
                or str(item.get("id")) == "0"
                or not matcher(item, data)
            ):
                continue
            name = item.get("name")
            results.append(
                self._result(
                    item.get("info_hash"),
                    name,
                    seeders=item.get("seeders"),
                    size_bytes=item.get("size"),
                    metadata=name,
                )
            )
        return results
