import numpy as np
import pandas as pd
import pytest

from schneider_forecast.bands import (
    adaptive_results,
    envelope_results,
    ewma_vol,
    rw_vol_scaled,
    with_vol_bands,
)

ORIGIN = pd.Timestamp("2026-09-01")


def _history(changes):
    months = pd.date_range(end="2026-09", periods=len(changes), freq="MS")
    return pd.DataFrame({"X": 100 * np.exp(np.cumsum(changes))}, index=months)


def _calm_then(last_sd, n=120, seed=0):
    rng = np.random.default_rng(seed)
    changes = rng.normal(0, 0.01, n)
    changes[-6:] = rng.normal(0, last_sd, 6)
    return _history(changes)


def test_ewma_vol_uses_only_the_past():
    logs = np.log(_calm_then(0.01)["X"])
    vol = ewma_vol(logs)
    changed = logs.copy()
    changed.iloc[-1] += 1.0  # a shock in the last month only
    assert ewma_vol(changed).iloc[:-1].equals(vol.iloc[:-1])


def test_rw_vol_scaled_keeps_last_value_and_order():
    history = _calm_then(0.01)
    p10, p50, p90 = rw_vol_scaled(history, "X", 3, ORIGIN)
    assert p50 == pytest.approx(history["X"].iloc[-1])
    assert 0 < p10 < p50 < p90


def test_band_widens_after_a_volatile_spell():
    calm = rw_vol_scaled(_calm_then(0.01), "X", 3, ORIGIN)
    shock = rw_vol_scaled(_calm_then(0.08), "X", 3, ORIGIN)
    assert shock[2] / shock[1] > calm[2] / calm[1]


def test_with_vol_bands_keeps_the_model_p50():
    def fixed(history, target, horizon, origin):
        return 90.0, 123.0, 150.0

    p10, p50, p90 = with_vol_bands(fixed)(_calm_then(0.01), "X", 6, ORIGIN)
    assert p50 == 123.0 and p10 < p50 < p90


def _results(p10, p50, p90, actual, n=40):
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


def test_adaptive_widens_after_misses_and_only_uses_known_outcomes():
    out = adaptive_results(_results(95.0, 100.0, 105.0, 130.0), "aci", gamma=0.2)
    # h = 3: the first outcome (2020-04) is known from origin 2020-04 on, so 3 rows are untouched
    assert out["p90"].iloc[:3].tolist() == pytest.approx([105.0] * 3)
    assert out["p90"].iloc[3] > 105.0
    assert out["p90"].iloc[-1] > 105.0 and out["p10"].iloc[-1] < 95.0
    assert (out["p50"] == 100.0).all()


def test_adaptive_narrows_bands_that_always_cover():
    out = adaptive_results(_results(50.0, 100.0, 200.0, 100.0), "aci", gamma=0.2)
    assert out["p90"].iloc[-1] < 200.0


def test_envelope_takes_the_wider_side_around_the_main_p50():
    main = _results(95.0, 100.0, 120.0, 100.0)
    other = _results(160.0, 200.0, 220.0, 100.0)  # P10 is 20 % below P50, P90 10 % above
    out = envelope_results(main, other, "env")
    assert out["p10"].iloc[0] == pytest.approx(80.0)
    assert out["p90"].iloc[0] == pytest.approx(120.0)
    assert out["p50"].iloc[0] == 100.0


def test_target_logs_blanks_known_errors_and_keeps_the_gap():
    from schneider_forecast.bands import target_logs

    months = pd.date_range("2026-01", "2026-09", freq="MS")
    history = pd.DataFrame({"EPX_RESIN": 4900.0}, index=months)
    history.loc["2026-05-01", "EPX_RESIN"] = 3593.0  # the known May 2026 error
    logs = target_logs(history, "EPX_RESIN")
    assert np.isnan(logs["2026-05-01"]) and len(logs) == len(months)


def test_epoxy_error_does_not_inflate_the_band():
    rng = np.random.default_rng(3)
    months = pd.date_range(end="2026-09", periods=100, freq="MS")
    history = pd.DataFrame(
        {"EPX_RESIN": 4900 * np.exp(np.cumsum(rng.normal(0, 0.01, 100)))}, index=months
    )
    clean = rw_vol_scaled(history, "EPX_RESIN", 9, ORIGIN, halflife=3)
    history.loc["2026-05-01", "EPX_RESIN"] *= 0.73  # same −27 % error as in the data
    assert rw_vol_scaled(history, "EPX_RESIN", 9, ORIGIN, halflife=3) == pytest.approx(clean)


def test_weighted_quantiles_match_plain_quantiles_and_follow_weights():
    from schneider_forecast.bands import weighted_quantiles

    values = pd.Series(np.arange(1.0, 101.0))
    plain = weighted_quantiles(values, pd.Series(np.ones(100)), [0.5])
    assert plain[0] == pytest.approx(50.5)
    heavy_top = weighted_quantiles(values, pd.Series(np.r_[np.ones(50), 9 * np.ones(50)]), [0.5])
    assert heavy_top[0] > 60


def test_move_weights_crisis_and_decay():
    from schneider_forecast.bands import move_weights

    starts = pd.DatetimeIndex(["2019-06-01", "2021-06-01", "2026-06-01"])
    w = move_weights(starts, pd.Timestamp("2026-09-01"), crisis_weight=0.25)
    assert w.tolist() == [1.0, 0.25, 1.0]
    d = move_weights(starts, pd.Timestamp("2026-09-01"), decay_halflife=36)
    assert d.iloc[0] < d.iloc[1] < d.iloc[2] <= 1.0


def test_volatility_cap_limits_the_band_after_an_extreme_spell():
    from schneider_forecast.bands import vol_scaled_offsets

    logs = np.log(_calm_then(0.10)["X"])  # last 6 months ~10× the usual volatility
    capped = vol_scaled_offsets(logs, 9, halflife=3)
    uncapped = vol_scaled_offsets(logs, 9, halflife=3, max_vol_ratio=None)
    assert capped[2] < uncapped[2] and capped[0] > uncapped[0]
