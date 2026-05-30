<div align="center">

# 📘 CRSmart User Guide

### Learn CRS & datum transformation the transparent way — by doing

*Every section below is a hands-on tutorial: **sample data → exact steps → the result you should see**.
All numbers here were produced by the bundled sample data, so you can check your own run against them.*

</div>

---

## Contents

1. [The big ideas (read this first)](#ideas)
2. [Install & open CRSmart](#install)
3. [The sample data](#sample-data)
4. [Tutorial A — Recommend a transformation](#a-recommend)
5. [Tutorial — Reproject with an explicit operation](#reproject)
6. [Tutorial B — Epoch-aware transform](#b-epoch)
7. [Tutorial C — Local site calibration](#c-calibrate)
8. [Tutorial D — Repair a vertical CRS](#d-vertical)
9. [Two safety guarantees](#safety)
10. [Troubleshooting & FAQ](#faq)
11. [Glossary](#glossary)

---

<a id="ideas"></a>
## 1 · The big ideas (read this first)

CRSmart is built around **honesty about accuracy and time**. Four ideas explain everything it does:

| Idea | What it means | Why it matters |
|---|---|---|
| 📏 **Accuracy ≠ offset** | A transform's *accuracy* (e.g. "6 m") is how well the relationship is **known**. The *offset* is how far points actually **move** (e.g. ~100 m). | They're different numbers — CRSmart shows **both** so you don't confuse "uncertain" with "didn't move". |
| ⚠️ **Ballpark transforms** | A "ballpark" is a last-resort transform of **unknown** accuracy. | CRSmart **never** recommends one silently; you must opt in explicitly. |
| ⏱️ **Coordinate epoch** | On *dynamic* datums (ITRF, GDA2020…), coordinates **drift with time**, so a correct transform needs a date (decimal year). | Skip it and you can be wrong by centimetres-to-metres. CRSmart **refuses** to guess. |
| 🔌 **Consent for network** | High-accuracy transforms sometimes need a PROJ grid you don't have. | CRSmart downloads grids **only after you confirm** — never silently. |

> Keep these in mind and the rest of the tool is intuitive.

---

<a id="install"></a>
## 2 · Install & open CRSmart

**Install**
- **Plugin Manager:** `Plugins ▸ Manage and Install Plugins` → search **CRSmart** → Install.
- **From ZIP:** download `crsmart.vX.Y.Z.zip` from [Releases](https://github.com/Osman-Geomatics93/CRSmart/releases) → `Plugins ▸ Manage and Install Plugins ▸ Install from ZIP`.

**Open it — two ways, same engine**
- 🪟 **Dock panel:** the **CRSmart** toolbar button (or `Plugins ▸ CRSmart`) opens a panel with four tabs.
- ⚙️ **Processing Toolbox:** `Processing ▸ Toolbox ▸ CRS & datum tools` lists five algorithms (scriptable, batchable, model-friendly).

<div align="center">
  <img src="images/processing-toolbox.png" alt="CRSmart tools in the Processing Toolbox" width="520">
  <br><sub><i>The five CRSmart algorithms in the Processing Toolbox.</i></sub>
</div>

> 💡 **Setting a CRS:** the Source/Target fields are QGIS **CRS pickers**, not text boxes — click one, then type the **EPSG number** (e.g. `4326`) or name in the **Filter** box and pick it.

---

<a id="sample-data"></a>
## 3 · The sample data

All tutorials use the files in the plugin's `docs/` folder. Load CSVs via
**Layer ▸ Add Layer ▸ Add Delimited Text Layer…**, and **set the Geometry CRS** as shown.

| File | Used in | X / Y | Geometry CRS |
|---|---|---|---|
| `sample_points_adindan_sudan.csv` | A, Reproject | `x` / `y` | **EPSG:4201** (Adindan) |
| `sample_points_itrf2014_australia.csv` | B | `lon` / `lat` | **EPSG:7912** (ITRF2014) |
| `sample_control_points.csv` | C | — (pasted/loaded in the tool) | — |
| `sample_control_points_with_outlier.csv` | C | — | — |
| `sample_points_heights_sudan.csv` | D | `lon` / `lat` | **EPSG:4326** (WGS 84) |

> ⚠️ Assigning the **correct CRS on load** is what makes a transform meaningful — it tells QGIS what the numbers already are.

---

<a id="a-recommend"></a>
## 4 · Tutorial A — Recommend a transformation *(with uncertainty)*

**Goal:** see every way to go from one CRS to another, ranked by accuracy — and learn why CRSmart won't ballpark silently.

<div align="center">
  <img src="images/recommend-transformation.png" alt="Recommend Transformation dialog" width="780">
</div>

**Steps**
1. Open the **Recommend** tab (or `Processing ▸ Recommend transformation`).
2. **Source CRS** = `EPSG:4201` (Adindan, Sudan). **Target CRS** = `EPSG:4326` (WGS 84).
3. Leave **Allow ballpark** unchecked. Click **Find transformations**.

**✅ Result you should see**

| # | Operation | Accuracy | Ballpark | Available |
|---|---|---|---|---|
| 1 ⭐ | Adindan → WGS 84 **(4)** | **6 m** | no | yes |
| 2 | Adindan → WGS 84 **(7)** | 7 m | no | yes |
| 3 | Adindan → WGS 84 **(1)** | 9 m | no | yes |

- The **6 m** operation is **recommended** (best non-ballpark). Select it → **Copy pipeline**:
  ```
  +proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +inv +proj=longlat
  +a=6378249.145 +rf=293.465 +step +proj=push +v_3 +step +proj=cart +a=6378249.145 +rf=293.465
  +step +proj=helmert +x=-165 +y=-11 +z=206 +step +inv +proj=cart +ellps=WGS84 +step +proj=pop
  +v_3 +step +proj=unitconvert +xy_in=rad +xy_out=deg
  ```

> 📏 **Read it right:** "6 m" is the *uncertainty* of the Adindan→WGS 84 relationship. The `+helmert +x=-165 +y=-11 +z=206` is the datum shift — the points themselves will move **~100 m** (next tutorial). Different numbers, both shown.

---

<a id="reproject"></a>
## 5 · Tutorial — Reproject with an explicit operation

**Goal:** apply *exactly* the operation you chose (not PROJ's default guess) and confirm the points moved correctly.

<div align="center">
  <img src="images/reproject-layer.png" alt="Reproject Layer dialog" width="780">
</div>

**Steps**
1. Load `sample_points_adindan_sudan.csv` (X=`x`, Y=`y`, **CRS = EPSG:4201**).
2. `Processing ▸ Reproject layer (explicit operation)`:
   - **Input** = the Adindan layer
   - **Target CRS** = `EPSG:4326`
   - **PROJ coordinate operation** = *paste the pipeline copied in Tutorial A*
   - **Run**

**✅ Result you should see** (open the new layer's attribute table — compare `wkt_geom`):

| Point | Adindan (in) | WGS 84 (out) | Moved |
|---|---|---|---|
| Khartoum | 32.55990, 15.50070 | **32.56064, 15.50122** | ~98 m |
| Omdurman | 32.47990, 15.64450 | **32.48064, 15.64501** | ~98 m |
| Wad Madani | 33.51990, 14.40120 | **33.52066, 14.40181** | ~106 m |
| Kosti | 32.66350, 13.16290 | **32.66424, 13.16361** | ~113 m |
| Port Sudan | 37.21640, 19.61580 | **37.21727, 19.61598** | ~93 m |
| El Obeid | 30.21670, 13.18330 | **30.21738, 13.18402** | ~109 m |

> ⚠️ **Reproject moves geometry, not attribute columns.** If your CSV had `x`/`y` *columns*, they keep the old values — trust `wkt_geom`. To get new coordinate columns, use the Field Calculator (`$x`, `$y`) on the reprojected layer.

---

<a id="b-epoch"></a>
## 6 · Tutorial B — Epoch-aware transform *(dynamic datums)*

**Goal:** transform between a **dynamic** frame (ITRF2014) and a **plate-fixed** datum (GDA2020), and *see plate motion*.

<div align="center">
  <img src="images/epoch-transform.png" alt="Epoch-Aware Transform dialog" width="780">
</div>

**Steps**
1. Load `sample_points_itrf2014_australia.csv` (X=`lon`, Y=`lat`, **CRS = EPSG:7912**).
2. **Epoch** tab → **Point layer** = that layer, **Target CRS** = `EPSG:7843` (GDA2020).
3. **Explain epoch requirement** → it states an epoch **is required** and why.
4. Run with the **epoch unset** → CRSmart **refuses** (no output). *This refusal is the safety feature.*
5. Set **epoch = 2020.0** → **Run epoch transform** → a **"Transformed"** layer is added.
6. Run again at **1995.0** and **2025.0** (rename each output), then compare the same point.

**✅ Result you should see** (same point, two epochs):

| City | @ 1995 (lon, lat) | @ 2025 (lon, lat) | Difference |
|---|---|---|---|
| Sydney | 151.209305, −33.868788 | 151.209299, −33.868802 | **≈ 1.7 m** |

> ⏱️ The **same physical point** has different coordinates 30 years apart — the Australian plate drifts ~5–7 cm/year. **That difference is the whole reason epochs exist.**

> 🧭 **Common pitfall:** run each epoch from the **original ITRF2014 layer**, not from a previous output. If you feed the GDA2020 result back in, you'll see *"Neither CRS is dynamic"* — correct, because GDA2020 is plate-fixed, but not the comparison you want.

---

<a id="c-calibrate"></a>
## 7 · Tutorial C — Local site calibration *(Helmert / affine)*

**Goal:** fit a local transform from matched control points, read its quality, and catch a bad point.

<div align="center">
  <img src="images/site-calibration.png" alt="Fit Local Site Calibration dialog" width="780">
</div>

**Steps (clean fit)**
1. **Calibrate** tab → **Load CSV…** `sample_control_points.csv` (columns `local_x, local_y, target_x, target_y`).
2. **Method** = Helmert (conformal). **Outlier threshold** = `3.5`. Click **Fit**.

**✅ Result you should see**

| Parameter | Value |
|---|---|
| Scale | **1.0000107** (~10.7 ppm) |
| Rotation | **0.35°** |
| Translation | tx **12000**, ty **−8000** |
| RMSE | **~0.025 m** (a few cm) |
| Outliers | **0** |

→ **Copy pipeline** gives a reusable `+proj=affine …` string.

**Steps (catch the blunder)**
3. **Load CSV…** `sample_control_points_with_outlier.csv` → **Fit**.

**✅ Result:** **1 outlier flagged at index 4**, and **RMSE jumps to ~4.9 m** — your alarm that one point is bad. The fit points right at it instead of absorbing the error.

---

<a id="d-vertical"></a>
## 8 · Tutorial D — Repair a vertical CRS

**Goal:** fix data that loads with **no vertical CRS** by assembling a **compound** (horizontal + vertical) CRS.

<div align="center">
  <img src="images/vertical-repair.png" alt="Repair Vertical CRS dialog" width="780">
</div>

**Steps**
1. Load `sample_points_heights_sudan.csv` (X=`lon`, Y=`lat`, **CRS = EPSG:4326**). It has an `h_ortho_m` height column but no vertical CRS.
2. **Vertical** tab → **Detect vertical CRS** → reports **none**.
3. **Horizontal CRS** = `EPSG:4326`. **Vertical CRS** → pick the **EGM96 height (EPSG:5773)** preset.
4. **Assemble compound CRS** → **Copy compound WKT**.

**✅ Result you should see**
```
COMPOUNDCRS["WGS 84 + EGM96 height",
  GEOGCRS["WGS 84", … ID["EPSG",4326]],
  VERTCRS["EGM96 height", … ID["EPSG",5773]]]
```
(With an Input layer + Output set, a copy is written with this CRS **assigned** — it relabels what the heights mean; it does **not** move points.)

> 💡 **Choosing the vertical CRS:** QGIS's CRS picker often won't list pure vertical CRSs, so CRSmart gives you a **presets dropdown** (EGM96, EGM2008, NAVD88, …) **plus a custom field** where you can type any code (`EPSG:5773`) / WKT / PROJ string.
>
> ⚠️ Pick a *standalone* vertical CRS like **EGM96 height (EPSG:5773)** — **not** "WGS 84 + EGM96 height" (EPSG:9707), which is already a compound. CRSmart rejects a compound here with a clear message.

---

<a id="safety"></a>
## 9 · Two safety guarantees

**🛡️ No silent ballpark.** With *Allow ballpark* off, a pair with no real operation yields **no recommendation** — CRSmart won't quietly hand you an unknown-accuracy transform. In the Epoch tool, a ballpark-only target gives a **clear message** (not a crash); tick *Allow ballpark transform* to proceed deliberately.

**🔌 No silent network.** Choosing an operation that needs a grid you don't have offers **Download missing grid…**, which **always asks first**. Cancel → nothing is fetched. Merely browsing transformations never touches the network.

---

<a id="faq"></a>
## 10 · Troubleshooting & FAQ

<details>
<summary><b>The transformed layer's <code>x</code>/<code>y</code> columns didn't change.</b></summary>

That's expected — reprojection moves the **geometry** (`wkt_geom`), not stored attribute columns. Use the Field Calculator (`$x`, `$y`) on the reprojected layer if you need coordinate columns.
</details>

<details>
<summary><b>"Neither CRS is dynamic; a coordinate epoch is not needed."</b></summary>

You ran the epoch transform on a layer that's already in a static (plate-fixed) CRS — often a previous output. Start from the **original dynamic layer** (e.g. ITRF2014, EPSG:7912).
</details>

<details>
<summary><b>I can't find a vertical CRS (e.g. EPSG:5773) in the picker.</b></summary>

QGIS's CRS selector doesn't list standalone vertical CRSs on many builds. Use CRSmart's **vertical presets dropdown**, or type the code in the **custom field** (`EPSG:5773`).
</details>

<details>
<summary><b>"… is not a standalone vertical (height) CRS."</b></summary>

You chose a *compound* CRS (e.g. EPSG:9707 "WGS 84 + EGM96 height") in the Vertical slot. Pick a pure vertical CRS such as **EGM96 height (EPSG:5773)** instead.
</details>

<details>
<summary><b>Where do I see errors?</b></summary>

`View ▸ Panels ▸ Log Messages` → the **Python** / **Plugins** / **Processing** tabs show the full detail.
</details>

---

<a id="glossary"></a>
## 11 · Glossary

| Term | Meaning |
|---|---|
| **CRS** | Coordinate Reference System — how coordinates map to the Earth. |
| **Datum** | The reference surface/frame a CRS is tied to (e.g. WGS 84, Adindan). |
| **Transformation accuracy** | How well a datum transformation is **known**, in metres. Not the same as how far points move. |
| **Ballpark transform** | A fallback transform of **unknown** accuracy (often just a datum-less approximation). |
| **Dynamic datum** | A plate-fixed/Earth-fixed frame whose coordinates **change over time** (ITRF, GDA2020). |
| **Coordinate epoch** | The date (decimal year) coordinates refer to, needed for dynamic datums. |
| **Helmert / affine** | Least-squares fits mapping one set of points to another (4- and 6-parameter). |
| **Compound CRS** | A CRS combining a **horizontal** CRS + a **vertical** (height) CRS. |
| **PROJ pipeline** | A reusable, explicit string describing the exact transformation steps. |

---

<div align="center">

**Questions or issues?** → [github.com/Osman-Geomatics93/CRSmart/issues](https://github.com/Osman-Geomatics93/CRSmart/issues)
· Hands-on acceptance checklist: [`TESTING.md`](TESTING.md) · Sample data details: [`sample_data.md`](sample_data.md)

</div>
