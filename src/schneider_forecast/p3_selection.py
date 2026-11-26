"""Copper, aluminium, plastics, epoxy, EUR/USD: one model per target × horizon.

Rule: the blend replaces the random walk for a target × horizon only if
its P50 is no worse than the random walk in 2020–22 AND in 2023–26 on the strict backtest (only
data already published at each origin). Otherwise the random walk (simpler model) is kept.

| Target | +3 | +6 | +9 |
|---|---|---|---|
| EPX_RESIN, S08 | blend, own band | blend, volatility band | random walk |
| S07 | blend, own band | random walk | random walk |
| S11 | blend, own band | blend, volatility band | random walk |
| D01, S01, D02, S02, S06, S13 | random walk | random walk | random walk |

Blend = geometric mean of `ets_damped` and `chronos2` with drivers. Random walk = last value with
the volatility-scaled band (half-life `BAND_HALFLIFE` = 3). Chronos-2 needs the optional extra:
`uv sync --extra pretrained` (local CPU, no data leaves the PC).

Run: `uv run python -m schneider_forecast.p3_selection` writes the forecasts at origin 2026-09 to
`outputs/forecasts/p3_forecasts_202609.csv` and the strict and main backtests of the selection to
`outputs/backtest/p3_selected*.csv` (one row per origin × target × horizon, for the index backtest).
"""

from functools import partial

import pandas as pd

from schneider_forecast.backtest import available_at, load_data, run_backtest
from schneider_forecast.bands import BAND_HALFLIFE, rw_vol_scaled, with_vol_bands
from schneider_forecast.config import FORECASTS, HORIZONS
from schneider_forecast.p3_models import P3_TARGETS, blend_models, chronos2, ets_damped

RANDOM_WALK = partial(rw_vol_scaled, halflife=BAND_HALFLIFE)
BLEND = blend_models(ets_damped, partial(chronos2, covariates=True))
BLEND_VOL_BAND = with_vol_bands(BLEND, halflife=BAND_HALFLIFE)

# target × horizon cells where the blend passed the rule (strict run, both periods)
BLEND_CELLS = {("EPX_RESIN", 3), ("S08", 3), ("S07", 3), ("S11", 3)}
BLEND_VOL_CELLS = {("EPX_RESIN", 6), ("S08", 6), ("S11", 6)}


def _selection() -> dict[tuple[str, int], tuple[str, object]]:
    chosen = {(t, h): ("random_walk", RANDOM_WALK) for t in P3_TARGETS for h in HORIZONS}
    for cell in BLEND_CELLS:
        chosen[cell] = ("blend_ets_chronos2", BLEND)
    for cell in BLEND_VOL_CELLS:
        chosen[cell] = ("blend_ets_chronos2_volband", BLEND_VOL_BAND)
    return chosen


SELECTION = _selection()


def p3_selected(history, target, horizon, origin) -> tuple[float, float, float]:
    """Harness model that runs, for each target × horizon, the model chosen for it."""
    return SELECTION[(target, horizon)][1](history, target, horizon, origin)


def final_forecasts(
    data: tuple[pd.DataFrame, pd.DataFrame] | None = None,
    selection: dict = SELECTION,
    origin: str = "2026-09",
) -> pd.DataFrame:
    """Forecasts at the origin, as on the real date (each series cut by its gap), one row per
    target × horizon, in the submission columns (same layout as `p2_selection.final_forecasts`)."""
    prices, catalog = data if data is not None else load_data()[:2]
    origin_ts = pd.Timestamp(origin)
    history = available_at(prices, catalog, origin_ts)
    rows = []
    for (target, horizon), (name, model) in sorted(selection.items()):
        p10, p50, p90 = model(history.copy(), target, horizon, origin_ts)
        if not 0 < p10 <= p50 <= p90:
            raise ValueError(f"{target} +{horizon}: invalid quantiles {(p10, p50, p90)}")
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
    path = FORECASTS / "p3_forecasts_202609.csv"
    out.to_csv(path, index=False)
    print(f"{len(out)} forecasts → {path}")
    for strict in (True, False):
        run_backtest(p3_selected, "p3_selected", targets=list(P3_TARGETS), strict=strict)


if __name__ == "__main__":
    main()
