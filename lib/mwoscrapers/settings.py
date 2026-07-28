"""Kodi settings with deterministic non-Kodi defaults for tests."""

from urllib.parse import urlsplit

DEFAULTS = {
    "provider.torrentio": True,
    "provider.comet": False,
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


def provider_endpoint(name: str, default: str) -> str:
    """Return a validated provider or LAN-relay base URL.

    The endpoint remains an extension point owned by each provider. Invalid
    user configuration fails closed to the code-defined public default.
    """

    key = "provider.%s.endpoint" % name
    configured = ""
    try:
        import xbmcaddon  # type: ignore

        configured = xbmcaddon.Addon(
            "script.module.mwoscrapers"
        ).getSetting(key).strip()
    except (ImportError, RuntimeError):
        pass
    candidate = configured or default
    parsed = urlsplit(candidate)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        return default.rstrip("/")
    return candidate.rstrip("/")
