"""Comet provider; opt-in original implementation against its JSON endpoint."""

from .stremio import StremioSource


class source(StremioSource):
    provider_name = "comet"
    base_url = "https://comet.elfhosted.com"
