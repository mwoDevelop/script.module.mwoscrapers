import hashlib
import json
from io import BytesIO
from zipfile import ZipFile

from tools.discover_upstreams import discover, render_markdown


def _zip_payload():
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("script.module.example/addon.xml", "<addon/>")
    return buffer.getvalue()


def _write_sources(path, artifact_path="script.module.example-{version}.zip"):
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "sources": {
                    "example": {
                        "repository": "owner/repo",
                        "ref": "main",
                        "feed_path": "addons.xml",
                        "addon_id": "script.module.example",
                        "artifact_path": artifact_path,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def _write_lock(path, version, digest):
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "sources": {
                    "example": {
                        "repository": "owner/repo",
                        "ref": "main",
                        "commit": "b" * 40,
                        "version": version,
                        "url": (
                            "https://raw.githubusercontent.com/owner/repo/"
                            + "b" * 40
                            + "/artifact-%s.zip" % version
                        ),
                        "sha256": digest,
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_discovery_resolves_commit_and_reports_new_artifact(tmp_path):
    artifact = _zip_payload()
    commit = "a" * 40
    sources = tmp_path / "sources.json"
    lock = tmp_path / "lock.json"
    _write_sources(sources)
    _write_lock(lock, "1.0.0", "0" * 64)

    def read_url(url, limit=0):
        if "api.github.com" in url:
            return json.dumps({"sha": commit}).encode()
        if url.endswith("/addons.xml"):
            return b'<addons><addon id="script.module.example" version="1.1.0"/></addons>'
        if url.endswith("script.module.example-1.1.0.zip"):
            return artifact
        raise AssertionError(url)

    report = discover(sources, lock, tmp_path / "report.json", read_url)

    assert report["changed"] is True
    candidate = report["sources"]["example"]
    assert candidate["commit"] == commit
    assert candidate["sha256"] == hashlib.sha256(artifact).hexdigest()
    assert commit in candidate["url"]
    assert candidate["content_changed"] is True
    assert "Content" in render_markdown(report)


def test_discovery_flags_provenance_change_for_identical_artifact(tmp_path):
    artifact = _zip_payload()
    digest = hashlib.sha256(artifact).hexdigest()
    sources = tmp_path / "sources.json"
    lock = tmp_path / "lock.json"
    _write_sources(sources, "artifact-{version}.zip")
    _write_lock(lock, "1.0.0", digest)

    def read_url(url, limit=0):
        if "api.github.com" in url:
            return json.dumps({"sha": "b" * 40}).encode()
        if url.endswith("/addons.xml"):
            return b'<addons><addon id="script.module.example" version="1.0.0"/></addons>'
        return artifact

    report = discover(sources, lock, tmp_path / "report.json", read_url)
    assert report["changed"] is False
    candidate = report["sources"]["example"]
    assert candidate["content_changed"] is False
    assert candidate["provenance_changed"] is False


def test_dead_reviewed_url_with_identical_replacement_requires_update(tmp_path):
    artifact = _zip_payload()
    digest = hashlib.sha256(artifact).hexdigest()
    sources = tmp_path / "sources.json"
    lock = tmp_path / "lock.json"
    _write_sources(sources, "artifact-{version}.zip")
    _write_lock(lock, "1.0.0", digest)

    def read_url(url, limit=0):
        if "api.github.com" in url:
            return json.dumps({"sha": "c" * 40}).encode()
        if url.endswith("/addons.xml"):
            return b'<addons><addon id="script.module.example" version="1.0.0"/></addons>'
        if "/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb/" in url:
            from urllib.error import HTTPError

            raise HTTPError(url, 404, "not found", {}, None)
        return artifact

    report = discover(sources, lock, tmp_path / "report.json", read_url)

    assert report["changed"] is True
    candidate = report["sources"]["example"]
    assert candidate["content_changed"] is False
    assert candidate["provenance_changed"] is True
    assert candidate["reviewed_url_status"] == "unavailable"
