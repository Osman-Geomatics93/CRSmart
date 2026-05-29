# Changelog

All notable changes to CRSmart are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- **Phase 0 — Design.** `DESIGN.md`: module breakdown, verified QGIS/pyproj API
  surface (with introduction versions and fallbacks), data flow, and test plan.
- **Phase 1 — Scaffold.** Repository skeleton, `metadata.txt`
  (`qgisMinimumVersion=3.40`, `qgisMaximumVersion=4.99`, `supportsQt6=True`,
  GPL-2.0), `classFactory` + plugin class (`initGui`/`initProcessing`/`unload`),
  stub Processing provider, empty dockable panel, `pyproject.toml`
  (ruff/black/mypy + deps), pre-commit config, pytest-qgis smoke tests,
  core-has-no-Qt architecture guard, and a GitHub Actions CI matrix
  (lint + mypy + Qt6 checker + tests on QGIS 3.40 LTR and 4.x).
- **Phase 2 — Core engine** (pure Python, no Qt). Feature A transformation
  recommender with uncertainty (accuracy ranking, ballpark detection,
  missing-grid reporting, reusable PROJ pipelines, AOI coverage; never
  recommends a ballpark transform); Feature B epoch-aware / dynamic-datum 4D
  transforms with epoch enforcement; Feature C Helmert/affine least-squares
  calibration emitting a reusable PROJ pipeline (residuals, RMSE, robust
  3.5-sigma outlier flagging); Feature D vertical-CRS detection and compound-CRS
  assembly; and a grid module with a hard download-consent gate (no silent
  network access).
- **Phase 3 — Processing algorithms.** Five `QgsProcessingAlgorithm`s under the
  provider, each a thin wrapper over the core engine with help text: Recommend
  transformation (with uncertainty), Reproject layer (with an explicit pinned
  PROJ operation), Epoch-aware transform (refuses to run silently without a
  required epoch), Fit local site calibration (Helmert/affine from CSV), and
  Repair vertical CRS (assemble/assign a compound CRS). Added a WKT-based
  QGIS<->pyproj CRS bridge; pushed CSV parsing / reusable-transformer logic into
  the testable core. Headless algorithm tests run under pytest-qgis in CI.
- **Phase 4 — GUI dock panel.** A `QgsDockWidget` with one tab per feature
  (Recommend / Epoch / Calibrate / Vertical), built on native QGIS widgets
  (`QgsProjectionSelectionWidget`, `QgsMapLayerComboBox`). Results and warnings
  surface via `iface.messageBar()`; grid downloads require an explicit
  confirmation dialog (no silent network). The GUI holds no geodetic logic — it
  only collects input, calls the engine / Processing, and renders output.
  pytest-qgis interaction tests added for all four tabs.
