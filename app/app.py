"""ZestLoop - interactive website for the orange-pomace valorisation process (ChE 303, Step 6).

Run from the project root:
    streamlit run app/app.py

Works offline: it reads the exported Aspen dataset (data/aspen_results.csv) and the
Python equipment models in calc/. No Aspen connection is needed.
"""
from __future__ import annotations

import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
for p in (str(APP_DIR), str(ROOT)):          # ROOT ends up first -> `calc` package resolves
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

import content as T  # noqa: E402
import figures as F  # noqa: E402
from calc import constants as C  # noqa: E402
from calc.aspen_data import (DEFAULT_CSV, OUTPUT_COLUMNS, OUTPUT_LABELS, AspenInterpolator,  # noqa: E402
                             derived_metrics, load_aspen_csv)
from calc.mill import mill_performance  # noqa: E402
from calc.process import plant_balance  # noqa: E402
from calc.screen import screen_split  # noqa: E402
from calc.verify import compare_with_csv, holdout_table  # noqa: E402

st.set_page_config(page_title=f"{T.COMPANY_NAME} - orange pomace to citrus fibre", page_icon="🍊",
                   layout="wide")


# ---------------------------------------------------------------------------
# Cached data
# ---------------------------------------------------------------------------
@st.cache_data
def aspen_df() -> pd.DataFrame:
    return load_aspen_csv(DEFAULT_CSV)


@st.cache_resource
def interpolator(method: str) -> AspenInterpolator:
    return AspenInterpolator(aspen_df(), method)


@st.cache_data
def verification_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    return compare_with_csv(aspen_df()), holdout_table(aspen_df())


df = aspen_df()
F_MIN, F_MAX = interpolator("pchip").feed_range
C_MIN, C_MAX = interpolator("pchip").cut_range

# ---------------------------------------------------------------------------
# Sidebar - operating conditions
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Operating conditions")
    feed = st.slider("Total pomace feed (kg/h)", int(F_MIN), int(F_MAX), 1000, step=10,
                     help="Wet pomace, 80 wt% liquid / 20 wt% fibre solids (fixed composition).")
    cut = st.slider("Screen cut size d50 (mm)", float(C_MIN), float(C_MAX), 1.00, step=0.01, format="%.2f",
                    help="The screen aperture setting - the main design knob for fibre yield.")
    method = st.radio("Interpolation between Aspen cases", ["pchip", "linear"],
                      format_func=lambda m: {"pchip": "Monotone cubic (PCHIP)", "linear": "Linear"}[m],
                      help="Along the feed axis Aspen results are exactly linear; along the cut-size axis they "
                           "are curved, so PCHIP is more accurate (see the Dataset tab).")
    hours = st.number_input("Operating hours per day", 1, 24, 20)
    st.info(f"**Valid operating range** (Aspen sensitivity study, 42 cases)\n\n"
            f"- Feed: {F_MIN:.0f}-{F_MAX:.0f} kg/h (7 levels)\n"
            f"- Cut size: {C_MIN:.1f}-{C_MAX:.1f} mm (6 levels)\n\n"
            "Inputs are limited to this window; no extrapolation.")

it = interpolator(method)
aspen = it(feed, cut)
der = derived_metrics(feed, aspen)
py = plant_balance(feed, cut)
base = it(1000, 1.0)
exact = it.is_grid_point(feed, cut)
near = it.nearest_case(feed, cut)


def kg(v: float) -> str:
    return f"{v:,.1f} kg/h"


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title(f"🍊 {T.COMPANY_NAME}")
st.markdown(f"#### {T.TAGLINE}")
st.caption(f"{T.LOCATION} · ChE 303 Fluid Particle Systems startup project · "
           "Results come from an exported Aspen Plus dataset and Python equipment models; no live Aspen link.")

tabs = st.tabs(["Company & problem", "Process", "Calculator", "Performance trends",
                "Engineering (Python)", "Dataset & method"])

# ---------------------------------------------------------------------------
# 1. Company & problem
# ---------------------------------------------------------------------------
with tabs[0]:
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("The problem")
        st.markdown(T.PROBLEM)
        st.subheader("Our solution")
        st.markdown(T.SOLUTION)
        for name, desc in T.PRODUCTS:
            st.markdown(f"- **{name}** - {desc}")
        st.subheader("Who we serve")
        st.markdown(T.TARGET_CUSTOMER)
    with right:
        st.subheader("Design basis")
        b = derived_metrics(1000, base)
        st.dataframe(pd.DataFrame([
            ("Wet pomace treated", "1,000 kg/h"),
            ("Screen cut size", "1.0 mm"),
            ("Dry fibre product", kg(base["fiber_kg_per_h"])),
            ("Clarified juice", kg(base["juice_kg_per_h"])),
            ("Oversize peel solids", kg(base["oversize_solids_kg_per_h"])),
            ("Fibre recovery", f"{b['fiber_recovery_pct']:.1f} %"),
            ("Mill shaft power", f"{base['mill_power_kw']:.3f} kW"),
        ], columns=["Aspen base case", "Value"]), hide_index=True)
        st.subheader("Fluid-particle science inside")
        for line in T.WHY_FPS:
            st.markdown(f"- {line}")

# ---------------------------------------------------------------------------
# 2. Process
# ---------------------------------------------------------------------------
def flowsheet_dot() -> str:
    ink, mute = "#0b0b0b", "#52514e"
    unit = 'shape=box, style="rounded,filled", fillcolor="#fde3d6", color="#eb6834", penwidth=1.5'
    term = "shape=plaintext"
    return f"""digraph G {{
  rankdir=TB; bgcolor="#fcfcfb"; pad=0.25; nodesep=0.5; ranksep=0.4;
  node [fontname="Helvetica", fontsize=15, fontcolor="{ink}"];
  edge [fontname="Helvetica", fontsize=13, fontcolor="{ink}", color="{mute}", penwidth=1.6];
  POMACE [{term}, label="POMACE\\n{feed:,.0f} kg/h\\n80 % liquid / 20 % fibre"];
  AIR [{term}, label="HOT-AIR\\n{C.HOT_AIR_KG_PER_H:,.0f} kg/h, {C.HOT_AIR_T_C:.0f} °C"];
  MILL [{unit}, label="MILL\\nhammer mill\\n{aspen['mill_power_kw']:.3f} kW"];
  SCREEN [{unit}, label="SCREEN\\nvibrating screen\\nd50 = {cut:.2f} mm"];
  CENTRIF [{unit}, label="CENTRIF\\ndecanter centrifuge\\ncake {der['cake_moisture_pct']:.0f} % moisture"];
  DRYER [{unit}, label="DRYER\\nhot-air dryer"];
  OVERSIZE [{term}, label="OVERSIZE (peel co-product)\\n{der['oversize_total_kg_per_h']:,.1f} kg/h"];
  JUICE [{term}, label="JUICE (clarified)\\n{aspen['juice_kg_per_h']:,.1f} kg/h"];
  PRODUCT [{term}, label="PRODUCT (dry fibre)\\n{aspen['fiber_kg_per_h']:,.1f} kg/h"];
  EXHAUST [{term}, label="EXHAUST\\n{der['exhaust_kg_per_h']:,.0f} kg/h"];
  POMACE -> MILL;
  MILL -> SCREEN [label="MILLED\\n{feed:,.0f} kg/h"];
  SCREEN -> OVERSIZE [color="#1baf7a", penwidth=2.2];
  SCREEN -> CENTRIF [label="SLURRY\\n{der['slurry_kg_per_h']:,.1f} kg/h"];
  CENTRIF -> JUICE [color="#eb6834", penwidth=2.2];
  CENTRIF -> DRYER [label="WET-CAKE\\n{der['wet_cake_kg_per_h']:,.1f} kg/h"];
  AIR -> DRYER;
  DRYER -> PRODUCT [color="#2a78d6", penwidth=2.2];
  DRYER -> EXHAUST;
  {{rank=same; SCREEN; OVERSIZE}}
  {{rank=same; CENTRIF; JUICE}}
  {{rank=same; DRYER; AIR}}
}}"""


with tabs[1]:
    st.subheader("Process flowsheet - stream flows update with the sidebar inputs")
    g, txt = st.columns([3, 2], gap="large")
    with g:
        st.graphviz_chart(flowsheet_dot(), width="stretch")
        st.caption(f"Flows at {feed:.0f} kg/h and {cut:.2f} mm, from the Aspen dataset "
                   f"({'exact case' if exact else method.upper() + ' interpolation'}); intermediate streams "
                   "closed by mass balance.")
    with txt:
        st.markdown("##### Why this sequence")
        st.markdown(
            "1. **Mill first.** Intact peel holds juice inside its cells and is too coarse (F80 5.7 mm) to "
            "pump. Milling to a P80 of 0.75 mm opens the cells.\n"
            "2. **Screen before the centrifuge.** Coarse peel would wear the decanter scroll and make the "
            "powder gritty, so the screen scalps it off as a pectin or animal-feed co-product.\n"
            "3. **Centrifuge before the dryer.** Removing juice mechanically costs far less energy than "
            "evaporating it.\n"
            "4. **Dryer last.** The 65 % moisture cake spoils within hours, and drying turns it into a "
            "shelf-stable powder.")
        for u in T.UNITS:
            with st.expander(f"{u['Unit']} - {u['Equipment']}"):
                st.markdown(f"**Purpose:** {u['Purpose']}\n\n**Key setting:** {u['Key setting']}")

# ---------------------------------------------------------------------------
# 3. Calculator
# ---------------------------------------------------------------------------
with tabs[2]:
    st.subheader(f"Plant performance at {feed:.0f} kg/h and {cut:.2f} mm cut size")
    if exact:
        st.success(f"Exact Aspen case #{int(near['case'])} - values read directly from the dataset.")
    else:
        st.info(f"Interpolated ({'PCHIP' if method == 'pchip' else 'linear'}) between simulated Aspen cases. "
                f"Nearest simulated case: #{int(near['case'])} "
                f"({near['feed_total_kg_per_h']:.0f} kg/h, {near['cut_size_mm']:.1f} mm).")
    bd = derived_metrics(1000, base)
    st.caption("Small numbers under each value: change from the design point (1000 kg/h, 1.0 mm).")
    r1 = st.columns(4)
    r1[0].metric("Dry fibre product (kg/h)", f"{aspen['fiber_kg_per_h']:.1f}",
                 f"{aspen['fiber_kg_per_h'] - base['fiber_kg_per_h']:+.1f}", border=True)
    r1[1].metric("Clarified juice (kg/h)", f"{aspen['juice_kg_per_h']:.1f}",
                 f"{aspen['juice_kg_per_h'] - base['juice_kg_per_h']:+.1f}", border=True)
    r1[2].metric("Oversize peel solids (kg/h)", f"{aspen['oversize_solids_kg_per_h']:.1f}",
                 f"{aspen['oversize_solids_kg_per_h'] - base['oversize_solids_kg_per_h']:+.1f}",
                 delta_color="inverse", border=True)
    r1[3].metric("Mill shaft power (kW)", f"{aspen['mill_power_kw']:.3f}",
                 f"{aspen['mill_power_kw'] - base['mill_power_kw']:+.3f}", delta_color="inverse", border=True)
    r2 = st.columns(4)
    r2[0].metric("Fibre recovery (%)", f"{der['fiber_recovery_pct']:.1f}",
                 f"{der['fiber_recovery_pct'] - bd['fiber_recovery_pct']:+.1f}", border=True)
    r2[1].metric("Juice recovery (%)", f"{der['juice_recovery_pct']:.1f}",
                 f"{der['juice_recovery_pct'] - bd['juice_recovery_pct']:+.1f}", border=True)
    r2[2].metric("Mill energy (kWh/t)", f"{der['specific_energy_kwh_per_tonne_wet_feed']:.3f}",
                 help="Mill shaft energy per tonne of wet pomace", border=True)
    r2[3].metric("Dryer liquid load (kg/h)", f"{der['dryer_liquid_removed_kg_per_h']:.1f}",
                 help="Liquid leaving the wet cake in the dryer", border=True)
    r3 = st.columns(4)
    r3[0].metric(f"Fibre per day (t, {hours} h)", f"{aspen['fiber_kg_per_h'] * hours / 1000:.2f}", border=True)
    r3[1].metric(f"Juice per day (t, {hours} h)", f"{aspen['juice_kg_per_h'] * hours / 1000:.2f}", border=True)
    r3[2].metric("Pomace diverted (t/day)", f"{feed * hours / 1000:.1f}", border=True)
    r3[3].metric("Mill energy (kWh/day)", f"{aspen['mill_power_kw'] * hours:.1f}", border=True)

    st.markdown("##### Aspen dataset vs independent Python model")
    model = {"mill_power_kw": py.mill_power_kw, "oversize_solids_kg_per_h": py.oversize_solids_kg_per_h,
             "juice_kg_per_h": py.juice_kg_per_h, "fiber_kg_per_h": py.fiber_product_kg_per_h}
    comp = pd.DataFrame({
        "Output": [OUTPUT_LABELS[c] for c in OUTPUT_COLUMNS],
        "Aspen (CSV)": [aspen[c] for c in OUTPUT_COLUMNS],
        "Python model": [model[c] for c in OUTPUT_COLUMNS],
    })
    comp["Difference (%)"] = 100 * (comp["Python model"] / comp["Aspen (CSV)"] - 1)
    st.dataframe(comp, hide_index=True, column_config={
        "Aspen (CSV)": st.column_config.NumberColumn(format="%.4f"),
        "Python model": st.column_config.NumberColumn(format="%.4f"),
        "Difference (%)": st.column_config.NumberColumn(format="%+.4f")})
    st.caption("Python model = Bond's law (mill) + Whiten partition curve (screen) + centrifuge/dryer mass "
               "balances, written independently of Aspen. At simulated cases the two agree to ~1e-7 %; between "
               "cases the difference is the interpolation error.")
    with st.expander("Full stream table (mass balance closed around the Aspen outputs)"):
        streams = pd.DataFrame([
            ("POMACE (feed)", feed), ("HOT-AIR", C.HOT_AIR_KG_PER_H),
            ("OVERSIZE (solids + 5 % entrained liquid)", der["oversize_total_kg_per_h"]),
            ("SLURRY", der["slurry_kg_per_h"]), ("JUICE", aspen["juice_kg_per_h"]),
            ("WET-CAKE", der["wet_cake_kg_per_h"]), ("PRODUCT (dry fibre)", aspen["fiber_kg_per_h"]),
            ("EXHAUST (air + evaporated liquid)", der["exhaust_kg_per_h"]),
        ], columns=["Stream", "Total flow (kg/h)"])
        st.dataframe(streams, hide_index=True,
                     column_config={"Total flow (kg/h)": st.column_config.NumberColumn(format="%.2f")})
        out_total = (der["oversize_total_kg_per_h"] + aspen["juice_kg_per_h"] + aspen["fiber_kg_per_h"]
                     + der["exhaust_kg_per_h"])
        st.write(f"In: {feed + C.HOT_AIR_KG_PER_H:,.2f} kg/h · Out: {out_total:,.2f} kg/h · "
                 f"Implied cake moisture: {der['cake_moisture_pct']:.2f} % (Aspen spec 65 %)")

# ---------------------------------------------------------------------------
# 4. Performance trends
# ---------------------------------------------------------------------------
with tabs[3]:
    st.plotly_chart(F.products_vs_cut(it, feed, cut))
    st.markdown("**Trade-off:** opening the screen lets more milled fibre through to the centrifuge, so fibre "
                "product rises and oversize falls. Juice falls at the same time, because every extra kg of fibre "
                "leaves the decanter holding about 1.86 kg of liquid (65 wt% cake moisture).")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(F.recovery_vs_cut(df, cut, it))
        st.caption("Recoveries depend only on cut size: all 7 feed rates collapse onto the same points, "
                   "so the plant scales linearly with throughput.")
    with c2:
        st.plotly_chart(F.fiber_heatmap(it, feed, cut))
        st.caption("Dots = the 42 simulated Aspen cases; colour between them is interpolated.")

# ---------------------------------------------------------------------------
# 5. Engineering (Python)
# ---------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Unit A - Hammer mill: Bond's law of comminution")
    st.latex(r"W = 10\,W_i\left(\frac{1}{\sqrt{P_{80}}}-\frac{1}{\sqrt{F_{80}}}\right)"
             r"\qquad P = \frac{W\,\dot m_\mathrm{solids}}{\eta}")
    st.markdown(
        "| Symbol | Meaning | Unit |\n|---|---|---|\n"
        "| W | specific grinding energy | kWh/ton solids |\n"
        "| W<sub>i</sub> | Bond work index (12 for fibrous peel) | kWh/ton |\n"
        "| F<sub>80</sub>, P<sub>80</sub> | 80 % passing size of feed / product | µm |\n"
        "| ṁ<sub>solids</sub> | dry fibre flow through the mill (20 % of feed) | ton/h |\n"
        "| η | mechanical efficiency (1.0, as in Aspen) | - |", unsafe_allow_html=True)
    a1, a2 = st.columns([1, 2], gap="large")
    with a1:
        wi = st.number_input("Work index Wi (kWh/ton)", 4.0, 30.0, 12.0, step=0.5)
        basis = st.radio("Ton basis", ["short", "metric"],
                         format_func=lambda b: {"short": "Short ton, 907 kg (Bond / Aspen)",
                                                "metric": "Metric tonne, 1000 kg"}[b])
        m = mill_performance(feed, wi, ton_basis=basis)
        ton_kg = C.KG_PER_SHORT_TON if basis == "short" else C.KG_PER_METRIC_TONNE
        st.markdown(
            f"**Calculation at {feed:.0f} kg/h**\n\n"
            f"1. F80 from the raw PSD: Q(4 mm) = 0.55, Q(6 mm) = 0.85 → "
            f"F80 = 4 + 0.25/0.30 × 2 = **{m.f80_um/1000:.3f} mm**\n"
            f"2. P80 from the milled PSD: Q(0.5 mm) = 0.70, Q(1 mm) = 0.90 → "
            f"P80 = 0.5 + 0.10/0.20 × 0.5 = **{m.p80_um/1000:.3f} mm**\n"
            f"3. W = 10 × {wi:g} × (1/√{m.p80_um:.0f} − 1/√{m.f80_um:.0f}) = "
            f"**{m.specific_energy_kwh_per_ton_solids:.4f} kWh/ton**\n"
            f"4. ṁ = {m.solids_kg_per_h:.0f} kg/h ÷ {ton_kg:.2f} = {m.solids_kg_per_h/ton_kg:.5f} ton/h\n"
            f"5. P = **{m.power_kw:.4f} kW** (reduction ratio {m.reduction_ratio:.2f})")
        if np.isclose(wi, 12) and basis == "short":
            st.success(f"Aspen MILL_POWER = {aspen['mill_power_kw']:.6f} kW → difference "
                       f"{100*(m.power_kw/aspen['mill_power_kw']-1):+.1e} %")
        else:
            st.warning("Python-only what-if: Aspen was run with Wi = 12 on the short-ton basis.")
    with a2:
        st.plotly_chart(F.mill_power_vs_feed(df, feed, wi))
        st.caption("Aspen falls exactly on the short-ton line, which shows that Aspen applies Bond's original "
                   "definition (kWh per short ton). On the metric basis the power would be 9.3 % lower.")

    st.divider()
    st.subheader("Unit B - Vibrating screen: Whiten partition curve")
    st.latex(r"E(d)=\frac{e^{\alpha x}-1}{e^{\alpha x}+e^{\alpha}-2},\quad x=\frac{d}{d_{50}}"
             r"\qquad \dot m_\mathrm{oversize}=\dot m_\mathrm{solids}\sum_i w_i\,E(\bar d_i)")
    st.markdown("E(d) is the fraction of particles of size d that report to oversize. d<sub>50</sub> is the cut "
                "size, where E = 0.5. α is the sharpness: a large α gives an ideal sieve. "
                "w<sub>i</sub> is the mass fraction of milled solids in size class i, and "
                "d̄<sub>i</sub> is the class midpoint.", unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4, vertical_alignment="bottom")
    alpha = s1.slider("Sharpness α (-)", 1.0, 15.0, C.WHITEN_ALPHA, step=0.5,
                      help="3.5 is the value that reproduces the Aspen results.")
    sr = screen_split(py.feed_solids_kg_per_h, cut, alpha)
    s2.metric("Oversize solids (kg/h)", f"{sr.oversize_solids_kg_per_h:.2f}")
    s3.metric("Undersize → fibre (kg/h)", f"{sr.undersize_solids_kg_per_h:.2f}")
    s4.metric("Fibre to undersize (%)", f"{100*sr.undersize_recovery:.2f}")
    if np.isclose(alpha, C.WHITEN_ALPHA):
        st.success(f"Matches Aspen: OVERSIZE at this point = {aspen['oversize_solids_kg_per_h']:.3f} kg/h "
                   f"(Python {sr.oversize_solids_kg_per_h:.3f} kg/h; between cases the gap is interpolation error).")
    else:
        st.warning("Python-only what-if: a sharper screen passes more fine fibre and rejects more coarse "
                   "peel. Aspen was run with α = 3.5.")
    st.plotly_chart(F.screen_partition(cut, alpha))
    with st.expander("Hand-calculation table for this cut size (per interval)"):
        tbl = sr.table[sr.table.w_feed > 0].copy()
        st.dataframe(tbl, hide_index=True, column_config={
            c: st.column_config.NumberColumn(format="%.4f") for c in tbl.columns})
        st.write(f"Σ wᵢEᵢ = {sr.oversize_fraction:.5f} → oversize = {sr.solids_in_kg_per_h:.1f} × "
                 f"{sr.oversize_fraction:.5f} = {sr.oversize_solids_kg_per_h:.2f} kg/h")

    st.divider()
    st.subheader("Independent verification against Aspen")
    comp_all, hold = verification_tables()
    summ = pd.DataFrame({
        "Output": [OUTPUT_LABELS[c] for c in OUTPUT_COLUMNS],
        "Cases compared": [len(comp_all)] * 4,
        "Max |relative error|": [comp_all[f"{c}_rel_err"].abs().max() for c in OUTPUT_COLUMNS],
    })
    st.dataframe(summ, hide_index=True,
                 column_config={"Max |relative error|": st.column_config.NumberColumn(format="%.1e")})
    st.markdown("**Assumptions:**\n"
                "- steady state, with the feed composition (80/20) and raw PSD fixed;\n"
                "- Bond's law acts on the dry fibre only;\n"
                "- the mill outlet PSD is specified (as in Aspen), so mill power does not depend on the cut size;\n"
                "- the screen partition depends only on particle size, with no bypass and no breakage on the deck;\n"
                "- 5 wt% of the inlet liquid is carried into the oversize;\n"
                "- the centrifuge retains every particle above 0.05 mm, giving a 65 wt% moisture cake;\n"
                "- the dryer gives a bone-dry product.")

# ---------------------------------------------------------------------------
# 6. Dataset & method
# ---------------------------------------------------------------------------
with tabs[5]:
    st.subheader("How the Aspen dataset is organised")
    st.markdown(
        "Aspen Plus **Sensitivity S-1** varied two inputs on a full grid, giving 7 × 6 = **42 converged cases**:\n"
        "- **VARY 1:** POMACE MIXED mass flow, 400-1600 kg/h. A Calculator block (SCALE-FD) sets "
        "solids = 0.25 × liquid, so the total feed runs from 500 to 2000 kg/h in 250 kg/h steps.\n"
        "- **VARY 2:** SCREEN deck-1 cut size, 0.5-1.5 mm in 0.2 mm steps (exported in metres).\n"
        "- **Tabulated:** MILL_POWER (kW), OVERSIZE solids, JUICE and FIBER (all kg/h).\n\n"
        "The website reads the raw export `data/aspen_results.csv`. It cleans the multi-line Aspen headers, "
        "converts the cut size to mm, and checks that all cases have status OK and form a complete grid.")
    show = df.rename(columns={"feed_total_kg_per_h": "Feed (kg/h)", "feed_liquid_kg_per_h": "Liquid (kg/h)",
                              "cut_size_mm": "Cut size (mm)", **OUTPUT_LABELS})
    st.dataframe(show, hide_index=True, height=300)
    st.download_button("Download raw Aspen CSV", DEFAULT_CSV.read_bytes(), "aspen_results.csv", "text/csv")

    st.subheader("How results are retrieved")
    st.markdown(
        "- **Exact lookup** when the inputs land on a simulated case.\n"
        "- Otherwise **2-D interpolation** on the regular (feed, cut size) grid, using "
        "`scipy.interpolate.RegularGridInterpolator`.\n"
        "  - Along the feed axis every Aspen output is exactly linear (doubling the feed doubles every "
        "flow), so both methods are exact there.\n"
        "  - Along the cut-size axis the outputs are curved and monotone, so the default is **PCHIP**, a "
        "monotone cubic that cannot overshoot.\n"
        "- **Hold-out check:** the Aspen base case (1000 kg/h, **1.0 mm**) is *not* in the CSV, but its "
        "stream table is in the Aspen report. It is therefore a true blind test of the interpolation:")
    hold_show = hold.rename(columns={"output": "Output", "aspen_table3": "Aspen report",
                                     "pchip_interp": "PCHIP", "linear_interp": "Linear",
                                     "pchip_interp_err_pct": "PCHIP error (%)",
                                     "linear_interp_err_pct": "Linear error (%)"})
    hold_show["Output"] = hold_show["Output"].map(OUTPUT_LABELS)
    st.dataframe(hold_show[["Output", "Aspen report", "PCHIP", "PCHIP error (%)", "Linear", "Linear error (%)"]],
                 hide_index=True, column_config={
                     c: st.column_config.NumberColumn(format="%.4f")
                     for c in ["Aspen report", "PCHIP", "PCHIP error (%)", "Linear", "Linear error (%)"]})

    st.subheader("Model limitations")
    st.markdown(
        f"- Valid only for {F_MIN:.0f}-{F_MAX:.0f} kg/h and {C_MIN:.1f}-{C_MAX:.1f} mm. The site does not "
        "extrapolate.\n"
        "- The feed composition (80 % liquid) and raw PSD are fixed. Seasonal changes in the fruit are not "
        "modelled.\n"
        "- The mill outlet PSD is specified rather than predicted. Bond's work index (12 kWh/ton) is a "
        "literature-type value, not measured on our pomace.\n"
        "- The screen uses Aspen's default Whiten sharpness (α = 3.5), and blinding of fine meshes by sticky "
        "pectin is not modelled.\n"
        "- The centrifuge is ideal classification with a fixed 65 % cake moisture; it is not sized from "
        "Σ-theory.\n"
        "- The dryer is a shortcut model with the air flow fixed at 1500 kg/h for every case. Its heat "
        "balance and air capacity have not been sized here. Aspen also sends the dissolved sugar and acid "
        "to the exhaust, whereas in a real dryer they would stay in the powder.")
