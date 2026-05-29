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

## Phase 2 — Core engine (pure Python, fully tested)
- [ ] `core/models.py` dataclasses
- [ ] `core/transform_recommender.py` (Feature A) + tests (AU/UK/Sudan cases)
- [ ] `core/epoch.py` (Feature B) + tests (ITRF/GDA2020 epoch reproduction)
- [ ] `core/calibration.py` (Feature C) + tests (param recovery, RMSE, outlier, pipeline round-trip)
- [ ] `core/vertical.py` (Feature D) + tests (compound CRS assembly)
- [ ] `core/grids.py` (availability + consented CDN fetch) + consent-gate test

## Phase 3 — Processing algorithms (MVP surface, built first)
- [ ] recommend_transform, reproject_layer, epoch_transform, fit_calibration (CSV input first), repair_vertical
- [ ] Provider `loadAlgorithms` wires them; help text; headless tests

## Phase 4 — GUI dock panel
- [ ] Feature tabs on `QgsDockWidget`; native widgets; messageBar; consent modal
- [ ] A couple of pytest-qgis interaction tests

## Phase 5 — Tests & polish
- [ ] Edge cases, error states, docstrings, coverage round-out

## Phase 6 — CI, packaging, docs
- [ ] Finalize CI matrix; confirm/pin exact Qt6 checker entrypoint (see below)
- [ ] `qgis-plugin-ci` release config
- [ ] i18n `.ts`/`.qm` scaffolding
- [ ] README screenshots, user guide; verify built zip installs cleanly

## Open items / decisions to confirm with user
- Repo slug placeholder is `github.com/mohamed-fawzy/crsmart` — replace with the real one.
- Author name assumed "Mohamed Fawzy" from email — correct if wrong.
- **Qt6 checker CI entrypoint** is best-effort (`pyqgis-4-checker` / fallback
  script path) and must be confirmed against the Oslandia image in Phase 6.
- Defaults taken at Phase 1: GitHub Actions CI, CSV-first calibration input,
  cm-level tolerance for Feature B assertions.
