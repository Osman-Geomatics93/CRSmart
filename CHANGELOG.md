# Changelog

All notable changes to CRSmart are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

_Nothing yet._

## [0.1.0] - 2026-05-29

First public release. Runs on QGIS 3.40 LTR (Qt5) through
QGIS 4.x (Qt6); every capability is available both as a Processing algorithm and
in the dockable panel. All geodetic math goes through PROJ / pyproj.

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

[Unreleased]: https://github.com/Osman-Geomatics93/CRSmart/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Osman-Geomatics93/CRSmart/releases/tag/v0.1.0
