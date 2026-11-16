"""Vibrating screen (Aspen block SCREEN): Whiten partition (efficiency) curve.

Governing equation - Whiten selection function
----------------------------------------------
    E(d) = (exp(alpha * x) - 1) / (exp(alpha * x) + exp(alpha) - 2),     x = d / d50

    E      fraction of particles of size d that report to the OVERSIZE (coarse) stream, -
    d      particle size, mm (representative size of a PSD interval = arithmetic midpoint)
    d50    cut size (screen aperture setting in Aspen), mm - size with a 50 % chance of oversize
    alpha  sharpness of separation, -  (large alpha -> ideal sieve; Aspen default 3.5)

Screen performance for a feed PSD with mass fractions w_i at sizes d_i:
    oversize solids   = m_solids * sum_i w_i * E(d_i)
    undersize solids  = m_solids - oversize solids
    fine-fiber recovery to undersize = undersize solids / m_solids

Properties used as checks: E(d50) = 0.5 exactly; E -> 0 as d -> 0; E increases with d.

Assumptions: steady state; no particle breakage on the deck; no bypass/fish-hook term;
partition depends on size only (not on shape or moisture); liquid split handled separately
(fixed 5 wt% of inlet liquid entrained to oversize, as specified in Aspen).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import constants as C
from .psd import _check, interval_midpoints_mm


def whiten_partition(d_mm, d50_mm: float, alpha: float = C.WHITEN_ALPHA):
    """Fraction of particles of size ``d_mm`` going to oversize, [-]. Works on scalars or arrays."""
    if d50_mm <= 0:
        raise ValueError("Cut size d50 must be positive")
    if alpha <= 0:
        raise ValueError("Sharpness alpha must be positive")
    x = np.asarray(d_mm, dtype=float) / d50_mm
    if np.any(x < 0):
        raise ValueError("Particle size cannot be negative")
    # Algebraically identical form that stays finite for x -> 0 and x -> infinity:
    #   E = (e^{ax} - 1) / ((e^{ax} - 1) + (e^a - 1)) = 1 / (1 + (e^a - 1) / (e^{ax} - 1))
    with np.errstate(over="ignore", divide="ignore"):
        e = 1.0 / (1.0 + np.expm1(alpha) / np.expm1(alpha * x))
    return float(e) if np.ndim(e) == 0 else e


@dataclass(frozen=True)
class ScreenResult:
    cut_size_mm: float
    alpha: float
    solids_in_kg_per_h: float
    oversize_solids_kg_per_h: float
    undersize_solids_kg_per_h: float
    oversize_fraction: float
    undersize_recovery: float
    table: pd.DataFrame          # per-interval hand-calculation table


def screen_split(solids_kg_per_h: float, cut_size_mm: float, alpha: float = C.WHITEN_ALPHA,
                 edges_mm=C.PSD_EDGES_MM, wfrac=C.MILL_OUTLET_WFRAC) -> ScreenResult:
    """Split a solids stream with the given PSD over a screen of cut size ``cut_size_mm``."""
    if solids_kg_per_h < 0:
        raise ValueError("Solids flow cannot be negative")
    edges_mm, wfrac = _check(edges_mm, wfrac)
    d_mid = interval_midpoints_mm(edges_mm)
    e = whiten_partition(d_mid, cut_size_mm, alpha)
    contrib = wfrac * e
    frac_over = float(contrib.sum())
    over = solids_kg_per_h * frac_over
    table = pd.DataFrame({
        "lower_mm": edges_mm[:-1],
        "upper_mm": edges_mm[1:],
        "d_mid_mm": d_mid,
        "x_d_over_d50": d_mid / cut_size_mm,
        "w_feed": wfrac,
        "E_to_oversize": e,
        "w_times_E": contrib,
        "oversize_kg_per_h": solids_kg_per_h * contrib,
        "undersize_kg_per_h": solids_kg_per_h * (wfrac - contrib),
    })
    return ScreenResult(cut_size_mm, alpha, solids_kg_per_h, over, solids_kg_per_h - over,
                        frac_over, 1.0 - frac_over, table)
