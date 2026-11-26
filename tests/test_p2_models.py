import numpy as np
import pandas as pd
import pytest

from schneider_forecast.backtest import run_backtest
from schneider_forecast.bands import target_logs, vol_scaled_offsets
from schneider_forecast.p2_models import PooledLinearModel, pair_features

MONTHS = pd.date_range("2012-01-01", "2026-09-01", freq="MS")


def walk(seed: int, sd: float = 0.03, n: int = len(MONTHS)) -> np.ndarray:
    return 100 * np.exp(np.cumsum(np.random.default_rng(seed).normal(0.0, sd, n)))


def lead_history() -> pd.DataFrame:
    """S09 follows the steel price L01 three months later; S09 is published one month later."""
    steel = walk(0)
    h = pd.DataFrame({"L01": steel, "S09": np.r_[np.full(3, steel[0]), steel[:-3]]}, index=MONTHS)
    h.loc[MONTHS[-1], "S09"] = np.nan
    return h


def test_driver_features_use_the_months_the_driver_is_known_ahead():
    h = lead_history()
    f = pair_features(h, "S09", ("L01",), steps=4, season=False)
    assert f.index[-1] == MONTHS[-2]  # S09 ends one month before L01
    logs = np.log(h["L01"])
    vol = np.sqrt((logs.diff() ** 2).ewm(halflife=6, min_periods=6).mean())
    expected = (logs.iloc[-1] - logs.iloc[-2]) / vol.iloc[-1]  # L01's newest month
    assert f["drv0_mom_1"].iloc[-1] == pytest.approx(expected)


def test_learns_a_leading_driver():
    h = lead_history()
    origin = MONTHS[-1]
    model = PooledLinearModel({"S09": ("L01",)}, alpha=0.0)
    p10, p50, p90 = model.fit(h, "S09", 3, origin).predict(h, "S09", 3, origin)
    truth = h["L01"].iloc[-1]  # S09 at origin + 3 = L01 at origin
    last = h["S09"].dropna().iloc[-1]
    assert abs(np.log(p50 / truth)) < 0.5 * abs(np.log(last / truth))
    assert p10 < p50 < p90


def test_band_is_the_shared_volatility_band_around_p50():
    h = lead_history()
    origin = MONTHS[-1]
    model = PooledLinearModel({"S09": ("L01",)})
    p10, p50, p90 = model.fit(h, "S09", 6, origin).predict(h, "S09", 6, origin)
    offsets = vol_scaled_offsets(
        target_logs(h, "S09"), 7, halflife=3
    )  # 6 m + 1 m gap; band half-life
    assert np.log(p10 / p50) == pytest.approx(offsets[0])
    assert np.log(p90 / p50) == pytest.approx(offsets[2])


def test_target_outside_the_pool_is_refused():
    h = lead_history()
    with pytest.raises(ValueError, match="not in this model"):
        PooledLinearModel({"S09": ("L01",)}).fit(h, "L01", 3, MONTHS[-1])


def test_pooled_steel_model_runs_in_the_harness():
    names = ["L01", "L03", "MEPS_FR_CR"]
    prices = pd.DataFrame(
        {n: walk(i) for i, n in enumerate(names)}, index=pd.DatetimeIndex(MONTHS, name="month")
    )
    catalog = pd.DataFrame(
        {"gap_months": [0, 0, 0], "pub_lag": [1, 1, 1], "is_target": [True, True, False]},
        index=names,
    )
    flags = pd.DataFrame(columns=["month", "series_id", "issue", "treatment"])
    model = PooledLinearModel({n: () for n in names}, season=True)
    r = run_backtest(
        model,
        "steel",
        targets=["L01", "L03"],
        data=(prices, catalog, flags),
        start="2025-06",
        save=False,
        track_co2=False,
    )
    assert set(r["target"]) == {"L01", "L03"}
    assert (r["p10"] <= r["p50"]).all() and (r["p50"] <= r["p90"]).all()


def test_too_little_history_falls_back_to_the_random_walk():
    h = lead_history().loc["2023-01-01":]  # 45 months, too few rows to fit
    origin = h.index[-1]
    p10, p50, p90 = PooledLinearModel({"S09": ("L01",)}, min_rows=36).predict(h, "S09", 3, origin)
    assert p50 == pytest.approx(h["S09"].dropna().iloc[-1])
    assert p10 < p50 < p90


def test_feature_lags_can_be_chosen():
    model = PooledLinearModel({"S09": ("L01",)}, own_lags=(1, 3), driver_lags=(1,))
    assert model.features == ["mom_1", "mom_3", "drv0_mom_1"]
    steel = PooledLinearModel({"L01": (), "L03": ()}, season=True, own_lags=(1,))
    assert steel.features == ["mom_1", "season"]


def test_driver_published_later_uses_its_last_known_month():
    h = lead_history()  # the driver S09 ends one month before the target L01
    f = pair_features(h, "L01", ("S09",), steps=3, season=False)
    logs = np.log(h["S09"].dropna())
    vol = np.sqrt((logs.diff() ** 2).ewm(halflife=6, min_periods=6).mean())
    expected = (logs.iloc[-1] - logs.iloc[-2]) / vol.iloc[-1]  # driver's newest month, one before
    assert f.index[-1] == MONTHS[-1]
    assert f["drv0_mom_1"].iloc[-1] == pytest.approx(expected)
