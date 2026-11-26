import numpy as np
import pandas as pd
import pytest

from schneider_forecast.bands import BAND_HALFLIFE
from schneider_forecast.config import HORIZONS
from schneider_forecast.p3_models import P3_TARGETS
from schneider_forecast.p3_selection import RANDOM_WALK, SELECTION, final_forecasts


def test_selection_covers_every_target_and_horizon():
    assert set(SELECTION) == {(t, h) for t in P3_TARGETS for h in HORIZONS}


def test_band_default_is_three_months():
    assert BAND_HALFLIFE == 3


def test_market_prices_use_the_random_walk():
    for target in ("D01", "S01", "D02", "S02", "S06", "S13"):
        for h in HORIZONS:
            assert SELECTION[(target, h)][0] == "random_walk"


def _data():
    rng = np.random.default_rng(0)
    months = pd.date_range(end="2026-09", periods=80, freq="MS")
    prices = pd.DataFrame({"A": 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 80)))}, index=months)
    catalog = pd.DataFrame({"unit": ["EUR/t"], "gap_months": [0], "pub_lag": [1]}, index=["A"])
    return prices, catalog


def test_final_forecasts_layout():
    selection = {("A", h): ("random_walk", RANDOM_WALK) for h in HORIZONS}
    out = final_forecasts(_data(), selection=selection)
    assert list(out["horizon_m"]) == list(HORIZONS)
    assert list(out["target_month"]) == ["2026-12", "2027-03", "2027-06"]
    assert (out["p10"] <= out["p50"]).all() and (out["p50"] <= out["p90"]).all()
    assert out["p50"].iloc[0] == pytest.approx(_data()[0]["A"].iloc[-1])
