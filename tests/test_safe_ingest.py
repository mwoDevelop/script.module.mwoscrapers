import stat
from zipfile import ZipFile, ZipInfo

import pytest

from tools.safe_ingest import UnsafeArchive, inspect_zip


def test_safe_archive_inventory(tmp_path):
    archive = tmp_path / "safe.zip"
    with ZipFile(archive, "w") as handle:
        handle.writestr("addon/addon.xml", "<addon/>")
        handle.writestr("addon/lib/provider.py", "pass")
    report = inspect_zip(archive)
    assert report["files"] == 2


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
