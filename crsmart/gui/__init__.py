# -*- coding: utf-8 -*-
"""GUI layer: a dockable panel built on native QGIS widgets.

No geodetic / business logic lives here. The GUI only collects input, calls the
``crsmart.core`` engine (or the Processing algorithms), and renders results and
warnings via ``iface.messageBar()``.
"""
from __future__ import annotations
