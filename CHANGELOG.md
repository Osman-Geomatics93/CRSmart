# Changelog

All notable changes to CRSmart are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
