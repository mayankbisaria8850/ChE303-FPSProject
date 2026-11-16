"""Hammer mill (Bond's law): hand calculation + verification against Aspen MILL_POWER."""
import math

import pytest

from calc import constants as C
from calc.aspen_data import load_aspen_csv
from calc.mill import (bond_power_kw, bond_specific_energy_kwh_per_ton, kick_specific_energy_kwh_per_ton,
                       mill_performance, rittinger_specific_energy_kwh_per_ton)

F80_UM = 5666.6667
P80_UM = 750.0


def test_bond_specific_energy_hand_calc():
    # W = 10 * 12 * (1/sqrt(750) - 1/sqrt(5666.67)) = 120 * (0.036515 - 0.013284) = 2.7877 kWh/ton
    hand = 120 * (1 / math.sqrt(750) - 1 / math.sqrt(5666.6667))
    assert hand == pytest.approx(2.7877, abs=1e-4)
    assert bond_specific_energy_kwh_per_ton(12, F80_UM, P80_UM) == pytest.approx(hand, rel=1e-9)


def test_bond_power_base_case_matches_aspen():
    # 200 kg/h solids = 0.220462 short ton/h -> P = 2.7877 * 0.220462 = 0.6146 kW (Aspen 0.614576843)
    p = bond_power_kw(200, 12, F80_UM, P80_UM, ton_basis="short")
    assert p == pytest.approx(0.614576843, rel=1e-6)


def test_metric_basis_is_9_percent_lower():
    short = bond_power_kw(200, 12, F80_UM, P80_UM, ton_basis="short")
    metric = bond_power_kw(200, 12, F80_UM, P80_UM, ton_basis="metric")
    assert short / metric == pytest.approx(1000 / 907.18474, rel=1e-9)
    assert metric == pytest.approx(0.5575, abs=1e-4)


def test_mill_power_matches_all_aspen_cases():
    df = load_aspen_csv()
    for feed, aspen_kw in df.groupby("feed_total_kg_per_h")["mill_power_kw"].first().items():
        assert mill_performance(feed).power_kw == pytest.approx(aspen_kw, rel=1e-6)


def test_power_scales_linearly_with_feed():
    p500 = mill_performance(500).power_kw
    p2000 = mill_performance(2000).power_kw
    assert p2000 / p500 == pytest.approx(4.0, rel=1e-12)
    assert mill_performance(1000).energy_kwh_per_tonne_wet_feed == pytest.approx(0.6146, abs=1e-4)


def test_reduction_ratio():
    assert mill_performance(1000).reduction_ratio == pytest.approx(7.556, abs=1e-3)


def test_three_laws_agree_at_calibration_point():
    for law in (kick_specific_energy_kwh_per_ton, rittinger_specific_energy_kwh_per_ton):
        assert law(12, 1000, 100) == pytest.approx(bond_specific_energy_kwh_per_ton(12, 1000, 100))


def test_invalid_inputs():
    with pytest.raises(ValueError):
        bond_specific_energy_kwh_per_ton(12, 500, 750)      # P80 > F80
    with pytest.raises(ValueError):
        bond_power_kw(200, 12, F80_UM, P80_UM, ton_basis="long")
    with pytest.raises(ValueError):
        bond_power_kw(-1, 12, F80_UM, P80_UM)
