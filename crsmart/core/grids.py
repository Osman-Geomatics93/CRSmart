"""PROJ grid availability and *consented* CDN download (pure Python).

Hard rule (see CLAUDE.md): no module import or engine call may enable the PROJ
network as a side effect. A download proceeds ONLY when the caller passes
``consent=True``; the network flag is toggled on for the duration of the fetch
and restored afterwards.
"""

from __future__ import annotations

import os
import shutil
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass

from pyproj import network
from pyproj.datadir import get_user_data_dir

from .errors import ConsentRequiredError
from .models import GridInfo

CDN_BASE = "https://cdn.proj.org"


@dataclass(frozen=True)
class GridDownload:
    """Outcome of a single grid download attempt."""

    short_name: str
    ok: bool
    path: str | None
    error: str | None


@dataclass(frozen=True)
class DownloadReport:
    """Aggregate result of :func:`download_grids`."""

    results: tuple[GridDownload, ...]

    @property
    def all_ok(self) -> bool:
        return all(r.ok for r in self.results)

    @property
    def succeeded(self) -> tuple[GridDownload, ...]:
        return tuple(r for r in self.results if r.ok)

    @property
    def failed(self) -> tuple[GridDownload, ...]:
        return tuple(r for r in self.results if not r.ok)


def is_network_enabled() -> bool:
    """Whether PROJ network access is currently enabled."""
    return bool(network.is_network_enabled())


def select_missing(grids: Iterable[GridInfo]) -> tuple[GridInfo, ...]:
    """Filter to grids that are not present locally."""
    return tuple(g for g in grids if not g.available)


def _grid_url(grid: GridInfo) -> str | None:
    if grid.url:
        return grid.url
    if grid.short_name:
        return f"{CDN_BASE}/{grid.short_name}"
    return None


def _download_one(grid: GridInfo, dest_dir: str) -> GridDownload:
    url = _grid_url(grid)
    if not url:
        return GridDownload(grid.short_name, False, None, "no download URL")
    if not grid.open_license:
        return GridDownload(
            grid.short_name, False, None, "grid is not under an open license"
        )
    target = os.path.join(dest_dir, grid.short_name)
    try:
        os.makedirs(dest_dir, exist_ok=True)
        with urllib.request.urlopen(url) as response:
            if response.status != 200:
                return GridDownload(
                    grid.short_name, False, None, f"HTTP {response.status}"
                )
            tmp = target + ".part"
            with open(tmp, "wb") as fh:
                shutil.copyfileobj(response, fh)
        os.replace(tmp, target)
    except Exception as exc:
        return GridDownload(grid.short_name, False, None, str(exc))
    return GridDownload(grid.short_name, True, target, None)


def download_grids(
    grids: Iterable[GridInfo],
    *,
    consent: bool,
    dest_dir: str | None = None,
) -> DownloadReport:
    """Download the given grids from the PROJ CDN -- only with explicit consent.

    :param grids: grids to fetch (already-present ones are skipped).
    :param consent: MUST be ``True``; otherwise :class:`ConsentRequiredError` is
        raised and no network access happens.
    :param dest_dir: where to write grids; defaults to PROJ's user data dir.
    :raises ConsentRequiredError: if ``consent`` is not ``True``.
    """
    if consent is not True:
        raise ConsentRequiredError(
            "Grid download requires explicit consent (consent=True). "
            "No network access was attempted."
        )

    to_fetch = select_missing(grids)
    if not to_fetch:
        return DownloadReport(results=())

    destination = dest_dir or get_user_data_dir(True)
    previous = network.is_network_enabled()
    network.set_network_enabled(True)
    try:
        results: list[GridDownload] = [_download_one(g, destination) for g in to_fetch]
    finally:
        network.set_network_enabled(previous)
    return DownloadReport(results=tuple(results))
