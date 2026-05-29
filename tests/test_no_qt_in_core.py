"""Architecture guard: ``crsmart.core`` must import with ZERO Qt / iface deps.

Run in a fresh interpreter (subprocess) so the result is not polluted by Qt
modules that other tests / pytest-qgis have already imported into ``sys.modules``.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_FORBIDDEN_PREFIXES = ("qgis.PyQt", "qgis.gui", "PyQt5", "PyQt6", "PyQt4")

_PROBE = textwrap.dedent(
    """
    import importlib
    import pkgutil
    import sys

    import crsmart.core as core

    # Import every submodule of crsmart.core so nothing escapes the check.
    for module_info in pkgutil.walk_packages(core.__path__, core.__name__ + "."):
        importlib.import_module(module_info.name)

    forbidden_prefixes = ("qgis.PyQt", "qgis.gui", "PyQt5", "PyQt6", "PyQt4")
    leaked = sorted(
        name
        for name in sys.modules
        if any(
            name == p or name.startswith(p + ".") for p in forbidden_prefixes
        )
    )
    if leaked:
        print("\\n".join(leaked))
        sys.exit(1)
    sys.exit(0)
    """
)


def test_core_imports_without_qt() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Qt / iface leaked into crsmart.core:\n{result.stdout}\n{result.stderr}"
    )
