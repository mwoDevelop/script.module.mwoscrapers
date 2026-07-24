"""Per-provider health isolation without shared credentials."""

from dataclasses import dataclass
from time import monotonic


@dataclass
class Health:
    failures: int = 0
    quarantined_until: float = 0.0


_STATE = {}


def available(provider):
    return _STATE.get(provider, Health()).quarantined_until <= monotonic()


def success(provider):
    _STATE[provider] = Health()


def failure(provider, threshold=3, quarantine_seconds=300):
    state = _STATE.setdefault(provider, Health())
    state.failures += 1
    if state.failures >= threshold:
        state.quarantined_until = monotonic() + quarantine_seconds
