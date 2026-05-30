# CRSmart v0.1.5

**Usability release.** Makes choosing a vertical CRS easy — QGIS's CRS picker
doesn't list standalone vertical CRSs on many builds, which made vertical-datum
repair frustrating to use.

## What changed

### Added

- **Vertical CRS presets + free-text field.** Both the **Vertical** dock tab and the
  **Repair vertical CRS** Processing algorithm now let you choose the vertical CRS
  from a **dropdown of common geoid/height CRSs** — EGM96 (5773), EGM2008 (3855),
  EGM84 (5798), NAVD88 (5703), NAVD88 ftUS (6360), MSL (5714), EVRF2019 (9389),
  AHD (5711) — **or** type any EPSG code / authid / WKT / PROJ string in a custom
  field (the text overrides the preset). No more fighting the QGIS CRS selector,
  which often won't list pure vertical CRSs at all.
  (`crsmart/core/vertical.py`, `crsmart/gui/widgets/vertical_tab.py`,
  `crsmart/processing/algorithms/repair_vertical.py`)

Builds on the v0.1.4 fix (a compound CRS in the vertical slot is rejected with a
clear message). See [v0.1.0](RELEASE_NOTES_v0.1.0.md) for the full feature list.

## Install

1. Download `crsmart.v0.1.5.zip` from the assets below.
2. In QGIS: **Plugins ▸ Manage and Install Plugins ▸ Install from ZIP**.
3. Enable **CRSmart** — a toolbar button toggles the dock, and the algorithms
   appear under **Processing Toolbox ▸ CRSmart**.

## Links

- Documentation: [`README.md`](../README.md), [`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md)
- Issues: https://github.com/Osman-Geomatics93/CRSmart/issues
- License: GPL-2.0-or-later

🤖 Generated with [Claude Code](https://claude.com/claude-code)
