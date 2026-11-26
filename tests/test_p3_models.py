import numpy as np
import pandas as pd
import pytest

from schneider_forecast.bands import calibrate_results
from schneider_forecast.p3_models import (
    blend_results,
    change_quantiles,
    driver_qr,
    ets_damped,
    steps_to,
)


def _history(values, end="2026-09"):
    months = pd.date_range(end=end, periods=len(values), freq="MS")
    return pd.DataFrame({"X": values}, index=months)


def test_steps_count_from_last_value():
    origin = pd.Timestamp("2026-09-01")
    assert steps_to(pd.Timestamp("2026-09-01"), origin, 3) == 3
    assert steps_to(pd.Timestamp("2026-08-01"), origin, 3) == 4


def test_change_quantiles_need_enough_history():
    with pytest.raises(ValueError):
        change_quantiles(np.log(_history(np.arange(1.0, 10.0))["X"]), 3)


def test_ets_damped_is_ordered_and_positive():
    rng = np.random.default_rng(0)
    values = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 80)))
    p10, p50, p90 = ets_damped(_history(values), "X", 6, pd.Timestamp("2026-09-01"))
    assert 0 < p10 <= p50 <= p90


def test_ets_damped_follows_a_steady_trend():
    values = 100 * np.exp(0.01 * np.arange(80))  # +1 % a month
    _, p50, _ = ets_damped(_history(values), "X", 3, pd.Timestamp("2026-09-01"))
    assert p50 > values[-1]


def _driver_history(n):
    rng = np.random.default_rng(1)
    months = pd.date_range(end="2026-09", periods=n, freq="MS")
    walk = lambda: 100 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))  # noqa: E731
    return pd.DataFrame({"S11": walk(), "E01": walk(), "ED02": walk(), "E22": walk()}, months)


def test_driver_qr_is_ordered_and_positive():
    p10, p50, p90 = driver_qr(_driver_history(100), "S11", 3, pd.Timestamp("2026-09-01"))
    assert 0 < p10 <= p50 <= p90


def test_driver_qr_falls_back_to_random_walk_on_short_history():
    history = _driver_history(40)
    p10, p50, p90 = driver_qr(history, "S11", 9, pd.Timestamp("2026-09-01"))
    assert p10 <= history["S11"].iloc[-1] * 1.5 and p10 <= p50 <= p90


def test_chronos_bolt_is_ordered_and_positive():
    pytest.importorskip("chronos")  # optional extra: CI runs without it
    from schneider_forecast.p3_models import chronos_bolt

    values = 100 * np.exp(np.cumsum(np.random.default_rng(2).normal(0, 0.03, 60)))
    p10, p50, p90 = chronos_bolt(_history(values), "X", 6, pd.Timestamp("2026-09-01"))
    assert 0 < p10 <= p50 <= p90


def _results(p10, p50, p90, actual, n=30):
    origins = pd.date_range("2020-01", periods=n, freq="MS")
    return pd.DataFrame(
        {
            "model": "m",
            "target": "X",
            "origin": origins,
            "horizon": 3,
            "target_month": origins + pd.DateOffset(months=3),
            "p10": p10,
            "p50": p50,
            "p90": p90,
            "actual": actual,
            "last_value": 100.0,
            "flagged": False,
        }
    )


def test_blend_is_geometric_mean_of_quantiles():
    a, b = _results(80.0, 100.0, 125.0, 100.0), _results(20.0, 25.0, 50.0, 100.0)
    out = blend_results("ab", a, b)
    assert np.allclose(out["p50"], 50.0) and np.allclose(out["p10"], 40.0)
    assert (out["model"] == "ab").all()


def test_calibration_widens_bands_that_were_too_narrow():
    actual = np.where(np.arange(30) % 2 == 0, 130.0, 75.0)  # always outside 95–105
    out = calibrate_results(_results(95.0, 100.0, 105.0, actual), "cal", min_errors=5)
    assert (out["p90"].iloc[-1] > 105.0) and (out["p10"].iloc[-1] < 95.0)
    assert out["p50"].equals(_results(95.0, 100.0, 105.0, actual)["p50"])  # centre unchanged
    assert out["p90"].iloc[0] == pytest.approx(105.0)  # no known outcomes yet: unchanged


def test_chronos2_is_ordered_and_positive():
    pytest.importorskip("chronos")
    from schneider_forecast.p3_models import chronos2

    history = _driver_history(60)
    p10, p50, p90 = chronos2(history, "S11", 6, pd.Timestamp("2026-09-01"))
    assert 0 < p10 <= p50 <= p90
