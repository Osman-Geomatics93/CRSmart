"""Phase 5 -- edge cases and error states across the pure engine (no QGIS)."""

from __future__ import annotations

import numpy as np
import pytest
from crsmart.core import grids
from crsmart.core.calibration import fit_affine_2d, fit_helmert_2d
from crsmart.core.errors import CalibrationError
from crsmart.core.models import AreaOfUseInfo, GridInfo
from crsmart.core.transform_recommender import enumerate_candidates
from crsmart.core.vertical import assemble_compound, detect_vertical

WGS84 = 4326
WGS84_3D = 4979  # geographic 3D (ellipsoidal height -- NOT a gravity vertical CRS)
UTM36N = 32636
NAVD88 = 5703


# --- recommender edge cases -------------------------------------------------
def test_identity_transform_is_exact_and_recommended() -> None:
    result = enumerate_candidates(WGS84, WGS84)
    assert result.recommended is not None
    assert result.recommended.accuracy_m == 0.0
    assert not result.ballpark_only


def test_string_and_int_crs_inputs_agree() -> None:
    by_int = enumerate_candidates(4201, 4326)
    by_str = enumerate_candidates("EPSG:4201", "EPSG:4326")
    assert len(by_int.candidates) == len(by_str.candidates)


# --- calibration error states ----------------------------------------------
def test_nan_control_points_raise_clean_error() -> None:
    local = np.array([[0, 0], [1, 0], [0, 1], [float("nan"), 1]], float)
    target = local + np.array([10.0, 5.0])  # numpy broadcast, not list concat
    with pytest.raises(CalibrationError, match="non-finite"):
        fit_helmert_2d(local, target)


def test_infinite_control_points_raise_clean_error() -> None:
    local = np.array([[0, 0], [1, 0], [0, 1], [float("inf"), 1]], float)
    target = local.copy()
    with pytest.raises(CalibrationError, match="non-finite"):
        fit_affine_2d(local, target)


def test_mismatched_shapes_raise() -> None:
    with pytest.raises(CalibrationError, match="same shape"):
        fit_helmert_2d([[0, 0], [1, 1]], [[0, 0], [1, 1], [2, 2]])


def test_ragged_input_raises_clean_error() -> None:
    with pytest.raises(CalibrationError):
        fit_helmert_2d([[0, 0], [1]], [[0, 0], [1, 1]])


# --- vertical edge cases ----------------------------------------------------
def test_3d_geographic_reports_missing_vertical() -> None:
    # Ellipsoidal height is not a gravity-related vertical CRS.
    status = detect_vertical(WGS84_3D)
    assert status.has_vertical is False


def test_assemble_compound_accepts_projected_horizontal() -> None:
    compound = assemble_compound(UTM36N, NAVD88)
    assert compound.is_compound
    assert detect_vertical(compound).has_vertical is True


def test_assemble_compound_rejects_vertical_as_horizontal() -> None:
    with pytest.raises(ValueError, match="not a horizontal"):
        assemble_compound(NAVD88, NAVD88)


# --- AreaOfUseInfo geometry (pure, no pyproj) -------------------------------
def test_area_of_use_undefined_never_intersects() -> None:
    area = AreaOfUseInfo(name="x", west=None, south=None, east=None, north=None)
    assert area.is_defined is False
    assert area.intersects_bbox(0, 0, 1, 1) is False
    assert area.contains_point(0.5, 0.5) is False


def test_area_of_use_basic_intersection() -> None:
    area = AreaOfUseInfo(name="AU", west=112, south=-44, east=154, north=-9)
    assert area.intersects_bbox(120, -40, 130, -20) is True
    assert area.intersects_bbox(0, 0, 10, 10) is False  # Europe-ish, no overlap
    assert area.contains_point(133, -25) is True
    assert area.contains_point(0, 0) is False


def test_area_of_use_antimeridian_wrap() -> None:
    # Fiji-like area crossing the antimeridian: west > east.
    area = AreaOfUseInfo(name="FJ", west=174, south=-22, east=-178, north=-12)
    assert area.contains_point(179, -17) is True
    assert area.contains_point(-179, -17) is True
    assert area.contains_point(100, -17) is False
    assert area.intersects_bbox(178, -20, 180, -15) is True


# --- grids: consent gate + helpers (no network) -----------------------------
def _grid(
    url: str | None,
    *,
    available: bool,
    open_license: bool = True,
    short_name: str = "g.tif",
) -> GridInfo:
    return GridInfo(
        short_name=short_name,
        full_name="g",
        package_name=None,
        url=url,
        direct_download=True,
        open_license=open_license,
        available=available,
    )


def test_download_no_url_reports_failure_without_network() -> None:
    # No url AND no short_name -> _grid_url() returns None, so no network at all.
    before = grids.is_network_enabled()
    report = grids.download_grids(
        [_grid(None, available=False, short_name="")], consent=True
    )
    assert not report.all_ok
    assert report.failed[0].error == "no download URL"
    assert grids.is_network_enabled() == before


def test_download_non_open_license_refused_without_network() -> None:
    before = grids.is_network_enabled()
    report = grids.download_grids(
        [_grid("https://cdn.proj.org/g.tif", available=False, open_license=False)],
        consent=True,
    )
    assert not report.all_ok
    assert "open license" in (report.failed[0].error or "")
    assert grids.is_network_enabled() == before


def test_download_report_partitions_results() -> None:
    ok = grids.GridDownload("a", True, "/p/a", None)
    bad = grids.GridDownload("b", False, None, "boom")
    report = grids.DownloadReport(results=(ok, bad))
    assert report.succeeded == (ok,)
    assert report.failed == (bad,)
    assert report.all_ok is False
