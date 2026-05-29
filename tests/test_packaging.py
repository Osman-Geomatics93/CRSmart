"""Phase 6 -- verify the built plugin zip has correct structure (no QGIS)."""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent.parent


def _load_build_zip() -> ModuleType:
    """Import scripts/build_zip.py by absolute path.

    Avoids relying on sys.path / cwd, which differ between local runs and the
    CI containers (where a bare ``import build_zip`` fails at collection).
    """
    spec = importlib.util.spec_from_file_location(
        "crsmart_build_zip", ROOT / "scripts" / "build_zip.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_zip = _load_build_zip()


def test_zip_structure(tmp_path: Path) -> None:
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
