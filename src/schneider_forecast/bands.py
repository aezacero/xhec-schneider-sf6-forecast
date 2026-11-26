"""Uncertainty bands (P10 / P90) shared by every model.

Two kinds of tools:
1. At forecast time (harness interface `model(history, target, horizon, origin)`):
   - `rw_vol_scaled`: random walk whose band scales with recent volatility.
   - `with_vol_bands(model)`: keep any model's P50, replace its band by the volatility-scaled one.
2. After a backtest (one row per forecast, as `run_backtest` returns), leak-free because each
   forecast only uses outcomes already known at its origin (target_month ≤ origin):
   - `calibrate_results`: rescale bands so past forecasts would have covered 80 %.
   - `adaptive_results`: adaptive conformal update of the band width after each known outcome.
   - `envelope_results`: the wider of two bands around one model's P50.
   Post-processing assumes targets observed up to the origin (gap_months = 0).
"""

from collections.abc import Callable

import numpy as np
import pandas as pd

from schneider_forecast.config import QUANTILES
from schneider_forecast.data import KNOWN_DATA_ISSUES

Forecast = tuple[float, float, float]
MIN_CHANGES = 12  # standardised changes needed before volatility scaling is used
BAND_HALFLIFE = 3  # months; best in the band backtest (docs/forecasting_other.md §2)
MAX_VOL_RATIO = 2.0  # today's volatility counts at most 2× its median (forecasting_other.md §2c)

# (series, month) pairs that are data errors (data pipeline), not market events: models skip them
ERROR_MONTHS = frozenset(
    (series, pd.Timestamp(month))
    for month, series, _, treatment in KNOWN_DATA_ISSUES
    if treatment.startswith("error")
)


def target_logs(history: pd.DataFrame, target: str) -> pd.Series:
    """Log values of the target, monthly, from its first to its last valid month.

    Known data errors (ERROR_MONTHS) become gaps, and gaps stay in the series, so `shift(k)` is
    always k calendar months. A target whose last month is an error ends one month earlier.
    """
    values = history[target].copy()
    for series, month in ERROR_MONTHS:
        if series == target and month in values.index:
            values[month] = np.nan
    observed = values.dropna()
    if observed.empty:
        raise ValueError(f"{target} has no observed values")
    return np.log(values.loc[observed.index[0] : observed.index[-1]])


# ---- 1. volatility-scaled bands (at forecast time) ----


def ewma_vol(logs: pd.Series, halflife: float = BAND_HALFLIFE) -> pd.Series:
    """Monthly volatility at each month t: EWMA of squared log changes up to t (no look-ahead)."""
    changes = logs.diff()
    return np.sqrt((changes**2).ewm(halflife=halflife, min_periods=6).mean())


CRISIS = (pd.Timestamp("2021-01-01"), pd.Timestamp("2022-12-01"))  # 2021–22 surge (EDA §5)


def weighted_quantiles(values: pd.Series, weights: pd.Series, qs=QUANTILES) -> np.ndarray:
    """Quantiles where each value counts by its weight (equal weights = usual quantiles)."""
    order = np.argsort(values.to_numpy())
    v, w = values.to_numpy()[order], weights.to_numpy()[order]
    cum = (np.cumsum(w) - 0.5 * w) / w.sum()
    return np.interp(qs, cum, v)


def move_weights(
    starts: pd.DatetimeIndex,
    last: pd.Timestamp,
    crisis_weight: float = 1.0,
    decay_halflife: float | None = None,
) -> pd.Series:
    """Weight of each past move by its start month.

    `crisis_weight` < 1 counts moves starting in 2021–22 less (uses hindsight on what the crisis
    was: judge it on later origins only). `decay_halflife` (months) makes a move that started
    that many months before `last` count half, so older moves fade.
    """
    w = pd.Series(1.0, index=starts)
    if crisis_weight != 1.0:
        w[(starts >= CRISIS[0]) & (starts <= CRISIS[1])] = crisis_weight
    if decay_halflife is not None:
        age = np.array([(last.to_period("M") - s.to_period("M")).n for s in starts])
        w *= 0.5 ** (age / decay_halflife)
    return w


def vol_scaled_offsets(
    logs: pd.Series,
    steps: int,
    halflife: float = BAND_HALFLIFE,
    crisis_weight: float = 1.0,
    decay_halflife: float | None = None,
    max_vol_ratio: float | None = MAX_VOL_RATIO,
    clip_to_history: bool = False,
) -> np.ndarray:
    """Band edges in log units relative to P50, sized for today's volatility.

    Guards against overshooting when today's volatility is far above normal:
    `max_vol_ratio` caps today's volatility at that multiple of the series' median past
    volatility; `clip_to_history` keeps each edge within the largest past `steps`-month fall / rise.

    Past `steps`-month changes are divided by the volatility at their start (standardised), their
    P10 / P50 / P90 taken, and the distances P10 − P50 and P90 − P50 multiplied by the volatility at
    the last month. Asymmetry of past moves (fat upside tails) is kept. With fewer than
    MIN_CHANGES standardised changes (short series, early origins), falls back to the unscaled
    spread of past changes. `crisis_weight` / `decay_halflife`: see `move_weights` (default: every
    past move counts equally).
    """
    vol = ewma_vol(logs, halflife)
    last_vol = vol.dropna().iloc[-1] if vol.notna().any() else np.nan
    if max_vol_ratio is not None and vol.notna().any():
        last_vol = min(last_vol, max_vol_ratio * vol.median())
    z = ((logs.shift(-steps) - logs) / vol).dropna()
    raw = (logs.shift(-steps) - logs).dropna()
    if len(z) >= MIN_CHANGES and np.isfinite(last_vol):
        if crisis_weight == 1.0 and decay_halflife is None:
            q10, q50, q90 = np.quantile(z, QUANTILES)
        else:
            w = move_weights(z.index, logs.index[-1], crisis_weight, decay_halflife)
            q10, q50, q90 = weighted_quantiles(z, w)
        offsets = np.array([q10 - q50, 0.0, q90 - q50]) * last_vol
        if clip_to_history:
            centre = np.median(raw)
            offsets[0] = max(offsets[0], raw.min() - centre)
            offsets[2] = min(offsets[2], raw.max() - centre)
        return offsets
    if len(raw) < 6:
        raise ValueError(f"only {len(raw)} past {steps}-month changes")
    q10, q50, q90 = np.quantile(raw, QUANTILES)
    return np.array([q10 - q50, 0.0, q90 - q50])


def _logs_and_steps(history: pd.DataFrame, target: str, horizon: int, origin: pd.Timestamp):
    logs = target_logs(history, target)
    steps = (origin.to_period("M") - logs.index[-1].to_period("M")).n + horizon
    return logs, steps


def rw_vol_scaled(
    history: pd.DataFrame,
    target: str,
    horizon: int,
    origin: pd.Timestamp,
    halflife: float = BAND_HALFLIFE,
    **weighting,
) -> Forecast:
    """P50 = last observed value; band = volatility-scaled past changes.

    `weighting`: optional `crisis_weight` / `decay_halflife` (see `move_weights`).
    """
    logs, steps = _logs_and_steps(history, target, horizon, origin)
    offsets = vol_scaled_offsets(logs, steps, halflife, **weighting)
    return tuple(float(np.exp(logs.iloc[-1] + o)) for o in offsets)


def with_vol_bands(
    model: Callable[..., Forecast], halflife: float = BAND_HALFLIFE, **weighting
) -> Callable[..., Forecast]:
    """Wrap a model: keep its P50, replace its band by the volatility-scaled band around it."""

    def wrapped(history, target, horizon, origin):
        p50 = model(history, target, horizon, origin)[1]
        logs, steps = _logs_and_steps(history, target, horizon, origin)
        offsets = vol_scaled_offsets(logs, steps, halflife, **weighting)
        return tuple(float(p50 * np.exp(o)) for o in offsets)

    return wrapped


# ---- 2. post-processing of backtest results ----


def _band_logs(results: pd.DataFrame):
    log50 = np.log(results["p50"])
    lower = (log50 - np.log(results["p10"])).clip(lower=1e-9)
    upper = (np.log(results["p90"]) - log50).clip(lower=1e-9)
    return log50, lower, upper


def _rescale(results: pd.DataFrame, factors: pd.Series, name: str) -> pd.DataFrame:
    out = results.copy()
    log50, lower, upper = _band_logs(results)
    out["p10"] = np.exp(log50 - factors * lower)
    out["p90"] = np.exp(log50 + factors * upper)
    out["model"] = name
    return out


def calibrate_results(
    results: pd.DataFrame,
    name: str,
    target_coverage: float = 0.8,
    min_errors: int = 12,
    window: int | None = None,
) -> pd.DataFrame:
    """Rescale each band so past forecasts would have covered `target_coverage`.

    For a forecast at origin t, only same target × horizon forecasts with target month ≤ t are
    used. Each miss is measured in band units: z = |actual − P50| ÷ (P50 to the band edge on that
    side), so the band covered when z ≤ 1. Factor k = `target_coverage` quantile of past z (k = 1
    with fewer than `min_errors` outcomes); `window` keeps only the most recent outcomes.
    Too slow to react (an h-month miss is known only h months later).
    """
    log50, lower, upper = _band_logs(results)
    dev = np.log(results["actual"]) - log50
    z = pd.Series(np.where(dev >= 0, dev / upper, -dev / lower), index=results.index)
    factors = pd.Series(1.0, index=results.index)
    for _, group in results.groupby(["target", "horizon"]):
        for idx, origin in group["origin"].items():
            known = z[group.index[group["target_month"] <= origin]]
            if window is not None:
                known = known.iloc[-window:]
            if len(known) >= min_errors:
                factors[idx] = float(np.quantile(known, target_coverage))
    return _rescale(results, factors, name)


def adaptive_results(
    results: pd.DataFrame, name: str, gamma: float = 0.1, target_coverage: float = 0.8
) -> pd.DataFrame:
    """Adaptive conformal: one width factor per target × horizon, updated after every outcome.

    Each time an outcome becomes known (in target-month order), log k += gamma × (miss − (1 −
    target_coverage)): a miss widens the band by exp(0.8 γ), a hit narrows it by exp(−0.2 γ),
    so the long-run miss rate settles at 1 − target_coverage. The factor used at origin t only
    reflects outcomes with target month ≤ t. Misses are judged on the adjusted band.
    """
    log50, lower, upper = _band_logs(results)
    log_actual = np.log(results["actual"])
    factors = pd.Series(1.0, index=results.index)
    for _, group in results.groupby(["target", "horizon"]):
        group = group.sort_values("origin")
        pending = group.sort_values("target_month")  # outcomes in the order they become known
        log_k, used, done = 0.0, {}, 0
        for idx, origin in group["origin"].items():
            # learn from every outcome known by this origin that was not used yet
            while done < len(pending) and pending["target_month"].iloc[done] <= origin:
                j = pending.index[done]
                k_j = np.exp(used.get(j, 0.0))
                inside = (log50[j] - k_j * lower[j]) <= log_actual[j] <= (log50[j] + k_j * upper[j])
                log_k += gamma * ((not inside) - (1 - target_coverage))
                done += 1
            used[idx] = log_k
            factors[idx] = np.exp(log_k)
    return _rescale(results, factors, name)


def envelope_results(main: pd.DataFrame, other: pd.DataFrame, name: str) -> pd.DataFrame:
    """Keep `main`'s P50; band = the wider of the two bands (both measured around their P50)."""
    keys = ["target", "origin", "horizon"]
    a, b = main.set_index(keys), other.set_index(keys).reindex(main.set_index(keys).index)
    _, lower_a, upper_a = _band_logs(a)
    _, lower_b, upper_b = _band_logs(b)
    out = a.copy()
    log50 = np.log(a["p50"])
    out["p10"] = np.exp(log50 - np.maximum(lower_a, lower_b))
    out["p90"] = np.exp(log50 + np.maximum(upper_a, upper_b))
    out["model"] = name
    return out.reset_index()[main.columns]
