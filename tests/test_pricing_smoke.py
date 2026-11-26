"""Smoke test of the pricing chain on the real data (skipped where the data is absent, e.g. CI).

The unit tests use small made-up tables; this one runs the real loaders and the team's
Sep 2026 forecasts end to end and checks the structure of what reaches the submission.
"""

import pandas as pd
import pytest

from schneider_forecast import pricing
from schneider_forecast.config import BOM_CLEAN, HORIZONS, PRICES_WIDE, SERIES_CATALOG

NEEDED = (PRICES_WIDE, SERIES_CATALOG, BOM_CLEAN, *pricing.TEAM_FORECAST_FILES)
pytestmark = pytest.mark.skipif(
    not all(path.exists() for path in NEEDED), reason="needs the real data and team forecasts"
)
# priced raw-material cost per unit in eda_findings.md §8 (v1 BOM)
EDA_COST = {"AirSeT": 975.0, "RM6": 900.0}


def test_pricing_chain_on_real_data_gives_six_valid_bom_rows():
    """The real chain must give one index row per product × horizon, ordered quantiles."""
    prices = pd.read_csv(PRICES_WIDE, parse_dates=["month"], index_col="month")
    bom = pd.read_csv(BOM_CLEAN)
    lines = pricing.cost_weights(bom, prices)
    costs = lines.groupby("product")["cost"].sum()
    for product, eda in EDA_COST.items():
        assert costs[product] == pytest.approx(eda, rel=0.01)

    forecasts = pricing.load_forecasts(prices, sorted(lines["series"].unique()))
    assert (forecasts["model_name"] != "placeholder_rw_vol").all()
    draws = {
        h: pricing.simulate_index(lines, forecasts, prices, h, n_draws=2_000) for h in HORIZONS
    }
    rows = pricing.bom_index_rows(pricing.index_scenarios(draws), lines)

    assert len(rows) == 2 * len(HORIZONS)
    assert ((rows["p10"] <= rows["p50"]) & (rows["p50"] <= rows["p90"])).all()
    assert rows["p50"].between(80, 125).all()  # a 9-month middle case far outside is a bug
