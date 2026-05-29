# CLAUDE.md — working constraints for CRSmart

This file persists the **hard constraints** for this codebase across sessions.
Read it before changing anything. The full rationale and design live in
`DESIGN.md`; the running task list is in `TODO.md`.

## What CRSmart is
A QGIS plugin: an uncertainty- and epoch-aware CRS / datum transformation
assistant. Four features: (A) transformation recommender with uncertainty,
(B) epoch-aware / dynamic-datum (4D) transforms, (C) local site calibration
(Helmert/affine least squares), (D) vertical datum repair.

## Non-negotiable rules

### Geodesy
- **All** datum/projection math goes through **PROJ / pyproj** (or QGIS's
  PROJ-backed classes). The ONLY math we implement ourselves is the
  Helmert/affine **least-squares fit** in feature C (numpy) — and even that
  must **emit a PROJ pipeline string** (`+proj=helmert` / `+proj=affine`).
- **Never silently use a ballpark transform** for survey-grade work — explicit
  opt-in only.
- **No silent network access.** PROJ CDN grid downloads happen **only** behind
  explicit user consent. Importing a module or enumerating transforms must
  never enable the network.

### Architecture
- **`crsmart/core/` is pure Python.** No `qgis.PyQt`, no `qgis.gui`, no `iface`.
  It may use `pyproj`, `numpy`, and `qgis.core` ONLY behind an `hasattr` /
  try-import feature guard with a pyproj fallback. Enforced by
  `tests/test_no_qt_in_core.py`.
- Every capability is exposed as a **Processing algorithm** (scriptable/batchable)
  *and* via the GUI dock. GUI/Processing are thin wrappers — **no business logic**
  in them; they call `crsmart.core`.

### Qt portability (runs on QGIS 3.40 LTR / Qt5 through QGIS 4.x / Qt6)
- Import Qt ONLY via the shim: `from qgis.PyQt.QtWidgets import ...`, etc.
  **Never** `import PyQt5` / `import PyQt6` (ruff TID banned-api enforces this).
- Use **fully-qualified Qt6-style enums**: `Qt.AlignmentFlag.AlignCenter`,
  `Qt.DockWidgetArea.RightDockWidgetArea` — not `Qt.AlignCenter`.
- **Feature-detect** version-specific QGIS API (e.g. `hasVerticalAxis`,
  `createCompoundCrs`, `coordinateEpoch`) with `hasattr` and degrade gracefully.
- Don't assume an API exists — verify against the PyQGIS docs for the target
  version before using it.

### Quality gates (must stay green)
- `ruff` (lint) + `black` (format) + `mypy` with `qgis-stubs`.
- Tests via **`pytest-qgis`** — meaningful coverage of the core engine.
- CI matrix: **QGIS 3.40 LTR + QGIS 4.x**, plus the **Qt5/Qt6 checker**.
- Full **type hints** on every function/method. Python 3.9+.
- User-facing strings wrapped in `self.tr(...)` / `QCoreApplication.translate`.
- License **GPL-2.0** (required by QGIS).

## Workflow discipline
- Work **phase by phase** (see `DESIGN.md` §5 / `TODO.md`). Each phase ends with
  passing tests before moving on. Checkpoint with the user at phase boundaries.
- Keep `TODO.md` and `CHANGELOG.md` current as you go.
