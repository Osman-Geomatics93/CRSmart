# -*- coding: utf-8 -*-
"""Feature B -- epoch-aware / dynamic-datum transforms (pure engine)."""
from __future__ import annotations

import math

import pytest

from crsmart.core.epoch import (
    analyze_epoch,
    is_dynamic,
    require_epoch_or_raise,
    transform_4d,
)
from crsmart.core.errors import EpochRequiredError

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
