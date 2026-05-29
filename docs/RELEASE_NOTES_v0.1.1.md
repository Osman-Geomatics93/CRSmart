# CRSmart v0.1.1

**Security fix release.** Re-submission of the first public version after the
plugins.qgis.org security scan blocked v0.1.0.

## What changed

- **Restrict PROJ-CDN grid downloads to HTTP(S) schemes.** The grid downloader
  now rejects any non-`http`/`https` URL (for example a crafted `file:`, `ftp:`,
  or custom-scheme `GridInfo.url`) and connects through an opener wired with only
  HTTP(S) handlers — there is no `file`/`ftp` handler to fall back to, so a
  local-file or alternate-scheme fetch cannot happen even if the up-front scheme
  check were bypassed. This resolves the Bandit **B310** finding that blocked
  v0.1.0 on plugins.qgis.org. (`crsmart/core/grids.py`)

No functional or API changes otherwise — see [v0.1.0](RELEASE_NOTES_v0.1.0.md)
for the full feature list.

## Install

1. Download `crsmart.v0.1.1.zip` from the assets below.
2. In QGIS: **Plugins ▸ Manage and Install Plugins ▸ Install from ZIP**.
3. Enable **CRSmart** — a toolbar button toggles the dock, and the algorithms
   appear under **Processing Toolbox ▸ CRSmart**.

## Links

- Documentation: [`README.md`](../README.md), [`docs/USER_GUIDE.md`](../docs/USER_GUIDE.md)
- Issues: https://github.com/Osman-Geomatics93/CRSmart/issues
- License: GPL-2.0-or-later

🤖 Generated with [Claude Code](https://claude.com/claude-code)
