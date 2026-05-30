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

# Common standalone vertical (height) CRSs, as (label, EPSG code). Shared by the
# GUI dock and the Processing algorithm so users can pick one without QGIS's CRS
# selector, which on many builds does not list pure vertical CRSs at all.
COMMON_VERTICAL_CRS: tuple[tuple[str, int], ...] = (
    ("EGM96 height (EPSG:5773)", 5773),
    ("EGM2008 height (EPSG:3855)", 3855),
    ("EGM84 height (EPSG:5798)", 5798),
    ("NAVD88 height (EPSG:5703)", 5703),
    ("NAVD88 height - US survey foot (EPSG:6360)", 6360),
    ("MSL height (EPSG:5714)", 5714),
    ("EVRF2019 height - Europe (EPSG:9389)", 9389),
    ("AHD height - Australia (EPSG:5711)", 5711),
)


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

    :raises ValueError: if ``horizontal`` is not a plain horizontal CRS, or
        ``vertical`` is not a standalone vertical CRS (a compound CRS is rejected
        even though PROJ reports it as ``is_vertical`` — it merely *contains* a
        vertical axis, and nesting compounds is invalid).
    """
    h = coerce_crs(horizontal)
    v = coerce_crs(vertical)
    if h.is_compound or not (h.is_geographic or h.is_projected):
        raise ValueError(f"'{h.name}' is not a horizontal (geographic/projected) CRS.")
    # PROJ flags any CRS that contains a vertical axis as ``is_vertical`` -- that
    # includes compound CRSs (e.g. EPSG:9707 'WGS 84 + EGM96 height'). We need a
    # *standalone* vertical CRS so we never nest one compound inside another.
    if v.is_compound or not v.is_vertical:
        raise ValueError(
            f"'{v.name}' is not a standalone vertical (height) CRS. Choose a pure "
            "vertical CRS such as EGM96 height (EPSG:5773) or EGM2008 height "
            "(EPSG:3855) -- not a compound CRS like EPSG:9707."
        )
    compound_name = name or f"{h.name} + {v.name}"
    try:
        return CRS(CompoundCRS(name=compound_name, components=[h, v]).to_wkt())
    except Exception as exc:  # pragma: no cover - defensive; guards catch known cases
        raise ValueError(
            f"Could not assemble a compound CRS from '{h.name}' + '{v.name}': {exc}"
        ) from exc
