#!/usr/bin/env python3
"""Discover provider observations without importing or executing their code."""

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
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
USER_AGENT = "MwoScrapers-Discovery/0.2"


def _read_url(url, limit=MAX_DOWNLOAD):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:
        payload = response.read(limit + 1)
    if len(payload) > limit:
        raise ValueError("download exceeds limit")
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
        if addon.get("id") == addon_id and addon.get("version"):
            return addon.get("version")
    raise ValueError("addon %s not found in feed" % addon_id)


def load_sources(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema") != 1 or not payload.get("sources"):
        raise ValueError("invalid upstream source configuration")
    return payload["sources"]


def _availability(error):
    if isinstance(error, HTTPError) and error.code in (404, 410):
        return "unavailable"
    if isinstance(error, (TimeoutError, URLError)):
        return "transient_error"
    if isinstance(error, HTTPError) and error.code in (429, 500, 502, 503, 504):
        return "transient_error"
    return "invalid"


def _inspect(payload):
    with tempfile.NamedTemporaryFile(suffix=".zip") as handle:
        handle.write(payload)
        handle.flush()
        return inspect_zip(handle.name)


def discover(source_path, lock_path, output, read_url=_read_url):
    reviewed = load_lock(lock_path)
    candidates = {}
    changed = False
    for name, source in sorted(load_sources(source_path).items()):
        current = reviewed.get(name)
        if not current:
            candidates[name] = {
                "status": "invalid",
                "error": "source has no reviewed observation",
            }
            changed = True
            continue
        try:
            commit = _commit_sha(source["repository"], source["ref"], read_url)
            feed_url = _raw_url(source["repository"], commit, source["feed_path"])
            version = _addon_version(read_url(feed_url), source["addon_id"])
            artifact_path = source["artifact_path"].format(version=version)
            artifact_url = _raw_url(source["repository"], commit, artifact_path)
            artifact = read_url(artifact_url)
            digest = hashlib.sha256(artifact).hexdigest()
            inventory = _inspect(artifact)
            content_changed = (
                current["version"] != version or current["sha256"] != digest
            )
            provenance_changed = (
                current["commit"] != commit or current["url"] != artifact_url
            )
            reviewed_url_status = "healthy"
            if provenance_changed:
                try:
                    reviewed_payload = read_url(current["url"])
                    if hashlib.sha256(reviewed_payload).hexdigest() != current["sha256"]:
                        reviewed_url_status = "invalid"
                except Exception as error:
                    reviewed_url_status = _availability(error)
            source_changed = (
                content_changed
                or provenance_changed
                or reviewed_url_status != "healthy"
            )
            changed = changed or source_changed
            candidates[name] = {
                "status": "ok",
                "repository": source["repository"],
                "ref": source["ref"],
                "commit": commit,
                "version": version,
                "url": artifact_url,
                "sha256": digest,
                "content_changed": content_changed,
                "provenance_changed": provenance_changed,
                "reviewed_url_status": reviewed_url_status,
                "files": inventory["files"],
                "uncompressed_bytes": inventory["uncompressed_bytes"],
            }
        except Exception as error:  # Report all sources in one run.
            changed = True
            candidates[name] = {
                "status": _availability(error),
                "error": str(error).split("?", 1)[0],
                "reviewed": current,
            }
    report = {"schema": 2, "changed": changed, "sources": candidates}
    Path(output).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def render_markdown(report):
    lines = [
        "## Provider upstream discovery",
        "",
        "| Source | Version | Commit | Content | Provenance | Reviewed URL |",
        "|---|---:|---|---|---|---|",
    ]
    for name, item in sorted(report["sources"].items()):
        if item["status"] != "ok":
            lines.append(
                "| %s | - | - | unknown | unknown | %s |"
                % (name, item["status"])
            )
            continue
        lines.append(
            "| %s | %s | `%s` | %s | %s | %s |"
            % (
                name,
                item["version"],
                item["commit"][:12],
                "changed" if item["content_changed"] else "unchanged",
                "changed" if item["provenance_changed"] else "unchanged",
                item["reviewed_url_status"],
            )
        )
    lines.extend(
        (
            "",
            "Observed artifacts are not accepted imports. No provider code was "
            "imported or executed.",
        )
    )
    return "\n".join(lines) + "\n"


def main():
    root = Path(__file__).parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sources", default=str(root / ".upstream" / "upstream-sources.json")
    )
    parser.add_argument(
        "--lock",
        default=str(root / ".upstream" / "upstream-observations.lock.json"),
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--markdown")
    args = parser.parse_args()
    report = discover(args.sources, args.lock, args.output)
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
