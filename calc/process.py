"""Whole-flowsheet Python model: POMACE -> MILL -> SCREEN -> CENTRIF -> DRYER.

This is an independent re-implementation of the Aspen flowsheet using the same
block specifications (report Table 2). It lets us check the exported Aspen CSV and
evaluate any operating point without Aspen.

Mass balances (all kg/h)
------------------------
    liquid_in  = x_L * F,            solids_in = (1 - x_L) * F
    MILL       power from Bond's law on solids_in; outlet PSD fixed (user-specified)
    SCREEN     oversize_solids = solids_in * sum(w_i E_i)       (Whiten, calc.screen)
               oversize_liquid = f_ent * liquid_in               (5 wt% entrainment)
    CENTRIF    every slurry particle is > 0.05 mm  -> all slurry solids go to the cake
               cake_liquid = cake_solids * M / (1 - M)           (M = 0.65 wet basis)
               juice       = slurry_liquid - cake_liquid
    DRYER      product = cake_solids (bone dry); water load = cake_liquid
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from . import constants as C
from .mill import mill_performance
from .screen import screen_split


@dataclass(frozen=True)
class PlantResult:
    feed_total_kg_per_h: float
    cut_size_mm: float
    feed_liquid_kg_per_h: float
    feed_solids_kg_per_h: float
    mill_power_kw: float
    oversize_solids_kg_per_h: float
    oversize_liquid_kg_per_h: float
    oversize_total_kg_per_h: float
    slurry_solids_kg_per_h: float
    slurry_liquid_kg_per_h: float
    slurry_total_kg_per_h: float
    juice_kg_per_h: float
    wet_cake_kg_per_h: float
    cake_liquid_kg_per_h: float
    fiber_product_kg_per_h: float
    dryer_liquid_removed_kg_per_h: float
    fiber_recovery_pct: float
    juice_recovery_pct: float
    specific_energy_kwh_per_tonne_wet_feed: float

    def as_dict(self) -> dict:
        return asdict(self)


def plant_balance(feed_total_kg_per_h: float,
                  cut_size_mm: float,
                  wi_kwh_per_ton: float = C.BOND_WORK_INDEX_KWH_PER_TON,
                  alpha: float = C.WHITEN_ALPHA,
                  liquid_fraction: float = C.FEED_LIQUID_MASS_FRACTION,
                  liquid_entrainment: float = C.SCREEN_LIQUID_TO_OVERSIZE_FRAC,
                  cake_moisture: float = C.CAKE_MOISTURE_WET_BASIS,
                  ton_basis: str = C.BOND_TON_BASIS) -> PlantResult:
    """Steady-state stream table for a given total pomace feed (kg/h) and screen cut size (mm)."""
    if feed_total_kg_per_h <= 0:
        raise ValueError("Feed rate must be positive")
    if not 0 < liquid_fraction < 1:
        raise ValueError("Liquid fraction must be between 0 and 1")
    if not 0 <= liquid_entrainment < 1:
        raise ValueError("Liquid entrainment must be in [0, 1)")
    if not 0 <= cake_moisture < 1:
        raise ValueError("Cake moisture must be in [0, 1)")

    liquid_in = liquid_fraction * feed_total_kg_per_h
    solids_in = feed_total_kg_per_h - liquid_in

    mill = mill_performance(feed_total_kg_per_h, wi_kwh_per_ton, solid_fraction=1 - liquid_fraction,
                            ton_basis=ton_basis)
    scr = screen_split(solids_in, cut_size_mm, alpha)

    over_liq = liquid_entrainment * liquid_in
    slurry_liq = liquid_in - over_liq
    slurry_sol = scr.undersize_solids_kg_per_h

    cake_liq = slurry_sol * cake_moisture / (1 - cake_moisture)
    juice = slurry_liq - cake_liq
    if juice < 0:
        raise ValueError("Cake would need more liquid than the slurry carries - "
                         "reduce cake moisture or the solids fraction")

    return PlantResult(
        feed_total_kg_per_h=feed_total_kg_per_h,
        cut_size_mm=cut_size_mm,
        feed_liquid_kg_per_h=liquid_in,
        feed_solids_kg_per_h=solids_in,
        mill_power_kw=mill.power_kw,
        oversize_solids_kg_per_h=scr.oversize_solids_kg_per_h,
        oversize_liquid_kg_per_h=over_liq,
        oversize_total_kg_per_h=scr.oversize_solids_kg_per_h + over_liq,
        slurry_solids_kg_per_h=slurry_sol,
        slurry_liquid_kg_per_h=slurry_liq,
        slurry_total_kg_per_h=slurry_sol + slurry_liq,
        juice_kg_per_h=juice,
        wet_cake_kg_per_h=slurry_sol + cake_liq,
        cake_liquid_kg_per_h=cake_liq,
        fiber_product_kg_per_h=slurry_sol,
        dryer_liquid_removed_kg_per_h=cake_liq,
        fiber_recovery_pct=100 * slurry_sol / solids_in,
        juice_recovery_pct=100 * juice / liquid_in,
        specific_energy_kwh_per_tonne_wet_feed=mill.energy_kwh_per_tonne_wet_feed,
    )
