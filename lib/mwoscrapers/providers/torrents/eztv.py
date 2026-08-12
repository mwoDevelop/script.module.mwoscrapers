"""EZTV episode adapter against its public structured JSON API."""

import math
import re
from urllib.parse import urlencode

from .json_api import JsonApiSource


class source(JsonApiSource):
    provider_name = "eztv"
    base_url = "https://eztvx.to"
    hasMovies = False
    hasEpisodes = True
    page_size = 100
    max_pages = 10

    def _page_url(self, endpoint, imdb, page):
        query = urlencode(
            {
                "imdb_id": imdb,
                "limit": self.page_size,
                "page": page,
            }
        )
        return "%s/api/get-torrents?%s" % (endpoint.rstrip("/"), query)

    def _page(self, endpoint, imdb, page):
        payload = self._request_json(self._page_url(endpoint, imdb, page))
        if not isinstance(payload, dict) or not isinstance(
            payload.get("torrents"), list
        ):
            raise ValueError("EZTV violated JSON contract")
        return payload

    @staticmethod
    def _page_order(total_pages, limit):
        limit = min(max(int(limit), 0), max(int(total_pages), 0))
        if limit == 0:
            return []
        order = [1]
        if limit == 1:
            return order
        order.append(total_pages)
        intervals = [(2, total_pages - 1)]
        while intervals and len(order) < limit:
            next_intervals = []
            for low, high in intervals:
                if len(order) >= limit:
                    break
                if low > high:
                    continue
                middle = (low + high) // 2
                order.append(middle)
                next_intervals.extend(
                    ((low, middle - 1), (middle + 1, high))
                )
            intervals = next_intervals
        return order

    def _normalize_matches(self, torrents, season, episode):
        result = []
        for torrent in torrents:
            if not isinstance(torrent, dict):
                continue
            observed_season = torrent.get("season")
            observed_episode = torrent.get("episode")
            try:
                season_mismatch = (
                    observed_season is not None
                    and int(observed_season) != int(season)
                )
                episode_mismatch = (
                    observed_episode is not None
                    and int(observed_episode) != int(episode)
                )
            except (TypeError, ValueError):
                continue
            if season_mismatch or episode_mismatch:
                continue
            name = torrent.get("filename") or torrent.get("title")
            if (observed_season is None or observed_episode is None) and not re.search(
                r"(?<![a-z0-9])s0*%d[\W_]*e0*%d(?!\d)"
                % (int(season), int(episode)),
                str(name or "").casefold(),
            ):
                continue
            result.append(
                self._result(
                    torrent.get("hash"),
                    name,
                    seeders=torrent.get("seeds"),
                    size_bytes=torrent.get("size_bytes"),
                    metadata=name,
                )
            )
        return result

    def _results_for_endpoint(self, endpoint, data):
        if "tvshowtitle" not in data:
            return []
        imdb = str(data.get("imdb") or "").strip()
        if not re.fullmatch(r"tt\d+", imdb):
            return []
        season = int(data["season"])
        episode = int(data["episode"])
        first = self._page(endpoint, imdb[2:], 1)
        matches = self._normalize_matches(
            first["torrents"], season, episode
        )
        if matches:
            return matches
        try:
            total = max(int(first.get("torrents_count") or 0), 0)
        except (TypeError, ValueError):
            total = 0
        total_pages = max(1, math.ceil(total / self.page_size))
        for page in self._page_order(total_pages, self.max_pages):
            if page == 1:
                continue
            matches = self._normalize_matches(
                self._page(endpoint, imdb[2:], page)["torrents"],
                season,
                episode,
            )
            if matches:
                return matches
        return []
