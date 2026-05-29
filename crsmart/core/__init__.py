"""CRSmart pure-Python engine.

CONTRACT: nothing in this subpackage may import ``qgis.PyQt``, ``qgis.gui`` or
rely on a QGIS ``iface``. Allowed third-party imports: ``pyproj``, ``numpy``, and
optionally ``qgis.core`` *only* behind an ``hasattr`` / try-import feature guard
with a pyproj fallback. This rule is enforced by ``tests/test_no_qt_in_core.py``.
"""

from __future__ import annotations

from .calibration import fit_affine_2d, fit_helmert_2d, to_pipeline
from .epoch import analyze_epoch, is_dynamic, require_epoch_or_raise, transform_4d
from .errors import (
    BallparkNotAllowedError,
    CalibrationError,
    ConsentRequiredError,
    CRSmartError,
    EpochRequiredError,
)
from .grids import DownloadReport, download_grids, is_network_enabled, select_missing
from .models import (
    AreaOfUseInfo,
    CalibrationResult,
    EpochInfo,
    GridInfo,
    RecommendationResult,
    Residual,
    TransformCandidate,
    VerticalStatus,
)
from .transform_recommender import coerce_crs, enumerate_candidates
from .vertical import assemble_compound, detect_vertical

__all__ = [
    "AreaOfUseInfo",
    "BallparkNotAllowedError",
    "CRSmartError",
    "CalibrationError",
    "CalibrationResult",
    "ConsentRequiredError",
    "DownloadReport",
    "EpochInfo",
    "EpochRequiredError",
    "GridInfo",
    "RecommendationResult",
    "Residual",
    "TransformCandidate",
    "VerticalStatus",
    "analyze_epoch",
    "assemble_compound",
    "coerce_crs",
    "detect_vertical",
    "download_grids",
    "enumerate_candidates",
    "fit_affine_2d",
    "fit_helmert_2d",
    "is_dynamic",
    "is_network_enabled",
    "require_epoch_or_raise",
    "select_missing",
    "to_pipeline",
    "transform_4d",
]
