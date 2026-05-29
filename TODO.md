# TODO / progress

Phase-by-phase build log. See `DESIGN.md` for detail, `CLAUDE.md` for constraints.

## Phase 0 — Design ✅
- [x] `DESIGN.md` written, API surface verified, approved by user.

## Phase 1 — Scaffold ✅ (this checkpoint)
- [x] Repo skeleton (`crsmart/` package + `core`/`processing`/`gui` subpackages)
- [x] `metadata.txt` (3.40/4.99, supportsQt6, GPL-2.0, hasProcessingProvider)
- [x] `__init__.py` `classFactory` + `plugin.py` (`initGui`/`initProcessing`/`unload`)
- [x] Stub `QgsProcessingProvider`
- [x] Empty `QgsDockWidget` panel that loads
- [x] `pyproject.toml` (ruff/black/mypy + deps), `.pre-commit-config.yaml`
- [x] Smoke tests + core-has-no-Qt guard (pytest-qgis)
- [x] GitHub Actions CI (lint, mypy, Qt6 checker, tests on 3.40 + 4.x)
- [x] `README.md`, `CHANGELOG.md`, `LICENSE` (GPL-2.0), `CLAUDE.md`, `.gitignore`
- [ ] `git init` + initial commit  ← pending (run after user confirms)
- [ ] Confirm the empty plugin loads in local QGIS 3.40 LTR (manual)
- [ ] Confirm CI is green on the remote (needs a pushed repo)

## Phase 2 — Core engine (pure Python, fully tested) ✅
- [x] `core/models.py` dataclasses + `core/errors.py` exception hierarchy
- [x] `core/transform_recommender.py` (Feature A) + tests (Sudan/AGD66/GDA cases)
- [x] `core/epoch.py` (Feature B) + tests (ITRF dynamic detect, 4D round-trip, epoch enforcement)
- [x] `core/calibration.py` (Feature C) + tests (param recovery, RMSE, outlier, pipeline round-trip)
- [x] `core/vertical.py` (Feature D) + tests (detect + compound CRS assembly)
- [x] `core/grids.py` (availability + consented CDN fetch) + consent-gate + no-silent-network tests
- [x] **31 tests pass locally** (pyproj 3.6.1 / PROJ 9.3.0 / numpy 2.0.2); no-Qt-in-core guard green
- [x] **ruff + mypy + ruff-format all clean locally** (ruff 0.14.14, mypy 1.19.1)
- [ ] black not runnable locally (blib2to3 bug on Python 3.9.0 32-bit) — formatted via
      black-compatible `ruff format`; black runs in CI (Python 3.11)

## Phase 3 — Processing algorithms (MVP surface, built first) ✅
- [x] recommend_transform, reproject_layer, epoch_transform, fit_calibration (CSV input first), repair_vertical
- [x] Provider `loadAlgorithms` wires all five; each has displayName/group/shortHelpString
- [x] Shared `base.py` (CRSmartAlgorithm, WKT-based QGIS<->pyproj CRS bridges); thin wrappers, no geodesy
- [x] Pushed locally-testable logic into core (`control_points_from_rows`, `make_4d_transformer`) + tests
- [x] `tests/test_processing.py` headless algorithm tests (run under pytest-qgis in CI)
- [x] Local gates green: mypy (22 files), ruff, ruff format, pytest 44 (non-QGIS subset)
- [ ] QGIS-dependent Processing tests verified only in CI (no local QGIS / no remote yet)

## Phase 4 — GUI dock panel ✅
- [x] `QTabWidget` dock with four tabs (Recommend / Epoch / Calibrate / Vertical)
- [x] Native widgets: QgsProjectionSelectionWidget, QgsMapLayerComboBox
- [x] Results/warnings via `iface.messageBar()`; explicit QMessageBox consent
      modal before any PROJ-CDN grid download (Recommend tab)
- [x] No business logic in GUI — tabs call core/Processing only
- [x] pytest-qgis interaction tests in `tests/test_gui.py` (run in CI)
- [x] Local gates green: ruff, ruff format, mypy (26 files), pytest 37 (non-QGIS subset)

## Phase 5 — Tests & polish ✅
- [x] `tests/test_edge_cases.py`: 23 tests for error states & edge cases
- [x] Calibration input validation: NaN/inf/ragged/non-numeric -> clean CalibrationError
- [x] Identity (src==dst) transform, str-vs-int CRS parity, antimeridian AoU wrap
- [x] grids consent-gate paths: no-URL, non-open-license, report partitioning (offline)
- [x] Core engine coverage 88% -> 93% (remaining gap = live CDN download body, not unit-tested)
- [x] Local gates green: ruff, ruff format, mypy (26 files), pytest 58 (non-QGIS subset)

## Phase 6 — CI, packaging, docs ✅
- [x] CI matrix finalized: lint+mypy, Qt6 checker, tests on QGIS 3.40 + 4.x,
      package (build+verify zip), release (tag-gated qgis-plugin-ci)
- [x] `.qgis-plugin-ci` release config
- [x] i18n scaffolding: `crsmart/i18n/crsmart_en.ts` baseline catalogue
- [x] `scripts/build_zip.py` (dependency-free) + `tests/test_packaging.py`
- [x] Built & structure-verified `dist/crsmart-0.1.0.zip` (crsmart/ top-level,
      no pyc/cache/tests, ships metadata + i18n)
- [x] `docs/USER_GUIDE.md` + README usage/build sections; metadata changelog
- [x] Pushed to GitHub (Osman-Geomatics93/CRSmart, public); **CI FULLY GREEN**
      at 6366a51 (run 26645629199, conclusion=success): lint+mypy, Qt6 gate,
      Tests on QGIS ltr (3.40/Qt5) **71 passed, 1 skipped** AND latest (Qt6)
      **71 passed, 1 skipped**, and build+verify zip. release skipped (tag-gated).
      Real Processing + GUI pytest-qgis tests run on both Qt5 and Qt6.
- [x] Qt6 gate is a self-contained grep check (no fragile external image)

## Remaining — need the user (not code)
- [ ] Load `dist/crsmart-0.1.0.zip` in local QGIS 3.40 desktop to eyeball it.
- [ ] Capture README screenshots (placeholders for now; need a running QGIS).
- [ ] Publish: add repo secrets OSGEO_USERNAME / OSGEO_PASSWORD, then push a
      version tag (e.g. `v0.1.0`) to trigger the tag-gated release job.

## Notes
- Author: **OSMAN IBRAHIM** <osmangeomatics93@gmail.com>; slug Osman-Geomatics93/CRSmart.
- Defaults locked at Phase 1: GitHub Actions CI, CSV-first calibration input,
  cm-level tolerance for Feature B assertions. ruff is the sole formatter
  (black removed). The 1 skipped test = GUI vertical-tab on QGIS builds whose
  projection widget can't hold a standalone vertical CRS (engine path covered
  in tests/test_vertical.py).
