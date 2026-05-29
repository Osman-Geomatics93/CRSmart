# -*- coding: utf-8 -*-
"""Feature A -- transformation recommender with uncertainty (pure Python).

Heart of the feature is :class:`pyproj.transformer.TransformerGroup`. We build it
once with ballpark allowed (to enumerate every candidate, including the ballpark
fallback) and surface ``unavailable_operations`` -- the better operations that
exist but need PROJ grids not installed locally.

Verified against pyproj 3.6.1 / PROJ 9.3.0:
  * ``transformer.accuracy`` -> float metres (``-1.0`` for ballpark/unknown)
  * ``operation.has_ballpark_transformation`` -> bool (authoritative flag)
  * ``transformer.to_proj4()`` -> reusable ``+proj=pipeline ...`` string
  * grids reached via ``operation.grids`` (each with short_name/full_name/
    package_name/url/direct_download/open_license/available)
  * missing-grid ops live in ``group.unavailable_operations``
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Union

from pyproj import CRS
from pyproj.aoi import AreaOfInterest
from pyproj.transformer import TransformerGroup

from .models import AreaOfUseInfo, GridInfo, RecommendationResult, TransformCandidate

CRSLike = Union[CRS, str, int]
BBox = Tuple[float, float, float, float]  # (west, south, east, north) in WGS84 deg


def coerce_crs(value: CRSLike) -> CRS:
    """Coerce an EPSG int, string, or CRS into a :class:`pyproj.CRS`."""
    if isinstance(value, CRS):
        return value
    return CRS.from_user_input(value)


def _to_area_of_interest(
    area: Optional[Union[BBox, AreaOfInterest]],
) -> Optional[AreaOfInterest]:
    if area is None or isinstance(area, AreaOfInterest):
        return area
    west, south, east, north = area
    return AreaOfInterest(
        west_lon_degree=west,
        south_lat_degree=south,
        east_lon_degree=east,
        north_lat_degree=north,
    )


def _area_of_use_info(area_of_use: object) -> Optional[AreaOfUseInfo]:
    if area_of_use is None:
        return None
    name = getattr(area_of_use, "name", None)
    west = getattr(area_of_use, "west", None)
    south = getattr(area_of_use, "south", None)
    east = getattr(area_of_use, "east", None)
    north = getattr(area_of_use, "north", None)
    if None in (west, south, east, north) and name is None:
        return None
    return AreaOfUseInfo(name=name, west=west, south=south, east=east, north=north)


def _grid_info(grid: object) -> GridInfo:
    return GridInfo(
        short_name=getattr(grid, "short_name", "") or "",
        full_name=getattr(grid, "full_name", "") or "",
        package_name=getattr(grid, "package_name", None) or None,
        url=getattr(grid, "url", None) or None,
        direct_download=bool(getattr(grid, "direct_download", False)),
        open_license=bool(getattr(grid, "open_license", False)),
        available=bool(getattr(grid, "available", False)),
    )


def _grids_from_operations(operations: Sequence[object]) -> Tuple[GridInfo, ...]:
    grids: List[GridInfo] = []
    for op in operations:
        for grid in getattr(op, "grids", ()) or ():
            grids.append(_grid_info(grid))
    return tuple(grids)


def _normalize_accuracy(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if value < 0:  # PROJ uses -1 for unknown / ballpark
        return None
    return float(value)


def _is_ballpark(operations: Sequence[object]) -> bool:
    return any(
        bool(getattr(op, "has_ballpark_transformation", False)) for op in operations
    )


def _safe_proj4(obj: object) -> Optional[str]:
    try:
        text = obj.to_proj4()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - some unavailable ops aren't instantiable
        return None
    return text or None


def _covers(area: Optional[AreaOfUseInfo], aoi_bbox: Optional[BBox]) -> bool:
    if aoi_bbox is None:
        return True  # no constraint => trivially "covers"
    if area is None:
        return False
    return area.intersects_bbox(*aoi_bbox)


def _sort_key(candidate: TransformCandidate) -> Tuple:
    """Higher tuple == better. Priority: AOI cover -> accuracy -> available
    -> non-ballpark -> stable by description."""
    has_acc = candidate.accuracy_m is not None
    acc_component = -candidate.accuracy_m if has_acc else 0.0
    return (
        1 if candidate.covers_aoi else 0,
        1 if has_acc else 0,
        acc_component,
        1 if candidate.available else 0,
        0 if candidate.is_ballpark else 1,
        candidate.description,
    )


def enumerate_candidates(
    source: CRSLike,
    target: CRSLike,
    *,
    area_of_interest: Optional[Union[BBox, AreaOfInterest]] = None,
    allow_ballpark: bool = True,
) -> RecommendationResult:
    """Enumerate, annotate and rank every candidate transform from src to dst.

    :param source: source CRS (CRS / EPSG int / authority string).
    :param target: target CRS.
    :param area_of_interest: optional WGS84 ``(west, south, east, north)`` bbox
        used both to bias PROJ's selection and to compute ``covers_aoi``.
    :param allow_ballpark: if False, ballpark candidates are excluded from the
        returned list (the ``ballpark_only`` flag is still computed honestly).
    """
    src = coerce_crs(source)
    dst = coerce_crs(target)
    aoi = _to_area_of_interest(area_of_interest)
    aoi_bbox: Optional[BBox] = None
    if aoi is not None:
        aoi_bbox = (
            aoi.west_lon_degree,
            aoi.south_lat_degree,
            aoi.east_lon_degree,
            aoi.north_lat_degree,
        )

    group = TransformerGroup(
        src, dst, always_xy=True, area_of_interest=aoi, allow_ballpark=True
    )

    candidates: List[TransformCandidate] = []

    # 1) Available transformers.
    for transformer in group.transformers:
        operations = list(transformer.operations or ())
        is_ballpark = _is_ballpark(operations)
        area = _area_of_use_info(transformer.area_of_use)
        grids = _grids_from_operations(operations)
        candidates.append(
            TransformCandidate(
                description=transformer.description,
                accuracy_m=None if is_ballpark else _normalize_accuracy(
                    transformer.accuracy
                ),
                is_ballpark=is_ballpark,
                area_of_use=area,
                grids=grids,
                pipeline=_safe_proj4(transformer),
                available=all(g.available for g in grids),
                covers_aoi=_covers(area, aoi_bbox),
                rank_score=0.0,
            )
        )

    # 2) Operations that exist but need missing grids (not directly usable yet).
    for op in group.unavailable_operations:
        operations = [op]
        is_ballpark = _is_ballpark(operations)
        area = _area_of_use_info(getattr(op, "area_of_use", None))
        grids = _grids_from_operations(operations)
        candidates.append(
            TransformCandidate(
                description=getattr(op, "name", "") or "",
                accuracy_m=None if is_ballpark else _normalize_accuracy(
                    getattr(op, "accuracy", None)
                ),
                is_ballpark=is_ballpark,
                area_of_use=area,
                grids=grids,
                pipeline=_safe_proj4(op),
                available=False,
                covers_aoi=_covers(area, aoi_bbox),
                rank_score=0.0,
            )
        )

    # Rank (best first) and stamp a monotonic rank_score (higher == better).
    candidates.sort(key=_sort_key, reverse=True)
    ranked = tuple(
        _with_score(c, float(len(candidates) - i))
        for i, c in enumerate(candidates)
    )

    non_ballpark = [c for c in ranked if not c.is_ballpark]
    ballpark_only = len(ranked) > 0 and len(non_ballpark) == 0

    if allow_ballpark:
        visible = ranked
    else:
        visible = tuple(c for c in ranked if not c.is_ballpark)

    recommended = _choose_recommended(non_ballpark, aoi_bbox)

    missing = _dedupe_grids(
        g for c in ranked for g in c.grids if not g.available
    )

    return RecommendationResult(
        source_crs=src.to_string(),
        target_crs=dst.to_string(),
        candidates=visible,
        recommended=recommended,
        ballpark_only=ballpark_only,
        missing_grids=missing,
    )


def _with_score(candidate: TransformCandidate, score: float) -> TransformCandidate:
    # dataclass is frozen; rebuild with the computed score.
    return TransformCandidate(
        description=candidate.description,
        accuracy_m=candidate.accuracy_m,
        is_ballpark=candidate.is_ballpark,
        area_of_use=candidate.area_of_use,
        grids=candidate.grids,
        pipeline=candidate.pipeline,
        available=candidate.available,
        covers_aoi=candidate.covers_aoi,
        rank_score=score,
        auth_code=candidate.auth_code,
    )


def _choose_recommended(
    non_ballpark: Sequence[TransformCandidate], aoi_bbox: Optional[BBox]
) -> Optional[TransformCandidate]:
    """Top non-ballpark, available candidate -- preferring AOI coverage.

    Never recommends a ballpark transform (survey-grade safety).
    """
    available = [c for c in non_ballpark if c.available]
    if not available:
        return None
    if aoi_bbox is not None:
        covering = [c for c in available if c.covers_aoi]
        if covering:
            return covering[0]
    return available[0]


def _dedupe_grids(grids) -> Tuple[GridInfo, ...]:  # noqa: ANN001
    seen = set()
    out: List[GridInfo] = []
    for g in grids:
        if g.short_name in seen:
            continue
        seen.add(g.short_name)
        out.append(g)
    return tuple(out)
