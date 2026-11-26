"""Models for copper, aluminium, plastics, epoxy, EUR/USD (docs/forecasting_other.md).

Every model follows the harness interface:
    model(history, target, horizon, origin) -> (p10, p50, p90) in the target's own unit.
`history` is already cut by the harness; the last value of a target can be older than the origin,
so each model forecasts `steps` months from that last value to origin + horizon.
"""

import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from schneider_forecast.bands import target_logs
from schneider_forecast.config import QUANTILES

P3_TARGETS = ("D01", "S01", "S07", "D02", "S02", "S08", "S11", "S13", "EPX_RESIN", "S06")


def known_logs(history: pd.DataFrame, target: str) -> pd.Series:
    """Monthly log values, first to last valid month; known data errors are gaps (bands.py)."""
    return target_logs(history, target)


def filled(logs: pd.Series) -> pd.Series:
    """Gaps inside the series filled by straight-line interpolation (for ETS / Chronos input)."""
    return logs.interpolate()


def steps_to(last: pd.Timestamp, origin: pd.Timestamp, horizon: int) -> int:
    """Months from the last observed value to the target month (origin + horizon)."""
    return (origin.to_period("M") - last.to_period("M")).n + horizon


def past_changes(logs: pd.Series, steps: int) -> pd.Series:
    """Every past `steps`-month log change of a monthly series."""
    return (logs - logs.shift(steps)).dropna()


def change_quantiles(logs: pd.Series, steps: int) -> np.ndarray:
    """P10, P50, P90 of past `steps`-month log changes."""
    changes = past_changes(logs, steps)
    if len(changes) < 12:
        raise ValueError(f"only {len(changes)} past {steps}-month changes")
    return np.quantile(changes, QUANTILES)


def ets_damped(
    history: pd.DataFrame, target: str, horizon: int, origin: pd.Timestamp
) -> tuple[float, float, float]:
    """P50 = damped-trend exponential smoothing on log values; band = past change spread.

    The band keeps the shape of past `steps`-month changes (P10 − P50, P90 − P50) and is centred
    on the model's P50, so only the centre differs from the random walk.
    """
    logs = known_logs(history, target)
    steps = steps_to(logs.index[-1], origin, horizon)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # convergence chatter on short or flat windows
        fit = ExponentialSmoothing(
            filled(logs).to_numpy(),
            trend="add",
            damped_trend=True,
            initialization_method="estimated",
        ).fit()
    centre = float(fit.forecast(steps)[-1])
    q10, q50, q90 = change_quantiles(logs, steps)
    return tuple(float(np.exp(centre + q - q50)) for q in (q10, q50, q90))


# kept drivers per target (eda_findings.md §6); log-change drivers
_ENERGY = ("E01", "ED02", "E22")
DRIVERS = {
    "S11": _ENERGY,
    "S13": _ENERGY,
    "EPX_RESIN": _ENERGY,
    "D01": ("S06",),
    "S01": ("S06",),
    "S07": ("S06",),
    "D02": ("S06",),
    "S02": ("S06",),
    "S08": ("S06",),
}
# level drivers: can be negative, so used as levels, not log changes
MIN_TRAIN_ROWS = 36  # below this, driver_qr falls back to the random walk
LEVEL_DRIVERS = {"D02": ("LME_AL_SPREAD",), "S02": ("LME_AL_SPREAD",), "S08": ("LME_AL_SPREAD",)}


def driver_features(history: pd.DataFrame, target: str) -> pd.DataFrame:
    """Features known at month t: own and driver log changes over 1 / 3 / 6 months."""
    logs = np.log(history[target])
    feats = {f"own_{k}": logs - logs.shift(k) for k in (1, 3, 6)}
    for driver in DRIVERS.get(target, ()):
        d = np.log(history[driver].ffill())  # ragged edge: carry the last published value
        feats |= {f"{driver}_{k}": d - d.shift(k) for k in (1, 3)}
    for driver in LEVEL_DRIVERS.get(target, ()):
        feats[f"{driver}_lvl"] = history[driver].ffill()
    return pd.DataFrame(feats)


def driver_qr(
    history: pd.DataFrame,
    target: str,
    horizon: int,
    origin: pd.Timestamp,
    alpha: float = 0.002,
) -> tuple[float, float, float]:
    """Direct quantile regression of the `steps`-month log change on own and driver changes.

    One linear model per quantile, L1 penalty `alpha` (it drops weak drivers), features
    standardised on the training rows only. Rows use pairs (t, t + steps) both observed by the
    last known month, so nothing after the origin is used.
    """
    from sklearn.linear_model import QuantileRegressor

    logs = known_logs(history, target)
    last = logs.index[-1]
    steps = steps_to(last, origin, horizon)
    clean = history.assign(**{target: np.exp(logs).reindex(history.index)})
    feats = driver_features(clean.loc[:last], target)
    y = logs.shift(-steps) - logs
    train = feats.join(y.rename("y")).dropna()
    x_now = feats.loc[[last]]
    if len(train) < MIN_TRAIN_ROWS or x_now.isna().any(axis=None):
        # too little history (early origins, ~2016 starts): last value + past-change spread
        return tuple(float(np.exp(logs.iloc[-1] + q)) for q in change_quantiles(logs, steps))
    mean, std = train.drop(columns="y").mean(), train.drop(columns="y").std().replace(0, 1)
    x_train = ((train.drop(columns="y") - mean) / std).to_numpy()
    x_new = ((x_now - mean) / std).to_numpy()
    preds = [
        QuantileRegressor(quantile=q, alpha=alpha, solver="highs")
        .fit(x_train, train["y"].to_numpy())
        .predict(x_new)[0]
        for q in QUANTILES
    ]
    preds = np.sort(preds)  # quantile models fitted separately can cross
    return tuple(float(np.exp(logs.iloc[-1] + p)) for p in preds)


_CHRONOS: dict = {}  # loaded pipelines and cached forecasts (one forecast serves all horizons)


def chronos_bolt(
    history: pd.DataFrame,
    target: str,
    horizon: int,
    origin: pd.Timestamp,
    size: str = "small",
) -> tuple[float, float, float]:
    """Zero-shot Chronos-Bolt (Amazon, Apache-2.0), run locally on CPU: no data leaves the PC.

    Needs the optional extra: `uv sync --extra pretrained`. Weights download once from Hugging
    Face (`amazon/chronos-bolt-{size}`). Context = every observed value of the target up to its
    last month; the model returns P10 / P50 / P90 directly, in the target's unit.
    """
    import torch
    from chronos import BaseChronosPipeline

    observed = np.exp(filled(known_logs(history, target)))
    steps = steps_to(observed.index[-1], origin, horizon)
    key = (size, target, observed.index[-1], len(observed), float(observed.iloc[-1]))
    if key not in _CHRONOS:
        if size not in _CHRONOS:
            _CHRONOS[size] = BaseChronosPipeline.from_pretrained(
                f"amazon/chronos-bolt-{size}", device_map="cpu", dtype=torch.float32
            )
        context = torch.tensor(observed.to_numpy(), dtype=torch.float32)
        quantiles, _ = _CHRONOS[size].predict_quantiles(
            context, prediction_length=max(steps, 12), quantile_levels=list(QUANTILES)
        )
        _CHRONOS[key] = quantiles[0].numpy()  # (months ahead, 3)
    p10, p50, p90 = np.sort(_CHRONOS[key][steps - 1])
    return float(p10), float(p50), float(p90)


def chronos2(
    history: pd.DataFrame,
    target: str,
    horizon: int,
    origin: pd.Timestamp,
    covariates: bool = True,
) -> tuple[float, float, float]:
    """Zero-shot Chronos-2 (Amazon, Apache-2.0), local CPU; optional extra `pretrained`.

    With `covariates`, the target's kept drivers (DRIVERS, LEVEL_DRIVERS) are passed as past-only
    covariates over the same months as the target, last published value carried forward.
    """
    import torch
    from chronos import BaseChronosPipeline

    observed = np.exp(filled(known_logs(history, target)))
    steps = steps_to(observed.index[-1], origin, horizon)
    drivers = (*DRIVERS.get(target, ()), *LEVEL_DRIVERS.get(target, ())) if covariates else ()
    key = ("chronos2", covariates, target, observed.index[-1], len(observed))
    if key not in _CHRONOS:
        if "chronos2" not in _CHRONOS:
            _CHRONOS["chronos2"] = BaseChronosPipeline.from_pretrained(
                "amazon/chronos-2", device_map="cpu", dtype=torch.float32
            )
        item = {"target": observed.to_numpy(dtype=np.float32)}
        if drivers:
            past = history[list(drivers)].ffill().reindex(observed.index)
            item["past_covariates"] = {d: past[d].to_numpy(dtype=np.float32) for d in drivers}
        quantiles, _ = _CHRONOS["chronos2"].predict_quantiles(
            [item], prediction_length=max(steps, 12), quantile_levels=list(QUANTILES)
        )
        _CHRONOS[key] = quantiles[0].reshape(-1, len(QUANTILES)).numpy()  # (months ahead, 3)
    p10, p50, p90 = np.sort(_CHRONOS[key][steps - 1])
    return float(p10), float(p50), float(p90)


MODELS = {
    "ets_damped": ets_damped,
    "driver_qr": driver_qr,
    "chronos_bolt": chronos_bolt,
    "chronos2": chronos2,
}


def blend_models(*models):
    """Harness model averaging several models: geometric mean of each quantile.

    Same numbers as `blend_results` on their backtests, but usable at forecast time.
    """

    def blended(history, target, horizon, origin):
        logs = np.mean([np.log(m(history.copy(), target, horizon, origin)) for m in models], axis=0)
        p10, p50, p90 = np.sort(np.exp(logs))
        return float(p10), float(p50), float(p90)

    return blended


# ---- post-processing of backtest results (harness output: one row per forecast) ----


def blend_results(name: str, *runs: pd.DataFrame) -> pd.DataFrame:
    """Average several models' forecasts (geometric mean of each quantile), row by row."""
    keys = ["target", "origin", "horizon"]
    first = runs[0].set_index(keys)
    logs = sum(np.log(r.set_index(keys)[["p10", "p50", "p90"]]) for r in runs) / len(runs)
    out = first.copy()
    out[["p10", "p50", "p90"]] = np.exp(logs)
    out["model"] = name
    return out.reset_index()[runs[0].columns]


# Band methods (volatility scaling, calibration, adaptive, envelope): schneider_forecast.bands
