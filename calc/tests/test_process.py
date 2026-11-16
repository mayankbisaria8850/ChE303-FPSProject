"""Whole-flowsheet Python model vs Aspen base case (report Table 3) and the 42-case CSV."""
import pytest

from calc.aspen_data import load_aspen_csv
from calc.process import plant_balance

# Report Table 3 - base case 1000 kg/h, 1.0 mm cut, totals in kg/h
TABLE3 = {
    "oversize_total_kg_per_h": 72.52,
    "oversize_solids_kg_per_h": 32.52,
    "slurry_total_kg_per_h": 927.48,
    "juice_kg_per_h": 448.96,
    "wet_cake_kg_per_h": 478.52,
    "fiber_product_kg_per_h": 167.48,
    "dryer_liquid_removed_kg_per_h": 279.94 + 27.22 + 3.89,   # EXHAUST minus AIR
}


@pytest.mark.parametrize("key,expected", TABLE3.items())
def test_base_case_matches_aspen_table3(key, expected):
    res = plant_balance(1000, 1.0).as_dict()
    assert res[key] == pytest.approx(expected, abs=0.011)


def test_base_case_kpis():
    r = plant_balance(1000, 1.0)
    assert r.fiber_recovery_pct == pytest.approx(83.74, abs=0.005)
    assert r.juice_recovery_pct == pytest.approx(56.12, abs=0.005)
    assert r.mill_power_kw == pytest.approx(0.6146, abs=1e-4)


def test_overall_mass_balance_closes():
    r = plant_balance(1375, 0.83)
    out = r.oversize_total_kg_per_h + r.juice_kg_per_h + r.fiber_product_kg_per_h + r.dryer_liquid_removed_kg_per_h
    assert out == pytest.approx(1375, rel=1e-12)


def test_matches_all_42_aspen_cases():
    df = load_aspen_csv()
    for _, a in df.iterrows():
        r = plant_balance(a.feed_total_kg_per_h, a.cut_size_mm)
        assert r.mill_power_kw == pytest.approx(a.mill_power_kw, rel=1e-6)
        assert r.oversize_solids_kg_per_h == pytest.approx(a.oversize_solids_kg_per_h, rel=1e-6)
        assert r.juice_kg_per_h == pytest.approx(a.juice_kg_per_h, rel=1e-6)
        assert r.fiber_product_kg_per_h == pytest.approx(a.fiber_kg_per_h, rel=1e-6)


def test_wider_screen_trades_juice_for_fiber():
    narrow, wide = plant_balance(1000, 0.5), plant_balance(1000, 1.5)
    assert wide.fiber_product_kg_per_h > narrow.fiber_product_kg_per_h
    assert wide.juice_kg_per_h < narrow.juice_kg_per_h


def test_invalid_inputs():
    with pytest.raises(ValueError):
        plant_balance(0, 1.0)
    with pytest.raises(ValueError):
        plant_balance(1000, 1.0, cake_moisture=0.99)   # cake would need more liquid than available
