"""CSV loader and the interpolator the website uses."""
import numpy as np
import pytest

from calc.aspen_data import OUTPUT_COLUMNS, AspenInterpolator, derived_metrics, load_aspen_csv


@pytest.fixture(scope="module")
def df():
    return load_aspen_csv()


def test_loader_shape_and_units(df):
    assert len(df) == 42
    assert sorted(df.feed_total_kg_per_h.unique()) == [500, 750, 1000, 1250, 1500, 1750, 2000]
    assert np.allclose(sorted(df.cut_size_mm.unique()), [0.5, 0.7, 0.9, 1.1, 1.3, 1.5])
    assert (df.feed_liquid_kg_per_h == 0.8 * df.feed_total_kg_per_h).all()


def test_solids_balance_in_csv(df):
    # OVERSIZE column is solids only: FIBER + OVERSIZE = 20 % of the feed
    assert np.allclose(df.fiber_kg_per_h + df.oversize_solids_kg_per_h, 0.2 * df.feed_total_kg_per_h)


@pytest.mark.parametrize("method", ["pchip", "linear"])
def test_exact_at_grid_points(df, method):
    it = AspenInterpolator(df, method)
    for _, r in df.iterrows():
        got = it(r.feed_total_kg_per_h, r.cut_size_mm)
        for col in OUTPUT_COLUMNS:
            assert got[col] == pytest.approx(r[col], rel=1e-9)


def test_pchip_predicts_held_out_aspen_base_case(df):
    # 1.0 mm is NOT in the CSV grid; Aspen base case (report Table 3) is the held-out truth.
    got = AspenInterpolator(df, "pchip")(1000, 1.0)
    assert got["fiber_kg_per_h"] == pytest.approx(167.48, rel=5e-4)
    assert got["juice_kg_per_h"] == pytest.approx(448.96, rel=5e-4)
    assert got["oversize_solids_kg_per_h"] == pytest.approx(32.52, rel=5e-4)


def test_pchip_beats_linear_on_held_out_point(df):
    p = AspenInterpolator(df, "pchip")(1000, 1.0)["fiber_kg_per_h"]
    lin = AspenInterpolator(df, "linear")(1000, 1.0)["fiber_kg_per_h"]
    assert abs(p - 167.48) < abs(lin - 167.48)


def test_feed_axis_is_linear(df):
    it = AspenInterpolator(df, "pchip")
    mid = it(875, 0.9)["fiber_kg_per_h"]
    assert mid == pytest.approx(0.5 * (it(750, 0.9)["fiber_kg_per_h"] + it(1000, 0.9)["fiber_kg_per_h"]))


def test_out_of_range_rejected(df):
    it = AspenInterpolator(df)
    assert not it.in_range(2100, 1.0)
    with pytest.raises(ValueError):
        it(2100, 1.0)
    with pytest.raises(ValueError):
        it(1000, 0.4)


def test_nearest_case_and_grid_flag(df):
    it = AspenInterpolator(df)
    assert it.is_grid_point(1000, 0.5) and not it.is_grid_point(1000, 1.0)
    assert int(it.nearest_case(1010, 0.52)["case"]) == 13


def test_derived_metrics(df):
    out = AspenInterpolator(df)(1000, 0.5)
    d = derived_metrics(1000, out)
    assert d["fiber_recovery_pct"] == pytest.approx(61.02, abs=0.005)
    assert abs(d["solids_balance_error_kg_per_h"]) < 1e-6
    # The 65 wt% cake moisture set in Aspen is recovered from the balance alone
    assert d["cake_moisture_pct"] == pytest.approx(65.0, abs=1e-4)
    # Base case (report Table 3) streams from interpolated values
    b = derived_metrics(1000, AspenInterpolator(df)(1000, 1.0))
    assert b["slurry_kg_per_h"] == pytest.approx(927.48, abs=0.02)
    assert b["wet_cake_kg_per_h"] == pytest.approx(478.52, abs=0.02)
    assert b["exhaust_kg_per_h"] == pytest.approx(1811.04, abs=0.02)
