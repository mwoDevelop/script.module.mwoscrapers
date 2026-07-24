#!/usr/bin/env python3
"""Validate Kodi metadata and the full provider class contract."""

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree


def validate(root):
    root = Path(root).resolve()
    addon = ElementTree.parse(root / "addon.xml").getroot()
    if addon.attrib.get("id") != "script.module.mwoscrapers":
        raise ValueError("unexpected add-on id")
    module = addon.find("./extension[@point='xbmc.python.module']")
    if module is None or module.attrib.get("library") != "lib":
        raise ValueError("missing Python module extension")
    sys.path.insert(0, str(root / "lib"))
    from mwoscrapers import sources
    from mwoscrapers.contract import validate_provider_class

    providers = sources(ret_all=True)
    if not providers:
        raise ValueError("no providers registered")
    for _, provider_class in providers:
        validate_provider_class(provider_class)
    return [name for name, _ in providers]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    print("validated providers:", ", ".join(validate(args.root)))


if __name__ == "__main__":
    main()
