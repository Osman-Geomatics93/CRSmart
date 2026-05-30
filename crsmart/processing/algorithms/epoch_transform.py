"""Feature B as a Processing algorithm: epoch-aware (4D) point transform.

Performs a time-dependent transformation of a point layer at a given coordinate
epoch (decimal year), through pyproj. Refuses to proceed silently when a dynamic
reference frame is involved but no epoch is supplied.
"""

from __future__ import annotations

import math
from typing import Any

from pyproj.transformer import Transformer
from qgis.core import (
    QgsGeometry,
    QgsPoint,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsWkbTypes,
)

from ...core.epoch import analyze_epoch, make_4d_transformer
from ...core.errors import CRSmartError
from .base import CRSmartAlgorithm, qgs_crs_to_pyproj


class EpochTransformAlgorithm(CRSmartAlgorithm):
    INPUT = "INPUT"
    TARGET_CRS = "TARGET_CRS"
    EPOCH = "EPOCH"
    ALLOW_BALLPARK = "ALLOW_BALLPARK"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        return "epochtransform"

    def displayName(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr("Epoch-aware transform (dynamic datums)")

    def shortHelpString(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr(
            "Transforms a point layer between CRSs using a time-dependent (4D) "
            "operation at the given coordinate epoch (decimal year, e.g. 2020.0). "
            "Required when the source or target is a dynamic reference frame "
            "(e.g. an ITRF realization). Point Z values are carried through the "
            "transform; if a layer has no Z, height 0 is assumed."
        )

    def initAlgorithm(self, config: dict[str, Any] | None = None) -> None:  # noqa: N802
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input point layer"),
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(self.TARGET_CRS, self.tr("Target CRS"))
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.EPOCH,
                self.tr("Coordinate epoch (decimal year)"),
                type=QgsProcessingParameterNumber.Double,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ALLOW_BALLPARK,
                self.tr("Allow ballpark transform (low accuracy, not survey-grade)"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Transformed"))
        )

    def processAlgorithm(  # noqa: N802 (QGIS API name)
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )
        target_crs = self.parameterAsCrs(parameters, self.TARGET_CRS, context)
        source_crs = source.sourceCrs()

        epoch: float | None = None
        if parameters.get(self.EPOCH) is not None:
            epoch = self.parameterAsDouble(parameters, self.EPOCH, context)

        src_py = qgs_crs_to_pyproj(source_crs)
        dst_py = qgs_crs_to_pyproj(target_crs)

        info = analyze_epoch(src_py, dst_py, epoch, epoch)
        feedback.pushInfo(info.reason)
        if info.required:
            raise QgsProcessingException(
                self.tr(
                    "A coordinate epoch is required for this transform but none "
                    "was set. {reason}"
                ).format(reason=info.reason)
            )

        allow_ballpark = self.parameterAsBoolean(
            parameters, self.ALLOW_BALLPARK, context
        )
        try:
            transformer = make_4d_transformer(
                src_py, dst_py, allow_ballpark=allow_ballpark
            )
        except CRSmartError as exc:
            raise QgsProcessingException(str(exc)) from exc
        tt = epoch if epoch is not None else float("nan")

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            source.fields(),
            source.wkbType(),
            target_crs,
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        total = source.featureCount()
        step = 100.0 / total if total else 0.0
        for current, feature in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            geom = feature.geometry()
            if not geom.isEmpty():
                feature.setGeometry(self._transform_geometry(geom, transformer, tt))
            sink.addFeature(feature)
            feedback.setProgress(int(current * step))

        return {self.OUTPUT: dest_id}

    @staticmethod
    def _transform_geometry(
        geom: QgsGeometry, transformer: Transformer, tt: float
    ) -> QgsGeometry:
        has_z = QgsWkbTypes.hasZ(geom.wkbType())
        vertices = list(geom.vertices())
        xs = [v.x() for v in vertices]
        ys = [v.y() for v in vertices]
        zs = [(v.z() if has_z and not math.isnan(v.z()) else 0.0) for v in vertices]
        ts = [tt] * len(vertices)
        rx, ry, rz, _ = transformer.transform(xs, ys, zs, ts)
        out = QgsGeometry(geom)
        for i in range(len(vertices)):
            if has_z:
                out.moveVertex(QgsPoint(rx[i], ry[i], rz[i]), i)
            else:
                out.moveVertex(rx[i], ry[i], i)
        return out
