"""Feature A as a Processing algorithm: recommend a transformation.

Enumerates candidate operations between two CRSs, ranks them by accuracy and
area-of-validity, flags ballpark-only situations and missing PROJ grids, and
emits the recommended PROJ pipeline string for reuse.
"""

from __future__ import annotations

import html
from typing import Any

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingOutputBoolean,
    QgsProcessingOutputNumber,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFileDestination,
)

from ...core.models import RecommendationResult
from ...core.transform_recommender import enumerate_candidates
from .base import CRSmartAlgorithm

WGS84 = "EPSG:4326"


class RecommendTransformAlgorithm(CRSmartAlgorithm):
    SOURCE_CRS = "SOURCE_CRS"
    TARGET_CRS = "TARGET_CRS"
    EXTENT = "EXTENT"
    ALLOW_BALLPARK = "ALLOW_BALLPARK"
    OUTPUT_HTML = "OUTPUT_HTML"
    RECOMMENDED_PIPELINE = "RECOMMENDED_PIPELINE"
    RECOMMENDED_ACCURACY = "RECOMMENDED_ACCURACY"
    BALLPARK_ONLY = "BALLPARK_ONLY"

    def name(self) -> str:
        return "recommendtransform"

    def displayName(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr("Recommend transformation (with uncertainty)")

    def shortHelpString(self) -> str:  # noqa: N802 (QGIS API name)
        return self.tr(
            "Lists every candidate transformation between the source and target "
            "CRS, annotated with accuracy (metres), area of validity, whether it "
            "is a ballpark (unknown-accuracy) transform, and whether it needs a "
            "PROJ grid that is not installed locally. The best non-ballpark, "
            "locally-available operation is recommended and its PROJ pipeline is "
            "returned for reuse.\n\n"
            "If only a ballpark transform exists, the algorithm warns and makes "
            "no recommendation unless 'Allow ballpark transforms' is checked."
        )

    def initAlgorithm(self, config: dict[str, Any] | None = None) -> None:  # noqa: N802
        self.addParameter(
            QgsProcessingParameterCrs(self.SOURCE_CRS, self.tr("Source CRS"))
        )
        self.addParameter(
            QgsProcessingParameterCrs(self.TARGET_CRS, self.tr("Target CRS"))
        )
        self.addParameter(
            QgsProcessingParameterExtent(
                self.EXTENT, self.tr("Area of interest (optional)"), optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ALLOW_BALLPARK,
                self.tr("Allow ballpark transforms"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_HTML,
                self.tr("Candidate report (HTML)"),
                self.tr("HTML files (*.html)"),
                optional=True,
                createByDefault=False,
            )
        )
        self.addOutput(
            QgsProcessingOutputString(
                self.RECOMMENDED_PIPELINE, self.tr("Recommended PROJ pipeline")
            )
        )
        self.addOutput(
            QgsProcessingOutputNumber(
                self.RECOMMENDED_ACCURACY, self.tr("Recommended accuracy (m)")
            )
        )
        self.addOutput(
            QgsProcessingOutputBoolean(
                self.BALLPARK_ONLY, self.tr("Only ballpark available")
            )
        )

    def processAlgorithm(  # noqa: N802 (QGIS API name)
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        source = self.parameterAsCrs(parameters, self.SOURCE_CRS, context)
        target = self.parameterAsCrs(parameters, self.TARGET_CRS, context)
        allow_ballpark = self.parameterAsBool(
            parameters, self.ALLOW_BALLPARK, context
        )

        aoi_bbox = None
        if parameters.get(self.EXTENT):
            extent = self.parameterAsExtent(
                parameters,
                self.EXTENT,
                context,
                QgsCoordinateReferenceSystem(WGS84),
            )
            if not extent.isNull():
                aoi_bbox = (
                    extent.xMinimum(),
                    extent.yMinimum(),
                    extent.xMaximum(),
                    extent.yMaximum(),
                )

        result = enumerate_candidates(
            source.toWkt(),
            target.toWkt(),
            area_of_interest=aoi_bbox,
            allow_ballpark=allow_ballpark,
        )

        feedback.pushInfo(
            self.tr("Found {n} candidate operation(s).").format(
                n=len(result.candidates)
            )
        )
        for i, cand in enumerate(result.candidates, start=1):
            acc = "unknown" if cand.accuracy_m is None else f"{cand.accuracy_m:g} m"
            flags = []
            if cand.is_ballpark:
                flags.append("BALLPARK")
            if not cand.available:
                flags.append("MISSING GRID")
            suffix = f"  [{', '.join(flags)}]" if flags else ""
            feedback.pushInfo(f"  {i}. {cand.description} — {acc}{suffix}")

        if result.ballpark_only:
            feedback.pushWarning(
                self.tr(
                    "Only a BALLPARK transform is available between these CRSs. "
                    "Its accuracy is unknown and it must not be used for "
                    "survey-grade work."
                )
            )
        if result.missing_grids:
            names = ", ".join(g.short_name for g in result.missing_grids)
            feedback.pushWarning(
                self.tr(
                    "A more accurate operation needs PROJ grid(s) not installed "
                    "locally: {names}. Install them (with consent) to enable it."
                ).format(names=names)
            )

        recommended = result.recommended
        pipeline = recommended.pipeline if recommended else ""
        accuracy = (
            recommended.accuracy_m
            if recommended and recommended.accuracy_m is not None
            else -1.0
        )
        if recommended is not None:
            feedback.pushInfo(
                self.tr("Recommended: {desc}").format(desc=recommended.description)
            )

        outputs: dict[str, Any] = {
            self.RECOMMENDED_PIPELINE: pipeline or "",
            self.RECOMMENDED_ACCURACY: float(accuracy),
            self.BALLPARK_ONLY: result.ballpark_only,
        }

        html_path = self.parameterAsFileOutput(parameters, self.OUTPUT_HTML, context)
        if html_path:
            self._write_html(html_path, result)
            outputs[self.OUTPUT_HTML] = html_path

        return outputs

    def _write_html(self, path: str, result: RecommendationResult) -> None:
        rows = []
        for i, c in enumerate(result.candidates, start=1):
            acc = "unknown" if c.accuracy_m is None else f"{c.accuracy_m:g}"
            grids = ", ".join(g.short_name for g in c.grids) or "&mdash;"
            rows.append(
                "<tr>"
                f"<td>{i}</td>"
                f"<td>{html.escape(c.description)}</td>"
                f"<td>{acc}</td>"
                f"<td>{'yes' if c.is_ballpark else 'no'}</td>"
                f"<td>{'yes' if c.available else 'no'}</td>"
                f"<td>{html.escape(grids)}</td>"
                "</tr>"
            )
        rec = result.recommended
        rec_html = (
            f"<p><b>Recommended:</b> {html.escape(rec.description)}<br>"
            f"<code>{html.escape(rec.pipeline or '')}</code></p>"
            if rec
            else "<p><b>No non-ballpark recommendation available.</b></p>"
        )
        doc = (
            "<html><head><meta charset='utf-8'><title>CRSmart candidates</title>"
            "</head><body>"
            f"<h2>Transformation candidates</h2>"
            f"<p>{html.escape(result.source_crs)} &rarr; "
            f"{html.escape(result.target_crs)}</p>"
            f"{rec_html}"
            "<table border='1' cellpadding='4' cellspacing='0'>"
            "<tr><th>#</th><th>Operation</th><th>Accuracy (m)</th>"
            "<th>Ballpark</th><th>Available</th><th>Grids</th></tr>"
            f"{''.join(rows)}"
            "</table></body></html>"
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(doc)
