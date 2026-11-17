# ZestLoop – orange pomace to citrus fibre

ChE 303 Fluid Particle Systems startup project.

Around 50-60 % of each orange is put out as wet pomace, by Juice . ZestLoop turns it into dry citrus-fibre powder, clarified juice and a coarse peel co-product, using a continuous line:

**POMACE → hammer MILL → SCREEN → decanter CENTRIFUGE → DRYER**

The process was simulated in Aspen Plus, with 42 cases covering a feed of 500–2000 kg/h and a screen cut size of 0.5–1.5 mm. This repository holds the Python equipment calculations, the exported Aspen dataset, the interactive website and the presentation source.

## Run it

Requires Python 3.10 or newer.

```bash
python -m pip install -r requirements.txt
```

Start the website. It opens at http://localhost:8501 and works offline:

```bash
python -m streamlit run app/app.py
```

On Windows you can also double-click `start_website.bat`. The website runs only while that window stays open.

Run the tests:

```bash
python -m pytest
```

Print the hand calculations and the check against Aspen, and redraw the figures in `docs/figures/`:

```bash
python -m calc.verify
```

## What's in the repository

| Folder | Contents |
|---|---|
| `calc/` | Equipment models: Bond's law for the hammer mill, the Whiten partition curve for the screen, a plant mass balance, and interpolation of the Aspen dataset. `calc/tests/` holds the test suite. |
| `data/` | `aspen_results.csv`: the 42-case Aspen sensitivity study (an identical copy of `FPS dataset.csv`). |
| `app/` | The Streamlit website. All company text is in `app/content.py`. |
| `docs/` | Step 4 (equipment calculations) and Step 6 (website) write-ups, and their figures. |
| `slides/` | Source files for the final presentation. |

## Valid range

The website and the interpolation cover only the range Aspen was run for:
- **Feed:** 500–2000 kg/h of wet pomace.
- **Screen cut size:** 0.5–1.5 mm.

Inputs outside this range are refused, not extrapolated.

The Python model reproduces all 42 Aspen cases to a relative error of about 1e-9. Model assumptions and limitations are listed in `docs/`.
