"""Kodi settings with deterministic non-Kodi defaults for tests."""

from urllib.parse import urlsplit

from .descriptors import PROVIDER_DESCRIPTORS

DEFAULTS = {
    "provider.%s" % item.name: item.enabled_by_default
    for item in PROVIDER_DESCRIPTORS
}


def provider_enabled(name: str) -> bool:
    key = "provider.%s" % name
    try:
        import xbmcaddon  # type: ignore

        addon = xbmcaddon.Addon("script.module.mwoscrapers")
        if hasattr(addon, "getSettingBool"):
            return bool(addon.getSettingBool(key))
        return addon.getSetting(key).lower() == "true"
    except (ImportError, RuntimeError):
        return DEFAULTS.get(key, False)


def _configured_endpoint(name: str) -> str:
    key = "provider.%s.endpoint" % name
    try:
        import xbmcaddon  # type: ignore

        return xbmcaddon.Addon(
            "script.module.mwoscrapers"
        ).getSetting(key).strip()
    except (ImportError, RuntimeError):
        return ""


def _valid_endpoint(candidate: str) -> bool:
    parsed = urlsplit(candidate)
    return not (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    )


def provider_endpoints(name: str, default: str):
    """Return ordered, unique provider endpoints with a public fallback.

    A configured self-hosted endpoint or LAN relay remains preferred. The
    provider's code-defined public endpoint follows it so a relay transport
    failure cannot become a hard runtime dependency. Invalid configuration is
    ignored without weakening URL validation.
    """

    configured = _configured_endpoint(name)
    result = []
    for candidate in (configured, default):
        endpoint = candidate.rstrip("/")
        if not endpoint or not _valid_endpoint(endpoint):
            continue
        if endpoint not in result:
            result.append(endpoint)
    if not result:
        # Provider defaults are code-owned constants. Retain the historical
        # fail-closed behavior if a future provider accidentally supplies an
        # invalid default instead of accepting unsafe user configuration.
        return (default.rstrip("/"),)
    return tuple(result)


def provider_endpoint(name: str, default: str) -> str:
    """Return the preferred endpoint for compatibility with existing callers."""

    return provider_endpoints(name, default)[0]
