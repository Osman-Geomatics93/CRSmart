# Manual testing checklist

A repeatable, by-hand acceptance pass for a CRSmart build installed in QGIS.
It exercises both surfaces (the dockable panel **and** the Processing
algorithms) and uses the repo's sample data, which has **known** expected
results. Automated tests live in `tests/` and run in CI; this checklist is for
verifying the *installed plugin* in a real QGIS.

> Run it on **both** QGIS 3.40 LTR (Qt5) and a QGIS 4.x (Qt6) build when you can
> — that is the portability matrix the plugin targets.

**Fast automated pass:** for a one-shot PASS/FAIL of sections 1–6 (engine +
Processing registration + the safety gates), paste
`scripts/qgis_console_smoketest.py` into the QGIS **Python Console**, or run:
>
>     exec(open(r"<repo>/scripts/qgis_console_smoketest.py").read())
>
> It needs no files or network (sample data is embedded). Use the manual steps
> below for the GUI tabs, which the script does not drive.

Sample data referenced below lives in `docs/` (adjust the absolute path to wherever
you cloned the repo):

- `docs/sample_control_points.csv` — 12 clean control points
- `docs/sample_control_points_with_outlier.csv` — same, with one ~20 m blunder at index 4

---

## 0. Pre-flight (catch load errors first)

- [ ] **Plugins ▸ Manage and Install Plugins ▸ Installed** → CRSmart is enabled, **version 0.1.1**.
- [ ] Open **View ▸ Panels ▸ Log Messages**; check the **Plugins** and **Python** tabs. Reload the plugin (use *Plugin Reloader*, or toggle CRSmart off/on) — **no red tracebacks**.
- [ ] Toolbar button / **Plugins ▸ CRSmart** toggles a **dock with 4 tabs** (Recommend / Epoch / Calibrate / Vertical).
- [ ] **Processing ▸ Toolbox ▸ CRSmart** lists **5 algorithms**.

---

## A. Recommend transformation (with uncertainty)

**GUI — Recommend tab:** Source = **Adindan (EPSG:4201)**, Target = **WGS 84 (EPSG:4326)** → **Find transformations**.

- [ ] Table lists several parametric **Helmert** operations (~6–9 m) **plus** a ballpark fallback.
- [ ] The message bar recommends the **most accurate non-ballpark** op — **never the ballpark**.
- [ ] Select a row → **Copy pipeline** → it is a valid PROJ string.

**Processing — `Recommend transformation (with uncertainty)`:**

- [ ] `SOURCE_CRS=EPSG:4201`, `TARGET_CRS=EPSG:4326`, **Allow ballpark** off → outputs `RECOMMENDED_PIPELINE`, `RECOMMENDED_ACCURACY`, and `BALLPARK_ONLY = False`.
- [ ] For a CRS pair with no real operation, **Allow ballpark** on → `BALLPARK_ONLY = True`; with it off → no recommendation (ballpark refused).

---

## B. Epoch-aware transform (dynamic datums) — *the refusal is the test*

Load `sample_points_itrf2014_australia.csv` as **ITRF2014 (EPSG:7912)**. Target = **GDA2020 (EPSG:7843)** — a global-dynamic ↔ plate-fixed pair, so plate motion is actually visible.

**GUI — Epoch tab:**

- [ ] **Explain epoch requirement** states an epoch **is required** and why.
- [ ] **Run with the epoch unset** → CRSmart **refuses** (no silent output). *(key safety behavior)*
- [ ] Set epoch **2020.0** → runs and produces output.
- [ ] Same point at **1995.0** vs **2025.0** → coordinates **differ by ~1.7 m** (30 yr × ~5.7 cm/yr plate motion).

**Processing — `Epoch-aware transform`:** `INPUT` layer, `TARGET_CRS=EPSG:7843`, `EPOCH` empty → errors out; with `EPOCH=2020.0` → succeeds.

> ITRF2014 → ITRF2008 (EPSG:7911) also requires an epoch, but two global frames barely move relative to each other — the 1995-vs-2025 difference is ~0. Use the dynamic↔plate-fixed pair above to *see* the effect.

---

## C. Local site calibration (Helmert / affine) — *deterministic, exact numbers*

The fit recovers a near-conformal transform: scale **≈ 1.0000107 (~10.7 ppm)**, rotation **≈ 0.35°**, tx **≈ 12000**, ty **≈ −8000**.

**GUI — Calibrate tab:** **Load CSV…** `sample_control_points.csv`, Method = **Helmert**, threshold 3.5 → **Fit**.

- [ ] Recovers scale ≈ 1.0000107 (~10.7 ppm), rotation ≈ 0.35°, tx ≈ 12000, ty ≈ −8000.
- [ ] **RMSE a few cm**, **0 outliers**.
- [ ] **Copy pipeline** → a `+proj=affine` string.
- [ ] Load `sample_control_points_with_outlier.csv` → exactly **1 outlier flagged at index 4** (standardized residual ~4.2).

**Scripted check (QGIS Python Console — most reproducible):**

```python
import processing
res = processing.run("crsmart:fitcalibration", {
    "INPUT_CSV": r"<repo>/docs/sample_control_points.csv",
    "METHOD": 0,            # 0 = Helmert, 1 = Affine
    "OUTLIER_THRESHOLD": 3.5,
    "OUTPUT_HTML": "TEMPORARY_OUTPUT",
})
print("RMSE:", res["RMSE"], "outliers:", res["N_OUTLIERS"])
print(res["PIPELINE"])
# Expect RMSE ~0.0x m and N_OUTLIERS = 0; the _with_outlier file gives N_OUTLIERS = 1.

# Round-trip the emitted pipeline to prove it is exact:
from pyproj import Transformer
t = Transformer.from_pipeline(res["PIPELINE"])
print(t.transform(100.0, 200.0))   # ≈ (12098.76, -7799.38) = row 1 of the CSV
```

---

## D. Repair vertical CRS

**GUI — Vertical tab:** **Detect vertical CRS** on a plain 2D layer → reports missing/none. Horizontal = **EPSG:4326**, Vertical = **EGM96 height (EPSG:5773)** → **Assemble compound CRS** → **Copy compound WKT**.

- [ ] WKT is a `COMPOUNDCRS[...]` containing both the horizontal and vertical components.
- [ ] **Processing — `Repair vertical CRS`** with the optional output layer enabled writes a copy with the compound CRS **assigned** — coordinates unchanged (it relabels, does not move them).

---

## E. Reproject layer (explicit operation)

- [ ] `Reproject layer (explicit operation)`: paste `RECOMMENDED_PIPELINE` from step A into `OPERATION`, reproject a layer, and confirm it uses **that** op (compare against leaving `OPERATION` blank).

---

## F. No-silent-network / consent gate (a headline guarantee)

**GUI — Recommend tab:** pick a CRS pair whose best op needs a grid you do **not** have (a NTv2 / geoid case) → select it → **Download missing grid…**.

- [ ] A **confirmation dialog** appears **first**. Cancel → nothing downloads; PROJ network stays off.
- [ ] Merely browsing transformations **never** triggers a download.

**Scripted proof the engine never goes online without consent:**

```python
from crsmart.core import grids
from crsmart.core.models import GridInfo
g = GridInfo(short_name="x.tif", url="https://cdn.proj.org/x.tif",
             open_license=True, available=False, direct_download=True)
try:
    grids.download_grids([g], consent=False)   # raises ConsentRequiredError
except Exception as e:
    print("blocked as expected:", type(e).__name__)
print("network enabled?", grids.is_network_enabled())  # still False
```

---

## When something breaks — where to look

- **Log Messages** panel → *Python* / *Plugins* / *Processing* tabs = the actual traceback.
- **First Aid** plugin → drops you into the exception with a stack / locals inspector.
- **Plugin Reloader** → reload after a change without restarting QGIS.
