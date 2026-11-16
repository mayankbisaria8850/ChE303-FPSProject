"""Design-basis constants, copied from the Aspen Plus report (FPS_project_aspen_report.pdf).

Every name carries its unit. Sizes are in mm unless the name says ``_um``.
Nothing here is a simulation *result*; these are the *inputs* that were typed into Aspen.
"""
import numpy as np

# ---------------------------------------------------------------------------
# Unit conversions
# ---------------------------------------------------------------------------
KG_PER_METRIC_TONNE = 1000.0
KG_PER_SHORT_TON = 907.18474          # 1 US short ton = 2000 lb (Bond's original basis)
UM_PER_MM = 1000.0

# ---------------------------------------------------------------------------
# Global PSD mesh (report Table 1) - 10 intervals, edges in mm
# ---------------------------------------------------------------------------
PSD_EDGES_MM = np.array([0.00, 0.05, 0.10, 0.25, 0.50, 1.00, 1.50, 2.00, 4.00, 6.00, 10.00])

# Mass fraction of solids in each interval (sums to 1)
RAW_POMACE_WFRAC = np.array([0.00, 0.00, 0.00, 0.00, 0.05, 0.07, 0.08, 0.35, 0.30, 0.15])
MILL_OUTLET_WFRAC = np.array([0.00, 0.10, 0.25, 0.35, 0.20, 0.10, 0.00, 0.00, 0.00, 0.00])

# ---------------------------------------------------------------------------
# Feed (POMACE) - report section 4.1
# ---------------------------------------------------------------------------
BASE_FEED_TOTAL_KG_PER_H = 1000.0
FEED_LIQUID_MASS_FRACTION = 0.80      # MIXED substream (water + glucose + citric acid)
FEED_SOLID_MASS_FRACTION = 0.20       # CIPSD substream (cellulose)
LIQUID_COMPOSITION_WFRAC = {"H2O": 0.90, "GLUCOSE": 0.0875, "CITRIC": 0.0125}

HOT_AIR_KG_PER_H = 1500.0
HOT_AIR_T_C = 90.0

# ---------------------------------------------------------------------------
# Block specifications - report Table 2
# ---------------------------------------------------------------------------
# MILL (Crusher, Bond's law). Aspen interprets Wi on Bond's original short-ton basis
# (verified: reproduces MILL_POWER to 9 significant figures, see calc/verify.py).
BOND_WORK_INDEX_KWH_PER_TON = 12.0
BOND_TON_BASIS = "short"
MILL_MECHANICAL_EFFICIENCY = 1.0

# SCREEN (Whiten selection function)
BASE_SCREEN_CUT_SIZE_MM = 1.0
WHITEN_ALPHA = 3.5                     # sharpness; Aspen default, back-identified from the CSV
SCREEN_LIQUID_TO_OVERSIZE_FRAC = 0.05  # 5 wt% of inlet liquid entrained with oversize

# CENTRIF (Cfuge)
CENTRIFUGE_CUT_SIZE_MM = 0.05          # 100 % retention of solids > 0.05 mm
CAKE_MOISTURE_WET_BASIS = 0.65         # kg liquid / kg wet cake

# DRYER - bone-dry product, all residual liquid leaves with EXHAUST (Aspen simplification)

# ---------------------------------------------------------------------------
# Valid operating range of the Aspen sensitivity study (Step 5 CSV)
# ---------------------------------------------------------------------------
FEED_RANGE_KG_PER_H = (500.0, 2000.0)
CUT_SIZE_RANGE_MM = (0.5, 1.5)
