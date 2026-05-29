"""The CRSmart dockable panel: one tab per feature (A-D).

The dock is a thin shell. Each tab collects input via native QGIS widgets, calls
the ``crsmart.core`` engine (or a Processing algorithm), and reports results and
warnings through ``iface.messageBar()``. No geodetic logic lives in the GUI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.gui import QgsDockWidget
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QTabWidget, QWidget

from .widgets.calibration_tab import CalibrationTab
from .widgets.epoch_tab import EpochTab
from .widgets.recommender_tab import RecommenderTab
from .widgets.vertical_tab import VerticalTab

if TYPE_CHECKING:  # pragma: no cover - typing only
    from qgis.gui import QgisInterface


class CRSmartDock(QgsDockWidget):
    """Dockable container hosting the four CRSmart feature tabs."""

    def __init__(self, iface: QgisInterface, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.iface = iface
        self.setObjectName("CRSmartDock")
        self.setWindowTitle(self.tr("CRSmart"))

        tabs = QTabWidget(self)
        tabs.addTab(RecommenderTab(iface, tabs), self.tr("Recommend"))
        tabs.addTab(EpochTab(iface, tabs), self.tr("Epoch"))
        tabs.addTab(CalibrationTab(iface, tabs), self.tr("Calibrate"))
        tabs.addTab(VerticalTab(iface, tabs), self.tr("Vertical"))
        self.setWidget(tabs)

    def tr(self, message: str) -> str:  # type: ignore[override]
        return QCoreApplication.translate("CRSmartDock", message)
