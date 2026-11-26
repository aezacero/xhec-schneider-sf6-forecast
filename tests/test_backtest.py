import numpy as np
import pandas as pd
import pytest

from schneider_forecast.backtest import available_at, check_forecast, run_backtest
from schneider_forecast.metrics import compare, interval_score, pinball, score

MONTHS = pd.date_range("2018-01-01", "2026-09-01", freq="MS")


def _data():
    """Two targets (one ending a month early, like L02) and one input published with a lag."""
    trend = np.linspace(100, 200, len(MONTHS))
    prices = pd.DataFrame(
        {"A": trend, "L02": trend * 2, "X": trend / 2},
        index=pd.DatetimeIndex(MONTHS, name="month"),
    )
    prices.loc[MONTHS[-1], "L02"] = np.nan
    catalog = pd.DataFrame(
        {
            "gap_months": [0, 1, 0],
            "pub_lag": [0, 3, 2],
            "is_target": [True, True, False],
        },
        index=["A", "L02", "X"],
    )
    flags = pd.DataFrame(columns=["month", "series_id", "issue", "treatment"])
    return prices, catalog, flags


def _rw(history, target, horizon, origin):
    last = history[target].dropna().iloc[-1]
    return last * 0.9, last, last * 1.1


def _run(model=_rw, **kwargs):
    return run_backtest(model, "test", data=_data(), save=False, track_co2=False, **kwargs)


def test_available_at_cuts_each_series_by_its_gap():
    prices, catalog, _ = _data()
    origin = pd.Timestamp("2024-06-01")
    history = available_at(prices, catalog, origin)
    assert history.index.max() == origin
    assert history["A"].last_valid_index() == origin
    assert history["L02"].last_valid_index() == pd.Timestamp("2024-05-01")
    strict = available_at(prices, catalog, origin, strict=True)
    assert strict["X"].last_valid_index() == pd.Timestamp("2024-04-01")  # pub_lag 2
    assert strict["L02"].last_valid_index() == pd.Timestamp("2024-03-01")  # max(3, 1)


def test_model_never_sees_values_past_the_cutoff():
    def spy(history, target, horizon, origin):
        assert history.index.max() == origin
        assert history["L02"].last_valid_index() < origin
        return _rw(history, target, horizon, origin)

    _run(spy)


def test_target_month_is_origin_plus_horizon_even_when_target_ends_early():
    results = _run()
    l02 = results[(results["target"] == "L02") & (results["horizon"] == 3)].iloc[0]
    assert l02["target_month"] == l02["origin"] + pd.DateOffset(months=3)
    # last value is one month before the origin
    prices, _, _ = _data()
    assert l02["last_value"] == prices.loc[l02["origin"] - pd.DateOffset(months=1), "L02"]


def test_only_forecasts_with_a_known_actual_are_kept():
    results = _run()
    assert results["actual"].notna().all()
    assert results["target_month"].max() <= pd.Timestamp("2026-09-01")


def test_random_walk_has_zero_skill_against_itself():
    scores = score(_run())
    assert np.allclose(scores["skill_rw"], 0)
    table = compare(scores, scores)
    assert np.allclose(table["skill_mae_log"], 0)


def test_pinball_and_interval_score_on_hand_checked_numbers():
    assert pinball(np.array([10.0]), np.array([8.0]), 0.9)[0] == pytest.approx(1.8)
    assert pinball(np.array([10.0]), np.array([12.0]), 0.9)[0] == pytest.approx(0.2)
    # band 1–3, actual 4: width 2 + 10 × miss 1
    assert interval_score(np.array([4.0]), np.array([1.0]), np.array([3.0]))[0] == 12


def test_coverage_counts_actuals_inside_the_band():
    results = _run()
    expected = results["actual"].between(results["p10"], results["p90"]).mean()
    overall = score(results).xs("all", level="period")
    assert (overall["coverage"] * overall["n"]).sum() / overall["n"].sum() == pytest.approx(
        expected
    )


def test_refit_every_matches_refitting_each_time_for_a_model_with_no_fit():
    class NoFit:
        def fit(self, history, target, horizon, origin):
            pass

        def predict(self, history, target, horizon, origin):
            return _rw(history, target, horizon, origin)

    every_time = _run(NoFit())
    every_third = _run(NoFit(), refit_every=3)
    pd.testing.assert_frame_equal(every_time, every_third)


def test_refit_every_never_uses_one_targets_fit_for_another():
    class LastValueAtFit:  # keeps a single fitted state, like most model objects
        def fit(self, history, target, horizon, origin):
            self.level = history[target].dropna().iloc[-1]

        def predict(self, history, target, horizon, origin):
            return self.level * 0.9, self.level, self.level * 1.1

    results = _run(LastValueAtFit(), refit_every=3)
    prices, _, _ = _data()
    for _, row in results.iterrows():
        # the P50 must be a value of the row's own target, taken at its last fit
        assert row["p50"] in prices[row["target"]].to_numpy()


@pytest.mark.parametrize("bad", [(3, 2, 4), (1, np.nan, 2), (-1, 1, 2)])
def test_invalid_forecasts_are_rejected(bad):
    with pytest.raises(ValueError):
        check_forecast(bad)
