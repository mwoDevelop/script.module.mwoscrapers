"""Kodi settings with deterministic non-Kodi defaults for tests."""

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
