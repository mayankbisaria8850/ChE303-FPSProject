"""Particle-size-distribution (PSD) helpers.

A PSD is described by interval edges (mm, length n+1) and the mass fraction of
solids in each interval (length n). The cumulative-passing curve is known at the
interval edges and interpolated *linearly* between them - exactly the hand
calculation, and the way Aspen reports F80 / P80 for this flowsheet.
"""
from __future__ import annotations

import numpy as np


def _check(edges_mm, wfrac) -> tuple[np.ndarray, np.ndarray]:
    edges_mm = np.asarray(edges_mm, dtype=float)
    wfrac = np.asarray(wfrac, dtype=float)
    if edges_mm.ndim != 1 or wfrac.ndim != 1 or len(edges_mm) != len(wfrac) + 1:
        raise ValueError("edges must have exactly one more entry than the weight fractions")
    if np.any(np.diff(edges_mm) <= 0):
        raise ValueError("PSD edges must be strictly increasing")
    if np.any(wfrac < 0) or not np.isclose(wfrac.sum(), 1.0, atol=1e-9):
        raise ValueError(f"weight fractions must be >= 0 and sum to 1 (sum = {wfrac.sum():.6f})")
    return edges_mm, wfrac


def cumulative_passing(edges_mm, wfrac) -> np.ndarray:
    """Cumulative mass fraction passing (finer than) each edge, [-]. Length n+1, starts at 0."""
    edges_mm, wfrac = _check(edges_mm, wfrac)
    return np.concatenate([[0.0], np.cumsum(wfrac)])


def d_percent_passing(edges_mm, wfrac, fraction_passing: float) -> float:
    """Size (mm) below which ``fraction_passing`` of the solids mass lies (0.80 -> d80).

    Find the first edge i whose cumulative passing reaches the target, then interpolate
    linearly between edge i-1 and edge i:
        d = e[i-1] + (f - Q[i-1]) / (Q[i] - Q[i-1]) * (e[i] - e[i-1])
    """
    if not 0.0 < fraction_passing < 1.0:
        raise ValueError("fraction_passing must be strictly between 0 and 1")
    edges_mm, wfrac = _check(edges_mm, wfrac)
    q = cumulative_passing(edges_mm, wfrac)
    i = int(np.argmax(q >= fraction_passing - 1e-12))
    frac_of_interval = (fraction_passing - q[i - 1]) / (q[i] - q[i - 1])
    return float(edges_mm[i - 1] + frac_of_interval * (edges_mm[i] - edges_mm[i - 1]))


def interval_midpoints_mm(edges_mm) -> np.ndarray:
    """Arithmetic-mean size of each interval, mm (the representative size Aspen's screen uses)."""
    edges_mm = np.asarray(edges_mm, dtype=float)
    return 0.5 * (edges_mm[:-1] + edges_mm[1:])
