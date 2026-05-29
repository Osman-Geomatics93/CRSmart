# -*- coding: utf-8 -*-
"""Phase 1 smoke tests: the empty plugin imports, registers, and tears down."""
from __future__ import annotations

import configparser
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "crsmart"


def test_classfactory_importable() -> None:
    from crsmart import classFactory

    assert callable(classFactory)


def test_metadata_declares_target_versions() -> None:
    parser = configparser.ConfigParser()
    parser.read(PACKAGE_DIR / "metadata.txt", encoding="utf-8")
    general = parser["general"]
    assert general["qgisMinimumVersion"] == "3.40"
    assert general["qgisMaximumVersion"] == "4.99"
    assert general["supportsQt6"] == "True"
    assert general["license"] == "GPL-2.0"
    assert general["hasProcessingProvider"].lower() == "yes"


def test_provider_registers(qgis_app) -> None:  # noqa: ANN001 (pytest fixture)
    from qgis.core import QgsApplication

    from crsmart.processing.provider import CRSmartProvider

    provider = CRSmartProvider()
    registry = QgsApplication.processingRegistry()
    assert registry.addProvider(provider)
    try:
        assert provider.id() == "crsmart"
        assert registry.providerById("crsmart") is not None
    finally:
        registry.removeProvider(provider)


def test_dock_instantiates(qgis_app) -> None:  # noqa: ANN001 (pytest fixture)
    from crsmart.gui.dock import CRSmartDock

    dock = CRSmartDock(iface=None, parent=None)
    assert dock.objectName() == "CRSmartDock"
    dock.deleteLater()


def test_plugin_processing_lifecycle(qgis_app) -> None:  # noqa: ANN001 (pytest fixture)
    """initProcessing + unload must be reversible without a GUI iface."""
    from qgis.core import QgsApplication

    from crsmart import classFactory

    plugin = classFactory(iface=None)
    plugin.initProcessing()
    assert QgsApplication.processingRegistry().providerById("crsmart") is not None
    plugin.unload()
    assert QgsApplication.processingRegistry().providerById("crsmart") is None
