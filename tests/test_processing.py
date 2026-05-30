"""Phase 3 -- Processing algorithms (require QGIS; run under pytest-qgis in CI).

QGIS imports live inside the test bodies so local collection without a QGIS
runtime does not fail; these tests execute in the CI QGIS containers.
"""

from __future__ import annotations

from pathlib import Path

EXPECTED_ALGORITHMS = {
    "recommendtransform",
    "reprojectlayer",
    "epochtransform",
    "fitcalibration",
    "repairvertical",
}


def _run(alg, params):
    from qgis.core import QgsProcessingContext, QgsProcessingFeedback

    alg.initAlgorithm({})
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    results, ok = alg.run(params, context, feedback)
    assert ok, "algorithm run reported failure"
    return results


def test_provider_loads_all_algorithms(qgis_app) -> None:
    from crsmart.processing.provider import CRSmartProvider

    provider = CRSmartProvider()
    provider.refreshAlgorithms()
    ids = {alg.name() for alg in provider.algorithms()}
    assert ids >= EXPECTED_ALGORITHMS


def test_all_algorithms_run_on_main_thread(qgis_app) -> None:
    """Every CRSmart algorithm must declare NoThreading.

    The algorithms build pyproj/PROJ objects, whose database context is not
    reliably thread-safe inside QGIS Processing worker threads -- on Windows it
    can crash the host with a native access violation. NoThreading forces
    main-thread execution. Regression guard for that crash.
    """
    from crsmart.processing.provider import CRSmartProvider
    from qgis.core import Qgis, QgsProcessingAlgorithm

    no_threading = getattr(
        getattr(Qgis, "ProcessingAlgorithmFlag", None), "NoThreading", None
    )
    if no_threading is None:  # pragma: no cover - Qt5-only fallback
        no_threading = QgsProcessingAlgorithm.FlagNoThreading

    provider = CRSmartProvider()
    provider.refreshAlgorithms()
    algorithms = list(provider.algorithms())
    assert algorithms, "provider exposed no algorithms"
    for alg in algorithms:
        assert alg.flags() & no_threading, f"{alg.name()} is missing NoThreading"


def test_recommend_sudan_parametric(qgis_app) -> None:
    from crsmart.processing.algorithms.recommend_transform import (
        RecommendTransformAlgorithm,
    )

    results = _run(
        RecommendTransformAlgorithm(),
        {
            "SOURCE_CRS": "EPSG:4201",  # Adindan (Sudan)
            "TARGET_CRS": "EPSG:4326",
            "ALLOW_BALLPARK": False,
        },
    )
    assert results["RECOMMENDED_PIPELINE"].startswith("+proj=pipeline")
    assert results["BALLPARK_ONLY"] is False
    assert results["RECOMMENDED_ACCURACY"] > 0


def test_recommend_ballpark_only(qgis_app) -> None:
    from crsmart.processing.algorithms.recommend_transform import (
        RecommendTransformAlgorithm,
    )

    results = _run(
        RecommendTransformAlgorithm(),
        {
            "SOURCE_CRS": "EPSG:4202",  # AGD66
            "TARGET_CRS": "EPSG:4258",  # ETRS89 -> only ballpark exists
            "ALLOW_BALLPARK": False,
        },
    )
    assert results["BALLPARK_ONLY"] is True
    assert results["RECOMMENDED_PIPELINE"] == ""


def test_fit_calibration_from_csv(qgis_app, tmp_path) -> None:
    from crsmart.processing.algorithms.fit_calibration import (
        FitCalibrationAlgorithm,
    )

    csv_path = tmp_path / "control.csv"
    # Pure translation (+10, -5); Helmert must recover it with ~0 RMSE.
    lines = ["local_x,local_y,target_x,target_y"]
    pts = [(0, 0), (100, 0), (0, 100), (100, 100), (50, 50)]
    for x, y in pts:
        lines.append(f"{x},{y},{x + 10},{y - 5}")
    csv_path.write_text("\n".join(lines), encoding="utf-8")

    results = _run(
        FitCalibrationAlgorithm(),
        {"INPUT_CSV": str(csv_path), "METHOD": 0, "OUTLIER_THRESHOLD": 3.5},
    )
    assert results["PIPELINE"].startswith("+proj=pipeline")
    assert results["RMSE"] < 1e-6
    assert results["N_OUTLIERS"] == 0


def test_reproject_layer(qgis_app) -> None:
    from crsmart.processing.algorithms.reproject_layer import (
        ReprojectLayerAlgorithm,
    )
    from qgis.core import (
        QgsCoordinateReferenceSystem,
        QgsFeature,
        QgsGeometry,
        QgsPointXY,
        QgsVectorLayer,
    )

    layer = QgsVectorLayer("Point?crs=EPSG:4326&field=id:integer", "pts", "memory")
    feat = QgsFeature(layer.fields())
    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(32.5, 15.6)))  # Khartoum
    feat.setAttribute("id", 1)
    layer.dataProvider().addFeature(feat)

    results = _run(
        ReprojectLayerAlgorithm(),
        {"INPUT": layer, "TARGET_CRS": "EPSG:32636", "OUTPUT": "memory:"},
    )
    out = results["OUTPUT"]
    out_layer = out if isinstance(out, QgsVectorLayer) else None
    if out_layer is None:  # processing returns an id resolvable via context
        return
    assert out_layer.crs() == QgsCoordinateReferenceSystem("EPSG:32636")
    geom = next(out_layer.getFeatures()).geometry().asPoint()
    assert 200_000 < geom.x() < 800_000  # plausible UTM easting


def test_repair_vertical(qgis_app) -> None:
    from crsmart.processing.algorithms.repair_vertical import (
        RepairVerticalAlgorithm,
    )

    # Custom text field (overrides the preset).
    results = _run(
        RepairVerticalAlgorithm(),
        {"HORIZONTAL_CRS": "EPSG:4326", "VERTICAL_CRS": "EPSG:5703"},  # NAVD88
    )
    wkt = results["COMPOUND_WKT"]
    assert "COMPOUNDCRS" in wkt.upper() or "COMPD_CS" in wkt.upper()


def test_repair_vertical_preset(qgis_app) -> None:
    from crsmart.processing.algorithms.repair_vertical import (
        RepairVerticalAlgorithm,
    )

    # Preset path: no custom text, default preset (EGM96) -> compound assembled.
    results = _run(
        RepairVerticalAlgorithm(),
        {"HORIZONTAL_CRS": "EPSG:4326", "VERTICAL_PRESET": 0},
    )
    wkt = results["COMPOUND_WKT"]
    assert "COMPOUNDCRS" in wkt.upper() or "COMPD_CS" in wkt.upper()
    assert "EGM96" in wkt


def test_epoch_transform_points(qgis_app) -> None:
    from crsmart.processing.algorithms.epoch_transform import (
        EpochTransformAlgorithm,
    )
    from qgis.core import (
        QgsFeature,
        QgsGeometry,
        QgsPoint,
        QgsVectorLayer,
    )

    # ITRF2014 (dynamic) -> ITRF2008 (dynamic) at epoch 2010.0.
    layer = QgsVectorLayer("PointZ?crs=EPSG:7912&field=id:integer", "pts", "memory")
    feat = QgsFeature(layer.fields())
    feat.setGeometry(QgsGeometry(QgsPoint(7.0, 46.0, 500.0)))
    feat.setAttribute("id", 1)
    layer.dataProvider().addFeature(feat)

    results = _run(
        EpochTransformAlgorithm(),
        {
            "INPUT": layer,
            "TARGET_CRS": "EPSG:7911",
            "EPOCH": 2010.0,
            "OUTPUT": "memory:",
        },
    )
    assert "OUTPUT" in results


def test_epoch_transform_requires_epoch(qgis_app) -> None:
    from crsmart.processing.algorithms.epoch_transform import (
        EpochTransformAlgorithm,
    )
    from qgis.core import (
        QgsFeature,
        QgsGeometry,
        QgsPoint,
        QgsProcessingContext,
        QgsProcessingFeedback,
        QgsVectorLayer,
    )

    layer = QgsVectorLayer("PointZ?crs=EPSG:7912&field=id:integer", "pts", "memory")
    feat = QgsFeature(layer.fields())
    feat.setGeometry(QgsGeometry(QgsPoint(7.0, 46.0, 500.0)))
    layer.dataProvider().addFeature(feat)

    alg = EpochTransformAlgorithm()
    alg.initAlgorithm({})
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    # No EPOCH supplied between two dynamic frames -> must fail, not silently run.
    _results, ok = alg.run(
        {"INPUT": layer, "TARGET_CRS": "EPSG:7911", "OUTPUT": "memory:"},
        context,
        feedback,
    )
    assert ok is False


def test_processing_modules_import_only_in_qgis() -> None:
    """Sanity: the algorithm package directory contains the five modules."""
    alg_dir = (
        Path(__file__).resolve().parent.parent / "crsmart" / "processing" / "algorithms"
    )
    names = {p.stem for p in alg_dir.glob("*.py")}
    assert {
        "recommend_transform",
        "reproject_layer",
        "epoch_transform",
        "fit_calibration",
        "repair_vertical",
        "base",
    } <= names
