"""Torrentio provider; original implementation against its JSON endpoint."""

from .stremio import StremioSource


class source(StremioSource):
    provider_name = "torrentio"
    base_url = "https://torrentio.strem.fun"
