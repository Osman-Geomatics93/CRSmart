"""Recommender tab (Feature A): pick source/target CRS, list ranked candidates.

The tab collects input via native QGIS widgets and renders results from
``crsmart.core``. It never performs geodesy itself. Choosing a candidate that
needs a missing grid offers a *consented* CDN download via the engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.gui import QgsProjectionSelectionWidget
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.grids import download_grids
from ...core.models import RecommendationResult, TransformCandidate
from ...core.transform_recommender import enumerate_candidates

if TYPE_CHECKING:  # pragma: no cover - typing only
    from qgis.gui import QgisInterface


class RecommenderTab(QWidget):
    """Feature A UI."""

    def __init__(self, iface: QgisInterface, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.iface = iface
        self._result: RecommendationResult | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.source_sel = QgsProjectionSelectionWidget(self)
        self.target_sel = QgsProjectionSelectionWidget(self)
        form.addRow(self.tr("Source CRS"), self.source_sel)
        form.addRow(self.tr("Target CRS"), self.target_sel)
        self.allow_ballpark = QCheckBox(self.tr("Allow ballpark transforms"), self)
        form.addRow("", self.allow_ballpark)
        layout.addLayout(form)

        self.find_btn = QPushButton(self.tr("Find transformations"), self)
        self.find_btn.clicked.connect(self.on_find)
        layout.addWidget(self.find_btn)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("Operation"),
                self.tr("Accuracy (m)"),
                self.tr("Ballpark"),
                self.tr("Available"),
                self.tr("Grids"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._update_buttons)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        self.copy_btn = QPushButton(self.tr("Copy pipeline"), self)
        self.copy_btn.clicked.connect(self.on_copy_pipeline)
        self.copy_btn.setEnabled(False)
        self.download_btn = QPushButton(self.tr("Download missing grid…"), self)
        self.download_btn.clicked.connect(self.on_download_grid)
        self.download_btn.setEnabled(False)
        buttons.addWidget(self.copy_btn)
        buttons.addWidget(self.download_btn)
        buttons.addStretch(1)
        layout.addLayout(buttons)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate("CRSmart", message)

    # -- actions ------------------------------------------------------------
    def on_find(self) -> None:
        source = self.source_sel.crs()
        target = self.target_sel.crs()
        if not source.isValid() or not target.isValid():
            self._warn(self.tr("Choose a valid source and target CRS."))
            return
        try:
            result = enumerate_candidates(
                source.toWkt(),
                target.toWkt(),
                allow_ballpark=self.allow_ballpark.isChecked(),
            )
        except Exception as exc:
            self._warn(self.tr("Could not enumerate transforms: {e}").format(e=exc))
            return
        self._result = result
        self._populate(result)

        if result.ballpark_only:
            self._warn(
                self.tr(
                    "Only a BALLPARK transform is available — accuracy unknown. "
                    "Do not use it for survey-grade work."
                ),
                level_warning=True,
            )
        elif result.recommended is not None:
            self._info(
                self.tr("Recommended: {d}").format(d=result.recommended.description)
            )
        if result.missing_grids:
            names = ", ".join(g.short_name for g in result.missing_grids)
            self._info(
                self.tr("A better operation needs grid(s): {n}").format(n=names),
                level_warning=True,
            )

    def _populate(self, result: RecommendationResult) -> None:
        self.table.setRowCount(len(result.candidates))
        for row, cand in enumerate(result.candidates):
            acc = "" if cand.accuracy_m is None else f"{cand.accuracy_m:g}"
            grids = ", ".join(g.short_name for g in cand.grids)
            values = [
                cand.description,
                acc,
                self.tr("yes") if cand.is_ballpark else self.tr("no"),
                self.tr("yes") if cand.available else self.tr("no"),
                grids,
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)
        self._update_buttons()

    def _selected(self) -> TransformCandidate | None:
        if self._result is None:
            return None
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        index = rows[0].row()
        if 0 <= index < len(self._result.candidates):
            return self._result.candidates[index]
        return None

    def _update_buttons(self) -> None:
        cand = self._selected()
        self.copy_btn.setEnabled(cand is not None and bool(cand.pipeline))
        self.download_btn.setEnabled(cand is not None and cand.needs_download)

    def on_copy_pipeline(self) -> None:
        cand = self._selected()
        if cand is None or not cand.pipeline:
            return
        QApplication.clipboard().setText(cand.pipeline)
        self._info(self.tr("Pipeline copied to clipboard."))

    def on_download_grid(self) -> None:
        cand = self._selected()
        if cand is None:
            return
        missing = cand.missing_grids
        if not missing:
            return
        names = "\n".join(f"  • {g.short_name}" for g in missing)
        reply = QMessageBox.question(
            self,
            self.tr("Download grids from PROJ CDN?"),
            self.tr(
                "CRSmart will download the following grid(s) from "
                "https://cdn.proj.org over the network:\n\n{names}\n\n"
                "Proceed?"
            ).format(names=names),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._info(self.tr("Download cancelled. No network access was made."))
            return
        try:
            report = download_grids(missing, consent=True)
        except Exception as exc:
            self._warn(self.tr("Download failed: {e}").format(e=exc))
            return
        if report.all_ok:
            self._info(self.tr("Grid(s) downloaded. Re-run to use them."))
        else:
            failed = ", ".join(r.short_name for r in report.failed)
            self._warn(self.tr("Some grids failed: {f}").format(f=failed))

    # -- messaging ----------------------------------------------------------
    def _info(self, text: str, level_warning: bool = False) -> None:
        bar = self.iface.messageBar() if self.iface else None
        if bar is None:
            return
        if level_warning:
            bar.pushWarning("CRSmart", text)
        else:
            bar.pushInfo("CRSmart", text)

    def _warn(self, text: str, level_warning: bool = True) -> None:
        self._info(text, level_warning=level_warning)
