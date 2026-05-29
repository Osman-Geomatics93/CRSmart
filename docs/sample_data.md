# Sample data for testing CRSmart

Ready-to-load datasets for exercising every feature in the GUI dock and the
Processing algorithms. All files are plain CSV. Pair this with the step-by-step
checklist in [`TESTING.md`](TESTING.md).

> **How to load a CSV as a point layer:** `Layer ▸ Add Layer ▸ Add Delimited
> Text Layer…`, pick the file, set **X field** and **Y field** (see each section
> below), and — importantly — set **Geometry CRS** to the CRS named below. That
> "assign on load" step is what makes the transformation tests meaningful.

| File | Use with | Load as / assign CRS |
|---|---|---|
| `sample_points_adindan_sudan.csv` | A. Recommend, Reproject | X=`x`, Y=`y`, CRS **EPSG:4201 (Adindan)** |
| `sample_points_itrf2014_australia.csv` | B. Epoch-aware transform | X=`lon`, Y=`lat`, CRS **EPSG:7912 (ITRF2014)** |
| `sample_control_points.csv` | C. Calibration (clean) | not a map layer — used directly in the Calibrate tab |
| `sample_control_points_with_outlier.csv` | C. Calibration (blunder) | not a map layer |
| `sample_points_heights_sudan.csv` | D. Vertical CRS repair | X=`lon`, Y=`lat`, CRS **EPSG:4326 (WGS 84)** |

---

## A. Recommend a transformation / Reproject — `sample_points_adindan_sudan.csv`

Six Sudanese cities. Adindan is the classic local datum for Sudan, so a transform
to WGS 84 is a real (non-identity) datum shift of several metres.

**Recommend tab** (no layer needed): Source = **EPSG:4201 (Adindan)**, Target =
**EPSG:4326 (WGS 84)** → *Find transformations*.
- Expect ~3 candidates including a parametric Helmert whose **accuracy** is
  ~**6 m** (that is the transform's *uncertainty*), plus a ballpark fallback;
  CRSmart recommends the 6 m Helmert, never the ballpark.

**Reproject (explicit operation):** load the CSV as **EPSG:4201**, then run
`CRSmart ▸ Reproject layer (explicit operation)` to **EPSG:4326**. Paste the
recommended pipeline into `OPERATION` to pin it. Compare a point before/after —
it moves by roughly **90 m** (the size of the Adindan→WGS 84 datum shift in
Sudan), not the ~6 m accuracy figure. Datum *offset* and transform *uncertainty*
are different things, and that is exactly what CRSmart makes explicit.

---

## B. Epoch-aware transform — `sample_points_itrf2014_australia.csv`

Five Australian cities. Australia sits on a fast-moving plate (~7 cm/year). The
classic case is transforming between the **global dynamic** frame ITRF2014 and
the **plate-fixed** national datum GDA2020 (pinned to the plate at epoch 2020.0):
a point's ITRF coordinates drift with time, so the transform needs a **coordinate
epoch**.

1. Load the CSV with X=`lon`, Y=`lat`, CRS = **EPSG:7912 (ITRF2014)**.
2. **Epoch tab:** pick the layer, Target = **EPSG:7843 (GDA2020)**.
3. *Explain epoch requirement* → it states an epoch **is required** and why.
4. Run with the **epoch unset** → CRSmart **refuses** (the safety behavior).
5. Set epoch **2020.0** → it runs.
6. Run again at **1995.0** vs **2025.0** → the output coordinates **differ by
   ~1.7 m** (30 years × ~5.7 cm/yr of plate motion). That difference *is* the point.

> Note: ITRF2014 → ITRF2008 (EPSG:7911) also *requires* an epoch (both are
> dynamic), but two global frames barely move relative to each other, so the
> 1995-vs-2025 difference is near zero. Use a dynamic↔plate-fixed pair like
> ITRF2014 ↔ GDA2020 to actually *see* plate motion.

---

## C. Local site calibration — `sample_control_points*.csv`

Two control-point files for the **Calibrate** tab / `CRSmart ▸ Fit local site
calibration`. Columns are `local_x, local_y, target_x, target_y` with a header
row. Both have **12 points** with ~0.02 m noise. Fitting the clean set recovers
(the values the engine actually returns for this data):

| Parameter | Value |
|---|---|
| scale | ≈ 1.0000107 (~10.7 ppm) |
| rotation | ≈ 0.35° |
| translation | tx ≈ 12000, ty ≈ −8000 |

- **`sample_control_points.csv`** — clean: RMSE a few cm, **no outliers**. A
  sanity check that the fit and the emitted PROJ pipeline are correct.
- **`sample_control_points_with_outlier.csv`** — identical except point **index
  4** has a deliberate ~20 m blunder, which is flagged as an **outlier**
  (standardized residual above the 3.5σ threshold).

Try it: load either file in the Calibrate tab, choose **Helmert**, **Fit**.

---

## D. Repair a missing vertical CRS — `sample_points_heights_sudan.csv`

Five points with an orthometric height column (`h_ortho_m`) but **no vertical CRS
declared** — the situation CRSmart's vertical repair fixes.

1. Load the CSV with X=`lon`, Y=`lat`, CRS = **EPSG:4326 (WGS 84)**. (The height
   column rides along as an attribute; the layer has no vertical CRS.)
2. **Vertical tab:** *Detect vertical CRS* → reports none/missing.
3. Horizontal = **EPSG:4326**, Vertical = **EPSG:5773 (EGM96 height)** →
   *Assemble compound CRS* → *Copy compound WKT*.
4. Expect a `COMPOUNDCRS[...]` combining WGS 84 + EGM96 height. The Processing
   version can write a copy with that compound CRS **assigned** (it relabels what
   the coordinates mean; it does not move them).
