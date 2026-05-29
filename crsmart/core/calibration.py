# -*- coding: utf-8 -*-
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
from typing import List, Sequence, Tuple, Union

import numpy as np

from .errors import CalibrationError
from .models import CalibrationResult, Residual

PointArray = Union[Sequence[Sequence[float]], np.ndarray]

_DEFAULT_OUTLIER_THRESHOLD = 3.0


def _as_xy(points: PointArray, name: str) -> np.ndarray:
    arr = np.asarray(points, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 2:
        raise CalibrationError(f"{name} must be an N x 2 array of (x, y) pairs.")
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
    dof: int,
    outlier_threshold: float,
) -> Tuple[Tuple[Residual, ...], float, Tuple[int, ...]]:
    diff = pred - target
    mags = np.hypot(diff[:, 0], diff[:, 1])
    n = len(mags)
    sq = float(np.sum(diff**2))
    rmse = math.sqrt(sq / n) if n else 0.0

    # Robust scale (MAD) for outlier flagging; fall back to RMSE if degenerate.
    med = float(np.median(mags))
    mad = float(np.median(np.abs(mags - med)))
    sigma = 1.4826 * mad
    if sigma <= 1e-12:
        sigma = rmse if rmse > 1e-12 else 1.0

    residuals: List[Residual] = []
    outliers: List[int] = []
    for i in range(n):
        std = float(mags[i] / sigma)
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
    return tuple(residuals), rmse, tuple(outliers)


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

    pred = np.column_stack(
        (tx + a * x - b * y, ty + b * x + a * y)
    )
    residuals, rmse, outliers = _residuals(
        pred, target, dof=4, outlier_threshold=outlier_threshold
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

    pred = np.column_stack(
        (a * x + b * y + c, d * x + e * y + f)
    )
    residuals, rmse, outliers = _residuals(
        pred, target, dof=6, outlier_threshold=outlier_threshold
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
