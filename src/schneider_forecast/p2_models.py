"""Steel and stainless models (docs/forecasting_steel.md §2).

One small linear model of the P50, pooled over related series, with the shared
volatility-scaled bands around it (`bands.vol_scaled_offsets`):

- `meps_pooled` (L01, L03): own momentum + steel season, trained on the 8 MEPS coil prices together
  (they move as one, EDA §6), so the model has 8× more rows than one series alone.
- `steel_ppi_lead` (S09, S10): own momentum + the MEPS coil price that leads each index (EDA §6).
  MEPS is published one month before the indices, so in real time the driver is known further
  ahead: the driver's newest months are used.
- `stainless_drivers` (L02): own momentum + nickel (S03) and EUR/USD (S06), both known before L02.

Every change is in volatility units (log change ÷ EWMA volatility × √months), the model has no
intercept: with all coefficients at zero it is the random walk. P50 = last value × exp(z ×
volatility × √span). With fewer than `min_rows` training rows (early origins: S09, S10, S03, S06
start in 2016-11) the P50 falls back to the last value, as `p3_models.driver_qr` does.

Nickel, iron ore, zinc and US steel PPI (S03, S04, S05, S12) get no model of their own: no robust
driver was found (EDA §6); they are forecast by the shared models.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import QuantileRegressor

from schneider_forecast.bands import ewma_vol, target_logs, vol_scaled_offsets
from schneider_forecast.features import BAND_HALFLIFE, HALFLIFE, _season, clean_series
from schneider_forecast.pooled import _span

P2_TARGETS = ("L01", "L03", "L02", "S09", "S10", "S12", "S03", "S04", "S05")
MEPS = (
    "L01",  # CR coil, Germany
    "L03",  # HDG coil, Germany
    "MEPS_DE_HR",
    "MEPS_DE_EG",
    "MEPS_FR_HR",
    "MEPS_FR_CR",
    "MEPS_FR_HDG",
    "MEPS_FR_EG",
)


def _logs_vol(history: pd.DataFrame, name: str) -> tuple[pd.Series, pd.Series]:
    logs = np.log(clean_series(history, name))
    return logs, ewma_vol(logs, HALFLIFE)


def _months(a: pd.Timestamp, b: pd.Timestamp) -> int:
    return (b.to_period("M") - a.to_period("M")).n


def pair_features(
    history: pd.DataFrame, series: str, drivers: tuple[str, ...], steps: int, season: bool = False
) -> pd.DataFrame:
    """Features and target `y` for one series, one row per observed month.

    Driver j's momentum (`drv{j}_mom_1`, `drv{j}_mom_3`) is taken `lead` months after the row's
    month, where `lead` = months the driver's data runs past the series' data today (negative when
    the driver is published later than the series).
    """
    logs, vol = _logs_vol(history, series)
    f = pd.DataFrame(index=logs.index)
    for k in (1, 3):
        f[f"mom_{k}"] = (logs - logs.shift(k)) / (vol * np.sqrt(k))
    if season:
        f["season"] = _season(logs.index, steps)
    for j, name in enumerate(drivers):
        d_logs, d_vol = _logs_vol(history, name)
        lead = _months(logs.index[-1], d_logs.index[-1])
        for k in (1, 3):
            mom = (d_logs - d_logs.shift(k)) / (d_vol * np.sqrt(k))
            # move the dates, not the values: works whether the driver ends after or before
            f[f"drv{j}_mom_{k}"] = mom.shift(-lead, freq="MS").reindex(f.index)
    f["vol"] = vol
    f["y"] = (logs.shift(-steps) - logs) / (vol * np.sqrt(steps))
    return f


class PooledLinearModel:
    """Median regression (L1 penalty) of the future change, pooled over `pool`.

    `pool` maps each series to its drivers (same number of drivers for every series). Harness
    interface: `fit` / `predict(history, target, horizon, origin)`; the fit is shared by all
    targets of the pool through a class-level cache.
    """

    _cache: dict = {}

    def __init__(
        self,
        pool: dict[str, tuple[str, ...]],
        season: bool = False,
        alpha: float = 0.005,
        min_rows: int = 36,
        own_lags: tuple[int, ...] = (1, 3),
        driver_lags: tuple[int, ...] = (1, 3),
    ) -> None:
        if len({len(d) for d in pool.values()}) != 1:
            raise ValueError("every series in the pool needs the same number of drivers")
        self.pool, self.season, self.alpha, self.min_rows = dict(pool), season, alpha, min_rows
        n_drivers = len(next(iter(pool.values())))
        own = [f"mom_{k}" for k in own_lags]
        drv = [f"drv{j}_mom_{k}" for j in range(n_drivers) for k in driver_lags]
        self.features = [*own, *(["season"] if season else []), *drv]

    def _fitted(self, history: pd.DataFrame, origin: pd.Timestamp, span: int):
        members = [s for s in self.pool if s in history.columns]
        used = sorted({*members, *(d for s in members for d in self.pool[s])})
        fingerprint = float(np.nansum(history[used].to_numpy()))  # main vs strict run differ
        key = (
            origin,
            span,
            tuple(self.pool.items()),
            tuple(self.features),
            self.alpha,
            fingerprint,
        )
        cache = PooledLinearModel._cache
        if key in cache:
            return cache[key]
        if any(k[0] != origin for k in cache):
            cache.clear()  # the harness moves forward one origin at a time
        frames = {s: pair_features(history, s, self.pool[s], span, self.season) for s in members}
        train = pd.concat(frames.values()).dropna(subset=[*self.features, "y"])
        model = None  # too few rows: random walk
        if len(train) >= self.min_rows:
            model = QuantileRegressor(
                quantile=0.5, alpha=self.alpha, fit_intercept=False, solver="highs"
            ).fit(train[self.features], train["y"])
        cache[key] = (frames, model)
        return cache[key]

    def _check(self, target: str) -> None:
        if target not in self.pool:
            raise ValueError(f"{target} is not in this model's pool {list(self.pool)}")

    def fit(self, history, target, horizon, origin) -> "PooledLinearModel":
        self._check(target)
        self._fitted(history, origin, _span(history, target, horizon, origin))
        return self

    def predict(self, history, target, horizon, origin) -> tuple[float, float, float]:
        self._check(target)
        span = _span(history, target, horizon, origin)
        frames, model = self._fitted(history, origin, span)
        last = float(clean_series(history, target).iloc[-1])
        p50 = last
        if model is not None:
            row = frames[target].iloc[[-1]]
            if row[self.features].isna().any(axis=None):
                raise ValueError(f"{target}: features missing at {row.index[0]:%Y-%m}")
            z = float(model.predict(row[self.features])[0])
            p50 = last * np.exp(z * float(row["vol"].iloc[0]) * np.sqrt(span))
        offsets = vol_scaled_offsets(target_logs(history, target), span, BAND_HALFLIFE)
        p10, _, p90 = p50 * np.exp(offsets)
        return float(p10), float(p50), float(p90)


# Features kept by the robust-driver rule (same sign before and after 2020):
# 3-month momentum flips sign for MEPS steel; the driver's 3-month change flips for S09 / S10.
MODELS = {
    "meps_pooled": PooledLinearModel({s: () for s in MEPS}, season=True, own_lags=(1,)),
    "steel_ppi_lead": PooledLinearModel({"S09": ("L01",), "S10": ("L03",)}, driver_lags=(1,)),
    # tested and rejected: loses to the random walk, most signs flip after 2020
    "stainless_drivers": PooledLinearModel({"L02": ("S03", "S06")}),
}
MODEL_TARGETS = {
    "meps_pooled": ("L01", "L03"),
    "steel_ppi_lead": ("S09", "S10"),
    "stainless_drivers": ("L02",),
}
