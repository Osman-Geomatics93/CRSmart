# CRSmart v0.1.4

**Bug-fix release.** Makes vertical datum repair fail *clearly* instead of with a
cryptic PROJ traceback when the wrong kind of CRS is chosen as the vertical CRS.

## What changed

### Fixed

- **Vertical datum repair crashed with a cryptic `CRSError` traceback when a
  *compound* CRS — e.g. EPSG:9707 "WGS 84 + EGM96 height" — was selected in the
  **Vertical CRS** slot.** PROJ reports any CRS that *contains* a vertical axis as
  `is_vertical=True`, including compound CRSs, so the existing guard let it through
  and PROJ then rejected the (illegal) nested compound. `assemble_compound` now
  requires a **standalone** vertical CRS and refuses a compound (or horizontal) one
  with a clear, actionable message: *"… is not a standalone vertical (height) CRS.
  Choose a pure vertical CRS such as EGM96 height (EPSG:5773) …"*.
  (`crsmart/core/vertical.py`)

> **Tip:** the vertical slot needs a *pure* height CRS. When searching "EGM96" in
> the CRS picker, choose **EGM96 height (EPSG:5773)** — *not* "WGS 84 + EGM96
> height" (EPSG:9707), which is already a compound CRS.

No API changes — see [v0.1.0](RELEASE_NOTES_v0.1.0.md) for the full feature list.

## Install

1. Download `crsmart.v0.1.4.zip` from the assets below.
2. In QGIS: **Plugins ▸ Manage and Install Plugins ▸ Install from ZIP**.
3. Enable **CRSmart** — a toolbar button toggles the dock, and the algorithms
   appear under **Processing Toolbox ▸ CRSmart**.

## Links

- Documentation: [`README.md`](../README.md), [`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md)
- Issues: https://github.com/Osman-Geomatics93/CRSmart/issues
- License: GPL-2.0-or-later

🤖 Generated with [Claude Code](https://claude.com/claude-code)
