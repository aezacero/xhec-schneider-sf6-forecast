"""Steel and stainless: one model per target × horizon (docs/forecasting_steel.md, Final selection).

Chosen on the strict backtest: a model replaces the random walk only if its P50 is no worse in
2020–22 and in 2023–26; the simpler model wins a tie. Every model uses the shared volatility-scaled
band with half-life 3 (`features.BAND_HALFLIFE`).

| Target | +3 | +6 | +9 |
|---|---|---|---|
| L01, L03 | `meps_pooled` | `meps_pooled` | `meps_pooled` 3-month P50 held |
| S09, S10 | `steel_ppi_lead` | `steel_ppi_lead` | `steel_ppi_lead` 6-month P50 held |
| L02 | Chronos-2 | Chronos-2 | Chronos-2 |
| S05 | random walk | Chronos-2 | Chronos-2 |
| S03, S04, S12 | random walk | random walk | random walk |

Chronos-2 needs the optional extra: `uv sync --extra pretrained` (`p3_models`, local CPU).

Run: `uv run python -m schneider_forecast.p2_selection` writes the forecasts at origin 2026-09 to
`outputs/forecasts/p2_forecasts_202609.csv` and the strict backtest of the selection to
`outputs/backtest/p2_selected_strict.csv` (errors per origin, used by the index backtest).
Selection uses the strict run only.
"""

from functools import partial

import numpy as np
import pandas as pd

from schneider_forecast.backtest import available_at, load_data, run_backtest
from schneider_forecast.bands import rw_vol_scaled, target_logs, vol_scaled_offsets, with_vol_bands
from schneider_forecast.config import FORECASTS, HORIZONS
from schneider_forecast.features import BAND_HALFLIFE
from schneider_forecast.p2_models import MODELS, P2_TARGETS
from schneider_forecast.p3_models import chronos2


def call_model(model, history, target, horizon, origin) -> tuple[float, float, float]:
    """Run a harness model given as a function or as an object with fit / predict."""
    if hasattr(model, "predict"):
        model.fit(history, target, horizon, origin)
        return model.predict(history, target, horizon, origin)
    return model(history, target, horizon, origin)


class HeldForecast:
    """P50 of `model` at the shorter horizon `use` (the move happens by then, then the price
    stays), with the shared band of the horizon actually asked around it."""

    def __init__(self, model, use: int) -> None:
        self.model, self.use = model, use

    def fit(self, history, target, horizon, origin) -> "HeldForecast":
        return self

    def predict(self, history, target, horizon, origin) -> tuple[float, float, float]:
        p50 = call_model(self.model, history, target, self.use, origin)[1]
        logs = target_logs(history, target)
        span = (origin.to_period("M") - logs.index[-1].to_period("M")).n + horizon
        offsets = vol_scaled_offsets(logs, span, BAND_HALFLIFE)
        return float(p50 * np.exp(offsets[0])), float(p50), float(p50 * np.exp(offsets[2]))


RANDOM_WALK = partial(rw_vol_scaled, halflife=BAND_HALFLIFE)
CHRONOS2 = with_vol_bands(partial(chronos2, covariates=False), halflife=BAND_HALFLIFE)


def _selection() -> dict[tuple[str, int], tuple[str, object]]:
    rw = ("random_walk", RANDOM_WALK)
    chosen = {(t, h): rw for t in P2_TARGETS for h in HORIZONS}
    for t in ("L01", "L03"):
        chosen[(t, 3)] = chosen[(t, 6)] = ("meps_pooled", MODELS["meps_pooled"])
        chosen[(t, 9)] = ("meps_pooled_3m_held", HeldForecast(MODELS["meps_pooled"], use=3))
    for t in ("S09", "S10"):
        chosen[(t, 3)] = chosen[(t, 6)] = ("steel_ppi_lead", MODELS["steel_ppi_lead"])
        chosen[(t, 9)] = ("steel_ppi_lead_6m_held", HeldForecast(MODELS["steel_ppi_lead"], use=6))
    for h in HORIZONS:
        chosen[("L02", h)] = ("chronos2", CHRONOS2)
    chosen[("S05", 6)] = chosen[("S05", 9)] = ("chronos2", CHRONOS2)
    return chosen


SELECTION = _selection()


class P2Selected:
    """Harness model that runs, for each target × horizon, the model chosen for it."""

    def __init__(self, selection: dict = SELECTION) -> None:
        self.selection = selection

    def _model(self, target, horizon):
        return self.selection[(target, horizon)][1]

    def fit(self, history, target, horizon, origin) -> "P2Selected":
        model = self._model(target, horizon)
        if hasattr(model, "fit"):
            model.fit(history, target, horizon, origin)
        return self

    def predict(self, history, target, horizon, origin) -> tuple[float, float, float]:
        model = self._model(target, horizon)
        if hasattr(model, "predict"):
            return model.predict(history, target, horizon, origin)
        return model(history, target, horizon, origin)


def final_forecasts(
    data: tuple[pd.DataFrame, pd.DataFrame] | None = None,
    selection: dict = SELECTION,
    origin: str = "2026-09",
    horizons: tuple[int, ...] = HORIZONS,
) -> pd.DataFrame:
    """Forecasts at the origin, as on the real date (each series cut by its gap), one row per
    target × horizon, in the submission columns."""
    prices, catalog = data if data is not None else load_data()[:2]
    origin_ts = pd.Timestamp(origin)
    history = available_at(prices, catalog, origin_ts)
    rows = []
    for (target, horizon), (name, model) in sorted(selection.items()):
        if horizon not in horizons:
            continue
        p10, p50, p90 = call_model(model, history.copy(), target, horizon, origin_ts)
        if not p10 <= p50 <= p90:
            raise ValueError(f"{target} +{horizon}: quantiles cross")
        rows.append(
            {
                "target_type": "material",
                "target_id": target,
                "origin_month": f"{origin_ts:%Y-%m}",
                "horizon_m": horizon,
                "target_month": f"{origin_ts + pd.DateOffset(months=horizon):%Y-%m}",
                "unit": catalog.loc[target, "unit"],
                "p10": p10,
                "p50": p50,
                "p90": p90,
                "model_name": name,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    FORECASTS.mkdir(parents=True, exist_ok=True)
    out = final_forecasts()
    path = FORECASTS / "p2_forecasts_202609.csv"
    out.to_csv(path, index=False)
    print(f"{len(out)} forecasts → {path}")
    run_backtest(P2Selected(), "p2_selected", targets=list(P2_TARGETS), strict=True)


if __name__ == "__main__":
    main()
