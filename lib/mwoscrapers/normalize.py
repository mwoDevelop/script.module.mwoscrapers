"""Normalization helpers shared by independently implemented providers."""

import base64
import re
from urllib.parse import quote

HEX_BTIH = re.compile(r"^[0-9a-fA-F]{40}$")
BASE32_BTIH = re.compile(r"^[A-Z2-7]{32}$", re.IGNORECASE)
MAGNET_BTIH = re.compile(r"urn:btih:([0-9a-fA-F]{40}|[A-Z2-7]{32})", re.IGNORECASE)
SIZE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(GiB|GB|MiB|MB)", re.IGNORECASE)


def normalize_btih(value):
    if not value:
        return None
    value = str(value).strip()
    match = MAGNET_BTIH.search(value)
    if match:
        value = match.group(1)
    if HEX_BTIH.fullmatch(value):
        return value.lower()
    if BASE32_BTIH.fullmatch(value):
        try:
            return base64.b32decode(value.upper()).hex()
        except ValueError:
            return None
    return None


def magnet_uri(btih, name):
    return "magnet:?xt=urn:btih:%s&dn=%s" % (btih, quote(name or ""))


def quality_from_name(name):
    lowered = (name or "").lower()
    if "2160p" in lowered or "4k" in lowered:
        return "4K"
    if "1080p" in lowered:
        return "1080p"
    if "720p" in lowered:
        return "720p"
    if "cam" in lowered:
        return "CAM"
    return "SD"


def size_gib_from_name(name):
    match = SIZE.search(name or "")
    if not match:
        return 0.0
    value = float(match.group(1).replace(",", "."))
    return value if match.group(2).lower() in ("gib", "gb") else value / 1024.0
