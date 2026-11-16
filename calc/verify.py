"""Step 4 verification report.

Run from the project root:
    python -m calc.verify            # print hand calculations + verification tables, save figures
    python -m calc.verify --no-figs  # tables only

What it checks
1. Hand calculation of the mill (Bond) and screen (Whiten) at the Aspen base case.
2. Python model vs every Aspen case in data/aspen_results.csv (42 cases x 4 outputs).
3. Python model vs the Aspen base-case stream table (report Table 3, not in the CSV).
4. Interpolation of the CSV vs that held-out base case (PCHIP and linear).
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from . import constants as C
from .aspen_data import OUTPUT_COLUMNS, PROJECT_ROOT, AspenInterpolator, load_aspen_csv
from .mill import (bond_power_kw, kick_specific_energy_kwh_per_ton, mill_performance,
                   rittinger_specific_energy_kwh_per_ton)
from .process import plant_balance
from .psd import cumulative_passing
from .screen import screen_split

FIG_DIR = PROJECT_ROOT / "docs" / "figures"
MODEL_KEY = {  # Aspen CSV column -> PlantResult field
    "mill_power_kw": "mill_power_kw",
    "oversize_solids_kg_per_h": "oversize_solids_kg_per_h",
    "juice_kg_per_h": "juice_kg_per_h",
    "fiber_kg_per_h": "fiber_product_kg_per_h",
}
# Aspen base case, report Table 3 (1000 kg/h, 1.0 mm) - not part of the 42-case CSV
TABLE3 = {"oversize_solids_kg_per_h": 32.52, "juice_kg_per_h": 448.96, "fiber_kg_per_h": 167.48,
          "mill_power_kw": 0.6146}


def hand_calc_mill() -> str:
    q_feed = cumulative_passing(C.PSD_EDGES_MM, C.RAW_POMACE_WFRAC)
    q_prod = cumulative_passing(C.PSD_EDGES_MM, C.MILL_OUTLET_WFRAC)
    m = mill_performance(C.BASE_FEED_TOTAL_KG_PER_H)
    t = 1 / math.sqrt(m.p80_um) - 1 / math.sqrt(m.f80_um)
    tons = m.solids_kg_per_h / C.KG_PER_SHORT_TON
    metric_kw = bond_power_kw(m.solids_kg_per_h, C.BOND_WORK_INDEX_KWH_PER_TON, m.f80_um, m.p80_um, "metric")
    lines = [
        "=" * 78, "UNIT A - HAMMER MILL (Bond's law), base case 1000 kg/h wet pomace", "=" * 78,
        "Governing equation: W = 10 Wi (1/sqrt(P80) - 1/sqrt(F80)),  P = W * m_solids",
        f"Step 1  F80 from raw PSD: Q(4 mm) = {q_feed[8]:.2f}, Q(6 mm) = {q_feed[9]:.2f}",
        f"        F80 = 4 + (0.80 - {q_feed[8]:.2f})/({q_feed[9]:.2f} - {q_feed[8]:.2f}) x 2 = {m.f80_um/1000:.4f} mm"
        f" = {m.f80_um:.1f} um",
        f"Step 2  P80 from milled PSD: Q(0.5 mm) = {q_prod[4]:.2f}, Q(1.0 mm) = {q_prod[5]:.2f}",
        f"        P80 = 0.5 + (0.80 - {q_prod[4]:.2f})/({q_prod[5]:.2f} - {q_prod[4]:.2f}) x 0.5 = {m.p80_um/1000:.4f} mm"
        f" = {m.p80_um:.1f} um",
        f"Step 3  1/sqrt(P80) - 1/sqrt(F80) = {1/math.sqrt(m.p80_um):.6f} - {1/math.sqrt(m.f80_um):.6f} = {t:.6f}",
        f"        W = 10 x {C.BOND_WORK_INDEX_KWH_PER_TON:g} x {t:.6f} = {m.specific_energy_kwh_per_ton_solids:.4f}"
        " kWh/short ton",
        f"Step 4  m_solids = 0.20 x 1000 = {m.solids_kg_per_h:.0f} kg/h = {m.solids_kg_per_h:.0f}/907.185"
        f" = {tons:.5f} short ton/h",
        f"        P = {m.specific_energy_kwh_per_ton_solids:.4f} x {tons:.5f} = {m.power_kw:.6f} kW",
        "        Aspen MILL_POWER = 0.614576843 kW  ->  difference "
        f"{100*(m.power_kw/0.614576843-1):+.2e} %",
        f"        (metric-tonne basis would give {metric_kw:.4f} kW, {100*(metric_kw/m.power_kw-1):.1f} %)",
        f"Reduction ratio F80/P80 = {m.reduction_ratio:.2f};  "
        f"specific energy = {m.energy_kwh_per_tonne_wet_feed:.4f} kWh per tonne wet feed",
        "Comparison of classical laws for the same F80 -> P80 (constants matched at 1000 -> 100 um):",
        f"        Bond {m.specific_energy_kwh_per_ton_solids:.3f} | "
        f"Kick {kick_specific_energy_kwh_per_ton(12, m.f80_um, m.p80_um):.3f} | "
        f"Rittinger {rittinger_specific_energy_kwh_per_ton(12, m.f80_um, m.p80_um):.3f}  kWh/ton",
    ]
    return "\n".join(lines)


def hand_calc_screen() -> tuple[str, pd.DataFrame]:
    res = screen_split(200.0, C.BASE_SCREEN_CUT_SIZE_MM)
    t = res.table[res.table.w_feed > 0][["lower_mm", "upper_mm", "d_mid_mm", "x_d_over_d50", "w_feed",
                                         "E_to_oversize", "w_times_E", "oversize_kg_per_h"]]
    lines = [
        "", "=" * 78, "UNIT B - VIBRATING SCREEN (Whiten), base case cut size 1.0 mm, alpha = 3.5", "=" * 78,
        "Governing equation: E(x) = (exp(a x) - 1)/(exp(a x) + exp(a) - 2),  x = d/d50",
        "Oversize solids = m_solids * sum(w_i E_i),  d_i = interval midpoint",
        t.to_string(index=False, float_format=lambda v: f"{v:.5f}"),
        f"sum(w E) = {res.oversize_fraction:.5f}  ->  oversize = 200 x {res.oversize_fraction:.5f} = "
        f"{res.oversize_solids_kg_per_h:.2f} kg/h (Aspen 32.52),  undersize = {res.undersize_solids_kg_per_h:.2f}"
        " kg/h (Aspen 167.48)",
    ]
    return "\n".join(lines), t


def compare_with_csv(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, a in df.iterrows():
        r = plant_balance(a.feed_total_kg_per_h, a.cut_size_mm).as_dict()
        row = {"case": int(a.case), "feed_kg_per_h": a.feed_total_kg_per_h, "cut_mm": a.cut_size_mm}
        for col in OUTPUT_COLUMNS:
            row[f"{col}_aspen"] = a[col]
            row[f"{col}_python"] = r[MODEL_KEY[col]]
            row[f"{col}_rel_err"] = r[MODEL_KEY[col]] / a[col] - 1
        rows.append(row)
    return pd.DataFrame(rows)


def holdout_table(df: pd.DataFrame) -> pd.DataFrame:
    py = plant_balance(1000, 1.0).as_dict()
    out = []
    for col, truth in TABLE3.items():
        rec = {"output": col, "aspen_table3": truth, "python_model": py[MODEL_KEY[col]]}
        for m in ("pchip", "linear"):
            rec[f"{m}_interp"] = AspenInterpolator(df, m)(1000, 1.0)[col]
        for k in ("python_model", "pchip_interp", "linear_interp"):
            rec[f"{k}_err_pct"] = 100 * (rec[k] / truth - 1)
        out.append(rec)
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Figures (matplotlib, static PNGs for the report and slides)
# ---------------------------------------------------------------------------
SERIES = {"fiber": "#2a78d6", "juice": "#eb6834", "oversize": "#1baf7a"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def _style(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")
    ax.set_xlabel(xlabel, color=INK2)
    ax.set_ylabel(ylabel, color=INK2)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2)
    ax.set_facecolor(SURFACE)


def make_figures(df: pd.DataFrame, comp: pd.DataFrame) -> list[Path]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    saved = []

    # 1. Mill power vs feed: Aspen points on Bond's line
    fig, ax = plt.subplots(figsize=(6.4, 4.0), facecolor=SURFACE)
    feeds = np.linspace(*C.FEED_RANGE_KG_PER_H, 100)
    ax.plot(feeds, [mill_performance(f).power_kw for f in feeds], color=SERIES["fiber"], lw=2,
            label="Python - Bond, short-ton basis")
    ax.plot(feeds, [mill_performance(f, ton_basis="metric").power_kw for f in feeds], color=SERIES["juice"],
            lw=2, ls="--", label="Python - Bond, metric-tonne basis")
    pw = df.groupby("feed_total_kg_per_h")["mill_power_kw"].first()
    ax.scatter(pw.index, pw.values, s=64, facecolor=SURFACE, edgecolor=INK, lw=1.5, zorder=3,
               label="Aspen MILL_POWER (CSV)")
    _style(ax, "Hammer-mill power vs feed rate", "Total pomace feed (kg/h)", "Mill shaft power (kW)")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    saved.append(FIG_DIR / "mill_power_vs_feed.png")
    fig.savefig(saved[-1], dpi=160)
    plt.close(fig)

    # 2. Whiten partition curves over the milled PSD
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6.4, 6.0), sharex=True, facecolor=SURFACE,
                                   gridspec_kw={"height_ratios": [1, 1.4]})
    edges, w = C.PSD_EDGES_MM[:7], C.MILL_OUTLET_WFRAC[:6]
    ax1.bar(edges[:-1], w, width=np.diff(edges), align="edge", color=SERIES["fiber"], edgecolor=SURFACE, lw=2)
    _style(ax1, "Milled solids PSD (screen feed)", "", "Mass fraction in interval (-)")
    d = np.linspace(0.001, 1.6, 300)
    from .screen import whiten_partition
    for cut, color in zip((0.5, 1.0, 1.5), (SERIES["juice"], SERIES["fiber"], SERIES["oversize"])):
        ax2.plot(d, whiten_partition(d, cut), color=color, lw=2, label=f"d50 = {cut} mm")
    ax2.axhline(0.5, color=INK2, lw=0.8, ls=":")
    _style(ax2, "Whiten partition curve, alpha = 3.5", "Particle size d (mm)", "Fraction to oversize E(d) (-)")
    ax2.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    saved.append(FIG_DIR / "screen_partition_curve.png")
    fig.savefig(saved[-1], dpi=160)
    plt.close(fig)

    # 3. Parity: Python model vs Aspen, one panel per output
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 6.4), facecolor=SURFACE)
    for ax, col in zip(axes.flat, OUTPUT_COLUMNS):
        a, p = comp[f"{col}_aspen"], comp[f"{col}_python"]
        lo, hi = 0.95 * a.min(), 1.05 * a.max()
        ax.plot([lo, hi], [lo, hi], color=INK2, lw=1, ls="--")
        ax.scatter(a, p, s=40, color=SERIES["fiber"], edgecolor=SURFACE, lw=1, zorder=3)
        err = comp[f"{col}_rel_err"].abs().max()
        _style(ax, col.replace("_kg_per_h", " (kg/h)").replace("_kw", " (kW)"), "Aspen", "Python")
        ax.text(0.04, 0.92, f"max |rel. err| = {err:.1e}", transform=ax.transAxes, fontsize=8, color=INK2)
    fig.suptitle("Python model vs all 42 Aspen cases", x=0.02, ha="left", fontweight="bold", color=INK)
    fig.tight_layout()
    saved.append(FIG_DIR / "parity_python_vs_aspen.png")
    fig.savefig(saved[-1], dpi=160)
    plt.close(fig)

    # 4. Products vs cut size at nominal feed: Aspen points, PCHIP curve, held-out base case
    fig, ax = plt.subplots(figsize=(6.4, 4.2), facecolor=SURFACE)
    it = AspenInterpolator(df, "pchip")
    cuts = np.linspace(*C.CUT_SIZE_RANGE_MM, 101)
    curve = it.curve_vs_cut(1000, cuts)
    d1000 = df[df.feed_total_kg_per_h == 1000]
    for col, key, name in (("juice_kg_per_h", "juice", "Clarified juice"),
                           ("fiber_kg_per_h", "fiber", "Dry fiber"),
                           ("oversize_solids_kg_per_h", "oversize", "Oversize solids")):
        ax.plot(cuts, curve[col], color=SERIES[key], lw=2, label=f"{name} - PCHIP of CSV")
        ax.scatter(d1000.cut_size_mm, d1000[col], s=56, facecolor=SURFACE, edgecolor=SERIES[key], lw=2, zorder=3)
        ax.scatter([1.0], [TABLE3[col]], marker="*", s=160, color=INK, zorder=4)
    ax.scatter([], [], s=56, facecolor=SURFACE, edgecolor=INK2, lw=2, label="Aspen CSV cases")
    ax.scatter([], [], marker="*", s=120, color=INK, label="Aspen base case (held out)")
    _style(ax, "Product split vs screen cut size (1000 kg/h feed)", "Screen cut size d50 (mm)", "Flow (kg/h)")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="center right")
    fig.tight_layout()
    saved.append(FIG_DIR / "products_vs_cut_size.png")
    fig.savefig(saved[-1], dpi=160)
    plt.close(fig)
    return saved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-figs", action="store_true", help="skip writing PNG figures")
    args = ap.parse_args(argv)
    pd.set_option("display.width", 160)

    df = load_aspen_csv()
    print(hand_calc_mill())
    text, _ = hand_calc_screen()
    print(text)

    comp = compare_with_csv(df)
    print("\n" + "=" * 78 + "\nPYTHON MODEL vs ASPEN CSV (42 cases)\n" + "=" * 78)
    summary = pd.DataFrame({col: {"max |rel err|": comp[f"{col}_rel_err"].abs().max(),
                                  "mean |rel err|": comp[f"{col}_rel_err"].abs().mean()}
                            for col in OUTPUT_COLUMNS}).T
    print(summary.to_string(float_format=lambda v: f"{v:.2e}"))
    show = comp[comp.feed_kg_per_h == 1000][["case", "cut_mm"] + [f"{c}_{s}" for c in ("fiber_kg_per_h",)
                                                                  for s in ("aspen", "python")]]
    print("\nSample (1000 kg/h):\n" + show.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    print("\n" + "=" * 78 + "\nHELD-OUT CHECK: Aspen base case 1000 kg/h, 1.0 mm (report Table 3, not in CSV)\n"
          + "=" * 78)
    ho = holdout_table(df)
    print(ho.to_string(index=False, float_format=lambda v: f"{v:.4f}"))

    worst = summary["max |rel err|"].max()
    print(f"\nRESULT: max relative error Python vs Aspen = {worst:.2e} -> "
          f"{'PASS' if worst < 1e-6 else 'FAIL'} (tolerance 1e-6)")

    if not args.no_figs:
        for p in make_figures(df, comp):
            print(f"figure saved: {p.relative_to(PROJECT_ROOT)}")
    return 0 if worst < 1e-6 else 1


if __name__ == "__main__":
    raise SystemExit(main())
