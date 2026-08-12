"""Static provider descriptors used by the registry and settings layer."""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ProviderDescriptor:
    name: str
    module: str
    folder: str
    protocol: str
    enabled_by_default: bool
    status: str
    capabilities: Tuple[str, ...]
    timeout_seconds: int
    max_results: int


PROVIDER_DESCRIPTORS = (
    ProviderDescriptor(
        name="torrentio",
        module="mwoscrapers.providers.torrents.torrentio",
        folder="torrents",
        protocol="stremio_json",
        enabled_by_default=True,
        status="qualified",
        capabilities=("movie", "episode"),
        timeout_seconds=8,
        max_results=100,
    ),
    ProviderDescriptor(
        name="comet",
        module="mwoscrapers.providers.torrents.comet",
        folder="torrents",
        protocol="stremio_json",
        enabled_by_default=True,
        status="qualified",
        capabilities=("movie", "episode"),
        timeout_seconds=8,
        max_results=100,
    ),
    ProviderDescriptor(
        name="torz",
        module="mwoscrapers.providers.torrents.torz",
        folder="torrents",
        protocol="stremio_json_p2p",
        enabled_by_default=True,
        status="qualified",
        capabilities=("movie", "episode"),
        timeout_seconds=8,
        max_results=100,
    ),
    ProviderDescriptor(
        name="mediafusion",
        module="mwoscrapers.providers.torrents.mediafusion",
        folder="torrents",
        protocol="stremio_json_p2p",
        enabled_by_default=True,
        status="qualified",
        capabilities=("movie", "episode"),
        timeout_seconds=8,
        max_results=50,
    ),
    ProviderDescriptor(
        name="eztv",
        module="mwoscrapers.providers.torrents.eztv",
        folder="torrents",
        protocol="structured_json",
        enabled_by_default=True,
        status="qualified",
        capabilities=("episode",),
        timeout_seconds=8,
        max_results=100,
    ),
    ProviderDescriptor(
        name="piratebay",
        module="mwoscrapers.providers.torrents.piratebay",
        folder="torrents",
        protocol="structured_json",
        enabled_by_default=True,
        status="qualified",
        capabilities=("movie", "episode"),
        timeout_seconds=8,
        max_results=100,
    ),
)


def descriptor(name):
    for item in PROVIDER_DESCRIPTORS:
        if item.name == name:
            return item
    raise KeyError(name)
