import hashlib
import json
import subprocess

import pytest

from tools.provider_provenance_candidate import apply, prepare


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _repo(tmp_path):
    subprocess.run(["git", "init", "-b", "main", tmp_path], check=True)
    subprocess.run(["git", "-C", tmp_path, "config", "user.name", "test"], check=True)
    subprocess.run(
        ["git", "-C", tmp_path, "config", "user.email", "test@example.invalid"],
        check=True,
    )
    lock = {
        "schema": 1,
        "sources": {
            "example": {
                "repository": "owner/old",
                "ref": "main",
                "commit": "a" * 40,
                "version": "1.0.0",
                "url": "https://example.invalid/old.zip",
                "sha256": "1" * 64,
            }
        },
    }
    _write(tmp_path / ".upstream/upstream-observations.lock.json", lock)
    subprocess.run(["git", "-C", tmp_path, "add", "."], check=True)
    subprocess.run(["git", "-C", tmp_path, "commit", "-m", "base"], check=True)
    return lock


def _discovery(lock, content_changed=False):
    return {
        "schema": 2,
        "changed": True,
        "sources": {
            "example": {
                "status": "ok",
                "repository": "owner/new",
                "ref": "main",
                "commit": "b" * 40,
                "version": "1.0.0",
                "url": "https://example.invalid/new.zip",
                "sha256": (
                    hashlib.sha256(b"changed").hexdigest()
                    if content_changed
                    else lock["sources"]["example"]["sha256"]
                ),
                "content_changed": content_changed,
                "provenance_changed": True,
            }
        },
    }


def test_prepare_apply_only_changes_identical_byte_provenance(tmp_path):
    lock = _repo(tmp_path)
    discovery = tmp_path / "discovery.json"
    _write(discovery, _discovery(lock))
    candidate = prepare(tmp_path, discovery, tmp_path / "candidate")
    assert candidate["action"] == "propose"
    apply(tmp_path / "candidate", tmp_path)
    updated = json.loads(
        (tmp_path / ".upstream/upstream-observations.lock.json").read_text()
    )
    assert updated["sources"]["example"]["commit"] == "b" * 40
    assert updated["sources"]["example"]["sha256"] == "1" * 64


def test_changed_bytes_are_quarantined_not_proposed(tmp_path):
    lock = _repo(tmp_path)
    discovery = tmp_path / "discovery.json"
    _write(discovery, _discovery(lock, content_changed=True))
    candidate = prepare(tmp_path, discovery, tmp_path / "candidate")
    assert candidate["action"] == "noop"
    assert candidate["quarantined_sources"] == ["example"]
    with pytest.raises(ValueError, match="no safe proposal"):
        apply(tmp_path / "candidate", tmp_path)
