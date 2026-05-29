"""Main plugin class: wires the Processing provider and the dockable GUI.

Qt portability: every Qt symbol is imported through the ``qgis.PyQt`` shim and
every Qt enum is used in its fully-qualified (Qt6) form so this single codebase
runs on Qt5 (QGIS <= 3.44) and Qt6 (QGIS 4.x).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

if TYPE_CHECKING:  # pragma: no cover - typing only
    from qgis.gui import QgisInterface

    from .gui.dock import CRSmartDock
    from .processing.provider import CRSmartProvider

PLUGIN_DIR = os.path.dirname(__file__)
ICON_PATH = os.path.join(PLUGIN_DIR, "resources", "icon.svg")


class CRSmartPlugin:
    """Entry point QGIS instantiates via ``classFactory``."""

    def __init__(self, iface: QgisInterface) -> None:
        self.iface = iface
        self.provider: CRSmartProvider | None = None
        self.dock: CRSmartDock | None = None
        self.action: QAction | None = None

    # -- i18n ---------------------------------------------------------------
    def tr(self, message: str) -> str:
        """Translate a user-facing string."""
        return QCoreApplication.translate("CRSmart", message)

    # -- lifecycle ----------------------------------------------------------
    def initGui(self) -> None:  # noqa: N802 (QGIS API name)
        """Called by QGIS when the plugin is enabled."""
        self.initProcessing()

        from .gui.dock import CRSmartDock

        self.dock = CRSmartDock(self.iface, parent=self.iface.mainWindow())
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock)
        self.dock.hide()

        icon = QIcon(ICON_PATH) if os.path.exists(ICON_PATH) else QIcon()
        self.action = QAction(icon, self.tr("CRSmart"), self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.toggled.connect(self._toggle_dock)
        self.iface.addPluginToMenu(self.tr("&CRSmart"), self.action)
        self.iface.addToolBarIcon(self.action)

    def initProcessing(self) -> None:  # noqa: N802 (QGIS API name)
        """Register the Processing provider."""
        from .processing.provider import CRSmartProvider

        self.provider = CRSmartProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self) -> None:
        """Called by QGIS when the plugin is disabled. Reverse everything."""
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None

        if self.action is not None:
            self.iface.removePluginMenu(self.tr("&CRSmart"), self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

        if self.dock is not None:
            self.iface.removeDockWidget(self.dock)
            self.dock.deleteLater()
            self.dock = None

    # -- ui callbacks -------------------------------------------------------
    def _toggle_dock(self, checked: bool) -> None:
        if self.dock is not None:
            self.dock.setVisible(checked)
