"""Plotly figure builders for the website (kept out of app.py so the page code stays readable).

Colour roles (validated categorical slots 1-3, fixed per entity on every chart):
fibre = blue, juice = orange, oversize = aqua. Magnitude (heatmap) = one-hue blue ramp.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from calc import constants as C
from calc.aspen_data import AspenInterpolator
from calc.mill import mill_performance
from calc.screen import screen_split, whiten_partition

FIBER, JUICE, OVERSIZE = "#2a78d6", "#eb6834", "#1baf7a"
NEUTRAL = "#8a8984"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

SERIES = [  # (column, label, colour)
    ("juice_kg_per_h", "Clarified juice", JUICE),
    ("fiber_kg_per_h", "Dry fibre product", FIBER),
    ("oversize_solids_kg_per_h", "Oversize peel solids", OVERSIZE),
]


def _layout(fig: go.Figure, title: str, x: str, y: str, height: int = 400) -> go.Figure:
    fig.update_layout(title=dict(text=title, x=0, xanchor="left"), height=height,
                      margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified",
                      legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="left", x=0))
    fig.update_xaxes(title_text=x, showgrid=False, zeroline=False)
    fig.update_yaxes(title_text=y, zeroline=False)
    return fig


def products_vs_cut(it: AspenInterpolator, feed: float, cut: float) -> go.Figure:
    cuts = np.linspace(*it.cut_range, 101)
    curve = it.curve_vs_cut(feed, cuts)
    on_grid_feed = bool(np.any(np.isclose(it.feed_levels, feed)))
    pts = it.df[np.isclose(it.df.feed_total_kg_per_h, feed)] if on_grid_feed else None
    now = it(feed, cut)
    fig = go.Figure()
    for col, name, color in SERIES:
        fig.add_trace(go.Scatter(x=cuts, y=curve[col], name=name, mode="lines",
                                 line=dict(color=color, width=2),
                                 hovertemplate="%{y:.1f} kg/h<extra>" + name + "</extra>"))
        if pts is not None:
            fig.add_trace(go.Scatter(x=pts.cut_size_mm, y=pts[col], mode="markers", showlegend=False,
                                     marker=dict(size=9, color="white", line=dict(color=color, width=2)),
                                     name=f"Aspen case - {name}", hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=[cut], y=[now[col]], mode="markers", showlegend=False, hoverinfo="skip",
                                 marker=dict(size=14, color=color, line=dict(color="white", width=2))))
    fig.add_vline(x=cut, line=dict(color=NEUTRAL, width=1, dash="dot"))
    sub = "open circles = Aspen cases" if on_grid_feed else "feed between simulated levels: curves interpolated"
    return _layout(fig, f"Product split vs screen cut size at {feed:.0f} kg/h ({sub})",
                   "Screen cut size d50 (mm)", "Flow (kg/h)")


def recovery_vs_cut(df: pd.DataFrame, cut: float, it: AspenInterpolator) -> go.Figure:
    d = df.assign(fiber_rec=100 * df.fiber_kg_per_h / (0.2 * df.feed_total_kg_per_h),
                  juice_rec=100 * df.juice_kg_per_h / (0.8 * df.feed_total_kg_per_h))
    cuts = np.linspace(*it.cut_range, 101)
    curve = it.curve_vs_cut(1000, cuts)
    fig = go.Figure()
    for col, curve_col, base, name, color in (
            ("fiber_rec", "fiber_kg_per_h", 200, "Fibre recovery to product", FIBER),
            ("juice_rec", "juice_kg_per_h", 800, "Juice recovery", JUICE)):
        fig.add_trace(go.Scatter(x=cuts, y=100 * curve[curve_col] / base, mode="lines", name=name,
                                 line=dict(color=color, width=2),
                                 hovertemplate="%{y:.1f} %<extra>" + name + "</extra>"))
        fig.add_trace(go.Scatter(x=d.cut_size_mm, y=d[col], mode="markers", showlegend=False, name=name,
                                 customdata=d[["case", "feed_total_kg_per_h"]],
                                 marker=dict(size=9, color="white", line=dict(color=color, width=2)),
                                 hovertemplate="case %{customdata[0]} - %{customdata[1]:.0f} kg/h: "
                                               "%{y:.2f} %<extra></extra>"))
    fig.add_vline(x=cut, line=dict(color=NEUTRAL, width=1, dash="dot"))
    fig.update_layout(hovermode="closest")
    return _layout(fig, "Recovery vs cut size (all 42 Aspen cases)",
                   "Screen cut size d50 (mm)", "Recovery (%)")


def fiber_heatmap(it: AspenInterpolator, feed: float, cut: float) -> go.Figure:
    feeds = np.linspace(*it.feed_range, 61)
    cuts = np.linspace(*it.cut_range, 51)
    z = it.surface("fiber_kg_per_h", feeds, cuts)
    scale = [[i / (len(BLUE_RAMP) - 1), c] for i, c in enumerate(BLUE_RAMP)]
    fig = go.Figure(go.Heatmap(x=cuts, y=feeds, z=z, colorscale=scale,
                               colorbar=dict(title="kg/h", thickness=12),
                               hovertemplate="cut %{x:.2f} mm<br>feed %{y:.0f} kg/h<br>"
                                             "fibre %{z:.1f} kg/h<extra></extra>"))
    fig.add_trace(go.Scatter(x=it.df.cut_size_mm, y=it.df.feed_total_kg_per_h, mode="markers",
                             marker=dict(size=5, color="white", line=dict(color="#0d366b", width=1)),
                             name="Aspen cases", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=[cut], y=[feed], mode="markers", name="Your operating point",
                             marker=dict(size=16, symbol="x", color=JUICE, line=dict(color="white", width=1)),
                             hoverinfo="skip"))
    fig.update_layout(hovermode="closest")
    return _layout(fig, "Dry fibre product (kg/h) over the whole operating window",
                   "Screen cut size d50 (mm)", "Total pomace feed (kg/h)", height=430)


def mill_power_vs_feed(df: pd.DataFrame, feed: float, wi: float = C.BOND_WORK_INDEX_KWH_PER_TON) -> go.Figure:
    feeds = np.linspace(*C.FEED_RANGE_KG_PER_H, 61)
    fig = go.Figure()
    for basis, dash, color, name in (("short", "solid", FIBER, "Python Bond - short-ton basis"),
                                     ("metric", "dash", JUICE, "Python Bond - metric-tonne basis")):
        fig.add_trace(go.Scatter(x=feeds, y=[mill_performance(f, wi, ton_basis=basis).power_kw for f in feeds],
                                 mode="lines", name=name, line=dict(color=color, width=2, dash=dash),
                                 hovertemplate="%{y:.4f} kW<extra>" + name + "</extra>"))
    pw = df.groupby("feed_total_kg_per_h")["mill_power_kw"].first()
    fig.add_trace(go.Scatter(x=pw.index, y=pw.values, mode="markers", name="Aspen MILL_POWER",
                             marker=dict(size=10, color="white", line=dict(color=NEUTRAL, width=2)),
                             hovertemplate="%{y:.4f} kW<extra>Aspen</extra>"))
    fig.add_vline(x=feed, line=dict(color=NEUTRAL, width=1, dash="dot"))
    return _layout(fig, f"Mill power vs feed (Wi = {wi:g} kWh/ton)", "Total pomace feed (kg/h)", "Shaft power (kW)",
                   height=380)


def screen_partition(cut: float, alpha: float) -> go.Figure:
    res = screen_split(200.0, cut, alpha)
    t = res.table[res.table.upper_mm <= 1.5 + 1e-9]
    labels = [f"{lo:g}-{hi:g}" for lo, hi in zip(t.lower_mm, t.upper_mm)]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.1,
                        subplot_titles=("Where each size class goes",
                                        f"Partition curve (d50 = {cut:.2f} mm)"))
    fig.add_trace(go.Bar(x=labels, y=100 * (t.w_feed - t.w_times_E), name="To undersize → fibre product",
                         marker=dict(color=FIBER, line=dict(color="white", width=2)),
                         hovertemplate="%{y:.2f} kg<extra>undersize</extra>"), 1, 1)
    fig.add_trace(go.Bar(x=labels, y=100 * t.w_times_E, name="To oversize → peel co-product",
                         marker=dict(color=OVERSIZE, line=dict(color="white", width=2)),
                         hovertemplate="%{y:.2f} kg<extra>oversize</extra>"), 1, 1)
    d = np.linspace(0, 1.6, 200)
    fig.add_trace(go.Scatter(x=d, y=whiten_partition(d, cut, alpha), mode="lines", name=f"E(d), α = {alpha:g}",
                             line=dict(color=OVERSIZE, width=2), hovertemplate="E = %{y:.3f}<extra></extra>"), 1, 2)
    if not np.isclose(alpha, C.WHITEN_ALPHA):
        fig.add_trace(go.Scatter(x=d, y=whiten_partition(d, cut, C.WHITEN_ALPHA), mode="lines",
                                 name="E(d), α = 3.5 (Aspen)", line=dict(color=NEUTRAL, width=2, dash="dash"),
                                 hovertemplate="E = %{y:.3f}<extra></extra>"), 1, 2)
    fig.add_hline(y=0.5, line=dict(color=NEUTRAL, width=1, dash="dot"), row=1, col=2)
    fig.update_layout(barmode="stack", bargap=0.15, height=400, margin=dict(l=10, r=10, t=70, b=10),
                      legend=dict(orientation="h", yanchor="top", y=-0.18, x=0))
    fig.update_xaxes(title_text="Size class (mm)", row=1, col=1)
    fig.update_yaxes(title_text="Mass (kg per 100 kg solids)", row=1, col=1)
    fig.update_xaxes(title_text="Particle size d (mm)", row=1, col=2)
    fig.update_yaxes(title_text="Fraction to oversize (-)", range=[0, 1.02], row=1, col=2)
    return fig
