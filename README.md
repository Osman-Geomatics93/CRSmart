# CRSmart

**An uncertainty- and epoch-aware CRS / datum transformation assistant for QGIS.**

CRSmart turns CRS and datum transformation from a guessing game into a guided,
transparent, *uncertainty-aware* workflow. Its angle is **honesty about accuracy
and epoch**, not just "reproject".

> Status: **early development** (Phase 1 scaffold). See `TODO.md` for progress
> and `DESIGN.md` for the full design.

## Features

| | Feature | What it does |
|---|---|---|
| **A** | Transformation recommender with uncertainty | Enumerates every candidate transform between two CRSs, annotated with accuracy (m), area of validity, ballpark/grid-dependency flags; ranks them and recommends the best. Never silently uses a ballpark transform. |
| **B** | Epoch-aware / dynamic-datum transforms | Detects dynamic datums, lets you set a coordinate epoch, and performs correct time-dependent (4D) transforms — explaining *why* an epoch is needed. |
| **C** | Local site calibration | Fits a 2D Helmert (4-param) or affine (6-param) from matched control points by least squares; reports residuals, RMSE, scale/rotation/translation, flags outliers, and emits a reusable PROJ pipeline. |
| **D** | Vertical datum repair | Detects missing vertical CRS and lets you assemble/assign a compound (horizontal + vertical) CRS in a few clicks. |

Every feature is available both as a **Processing algorithm** (scriptable,
batchable) and via a **dockable panel**.

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
git clone https://github.com/osmangeomatics/crsmart
cd crsmart
pip install -e ".[dev]"
pre-commit install
```
Symlink/copy the `crsmart/` package into your QGIS profile plugins directory:
- **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\crsmart`
- **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/crsmart`
- **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/crsmart`

## Development

```bash
ruff check crsmart tests      # lint
black --check crsmart tests   # format
mypy crsmart                  # types (uses qgis-stubs)
pytest                        # tests (pytest-qgis)
```

The pure-Python engine lives in `crsmart/core/` and has **zero** Qt/`iface`
dependencies (enforced by `tests/test_no_qt_in_core.py`), so it is unit-testable
without a running QGIS GUI. See `CLAUDE.md` for the full constraint set.

## License

GPL-2.0-only. See [`LICENSE`](LICENSE).
