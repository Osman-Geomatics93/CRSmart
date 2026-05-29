"""Feature D as a Processing algorithm: repair a missing vertical CRS.

Assembles a compound (horizontal + vertical) CRS and, optionally, writes a copy
of an input layer with that compound CRS assigned. Assigning a CRS does not move
coordinates; it declares what the existing coordinates mean.
"""

from __future__ import annotations

from typing import Any

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputString,
    QgsProcessingParameterCrs,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
)

from ...core.vertical import assemble_compound, detect_vertical
from .base import CRSmartAlgorithm, pyproj_crs_to_qgs, qgs_crs_to_pyproj


class RepairVerticalAlgorithm(CRSmartAlgorithm):
    INPUT = "INPUT"
    HORIZONTAL_CRS = "HORIZONTAL_CRS"
    VERTICAL_CRS = "VERTICAL_CRS"
    OUTPUT = "OUTPUT"
    COMPOUND_WKT = "COMPOUND_WKT"

    def name(self) -> str:
        return "repairvertical"

    def displayName(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr("Repair vertical CRS (assemble compound)")

    def shortHelpString(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr(
            "Assembles a compound CRS from a horizontal and a vertical CRS, to "
            "fix data that loads with a missing vertical CRS. If a layer is "
            "given, a copy is written with the compound CRS assigned (this "
            "declares the meaning of existing coordinates; it does not move "
            "them). The horizontal CRS defaults to the input layer's CRS when "
            "not set explicitly. The assembled compound CRS WKT is also returned."
        )

    def initAlgorithm(self, config: dict[str, Any] | None = None) -> None:  # noqa: N802
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT, self.tr("Input layer (optional)"), optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(
                self.HORIZONTAL_CRS,
                self.tr("Horizontal CRS (defaults to input layer CRS)"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterCrs(self.VERTICAL_CRS, self.tr("Vertical CRS"))
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Output (compound CRS assigned)"),
                optional=True,
                createByDefault=False,
            )
        )
        self.addOutput(
            QgsProcessingOutputString(self.COMPOUND_WKT, self.tr("Compound CRS WKT"))
        )

    def processAlgorithm(  # noqa: N802 (QGIS API name)
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        source = self.parameterAsSource(parameters, self.INPUT, context)

        horizontal = self.parameterAsCrs(parameters, self.HORIZONTAL_CRS, context)
        if horizontal is None or not horizontal.isValid():
            if source is None:
                raise QgsProcessingException(
                    self.tr(
                        "Provide a horizontal CRS, or an input layer to take it from."
                    )
                )
            horizontal = source.sourceCrs()

        vertical = self.parameterAsCrs(parameters, self.VERTICAL_CRS, context)

        h_py = qgs_crs_to_pyproj(horizontal)
        v_py = qgs_crs_to_pyproj(vertical)

        status = detect_vertical(h_py)
        feedback.pushInfo(status.message)

        try:
            compound_py = assemble_compound(h_py, v_py)
        except ValueError as exc:
            raise QgsProcessingException(str(exc)) from exc

        compound_qgs = pyproj_crs_to_qgs(compound_py)
        feedback.pushInfo(
            self.tr("Assembled compound CRS: {name}").format(
                name=compound_qgs.description() or compound_py.name
            )
        )

        outputs: dict[str, Any] = {self.COMPOUND_WKT: compound_py.to_wkt()}

        if source is not None and parameters.get(self.OUTPUT) is not None:
            sink, dest_id = self.parameterAsSink(
                parameters,
                self.OUTPUT,
                context,
                source.fields(),
                source.wkbType(),
                compound_qgs,
            )
            if sink is None:
                raise QgsProcessingException(
                    self.invalidSinkError(parameters, self.OUTPUT)
                )
            for feature in source.getFeatures():
                if feedback.isCanceled():
                    break
                sink.addFeature(feature)
            outputs[self.OUTPUT] = dest_id

        return outputs
