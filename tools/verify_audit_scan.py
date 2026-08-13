#!/usr/bin/env python3
"""Fail closed unless the malware scan covered exact reviewed provider bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath


class CoverageFailure(RuntimeError):
    pass


def _regular_files(root):
    files = []
    for directory, directories, names in os.walk(root, followlinks=False):
        base = Path(directory)
        if any((base / name).is_symlink() for name in directories):
            raise CoverageFailure("audit tree contains a directory symlink")
        for name in names:
            path = base / name
            if path.is_symlink() or not path.is_file():
                raise CoverageFailure("audit tree contains a non-regular file")
            files.append(path)
    return files


def _safe_relative(value):
    if not isinstance(value, str):
        raise CoverageFailure("audit summary contains an unsafe path")
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise CoverageFailure("audit summary contains an unsafe path")
    return path


def verify(audit_dir, report_path):
    audit_dir = Path(audit_dir).resolve()
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    summary = json.loads((audit_dir / "summary.json").read_text(encoding="utf-8"))
    sources = summary.get("sources")
    if summary.get("schema") != 1 or not isinstance(sources, dict) or not sources:
        raise CoverageFailure("invalid provider audit summary")
    expected_archives = 0
    expected_members = 0
    expected_expanded_bytes = 0
    for name, item in sources.items():
        if item.get("status") != "ok":
            raise CoverageFailure("provider audit source is not healthy: %s" % name)
        archive_relative = _safe_relative(item.get("archive"))
        expected_archive = "archives/%s-%s.zip" % (name, item.get("actual_sha256"))
        if archive_relative.as_posix() != expected_archive:
            raise CoverageFailure("provider archive path differs: %s" % name)
        archive = audit_dir.joinpath(*archive_relative.parts)
        payload = archive.read_bytes()
        if hashlib.sha256(payload).hexdigest() != item.get("actual_sha256"):
            raise CoverageFailure("provider archive identity differs: %s" % name)
        materialized_relative = _safe_relative(item.get("materialized"))
        if materialized_relative.as_posix() != "materialized/" + name:
            raise CoverageFailure("provider materialized path differs: %s" % name)
        content = audit_dir.joinpath(*materialized_relative.parts)
        materialized_files = _regular_files(content)
        if len(materialized_files) != item.get("materialized_files"):
            raise CoverageFailure("provider materialized file count differs: %s" % name)
        expanded_bytes = sum(path.stat().st_size for path in materialized_files)
        if expanded_bytes != item.get("materialized_bytes"):
            raise CoverageFailure("provider materialized byte count differs: %s" % name)
        expected_archives += 1
        expected_members += item["materialized_files"]
        expected_expanded_bytes += item["materialized_bytes"]
    files = _regular_files(audit_dir)
    coverage = report.get("coverage", {})
    expected = {
        "archives": expected_archives,
        "archive_members": expected_members,
        "archive_expanded_bytes": expected_expanded_bytes,
        "files": len(files),
        "bytes": sum(path.stat().st_size for path in files),
        "clamav_files": sum(path.stat().st_size > 0 for path in files),
        "skipped": 0,
    }
    required_checks = {
        "archive_safety": "pass",
        "clamav": "pass",
        "gitleaks": "pass",
        "semgrep": "pass",
    }
    if (
        report.get("schema") != 1
        or report.get("result") != "clean"
        or report.get("checks") != required_checks
    ):
        raise CoverageFailure("provider malware scan did not pass every check")
    for key, value in expected.items():
        if coverage.get(key) != value:
            raise CoverageFailure(
                "provider malware scan coverage differs for %s: expected %s, got %s"
                % (key, value, coverage.get(key))
            )
    return {"schema": 1, "result": "pass", "sources": len(sources), "coverage": expected}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.audit_dir, args.report), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
