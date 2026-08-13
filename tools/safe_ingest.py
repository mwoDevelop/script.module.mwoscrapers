#!/usr/bin/env python3
"""Inventory an upstream ZIP without extracting or importing its code."""

import argparse
import json
import os
import stat
from pathlib import Path, PurePosixPath, PureWindowsPath
from zipfile import BadZipFile, ZipFile

MAX_FILES = 2_000
MAX_COMPRESSED = 64 * 1024 * 1024
MAX_UNCOMPRESSED = 256 * 1024 * 1024
MAX_RATIO = 100


class UnsafeArchive(ValueError):
    pass


def _safe_name(name):
    posix = PurePosixPath(name)
    windows = PureWindowsPath(name)
    if not name or "\x00" in name:
        return False
    if posix.is_absolute() or windows.is_absolute() or windows.drive:
        return False
    if ".." in posix.parts or ".." in windows.parts:
        return False
    return True


def inspect_zip(path):
    path = Path(path)
    if path.stat().st_size > MAX_COMPRESSED:
        raise UnsafeArchive("compressed size exceeds limit")
    try:
        archive = ZipFile(path)
    except BadZipFile as exc:
        raise UnsafeArchive("invalid ZIP") from exc
    with archive:
        entries = archive.infolist()
        if len(entries) > MAX_FILES:
            raise UnsafeArchive("file count exceeds limit")
        names = set()
        folded_names = set()
        regular_names = set()
        uncompressed = 0
        compressed = 0
        for entry in entries:
            if not _safe_name(entry.filename):
                raise UnsafeArchive("unsafe path: %s" % entry.filename)
            normalized = entry.filename.replace("\\", "/")
            folded = normalized.casefold()
            if normalized in names or folded in folded_names:
                raise UnsafeArchive("duplicate or case-colliding path: %s" % entry.filename)
            names.add(normalized)
            folded_names.add(folded)
            mode = entry.external_attr >> 16
            file_type = stat.S_IFMT(mode)
            if entry.flag_bits & 0x1:
                raise UnsafeArchive("encrypted member: %s" % entry.filename)
            if file_type and file_type not in {stat.S_IFREG, stat.S_IFDIR}:
                raise UnsafeArchive("unsupported special file: %s" % entry.filename)
            if not entry.is_dir():
                regular_names.add(normalized.rstrip("/"))
            if normalized.lower().endswith((".zip", ".tar", ".tgz", ".gz", ".7z", ".rar")):
                raise UnsafeArchive("nested archive: %s" % entry.filename)
            uncompressed += entry.file_size
            compressed += entry.compress_size
        for name in regular_names:
            parent = PurePosixPath(name).parent
            while parent != PurePosixPath("."):
                if parent.as_posix() in regular_names:
                    raise UnsafeArchive("file is also an archive directory: %s" % parent)
                parent = parent.parent
        if uncompressed > MAX_UNCOMPRESSED:
            raise UnsafeArchive("uncompressed size exceeds limit")
        if compressed and uncompressed / compressed > MAX_RATIO:
            raise UnsafeArchive("compression ratio exceeds limit")
        return {
            "path": str(path),
            "files": len(entries),
            "compressed_bytes": compressed,
            "uncompressed_bytes": uncompressed,
            "entries": sorted(names),
        }


def materialize_zip(path, destination):
    """Safely materialize a reviewed ZIP without importing or executing it."""

    path = Path(path)
    destination = Path(destination)
    report = inspect_zip(path)
    if destination.exists() or destination.is_symlink():
        raise UnsafeArchive("materialization destination already exists")
    destination.mkdir(parents=True, mode=0o700)
    materialized_files = 0
    materialized_bytes = 0
    try:
        with ZipFile(path) as archive:
            for entry in archive.infolist():
                relative = PurePosixPath(entry.filename.replace("\\", "/"))
                target = destination.joinpath(*relative.parts)
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True, mode=0o700)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                descriptor = os.open(
                    target,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
                with archive.open(entry) as source, os.fdopen(descriptor, "wb") as output:
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        output.write(block)
                materialized_files += 1
                materialized_bytes += entry.file_size
    except Exception:
        import shutil

        shutil.rmtree(destination, ignore_errors=True)
        raise
    return {
        **report,
        "materialized_files": materialized_files,
        "materialized_bytes": materialized_bytes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("zip")
    parser.add_argument("--output")
    args = parser.parse_args()
    report = inspect_zip(args.zip)
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
