"""CRSmart smoke test — paste into the QGIS Python Console.

Verifies an *installed* CRSmart build end to end: the Processing provider is
registered, the four core features behave, and the two headline safety
guarantees hold (epoch refusal + no-silent-network consent gate). Sample data
is embedded, so no files or network are needed.

Usage (QGIS ▸ Plugins ▸ Python Console):

    exec(open(r"<repo>/scripts/qgis_console_smoketest.py").read())

or just paste the whole file into the console. It prints PASS/FAIL per check
and a summary line; the final value `crsmart_smoketest_ok` is True iff all
checks passed.
"""

_results = []


def _check(name: str, cond: object, detail: str = "") -> bool:
    ok = bool(cond)
    _results.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{('  :: ' + detail) if detail else ''}")
    return ok


def _approx(a: "float | None", b: float, tol: float) -> bool:
    return a is not None and abs(a - b) <= tol


# 12 clean control points from a known Helmert: scale 1.0000150 (15 ppm),
# rotation 0.35 deg, tx 12000, ty -8000 (cols: local_x, local_y, target_x, target_y).
_CLEAN = [
    (100.0, 200.0, 12098.761, -7799.375),
    (1500.0, 300.0, 13498.140, -7690.821),
    (2600.0, 1800.0, 14588.976, -6184.077),
    (400.0, 2500.0, 12384.753, -5497.597),
    (3000.0, 3000.0, 14981.642, -4981.701),
    (1800.0, 900.0, 13794.492, -7089.010),
    (700.0, 1600.0, 12690.187, -6395.706),
    (2200.0, 2400.0, 14185.333, -5586.544),
    (900.0, 2900.0, 12882.292, -5094.504),
    (2400.0, 600.0, 14396.328, -7385.339),
    (1300.0, 2100.0, 13287.148, -5892.072),
    (500.0, 800.0, 12495.093, -7196.923),
]
# Same, but index 4 carries a deliberate ~20 m blunder.
_OUTLIER = list(_CLEAN)
_OUTLIER[4] = (3000.0, 3000.0, 14997.642, -4993.701)


# --- 0. Imports -------------------------------------------------------------
print("\n--- 0. Imports ---")
try:
    from crsmart.core import calibration, epoch, grids, vertical
    from crsmart.core import transform_recommender as rec
    from crsmart.core.errors import ConsentRequiredError, EpochRequiredError
    from crsmart.core.models import GridInfo

    _check("import crsmart.core.*", True)
    _core_ok = True
except Exception as exc:
    _check("import crsmart.core.*", False, repr(exc))
    _core_ok = False


# --- 1. Processing provider registered --------------------------------------
print("\n--- 1. Processing algorithms registered ---")
try:
    from qgis.core import QgsApplication

    _reg = QgsApplication.processingRegistry()
    for _aid in (
        "crsmart:recommendtransform",
        "crsmart:reprojectlayer",
        "crsmart:epochtransform",
        "crsmart:fitcalibration",
        "crsmart:repairvertical",
    ):
        _check(f"algorithm registered: {_aid}", _reg.algorithmById(_aid) is not None)
except Exception as exc:
    _check("processing registry reachable", False, repr(exc))


# --- 2. Calibration (deterministic, known answer) ---------------------------
print("\n--- 2. Local site calibration (Helmert) ---")
if _core_ok:
    try:
        local = [(r[0], r[1]) for r in _CLEAN]
        target = [(r[2], r[3]) for r in _CLEAN]
        res = calibration.fit_helmert_2d(local, target)
        p = res.params
        _check(
            "scale near unity (|ppm| < 50)",
            abs(p.get("scale_ppm", 1e9)) < 50.0,
            f"{p.get('scale_ppm'):.3f} ppm",
        )
        _check(
            "rotation ~ 0.35 deg",
            _approx(p.get("rotation_deg"), 0.35, 0.02),
            f"{p.get('rotation_deg'):.4f} deg",
        )
        _check("tx ~ 12000", _approx(p.get("tx"), 12000.0, 0.5), f"{p.get('tx'):.3f}")
        _check("ty ~ -8000", _approx(p.get("ty"), -8000.0, 0.5), f"{p.get('ty'):.3f}")
        _check("RMSE < 0.1 m (clean)", res.rmse < 0.1, f"{res.rmse:.4f} m")
        _check("0 outliers (clean)", len(res.outliers) == 0, str(res.outliers))

        # Emitted pipeline must round-trip exactly through PROJ.
        from pyproj import Transformer

        t = Transformer.from_pipeline(res.pipeline)
        X, Y = t.transform(100.0, 200.0)
        _check(
            "pipeline round-trip matches row 1",
            _approx(X, 12098.761, 0.1) and _approx(Y, -7799.375, 0.1),
            f"({X:.3f}, {Y:.3f})",
        )

        # Outlier set: index 4 must be flagged.
        local_out = [(r[0], r[1]) for r in _OUTLIER]
        target_out = [(r[2], r[3]) for r in _OUTLIER]
        res2 = calibration.fit_helmert_2d(local_out, target_out)
        _check(
            "outlier flagged at index 4",
            4 in res2.outliers,
            f"outliers={res2.outliers}",
        )
    except Exception as exc:
        _check("calibration block ran", False, repr(exc))


# --- 3. Recommend transformation (Adindan -> WGS 84) ------------------------
print("\n--- 3. Recommend transformation ---")
if _core_ok:
    try:
        r = rec.enumerate_candidates(4201, 4326, allow_ballpark=True)
        _check(
            "candidates found (EPSG:4201->4326)",
            len(r.candidates) > 0,
            f"{len(r.candidates)} candidates",
        )
        _check("has a recommendation", r.has_recommendation)
        if r.recommended is not None:
            _check(
                "recommended op is NOT ballpark",
                not r.recommended.is_ballpark,
                f"acc={r.recommended.accuracy_m} m",
            )
        r2 = rec.enumerate_candidates(4201, 4326, allow_ballpark=False)
        _check("still recommends with ballpark disallowed", r2.has_recommendation)
    except Exception as exc:
        _check("recommender block ran", False, repr(exc))


# --- 4. Epoch-aware transform (the refusal is the test) ---------------------
print("\n--- 4. Epoch awareness (ITRF2014 -> ITRF2008) ---")
if _core_ok:
    try:
        _check("ITRF2014 (EPSG:7912) is dynamic", epoch.is_dynamic(7912) is True)
        _check("WGS 84 (EPSG:4326) is NOT dynamic", epoch.is_dynamic(4326) is False)
        info = epoch.analyze_epoch(7912, 7911)
        _check("epoch required when unset", info.required is True, info.reason)
        refused = False
        try:
            epoch.require_epoch_or_raise(7912, 7911)
        except EpochRequiredError:
            refused = True
        _check("refuses to run without epoch", refused)
        info2 = epoch.analyze_epoch(
            7912, 7911, source_epoch=2010.0, target_epoch=2010.0
        )
        _check("epoch satisfied when supplied", info2.required is False)
    except Exception as exc:
        _check("epoch block ran", False, repr(exc))


# --- 5. Vertical CRS repair -------------------------------------------------
print("\n--- 5. Vertical CRS repair ---")
if _core_ok:
    try:
        _check(
            "plain 2D CRS has no vertical",
            vertical.detect_vertical(4326).has_vertical is False,
        )
        comp = vertical.assemble_compound(4326, 5773)  # WGS84 + EGM96 height
        wkt = comp.to_wkt()
        _check("assembled a COMPOUNDCRS", "COMPOUND" in wkt.upper())
        _check(
            "compound reports a vertical component",
            vertical.detect_vertical(comp).has_vertical is True,
        )
    except Exception as exc:
        _check("vertical block ran", False, repr(exc))


# --- 6. No-silent-network consent gate + scheme guard -----------------------
print("\n--- 6. Consent gate & scheme guard ---")
if _core_ok:
    try:
        before = grids.is_network_enabled()
        g = GridInfo(
            short_name="x.tif",
            full_name="x",
            package_name=None,
            url="https://cdn.proj.org/x.tif",
            direct_download=True,
            open_license=True,
            available=False,
        )
        blocked = False
        try:
            grids.download_grids([g], consent=False)
        except ConsentRequiredError:
            blocked = True
        _check("download without consent is refused", blocked)
        _check(
            "network NOT enabled as a side effect", grids.is_network_enabled() == before
        )

        # v0.1.1 security fix: a non-HTTP(S) URL must be refused, never opened.
        gf = GridInfo(
            short_name="y.tif",
            full_name="y",
            package_name=None,
            url="file:///etc/passwd",
            direct_download=True,
            open_license=True,
            available=False,
        )
        report = grids.download_grids([gf], consent=True)
        err = (report.failed[0].error or "") if report.failed else ""
        _check(
            "file:// scheme refused (not opened)",
            (not report.all_ok) and "scheme" in err,
            err,
        )
    except Exception as exc:
        _check("grids block ran", False, repr(exc))


# --- Summary ----------------------------------------------------------------
_passed = sum(1 for _, ok in _results if ok)
_total = len(_results)
print("\n" + "=" * 52)
print(f"CRSmart smoke test: {_passed}/{_total} checks passed")
_failed = [name for name, ok in _results if not ok]
if _failed:
    print("FAILED:")
    for _name in _failed:
        print("  -", _name)
print("=" * 52)

crsmart_smoketest_ok = _passed == _total and _total > 0
print("crsmart_smoketest_ok =", crsmart_smoketest_ok)
