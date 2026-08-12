"""Explicit provider registry; no import-time filesystem discovery."""

from importlib import import_module
from typing import Iterable, List, Optional, Tuple, Type

from .descriptors import PROVIDER_DESCRIPTORS
from .settings import provider_enabled

PROVIDERS = {}
for _descriptor in PROVIDER_DESCRIPTORS:
    PROVIDERS.setdefault(_descriptor.folder, []).append(
        (_descriptor.name, _descriptor.module)
    )
PROVIDERS = {
    folder: tuple(items) for folder, items in PROVIDERS.items()
}


def sources(
    specified_folders: Optional[Iterable[str]] = None,
    ret_all: bool = False,
) -> List[Tuple[str, Type]]:
    """Return `(name, source class)` pairs expected by Umbrella."""
    folders = tuple(specified_folders or PROVIDERS)
    result = []
    for folder in folders:
        for name, module_name in PROVIDERS.get(folder, ()):
            if not ret_all and not provider_enabled(name):
                continue
            module = import_module(module_name)
            result.append((name, module.source))
    return result


def pack_sources(source_subfolder: str = "torrents") -> List[str]:
    """Return enabled pack-capable provider names."""
    result = []
    for name, provider_class in sources((source_subfolder,), ret_all=True):
        if getattr(provider_class, "pack_capable", False):
            result.append(name)
    return result
