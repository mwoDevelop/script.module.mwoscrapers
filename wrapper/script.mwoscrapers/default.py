"""User-facing Kodi manager for the MwoScrapers provider module."""

import xbmcaddon
import xbmcgui

ADDON = xbmcaddon.Addon()
MODULE_ID = "script.module.mwoscrapers"


def text(message_id):
    return ADDON.getLocalizedString(message_id)


def provider_status():
    from mwoscrapers.registry import PROVIDERS
    from mwoscrapers.settings import provider_enabled

    rows = []
    for providers in PROVIDERS.values():
        for name, _module_name in providers:
            state = text(32004) if provider_enabled(name) else text(32005)
            rows.append("%s: %s" % (name.title(), state))
    return rows


def show_status(module):
    version = module.getAddonInfo("version")
    rows = [text(32003) % version, ""] + provider_status()
    xbmcgui.Dialog().ok(ADDON.getAddonInfo("name"), "\n".join(rows))


def main():
    module = xbmcaddon.Addon(MODULE_ID)
    choice = xbmcgui.Dialog().select(
        ADDON.getAddonInfo("name"),
        (text(32001), text(32002)),
    )
    if choice == 0:
        module.openSettings()
    elif choice == 1:
        show_status(module)


if __name__ == "__main__":
    main()
