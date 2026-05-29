"""Phase 4 -- GUI dock smoke/interaction tests (run under pytest-qgis in CI).

QGIS/Qt imports live inside test bodies so local collection without a QGIS
runtime succeeds; these execute in the CI QGIS containers.
"""

from __future__ import annotations


def test_dock_builds_all_tabs(qgis_iface) -> None:
    from crsmart.gui.dock import CRSmartDock

    dock = CRSmartDock(qgis_iface)
    tabs = dock.widget()
    titles = {tabs.tabText(i) for i in range(tabs.count())}
    assert {"Recommend", "Epoch", "Calibrate", "Vertical"} <= titles
    dock.deleteLater()


def test_recommender_tab_populates(qgis_iface) -> None:
    from crsmart.gui.widgets.recommender_tab import RecommenderTab
    from qgis.core import QgsCoordinateReferenceSystem

    tab = RecommenderTab(qgis_iface)
    tab.source_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:4201"))  # Adindan
    tab.target_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    tab.on_find()
    assert tab.table.rowCount() > 0
    assert tab._result is not None
    assert tab._result.recommended is not None
    tab.deleteLater()


def test_calibration_tab_fits_pasted_points(qgis_iface) -> None:
    from crsmart.gui.widgets.calibration_tab import CalibrationTab

    tab = CalibrationTab(qgis_iface)
    # Pure translation (+10, -5).
    text = "\n".join(
        f"{x},{y},{x + 10},{y - 5}" for x, y in [(0, 0), (100, 0), (0, 100), (100, 100)]
    )
    tab.points_edit.setPlainText(text)
    tab.on_fit()
    assert tab._result is not None
    assert tab._result.rmse < 1e-6
    assert tab._result.params["tx"] == __import__("pytest").approx(10.0, abs=1e-6)
    tab.deleteLater()


def test_vertical_tab_assembles_compound(qgis_iface) -> None:
    import pytest
    from crsmart.gui.widgets.vertical_tab import VerticalTab
    from qgis.core import QgsCoordinateReferenceSystem

    tab = VerticalTab(qgis_iface)
    tab.horizontal_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    tab.vertical_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:5703"))  # NAVD88
    # Some headless QGIS builds will not hold a standalone vertical CRS in the
    # projection-selection widget. The engine-level compound assembly is covered
    # authoritatively in tests/test_vertical.py, so skip only that environment.
    if not tab.vertical_sel.crs().isValid():
        tab.deleteLater()
        pytest.skip("QgsProjectionSelectionWidget cannot hold a vertical CRS here")

    tab.on_assemble()
    assert tab._compound_wkt is not None
    assert (
        "COMPOUND" in tab._compound_wkt.upper() or "COMPD" in tab._compound_wkt.upper()
    )
    tab.deleteLater()


def test_epoch_tab_explains_requirement(qgis_iface) -> None:
    from crsmart.gui.widgets.epoch_tab import EpochTab
    from qgis.core import (
        QgsCoordinateReferenceSystem,
        QgsFeature,
        QgsGeometry,
        QgsPoint,
        QgsProject,
        QgsVectorLayer,
    )

    layer = QgsVectorLayer("PointZ?crs=EPSG:7912", "itrf", "memory")  # dynamic
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry(QgsPoint(7.0, 46.0, 500.0)))
    layer.dataProvider().addFeature(feat)
    QgsProject.instance().addMapLayer(layer)
    try:
        tab = EpochTab(qgis_iface)
        tab.layer_combo.setLayer(layer)
        tab.target_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:7911"))
        tab.epoch_spin.setValue(0.0)  # "not set"
        tab.on_check()
        # Two dynamic frames + no epoch -> the status must explain it is required.
        assert "epoch" in tab.status.text().lower()
        tab.deleteLater()
    finally:
        QgsProject.instance().removeMapLayer(layer.id())
