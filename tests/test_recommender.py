"""Feature A -- transformation recommender (pure engine, no QGIS)."""

from __future__ import annotations

import pytest
from crsmart.core.transform_recommender import enumerate_candidates

# EPSG anchors used across the suite.
GDA94 = 4283
GDA2020 = 7844
ADINDAN = 4201  # Adindan (Sudan)
WGS84 = 4326
AGD66 = 4202
ETRS89 = 4258

AU_BBOX = (112.0, -44.0, 154.0, -9.0)


def test_sudan_parametric_helmert_recommended_no_grid() -> None:
    """Adindan(Sudan)->WGS84: parametric Helmert ops only, no grid, not ballpark."""
    result = enumerate_candidates(ADINDAN, WGS84)
    assert not result.ballpark_only
    assert result.recommended is not None
    rec = result.recommended
    assert not rec.is_ballpark
    assert rec.available
    # Best EPSG Helmert for Adindan/Sudan is ~6 m; must be the most accurate one.
    accs = [c.accuracy_m for c in result.candidates if c.accuracy_m is not None]
    assert rec.accuracy_m == min(accs)
    assert rec.accuracy_m == pytest.approx(6.0, abs=1.0)
    assert result.missing_grids == ()


def test_ballpark_only_pair_flagged_and_not_recommended() -> None:
    """AGD66->ETRS89 has no real transform -> ballpark only, no recommendation."""
    result = enumerate_candidates(AGD66, ETRS89)
    assert result.ballpark_only is True
    assert result.recommended is None
    assert all(c.is_ballpark for c in result.candidates)


def test_allow_ballpark_false_hides_ballpark_but_flag_honest() -> None:
    result = enumerate_candidates(AGD66, ETRS89, allow_ballpark=False)
    assert result.candidates == ()  # ballpark hidden
    assert result.ballpark_only is True  # flag still computed honestly
    assert result.recommended is None


def test_gda94_to_gda2020_reports_missing_conformal_grid() -> None:
    """Better conformal-grid ops exist but the .tif grids aren't installed."""
    result = enumerate_candidates(GDA94, GDA2020)
    assert not result.ballpark_only
    # The conformal/distortion grids should show up as missing.
    assert any("conformal" in g.short_name for g in result.missing_grids)
    # And at least one candidate is a real op that needs a CDN download.
    assert any(c.needs_download for c in result.candidates)
    # A usable (available, non-ballpark) op is still recommended.
    assert result.recommended is not None
    assert result.recommended.available


def test_candidates_ranked_best_first() -> None:
    result = enumerate_candidates(GDA94, GDA2020)
    scores = [c.rank_score for c in result.candidates]
    assert scores == sorted(scores, reverse=True)


def test_recommended_has_reusable_pipeline() -> None:
    result = enumerate_candidates(ADINDAN, WGS84)
    assert result.recommended is not None
    assert result.recommended.pipeline is not None
    assert result.recommended.pipeline.startswith("+proj=pipeline")


def test_area_of_interest_marks_coverage() -> None:
    result = enumerate_candidates(GDA94, GDA2020, area_of_interest=AU_BBOX)
    assert result.recommended is not None
    assert result.recommended.covers_aoi is True
