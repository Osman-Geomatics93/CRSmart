# -*- coding: utf-8 -*-
"""Immutable result types for the CRSmart engine.

Pure data only -- no Qt, no pyproj, no logic beyond trivial geometry helpers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional, Tuple


@dataclass(frozen=True)
class AreaOfUseInfo:
    """Bounding box (WGS84 degrees) describing where an operation is valid."""

    name: Optional[str]
    west: Optional[float]
    south: Optional[float]
    east: Optional[float]
    north: Optional[float]

    @property
    def is_defined(self) -> bool:
        return None not in (self.west, self.south, self.east, self.north)

    def intersects_bbox(
        self, west: float, south: float, east: float, north: float
    ) -> bool:
        """True if this area overlaps the given WGS84 bounding box.

        Antimeridian-crossing areas (west > east) are treated as wrapping.
        """
        if not self.is_defined:
            return False
        assert self.south is not None and self.north is not None
        if south > self.north or north < self.south:
            return False
        return _lon_ranges_overlap(self.west, self.east, west, east)  # type: ignore[arg-type]

    def contains_point(self, lon: float, lat: float) -> bool:
        if not self.is_defined:
            return False
        assert self.south is not None and self.north is not None
        if not (self.south <= lat <= self.north):
            return False
        return _lon_in_range(self.west, self.east, lon)  # type: ignore[arg-type]


def _lon_in_range(west: float, east: float, lon: float) -> bool:
    if west <= east:
        return west <= lon <= east
    # wraps the antimeridian
    return lon >= west or lon <= east


def _lon_ranges_overlap(w1: float, e1: float, w2: float, e2: float) -> bool:
    # Sample-free overlap test handling antimeridian wrap on either range.
    def normal(w: float, e: float) -> bool:
        return w <= e

    if normal(w1, e1) and normal(w2, e2):
        return not (w1 > e2 or w2 > e1)
    # If either wraps, fall back to checking endpoint containment both ways.
    return (
        _lon_in_range(w1, e1, w2)
        or _lon_in_range(w1, e1, e2)
        or _lon_in_range(w2, e2, w1)
        or _lon_in_range(w2, e2, e1)
    )


@dataclass(frozen=True)
class GridInfo:
    """A PROJ transformation grid required by an operation."""

    short_name: str
    full_name: str
    package_name: Optional[str]
    url: Optional[str]
    direct_download: bool
    open_license: bool
    available: bool  # present locally?

    @property
    def downloadable(self) -> bool:
        return bool(self.url) and self.direct_download


@dataclass(frozen=True)
class TransformCandidate:
    """One candidate transformation operation, fully annotated."""

    description: str
    accuracy_m: Optional[float]  # None == unknown (ballpark / undefined)
    is_ballpark: bool
    area_of_use: Optional[AreaOfUseInfo]
    grids: Tuple[GridInfo, ...]
    pipeline: Optional[str]  # PROJ pipeline string for reuse
    available: bool  # all required grids present locally?
    covers_aoi: bool  # area_of_use covers the requested area of interest
    rank_score: float
    auth_code: Optional[str] = None  # e.g. "EPSG:8048"

    @property
    def missing_grids(self) -> Tuple[GridInfo, ...]:
        return tuple(g for g in self.grids if not g.available)

    @property
    def needs_download(self) -> bool:
        return any(not g.available and g.downloadable for g in self.grids)


@dataclass(frozen=True)
class RecommendationResult:
    """Ranked candidates plus a recommendation and safety flags."""

    source_crs: str
    target_crs: str
    candidates: Tuple[TransformCandidate, ...]  # ranked best-first
    recommended: Optional[TransformCandidate]
    ballpark_only: bool
    missing_grids: Tuple[GridInfo, ...]

    @property
    def has_recommendation(self) -> bool:
        return self.recommended is not None


@dataclass(frozen=True)
class Residual:
    """Per-control-point residual from a calibration fit."""

    index: int
    dx: float
    dy: float
    magnitude: float
    standardized: float
    is_outlier: bool


@dataclass(frozen=True)
class CalibrationResult:
    """Result of a Helmert/affine least-squares fit."""

    method: Literal["helmert", "affine"]
    params: Dict[str, float]
    residuals: Tuple[Residual, ...]
    rmse: float
    outliers: Tuple[int, ...]
    pipeline: str  # +proj=helmert ... / +proj=affine ...
    n_points: int


@dataclass(frozen=True)
class EpochInfo:
    """Why (or whether) a coordinate epoch is required for a transform."""

    required: bool
    reason: str
    source_is_dynamic: bool
    target_is_dynamic: bool
    source_epoch: Optional[float]
    target_epoch: Optional[float]


@dataclass(frozen=True)
class VerticalStatus:
    """Vertical-CRS state of a layer/CRS for the repair feature."""

    has_vertical: bool
    is_compound: bool
    horizontal_name: Optional[str]
    vertical_name: Optional[str]
    message: str
