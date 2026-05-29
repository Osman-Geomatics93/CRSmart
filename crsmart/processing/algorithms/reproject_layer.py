"""Feature A (apply): reproject a vector layer with an optional chosen operation.

Unlike the native reproject tool, this lets the user pin a specific PROJ
coordinate operation / pipeline (e.g. the one recommended by
``recommendtransform``) so the transform used is explicit and reproducible.
"""

from __future__ import annotations

from typing import Any

from qgis.core import (
    QgsCoordinateTransform,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterString,
)

from .base import CRSmartAlgorithm


class ReprojectLayerAlgorithm(CRSmartAlgorithm):
    INPUT = "INPUT"
    TARGET_CRS = "TARGET_CRS"
    OPERATION = "OPERATION"
    OUTPUT = "OUTPUT"

    def name(self) -> str:
        return "reprojectlayer"

    def displayName(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr("Reproject layer (explicit operation)")

    def shortHelpString(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr(
            "Writes a reprojected copy of a vector layer to the target CRS. "
            "Optionally pin a specific PROJ coordinate operation (pipeline "
            "string) so the exact transformation used is explicit and "
            "reproducible — paste the pipeline from 'Recommend transformation'."
        )

    def initAlgorithm(self, config: dict[str, Any] | None = None) -> None:  # noqa: N802
        self.addParameter(
            QgsProcessingParameterFeatureSource(self.INPUT, self.tr("Input layer"))
        )
        self.addParameter(
            QgsProcessingParameterCrs(self.TARGET_CRS, self.tr("Target CRS"))
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.OPERATION,
                self.tr("PROJ coordinate operation (optional)"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("Reprojected"))
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
        operation = self.parameterAsString(parameters, self.OPERATION, context)

        transform_context = context.transformContext()
        if operation:
            transform_context.addCoordinateOperation(source_crs, target_crs, operation)
            feedback.pushInfo(
                self.tr("Using pinned operation: {op}").format(op=operation)
            )
        xform = QgsCoordinateTransform(source_crs, target_crs, transform_context)

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
                if geom.transform(xform) != 0:
                    feedback.reportError(
                        self.tr("Failed to transform a feature; skipping it.")
                    )
                    continue
                feature.setGeometry(geom)
            sink.addFeature(feature)
            feedback.setProgress(int(current * step))

        return {self.OUTPUT: dest_id}
