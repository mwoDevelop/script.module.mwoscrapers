import hashlib
import json

import pytest

from tools.verify_audit_scan import CoverageFailure, verify


def _fixture(tmp_path):
    audit = tmp_path / "audit"
    digest = hashlib.sha256(b"zip-bytes").hexdigest()
    archive = audit / ("archives/coco-%s.zip" % digest)
    content = audit / "materialized/coco/addon.py"
    archive.parent.mkdir(parents=True)
    content.parent.mkdir(parents=True)
    archive.write_bytes(b"zip-bytes")
    content.write_bytes(b"VALUE = 1\n")
    summary = {
        "schema": 1,
        "sources": {
            "coco": {
                "status": "ok",
                "actual_sha256": digest,
                "archive": "archives/coco-%s.zip" % digest,
                "materialized": "materialized/coco",
                "materialized_files": 1,
                "materialized_bytes": len(b"VALUE = 1\n"),
            }
        },
    }
    (audit / "summary.json").write_text(json.dumps(summary))
    files = [path for path in audit.rglob("*") if path.is_file()]
    report = {
        "schema": 1,
        "result": "clean",
        "checks": {name: "pass" for name in ("archive_safety", "clamav", "gitleaks", "semgrep")},
        "coverage": {
            "archives": 1,
            "archive_members": 1,
            "archive_expanded_bytes": len(b"VALUE = 1\n"),
            "files": len(files),
            "bytes": sum(path.stat().st_size for path in files),
            "clamav_files": len(files),
            "skipped": 0,
        },
    }
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(report))
    return audit, report_path


def test_accepts_exact_archive_and_materialized_coverage(tmp_path):
    audit, report = _fixture(tmp_path)
    result = verify(audit, report)
    assert result["result"] == "pass"
    assert result["sources"] == 1


def test_rejects_summary_only_scanner_coverage(tmp_path):
    audit, report = _fixture(tmp_path)
    document = json.loads(report.read_text())
    document["coverage"].update({"archives": 0, "archive_members": 0, "files": 1})
    report.write_text(json.dumps(document))
    with pytest.raises(CoverageFailure, match="coverage differs"):
        verify(audit, report)


def test_rejects_archive_identity_drift(tmp_path):
    audit, report = _fixture(tmp_path)
    next((audit / "archives").iterdir()).write_bytes(b"changed")
    with pytest.raises(CoverageFailure, match="identity differs"):
        verify(audit, report)
