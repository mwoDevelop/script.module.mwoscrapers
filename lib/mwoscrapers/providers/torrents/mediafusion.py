"""MediaFusion adapter using its credential-free Direct P2P contract."""

import base64
import json

from .stremio import StremioSource


def _p2p_header():
    payload = {
        "enable_acestream_streams": False,
        "enable_telegram_streams": False,
        "enable_usenet_streams": False,
        "streaming_providers": [
            {
                "enabled": True,
                "name": "p2p",
                "service": "p2p",
                "use_mediaflow": False,
            }
        ],
    }
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(serialized.encode("utf-8")).rstrip(b"=").decode("ascii")


class source(StremioSource):
    provider_name = "mediafusion"
    base_url = "https://mediafusionfortheweebs.midnightignite.me"
    max_results = 50

    def _request_headers(self):
        return {"encoded_user_data": _p2p_header()}

