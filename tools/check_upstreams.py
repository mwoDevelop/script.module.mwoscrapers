#!/usr/bin/env python3
"""Audit every reviewed observation and always emit a complete report."""

import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    from .safe_ingest import inspect_zip
except ImportError:  # Direct script execution.
    from safe_ingest import inspect_zip


MAX_DOWNLOAD = 64 * 1024 * 1024
USER_AGENT = "MwoScrapers-Audit/0.2"
FIELDS = {"repository", "ref", "commit", "version", "url", "sha256"}


class AuditFailure(RuntimeError):
    def __init__(self, summary):
        self.summary = summary
        failed = [name for name, item in summary.items() if item["status"] != "ok"]
        super().__init__("provider observation audit failed: %s" % ", ".join(failed))


def load_lock(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    sources = payload.get("sources")
    if payload.get("schema") != 1 or not isinstance(sources, dict) or not sources:
        raise ValueError("invalid upstream observation lock")
    for name, entry in sources.items():
        if set(entry) != FIELDS:
            raise ValueError("invalid observation fields for %s" % name)
        if len(entry["commit"]) != 40 or len(entry["sha256"]) != 64:
            raise ValueError("invalid observation identity for %s" % name)
    return sources


def _read_url(url):
    last_error = None
    for attempt in range(3):
        try:
            request = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(request, timeout=30) as response:
                payload = response.read(MAX_DOWNLOAD + 1)
            if len(payload) > MAX_DOWNLOAD:
                raise ValueError("artifact exceeds download limit")
            return payload
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504):
                raise
            last_error = error
        except (TimeoutError, URLError) as error:
            last_error = error
        if attempt < 2:
            time.sleep(1 << attempt)
    raise last_error


def _error_kind(error):
    if isinstance(error, HTTPError):
        return "unavailable" if error.code in (404, 410) else "http_%s" % error.code
    if isinstance(error, (TimeoutError, URLError)):
        return "transient_error"
    if isinstance(error, ValueError):
        return "invalid"
    return "error"


def audit(lock_path, output, read_url=_read_url):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, entry in sorted(load_lock(lock_path).items()):
        item = {
            "status": "unknown",
            "repository": entry["repository"],
            "commit": entry["commit"],
            "version": entry["version"],
            "expected_sha256": entry["sha256"],
        }
        try:
            payload = read_url(entry["url"])
            digest = hashlib.sha256(payload).hexdigest()
            item["actual_sha256"] = digest
            if digest != entry["sha256"]:
                raise ValueError("SHA-256 drift")
            with tempfile.NamedTemporaryFile(suffix=".zip") as handle:
                handle.write(payload)
                handle.flush()
                report = inspect_zip(handle.name)
            report.pop("path", None)
            item.update(report)
            item["status"] = "ok"
        except Exception as error:  # Continue to audit the remaining sources.
            item["status"] = _error_kind(error)
            item["error"] = str(error).split("?", 1)[0]
        summary[name] = item
    report = {"schema": 1, "sources": summary}
    (output / "summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if any(item["status"] != "ok" for item in summary.values()):
        raise AuditFailure(summary)
    return report


def render_markdown(report):
    lines = [
        "## Reviewed provider artifact audit",
        "",
        "| Source | Version | Commit | Availability | SHA-256 |",
        "|---|---:|---|---|---|",
    ]
    for name, item in sorted(report["sources"].items()):
        lines.append(
            "| %s | %s | `%s` | %s | `%s` |"
            % (
                name,
                item["version"],
                item["commit"][:12],
                item["status"],
                item.get("actual_sha256", item["expected_sha256"])[:12],
            )
        )
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lock",
        default=str(
            Path(__file__).parents[1]
            / "resources"
            / "upstream-observations.lock.json"
        ),
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown")
    args = parser.parse_args()
    try:
        report = audit(args.lock, args.output)
    except AuditFailure as error:
        report = {"schema": 1, "sources": error.summary}
        if args.markdown:
            Path(args.markdown).write_text(render_markdown(report), encoding="utf-8")
        raise
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
