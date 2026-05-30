"""Feature B -- epoch-aware / dynamic-datum transforms (pure engine)."""

from __future__ import annotations

import math

import pytest
from crsmart.core.epoch import (
    analyze_epoch,
    is_dynamic,
    make_4d_transformer,
    require_epoch_or_raise,
    transform_4d,
)
from crsmart.core.errors import (
    BallparkNotAllowedError,
    CRSmartError,
    EpochRequiredError,
    TransformUnavailableError,
)
from pyproj import CRS

ITRF2014 = 7912  # ITRF2014 geographic 3D (dynamic)
ITRF2008 = 7911  # ITRF2008 geographic 3D (dynamic)
ETRS89 = 4258  # static, plate-fixed
WGS84 = 4326

# A point in Europe: lon, lat, ellipsoidal height.
LON, LAT, H = 7.0, 46.0, 500.0


def test_dynamic_detection() -> None:
    assert is_dynamic(ITRF2014) is True
    assert is_dynamic(ITRF2008) is True
    assert is_dynamic(ETRS89) is False
    assert is_dynamic(WGS84) is False


def test_epoch_required_when_unset() -> None:
    info = analyze_epoch(ITRF2014, ITRF2008)
    assert info.required is True
    assert info.source_is_dynamic and info.target_is_dynamic
    assert "epoch" in info.reason.lower()


def test_epoch_not_required_when_set() -> None:
    info = analyze_epoch(ITRF2014, ITRF2008, source_epoch=2010.0, target_epoch=2010.0)
    assert info.required is False


def test_static_pair_needs_no_epoch() -> None:
    info = analyze_epoch(ETRS89, WGS84)
    assert info.required is False


def test_require_epoch_or_raise() -> None:
    with pytest.raises(EpochRequiredError):
        require_epoch_or_raise(ITRF2014, ITRF2008)
    # With epoch supplied it returns instead of raising.
    info = require_epoch_or_raise(ITRF2014, ITRF2008, 2010.0, 2010.0)
    assert info.required is False


def test_transform_4d_round_trip() -> None:
    x, y, z, t = transform_4d(ITRF2014, ITRF2008, LON, LAT, H, 2010.0)
    bx, by, bz, bt = transform_4d(ITRF2008, ITRF2014, x, y, z, t)
    assert bx == pytest.approx(LON, abs=1e-7)  # < ~1 cm in longitude
    assert by == pytest.approx(LAT, abs=1e-7)
    assert bz == pytest.approx(H, abs=1e-3)  # < 1 mm in height
    assert bt == pytest.approx(2010.0, abs=1e-6)


def test_transform_4d_is_time_dependent() -> None:
    """Same point, different epochs -> different ITRF coordinates (plate motion)."""
    a = transform_4d(ITRF2014, ITRF2008, LON, LAT, H, 1995.0)
    b = transform_4d(ITRF2014, ITRF2008, LON, LAT, H, 2025.0)
    horizontal_shift = math.hypot(a[0] - b[0], a[1] - b[1])
    assert horizontal_shift > 0.0  # strictly time-dependent


def test_transform_4d_enforces_epoch_for_dynamic() -> None:
    with pytest.raises(EpochRequiredError):
        transform_4d(ITRF2014, ITRF2008, LON, LAT, H, float("nan"))


def test_ballpark_only_pair_raises_clear_error_not_cryptic_projerror() -> None:
    """A pair whose only path is a ballpark transform must raise a clear,
    actionable error -- not PROJ's cryptic 'Error creating Transformer from CRS.'"""
    # A custom CRS with an undefined datum: only a ballpark path to WGS 84 exists.
    custom = CRS.from_proj4("+proj=longlat +ellps=bessel +no_defs")
    with pytest.raises(BallparkNotAllowedError) as excinfo:
        make_4d_transformer(WGS84, custom)
    assert "ballpark" in str(excinfo.value).lower()
    # With explicit opt-in the transformer builds.
    transformer = make_4d_transformer(WGS84, custom, allow_ballpark=True)
    assert transformer is not None


def test_incompatible_pair_raises_clear_crsmart_error() -> None:
    """An incompatible pair (geographic -> vertical-only) must raise a clear
    CRSmartError, never PROJ's cryptic ProjError.

    Whether PROJ can synthesize a ballpark path between a horizontal and a
    vertical-only CRS is PROJ-version dependent: older builds fail outright
    (-> TransformUnavailableError) while newer builds offer a ballpark
    (-> BallparkNotAllowedError). Both are acceptable; the user-facing
    contract we assert is only that the error is one of ours, not a raw
    ProjError traceback. ``TransformUnavailableError`` is imported above so
    its branch stays referenced even when this PROJ build takes the ballpark
    path.
    """
    assert issubclass(TransformUnavailableError, CRSmartError)
    with pytest.raises(CRSmartError):
        make_4d_transformer(WGS84, 5703)  # NAVD88 height (vertical-only)


def test_make_4d_transformer_is_reusable_and_matches_transform_4d() -> None:
    transformer = make_4d_transformer(ITRF2014, ITRF2008)
    # Batch-transform several points/epochs through the one transformer.
    xs = [LON, LON + 1.0]
    ys = [LAT, LAT - 1.0]
    zs = [H, H + 50.0]
    ts = [2010.0, 2010.0]
    bx, by, bz, bt = transformer.transform(xs, ys, zs, ts)
    # First point matches the single-shot helper within tight tolerance.
    sx, sy, sz, _ = transform_4d(ITRF2014, ITRF2008, LON, LAT, H, 2010.0)
    assert bx[0] == pytest.approx(sx, abs=1e-9)
    assert by[0] == pytest.approx(sy, abs=1e-9)
    assert bz[0] == pytest.approx(sz, abs=1e-6)
