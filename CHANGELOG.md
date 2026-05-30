# Changelog

All notable changes to CRSmart are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

_Nothing yet._

## [0.1.5] - 2026-05-30

### Added

- **Pick a vertical CRS without QGIS's CRS selector.** QGIS's standard CRS picker
  does not list standalone vertical CRSs on many builds, which made vertical-datum
  repair hard to use. Both the **Vertical** dock tab and the **Repair vertical CRS**
  algorithm now offer a **presets dropdown** of common geoid/height CRSs (EGM96,
  EGM2008, EGM84, NAVD88, NAVD88 ftUS, MSL, EVRF2019, AHD) **plus a free-text field**
  for any EPSG code / authid / WKT / PROJ string (the text overrides the preset).
  (`crsmart/core/vertical.py`, `crsmart/gui/widgets/vertical_tab.py`,
  `crsmart/processing/algorithms/repair_vertical.py`)

## [0.1.4] - 2026-05-30

### Fixed

- **Vertical datum repair crashed with a cryptic `CRSError` traceback when a
  *compound* CRS (e.g. EPSG:9707 "WGS 84 + EGM96 height") was chosen in the
  Vertical CRS slot.** PROJ reports a compound CRS as `is_vertical=True` because
  it merely *contains* a vertical axis, so the guard let it through and PROJ then
  rejected the nested compound. `assemble_compound` now requires a **standalone**
  vertical CRS and refuses a compound (or horizontal) one with a clear, actionable
  message pointing to a pure vertical CRS such as EGM96 height (EPSG:5773).
  (`crsmart/core/vertical.py`)

## [0.1.3] - 2026-05-30

### Fixed

- **Running any algorithm from the Processing Toolbox could crash QGIS** with a
  native access violation (`projCppContext::getDatabaseContext`). The Toolbox
  runs algorithms in a background worker thread, and pyproj/PROJ's database
  context is not reliably thread-safe there. All CRSmart algorithms now declare
  the `NoThreading` flag, so QGIS executes them on the main thread where PROJ is
  already initialised. (`crsmart/processing/algorithms/base.py`)
- **The Epoch tab's "Run epoch transform" produced no visible output.** It used
  `processing.run(...)` with a memory output and discarded the result; it now
  uses `processing.runAndLoadResults(...)` so the transformed layer is added to
  the project. (`crsmart/gui/widgets/epoch_tab.py`)

## [0.1.2] - 2026-05-30

### Fixed

- **Epoch-aware transform no longer fails with a cryptic PROJ traceback when only
  a ballpark transform exists.** `make_4d_transformer` (feature B) called
  `Transformer.from_crs(..., allow_ballpark=False)`, which PROJ aborts with
  `ProjError: Error creating Transformer from CRS.` whenever the only available
  path is a low-accuracy ballpark transform (e.g. a required datum grid is not
  installed) — surfacing as an unhelpful traceback. The engine now detects that
  case and raises a clear, actionable `BallparkNotAllowedError`, and raises
  `TransformUnavailableError` when no operation exists at all.
  (`crsmart/core/epoch.py`, `crsmart/core/errors.py`)

### Added

- **Explicit "Allow ballpark transform" opt-in on the Epoch-aware transform
  algorithm.** Honors the survey-grade rule that a ballpark fallback is never
  silent: it is off by default and must be enabled deliberately. Engine errors
  are now surfaced as readable Processing messages instead of raw tracebacks.
  (`crsmart/processing/algorithms/epoch_transform.py`)

## [0.1.1] - 2026-05-29

### Security

- **Restrict PROJ-CDN grid downloads to HTTP(S) schemes.** The grid downloader
  now rejects any non-`http`/`https` URL (e.g. a crafted `file:` / `ftp:` /
  custom-scheme `GridInfo.url`) and opens connections through an opener wired
  with only HTTP(S) handlers, so a local-file or alternate-scheme fetch is not
  possible even if validation were bypassed. Resolves the Bandit B310 finding
  that blocked v0.1.0 on plugins.qgis.org. (`crsmart/core/grids.py`)

## [0.1.0] - 2026-05-29

First public release. Runs on QGIS 3.40 LTR (Qt5) through
QGIS 4.x (Qt6); every capability is available both as a Processing algorithm and
in the dockable panel. All geodetic math goes through PROJ / pyproj.

_Shipped 2026-05-29: tagged `v0.1.0`, published as a
[GitHub release](https://github.com/Osman-Geomatics93/CRSmart/releases/tag/v0.1.0)
with the plugin zip, and uploaded to
[plugins.qgis.org](https://plugins.qgis.org/plugins/crsmart/) (general / non-experimental;
first version awaiting the standard QGIS-repository approval)._

### Added

- **Transformation recommender with uncertainty (Feature A).** Enumerates every
  candidate transform between two CRSs, annotated with accuracy (metres), area of
  validity, ballpark flag, and missing-grid dependency; ranks them and recommends
  the best. Never silently uses a ballpark transform. Emits the chosen PROJ
  pipeline for reuse. Algorithm: `crsmart:recommendtransform`.
- **Reproject layer with an explicit operation.** Writes a reprojected copy of a
  vector layer, optionally pinning a specific PROJ coordinate operation so the
  transform used is explicit and reproducible. Algorithm: `crsmart:reprojectlayer`.
- **Epoch-aware / dynamic-datum (4D) transforms (Feature B).** Detects dynamic
  reference frames (e.g. ITRF, GDA2020), explains in plain language why an epoch
  is required, performs the time-dependent transform at a given coordinate epoch,
  and refuses to run silently when an epoch is required but unset. Algorithm:
  `crsmart:epochtransform`.
- **Local site calibration (Feature C).** Fits a 2D conformal Helmert
  (4-parameter) or 6-parameter affine transform from matched control points (CSV
  or pasted), reporting per-point residuals, RMSE, and robustly flagged outliers,
  and emitting a reusable `+proj=affine` pipeline. Algorithm:
  `crsmart:fitcalibration`.
- **Vertical datum repair (Feature D).** Detects a missing vertical CRS and
  assembles/assigns a compound (horizontal + vertical) CRS. Algorithm:
  `crsmart:repairvertical`.
- **Dockable GUI panel** with one tab per feature, built on native QGIS widgets
  (`QgsProjectionSelectionWidget`, `QgsMapLayerComboBox`); results and warnings
  via `iface.messageBar()`.
- **Consented PROJ-CDN grid download.** When a more accurate operation needs a
  grid that is not installed, CRSmart offers to fetch it from
  `https://cdn.proj.org` only after explicit confirmation. No network access
  happens as a side effect of browsing transformations.
- **Sample data and docs.** `docs/USER_GUIDE.md`, sample control-point CSVs, and
  README usage/build sections.

### Engineering

- Pure-Python engine in `crsmart/core` (pyproj + numpy) with **zero Qt / iface
  dependency**, enforced by a test, so it is unit-testable headlessly.
- Qt5/Qt6 portability: all Qt access via the `qgis.PyQt` shim with fully
  qualified enums; CI gates reject direct `PyQt5`/`PyQt6` imports and unqualified
  Qt enums.
- CI on GitHub Actions: ruff + mypy, a Qt5/Qt6 compatibility gate, the test suite
  on QGIS 3.40 LTR (Qt5) and latest (Qt6) containers, and a build-and-verify
  plugin-zip job. Packaging/release via `qgis-plugin-ci`.
- License: GPL-2.0-or-later.

[Unreleased]: https://github.com/Osman-Geomatics93/CRSmart/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/Osman-Geomatics93/CRSmart/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Osman-Geomatics93/CRSmart/releases/tag/v0.1.0
