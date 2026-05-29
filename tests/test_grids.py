"""Grid availability + the hard download-consent gate (pure engine, no network)."""

from __future__ import annotations

import pytest
from crsmart.core import grids
from crsmart.core.errors import ConsentRequiredError
from crsmart.core.models import GridInfo
from crsmart.core.transform_recommender import enumerate_candidates

_MISSING_GRID = GridInfo(
    short_name="example_missing.tif",
    full_name="Example missing grid",
    package_name=None,
    url="https://cdn.proj.org/example_missing.tif",
    direct_download=True,
    open_license=True,
    available=False,
)
_PRESENT_GRID = GridInfo(
    short_name="present.tif",
    full_name="Already present",
    package_name=None,
    url="https://cdn.proj.org/present.tif",
    direct_download=True,
    open_license=True,
    available=True,
)


def test_download_without_consent_raises_and_no_network() -> None:
    before = grids.is_network_enabled()
    with pytest.raises(ConsentRequiredError):
        grids.download_grids([_MISSING_GRID], consent=False)
    # Network state must be untouched by the refused call.
    assert grids.is_network_enabled() == before


def test_consent_false_is_strict() -> None:
    # Even the default/omitted truthiness traps: only literal True passes.
    with pytest.raises(ConsentRequiredError):
        grids.download_grids([_MISSING_GRID], consent=bool(1) and False)


def test_select_missing_filters_present() -> None:
    out = grids.select_missing([_MISSING_GRID, _PRESENT_GRID])
    assert out == (_MISSING_GRID,)


def test_consent_with_nothing_to_fetch_is_noop_no_network() -> None:
    before = grids.is_network_enabled()
    report = grids.download_grids([_PRESENT_GRID], consent=True)  # all present
    assert report.results == ()
    assert report.all_ok
    assert grids.is_network_enabled() == before


def test_enumeration_does_not_enable_network() -> None:
    before = grids.is_network_enabled()
    enumerate_candidates(4283, 7844)  # GDA94 -> GDA2020 (has missing grids)
    assert grids.is_network_enabled() == before
    assert grids.is_network_enabled() is False  # default-off, no silent enable
