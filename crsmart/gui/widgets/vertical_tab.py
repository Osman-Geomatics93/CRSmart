"""Vertical tab (Feature D): detect a missing vertical CRS, assemble a compound.

The tab reports the vertical status of a chosen CRS/layer and assembles a
compound CRS from a horizontal + vertical pair. Detection and assembly come from
``crsmart.core``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.core import QgsApplication, QgsCoordinateReferenceSystem
from qgis.gui import QgsMapLayerComboBox, QgsProjectionSelectionWidget
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import (
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.vertical import assemble_compound, detect_vertical
from ...processing.algorithms.base import qgs_crs_to_pyproj

if TYPE_CHECKING:  # pragma: no cover - typing only
    from qgis.gui import QgisInterface


class VerticalTab(QWidget):
    """Feature D UI."""

    def __init__(self, iface: QgisInterface, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.iface = iface
        self._compound_wkt: str | None = None

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.layer_combo = QgsMapLayerComboBox(self)
        form.addRow(self.tr("Layer (optional)"), self.layer_combo)
        self.layer_combo.layerChanged.connect(self.on_detect)  # type: ignore[attr-defined]

        self.horizontal_sel = QgsProjectionSelectionWidget(self)
        form.addRow(self.tr("Horizontal CRS"), self.horizontal_sel)
        self.vertical_sel = QgsProjectionSelectionWidget(self)
        form.addRow(self.tr("Vertical CRS"), self.vertical_sel)
        layout.addLayout(form)

        self.status = QLabel("", self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.detect_btn = QPushButton(self.tr("Detect vertical CRS"), self)
        self.detect_btn.clicked.connect(self.on_detect)
        layout.addWidget(self.detect_btn)

        self.assemble_btn = QPushButton(self.tr("Assemble compound CRS"), self)
        self.assemble_btn.clicked.connect(self.on_assemble)
        layout.addWidget(self.assemble_btn)

        self.copy_btn = QPushButton(self.tr("Copy compound WKT"), self)
        self.copy_btn.clicked.connect(self.on_copy)
        self.copy_btn.setEnabled(False)
        layout.addWidget(self.copy_btn)
        layout.addStretch(1)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate("CRSmart", message)

    def _horizontal_crs(self) -> QgsCoordinateReferenceSystem:
        crs = self.horizontal_sel.crs()
        if crs.isValid():
            return crs
        layer = self.layer_combo.currentLayer()
        return layer.crs() if layer is not None else crs

    def on_detect(self) -> None:
        crs = self._horizontal_crs()
        if not crs.isValid():
            self.status.setText(self.tr("Select a CRS or a layer."))
            return
        try:
            status = detect_vertical(qgs_crs_to_pyproj(crs))
        except Exception as exc:
            self.status.setText(self.tr("Error: {e}").format(e=exc))
            return
        self.status.setText(status.message)

    def on_assemble(self) -> None:
        horizontal = self._horizontal_crs()
        vertical = self.vertical_sel.crs()
        if not horizontal.isValid() or not vertical.isValid():
            self._warn(self.tr("Select both a horizontal and a vertical CRS."))
            return
        try:
            compound = assemble_compound(
                qgs_crs_to_pyproj(horizontal), qgs_crs_to_pyproj(vertical)
            )
        except Exception as exc:
            self._warn(self.tr("Could not assemble: {e}").format(e=exc))
            return
        self._compound_wkt = compound.to_wkt()
        self.copy_btn.setEnabled(True)
        self.status.setText(
            self.tr("Assembled compound CRS: {name}").format(name=compound.name)
        )
        self._info(self.tr("Compound CRS assembled."))

    def on_copy(self) -> None:
        if self._compound_wkt is None:
            return
        QgsApplication.clipboard().setText(self._compound_wkt)
        self._info(self.tr("Compound WKT copied to clipboard."))

    def _info(self, text: str) -> None:
        bar = self.iface.messageBar() if self.iface else None
        if bar is not None:
            bar.pushInfo("CRSmart", text)

    def _warn(self, text: str) -> None:
        bar = self.iface.messageBar() if self.iface else None
        if bar is not None:
            bar.pushWarning("CRSmart", text)
