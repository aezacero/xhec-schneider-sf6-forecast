import numpy as np
import pandas as pd
import pytest

from schneider_forecast.backtest import run_backtest
from schneider_forecast.bands import rw_vol_scaled, target_logs, vol_scaled_offsets
from schneider_forecast.total_cost import (
    BottomUpModel,
    add_totals,
    cost_lines,
    total_cost_history,
)

MONTHS = pd.date_range("2014-01-01", "2026-09-01", freq="MS")


def walk(seed: int, sd: float = 0.03) -> np.ndarray:
    return np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sd, len(MONTHS))))


def toy_data():
    """A product with 100 kg of steel (€/t) and 10 kg of plastic (index); stainless ends early."""
    prices = pd.DataFrame(
        {"L01": 800 * walk(0), "L02": 3000 * walk(1), "S11": 120 * walk(2, 0.01)},
        index=pd.DatetimeIndex(MONTHS, name="month"),
    )
    prices.loc[MONTHS[-1], "L02"] = np.nan
    catalog = pd.DataFrame(
        {
            "source": ["MEPS", "CRU", "Eurostat"],  # the real catalog has more columns
            "unit": ["EUR/t", "EUR/t", "Index 2021=100"],
            "gap_months": [0, 1, 0],
            "pub_lag": [1, 3, 2],
            "is_target": [True, True, True],
        },
        index=["L01", "L02", "S11"],
    )
    bom = pd.DataFrame(
        {
            "product_ref": ["P", "P", "P", "P"],
            "mass_kg": [100.0, 20.0, 6.0, 4.0],
            "price_series": ["L01", "L02", "S11", "S11"],
        }
    )
    return prices, catalog, bom


def test_cost_lines_convert_each_series_to_euro_per_kg():
    prices, catalog, bom = toy_data()
    lines = cost_lines(bom, prices, catalog, names={"P": "TOTAL_P"})
    w = lines.set_index("series")["eur_per_unit_of_price"]
    assert w["L01"] == pytest.approx(100 / 1000)  # 100 kg × €/t ÷ 1000
    s11_last = prices["S11"].dropna().iloc[-1]
    assert w["S11"] == pytest.approx(10 * 3.0 / s11_last)  # 10 kg at 3 €/kg at the last month


def test_total_cost_is_known_only_when_every_line_is():
    prices, catalog, bom = toy_data()
    lines = cost_lines(bom, prices, catalog, names={"P": "TOTAL_P"})
    total = total_cost_history(prices, lines)["TOTAL_P"]
    month = MONTHS[-2]
    w = lines.set_index("series")["eur_per_unit_of_price"]
    expected = sum(w[s] * prices.loc[month, s] for s in w.index)
    assert total[month] == pytest.approx(expected)
    assert np.isnan(total[MONTHS[-1]])  # stainless missing in the last month


def test_bottom_up_p50_is_the_cost_of_the_component_p50s():
    prices, catalog, bom = toy_data()
    lines = cost_lines(bom, prices, catalog, names={"P": "TOTAL_P"})
    history, _ = add_totals(prices, catalog, lines)
    origin = MONTHS[-1]
    model = BottomUpModel(lines, choose=lambda series, horizon: rw_vol_scaled)
    _, p50, _ = model.predict(history, "TOTAL_P", 3, origin)
    w = lines.set_index("series")["eur_per_unit_of_price"]
    expected = sum(w[s] * prices[s].dropna().iloc[-1] for s in w.index)
    assert p50 == pytest.approx(expected)


def test_joint_band_of_identical_materials_is_their_own_band():
    prices, catalog, bom = toy_data()
    prices["L02"] = prices["L01"] * 4  # stainless moves exactly like steel
    catalog.loc["L02", ["gap_months", "pub_lag"]] = [0, 1]
    bom = bom[bom["price_series"] != "S11"]
    lines = cost_lines(bom, prices, catalog, names={"P": "TOTAL_P"})
    history, _ = add_totals(prices, catalog, lines)
    origin = MONTHS[-1]
    model = BottomUpModel(lines, choose=lambda series, horizon: rw_vol_scaled)
    p10, p50, p90 = model.predict(history, "TOTAL_P", 6, origin)
    offsets = vol_scaled_offsets(target_logs(prices, "L01"), 6, halflife=3)  # band half-life
    assert np.log(p10 / p50) == pytest.approx(offsets[0])
    assert np.log(p90 / p50) == pytest.approx(offsets[2])


def test_top_down_and_bottom_up_run_in_the_harness_on_the_total():
    prices, catalog, bom = toy_data()
    lines = cost_lines(bom, prices, catalog, names={"P": "TOTAL_P"})
    data_prices, data_catalog = add_totals(prices, catalog, lines)
    assert data_catalog.loc["TOTAL_P", "pub_lag"] == 3  # the slowest line
    assert data_catalog.loc["TOTAL_P", "gap_months"] == 1
    flags = pd.DataFrame(columns=["month", "series_id", "issue", "treatment"])
    data = (data_prices, data_catalog, flags)
    kw = dict(targets=["TOTAL_P"], data=data, start="2025-06", strict=True, save=False)
    top = run_backtest(rw_vol_scaled, "top", track_co2=False, **kw)
    bottom = run_backtest(
        BottomUpModel(lines, choose=lambda s, h: rw_vol_scaled), "bottom", track_co2=False, **kw
    )
    assert len(top) == len(bottom) > 0
    assert (bottom["p10"] <= bottom["p50"]).all() and (bottom["p50"] <= bottom["p90"]).all()
