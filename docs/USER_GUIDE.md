# CRSmart user guide

CRSmart makes CRS / datum transformation **transparent about accuracy and
epoch**. This guide walks through each of the four features, in both the GUI
panel and the Processing Toolbox.

> Reminder: CRSmart never makes a network request without your explicit consent,
> and never silently uses a *ballpark* (unknown-accuracy) transform for
> survey-grade work.

---

## Opening CRSmart

- **GUI panel:** `Plugins ▸ CRSmart` (or the CRSmart toolbar button) toggles a
  dockable panel with four tabs.
- **Processing algorithms:** `Processing ▸ Toolbox ▸ CRSmart` lists the five
  algorithms (scriptable and usable in models / batch).

---

## A. Recommend a transformation (with uncertainty)

**The problem it solves:** QGIS often offers several transformations between two
CRSs with no guidance on which is best or how accurate it is.

**GUI (Recommend tab)**
1. Choose a **Source CRS** and **Target CRS**.
2. Click **Find transformations**. The table lists each candidate with its
   accuracy (m), whether it is *ballpark*, whether it is locally *available*,
   and the grids it needs.
3. The best non-ballpark, locally-available operation is **recommended** (shown
   in the message bar). Select any row and **Copy pipeline** to reuse its PROJ
   string elsewhere.
4. If a more accurate operation needs a grid you do not have, select it and
   **Download missing grid…**. You will be asked to confirm before any download.

**Processing:** `CRSmart ▸ Recommend transformation (with uncertainty)`
- Inputs: source CRS, target CRS, optional area of interest, *Allow ballpark*.
- Outputs: recommended PROJ pipeline, recommended accuracy (m), *ballpark only*
  flag, and an optional HTML report of all candidates.

> **Example (Sudan):** Adindan (EPSG:4201) → WGS 84 (EPSG:4326) returns several
> parametric Helmert operations (~6–9 m) and a ballpark fallback. CRSmart
> recommends the most accurate Helmert and never the ballpark.

---

## B. Epoch-aware transform (dynamic datums)

**The problem it solves:** modern plate-fixed frames (ITRF realizations,
GDA2020, NATRF2022) drift with time. A correct transform is *time-dependent* and
needs a **coordinate epoch** (decimal year). Most tools handle this poorly.

**GUI (Epoch tab)**
1. Pick a **point layer** and a **Target CRS**.
2. Set the **coordinate epoch** (e.g. `2020.0`), or leave it unset.
3. Click **Explain epoch requirement** to see, in plain language, whether an
   epoch is required and why.
4. Click **Run epoch transform**. If an epoch is required but unset, CRSmart
   refuses to run rather than silently producing wrong coordinates.

**Processing:** `CRSmart ▸ Epoch-aware transform (dynamic datums)`
- Inputs: point layer, target CRS, optional epoch. Z values are carried through;
  layers without Z assume height 0.

> **Example:** ITRF2014 (EPSG:7912) → ITRF2008 (EPSG:7911) at epoch 2010.0
> reproduces published coordinates within tolerance; running the same point at
> 1995 vs 2025 yields different results — that is plate motion.

---

## C. Local site calibration (Helmert / affine)

**The problem it solves:** surveyors need to fit a local site grid from control
points, see residuals, and reuse the calibration — with no friendly native tool.

**GUI (Calibrate tab)**
1. Enter control points, one per line: `local_x, local_y, target_x, target_y`
   (or **Load CSV…**; a header row is auto-detected).
2. Choose **Helmert** (conformal: scale, rotation, translation) or **Affine**
   (6-parameter). Set the outlier threshold (default 3.5σ).
3. Click **Fit calibration**. Review the RMSE, computed parameters, the
   per-point residual table, and any flagged **outliers**.
4. **Copy pipeline** to reuse the calibration as a `+proj=affine` PROJ string.

**Processing:** `CRSmart ▸ Fit local site calibration (Helmert/affine)`
- Input: control-points CSV. Outputs: PROJ pipeline, RMSE, number of outliers,
  and an optional HTML report (parameters + residuals).

> **Tip:** the emitted pipeline is an exact `+proj=affine` encoding that
> round-trips through PROJ — the same transform CRSmart fitted.

---

## D. Repair a missing vertical CRS

**The problem it solves:** data (especially point clouds / LAS) frequently loads
with "vertical CRS missing!" and there is no clean way to fix it.

**GUI (Vertical tab)**
1. Optionally pick a **layer** (its CRS becomes the horizontal default).
2. Click **Detect vertical CRS** to see the current vertical status.
3. Choose a **Horizontal CRS** and a **Vertical CRS**, then **Assemble compound
   CRS**. **Copy compound WKT** to reuse it.

**Processing:** `CRSmart ▸ Repair vertical CRS (assemble compound)`
- Inputs: optional layer, horizontal CRS (defaults to the layer's), vertical CRS.
- Output: the compound CRS WKT; optionally writes a copy of the layer with the
  compound CRS **assigned** (this declares what existing coordinates mean — it
  does not move them).

---

## Reproject a layer with an explicit operation

`CRSmart ▸ Reproject layer (explicit operation)` writes a reprojected copy of a
vector layer. Unlike the native tool, you can **pin a specific PROJ operation**
(paste the pipeline from *Recommend*) so the exact transformation used is
explicit and reproducible.

---

## Grids and the network

When a high-accuracy operation needs a PROJ grid you do not have installed,
CRSmart can fetch it from the PROJ CDN (`https://cdn.proj.org`) — but **only
after you confirm**. Nothing is downloaded, and the PROJ network is never
enabled, as a side effect of browsing transformations.
