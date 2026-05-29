#!/usr/bin/env python3
"""Build an installable CRSmart plugin zip without external tooling.

This mirrors what ``qgis-plugin-ci package`` produces: a zip whose single top
level directory is ``crsmart/`` (the folder name QGIS uses as the plugin id),
containing the runtime package only -- no tests, caches, or dev files.

Usage:
    python scripts/build_zip.py            # -> dist/crsmart-<version>.zip
    python scripts/build_zip.py --out X    # custom output path
"""

from __future__ import annotations

import argparse
import configparser
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "crsmart"

# Files/dirs never shipped inside the plugin zip.
EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_NAMES = {".gitkeep", ".DS_Store"}


def plugin_version() -> str:
    parser = configparser.ConfigParser()
    parser.read(PKG / "metadata.txt", encoding="utf-8")
    return parser["general"]["version"]


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(PKG.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if path.suffix in EXCLUDE_SUFFIXES or path.name in EXCLUDE_NAMES:
            continue
        files.append(path)
    return files


def build(out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    files = iter_files()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            # Arcname keeps the leading "crsmart/" so QGIS installs it correctly.
            arcname = path.relative_to(ROOT).as_posix()
            zf.write(path, arcname)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    version = plugin_version()
    out = args.out or (ROOT / "dist" / f"crsmart-{version}.zip")
    built = build(out)
    size = built.stat().st_size
    print(f"Built {built} ({size} bytes, {len(iter_files())} files)")


if __name__ == "__main__":
    main()
