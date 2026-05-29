"""Calibration tab (Feature C): paste/load control points, fit Helmert/affine.

Control points are entered as text (one ``local_x,local_y,target_x,target_y`` per
line) or loaded from a CSV. Fitting, residuals and the emitted PROJ pipeline all
come from ``crsmart.core``; the tab only displays them.
"""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING

import numpy as np
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core.calibration import (
    control_points_from_rows,
    fit_affine_2d,
    fit_helmert_2d,
)
from ...core.models import CalibrationResult

if TYPE_CHECKING:  # pragma: no cover - typing only
    from qgis.gui import QgisInterface


class CalibrationTab(QWidget):
    """Feature C UI."""

    def __init__(self, iface: QgisInterface, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.iface = iface
        self._result: CalibrationResult | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                self.tr(
                    "Control points — one per line: "
                    "local_x, local_y, target_x, target_y"
                ),
                self,
            )
        )
        self.points_edit = QPlainTextEdit(self)
        self.points_edit.setPlaceholderText("100,200,500100,6000200\n…")
        layout.addWidget(self.points_edit)

        top = QHBoxLayout()
        self.load_btn = QPushButton(self.tr("Load CSV…"), self)
        self.load_btn.clicked.connect(self.on_load_csv)
        top.addWidget(self.load_btn)
        top.addStretch(1)
        layout.addLayout(top)

        form = QFormLayout()
        self.method_combo = QComboBox(self)
        self.method_combo.addItems(
            [self.tr("Helmert (conformal, 4-param)"), self.tr("Affine (6-param)")]
        )
        form.addRow(self.tr("Method"), self.method_combo)
        self.threshold_edit = QLineEdit("3.5", self)
        form.addRow(self.tr("Outlier threshold (sigma)"), self.threshold_edit)
        layout.addLayout(form)

        self.fit_btn = QPushButton(self.tr("Fit calibration"), self)
        self.fit_btn.clicked.connect(self.on_fit)
        layout.addWidget(self.fit_btn)

        self.summary = QLabel("", self)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["#", "dx", "dy", self.tr("std"), self.tr("outlier")]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        layout.addWidget(self.table)

        self.copy_btn = QPushButton(self.tr("Copy pipeline"), self)
        self.copy_btn.clicked.connect(self.on_copy)
        self.copy_btn.setEnabled(False)
        layout.addWidget(self.copy_btn)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate("CRSmart", message)

    def on_load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Open control points CSV"), "", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, encoding="utf-8-sig", newline="") as fh:
                rows = list(csv.reader(fh))
        except OSError as exc:
            self._warn(self.tr("Could not read file: {e}").format(e=exc))
            return
        self.points_edit.setPlainText("\n".join(",".join(r) for r in rows))

    def _parse_points(self) -> tuple[np.ndarray, np.ndarray]:
        text = self.points_edit.toPlainText()
        rows = [line.split(",") for line in text.splitlines() if line.strip()]
        return control_points_from_rows(rows)

    def on_fit(self) -> None:
        try:
            local, target = self._parse_points()
            threshold = float(self.threshold_edit.text() or "3.5")
            if self.method_combo.currentIndex() == 0:
                result = fit_helmert_2d(local, target, outlier_threshold=threshold)
            else:
                result = fit_affine_2d(local, target, outlier_threshold=threshold)
        except Exception as exc:
            self._warn(self.tr("Fit failed: {e}").format(e=exc))
            return
        self._result = result
        self._show(result)

    def _show(self, result: CalibrationResult) -> None:
        params = "  ".join(f"{k}={v:.6g}" for k, v in result.params.items())
        self.summary.setText(
            self.tr("RMSE: {rmse:.4g} — outliers: {n}\n{params}").format(
                rmse=result.rmse, n=len(result.outliers), params=params
            )
        )
        self.table.setRowCount(len(result.residuals))
        for row, res in enumerate(result.residuals):
            values = [
                str(res.index),
                f"{res.dx:.4g}",
                f"{res.dy:.4g}",
                f"{res.standardized:.3g}",
                self.tr("YES") if res.is_outlier else "",
            ]
            for col, text in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(text))
        self.copy_btn.setEnabled(True)

    def on_copy(self) -> None:
        if self._result is None:
            return
        QApplication.clipboard().setText(self._result.pipeline)
        self._info(self.tr("Pipeline copied to clipboard."))

    def _info(self, text: str) -> None:
        bar = self.iface.messageBar() if self.iface else None
        if bar is not None:
            bar.pushInfo("CRSmart", text)

    def _warn(self, text: str) -> None:
        bar = self.iface.messageBar() if self.iface else None
        if bar is not None:
            bar.pushWarning("CRSmart", text)
