"""Load the Aspen Plus sensitivity export (Step 5 CSV) and interpolate between cases.

The raw export has multi-line quoted headers (e.g. "VARY 2\\nSCREEN\\n1\\nDECK-DAT\\nCUT-SIZE\\nMETER")
and a trailing empty column. ``load_aspen_csv`` turns it into a tidy table:

    case, status, feed_total_kg_per_h, feed_liquid_kg_per_h, cut_size_mm,
    mill_power_kw, oversize_solids_kg_per_h, juice_kg_per_h, fiber_kg_per_h

The 42 cases form a full 7 x 6 grid (feed 500-2000 kg/h, cut size 0.5-1.5 mm), so the
website uses a regular-grid interpolator. Default method is PCHIP (monotone piecewise
cubic) because the outputs are smooth, monotone and curved in cut size; along the feed
axis the Aspen outputs are exactly linear, which PCHIP reproduces exactly.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import RegularGridInterpolator

from . import constants as C

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = PROJECT_ROOT / "data" / "aspen_results.csv"

OUTPUT_COLUMNS = ["mill_power_kw", "oversize_solids_kg_per_h", "juice_kg_per_h", "fiber_kg_per_h"]
OUTPUT_LABELS = {
    "mill_power_kw": "Mill power (kW)",
    "oversize_solids_kg_per_h": "Oversize peel solids (kg/h)",
    "juice_kg_per_h": "Clarified juice (kg/h)",
    "fiber_kg_per_h": "Dry citrus fiber (kg/h)",
}

# (tidy name, keywords that must appear in the raw Aspen header) - checked so a re-export
# with re-ordered columns fails loudly instead of silently mislabelling data.
_EXPECTED = [
    ("case", ["ROW"]),
    ("status", ["STATUS"]),
    ("feed_total_kg_per_h", ["TOTAL FEED"]),
    ("feed_liquid_kg_per_h", ["POMACE", "KG/HR"]),
    ("cut_size_m", ["CUT-SIZE", "METER"]),
    ("mill_power_kw", ["MILL_POWER", "KW"]),
    ("oversize_solids_kg_per_h", ["OVERSIZE", "KG/HR"]),
    ("juice_kg_per_h", ["JUICE", "KG/HR"]),
    ("fiber_kg_per_h", ["FIBER", "KG/HR"]),
]


def _norm(header: str) -> str:
    return " ".join(str(header).upper().split())


def load_aspen_csv(path: str | Path = DEFAULT_CSV) -> pd.DataFrame:
    """Read the raw Aspen export and return the tidy, unit-labelled table (cut size in mm)."""
    raw = pd.read_csv(path)
    raw = raw.loc[:, [c for c in raw.columns if not str(c).startswith("Unnamed")]]
    if raw.shape[1] != len(_EXPECTED):
        raise ValueError(f"Expected {len(_EXPECTED)} data columns, found {raw.shape[1]}")
    names = []
    for header, (name, keys) in zip(raw.columns, _EXPECTED):
        h = _norm(header)
        if not all(k in h for k in keys):
            raise ValueError(f"Column '{h}' does not look like '{name}' (expected {keys})")
        names.append(name)
    df = raw.copy()
    df.columns = names
    df["status"] = df["status"].astype(str).str.strip()
    bad = df[df["status"] != "OK"]
    if len(bad):
        raise ValueError(f"Aspen cases not converged: {bad['case'].tolist()}")
    df["cut_size_mm"] = (df.pop("cut_size_m") * 1000.0).round(6)
    df["feed_total_kg_per_h"] = df["feed_total_kg_per_h"].astype(float)
    df = df[["case", "status", "feed_total_kg_per_h", "feed_liquid_kg_per_h", "cut_size_mm"] + OUTPUT_COLUMNS]
    return df.sort_values(["feed_total_kg_per_h", "cut_size_mm"]).reset_index(drop=True)


class AspenInterpolator:
    """Look-up / interpolation of precomputed Aspen results on the (feed, cut size) grid."""

    METHODS = ("pchip", "linear")

    def __init__(self, df: pd.DataFrame | None = None, method: str = "pchip"):
        if method not in self.METHODS:
            raise ValueError(f"method must be one of {self.METHODS}")
        self.df = load_aspen_csv() if df is None else df
        self.method = method
        self.feed_levels = np.sort(self.df["feed_total_kg_per_h"].unique())
        self.cut_levels = np.sort(self.df["cut_size_mm"].unique())
        nf, nc = len(self.feed_levels), len(self.cut_levels)
        if len(self.df) != nf * nc:
            raise ValueError("Aspen cases do not form a complete feed x cut-size grid")
        grid = self.df.set_index(["feed_total_kg_per_h", "cut_size_mm"]).sort_index()
        values = grid[OUTPUT_COLUMNS].to_numpy().reshape(nf, nc, len(OUTPUT_COLUMNS))
        self._interp = RegularGridInterpolator((self.feed_levels, self.cut_levels), values,
                                               method=method, bounds_error=True)

    # -- range --------------------------------------------------------------
    @property
    def feed_range(self) -> tuple[float, float]:
        return float(self.feed_levels[0]), float(self.feed_levels[-1])

    @property
    def cut_range(self) -> tuple[float, float]:
        return float(self.cut_levels[0]), float(self.cut_levels[-1])

    def in_range(self, feed_kg_per_h: float, cut_mm: float) -> bool:
        (f0, f1), (c0, c1) = self.feed_range, self.cut_range
        tol = 1e-9
        return f0 - tol <= feed_kg_per_h <= f1 + tol and c0 - tol <= cut_mm <= c1 + tol

    # -- lookup ---------------------------------------------------------------
    def __call__(self, feed_kg_per_h: float, cut_mm: float) -> dict:
        if not self.in_range(feed_kg_per_h, cut_mm):
            (f0, f1), (c0, c1) = self.feed_range, self.cut_range
            raise ValueError(f"Outside the simulated range: feed {f0:g}-{f1:g} kg/h, "
                             f"cut size {c0:g}-{c1:g} mm")
        f = float(np.clip(feed_kg_per_h, *self.feed_range))
        c = float(np.clip(cut_mm, *self.cut_range))
        row = self._interp([[f, c]])[0]
        return dict(zip(OUTPUT_COLUMNS, map(float, row)))

    def curve_vs_cut(self, feed_kg_per_h: float, cuts_mm) -> pd.DataFrame:
        cuts_mm = np.asarray(cuts_mm, dtype=float)
        pts = np.column_stack([np.full_like(cuts_mm, feed_kg_per_h), cuts_mm])
        out = pd.DataFrame(self._interp(pts), columns=OUTPUT_COLUMNS)
        out.insert(0, "cut_size_mm", cuts_mm)
        return out

    def surface(self, column: str, feeds_kg_per_h, cuts_mm) -> np.ndarray:
        """Vectorised values of one output on a feed x cut mesh, shape (len(feeds), len(cuts))."""
        f, c = np.meshgrid(np.asarray(feeds_kg_per_h, float), np.asarray(cuts_mm, float), indexing="ij")
        vals = self._interp(np.column_stack([f.ravel(), c.ravel()]))[:, OUTPUT_COLUMNS.index(column)]
        return vals.reshape(f.shape)

    def is_grid_point(self, feed_kg_per_h: float, cut_mm: float) -> bool:
        return bool(np.any(np.isclose(self.feed_levels, feed_kg_per_h)) and
                    np.any(np.isclose(self.cut_levels, cut_mm)))

    def nearest_case(self, feed_kg_per_h: float, cut_mm: float) -> pd.Series:
        """Closest simulated case, distance measured in fractions of each axis range."""
        (f0, f1), (c0, c1) = self.feed_range, self.cut_range
        d = (((self.df["feed_total_kg_per_h"] - feed_kg_per_h) / (f1 - f0)) ** 2 +
             ((self.df["cut_size_mm"] - cut_mm) / (c1 - c0)) ** 2)
        return self.df.loc[d.idxmin()]


def derived_metrics(feed_total_kg_per_h: float, outputs: dict,
                    liquid_fraction: float = C.FEED_LIQUID_MASS_FRACTION,
                    liquid_entrainment: float = C.SCREEN_LIQUID_TO_OVERSIZE_FRAC,
                    hot_air_kg_per_h: float = C.HOT_AIR_KG_PER_H) -> dict:
    """Every stream and KPI, closed by mass balance around the four Aspen outputs.

    Only the feed split (80/20) and the 5 wt% screen liquid entrainment from the Aspen
    input specs are used; the cake moisture is *recovered* from the balance as a check.
    """
    solids_in = (1 - liquid_fraction) * feed_total_kg_per_h
    liquid_in = liquid_fraction * feed_total_kg_per_h
    fiber, juice = outputs["fiber_kg_per_h"], outputs["juice_kg_per_h"]
    oversize_total = outputs["oversize_solids_kg_per_h"] + liquid_entrainment * liquid_in
    slurry = feed_total_kg_per_h - oversize_total
    wet_cake = slurry - juice
    cake_liquid = wet_cake - fiber
    return {
        "feed_solids_kg_per_h": solids_in,
        "feed_liquid_kg_per_h": liquid_in,
        "oversize_total_kg_per_h": oversize_total,
        "slurry_kg_per_h": slurry,
        "wet_cake_kg_per_h": wet_cake,
        "dryer_liquid_removed_kg_per_h": cake_liquid,
        "exhaust_kg_per_h": hot_air_kg_per_h + cake_liquid,
        "cake_moisture_pct": 100 * cake_liquid / wet_cake,
        "fiber_recovery_pct": 100 * fiber / solids_in,
        "juice_recovery_pct": 100 * juice / liquid_in,
        "specific_energy_kwh_per_tonne_wet_feed": outputs["mill_power_kw"] / (feed_total_kg_per_h / 1000),
        "solids_balance_error_kg_per_h": fiber + outputs["oversize_solids_kg_per_h"] - solids_in,
    }
