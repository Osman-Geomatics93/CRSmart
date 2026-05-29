"""Feature C as a Processing algorithm: fit a local site calibration from a CSV.

Reads matched control points from a CSV (columns: local_x, local_y, target_x,
target_y), fits a 2D Helmert (4-parameter) or affine (6-parameter) transform by
least squares, reports residuals / RMSE / outliers, and emits a reusable PROJ
pipeline string.
"""

from __future__ import annotations

import csv
import html
from typing import Any

from qgis.core import (
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingOutputNumber,
    QgsProcessingOutputString,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
)

from ...core.calibration import (
    control_points_from_rows,
    fit_affine_2d,
    fit_helmert_2d,
)
from ...core.errors import CalibrationError
from ...core.models import CalibrationResult
from .base import CRSmartAlgorithm

_METHODS = ["helmert", "affine"]


class FitCalibrationAlgorithm(CRSmartAlgorithm):
    INPUT_CSV = "INPUT_CSV"
    METHOD = "METHOD"
    OUTLIER_THRESHOLD = "OUTLIER_THRESHOLD"
    OUTPUT_HTML = "OUTPUT_HTML"
    PIPELINE = "PIPELINE"
    RMSE = "RMSE"
    N_OUTLIERS = "N_OUTLIERS"

    def name(self) -> str:
        return "fitcalibration"

    def displayName(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr("Fit local site calibration (Helmert/affine)")

    def shortHelpString(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr(
            "Fits a local site calibration from matched control points in a CSV "
            "file with columns: local_x, local_y, target_x, target_y (a header "
            "row is auto-detected). Choose a conformal Helmert (4-parameter: "
            "scale, rotation, translation) or a 6-parameter affine fit. Reports "
            "per-point residuals, RMSE and flagged outliers, and returns a "
            "reusable PROJ pipeline (+proj=affine) describing the calibration."
        )

    def initAlgorithm(self, config: dict[str, Any] | None = None) -> None:  # noqa: N802
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_CSV,
                self.tr("Control points CSV"),
                extension="csv",
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.METHOD,
                self.tr("Method"),
                options=[
                    self.tr("Helmert (conformal, 4-param)"),
                    self.tr("Affine (6-param)"),
                ],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.OUTLIER_THRESHOLD,
                self.tr("Outlier threshold (standardized residual)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=3.5,
                minValue=0.0,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_HTML,
                self.tr("Calibration report (HTML)"),
                self.tr("HTML files (*.html)"),
                optional=True,
                createByDefault=False,
            )
        )
        self.addOutput(
            QgsProcessingOutputString(self.PIPELINE, self.tr("Calibration pipeline"))
        )
        self.addOutput(QgsProcessingOutputNumber(self.RMSE, self.tr("RMSE")))
        self.addOutput(
            QgsProcessingOutputNumber(self.N_OUTLIERS, self.tr("Number of outliers"))
        )

    def processAlgorithm(  # noqa: N802 (QGIS API name)
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        csv_path = self.parameterAsFile(parameters, self.INPUT_CSV, context)
        method_idx = self.parameterAsEnum(parameters, self.METHOD, context)
        threshold = self.parameterAsDouble(parameters, self.OUTLIER_THRESHOLD, context)
        method = _METHODS[method_idx]

        try:
            with open(csv_path, encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.reader(fh))
            local, target = control_points_from_rows(rows)
        except (OSError, CalibrationError) as exc:
            raise QgsProcessingException(
                self.tr("Could not read control points: {err}").format(err=exc)
            ) from exc

        feedback.pushInfo(
            self.tr("Read {n} control points; fitting {method}.").format(
                n=len(local), method=method
            )
        )

        try:
            if method == "helmert":
                result = fit_helmert_2d(local, target, outlier_threshold=threshold)
            else:
                result = fit_affine_2d(local, target, outlier_threshold=threshold)
        except CalibrationError as exc:
            raise QgsProcessingException(str(exc)) from exc

        feedback.pushInfo(self.tr("RMSE: {rmse:.4g}").format(rmse=result.rmse))
        if result.outliers:
            feedback.pushWarning(
                self.tr("Outliers at point index/indices: {idx}").format(
                    idx=", ".join(str(i) for i in result.outliers)
                )
            )
        feedback.pushInfo(self.tr("Pipeline: {p}").format(p=result.pipeline))

        outputs: dict[str, Any] = {
            self.PIPELINE: result.pipeline,
            self.RMSE: float(result.rmse),
            self.N_OUTLIERS: len(result.outliers),
        }

        html_path = self.parameterAsFileOutput(parameters, self.OUTPUT_HTML, context)
        if html_path:
            self._write_html(html_path, result)
            outputs[self.OUTPUT_HTML] = html_path

        return outputs

    def _write_html(self, path: str, result: CalibrationResult) -> None:
        params = "".join(
            f"<tr><td>{html.escape(k)}</td><td>{v:.6g}</td></tr>"
            for k, v in result.params.items()
        )
        res_rows = "".join(
            "<tr>"
            f"<td>{r.index}</td><td>{r.dx:.4g}</td><td>{r.dy:.4g}</td>"
            f"<td>{r.magnitude:.4g}</td><td>{r.standardized:.3g}</td>"
            f"<td>{'YES' if r.is_outlier else ''}</td>"
            "</tr>"
            for r in result.residuals
        )
        doc = (
            "<html><head><meta charset='utf-8'>"
            "<title>CRSmart calibration</title></head><body>"
            f"<h2>Local site calibration ({html.escape(result.method)})</h2>"
            f"<p>Points: {result.n_points} &nbsp; RMSE: {result.rmse:.6g} "
            f"&nbsp; Outliers: {len(result.outliers)}</p>"
            f"<p><b>Pipeline:</b><br><code>{html.escape(result.pipeline)}</code></p>"
            "<h3>Parameters</h3>"
            "<table border='1' cellpadding='4' cellspacing='0'>"
            f"<tr><th>name</th><th>value</th></tr>{params}</table>"
            "<h3>Residuals</h3>"
            "<table border='1' cellpadding='4' cellspacing='0'>"
            "<tr><th>#</th><th>dx</th><th>dy</th><th>|r|</th>"
            f"<th>std</th><th>outlier</th></tr>{res_rows}</table>"
            "</body></html>"
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(doc)
