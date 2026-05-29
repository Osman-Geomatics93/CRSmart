# -*- coding: utf-8 -*-
"""CRSmart — an uncertainty- and epoch-aware CRS / datum transformation assistant.

This package is a QGIS plugin. The QGIS plugin loader calls :func:`classFactory`
with the running ``QgisInterface`` to instantiate the plugin.

Architecture note: only ``crsmart.plugin`` and the ``crsmart.gui`` /
``crsmart.processing`` subpackages may import Qt or ``qgis.gui``. The
``crsmart.core`` subpackage is deliberately free of any Qt / iface dependency so
it can be unit-tested headlessly. See ``CLAUDE.md`` and ``DESIGN.md``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from qgis.gui import QgisInterface

    from .plugin import CRSmartPlugin


def classFactory(iface: "QgisInterface") -> "CRSmartPlugin":  # noqa: N802 (QGIS API name)
    """Load the CRSmart plugin class.

    :param iface: A QGIS interface instance handed to us by the plugin loader.
    :returns: An instance of the main plugin class.
    """
    from .plugin import CRSmartPlugin

    return CRSmartPlugin(iface)
