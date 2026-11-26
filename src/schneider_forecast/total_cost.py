"""Total raw-material cost per product: top-down vs bottom-up forecasts (forecasting_steel.md).

The total cost of a product at month t is Σ kg × price per kg over its priced BOM lines (v1 BOM,
`bom_clean.csv`). Only the masses are fixed; prices are those of month t, so the history uses no
later prices. €/t series are divided by 1,000; plastics follow the S11 index from 3 €/kg at the
last month (eda_findings.md §8, as in the cost index). Lines without a price series (AirSeT
"Other", RM6 brass and remainder) are left out, as in the cost index.

- **Top-down:** forecast the total-cost series itself with any harness model. `add_totals` adds the
  totals to the price table and catalog (publication lag and gap of the slowest line), so the
  harness cuts them like any series.
- **Bottom-up:** `BottomUpModel` forecasts each material with its own model and adds the costs.
  P50 = Σ kg × price-per-kg of each material's P50. The band is joint: past months are resampled
  as a whole (all materials together, EDA §6), each material's move in volatility units scaled to
  today's volatility, as `bands.vol_scaled_offsets` does for one series.
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from schneider_forecast.bands import MIN_CHANGES, ewma_vol, target_logs
from schneider_forecast.config import QUANTILES
from schneider_forecast.features import BAND_HALFLIFE

PLASTIC_EUR_PER_KG = 3.0  # eda_findings.md §8, price of plastics and epoxy at the origin
PRODUCTS = {"RMAirSeT IIQ 24kV IEC": "TOTAL_AIRSET", "RM6_NE_IQI_433520": "TOTAL_RM6"}


def cost_lines(
    bom: pd.DataFrame, prices: pd.DataFrame, catalog: pd.DataFrame, names: dict = PRODUCTS
) -> pd.DataFrame:
    """One row per product × price series: kg and € per unit of the series' price."""
    priced = bom.dropna(subset=["price_series"])
    priced = priced[priced["product_ref"].isin(names)]
    lines = priced.groupby(["product_ref", "price_series"], as_index=False)["mass_kg"].sum()
    lines = lines.rename(columns={"price_series": "series", "mass_kg": "kg"})
    lines.insert(0, "total", lines.pop("product_ref").map(names))

    def factor(row) -> float:
        unit = str(catalog.loc[row["series"], "unit"])
        if unit.endswith("/t"):
            return row["kg"] / 1000
        if unit.startswith("Index"):
            return row["kg"] * PLASTIC_EUR_PER_KG / prices[row["series"]].dropna().iloc[-1]
        raise ValueError(f"{row['series']}: no € per kg conversion for unit {unit!r}")

    lines["eur_per_unit_of_price"] = lines.apply(factor, axis=1)
    return lines


def total_cost_history(prices: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """Total cost per product and month; NaN where any line has no price."""
    out = {}
    for total, rows in lines.groupby("total"):
        w = rows.set_index("series")["eur_per_unit_of_price"]
        out[total] = prices[w.index].mul(w).sum(axis=1, min_count=len(w))
    return pd.DataFrame(out, index=prices.index)


def add_totals(
    prices: pd.DataFrame, catalog: pd.DataFrame, lines: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Price table and catalog with the totals added as targets (slowest line's lags)."""
    totals = total_cost_history(prices, lines)
    rows = {}
    for total, group in lines.groupby("total"):
        parts = catalog.loc[group["series"]]
        rows[total] = {
            "unit": "EUR per unit",
            "gap_months": int(parts["gap_months"].max()),
            "pub_lag": int(parts["pub_lag"].max()),
            "is_target": True,
        }
    new = pd.DataFrame(rows).T.astype({"gap_months": int, "pub_lag": int, "is_target": bool})
    return prices.join(totals), pd.concat([catalog, new])


def _call(model, history, target, horizon, origin) -> tuple[float, float, float]:
    if hasattr(model, "predict"):
        model.fit(history, target, horizon, origin)
        return model.predict(history, target, horizon, origin)
    return model(history, target, horizon, origin)


def _standard_moves(history: pd.DataFrame, series: str, horizon: int, origin: pd.Timestamp):
    """Past moves of `series` over its forecast span in volatility units; today's volatility."""
    logs = target_logs(history, series)
    steps = (origin.to_period("M") - logs.index[-1].to_period("M")).n + horizon
    vol = ewma_vol(logs, BAND_HALFLIFE)
    z = ((logs.shift(-steps) - logs) / vol).dropna()
    return z, float(vol.dropna().iloc[-1])


class BottomUpModel:
    """Forecast a product's total cost from one forecast per material.

    `choose(series, horizon)` returns the harness model used for that material and horizon.
    With fewer than MIN_CHANGES months where every material has a past move (early origins), the
    band assumes the materials move fully together: Σ cost of the material P10s / P90s.
    """

    def __init__(self, lines: pd.DataFrame, choose: Callable) -> None:
        self.lines, self.choose = lines, choose

    def fit(self, history, target, horizon, origin) -> "BottomUpModel":
        return self

    def predict(self, history, target, horizon, origin) -> tuple[float, float, float]:
        rows = self.lines[self.lines["total"] == target]
        if rows.empty:
            raise ValueError(f"{target} is not a product total in these cost lines")
        w = rows.set_index("series")["eur_per_unit_of_price"]
        q = pd.DataFrame(
            {s: _call(self.choose(s, horizon), history, s, horizon, origin) for s in w.index},
            index=["p10", "p50", "p90"],
        )
        p50 = float((q.loc["p50"] * w).sum())
        moves = {s: _standard_moves(history, s, horizon, origin) for s in w.index}
        z = pd.DataFrame({s: m[0] for s, m in moves.items()}).dropna()
        if len(z) < MIN_CHANGES:
            return float((q.loc["p10"] * w).sum()), p50, float((q.loc["p90"] * w).sum())
        vol = pd.Series({s: m[1] for s, m in moves.items()})
        sims = (np.exp((z - z.median()) * vol) * q.loc["p50"] * w).sum(axis=1)
        lo, _, hi = np.quantile(np.log(sims / p50), QUANTILES)
        return float(p50 * np.exp(min(lo, 0.0))), p50, float(p50 * np.exp(max(hi, 0.0)))
