"""Vibrating screen (Whiten partition curve): hand calculation + verification against Aspen OVERSIZE."""
import math

import numpy as np
import pytest

from calc.aspen_data import load_aspen_csv
from calc.screen import screen_split, whiten_partition


def _whiten_by_hand(d, d50, a=3.5):
    x = d / d50
    return (math.exp(a * x) - 1) / (math.exp(a * x) + math.exp(a) - 2)


def test_partition_is_half_at_cut_size():
    assert whiten_partition(0.8, 0.8) == pytest.approx(0.5)
    assert whiten_partition(1.3, 1.3, alpha=10) == pytest.approx(0.5)


def test_partition_limits_and_monotonic():
    d = np.linspace(0, 5, 200)
    e = whiten_partition(d, 1.0)
    assert e[0] == 0.0
    assert np.all(np.diff(e) > 0)
    assert whiten_partition(1e6, 1.0) == pytest.approx(1.0)


def test_sharper_screen_is_closer_to_ideal_sieve():
    assert whiten_partition(0.5, 1.0, alpha=20) < whiten_partition(0.5, 1.0, alpha=3.5)
    assert whiten_partition(1.5, 1.0, alpha=20) > whiten_partition(1.5, 1.0, alpha=3.5)


def test_hand_calc_base_case_cut_1mm():
    # Hand table (d50 = 1.0 mm, alpha = 3.5, interval midpoints):
    rows = [(0.075, 0.10), (0.175, 0.25), (0.375, 0.35), (0.75, 0.20), (1.25, 0.10)]
    sum_we = sum(w * _whiten_by_hand(d, 1.0) for d, w in rows)
    assert sum_we == pytest.approx(0.16258, abs=1e-5)
    res = screen_split(200, 1.0)
    assert res.oversize_fraction == pytest.approx(sum_we, rel=1e-12)
    assert res.oversize_solids_kg_per_h == pytest.approx(32.52, abs=0.005)    # Aspen Table 3
    assert res.undersize_solids_kg_per_h == pytest.approx(167.48, abs=0.005)  # Aspen Table 3


def test_screen_matches_all_42_aspen_cases():
    df = load_aspen_csv()
    for _, r in df.iterrows():
        res = screen_split(0.2 * r.feed_total_kg_per_h, r.cut_size_mm)
        assert res.oversize_solids_kg_per_h == pytest.approx(r.oversize_solids_kg_per_h, rel=1e-6)
        assert res.undersize_solids_kg_per_h == pytest.approx(r.fiber_kg_per_h, rel=1e-6)


def test_split_conserves_mass_per_interval():
    res = screen_split(350, 0.7)
    t = res.table
    assert np.allclose(t.oversize_kg_per_h + t.undersize_kg_per_h, 350 * t.w_feed)
    assert res.oversize_solids_kg_per_h + res.undersize_solids_kg_per_h == pytest.approx(350)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        whiten_partition(1.0, 0.0)
    with pytest.raises(ValueError):
        whiten_partition(1.0, 1.0, alpha=-1)
