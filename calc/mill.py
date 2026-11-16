"""Hammer mill (Aspen block MILL, Crusher model): comminution energy.

Governing equation - Bond's third law of comminution
----------------------------------------------------
    W = 10 * Wi * (1/sqrt(P80) - 1/sqrt(F80))        [kWh per ton of solids]
    P = W * m_solids / eta                            [kW]

    W     specific grinding energy, kWh/ton
    Wi    Bond work index, kWh/ton (energy to grind from infinite size to 80 % < 100 um)
    F80   size through which 80 % of the FEED passes, um
    P80   size through which 80 % of the PRODUCT passes, um
    m     solids mass flow, ton/h  (Bond acts on the dry CIPSD solids only)
    eta   mechanical efficiency, -  (1.0 in Aspen)

The "ton" in Bond's original work index is the US short ton (907.18474 kg). Aspen Plus
uses that basis: with Wi = 12 it reproduces MILL_POWER = 0.614577 kW exactly, while a
metric-tonne basis would give 0.5575 kW. ``ton_basis`` lets the user choose.

Kick's and Rittinger's laws are included only as a comparison of the three classical
energy laws for the same size reduction, each calibrated to Wi at the 100 um reference.

Assumptions: steady state; Wi constant over the size range; outlet PSD fixed (Aspen
"user-specified outlet PSD"); liquid passes through the mill without absorbing energy.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import constants as C
from .psd import d_percent_passing

_TON_KG = {"short": C.KG_PER_SHORT_TON, "metric": C.KG_PER_METRIC_TONNE}


def _ton_kg(ton_basis: str) -> float:
    try:
        return _TON_KG[ton_basis]
    except KeyError:
        raise ValueError("ton_basis must be 'short' or 'metric'") from None


def _check_sizes(f80_um: float, p80_um: float) -> None:
    if f80_um <= 0 or p80_um <= 0:
        raise ValueError("F80 and P80 must be positive")
    if p80_um >= f80_um:
        raise ValueError("P80 must be smaller than F80 for size reduction")


def bond_specific_energy_kwh_per_ton(wi_kwh_per_ton: float, f80_um: float, p80_um: float) -> float:
    """Bond specific energy W, kWh per ton of solids (same ton as Wi)."""
    _check_sizes(f80_um, p80_um)
    if wi_kwh_per_ton <= 0:
        raise ValueError("Work index must be positive")
    return 10.0 * wi_kwh_per_ton * (1.0 / np.sqrt(p80_um) - 1.0 / np.sqrt(f80_um))


def bond_power_kw(solids_kg_per_h: float, wi_kwh_per_ton: float, f80_um: float, p80_um: float,
                  ton_basis: str = C.BOND_TON_BASIS,
                  efficiency: float = C.MILL_MECHANICAL_EFFICIENCY) -> float:
    """Mill shaft power, kW, for a solids mass flow in kg/h."""
    if solids_kg_per_h < 0:
        raise ValueError("Solids flow cannot be negative")
    if not 0 < efficiency <= 1:
        raise ValueError("Efficiency must be in (0, 1]")
    w = bond_specific_energy_kwh_per_ton(wi_kwh_per_ton, f80_um, p80_um)
    tons_per_h = solids_kg_per_h / _ton_kg(ton_basis)
    return w * tons_per_h / efficiency


def kick_specific_energy_kwh_per_ton(wi_kwh_per_ton: float, f80_um: float, p80_um: float) -> float:
    """Kick's law, W = K_K ln(F80/P80), with K_K chosen so Kick = Bond for a 1000 -> 100 um reduction."""
    _check_sizes(f80_um, p80_um)
    k_k = 10.0 * wi_kwh_per_ton * (1 / np.sqrt(100.0) - 1 / np.sqrt(1000.0)) / np.log(10.0)
    return k_k * np.log(f80_um / p80_um)


def rittinger_specific_energy_kwh_per_ton(wi_kwh_per_ton: float, f80_um: float, p80_um: float) -> float:
    """Rittinger's law, W = K_R (1/P80 - 1/F80), with K_R chosen to match Bond at 1000->100 um."""
    _check_sizes(f80_um, p80_um)
    k_r = 10.0 * wi_kwh_per_ton * (1 / np.sqrt(100.0) - 1 / np.sqrt(1000.0)) / (1 / 100.0 - 1 / 1000.0)
    return k_r * (1.0 / p80_um - 1.0 / f80_um)


@dataclass(frozen=True)
class MillResult:
    feed_total_kg_per_h: float
    solids_kg_per_h: float
    f80_um: float
    p80_um: float
    reduction_ratio: float
    specific_energy_kwh_per_ton_solids: float
    power_kw: float
    energy_kwh_per_tonne_wet_feed: float
    ton_basis: str


def mill_performance(feed_total_kg_per_h: float,
                     wi_kwh_per_ton: float = C.BOND_WORK_INDEX_KWH_PER_TON,
                     solid_fraction: float = C.FEED_SOLID_MASS_FRACTION,
                     edges_mm=C.PSD_EDGES_MM,
                     feed_wfrac=C.RAW_POMACE_WFRAC,
                     product_wfrac=C.MILL_OUTLET_WFRAC,
                     ton_basis: str = C.BOND_TON_BASIS,
                     efficiency: float = C.MILL_MECHANICAL_EFFICIENCY) -> MillResult:
    """Full mill calculation from the feed rate and the feed/product PSDs."""
    f80_um = d_percent_passing(edges_mm, feed_wfrac, 0.80) * C.UM_PER_MM
    p80_um = d_percent_passing(edges_mm, product_wfrac, 0.80) * C.UM_PER_MM
    solids = feed_total_kg_per_h * solid_fraction
    w = float(bond_specific_energy_kwh_per_ton(wi_kwh_per_ton, f80_um, p80_um))
    power = float(bond_power_kw(solids, wi_kwh_per_ton, f80_um, p80_um, ton_basis, efficiency))
    per_tonne_wet = power / (feed_total_kg_per_h / C.KG_PER_METRIC_TONNE) if feed_total_kg_per_h > 0 else 0.0
    return MillResult(feed_total_kg_per_h, solids, f80_um, p80_um, f80_um / p80_um, w, power,
                      per_tonne_wet, ton_basis)
