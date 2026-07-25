import hashlib
import json
from io import BytesIO
from urllib.error import HTTPError
from zipfile import ZipFile

import pytest

from tools.check_upstreams import AuditFailure, audit, load_lock, render_markdown


def _zip_payload(name):
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("%s/addon.xml" % name, "<addon/>")
    return buffer.getvalue()


def _write_lock(path, sources):
    path.write_text(
        json.dumps({"schema": 1, "sources": sources}), encoding="utf-8"
    )


def _entry(name, payload):
    return {
        "repository": "owner/repo",
        "ref": "main",
        "commit": name[0] * 40,
        "version": "1.0.0",
        "url": "https://example.invalid/%s.zip" % name,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def test_audit_records_all_sources_before_failing(tmp_path):
    good = _zip_payload("good")
    bad = _zip_payload("bad")
    lock = tmp_path / "lock.json"
    _write_lock(lock, {"bad": _entry("bad", bad), "good": _entry("good", good)})

    def read_url(url):
        if url.endswith("bad.zip"):
            raise HTTPError(url, 404, "not found", {}, None)
        return good

    with pytest.raises(AuditFailure):
        audit(lock, tmp_path / "report", read_url)

    report = json.loads((tmp_path / "report/summary.json").read_text())
    assert report["sources"]["bad"]["status"] == "unavailable"
    assert report["sources"]["good"]["status"] == "ok"


def test_lock_requires_structured_identity(tmp_path):
    path = tmp_path / "lock.json"
    path.write_text(
        json.dumps({"schema": 1, "sources": {"bad": {"version": "1"}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="fields"):
        load_lock(path)


def test_markdown_reports_every_audited_source(tmp_path):
    payload = _zip_payload("good")
    lock = tmp_path / "lock.json"
    _write_lock(
        lock,
        {
            "first": _entry("first", payload),
            "second": _entry("second", payload),
        },
    )

    report = audit(lock, tmp_path / "report", lambda _url: payload)
    markdown = render_markdown(report)

    assert "| first |" in markdown
    assert "| second |" in markdown
