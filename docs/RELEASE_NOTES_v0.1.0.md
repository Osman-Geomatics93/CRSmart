# CRSmart v0.1.0

**An uncertainty- and epoch-aware CRS / datum transformation assistant for QGIS.**

First public release. CRSmart turns CRS and datum transformation
from a guessing game into a guided, transparent workflow — its angle is honesty
about **accuracy** and **epoch**, not just "reproject". Runs on **QGIS 3.40 LTR
(Qt5) through QGIS 4.x (Qt6)**; every feature is available both as a Processing
algorithm and in a dockable panel. All geodetic math goes through PROJ / pyproj.

## Highlights

- **Recommend transformation (with uncertainty)** — lists every candidate
  transform with its accuracy (m) and area of validity, flags ballpark and
  missing-grid cases, recommends the best, and gives you the PROJ pipeline.
  *Never* silently uses a ballpark transform.
- **Epoch-aware (4D) transforms** — correct time-dependent transforms for
  dynamic datums (ITRF, GDA2020, …); explains why an epoch is needed and refuses
  to run silently without one.
- **Local site calibration** — fit a Helmert or affine transform from control
  points (CSV or pasted), with residuals, RMSE, outlier flagging, and a reusable
  `+proj=affine` pipeline.
- **Vertical datum repair** — fix "vertical CRS missing!" by assembling and
  assigning a compound CRS.
- **No silent network** — PROJ-CDN grid downloads happen only after you confirm.

## Install

1. Download `crsmart-0.1.0.zip` from the assets below.
2. In QGIS: **Plugins ▸ Manage and Install Plugins ▸ Install from ZIP**.
3. Enable **CRSmart** — a toolbar button toggles the dock, and the algorithms
   appear under **Processing Toolbox ▸ CRSmart**.

See [`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md) for a full walkthrough.

## Requirements

- QGIS 3.40 LTR (Qt5) … QGIS 4.x (Qt6). Python 3.9+. PROJ / pyproj (bundled with
  QGIS).

## Quality

- CI green on **QGIS 3.40 LTR (Qt5)** and **QGIS latest (Qt6)**: ruff + mypy, a
  Qt5/Qt6 compatibility gate, the full pytest-qgis suite (Processing + GUI), and
  a build-and-verify plugin-zip job.
- Pure-Python engine with zero Qt dependency, ~94% covered.

## Known limitations

- Early release; APIs and UI may still change before 1.0.
- README screenshots are placeholders.
- One GUI test self-skips on QGIS builds whose projection widget can't hold a
  standalone vertical CRS; the underlying engine path is fully tested.

## Links

- Documentation: [`README.md`](../README.md), [`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md)
- Issues: https://github.com/Osman-Geomatics93/CRSmart/issues
- License: GPL-2.0-or-later

🤖 Generated with [Claude Code](https://claude.com/claude-code)
