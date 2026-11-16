import numpy as np
import pytest

from calc import constants as C
from calc.psd import cumulative_passing, d_percent_passing, interval_midpoints_mm


def test_cumulative_passing_ends_at_one():
    q = cumulative_passing(C.PSD_EDGES_MM, C.RAW_POMACE_WFRAC)
    assert q[0] == 0 and np.isclose(q[-1], 1.0)
    assert np.all(np.diff(q) >= 0)


def test_feed_f80_hand_calc():
    # Hand calc: Q(4 mm) = 0.55, Q(6 mm) = 0.85 -> F80 = 4 + (0.80 - 0.55)/0.30 * 2 = 5.667 mm
    assert d_percent_passing(C.PSD_EDGES_MM, C.RAW_POMACE_WFRAC, 0.80) == pytest.approx(4 + 0.25 / 0.30 * 2)


def test_product_p80_hand_calc():
    # Hand calc: Q(0.5 mm) = 0.70, Q(1.0 mm) = 0.90 -> P80 = 0.5 + 0.10/0.20 * 0.5 = 0.75 mm
    assert d_percent_passing(C.PSD_EDGES_MM, C.MILL_OUTLET_WFRAC, 0.80) == pytest.approx(0.75)


def test_d50_values_match_aspen_report():
    # Report section 5.1: D50 drops from 3.714 mm to 0.357 mm
    assert d_percent_passing(C.PSD_EDGES_MM, C.RAW_POMACE_WFRAC, 0.5) == pytest.approx(3.714, abs=5e-4)
    assert d_percent_passing(C.PSD_EDGES_MM, C.MILL_OUTLET_WFRAC, 0.5) == pytest.approx(0.357, abs=5e-4)


def test_midpoints():
    assert interval_midpoints_mm([0, 1, 3]) == pytest.approx([0.5, 2.0])


def test_bad_psd_rejected():
    with pytest.raises(ValueError):
        cumulative_passing([0, 1, 2], [0.5, 0.4])          # does not sum to 1
    with pytest.raises(ValueError):
        d_percent_passing(C.PSD_EDGES_MM, C.RAW_POMACE_WFRAC, 1.2)
