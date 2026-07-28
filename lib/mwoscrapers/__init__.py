"""Public Umbrella-compatible provider registry."""

from .registry import pack_sources, sources

PROVIDER_API_VERSION = 1

__all__ = ["PROVIDER_API_VERSION", "pack_sources", "sources"]
__version__ = "0.1.5"
