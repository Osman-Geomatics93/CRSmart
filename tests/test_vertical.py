"""Feature D -- vertical datum repair (pure engine)."""

from __future__ import annotations

import pytest
from crsmart.core.vertical import (
    COMMON_VERTICAL_CRS,
    assemble_compound,
    detect_vertical,
)

WGS84_2D = 4326
NAVD88_HEIGHT = 5703  # vertical CRS
NAD83_NAVD88 = 5498  # compound: NAD83 + NAVD88 height
WGS84_EGM96 = 9707  # compound: WGS 84 + EGM96 height (NOT a standalone vertical)


def test_missing_vertical_detected() -> None:
    status = detect_vertical(WGS84_2D)
    assert status.has_vertical is False
    assert status.is_compound is False
    assert status.vertical_name is None
    assert "no vertical" in status.message.lower()


def test_standalone_vertical_detected() -> None:
    status = detect_vertical(NAVD88_HEIGHT)
    assert status.has_vertical is True
    assert status.vertical_name is not None
    assert "navd88" in status.vertical_name.lower()


def test_compound_crs_detected() -> None:
    status = detect_vertical(NAD83_NAVD88)
    assert status.has_vertical is True
    assert status.is_compound is True
    assert status.horizontal_name is not None
    assert "navd88" in (status.vertical_name or "").lower()


def test_assemble_compound_repairs_missing_vertical() -> None:
    compound = assemble_compound(WGS84_2D, NAVD88_HEIGHT)
    assert compound.is_compound
    status = detect_vertical(compound)
    assert status.has_vertical is True
    assert "navd88" in (status.vertical_name or "").lower()


def test_assemble_compound_rejects_non_vertical() -> None:
    with pytest.raises(ValueError):
        assemble_compound(WGS84_2D, WGS84_2D)  # second arg isn't vertical


def test_assemble_compound_rejects_compound_in_vertical_slot() -> None:
    """A compound CRS (e.g. EPSG:9707) reports is_vertical=True but must be
    refused with a clear message -- not allowed to reach PROJ and raise a cryptic
    CRSError by nesting compounds."""
    with pytest.raises(ValueError) as excinfo:
        assemble_compound(WGS84_2D, WGS84_EGM96)
    msg = str(excinfo.value).lower()
    assert "standalone vertical" in msg and "5773" in str(excinfo.value)


def test_common_vertical_presets_are_standalone_and_assemble() -> None:
    """Every preset offered in the GUI/Processing must be a real, standalone
    vertical CRS that assembles cleanly with a horizontal CRS."""
    assert COMMON_VERTICAL_CRS, "preset list is empty"
    for label, code in COMMON_VERTICAL_CRS:
        compound = assemble_compound(WGS84_2D, code)  # must not raise
        assert detect_vertical(compound).has_vertical is True, label
