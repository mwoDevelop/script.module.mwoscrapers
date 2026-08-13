import stat
from zipfile import ZipFile, ZipInfo

import pytest

from tools.safe_ingest import UnsafeArchive, inspect_zip, materialize_zip


def test_safe_archive_inventory(tmp_path):
    archive = tmp_path / "safe.zip"
    with ZipFile(archive, "w") as handle:
        handle.writestr("addon/addon.xml", "<addon/>")
        handle.writestr("addon/lib/provider.py", "pass")
    report = inspect_zip(archive)
    assert report["files"] == 2


def test_materializes_safe_archive_without_executable_bits(tmp_path):
    archive = tmp_path / "safe.zip"
    with ZipFile(archive, "w") as handle:
        handle.writestr("addon/lib/provider.py", "VALUE = 1\n")
    report = materialize_zip(archive, tmp_path / "content")
    target = tmp_path / "content/addon/lib/provider.py"
    assert target.read_text() == "VALUE = 1\n"
    assert target.stat().st_mode & 0o111 == 0
    assert report["materialized_files"] == 1
    assert report["materialized_bytes"] == len("VALUE = 1\n")


def test_rejects_file_used_as_parent_directory(tmp_path):
    archive = tmp_path / "collision.zip"
    with ZipFile(archive, "w") as handle:
        handle.writestr("addon", "file")
        handle.writestr("addon/provider.py", "VALUE = 1\n")
    with pytest.raises(UnsafeArchive, match="also an archive directory"):
        inspect_zip(archive)


@pytest.mark.parametrize("name", ["../escape.py", "/absolute.py", "C:\\escape.py", "inner.zip"])
def test_unsafe_names_are_rejected(tmp_path, name):
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as handle:
        handle.writestr(name, "x")
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive)


def test_symlink_is_rejected(tmp_path):
    archive = tmp_path / "link.zip"
    entry = ZipInfo("addon/link")
    entry.create_system = 3
    entry.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(archive, "w") as handle:
        handle.writestr(entry, "target")
    with pytest.raises(UnsafeArchive):
        inspect_zip(archive)
