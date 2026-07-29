#!/usr/bin/env python3
"""Prepare and apply a content-addressed provider provenance-only candidate."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

LOCK_PATH = Path(".upstream/upstream-observations.lock.json")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def canonical_json(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def digest(value):
    payload = value if isinstance(value, bytes) else canonical_json(value)
    return hashlib.sha256(payload).hexdigest()


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _git_head(checkout):
    return subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True
    ).strip()


def prepare(checkout, discovery_path, output):
    checkout = Path(checkout).resolve()
    output = Path(output)
    if output.exists():
        raise ValueError("candidate output already exists")
    discovery = _load(discovery_path)
    current = _load(checkout / LOCK_PATH)
    if current.get("schema") != 1 or discovery.get("schema") != 2:
        raise ValueError("unsupported provider document schema")
    proposed = json.loads(json.dumps(current))
    safe_sources = []
    quarantined = []
    for name, item in sorted(discovery["sources"].items()):
        if item.get("status") != "ok":
            continue
        if item.get("content_changed"):
            quarantined.append(name)
            continue
        if not item.get("provenance_changed"):
            continue
        if not COMMIT.fullmatch(item.get("commit", "")):
            raise ValueError("invalid observed commit: %s" % name)
        if not SHA256.fullmatch(item.get("sha256", "")):
            raise ValueError("invalid observed digest: %s" % name)
        accepted = current["sources"].get(name)
        if not accepted or accepted["sha256"] != item["sha256"]:
            raise ValueError("provenance candidate changed accepted bytes: %s" % name)
        proposed["sources"][name] = {
            "repository": item["repository"],
            "ref": item["ref"],
            "commit": item["commit"],
            "version": item["version"],
            "url": item["url"],
            "sha256": item["sha256"],
        }
        safe_sources.append(name)
    action = "propose" if safe_sources else "noop"
    base_commit = _git_head(checkout)
    identity = {
        "schema": 1,
        "action": action,
        "base_commit": base_commit,
        "lock_path": LOCK_PATH.as_posix(),
        "current_lock_sha256": digest(current),
        "proposed_lock_sha256": digest(proposed),
        "safe_sources": safe_sources,
        "quarantined_sources": quarantined,
    }
    candidate = {**identity, "candidate_id": digest(identity)}
    output.mkdir(parents=True)
    (output / "candidate.json").write_bytes(canonical_json(candidate))
    (output / "proposed-lock.json").write_text(
        json.dumps(proposed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return candidate


def apply(bundle, checkout):
    bundle = Path(bundle).resolve()
    checkout = Path(checkout).resolve()
    candidate = _load(bundle / "candidate.json")
    proposed = _load(bundle / "proposed-lock.json")
    identity = {
        key: candidate[key]
        for key in (
            "schema",
            "action",
            "base_commit",
            "lock_path",
            "current_lock_sha256",
            "proposed_lock_sha256",
            "safe_sources",
            "quarantined_sources",
        )
    }
    if candidate.get("candidate_id") != digest(identity):
        raise ValueError("candidate identity mismatch")
    if candidate["action"] != "propose":
        raise ValueError("candidate has no safe proposal")
    if candidate["lock_path"] != LOCK_PATH.as_posix():
        raise ValueError("candidate lock path is not allowlisted")
    if _git_head(checkout) != candidate["base_commit"]:
        raise ValueError("candidate base commit drift")
    current = _load(checkout / LOCK_PATH)
    if digest(current) != candidate["current_lock_sha256"]:
        raise ValueError("accepted observation lock drift")
    if digest(proposed) != candidate["proposed_lock_sha256"]:
        raise ValueError("proposed observation lock digest mismatch")
    changed = {
        name
        for name in proposed["sources"]
        if proposed["sources"].get(name) != current["sources"].get(name)
    }
    if changed != set(candidate["safe_sources"]):
        raise ValueError("candidate changed an undeclared provider")
    for name in changed:
        if proposed["sources"][name]["sha256"] != current["sources"][name]["sha256"]:
            raise ValueError("provenance-only apply changed bytes: %s" % name)
    (checkout / LOCK_PATH).write_text(
        json.dumps(proposed, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return candidate


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--checkout", default=".")
    prepare_parser.add_argument("--discovery", required=True)
    prepare_parser.add_argument("--output", required=True)
    apply_parser = commands.add_parser("apply")
    apply_parser.add_argument("--bundle", required=True)
    apply_parser.add_argument("--checkout", default=".")
    args = parser.parse_args()
    result = (
        prepare(args.checkout, args.discovery, args.output)
        if args.command == "prepare"
        else apply(args.bundle, args.checkout)
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
