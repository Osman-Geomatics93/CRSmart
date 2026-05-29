# -*- coding: utf-8 -*-
"""Shared pytest configuration.

``pytest-qgis`` provides the ``qgis_app``, ``qgis_iface`` and related fixtures
automatically once installed; we only need to make the ``crsmart`` package
importable from the repository root.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
