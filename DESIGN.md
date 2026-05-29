# DESIGN.md — CRSmart

> An uncertainty- and epoch-aware CRS / datum transformation assistant for QGIS.
> **Phase 0 deliverable. No plugin code is written until this document is approved.**

---

## 0. Status of this document

This is the design contract for the build. It records:

- module breakdown (engine / processing / gui),
- the **exact** QGIS & pyproj classes/methods per feature, **with the version each was introduced** and the fallback when absent,
- data flow,
- the test plan,
- decisions already taken, and
- the open questions I need you to confirm.

**Decisions locked from your answers:**

| Topic | Decision |
|---|---|
| Test-fixture regions | **Australia (GDA94/GDA2020)**, **USA (NAD83/NATRF2022/ITRF)**, **Europe (ETRS89/ITRF)**, **UK (OSGB36/OSTN15)**, **Sudan (Adindan/WGS84)** |
| MVP surface order | **Processing algorithms first** (Phase 3), GUI dock after (Phase 4) |
| Local QGIS for testing | **QGIS 3.40 LTR** (Qt5) on Windows 11. Qt6/4.x verified in CI. README ships install guidance for both. |

**Why each region earns its place in the test matrix:**

| Region | EPSG anchors | What it exercises |
|---|---|---|
| Australia | GDA94 `4283` → GDA2020 `7844` | Dynamic datum + conformal **distortion grid**; plate-motion epoch transform (Features A & B) |
| USA | NAD83(2011) `6318`, ITRF2014 `9000`s, NATRF2022 (in-flux) | ITRF realization↔realization at epoch; NAVD88 geoid **vertical** grids (Features B & D) |
| Europe | ETRS89 `4258` ↔ ITRF dynamic frames; EVRF vertical | Static-realization vs dynamic-frame contrast; widely-available grids |
| UK | OSGB36 `27700`, OSTN15/OSGM15 | Historic 7-param Helmert (**ballpark**) vs high-accuracy **grid-shift** — the cleanest A/B flag contrast |
| **Sudan** | Adindan (Sudan) `4201`/`20137` (UTM 37N), Adindan→WGS84 | **No CDN grid exists** → only a parametric Helmert + a true **ballpark** fallback. Forces the "never silently use ballpark" path and the missing-grid-but-no-download-available case |

---

## 1. API verification summary (done before writing this doc)

Per your hard rule ("do not assume any API exists — verify"), I checked the version-sensitive surface against the live PyQGIS master docs and pyproj stable docs. Key findings:

### QGIS — `QgsCoordinateReferenceSystem`
| Method | Introduced | Available in our range (≥3.40)? |
|---|---|---|
| `coordinateEpoch()` / `setCoordinateEpoch()` | **QGIS 3.30** | ✅ yes |
| `isDynamic()` | **QGIS 3.30** | ✅ yes |
| `hasVerticalAxis()` | **QGIS 3.38** | ✅ yes |
| `verticalCrs()` / `horizontalCrs()` | **QGIS 3.38** | ✅ yes |
| `createCompoundCrs(h, v)` (static) | **QGIS 3.38** | ✅ yes |
| `toWkt(...)`, `isValid()`, `isGeographic()` | base API | ✅ yes |

**Consequence:** every version-sensitive QGIS method we need is present from **3.30/3.38**, i.e. below our **3.40** minimum. So on the *plugin* side they are always available. We still **feature-detect** (`hasattr`) and **fall back to pyproj** because (a) it future-proofs against API churn in 4.x, and (b) the **pure engine must run headless in CI/pytest without a full QGIS GUI build**, where pyproj is the reliable path.

### pyproj — confirmed surface (stable docs)
- `TransformerGroup(crs_from, crs_to, *, always_xy=False, area_of_interest=None, allow_ballpark=True, authority=None, accuracy=None, only_best=None, force_over=False)`.
  - Attributes: **`.transformers`** (list), **`.unavailable_operations`** (list of `CoordinateOperation` blocked by missing grids), **`.best_available`** (bool).
- Each `Transformer`: **`.description`**, **`.accuracy`** (metres, `-1` if unknown), **`.area_of_use`**, **`.operations`** (the concatenated `CoordinateOperation` list), **`.is_network_enabled`**.
  - ⚠️ **Correction vs first pass:** the pyproj `Transformer` object does **not** expose a top-level `.grids` attribute. Grids are reached via **`transformer.operations[*].grids`** — each `CoordinateOperation` carries its `Grid` list. The recommender therefore flattens grids across a transformer's operations.
- Each `Grid` (on a `CoordinateOperation`): **`.short_name`**, **`.full_name`**, **`.package_name`**, **`.url`**, **`.direct_download`**, **`.open_license`**, **`.available`** (bool — local availability).
- `Transformer.from_crs(..., always_xy=True, allow_ballpark=False)`; `Transformer.from_pipeline(pipeline_str)`.
- 4D transform: `transformer.transform(xx, yy, zz=None, tt=None)` — **`tt`** carries the epoch (decimal year) for time-dependent operations.
- `CRS.is_geographic / is_projected / is_compound / is_vertical / is_geocentric`, `CRS.sub_crs_list`, `CRS.datum`.
- **Dynamic-datum detection:** `CRS.datum.type_name == "Dynamic Geodetic Reference Frame"` (vs "Geodetic Reference Frame" / "Datum Ensemble"). Frame reference epoch via `CRS.coordinate_operation` where present.
- `pyproj.network.set_network_enabled(active)`, `is_network_enabled()`; CDN at `https://cdn.proj.org`. `pyproj.datadir` for the local grid dir.

### QGIS — `QgsDatumTransform.operations(src, dst)` (native mirror of `TransformerGroup`)
Returns a list of `TransformDetails`, each exposing `name`, `accuracy`, `proj` (pipeline string), `isAvailable`, and `grids` — a list of `GridDetails` with `shortName`, `fullName`, `isAvailable`, `url`, `packageName`, `directUrl`.
> ⚠️ The precise `GridDetails` field set has shifted slightly across 3.x. **I will feature-detect each attribute at runtime** and treat this native path as an *optional enrichment* over the pyproj path (which is the canonical engine source). To be re-verified against the running build in Phase 3.

---

## 2. Architecture overview

```
                         ┌──────────────────────────────────────────┐
                         │              crsmart.core                 │
                         │   PURE PYTHON — no qgis.gui, no iface,    │
                         │   no qgis.PyQt. Imports: pyproj, numpy.   │
                         │   (Optionally uses qgis.core ONLY behind  │
                         │    a feature-detect guard; never required)│
                         └──────────────────────────────────────────┘
                              ▲                         ▲
              calls engine    │                         │   calls engine
                              │                         │
        ┌─────────────────────┴───────┐     ┌───────────┴──────────────────┐
        │     crsmart.processing       │     │          crsmart.gui          │
        │  QgsProcessingProvider +     │     │  QgsDockWidget panel +        │
        │  one Algorithm per feature   │     │  native widgets. NO business  │
        │  (headless, scriptable)      │     │  logic — collects input,      │
        │                              │     │  calls engine/processing,     │
        │                              │     │  renders results + messageBar │
        └──────────────────────────────┘     └───────────────────────────────┘
                              ▲                         ▲
                              └───────────┬─────────────┘
                                          │
                                  crsmart/plugin.py
                          initGui / initProcessing / unload
                                          │
                                  crsmart/__init__.py
                                   classFactory(iface)
```

**The golden rule (enforced by a test):** `import crsmart.core.*` must succeed with **zero** `qgis.PyQt`, `qgis.gui`, or `iface` imports. Any QGIS-native enrichment inside core is reached only through a guarded helper that fails soft to pyproj.

---

## 3. Module breakdown

### 3.1 `crsmart/core/` (pure Python — the testable heart)

#### `models.py` — dataclasses (no logic)
```python
@dataclass(frozen=True)
class GridInfo:
    short_name: str
    full_name: str
    url: str | None
    package_name: str | None
    available: bool          # locally present?
    open_license: bool

@dataclass(frozen=True)
class TransformCandidate:
    description: str
    accuracy_m: float | None       # None == unknown
    is_ballpark: bool
    area_of_use: AreaOfUseInfo | None
    grids: tuple[GridInfo, ...]
    pipeline: str | None           # PROJ pipeline string for reuse
    available: bool                # all required grids present?
    rank_score: float              # computed (see ranking)

@dataclass(frozen=True)
class RecommendationResult:
    candidates: tuple[TransformCandidate, ...]   # ranked best-first
    recommended: TransformCandidate | None
    ballpark_only: bool
    missing_grids: tuple[GridInfo, ...]

@dataclass(frozen=True)
class CalibrationResult:
    method: Literal["helmert", "affine"]
    params: dict[str, float]       # scale, rotation_deg, tx, ty (+ shear for affine)
    residuals: tuple[Residual, ...]
    rmse: float
    outliers: tuple[int, ...]      # indices flagged
    pipeline: str                  # +proj=helmert / +proj=affine ...

@dataclass(frozen=True)
class EpochInfo:
    required: bool
    reason: str
    source_epoch: float | None
    target_epoch: float | None
```
(Plus `AreaOfUseInfo`, `Residual`.)

#### `transform_recommender.py` — **Feature A**
- `enumerate_candidates(src, dst, *, area_of_interest=None, allow_ballpark=True) -> RecommendationResult`
  - Builds two `TransformerGroup`s (one with `allow_ballpark=True`, one `False`) to cleanly separate ballpark from non-ballpark and to surface `unavailable_operations` (missing grids).
  - Maps each `Transformer` → `TransformCandidate`: accuracy from `.accuracy` (`-1`→`None`); grids **flattened from `transformer.operations[*].grids`**; pipeline string via `transformer.to_proj4()` / definition; ballpark flag by set-difference against the no-ballpark group; `available = all(g.available for g in grids)`.
  - **Ranking** (`rank_score`, higher = better): primary = covers AOI (boolean), secondary = lower accuracy-in-metres (unknown/None sinks to the bottom), tertiary = all grids available (no download needed), quaternary = not ballpark. Deterministic tie-break by description.
  - `recommended` = top non-ballpark, AOI-covering, available candidate; `None` if only ballpark exists. `ballpark_only` set accordingly.
- Native enrichment hook: if `qgis.core.QgsDatumTransform` is importable, optionally cross-reference `directUrl`/`packageName`. Guarded; never required.

#### `epoch.py` — **Feature B**
- `analyze_epoch(src, dst, src_epoch=None, dst_epoch=None) -> EpochInfo` — detects dynamic datum via `datum.type_name`, decides whether an epoch is required, and produces the plain-language `reason`.
- `transform_4d(src, dst, xx, yy, zz, tt, *, allow_ballpark=False) -> tuple[...]` — wraps `Transformer.from_crs(...).transform(xx, yy, zz, tt)`.
- `require_epoch_or_raise(...)` — raises `EpochRequiredError` when dynamic transform attempted without an epoch (the engine-level enforcement behind the GUI's refusal).

#### `calibration.py` — **Feature C** (the only self-implemented math)
- `fit_helmert_2d(local_xy, target_xy) -> CalibrationResult` — 4-param conformal (scale, rotation, tx, ty) by linear least squares (numpy), closed-form.
- `fit_affine_2d(local_xy, target_xy) -> CalibrationResult` — 6-param affine least squares.
- Both compute per-point residuals, RMSE, standardized residuals; flag outliers where |std. residual| > configurable threshold (default 3σ).
- `to_pipeline(result) -> str` — emit `+proj=helmert ...` (with `convention=` and `+s=` scale ppm) or `+proj=affine ...`. **Round-trips: the emitted pipeline is fed back through `Transformer.from_pipeline` in tests to confirm it reproduces the fit.**

#### `vertical.py` — **Feature D**
- `detect_vertical(crs) -> VerticalStatus` — uses `is_compound` / `is_vertical` / `sub_crs_list` (pyproj) and, when available, QGIS `hasVerticalAxis()`/`verticalCrs()`.
- `assemble_compound(horizontal_crs, vertical_crs) -> CRS` — pyproj `CompoundCRS` (and/or QGIS `createCompoundCrs` when present).
- Reuses `grids.py` for geoid/vertical grid availability + consented fetch.

#### `grids.py` — shared by A & D
- `grid_status(candidate) -> list[GridInfo]`, `missing_grids(...)`.
- `download_grids(grids, *, consent: bool) -> DownloadReport` — **hard gate**: raises `ConsentRequiredError` unless `consent is True`; only then calls `pyproj.network.set_network_enabled(True)` (restored afterwards) and triggers the CDN fetch. **No module import or engine call ever enables the network as a side effect.**

### 3.2 `crsmart/processing/` (built first — MVP)
- `provider.py` — single `QgsProcessingProvider` (id `crsmart`, icon, name).
- `algorithms/`:
  - `recommend_transform.py` — params: `ParameterCrs` src/dst, optional `ParameterExtent` AOI, `ParameterBoolean` allow_ballpark → outputs an HTML/CSV table of ranked candidates + the chosen pipeline string.
  - `reproject_layer.py` — apply a chosen operation to a vector layer (`ParameterVectorLayer` + `ParameterFeatureSink`), optionally pinned to a specific pipeline.
  - `epoch_transform.py` — 4D transform of a point layer at a given `ParameterNumber` epoch.
  - `fit_calibration.py` — `ParameterMatrix` (or two layers / `ParameterFile` CSV) → calibration report + emitted pipeline.
  - `repair_vertical.py` — assign/assemble compound CRS on a layer.
- Each algorithm: `name/displayName/group/shortHelpString`, thin wrapper that **only** marshals params → core → outputs.

### 3.3 `crsmart/gui/` (Phase 4)
- `dock.py` — `QgsDockWidget` with a tab/section per feature.
- `widgets/` — `QgsProjectionSelectionWidget` (src/dst), `QgsMapLayerComboBox`, a results table, a calibration paste/import widget.
- Results & warnings via `iface.messageBar()`. Consent for downloads via an explicit modal. **No geodetic logic here.**

---

## 4. Data flow (Feature A, representative)

```
GUI/Processing collects: src CRS, dst CRS, optional AOI, allow_ballpark flag
        │
        ▼
core.transform_recommender.enumerate_candidates(...)
        │  TransformerGroup(allow_ballpark=True)  ── all ops
        │  TransformerGroup(allow_ballpark=False) ── non-ballpark set (diff → ballpark flags)
        │  .unavailable_operations               ── missing-grid ops
        ▼
ranked RecommendationResult (best-first)
        │
        ├─ if recommended.available  → offer Apply / Copy pipeline
        ├─ if missing_grids          → offer consented CDN download (grids.download_grids(consent=True))
        └─ if ballpark_only          → WARN, require explicit opt-in before any apply
```

---

## 5. Test plan (`tests/`, pytest + pytest-qgis)

| Test file | Covers | Key assertions |
|---|---|---|
| `test_no_qt_in_core.py` | architecture rule | importing every `crsmart.core` module records **no** `qgis.PyQt`/`qgis.gui`/`iface` in `sys.modules` attributable to core |
| `test_recommender.py` | Feature A | **GDA94→GDA2020** returns the conformal+distortion grid op with finite accuracy ranked above the ballpark; **OSGB36→WGS84** ranks the OSTN15 grid-shift above the historic Helmert; **Adindan(Sudan)→WGS84** yields parametric-Helmert + ballpark only (no grid) and sets `recommended` to the non-ballpark Helmert, never the ballpark; a deliberately grid-dependent op appears in `missing_grids` when grid absent; a true ballpark-only pair sets `ballpark_only=True` |
| `test_epoch.py` | Feature B | dynamic-datum detection true for ITRF/GDA2020, false for ETRS89-static-vs-static; a known **ITRF realization↔realization at epoch** reproduces reference coords within tolerance; `EpochRequiredError` raised when epoch needed but unset |
| `test_calibration.py` | Feature C | synthetic points from known Helmert params + Gaussian noise **recover params within tol**; RMSE/residuals correct; injected gross outlier flagged; **emitted pipeline round-trips** via `from_pipeline` |
| `test_vertical.py` | Feature D | 2D CRS detected as missing-vertical; `assemble_compound` yields valid compound CRS with expected vertical sub-CRS |
| `test_grids_consent.py` | safety | `download_grids(consent=False)` raises `ConsentRequiredError`; network never enabled on plain import/enumerate (assert `is_network_enabled()` unchanged) |
| `test_processing.py` | Phase 3 | provider registers; each algorithm runs headless on a fixture layer and produces expected outputs |
| `test_gui_smoke.py` | Phase 4 | dock instantiates under pytest-qgis; a couple of interaction tests |

**Reference data:** EPSG codes for all five regions baked as fixtures — GDA94 `4283`, GDA2020 `7844`, NAD83(2011) `6318`, ITRF2014 `9000`-series, ETRS89 `4258`, OSGB36 `27700`, Adindan-Sudan `4201`/UTM37N `20137` — plus the relevant grids. Reference coordinates sourced from official transformation examples; exact numeric tolerances set per test (mm–cm scale; see §8 Q6).

---

## 6. Tooling / quality gates (Phase 1 + 6)

- `pyproject.toml`: deps (`pyproj`, `numpy`), dev deps (`ruff`, `black`, `mypy`, `qgis-stubs`, `pytest`, `pytest-qgis`, `pre-commit`); ruff + black + mypy config.
- `.pre-commit-config.yaml`: ruff, black, end-of-file/whitespace, and the **Qt5→Qt6 checker**.
- `metadata.txt`: `qgisMinimumVersion=3.40`, `qgisMaximumVersion=4.99`, `supportsQt6=True`, GPL-2.0, full author/repo/tracker/homepage, category.
- `.github/workflows/ci.yml`: matrix lint → mypy → **Oslandia pyqgis Qt6 checker** → pytest against **QGIS 3.40 LTR** and **QGIS 4.x** containers.
- `qgis-plugin-ci` release config; i18n scaffolding (`.ts`/`.qm`, `self.tr(...)`).

---

## 7. Decisions I made without asking (flag if you disagree)

1. **pyproj is the canonical engine source; QGIS-native classes are optional enrichment.** Rationale: keeps core headless-testable and CI-cheap; QGIS classes are used in Processing/GUI where a QGIS runtime exists. (All needed QGIS methods exist ≥3.40 anyway.)
2. **Ranking is multi-key deterministic** (AOI-cover → accuracy → no-download → non-ballpark → name). Open to a different priority order.
3. **Outlier rule:** standardized residual > 3σ, configurable.
4. **Helmert convention:** emit `+proj=helmert` with explicit `convention=` and scale in ppm; document the sign/convention choice in code.
5. **Consent model:** a single `consent: bool` arg deep in `grids.download_grids`, plus a UI modal; network toggled on only for the duration of a consented fetch, then restored.

---

## 8. Open questions for you (please answer to unblock Phase 1)

1. **Repo name & slug.** Keep `crsmart` (package `crsmart/`, provider id `crsmart`)? Or rename now?
2. **Author/contact for `metadata.txt`.** Name + the email to ship (your `mohamed.fawzy98@hotmail.com`?), and the eventual **repository/tracker/homepage URLs** (a GitHub repo I should assume the slug for, e.g. `github.com/<you>/crsmart`?).
3. **Git.** This directory is **not yet a git repo**. Shall I `git init` (with `.gitignore`, GPL-2.0 `LICENSE`) in Phase 1?
4. **CI host.** GitHub Actions (default) or GitLab CI? The Qt6 checker image is GitLab-hosted but runs fine on GHA.
5. **Calibration input priority for the MVP algorithm.** Of {paste table, two layers, CSV file}, which do you want wired first? (I'll default to **CSV file**, simplest to test headless.)
6. **Reference-coordinate strictness.** For Feature B's "reproduces published coordinates within tolerance," is **cm-level** tolerance acceptable for the assertion, or do you want **mm-level** (requires sourcing higher-precision published vectors)?

---

## 9. What happens after approval

On your "approved" I proceed to **Phase 1 (Scaffold)** only: repo skeleton, `metadata.txt`, `__init__.py`/`plugin.py`, `pyproject.toml`, pre-commit, stub Processing provider, empty dock that loads, a passing pytest-qgis smoke test, CI workflow — then checkpoint with you before Phase 2. I will also add `CLAUDE.md` (the §4 constraints) and `TODO.md` at Phase 1 so they persist.

**→ Awaiting your approval of this design (and answers to §8) before any plugin code is written.**
