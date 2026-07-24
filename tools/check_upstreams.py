#!/usr/bin/env python3
"""Download pinned artifacts, verify hashes, and inventory them safely."""

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from safe_ingest import inspect_zip

ENTRY = re.compile(
    r"^  (?P<name>[a-z]+):\n"
    r"(?:    .*\n)*?"
    r'    url: "(?P<url>[^"]+)"\n'
    r'    sha256: "(?P<sha>[0-9a-f]{64})"$',
    re.MULTILINE,
)


def load_lock(path):
    text = Path(path).read_text(encoding="utf-8")
    result = {}
    for match in ENTRY.finditer(text):
        result[match.group("name")] = {
            "url": match.group("url"),
            "sha256": match.group("sha"),
        }
    if not result:
        raise ValueError("no upstream entries found")
    return result


def audit(lock_path, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, entry in load_lock(lock_path).items():
        request = Request(entry["url"], headers={"User-Agent": "MwoScrapers-Audit/0.1"})
        with urlopen(request, timeout=30) as response, tempfile.NamedTemporaryFile(
            suffix=".zip"
        ) as handle:
            payload = response.read(64 * 1024 * 1024 + 1)
            if len(payload) > 64 * 1024 * 1024:
                raise ValueError("%s artifact exceeds download limit" % name)
            handle.write(payload)
            handle.flush()
            digest = hashlib.sha256(payload).hexdigest()
            if digest != entry["sha256"]:
                raise ValueError("%s SHA-256 drift: %s" % (name, digest))
            report = inspect_zip(handle.name)
            report.pop("path", None)
            summary[name] = report
    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    (output / "summary.json").write_text(rendered, encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lock",
        default=str(Path(__file__).parents[1] / "resources" / "upstreams.lock.yml"),
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    audit(args.lock, args.output)


if __name__ == "__main__":
    main()
