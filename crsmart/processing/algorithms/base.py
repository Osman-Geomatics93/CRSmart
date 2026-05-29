"""Shared base class and helpers for CRSmart Processing algorithms.

Algorithms are thin wrappers: they marshal QGIS parameters into the pure
``crsmart.core`` engine and render the results. No geodetic logic lives here.
"""

from __future__ import annotations

from pyproj import CRS
from qgis.core import QgsCoordinateReferenceSystem, QgsProcessingAlgorithm
from qgis.PyQt.QtCore import QCoreApplication

GROUP_NAME = "CRS & datum tools"
GROUP_ID = "crsmarttools"


def qgs_crs_to_pyproj(crs: QgsCoordinateReferenceSystem) -> CRS:
    """Convert a QgsCoordinateReferenceSystem into a pyproj CRS via WKT.

    WKT is the lossless interchange that preserves compound CRS, datum ensembles
    and dynamic-frame metadata, so the engine sees exactly what QGIS holds.
    """
    return CRS.from_wkt(crs.toWkt())


def qgs_crs_to_crslike(crs: QgsCoordinateReferenceSystem) -> str:
    """Return an engine CRS identifier, preferring the authority id.

    The transformation recommender depends on PROJ's *catalogued* coordinate
    operations, which are keyed by authority code (e.g. ``EPSG:4201``). A WKT
    round-trip can drop that authority binding on some PROJ versions, leaving
    only a ballpark transform. So we pass the authid (``EPSG:xxxx``) when QGIS
    has one and fall back to WKT only for custom/compound CRSs without an id.
    """
    authid = crs.authid()
    return authid if authid else crs.toWkt()


def pyproj_crs_to_qgs(crs: CRS) -> QgsCoordinateReferenceSystem:
    """Convert a pyproj CRS back into a QgsCoordinateReferenceSystem via WKT."""
    return QgsCoordinateReferenceSystem.fromWkt(crs.to_wkt())


class CRSmartAlgorithm(QgsProcessingAlgorithm):
    """Base for all CRSmart algorithms: common group, tr, and createInstance."""

    def tr(self, string: str) -> str:
        return QCoreApplication.translate("CRSmart", string)

    def createInstance(self) -> CRSmartAlgorithm:  # noqa: N802 (QGIS API name)
        return type(self)()

    def group(self) -> str:
        return self.tr(GROUP_NAME)

    def groupId(self) -> str:  # noqa: N802 (QGIS API name)
        return GROUP_ID
