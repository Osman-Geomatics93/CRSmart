# -*- coding: utf-8 -*-
"""Feature D -- vertical datum repair (pure engine)."""
from __future__ import annotations

import pytest

from crsmart.core.vertical import assemble_compound, detect_vertical

WGS84_2D = 4326
NAVD88_HEIGHT = 5703  # vertical CRS
NAD83_NAVD88 = 5498  # compound: NAD83 + NAVD88 height


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
