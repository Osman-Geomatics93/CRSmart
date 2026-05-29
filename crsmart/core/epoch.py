"""Feature B -- epoch-aware / dynamic-datum (4D) transformations (pure Python).

A *dynamic* datum is tied to a plate-fixed reference frame whose coordinates
drift with time (e.g. the ITRF realizations, GDA2020). Transforming to/from such
a frame is time-dependent: the coordinate epoch (decimal year) matters. This
module detects when an epoch is required, explains why in plain language, and
performs the 4D transform (x, y, z, t) through pyproj/PROJ.
"""

from __future__ import annotations

from pyproj.transformer import Transformer

from .errors import EpochRequiredError
from .models import EpochInfo
from .transform_recommender import CRSLike, coerce_crs


def is_dynamic(crs: CRSLike) -> bool:
    """Whether a CRS is based on a dynamic (time-dependent) reference frame.

    Verified against pyproj/PROJ: a dynamic frame's datum ``type_name`` contains
    "Dynamic" (e.g. "Dynamic Geodetic Reference Frame").
    """
    obj = coerce_crs(crs)
    datum = obj.datum
    if datum is None:
        # Compound CRS: inspect the horizontal sub-CRS.
        return any(is_dynamic(sub) for sub in obj.sub_crs_list)
    type_name = (getattr(datum, "type_name", "") or "").lower()
    return "dynamic" in type_name


def analyze_epoch(
    source: CRSLike,
    target: CRSLike,
    source_epoch: float | None = None,
    target_epoch: float | None = None,
) -> EpochInfo:
    """Decide whether a coordinate epoch is required and explain why.

    An epoch is required when at least one side is a dynamic frame and the user
    has not supplied an epoch for it; without it the time-dependent step is
    ambiguous and could be silently wrong.
    """
    src = coerce_crs(source)
    dst = coerce_crs(target)
    src_dyn = is_dynamic(src)
    dst_dyn = is_dynamic(dst)

    if not src_dyn and not dst_dyn:
        return EpochInfo(
            required=False,
            reason="Neither CRS is dynamic; a coordinate epoch is not needed.",
            source_is_dynamic=False,
            target_is_dynamic=False,
            source_epoch=source_epoch,
            target_epoch=target_epoch,
        )

    missing = (src_dyn and source_epoch is None) or (dst_dyn and target_epoch is None)
    sides = []
    if src_dyn:
        sides.append(f"source ({src.name})")
    if dst_dyn:
        sides.append(f"target ({dst.name})")
    side_text = " and ".join(sides)

    if missing:
        reason = (
            f"A coordinate epoch is required: {side_text} uses a dynamic "
            "reference frame whose coordinates change over time. Set the epoch "
            "(decimal year, e.g. 2020.0) of the data so the transformation is "
            "time-correct."
        )
    else:
        reason = (
            f"Epoch-aware transform: {side_text} is dynamic and an epoch is set, "
            "so the time-dependent step will be applied."
        )

    return EpochInfo(
        required=missing,
        reason=reason,
        source_is_dynamic=src_dyn,
        target_is_dynamic=dst_dyn,
        source_epoch=source_epoch,
        target_epoch=target_epoch,
    )


def require_epoch_or_raise(
    source: CRSLike,
    target: CRSLike,
    source_epoch: float | None = None,
    target_epoch: float | None = None,
) -> EpochInfo:
    """Return the :class:`EpochInfo`, raising if an epoch is required but unset."""
    info = analyze_epoch(source, target, source_epoch, target_epoch)
    if info.required:
        raise EpochRequiredError(info.reason)
    return info


def _build_4d_transformer(
    source: CRSLike,
    target: CRSLike,
    *,
    allow_ballpark: bool = False,
) -> Transformer:
    src = coerce_crs(source)
    dst = coerce_crs(target)
    return Transformer.from_crs(src, dst, always_xy=True, allow_ballpark=allow_ballpark)


def transform_4d(
    source: CRSLike,
    target: CRSLike,
    xx: float,
    yy: float,
    zz: float,
    tt: float,
    *,
    allow_ballpark: bool = False,
    enforce_epoch: bool = True,
) -> tuple[float, float, float, float]:
    """Perform a time-dependent (4D) transform of a single coordinate.

    :param xx, yy: horizontal coordinates (lon, lat for geographic CRS with
        ``always_xy=True``; easting, northing for projected).
    :param zz: ellipsoidal/vertical height.
    :param tt: coordinate epoch as a decimal year (e.g. ``2020.0``).
    :param enforce_epoch: if True (default), refuse to proceed when a dynamic
        frame is involved but ``tt`` is not finite.
    """
    if enforce_epoch and (tt is None or tt != tt):  # NaN check
        require_epoch_or_raise(source, target)
    transformer = _build_4d_transformer(source, target, allow_ballpark=allow_ballpark)
    x, y, z, t = transformer.transform(xx, yy, zz, tt)
    return float(x), float(y), float(z), float(t)
