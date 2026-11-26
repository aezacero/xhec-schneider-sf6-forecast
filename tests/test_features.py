import numpy as np
import pandas as pd
import pytest

from schneider_forecast.features import FEATURES, build_dataset, clean_series, series_features

MONTHS = pd.date_range("2016-01-01", periods=60, freq="MS")


def growth(g: float = 0.01, n: int = 60) -> pd.Series:
    """Log price rising by exactly g a month: volatility g, every k-month change k × g."""
    return pd.Series(np.exp(g * np.arange(n)), index=MONTHS[:n])


def test_momentum_is_past_change_in_volatility_units():
    f = series_features(growth(), steps=3, group="metal")
    row = f.loc["2018-01-01"]
    for k in (1, 3, 6):
        assert row[f"mom_{k}"] == pytest.approx(np.sqrt(k))  # k·g / (g·√k)


def test_target_is_future_change_in_volatility_units():
    f = series_features(growth(), steps=3, group="metal")
    assert f.loc["2018-01-01", "y"] == pytest.approx(np.sqrt(3))
    assert f["y"].iloc[-3:].isna().all()  # no outcome yet for the last 3 months
    assert f["y"].iloc[-4:-3].notna().all()


def test_gap_to_12_month_average():
    f = series_features(growth(), steps=3, group="metal")
    assert f.loc["2018-01-01", "ma_gap"] == pytest.approx(5.5)  # 5.5 months of growth / g


def test_features_at_a_month_ignore_later_data():
    s = growth()
    changed = s.copy()
    changed.loc["2018-06-01":] *= 3
    a = series_features(s, steps=3, group="metal").loc[:"2018-05-01"].drop(columns="y")
    b = series_features(changed, steps=3, group="metal").loc[:"2018-05-01"].drop(columns="y")
    pd.testing.assert_frame_equal(a, b)


def test_steel_season_counts_march_up_june_july_down():
    f = series_features(growth(), steps=3, group="steel")
    assert f.loc["2018-02-01", "season"] == 1  # Mar, Apr, May
    assert f.loc["2018-05-01", "season"] == -2  # Jun, Jul, Aug
    other = series_features(growth(), steps=3, group="ppi")
    assert (other["season"] == 0).all()


def history() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    cols = {"S09": 0.01, "D01": 0.05, "L02": 0.03}
    h = pd.DataFrame(
        {c: 100 * np.exp(np.cumsum(rng.normal(0.002, sd, 60))) for c, sd in cols.items()},
        index=MONTHS,
    )
    h.loc[MONTHS[-1], "L02"] = np.nan  # ends one month early, like stainless
    return h


def test_dataset_has_one_row_per_series_and_month_with_all_features():
    d = build_dataset(history(), ["S09", "D01", "L02"], steps=3)
    assert set(FEATURES) <= set(d.columns)
    assert d.groupby("series")["month"].max().to_dict() == {
        "S09": MONTHS[-1],
        "D01": MONTHS[-1],
        "L02": MONTHS[-2],
    }


def test_market_momentum_is_average_across_series():
    d = build_dataset(history(), ["S09", "D01", "L02"], steps=3)
    month = d[d["month"] == MONTHS[30]]
    assert month["market_mom_3"].iloc[0] == pytest.approx(month["mom_3"].mean())


def test_group_dummies_and_ppi_interactions():
    d = build_dataset(history(), ["S09", "D01", "L02"], steps=3).dropna(subset=["mom_3"])
    s09, d01 = d[d["series"] == "S09"], d[d["series"] == "D01"]
    assert (s09["is_ppi"] == 1).all() and (d01["is_ppi"] == 0).all()
    assert (d01["is_metal"] == 1).all()
    np.testing.assert_allclose(s09["mom_3_ppi"], s09["mom_3"])
    assert (d01["mom_3_ppi"] == 0).all()


def epoxy_history(end: str) -> pd.DataFrame:
    """Epoxy rising 1 % a month with a wrong value in May 2026 (a known data error)."""
    months = pd.date_range("2024-01-01", end, freq="MS")
    h = pd.DataFrame({"EPX_RESIN": 100 * np.exp(0.01 * np.arange(len(months)))}, index=months)
    h.loc["2026-05-01", "EPX_RESIN"] = 1.0
    return h


def test_known_error_month_is_filled_from_its_neighbours():
    h = epoxy_history("2026-09-01")
    s = clean_series(h, "EPX_RESIN")
    expected = np.sqrt(h.loc["2026-04-01", "EPX_RESIN"] * h.loc["2026-06-01", "EPX_RESIN"])
    assert s["2026-05-01"] == pytest.approx(expected)
    assert s.index[-1] == pd.Timestamp("2026-09-01")


def test_known_error_in_the_last_month_ends_the_series_early():
    s = clean_series(epoxy_history("2026-05-01"), "EPX_RESIN")
    assert s.index[-1] == pd.Timestamp("2026-04-01")


def test_dataset_uses_the_cleaned_series():
    d = build_dataset(epoxy_history("2026-09-01"), ["EPX_RESIN"], steps=3)
    june = d[d["month"] == pd.Timestamp("2026-06-01")].iloc[0]
    assert june["mom_1"] == pytest.approx(1.0)  # one month of 1 % growth / 1 % volatility
