import numpy as np
import pandas as pd
import pytest

from schneider_forecast.backtest import run_backtest
from schneider_forecast.bands import target_logs, vol_scaled_offsets
from schneider_forecast.config import HORIZONS
from schneider_forecast.p2_models import P2_TARGETS
from schneider_forecast.p2_selection import (
    SELECTION,
    HeldForecast,
    P2Selected,
    final_forecasts,
)

MONTHS = pd.date_range("2014-01-01", "2026-09-01", freq="MS")


def prices() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    p = pd.DataFrame(
        {c: 100 * np.exp(np.cumsum(rng.normal(0.002, 0.03, len(MONTHS)))) for c in ["A", "B"]},
        index=pd.DatetimeIndex(MONTHS, name="month"),
    )
    p.loc[MONTHS[-1], "B"] = np.nan  # B ends one month early
    return p


def grows_one_percent_a_month(history, target, horizon, origin):
    last = history[target].dropna()
    steps = (origin.to_period("M") - last.index[-1].to_period("M")).n + horizon
    p50 = last.iloc[-1] * np.exp(0.01 * steps)
    return p50 * 0.9, p50, p50 * 1.1


def test_held_forecast_keeps_the_shorter_p50_with_the_longer_band():
    h = prices()
    origin = MONTHS[-1]
    p10, p50, p90 = HeldForecast(grows_one_percent_a_month, use=3).predict(h, "B", 9, origin)
    assert p50 == pytest.approx(grows_one_percent_a_month(h, "B", 3, origin)[1])
    offsets = vol_scaled_offsets(target_logs(h, "B"), 10, halflife=3)  # 9 months + 1 month gap
    assert np.log(p10 / p50) == pytest.approx(offsets[0])
    assert np.log(p90 / p50) == pytest.approx(offsets[2])


def test_every_p2_target_and_horizon_has_one_model():
    assert set(SELECTION) == {(t, h) for t in P2_TARGETS for h in HORIZONS}
    assert all(isinstance(name, str) for name, _ in SELECTION.values())


def constant(value):
    return lambda history, target, horizon, origin: (value * 0.9, value, value * 1.1)


TOY = {
    ("A", 3): ("three", constant(3.0)),
    ("A", 6): ("six", constant(6.0)),
    ("B", 3): ("b", HeldForecast(grows_one_percent_a_month, use=3)),
    ("B", 6): ("b", HeldForecast(grows_one_percent_a_month, use=3)),
}


def test_selected_model_dispatches_on_target_and_horizon_in_the_harness():
    p = prices()
    catalog = pd.DataFrame(
        {"gap_months": [0, 1], "pub_lag": [1, 1], "is_target": [True, True]}, index=["A", "B"]
    )
    flags = pd.DataFrame(columns=["month", "series_id", "issue", "treatment"])
    r = run_backtest(
        P2Selected(TOY),
        "sel",
        targets=["A", "B"],
        horizons=(3, 6),
        data=(p, catalog, flags),
        start="2026-01",
        save=False,
        track_co2=False,
    )
    a = r[r["target"] == "A"]
    assert set(a.loc[a["horizon"] == 3, "p50"]) == {3.0}
    assert set(a.loc[a["horizon"] == 6, "p50"]) == {6.0}


def test_final_forecasts_follow_the_submission_columns():
    p = prices()
    catalog = pd.DataFrame(
        {"unit": ["EUR/t", "Index 2021=100"], "gap_months": [0, 1], "pub_lag": [1, 3]},
        index=["A", "B"],
    )
    out = final_forecasts(data=(p, catalog), selection=TOY, origin="2026-09", horizons=(3, 6))
    assert list(out.columns) == [
        "target_type",
        "target_id",
        "origin_month",
        "horizon_m",
        "target_month",
        "unit",
        "p10",
        "p50",
        "p90",
        "model_name",
    ]
    assert len(out) == 4
    b6 = out[(out["target_id"] == "B") & (out["horizon_m"] == 6)].iloc[0]
    assert b6["target_month"] == "2027-03" and b6["unit"] == "Index 2021=100"
    assert b6["p10"] <= b6["p50"] <= b6["p90"]
