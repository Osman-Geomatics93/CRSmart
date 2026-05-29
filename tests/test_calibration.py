"""Feature C -- local site calibration (Helmert/affine least squares)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from crsmart.core.calibration import (
    control_points_from_rows,
    fit_affine_2d,
    fit_helmert_2d,
)
from crsmart.core.errors import CalibrationError
from pyproj.transformer import Transformer

# Known Helmert parameters used to synthesize control points.
TRUE_SCALE = 1.0000234  # 23.4 ppm
TRUE_ROT_DEG = 0.7
TRUE_TX = 120.5
TRUE_TY = -45.2
NOISE_SIGMA = 0.01


def _apply_helmert(local: np.ndarray) -> np.ndarray:
    theta = math.radians(TRUE_ROT_DEG)
    a = TRUE_SCALE * math.cos(theta)
    b = TRUE_SCALE * math.sin(theta)
    x = local[:, 0]
    y = local[:, 1]
    return np.column_stack((TRUE_TX + a * x - b * y, TRUE_TY + b * x + a * y))


def _synthetic(n: int = 12, seed: int = 7) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    local = rng.uniform(-500.0, 500.0, size=(n, 2))
    target = _apply_helmert(local)
    noisy = target + rng.normal(0.0, NOISE_SIGMA, size=target.shape)
    return local, noisy


def test_helmert_recovers_known_parameters() -> None:
    local, target = _synthetic()
    result = fit_helmert_2d(local, target)
    assert result.method == "helmert"
    assert result.params["scale"] == pytest.approx(TRUE_SCALE, abs=5e-5)
    assert result.params["rotation_deg"] == pytest.approx(TRUE_ROT_DEG, abs=0.05)
    assert result.params["tx"] == pytest.approx(TRUE_TX, abs=0.05)
    assert result.params["ty"] == pytest.approx(TRUE_TY, abs=0.05)
    # RMSE is on the order of the injected noise.
    assert result.rmse == pytest.approx(NOISE_SIGMA, abs=0.02)
    assert result.outliers == ()


def test_helmert_flags_injected_outlier() -> None:
    local, target = _synthetic()
    target = target.copy()
    target[5] += np.array([3.0, -2.5])  # gross blunder at index 5
    result = fit_helmert_2d(local, target)
    assert 5 in result.outliers
    bad = next(r for r in result.residuals if r.index == 5)
    assert bad.is_outlier
    assert bad.standardized > 3.0


def test_helmert_pipeline_round_trips() -> None:
    local, target = _synthetic()
    result = fit_helmert_2d(local, target)
    transformer = Transformer.from_pipeline(result.pipeline)
    gx, gy = transformer.transform(local[:, 0], local[:, 1])
    # The emitted pipeline reproduces the fitted model (predicted) coordinates.
    theta = math.radians(result.params["rotation_deg"])
    s = result.params["scale"]
    a = s * math.cos(theta)
    b = s * math.sin(theta)
    pred_x = result.params["tx"] + a * local[:, 0] - b * local[:, 1]
    pred_y = result.params["ty"] + b * local[:, 0] + a * local[:, 1]
    assert np.allclose(gx, pred_x, atol=1e-6)
    assert np.allclose(gy, pred_y, atol=1e-6)


def test_affine_fit_and_round_trip() -> None:
    rng = np.random.default_rng(3)
    local = rng.uniform(-300.0, 300.0, size=(10, 2))
    # A non-conformal affine (shear) map.
    a, b, c = 1.0002, 0.0007, 50.0
    d, e, f = -0.0009, 0.9996, -20.0
    target = np.column_stack(
        (a * local[:, 0] + b * local[:, 1] + c, d * local[:, 0] + e * local[:, 1] + f)
    )
    result = fit_affine_2d(local, target)
    assert result.method == "affine"
    assert result.params["a"] == pytest.approx(a, abs=1e-6)
    assert result.params["e"] == pytest.approx(e, abs=1e-6)
    transformer = Transformer.from_pipeline(result.pipeline)
    gx, gy = transformer.transform(local[:, 0], local[:, 1])
    assert np.allclose(gx, target[:, 0], atol=1e-6)
    assert np.allclose(gy, target[:, 1], atol=1e-6)


def test_too_few_points_raises() -> None:
    with pytest.raises(CalibrationError):
        fit_helmert_2d([[0.0, 0.0]], [[1.0, 1.0]])
    with pytest.raises(CalibrationError):
        fit_affine_2d([[0.0, 0.0], [1.0, 1.0]], [[0.0, 0.0], [1.0, 1.0]])


def test_control_points_from_rows_with_header() -> None:
    rows = [
        ["local_x", "local_y", "target_x", "target_y"],
        ["100.0", "200.0", "500100.0", "6000200.0"],
        ["150.5", "250.5", "500150.5", "6000250.5"],
        ["", ""],  # blank row skipped
        ["300", "400", "500300", "6000400", "ignored-extra-col"],
    ]
    local, target = control_points_from_rows(rows)
    assert local.shape == (3, 2)
    assert target.shape == (3, 2)
    assert local[0].tolist() == [100.0, 200.0]
    assert target[2].tolist() == [500300.0, 6000400.0]


def test_control_points_from_rows_no_header_autodetect() -> None:
    # has_header=True but the first row is numeric -> kept, not dropped.
    rows = [["1", "2", "3", "4"], ["5", "6", "7", "8"]]
    local, target = control_points_from_rows(rows, has_header=True)
    assert local.shape == (2, 2)


def test_control_points_from_rows_round_trips_fit() -> None:
    rng = np.random.default_rng(11)
    local = rng.uniform(-100, 100, size=(8, 2))
    target = local + np.array([10.0, -5.0])  # pure translation
    rows = [["lx", "ly", "tx", "ty"]] + [
        [str(local[i, 0]), str(local[i, 1]), str(target[i, 0]), str(target[i, 1])]
        for i in range(len(local))
    ]
    pl, pt = control_points_from_rows(rows)
    result = fit_helmert_2d(pl, pt)
    assert result.params["tx"] == pytest.approx(10.0, abs=1e-6)
    assert result.params["ty"] == pytest.approx(-5.0, abs=1e-6)


def test_control_points_from_rows_errors() -> None:
    with pytest.raises(CalibrationError):
        control_points_from_rows([["lx", "ly", "tx", "ty"]])  # header only
    with pytest.raises(CalibrationError):
        control_points_from_rows([["1", "2", "3"]], has_header=False)  # too few cols
    with pytest.raises(CalibrationError):
        control_points_from_rows(
            [["a", "b", "c", "d"]], has_header=False
        )  # non-numeric
