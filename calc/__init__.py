"""Equipment-level calculations for the orange-pomace valorisation process (ChE 303, Step 4).

Modules
-------
constants   Design-basis numbers taken from the Aspen Plus report (PSD mesh, Wi, alpha, ...)
psd         Particle-size-distribution helpers (cumulative passing, d80, interval midpoints)
mill        Hammer mill: Bond / Kick / Rittinger comminution energy
screen      Vibrating screen: Whiten partition (efficiency) curve
process     Whole-flowsheet Python model (mill -> screen -> centrifuge -> dryer)
aspen_data  Loader + interpolator for the exported Aspen sensitivity CSV
verify      `python -m calc.verify` - hand calculation and verification against Aspen
"""
