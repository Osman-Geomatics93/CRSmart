# CRSmart

**An uncertainty- and epoch-aware CRS / datum transformation assistant for QGIS.**

CRSmart turns CRS and datum transformation from a guessing game into a guided,
transparent, *uncertainty-aware* workflow. Its angle is **honesty about accuracy
and epoch**, not just "reproject".

> Status: **feature-complete, pre-release (v0.1.0, experimental).** All four
> features are implemented as both Processing algorithms and GUI tabs, with a
> tested pure-Python engine. See `TODO.md` for progress, `DESIGN.md` for the
> design, and [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md) for usage.

## Features

| | Feature | What it does |
|---|---|---|
| **A** | Transformation recommender with uncertainty | Enumerates every candidate transform between two CRSs, annotated with accuracy (m), area of validity, ballpark/grid-dependency flags; ranks them and recommends the best. Never silently uses a ballpark transform. |
| **B** | Epoch-aware / dynamic-datum transforms | Detects dynamic datums, lets you set a coordinate epoch, and performs correct time-dependent (4D) transforms — explaining *why* an epoch is needed. |
| **C** | Local site calibration | Fits a 2D Helmert (4-param) or affine (6-param) from matched control points by least squares; reports residuals, RMSE, scale/rotation/translation, flags outliers, and emits a reusable PROJ pipeline. |
| **D** | Vertical datum repair | Detects missing vertical CRS and lets you assemble/assign a compound (horizontal + vertical) CRS in a few clicks. |

Every feature is available both as a **Processing algorithm** (scriptable,
batchable) and via a **dockable panel**.

## Usage

Open the panel from **Plugins ▸ CRSmart** (toolbar icon), or find the algorithms
in the **Processing Toolbox ▸ CRSmart**. Quick tour:

- **Recommend** — pick a source and target CRS; CRSmart lists every candidate
  transform with its accuracy (m), flags ballpark and missing-grid cases, and
  recommends the best. Copy the PROJ pipeline, or download a missing grid (you
  are asked for consent first — no silent network access).
- **Epoch** — for dynamic datums (e.g. ITRF, GDA2020), set a coordinate epoch
  and run a correct 4D transform. CRSmart explains in plain language *why* an
  epoch is needed and refuses to run silently when one is required but unset.
- **Calibrate** — paste or load (CSV) matched control points
  (`local_x, local_y, target_x, target_y`), fit a Helmert or affine transform,
  inspect residuals/RMSE/outliers, and copy the resulting PROJ pipeline.
- **Vertical** — fix "vertical CRS missing!" by assembling a compound
  (horizontal + vertical) CRS and assigning it.

Full walkthrough with examples: [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md).

## Requirements

- **QGIS 3.40 LTR** (Qt5) through **QGIS 4.x** (Qt6).
- Python 3.9+. All geodetic math runs through **PROJ / pyproj** (bundled with QGIS).

## Install

### From the QGIS Plugin Manager
*(once published)* — search for **CRSmart** in `Plugins ▸ Manage and Install Plugins`.

### From a zip
1. Download the latest `crsmart-x.y.z.zip` from Releases.
2. In QGIS: `Plugins ▸ Manage and Install Plugins ▸ Install from ZIP`.

### From source (for development)
```bash
git clone https://github.com/Osman-Geomatics93/CRSmart
cd CRSmart
pip install -e ".[dev]"
pre-commit install
```
Symlink/copy the `crsmart/` package into your QGIS profile plugins directory:
- **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\crsmart`
- **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/crsmart`
- **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/crsmart`

## Development

```bash
ruff check crsmart tests          # lint
ruff format --check crsmart tests # format (ruff is the sole formatter)
mypy crsmart                      # types (uses qgis-stubs)
pytest                            # tests (pytest-qgis)
```

The pure-Python engine lives in `crsmart/core/` and has **zero** Qt/`iface`
dependencies (enforced by `tests/test_no_qt_in_core.py`), so it is unit-testable
without a running QGIS GUI. See `CLAUDE.md` for the full constraint set.

For verifying an installed build by hand in a real QGIS (both surfaces, with
known sample-data results), follow [`docs/TESTING.md`](docs/TESTING.md).

### Building the plugin zip

```bash
python scripts/build_zip.py        # -> dist/crsmart-<version>.zip
```

The zip has `crsmart/` as its single top-level directory (the id QGIS uses) and
excludes tests, caches and dev files. Install it via
`Plugins ▸ Manage and Install Plugins ▸ Install from ZIP`. Tagged releases are
published to the OSGeo plugin repository by CI via `qgis-plugin-ci`.

## License

GPL-2.0-only. See [`LICENSE`](LICENSE).
