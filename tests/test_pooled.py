import numpy as np
import pandas as pd
import pytest

from schneider_forecast.backtest import run_backtest
from schneider_forecast.bands import target_logs, vol_scaled_offsets
from schneider_forecast.pooled import PooledQuantileModel

MONTHS = pd.date_range("2014-01-01", "2026-09-01", freq="MS")


def growth_history() -> pd.DataFrame:
    """Every series grows exactly 1 % a month; L02 ends one month early (like stainless)."""
    t = np.arange(len(MONTHS))
    h = pd.DataFrame(
        {"S09": 100 * np.exp(0.01 * t), "D01": 50 * np.exp(0.01 * t), "L02": 80 * np.exp(0.01 * t)},
        index=MONTHS,
    )
    h.loc[MONTHS[-1], "L02"] = np.nan
    return h


def fitted(history, target, horizon):
    model = PooledQuantileModel(series=["S09", "D01", "L02"], alpha=0.0)
    origin = history.index[-1]
    model.fit(history, target, horizon, origin)
    return model.predict(history, target, horizon, origin)


def test_constant_growth_is_extrapolated():
    h = growth_history()
    p10, p50, p90 = fitted(h, "S09", 3)
    expected = h["S09"].iloc[-1] * np.exp(0.03)
    assert p50 == pytest.approx(expected, rel=1e-6)
    assert p10 <= p50 <= p90


def test_target_ending_early_is_forecast_over_the_longer_span():
    h = growth_history()
    _, p50, _ = fitted(h, "L02", 3)
    assert p50 == pytest.approx(h["L02"].iloc[-2] * np.exp(0.04), rel=1e-6)


def test_runs_in_the_backtest_harness_and_returns_ordered_quantiles():
    rng = np.random.default_rng(0)
    prices = pd.DataFrame(
        {
            c: 100 * np.exp(np.cumsum(rng.normal(0.003, sd, len(MONTHS))))
            for c, sd in {"S09": 0.01, "D01": 0.05, "L02": 0.03}.items()
        },
        index=pd.DatetimeIndex(MONTHS, name="month"),
    )
    catalog = pd.DataFrame(
        {"gap_months": [0, 0, 1], "pub_lag": [2, 2, 3], "is_target": [True, True, True]},
        index=["S09", "D01", "L02"],
    )
    flags = pd.DataFrame(columns=["month", "series_id", "issue", "treatment"])
    model = PooledQuantileModel(series=["S09", "D01", "L02"])
    r = run_backtest(
        model, "agg", data=(prices, catalog, flags), start="2025-01", save=False, track_co2=False
    )
    assert len(r) > 0
    assert (r["p10"] <= r["p50"]).all() and (r["p50"] <= r["p90"]).all()


def test_shared_volatility_bands_around_own_p50():
    rng = np.random.default_rng(1)
    h = pd.DataFrame(
        {c: 100 * np.exp(np.cumsum(rng.normal(0.002, 0.03, len(MONTHS)))) for c in ["S09", "D01"]},
        index=MONTHS,
    )
    origin = h.index[-1]
    model = PooledQuantileModel(series=["S09", "D01"], bands="vol")
    p10, p50, p90 = model.fit(h, "S09", 6, origin).predict(h, "S09", 6, origin)
    offsets = vol_scaled_offsets(target_logs(h, "S09"), 6, halflife=3)  # band half-life
    assert np.log(p10 / p50) == pytest.approx(offsets[0])
    assert np.log(p90 / p50) == pytest.approx(offsets[2])
    own = PooledQuantileModel(series=["S09", "D01"], bands="own")
    assert own.fit(h, "S09", 6, origin).predict(h, "S09", 6, origin)[1] == pytest.approx(p50)
