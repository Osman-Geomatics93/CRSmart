"""Epoch tab (Feature B): explain and run epoch-aware transforms via Processing.

The tab analyses whether an epoch is required between two CRSs (plain-language
reason from the engine) and runs the ``epochtransform`` Processing algorithm on a
selected point layer. It refuses to run when an epoch is required but unset.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.gui import QgsMapLayerComboBox, QgsProjectionSelectionWidget
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.epoch import analyze_epoch
from ...processing.algorithms.base import qgs_crs_to_pyproj

if TYPE_CHECKING:  # pragma: no cover - typing only
    from qgis.gui import QgisInterface


class EpochTab(QWidget):
    """Feature B UI."""

    def __init__(self, iface: QgisInterface, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.iface = iface

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.layer_combo = QgsMapLayerComboBox(self)
        try:
            from qgis.core import QgsMapLayerProxyModel

            self.layer_combo.setFilters(QgsMapLayerProxyModel.Filter.PointLayer)
        except Exception:  # pragma: no cover - older API name fallback
            pass
        form.addRow(self.tr("Point layer"), self.layer_combo)

        self.target_sel = QgsProjectionSelectionWidget(self)
        form.addRow(self.tr("Target CRS"), self.target_sel)

        self.epoch_spin = QDoubleSpinBox(self)
        self.epoch_spin.setRange(1900.0, 2100.0)
        self.epoch_spin.setDecimals(3)
        self.epoch_spin.setValue(2020.0)
        self.epoch_spin.setSpecialValueText(self.tr("(not set)"))
        self.epoch_spin.setMinimum(0.0)  # 0 acts as "not set" sentinel in the UI
        form.addRow(self.tr("Coordinate epoch (decimal year)"), self.epoch_spin)
        layout.addLayout(form)

        self.status = QLabel("", self)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.check_btn = QPushButton(self.tr("Explain epoch requirement"), self)
        self.check_btn.clicked.connect(self.on_check)
        layout.addWidget(self.check_btn)

        self.run_btn = QPushButton(self.tr("Run epoch transform"), self)
        self.run_btn.clicked.connect(self.on_run)
        layout.addWidget(self.run_btn)
        layout.addStretch(1)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate("CRSmart", message)

    def _epoch_value(self) -> float | None:
        value = self.epoch_spin.value()
        return None if value <= 0.0 else value

    def on_check(self) -> None:
        layer = self.layer_combo.currentLayer()
        target = self.target_sel.crs()
        if layer is None or not target.isValid():
            self.status.setText(self.tr("Select a point layer and a target CRS."))
            return
        try:
            info = analyze_epoch(
                qgs_crs_to_pyproj(layer.crs()),
                qgs_crs_to_pyproj(target),
                self._epoch_value(),
                self._epoch_value(),
            )
        except Exception as exc:
            self.status.setText(self.tr("Error: {e}").format(e=exc))
            return
        self.status.setText(info.reason)

    def on_run(self) -> None:
        import processing

        layer = self.layer_combo.currentLayer()
        target = self.target_sel.crs()
        if layer is None or not target.isValid():
            self._warn(self.tr("Select a point layer and a target CRS."))
            return
        params = {
            "INPUT": layer,
            "TARGET_CRS": target,
            "OUTPUT": "memory:",
        }
        epoch = self._epoch_value()
        if epoch is not None:
            params["EPOCH"] = epoch
        try:
            # runAndLoadResults adds the output layer to the project so the user
            # can actually see it; plain run() would create and discard it.
            processing.runAndLoadResults("crsmart:epochtransform", params)
        except Exception as exc:
            self._warn(self.tr("Transform failed: {e}").format(e=exc))
            return
        self._info(self.tr("Epoch transform complete; added the result layer."))

    def _info(self, text: str) -> None:
        bar = self.iface.messageBar() if self.iface else None
        if bar is not None:
            bar.pushInfo("CRSmart", text)

    def _warn(self, text: str) -> None:
        bar = self.iface.messageBar() if self.iface else None
        if bar is not None:
            bar.pushWarning("CRSmart", text)
