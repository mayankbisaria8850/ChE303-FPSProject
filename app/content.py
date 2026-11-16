"""All company / branding text for the website lives here - edit this file only.

ZestLoop is a suggested working name; replace it with the Step-1 company details.
"""

COMPANY_NAME = "ZestLoop"
TAGLINE = "Orange pomace in. Citrus fibre and juice out."
LOCATION = "Indore, Madhya Pradesh"

TARGET_CUSTOMER = (
    "Citrus juice and pulp processors in the Malwa orange belt of Madhya Pradesh and across India "
    "that generate roughly 0.5-2 tonnes per hour of wet orange pomace during the season."
)

PROBLEM = (
    "When a juice plant squeezes oranges, 45-50 % of the fruit mass leaves as wet **pomace** - peel, "
    "pulp, seeds and trapped juice. It is about 80 % liquid and full of fermentable sugar, so it spoils "
    "within hours, smells, and costs the plant money to haul to landfill or sell as low-value cattle feed."
)

SOLUTION = (
    "ZestLoop installs a compact, continuous **mill → screen → decanter centrifuge → dryer** line next to "
    "the juicer. Particle-size control turns the waste into two saleable products and one co-product:"
)

PRODUCTS = [
    ("Dry citrus-fibre powder", "Shelf-stable dietary fibre for food thickening, bakery and nutraceuticals."),
    ("Clarified secondary juice", "Particle-free juice returned to the beverage line or sent to fermentation."),
    ("Coarse peel fraction", "Screen oversize - feedstock for pectin extraction or animal feed."),
]

WHY_FPS = [
    "**Size reduction** (hammer mill) opens the juice-holding peel cells - energy from Bond's law.",
    "**Screening** sets the particle-size cut that decides how much fibre becomes product.",
    "**Centrifugal solid-liquid separation** recovers juice and leaves a 65 % moisture cake.",
    "**Drying** turns the cake into a stable powder.",
]

UNITS = [
    {"Unit": "MILL", "Equipment": "Hammer mill (Aspen Crusher)",
     "Purpose": "Shred coarse peel (F80 = 5.7 mm) to fine particles (P80 = 0.75 mm) and release trapped juice",
     "Key setting": "Bond work index 12 kWh/ton, user-specified outlet PSD"},
    {"Unit": "SCREEN", "Equipment": "Single-deck vibrating screen",
     "Purpose": "Scalp coarse peel that would wear the centrifuge; it is the main design knob for fibre yield",
     "Key setting": "Cut size 0.5-1.5 mm (base 1.0 mm), Whiten α = 3.5, 5 % liquid to oversize"},
    {"Unit": "CENTRIF", "Equipment": "Decanter centrifuge (Aspen Cfuge)",
     "Purpose": "Separate clarified juice from the fibre cake; works on viscous, pectin-rich slurry",
     "Key setting": "Cut size 0.05 mm (all milled fibre retained), cake moisture 65 wt%"},
    {"Unit": "DRYER", "Equipment": "Convective hot-air dryer",
     "Purpose": "Remove residual liquid from the cake to give shelf-stable fibre powder",
     "Key setting": "1500 kg/h air at 90 °C, bone-dry product"},
]
