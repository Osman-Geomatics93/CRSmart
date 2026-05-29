# Sample data for the calibration demo

Two ready-to-use control-point files for the **Calibrate** tab / the
`CRSmart ▸ Fit local site calibration` algorithm. Columns are
`local_x, local_y, target_x, target_y` with a header row.

Both were generated from a **known** 2D conformal Helmert transform:

| Parameter | Value |
|---|---|
| scale | 1.0000150 (15 ppm) |
| rotation | 0.35° |
| translation | tx = 12000, ty = −8000 |

### `sample_control_points.csv`
Clean points (no noise). Fitting recovers the parameters above exactly and
reports an RMSE of ~0 with **no outliers** — a sanity check that the fit and the
emitted PROJ pipeline are correct.

### `sample_control_points_with_outlier.csv`
Identical, except point **index 4** has a deliberate ~20 m blunder. Fitting flags
that point as an **outlier** (standardized residual ~9.9, well above the 3.5
threshold), demonstrating CRSmart's blunder detection.

Try it: load either file in the Calibrate tab, choose **Helmert**, and click
**Fit calibration**.
