"""StremThru Torz adapter using its credential-free P2P contract."""

import base64
import json

from .stremio import StremioSource


def _p2p_user_data():
    payload = {
        "indexers": [],
        "stores": [{"c": "p2p", "t": ""}],
    }
    serialized = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return base64.b64encode(serialized.encode("utf-8")).decode("ascii")


class source(StremioSource):
    provider_name = "torz"
    base_url = "https://stremthru.elfhosted.com/stremio/torz"
    max_results = 100

    def _endpoint_base(self, endpoint):
        return "%s/%s" % (endpoint.rstrip("/"), _p2p_user_data())

