"""The CRSmart dockable panel (empty shell for Phase 1).

Feature tabs (recommender / epoch / calibration / vertical) are added in Phase 4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from qgis.gui import QgsDockWidget
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtWidgets import QLabel, QVBoxLayout, QWidget

if TYPE_CHECKING:  # pragma: no cover - typing only
    from qgis.gui import QgisInterface


class CRSmartDock(QgsDockWidget):
    """Dockable container for the CRSmart UI."""

    def __init__(self, iface: QgisInterface, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.iface = iface
        self.setObjectName("CRSmartDock")
        self.setWindowTitle(self.tr("CRSmart"))

        container = QWidget(self)
        layout = QVBoxLayout(container)
        placeholder = QLabel(
            self.tr("CRSmart panel — features arrive in Phase 4."), container
        )
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        layout.addWidget(placeholder)
        layout.addStretch(1)
        self.setWidget(container)

    def tr(self, message: str) -> str:
        return QCoreApplication.translate("CRSmartDock", message)
