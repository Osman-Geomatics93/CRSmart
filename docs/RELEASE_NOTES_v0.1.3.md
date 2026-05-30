# CRSmart v0.1.3

**Bug-fix release.** Fixes a crash when running CRSmart algorithms from the
Processing Toolbox, and makes the Epoch tab show its result.

## What changed

### Fixed

- **Running any CRSmart algorithm from the Processing Toolbox could crash QGIS**
  with a native access violation (`projCppContext::getDatabaseContext`). The
  Toolbox executes algorithms in a background worker thread, and pyproj/PROJ's
  database context is not reliably thread-safe there — on Windows this brought
  the whole application down. All CRSmart algorithms now declare the
  `NoThreading` flag, so QGIS runs them on the main thread where PROJ is already
  initialised. (`crsmart/processing/algorithms/base.py`)
- **The Epoch tab's "Run epoch transform" button produced no visible output.**
  It ran the transform into a memory layer and then discarded it. It now uses
  `processing.runAndLoadResults(...)`, so the transformed layer is added to your
  project and appears in the Layers panel. (`crsmart/gui/widgets/epoch_tab.py`)

No API changes — see [v0.1.0](RELEASE_NOTES_v0.1.0.md) for the full feature list.

## Install

1. Download `crsmart.v0.1.3.zip` from the assets below.
2. In QGIS: **Plugins ▸ Manage and Install Plugins ▸ Install from ZIP**.
3. Enable **CRSmart** — a toolbar button toggles the dock, and the algorithms
   appear under **Processing Toolbox ▸ CRSmart**.

## Links

- Documentation: [`README.md`](../README.md), [`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md)
- Issues: https://github.com/Osman-Geomatics93/CRSmart/issues
- License: GPL-2.0-or-later

🤖 Generated with [Claude Code](https://claude.com/claude-code)
