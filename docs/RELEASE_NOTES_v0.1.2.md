# CRSmart v0.1.2

**Bug-fix release.** Makes the epoch-aware (4D) transform fail *clearly* instead
of with a cryptic PROJ traceback when no survey-grade transform is available.

## What changed

### Fixed

- **Epoch-aware transform no longer crashes with a cryptic PROJ traceback when
  only a ballpark transform exists.** The 4D transformer was built with
  `allow_ballpark=False`; PROJ aborts that with `ProjError: Error creating
  Transformer from CRS.` whenever the only available path is a low-accuracy
  ballpark transform — for example when a required PROJ datum grid is not
  installed. CRSmart now detects this and raises a clear, actionable message
  (`BallparkNotAllowedError`), and raises `TransformUnavailableError` when no
  operation exists between the two CRSs at all.
  (`crsmart/core/epoch.py`, `crsmart/core/errors.py`)

### Added

- **Explicit "Allow ballpark transform" opt-in on the Epoch-aware transform
  algorithm.** Off by default, honoring the survey-grade rule that a ballpark
  fallback is never silent — you must enable it deliberately. Engine errors are
  now surfaced as readable Processing messages rather than raw tracebacks.
  (`crsmart/processing/algorithms/epoch_transform.py`)

No API changes otherwise — see [v0.1.0](RELEASE_NOTES_v0.1.0.md) for the full
feature list.

## Install

1. Download `crsmart.v0.1.2.zip` from the assets below.
2. In QGIS: **Plugins ▸ Manage and Install Plugins ▸ Install from ZIP**.
3. Enable **CRSmart** — a toolbar button toggles the dock, and the algorithms
   appear under **Processing Toolbox ▸ CRSmart**.

## Links

- Documentation: [`README.md`](../README.md), [`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md)
- Issues: https://github.com/Osman-Geomatics93/CRSmart/issues
- License: GPL-2.0-or-later

🤖 Generated with [Claude Code](https://claude.com/claude-code)
