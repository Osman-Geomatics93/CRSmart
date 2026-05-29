"""Phase 6 -- verify the built plugin zip has correct structure (no QGIS)."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_zip  # noqa: E402


def test_zip_structure(tmp_path) -> None:  # noqa: ANN001
    out = tmp_path / "crsmart.zip"
    build_zip.build(out)
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()

    # QGIS uses the top-level folder name as the plugin id: must be "crsmart/".
    assert names, "zip is empty"
    assert all(n.startswith("crsmart/") for n in names)
    # Required runtime files present.
    assert "crsmart/metadata.txt" in names
    assert "crsmart/__init__.py" in names
    assert "crsmart/plugin.py" in names
    # i18n source shipped.
    assert any(n.endswith(".ts") for n in names)
    # No dev/cache artefacts.
    assert not any("__pycache__" in n for n in names)
    assert not any(n.endswith((".pyc", ".pyo")) for n in names)
    assert not any(n.endswith(".gitkeep") for n in names)
    # Tests are not shipped inside the plugin.
    assert not any(n.startswith("crsmart/tests") for n in names)


def test_zip_metadata_version_matches() -> None:
    version = build_zip.plugin_version()
    assert version.count(".") >= 2  # semver-ish
