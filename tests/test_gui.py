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
    from crsmart.core.vertical import COMMON_VERTICAL_CRS
    from crsmart.gui.widgets.vertical_tab import VerticalTab
    from qgis.core import QgsCoordinateReferenceSystem

    tab = VerticalTab(qgis_iface)
    tab.horizontal_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

    # Preset path (index 0 = EGM96 height) -- no QGIS CRS picker involved, so this
    # works on every build (unlike the old vertical projection-selection widget).
    tab.vertical_combo.setCurrentIndex(0)
    tab.on_assemble()
    assert tab._compound_wkt is not None
    assert (
        "COMPOUND" in tab._compound_wkt.upper() or "COMPD" in tab._compound_wkt.upper()
    )

    # Custom free-text path overrides the preset.
    tab.vertical_combo.setCurrentIndex(len(COMMON_VERTICAL_CRS))  # the "Custom…" item
    tab.vertical_custom.setText("EPSG:5703")  # NAVD88 height
    tab.on_assemble()
    assert (
        "COMPOUND" in tab._compound_wkt.upper() or "COMPD" in tab._compound_wkt.upper()
    )
    tab.deleteLater()


def test_dock_clickthrough_all_tabs(qgis_iface) -> None:
    """End-to-end click-through of the whole dock: each tab's primary action,
    copy-to-clipboard, GUI outlier detection, and the vertical-CRS refusal.

    Drives the real ``CRSmartDock`` and its four tab widgets exactly as clicking
    would, complementing the per-tab tests above with a dock-level pass.
    """
    from pathlib import Path

    from crsmart.core.vertical import COMMON_VERTICAL_CRS
    from crsmart.gui.dock import CRSmartDock
    from qgis.core import (
        QgsApplication,
        QgsCoordinateReferenceSystem,
        QgsFeature,
        QgsGeometry,
        QgsPoint,
        QgsProject,
        QgsVectorLayer,
    )

    docs = Path(__file__).resolve().parent.parent / "docs"
    dock = CRSmartDock(qgis_iface)
    tabs = dock.widget()
    assert tabs.count() == 4
    recommend, epoch, calibrate, vertical = (tabs.widget(i) for i in range(4))

    # -- Recommend: enumerate, recommend a non-ballpark op, copy its pipeline.
    recommend.source_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:4201"))
    recommend.target_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    recommend.allow_ballpark.setChecked(False)
    recommend.on_find()
    assert recommend.table.rowCount() >= 3
    assert recommend._result.recommended is not None
    assert not recommend._result.recommended.is_ballpark
    recommend.table.selectRow(0)
    recommend.on_copy_pipeline()
    assert QgsApplication.clipboard().text().startswith("+proj=pipeline")

    # -- Calibrate: clean fit + copy pipeline, then catch the planted outlier.
    calibrate.points_edit.setPlainText(
        (docs / "sample_control_points.csv").read_text(encoding="utf-8")
    )
    calibrate.method_combo.setCurrentIndex(0)  # Helmert
    calibrate.threshold_edit.setText("3.5")
    calibrate.on_fit()
    assert calibrate._result.rmse < 0.1
    assert len(calibrate._result.outliers) == 0
    assert calibrate.table.rowCount() == 12
    calibrate.on_copy()
    assert QgsApplication.clipboard().text().startswith("+proj=pipeline")
    calibrate.points_edit.setPlainText(
        (docs / "sample_control_points_with_outlier.csv").read_text(encoding="utf-8")
    )
    calibrate.on_fit()
    assert list(calibrate._result.outliers) == [4]

    # -- Vertical: preset assemble + copy, then a compound CRS is refused.
    vertical.horizontal_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    vertical.vertical_combo.setCurrentIndex(0)  # EGM96 height (EPSG:5773)
    vertical.on_assemble()
    assert vertical._compound_wkt and "COMPOUND" in vertical._compound_wkt.upper()
    vertical.on_copy()
    assert "COMPOUND" in QgsApplication.clipboard().text().upper()
    # A compound CRS (EPSG:9707) in the vertical slot is refused, so the prior
    # valid EGM96 (5773) compound is left untouched -- proof it did not proceed.
    vertical.vertical_combo.setCurrentIndex(len(COMMON_VERTICAL_CRS))  # "Custom…"
    vertical.vertical_custom.setText("EPSG:9707")
    vertical.on_assemble()
    assert "5773" in vertical._compound_wkt

    # -- Epoch: refusal-without-epoch, then epoch-set status (no run needed).
    layer = QgsVectorLayer("PointZ?crs=EPSG:7912", "itrf_dock", "memory")
    feat = QgsFeature()
    feat.setGeometry(QgsGeometry(QgsPoint(151.2093, -33.8688, 0.0)))
    layer.dataProvider().addFeature(feat)
    QgsProject.instance().addMapLayer(layer)
    try:
        epoch.layer_combo.setLayer(layer)
        epoch.target_sel.setCrs(QgsCoordinateReferenceSystem("EPSG:7843"))
        epoch.epoch_spin.setValue(0.0)  # not set
        epoch.on_check()
        assert "required" in epoch.status.text().lower()
        epoch.epoch_spin.setValue(2020.0)
        epoch.on_check()
        assert "required" not in epoch.status.text().lower()
    finally:
        QgsProject.instance().removeMapLayer(layer.id())

    dock.deleteLater()


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
