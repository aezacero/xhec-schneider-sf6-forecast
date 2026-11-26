"""Walk-forward backtest: replay every month since 2020 with only the data known at the time.

results = run_backtest(my_model, name="ets_v1")
scores = score(results)                       # schneider_forecast.metrics
"""

import copy
import json
import math
import time
from collections.abc import Callable

import numpy as np
import pandas as pd

from schneider_forecast.config import (
    BACKTEST_DIR,
    BACKTEST_START,
    DATA_FLAGS,
    HORIZONS,
    ORIGIN,
    PRICES_WIDE,
    SERIES_CATALOG,
)

Forecast = tuple[float, float, float]
ModelFn = Callable[[pd.DataFrame, str, int, pd.Timestamp], Forecast]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Pipeline outputs: prices (months × series), catalog (one row per series), flags."""
    prices = pd.read_csv(PRICES_WIDE, parse_dates=["month"], index_col="month")
    catalog = pd.read_csv(SERIES_CATALOG, index_col="series_id", parse_dates=["first", "last"])
    flags = pd.read_csv(DATA_FLAGS)
    return prices, catalog, flags


def available_at(
    prices: pd.DataFrame, catalog: pd.DataFrame, origin: pd.Timestamp, strict: bool = False
) -> pd.DataFrame:
    """What was known at the origin: no rows after it, each series cut by its gap.

    Main run: each series loses its last `gap_months` months, as on the real 2026-09 forecast.
    Strict run: it loses max(pub_lag, gap_months) months, i.e. only data already published.
    """
    history = prices.loc[:origin].copy()
    gap = catalog["gap_months"]
    if strict:
        gap = np.maximum(catalog["pub_lag"], gap)
    for series, months in gap.items():
        if months > 0:
            history.loc[history.index > origin - pd.DateOffset(months=int(months)), series] = np.nan
    return history


def check_forecast(forecast: Forecast) -> Forecast:
    """A forecast is three finite prices above 0 with P10 ≤ P50 ≤ P90."""
    p10, p50, p90 = (float(x) for x in forecast)
    if not all(math.isfinite(x) and x > 0 for x in (p10, p50, p90)):
        raise ValueError(f"forecast must be finite and > 0, got {(p10, p50, p90)}")
    if not p10 <= p50 <= p90:
        raise ValueError(f"forecast quantiles cross: P10={p10}, P50={p50}, P90={p90}")
    return p10, p50, p90


def error_months(flags: pd.DataFrame) -> set[tuple[str, pd.Timestamp]]:
    """(series, month) pairs flagged as data errors (real market events are not counted)."""
    errors = flags[flags["treatment"].str.startswith("error")]
    return {(s, pd.Timestamp(m)) for s, m in zip(errors["series_id"], errors["month"], strict=True)}


class _Refitter:
    """Calls fit every k origins and predict at every origin, per target and horizon.

    Each target × horizon gets its own copy of the model, so a fit made for one target is never
    reused to predict another.
    """

    def __init__(self, model: object, every: int) -> None:
        self.model, self.every = model, every
        self.copies, self.fitted_at = {}, {}

    def __call__(self, history, target, horizon, origin, step):
        key = (target, horizon)
        if key not in self.copies:
            self.copies[key] = copy.deepcopy(self.model)
        model = self.copies[key]
        if key not in self.fitted_at or step - self.fitted_at[key] >= self.every:
            model.fit(history, target, horizon, origin)
            self.fitted_at[key] = step
        return model.predict(history, target, horizon, origin)


def _model_caller(model: ModelFn | object, refit_every: int) -> Callable:
    if hasattr(model, "fit") and hasattr(model, "predict"):
        return _Refitter(model, refit_every)
    if refit_every != 1:
        raise ValueError("refit_every > 1 needs a model object with fit() and predict()")
    return lambda history, target, horizon, origin, step: model(history, target, horizon, origin)


def _track_co2():
    """Offline CO₂ estimate (no network call); country set to France (HEC)."""
    from codecarbon import OfflineEmissionsTracker

    return OfflineEmissionsTracker(
        country_iso_code="FRA", save_to_file=False, log_level="error", measure_power_secs=5
    )


def run_backtest(
    model: ModelFn | object,
    name: str,
    targets: list[str] | None = None,
    horizons: tuple[int, ...] = HORIZONS,
    start: str = BACKTEST_START,
    strict: bool = False,
    refit_every: int = 1,
    data: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | None = None,
    save: bool = True,
    track_co2: bool = True,
) -> pd.DataFrame:
    """Forecast every target × horizon from every origin since `start`; one row per forecast.

    `model(history, target, horizon, origin) -> (p10, p50, p90)` in price levels, or an object
    with fit() and predict() of the same arguments (needed for refit_every > 1). The forecast
    month is always origin + horizon. `data` overrides the pipeline outputs (used in tests).
    """
    prices, catalog, flags = data if data is not None else load_data()
    targets = targets or list(catalog.index[catalog["is_target"]])
    call = _model_caller(model, refit_every)
    errors = error_months(flags)
    origins = pd.date_range(start, ORIGIN, freq="MS")

    tracker = _track_co2() if track_co2 else None
    if tracker:
        tracker.start()
    began = time.perf_counter()
    rows = []
    for step, origin in enumerate(origins):
        history = available_at(prices, catalog, origin, strict)
        for target in targets:
            known = history[target].dropna()
            if known.empty:
                continue
            for horizon in horizons:
                target_month = origin + pd.DateOffset(months=horizon)
                actual = prices[target].get(target_month, np.nan)
                if pd.isna(actual):
                    continue  # no truth to score against (beyond the data or a gap)
                try:
                    p10, p50, p90 = check_forecast(
                        call(history.copy(), target, horizon, origin, step)
                    )
                except Exception as err:
                    err.add_note(f"{name}: target {target}, origin {origin:%Y-%m}, h={horizon}")
                    raise
                last_month = known.index[-1]
                rows.append(
                    {
                        "model": name,
                        "target": target,
                        "origin": origin,
                        "horizon": horizon,
                        "target_month": target_month,
                        "p10": p10,
                        "p50": p50,
                        "p90": p90,
                        "actual": actual,
                        "last_value": known.iloc[-1],
                        "flagged": (target, target_month) in errors
                        or (target, last_month) in errors,
                    }
                )
    results = pd.DataFrame(rows)
    results.attrs = {
        "name": name,
        "strict": strict,
        "runtime_s": round(time.perf_counter() - began, 2),
        "co2_kg": tracker.stop() if tracker else None,
    }
    if save:
        save_results(results)
    return results


def save_results(results: pd.DataFrame) -> None:
    """outputs/backtest/<name>.csv plus <name>_run.json with runtime and CO₂."""
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    stem = results.attrs["name"] + ("_strict" if results.attrs["strict"] else "")
    results.to_csv(BACKTEST_DIR / f"{stem}.csv", index=False)
    (BACKTEST_DIR / f"{stem}_run.json").write_text(json.dumps(results.attrs, indent=2))
