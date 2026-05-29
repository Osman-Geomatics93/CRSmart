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
