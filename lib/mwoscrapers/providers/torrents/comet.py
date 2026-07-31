"""Comet provider; independent public fallback for Torrentio outages."""

from .stremio import StremioSource


class source(StremioSource):
    provider_name = "comet"
    base_url = "https://comet.feels.legal"
