"""Pooled model: one linear quantile regression per horizon, trained on all materials at once.

For each forecast span (horizon + the target's gap to the origin) the model stacks the features
of every series (`features.build_dataset`) and fits P10, P50 and P90 of the future log change in
volatility units with an L1 penalty. A forecast is the target's last value × exp(quantile ×
volatility × √span).

`bands="vol"` (default) keeps the model's P50 and takes P10 / P90 from the shared
volatility-scaled bands (`bands.vol_scaled_offsets`); `bands="own"` uses the model's own P10 / P90.
Known data errors are handled as in `features.clean_series`.

Use with the backtest harness: `run_backtest(PooledQuantileModel(), name="pooled_qr")`.
The harness keeps one copy of the model per target × horizon; the fit is shared through a
class-level cache, so each origin × span is fitted once for all targets.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import QuantileRegressor

from schneider_forecast.bands import target_logs, vol_scaled_offsets
from schneider_forecast.config import QUANTILES
from schneider_forecast.features import (
    BAND_HALFLIFE,
    FEATURES,
    GROUPS,
    build_dataset,
    clean_series,
)


def _span(history: pd.DataFrame, target: str, horizon: int, origin: pd.Timestamp) -> int:
    """Months from the target's last valid value (errors removed) to origin + horizon."""
    last = clean_series(history, target).index[-1]
    return horizon + (origin.year - last.year) * 12 + origin.month - last.month


class PooledQuantileModel:
    _cache: dict = {}

    def __init__(
        self,
        series: list[str] | None = None,
        alpha: float = 0.005,
        quantiles: tuple[float, ...] = QUANTILES,
        min_rows: int = 200,
        bands: str = "vol",
    ) -> None:
        if bands not in ("vol", "own"):
            raise ValueError(f"bands must be 'vol' or 'own', not {bands!r}")
        self.series, self.alpha, self.min_rows, self.bands = series, alpha, min_rows, bands
        self.quantiles = (0.5,) if bands == "vol" else tuple(quantiles)  # only P50 is needed

    def _pool(self, history: pd.DataFrame) -> list[str]:
        if self.series is not None:
            return list(self.series)
        return [s for s in GROUPS if s in history.columns]

    def _fitted(self, history: pd.DataFrame, origin: pd.Timestamp, span: int):
        pool = self._pool(history)
        fingerprint = float(np.nansum(history[pool].to_numpy()))  # main vs strict run differ
        key = (origin, span, self.alpha, tuple(pool), self.quantiles, fingerprint)
        cache = PooledQuantileModel._cache
        if key in cache:
            return cache[key]
        if any(k[0] != origin for k in cache):
            cache.clear()  # the harness moves forward one origin at a time
        data = build_dataset(history, pool, span)
        train = data.dropna(subset=[*FEATURES, "y"])
        if len(train) < self.min_rows:
            raise ValueError(f"only {len(train)} training rows, need {self.min_rows}")
        models = {
            q: QuantileRegressor(
                quantile=q, alpha=self.alpha, fit_intercept=False, solver="highs"
            ).fit(train[FEATURES], train["y"])
            for q in self.quantiles
        }
        cache[key] = (data, models)
        return cache[key]

    def fit(self, history, target, horizon, origin) -> "PooledQuantileModel":
        self._fitted(history, origin, _span(history, target, horizon, origin))
        return self

    def predict(self, history, target, horizon, origin) -> tuple[float, float, float]:
        span = _span(history, target, horizon, origin)
        data, models = self._fitted(history, origin, span)
        row = data[data["series"] == target].iloc[[-1]]
        if row[FEATURES].isna().any(axis=None):
            raise ValueError(f"{target}: features missing at {row['month'].iloc[0]:%Y-%m}")
        z = np.sort([models[q].predict(row[FEATURES])[0] for q in self.quantiles])
        scale = float(row["vol"].iloc[0]) * np.sqrt(span)
        last = float(clean_series(history, target).iloc[-1])
        if self.bands == "vol":
            p50 = last * np.exp(z[0] * scale)
            offsets = vol_scaled_offsets(target_logs(history, target), span, BAND_HALFLIFE)
            p10, _, p90 = p50 * np.exp(offsets)
        else:
            p10, p50, p90 = last * np.exp(z * scale)
        return float(p10), float(p50), float(p90)
