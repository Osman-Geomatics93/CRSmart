# -*- coding: utf-8 -*-
"""Exception hierarchy for the CRSmart engine (pure Python, no Qt)."""
from __future__ import annotations


class CRSmartError(Exception):
    """Base class for all CRSmart engine errors."""


class EpochRequiredError(CRSmartError):
    """Raised when a dynamic-datum transform is attempted without a coordinate epoch.

    This is the engine-level enforcement behind the GUI's refusal to silently
    perform a time-dependent transform with an unknown epoch.
    """


class ConsentRequiredError(CRSmartError):
    """Raised when a PROJ grid download is attempted without explicit user consent.

    No module import or engine call may enable the PROJ network as a side effect;
    a download only proceeds when the caller passes ``consent=True``.
    """


class BallparkNotAllowedError(CRSmartError):
    """Raised when only a ballpark transform exists but ballpark was not allowed."""


class CalibrationError(CRSmartError):
    """Raised when a Helmert/affine fit cannot be computed (e.g. too few points)."""
