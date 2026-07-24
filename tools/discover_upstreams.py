#!/usr/bin/env python3
"""Discover immutable provider artifacts without importing their code."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

try:
    from .check_upstreams import load_lock
    from .safe_ingest import inspect_zip
except ImportError:  # Direct script execution.
    from check_upstreams import load_lock
    from safe_ingest import inspect_zip

MAX_DOWNLOAD = 64 * 1024 * 1024
USER_AGENT = "MwoScrapers-Discovery/0.1"


def _read_url(url, limit=MAX_DOWNLOAD):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("download exceeds limit: %s" % url)
    return payload


def _commit_sha(repository, ref, read_url=_read_url):
    url = "https://api.github.com/repos/%s/commits/%s" % (
        repository,
        quote(ref, safe=""),
    )
    payload = json.loads(read_url(url, 2 * 1024 * 1024).decode("utf-8"))
    commit = payload.get("sha", "")
    if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("invalid commit SHA for %s@%s" % (repository, ref))
    return commit


def _raw_url(repository, commit, path):
    return "https://raw.githubusercontent.com/%s/%s/%s" % (
        repository,
        commit,
        path.lstrip("/"),
    )


def _addon_version(feed_payload, addon_id):
    root = ElementTree.fromstring(feed_payload)
    for addon in root.findall("addon"):
        if addon.get("id") == addon_id:
            version = addon.get("version")
            if version:
                return version
    raise ValueError("addon %s not found in feed" % addon_id)


def load_sources(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != 1 or not payload.get("sources"):
        raise ValueError("invalid upstream source configuration")
    return payload["sources"]


def discover(source_path, lock_path, output, read_url=_read_url):
    pinned = load_lock(lock_path)
    candidates = {}
    changed = False
    for name, source in load_sources(source_path).items():
        commit = _commit_sha(source["repository"], source["ref"], read_url)
        feed_url = _raw_url(source["repository"], commit, source["feed_path"])
        version = _addon_version(read_url(feed_url), source["addon_id"])
        artifact_path = source["artifact_path"].format(version=version)
        artifact_url = _raw_url(source["repository"], commit, artifact_path)
        artifact = read_url(artifact_url)
        digest = hashlib.sha256(artifact).hexdigest()
        with tempfile.NamedTemporaryFile(suffix=".zip") as handle:
            handle.write(artifact)
            handle.flush()
            inventory = inspect_zip(handle.name)
        current = pinned.get(name, {})
        artifact_changed = (
            current.get("version") != version or current.get("sha256") != digest
        )
        changed = changed or artifact_changed
        candidates[name] = {
            "repository": source["repository"],
            "ref": source["ref"],
            "commit": commit,
            "version": version,
            "url": artifact_url,
            "sha256": digest,
            "artifact_changed": artifact_changed,
            "files": inventory["files"],
            "uncompressed_bytes": inventory["uncompressed_bytes"],
        }
    report = {"schema": 1, "changed": changed, "sources": candidates}
    Path(output).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def render_markdown(report):
    lines = [
        "## Provider upstream discovery",
        "",
        "| Source | Version | Commit | SHA-256 | Changed |",
        "|---|---:|---|---|---:|",
    ]
    for name, item in sorted(report["sources"].items()):
        lines.append(
            "| %s | %s | `%s` | `%s` | %s |"
            % (
                name,
                item["version"],
                item["commit"][:12],
                item["sha256"],
                "yes" if item["artifact_changed"] else "no",
            )
        )
    lines.extend(
        (
            "",
            "No code was imported or executed. Review provenance and licensing "
            "before updating a pin.",
        )
    )
    return "\n".join(lines) + "\n"


def main():
    root = Path(__file__).parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources", default=str(root / "resources" / "upstream-sources.json")
    )
    parser.add_argument(
        "--lock", default=str(root / "resources" / "upstreams.lock.yml")
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown")
    args = parser.parse_args()
    report = discover(args.sources, args.lock, args.output)
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
