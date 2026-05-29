"""The CRSmart Processing provider (stub for Phase 1).

Algorithms are added in Phase 3 via :meth:`loadAlgorithms`.
"""

from __future__ import annotations

import os

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

ICON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "resources", "icon.svg"
)


class CRSmartProvider(QgsProcessingProvider):
    """Groups all CRSmart Processing algorithms under one provider."""

    def loadAlgorithms(self) -> None:  # noqa: N802 (QGIS API name)
        """Register every CRSmart Processing algorithm."""
        from .algorithms.epoch_transform import EpochTransformAlgorithm
        from .algorithms.fit_calibration import FitCalibrationAlgorithm
        from .algorithms.recommend_transform import RecommendTransformAlgorithm
        from .algorithms.repair_vertical import RepairVerticalAlgorithm
        from .algorithms.reproject_layer import ReprojectLayerAlgorithm

        for algorithm in (
            RecommendTransformAlgorithm(),
            ReprojectLayerAlgorithm(),
            EpochTransformAlgorithm(),
            FitCalibrationAlgorithm(),
            RepairVerticalAlgorithm(),
        ):
            self.addAlgorithm(algorithm)

    def id(self) -> str:
        return "crsmart"

    def name(self) -> str:
        return "CRSmart"

    def longName(self) -> str:  # noqa: N802 (QGIS API name)
        return "CRSmart — CRS & datum transformation assistant"

    def icon(self) -> QIcon:
        return QIcon(ICON_PATH) if os.path.exists(ICON_PATH) else super().icon()
