#!/usr/bin/env python3
"""Run a sanitized live health probe against every registered provider."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

from mwoscrapers import sources  # noqa: E402, I001


CASES = {
    "movie": {
        "title": "The Matrix",
        "year": 1999,
        "imdb": "tt0133093",
    },
    "episode": {
        "title": "Pilot",
        "year": 2008,
        "imdb": "tt0903747",
        "season": 1,
        "episode": 1,
        "tvshowtitle": "Breaking Bad",
    },
}


def probe(provider_rows=None, monotonic=time.monotonic):
    """Return counts and timings only; never serialize provider result data."""

    rows = provider_rows if provider_rows is not None else sources(ret_all=True)
    report = {"schema": 1, "healthy": True, "providers": []}
    for name, provider_class in rows:
        provider_report = {"provider": name, "healthy": True, "checks": []}
        capabilities = []
        if getattr(provider_class, "hasMovies", False):
            capabilities.append("movie")
        if getattr(provider_class, "hasEpisodes", False):
            capabilities.append("episode")
        if not capabilities:
            provider_report["healthy"] = False
        for capability in capabilities:
            started = monotonic()
            error_type = None
            result_count = 0
            try:
                results = provider_class().sources(dict(CASES[capability]), {})
                result_count = len(results or ())
            except Exception as error:  # noqa: BLE001 - sanitized probe boundary
                error_type = type(error).__name__
            elapsed = round(monotonic() - started, 3)
            healthy = error_type is None and result_count > 0
            provider_report["checks"].append(
                {
                    "capability": capability,
                    "elapsed_seconds": elapsed,
                    "error_type": error_type,
                    "healthy": healthy,
                    "result_count": result_count,
                }
            )
            provider_report["healthy"] = provider_report["healthy"] and healthy
        report["providers"].append(provider_report)
        report["healthy"] = report["healthy"] and provider_report["healthy"]
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = probe()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
