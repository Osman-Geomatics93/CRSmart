"""Feature C -- local site calibration by least squares (pure Python + numpy).

This is the ONLY geodetic math CRSmart implements itself: a 2D conformal Helmert
(4-parameter) and a 6-parameter affine fit from matched control points. The
result is emitted as an exact, unit-unambiguous ``+proj=affine`` PROJ pipeline
(a conformal Helmert is a constrained affine, so the affine encoding reproduces
it exactly and round-trips through ``Transformer.from_pipeline``). The geometric
Helmert parameters (scale, rotation, translation) are also reported.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from typing import Union

import numpy as np

from .errors import CalibrationError
from .models import CalibrationResult, Residual

PointArray = Union[Sequence[Sequence[float]], np.ndarray]

_DEFAULT_OUTLIER_THRESHOLD = 3.5


def _as_xy(points: PointArray, name: str) -> np.ndarray:
    try:
        arr = np.asarray(points, dtype=float)
    except (ValueError, TypeError) as exc:
        raise CalibrationError(f"{name} must be numeric (x, y) pairs.") from exc
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise CalibrationError(f"{name} must be an N x 2 array of (x, y) pairs.")
    if not np.all(np.isfinite(arr)):
        raise CalibrationError(f"{name} contains non-finite values (NaN or infinity).")
    return arr


def _affine_pipeline(a: float, b: float, d: float, e: float, c: float, f: float) -> str:
    # X = c + a*x + b*y ; Y = f + d*x + e*y
    return (
        f"+proj=pipeline +step +proj=affine "
        f"+xoff={c!r} +s11={a!r} +s12={b!r} "
        f"+yoff={f!r} +s21={d!r} +s22={e!r}"
    )


def _residuals(
    pred: np.ndarray,
    target: np.ndarray,
    outlier_threshold: float,
) -> tuple[tuple[Residual, ...], float, tuple[int, ...]]:
    diff = pred - target
    mags = np.hypot(diff[:, 0], diff[:, 1])
    n = len(mags)
    sq = float(np.sum(diff**2))
    rmse = math.sqrt(sq / n) if n else 0.0

    # Robust scale from the residual *components* (each ~ N(0, sigma)), using the
    # median absolute deviation so a gross blunder does not inflate the scale and
    # mask itself. The standardized residual is then a per-component z-score,
    # which (unlike a magnitude/sigma ratio on Rayleigh-distributed magnitudes)
    # leaves clean Gaussian noise comfortably under the threshold.
    comps = diff.reshape(-1)
    med = float(np.median(comps))
    mad = float(np.median(np.abs(comps - med)))
    sigma = 1.4826 * mad
    if sigma <= 1e-12:
        sigma = rmse if rmse > 1e-12 else 1.0

    residuals: list[Residual] = []
    outliers: list[int] = []
    for i in range(n):
        zx = abs(float(diff[i, 0]) - med) / sigma
        zy = abs(float(diff[i, 1]) - med) / sigma
        std = float(max(zx, zy))
        is_out = std > outlier_threshold
        if is_out:
            outliers.append(i)
        residuals.append(
            Residual(
                index=i,
                dx=float(diff[i, 0]),
                dy=float(diff[i, 1]),
                magnitude=float(mags[i]),
                standardized=std,
                is_outlier=is_out,
            )
        )
    result: tuple[tuple[Residual, ...], float, tuple[int, ...]] = (
        tuple(residuals),
        float(rmse),
        tuple(outliers),
    )
    return result


def fit_helmert_2d(
    local_xy: PointArray,
    target_xy: PointArray,
    *,
    outlier_threshold: float = _DEFAULT_OUTLIER_THRESHOLD,
) -> CalibrationResult:
    """Fit a 2D conformal (4-parameter) Helmert: scale, rotation, tx, ty.

    Model (with a = s*cos(theta), b = s*sin(theta))::

        X = tx + a*x - b*y
        Y = ty + b*x + a*y
    """
    local = _as_xy(local_xy, "local_xy")
    target = _as_xy(target_xy, "target_xy")
    if local.shape != target.shape:
        raise CalibrationError("local_xy and target_xy must have the same shape.")
    n = local.shape[0]
    if n < 2:
        raise CalibrationError("Helmert fit needs at least 2 control points.")

    x = local[:, 0]
    y = local[:, 1]
    # Design matrix for [a, b, tx, ty].
    rows = np.zeros((2 * n, 4))
    rows[0::2, 0] = x
    rows[0::2, 1] = -y
    rows[0::2, 2] = 1.0
    rows[1::2, 0] = y
    rows[1::2, 1] = x
    rows[1::2, 3] = 1.0
    obs = np.empty(2 * n)
    obs[0::2] = target[:, 0]
    obs[1::2] = target[:, 1]

    sol, *_ = np.linalg.lstsq(rows, obs, rcond=None)
    a, b, tx, ty = (float(v) for v in sol)
    scale = math.hypot(a, b)
    rotation_rad = math.atan2(b, a)

    pred = np.column_stack((tx + a * x - b * y, ty + b * x + a * y))
    residuals, rmse, outliers = _residuals(
        pred, target, outlier_threshold=outlier_threshold
    )

    params = {
        "scale": scale,
        "scale_ppm": (scale - 1.0) * 1.0e6,
        "rotation_deg": math.degrees(rotation_rad),
        "rotation_rad": rotation_rad,
        "tx": tx,
        "ty": ty,
    }
    # Conformal map as exact affine: X = tx + a*x - b*y ; Y = ty + b*x + a*y
    pipeline = _affine_pipeline(a=a, b=-b, d=b, e=a, c=tx, f=ty)

    return CalibrationResult(
        method="helmert",
        params=params,
        residuals=residuals,
        rmse=rmse,
        outliers=outliers,
        pipeline=pipeline,
        n_points=n,
    )


def fit_affine_2d(
    local_xy: PointArray,
    target_xy: PointArray,
    *,
    outlier_threshold: float = _DEFAULT_OUTLIER_THRESHOLD,
) -> CalibrationResult:
    """Fit a 6-parameter affine transform by least squares.

    Model::

        X = a*x + b*y + c
        Y = d*x + e*y + f
    """
    local = _as_xy(local_xy, "local_xy")
    target = _as_xy(target_xy, "target_xy")
    if local.shape != target.shape:
        raise CalibrationError("local_xy and target_xy must have the same shape.")
    n = local.shape[0]
    if n < 3:
        raise CalibrationError("Affine fit needs at least 3 control points.")

    x = local[:, 0]
    y = local[:, 1]
    design = np.column_stack((x, y, np.ones(n)))
    coeff_x, *_ = np.linalg.lstsq(design, target[:, 0], rcond=None)
    coeff_y, *_ = np.linalg.lstsq(design, target[:, 1], rcond=None)
    a, b, c = (float(v) for v in coeff_x)
    d, e, f = (float(v) for v in coeff_y)

    pred = np.column_stack((a * x + b * y + c, d * x + e * y + f))
    residuals, rmse, outliers = _residuals(
        pred, target, outlier_threshold=outlier_threshold
    )

    # Decompose for reporting (scale/rotation are approximate for non-conformal).
    scale_x = math.hypot(a, d)
    scale_y = math.hypot(b, e)
    rotation_rad = math.atan2(d, a)
    params = {
        "a": a,
        "b": b,
        "c": c,
        "d": d,
        "e": e,
        "f": f,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "rotation_deg": math.degrees(rotation_rad),
        "tx": c,
        "ty": f,
    }
    pipeline = _affine_pipeline(a=a, b=b, d=d, e=e, c=c, f=f)

    return CalibrationResult(
        method="affine",
        params=params,
        residuals=residuals,
        rmse=rmse,
        outliers=outliers,
        pipeline=pipeline,
        n_points=n,
    )


def to_pipeline(result: CalibrationResult) -> str:
    """Return the PROJ pipeline string for a fitted calibration."""
    return result.pipeline


def control_points_from_rows(
    rows: Iterable[Sequence[str]],
    *,
    has_header: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Parse control-point rows into ``(local_xy, target_xy)`` arrays.

    Each row must hold at least four numeric columns in the order
    ``local_x, local_y, target_x, target_y``. Extra columns are ignored. Blank
    rows are skipped. If ``has_header`` is True the first non-blank row is
    treated as a header and dropped only when its first cell is non-numeric.

    :raises CalibrationError: if no usable rows are found or a row is malformed.
    """
    local: list[tuple[float, float]] = []
    target: list[tuple[float, float]] = []
    header_pending = has_header
    for line_no, row in enumerate(rows, start=1):
        cells = [c.strip() for c in row]
        if not cells or all(c == "" for c in cells):
            continue
        if header_pending:
            header_pending = False
            try:
                float(cells[0])
            except (ValueError, IndexError):
                continue  # genuine header row -> skip
        if len(cells) < 4:
            raise CalibrationError(
                f"Row {line_no}: expected >= 4 columns "
                f"(local_x, local_y, target_x, target_y), got {len(cells)}."
            )
        try:
            lx, ly, tx, ty = (float(cells[i]) for i in range(4))
        except ValueError as exc:
            raise CalibrationError(
                f"Row {line_no}: non-numeric value ({exc})."
            ) from exc
        local.append((lx, ly))
        target.append((tx, ty))
    if not local:
        raise CalibrationError("No control points found.")
    return np.asarray(local, dtype=float), np.asarray(target, dtype=float)
