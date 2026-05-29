"""Feature D -- vertical datum repair (pure Python).

Detect a missing/undefined vertical CRS and assemble a compound (horizontal +
vertical) CRS so data that loads as "vertical CRS missing!" becomes fixable.
Where a geoid/vertical transformation grid is needed, callers reuse
``crsmart.core.grids`` (the recommender enumerates the vertical operations).
"""

from __future__ import annotations

from pyproj import CRS
from pyproj.crs import CompoundCRS

from .models import VerticalStatus
from .transform_recommender import CRSLike, coerce_crs


def _vertical_sub_crs(crs: CRS) -> CRS | None:
    if crs.is_vertical:
        return crs
    for sub in crs.sub_crs_list:
        if sub.is_vertical:
            return sub
    return None


def _horizontal_sub_crs(crs: CRS) -> CRS | None:
    if crs.is_compound:
        for sub in crs.sub_crs_list:
            if not sub.is_vertical:
                return sub
    if crs.is_geographic or crs.is_projected:
        return crs
    return None


def detect_vertical(crs: CRSLike) -> VerticalStatus:
    """Report the vertical-CRS state of a CRS.

    ``has_vertical`` is True only when a gravity-related vertical CRS is present
    (a compound CRS with a vertical component, or a standalone vertical CRS).
    A plain 2D or 3D-ellipsoidal geographic CRS is reported as *missing* vertical.
    """
    obj = coerce_crs(crs)
    vertical = _vertical_sub_crs(obj)
    horizontal = _horizontal_sub_crs(obj)
    has_vertical = vertical is not None

    if has_vertical:
        message = (
            f"Vertical CRS present: '{vertical.name}'"  # type: ignore[union-attr]
            + (f" on horizontal '{horizontal.name}'." if horizontal else ".")
        )
    else:
        message = (
            f"No vertical CRS defined for '{obj.name}'. Heights are undefined or "
            "ellipsoidal only; assemble a compound CRS to assign one."
        )

    return VerticalStatus(
        has_vertical=has_vertical,
        is_compound=obj.is_compound,
        horizontal_name=horizontal.name if horizontal else None,
        vertical_name=vertical.name if vertical else None,
        message=message,
    )


def assemble_compound(
    horizontal: CRSLike,
    vertical: CRSLike,
    *,
    name: str | None = None,
) -> CRS:
    """Assemble a compound CRS from a horizontal and a vertical CRS.

    :raises ValueError: if ``horizontal`` is not horizontal or ``vertical`` is
        not a vertical CRS.
    """
    h = coerce_crs(horizontal)
    v = coerce_crs(vertical)
    if not (h.is_geographic or h.is_projected):
        raise ValueError(f"'{h.name}' is not a horizontal (geographic/projected) CRS.")
    if not v.is_vertical:
        raise ValueError(f"'{v.name}' is not a vertical CRS.")
    compound_name = name or f"{h.name} + {v.name}"
    return CRS(CompoundCRS(name=compound_name, components=[h, v]).to_wkt())
