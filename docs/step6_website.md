# Step 6 – Interactive website (ZestLoop)

A Streamlit site in `app/` that runs fully offline. It reads the exported Aspen dataset and the Python models in `calc/`. No connection to Aspen is needed.

## How to run

```bash
python -m pip install -r requirements.txt
```

```bash
streamlit run app/app.py
```

The site opens at http://localhost:8501.

On Windows you can instead double-click **`start_website.bat`** in the project folder. It starts the site and opens it in the browser. The site runs only while that window stays open; it does not time out from inactivity.

To change the company name, tagline, customer or problem text, edit **`app/content.py`** only.

## What is on the site (brief checklist)

| Requirement | Where |
|---|---|
| Company and problem description | **Company & problem** tab |
| Process diagram + explanation | **Process** tab: a Graphviz flowsheet whose stream flows update live with the inputs, plus "why this sequence" and a card per unit |
| Interactive calculator | **Sidebar** inputs and the **Calculator** tab (see below) |
| Plot of performance vs operating conditions | **Performance trends** tab (see below), plus the mill-power and partition-curve charts in the **Engineering** tab |
| Uses Python calculations | **Engineering (Python)** tab: Bond and Whiten models, live hand calculation, what-if inputs for W<sub>i</sub> and α, verification table. The Calculator also shows Python vs Aspen side by side |
| Retrieves precomputed Aspen results | `calc/aspen_data.py`: exact lookup at simulated cases, 2-D interpolation between them |
| Valid operating range shown | Blue box in the sidebar. The sliders cannot leave 500–2000 kg/h × 0.5–1.5 mm |
| No live Aspen connection | Reads `data/aspen_results.csv` only |

**Sidebar inputs:**
- feed rate, 500–2000 kg/h;
- screen cut size, 0.50–1.50 mm;
- interpolation method;
- operating hours per day.

**Calculator outputs:**
- fibre, juice and oversize flows;
- mill power;
- fibre and juice recoveries;
- kWh per tonne of feed;
- dryer liquid load;
- production per day.

**Performance trends charts:**
- product split vs cut size, at the selected feed rate;
- recovery vs cut size, for all 42 cases;
- heatmap of fibre product over the whole operating window.

## How the dataset is organised

The raw Aspen export is copied unchanged from `FPS dataset.csv` to `data/aspen_results.csv`.

It comes from Aspen **Sensitivity S-1**, a full 7 × 6 grid of 42 converged cases:

| Column (Aspen header) | Meaning | Unit |
|---|---|---|
| TOTAL FEED FLOW RATE | total wet pomace | kg/h (500 … 2000, step 250) |
| VARY 1 – POMACE MIXED TOTAL MASSFLOW | liquid part of the feed (SCALE-FD sets solids = 0.25 × liquid) | kg/h |
| VARY 2 – SCREEN 1 DECK-DAT CUT-SIZE | screen cut size | m (0.0005 … 0.0015, step 0.0002) |
| MILL_POWER | mill shaft power | kW |
| OVERSIZE | screen oversize **solids** (cellulose only) | kg/h |
| JUICE | clarified juice from the centrifuge | kg/h |
| FIBER | dry fibre product from the dryer | kg/h |

`load_aspen_csv()` prepares the data as follows:
- cleans the multi-line headers;
- checks that every header contains the expected keywords, so a re-ordered re-export fails loudly;
- checks that every case has status OK;
- converts the cut size from m to mm;
- confirms the 42 cases form a complete grid.

The site recomputes every other stream by mass balance around these four outputs: OVERSIZE total, SLURRY, WET-CAKE and EXHAUST. As a consistency check, the 65 % cake moisture is recovered from that balance.

## How results are retrieved / interpolated

- **Exact lookup.** If the inputs land on a simulated case, the CSV row is shown and labelled "Exact Aspen case #n".
- **Between cases.** The site uses `scipy.interpolate.RegularGridInterpolator` on the (feed, cut size) grid.
  - **Feed axis.** Every Aspen output is exactly linear in feed (doubling the feed doubles every flow), so any method is exact along this axis.
  - **Cut-size axis.** The outputs are curved and monotone. The default is **PCHIP**, a monotone piecewise-cubic that cannot overshoot. Linear interpolation is available as an option for comparison.
- **Blind validation.** The Aspen base case (1000 kg/h, **1.0 mm**) is *not* a CSV grid point, but its stream table is in the Aspen report (Table 3):

| Output | Aspen report | PCHIP | error | Linear | error |
|---|---|---|---|---|---|
| Dry fibre (kg/h) | 167.48 | 167.486 | +0.003 % | 166.965 | −0.31 % |
| Juice (kg/h) | 448.96 | 448.955 | −0.001 % | 449.922 | +0.21 % |
| Oversize solids (kg/h) | 32.52 | 32.514 | −0.02 % | 33.035 | +1.58 % |

PCHIP is about 100× more accurate than linear here, which is why it is the default.

## Demo script for the presentation (Step 7)

1. **Company tab.** Explain the problem and the customer.
2. **Process tab.** Move the **cut size** slider and watch the SLURRY, OVERSIZE, JUICE and PRODUCT labels change.
3. **Calculator.**
   - Set 1000 kg/h at 0.5 mm. The site shows "Exact Aspen case #13": 122.0 kg/h fibre and 533.4 kg/h juice.
   - Slide to 1.5 mm: fibre rises to 184.0 kg/h and juice falls to 418.3 kg/h.
   - Explain the trade-off. Every extra kg of fibre that reaches the decanter carries about 1.86 kg of liquid into the 65 % moisture cake.
4. **Raise the feed to 2000 kg/h.** Every flow and the mill power double, while recoveries stay the same: the plant scales linearly.
5. **Engineering tab.**
   - Show the Bond hand calculation. Switch to the metric-tonne basis and see the 9.3 % gap.
   - Move α from 3.5 to 10 to see what a sharper (more expensive) screen would do.
6. **Dataset tab.** Show how the data is organised, the interpolation hold-out test, and the limitations.

## Files

| File | Role |
|---|---|
| `app/app.py` | page layout, sidebar inputs, tabs |
| `app/figures.py` | plotly chart builders |
| `app/content.py` | all company and branding text |
| `calc/aspen_data.py` | CSV loader, interpolator, mass-balance-derived metrics |
| `calc/process.py`, `calc/mill.py`, `calc/screen.py` | Python equipment models (Step 4) |
| `.streamlit/config.toml` | orange accent colour; follows the viewer's light/dark setting |
