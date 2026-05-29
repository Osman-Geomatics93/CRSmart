# Publishing CRSmart to GitHub

The repository is committed locally but has **no remote yet**, and the URLs use
a placeholder slug (`osmangeomatics/crsmart`). Follow these steps once you decide
the real GitHub owner/repo name.

## 1. Create the GitHub repository

Either via the website (New repository → name it, e.g. `crsmart`, **do not** add
a README/license/.gitignore — the repo already has them), or with the GitHub CLI:

```powershell
gh repo create <owner>/<repo> --public --source . --remote origin --push
```

If you used `gh repo create ... --push`, you are done — skip to step 4.

## 2. Add the remote (if you created the repo on the website)

```powershell
git remote add origin https://github.com/<owner>/<repo>.git
git remote -v        # verify
```

## 3. Push

```powershell
git push -u origin main
```

## 4. Fix the slug if it is not `osmangeomatics/crsmart`

If your real `<owner>/<repo>` differs from the placeholder, update these files,
then commit and push:

- `crsmart/metadata.txt` — `tracker`, `repository`, `homepage`
- `pyproject.toml` — `[project.urls]` (Homepage / Repository / Issues)
- `.qgis-plugin-ci` — `github_organization_slug`, `project_slug`
- `README.md` — the `git clone` URL

```powershell
# Example: replace osmangeomatics/crsmart -> <owner>/<repo> across those files,
# then:
git add -A
git commit -m "chore: point repository URLs at <owner>/<repo>"
git push
```

> Ask the assistant to do this replacement in one pass — just give it the real
> `<owner>/<repo>`.

## 5. Watch CI

Pushing to `main` triggers `.github/workflows/ci.yml`:

- **lint** (ruff + black + mypy)
- **qt6-check** (Qt5→Qt6 compatibility)
- **test** — QGIS 3.40 LTR + QGIS 4.x containers (this is where the
  Processing/GUI pytest-qgis tests finally run)
- **package** — builds and verifies the plugin zip, uploads it as an artifact

Open the **Actions** tab to confirm everything is green. If a QGIS-only test
fails, that is the first real signal we have — fix and push again.

## 6. Cut a release (optional, when ready)

The `release` job runs only on a version tag and publishes to the OSGeo plugin
repository via `qgis-plugin-ci`.

1. Add repository **secrets** `OSGEO_USERNAME` / `OSGEO_PASSWORD`
   (your plugins.qgis.org credentials).
2. Tag and push:

   ```powershell
   git tag -a v0.1.0 -m "CRSmart 0.1.0"
   git push origin v0.1.0
   ```

The job builds the zip, attaches it to the GitHub release, and uploads it to
plugins.qgis.org.
