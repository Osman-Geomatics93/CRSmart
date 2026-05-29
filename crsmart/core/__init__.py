# -*- coding: utf-8 -*-
"""CRSmart pure-Python engine.

CONTRACT: nothing in this subpackage may import ``qgis.PyQt``, ``qgis.gui`` or
rely on a QGIS ``iface``. Allowed third-party imports: ``pyproj``, ``numpy``, and
optionally ``qgis.core`` *only* behind an ``hasattr`` / try-import feature guard
with a pyproj fallback. This rule is enforced by ``tests/test_no_qt_in_core.py``.

Implemented in Phase 2.
"""
from __future__ import annotations
