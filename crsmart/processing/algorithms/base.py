"""Shared base class and helpers for CRSmart Processing algorithms.

Algorithms are thin wrappers: they marshal QGIS parameters into the pure
``crsmart.core`` engine and render the results. No geodetic logic lives here.
"""

from __future__ import annotations

from pyproj import CRS
from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsProcessingAlgorithm
from qgis.PyQt.QtCore import QCoreApplication

GROUP_NAME = "CRS & datum tools"
GROUP_ID = "crsmarttools"


def qgs_crs_to_pyproj(crs: QgsCoordinateReferenceSystem) -> CRS:
    """Convert a QgsCoordinateReferenceSystem into a pyproj CRS.

    Prefer the authority id (e.g. ``EPSG:4326``) when QGIS has one: it is robust
    and keeps PROJ's catalogued metadata. Fall back to WKT for custom/compound
    CRSs without an authid. WKT alone is fragile -- some QGIS builds return an
    empty WKT for memory-layer CRSs, which would raise CRSError.
    """
    return CRS.from_user_input(qgs_crs_to_crslike(crs))


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

    def flags(self) -> QgsProcessingAlgorithm.Flags:
        """Run CRSmart algorithms on the main thread (never a worker thread).

        Every algorithm builds pyproj/PROJ objects, and PROJ's database context
        is not reliably thread-safe inside QGIS Processing worker threads -- on
        Windows, creating a ``pyproj.CRS`` in a worker thread can crash the host
        with a native access violation (``projCppContext::getDatabaseContext``).
        Declaring ``NoThreading`` makes QGIS execute the algorithm on the main
        thread, where QGIS has already initialised PROJ.

        Feature-detected so it works on both the Qt6 enum
        (``Qgis.ProcessingAlgorithmFlag.NoThreading``) and the older Qt5
        attribute (``QgsProcessingAlgorithm.FlagNoThreading``).
        """
        result = super().flags()
        no_threading = getattr(
            getattr(Qgis, "ProcessingAlgorithmFlag", None), "NoThreading", None
        )
        if no_threading is None:
            no_threading = getattr(QgsProcessingAlgorithm, "FlagNoThreading", None)
        if no_threading is not None:
            result |= no_threading
        return result

    def tr(self, string: str) -> str:
        return QCoreApplication.translate("CRSmart", string)

    def createInstance(self) -> CRSmartAlgorithm:  # noqa: N802 (QGIS API name)
        return type(self)()

    def group(self) -> str:
        return self.tr(GROUP_NAME)

    def groupId(self) -> str:  # noqa: N802 (QGIS API name)
        return GROUP_ID
