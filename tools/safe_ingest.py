#!/usr/bin/env python3
"""Inventory an upstream ZIP without extracting or importing its code."""

import argparse
import json
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
            if stat.S_ISLNK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
                raise UnsafeArchive("unsupported special file: %s" % entry.filename)
            if normalized.lower().endswith((".zip", ".tar", ".tgz", ".gz", ".7z", ".rar")):
                raise UnsafeArchive("nested archive: %s" % entry.filename)
            uncompressed += entry.file_size
            compressed += entry.compress_size
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
