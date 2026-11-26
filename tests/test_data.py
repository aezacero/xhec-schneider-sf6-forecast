import numpy as np
import pandas as pd
import pytest

from schneider_forecast.data import (
    build_catalog,
    clean_bom,
    cut_at_origin,
    parse_cru_stainless,
    parse_meps,
    run_checks,
    target_ids,
    to_month_start,
    to_numbers,
)


def test_to_month_start_labels_any_day_with_its_month():
    idx = to_month_start(pd.Index(["2024-03-15", "2024-04-03", "2024-05-01"]))
    assert list(idx.day) == [1, 1, 1]
    assert list(idx.month) == [3, 4, 5]


def test_cut_at_origin_keeps_the_origin_month():
    df = pd.DataFrame({"x": range(4)}, index=pd.date_range("2026-08-01", periods=4, freq="MS"))
    assert cut_at_origin(df, "2026-09").index.max() == pd.Timestamp("2026-09-01")


def test_to_numbers_fails_on_unreadable_cells():
    assert to_numbers(pd.DataFrame({"a": ["1", 2.5, None]}))["a"].tolist()[:2] == [1.0, 2.5]
    with pytest.raises(ValueError, match="Unreadable"):
        to_numbers(pd.DataFrame({"a": ["1,234", 2.0]}))


def test_parse_meps_rebuilds_header_and_fills_l01_l03():
    raw = pd.DataFrame(
        [
            ["MEPS", "Germany", None, None, "x", "France"],
            [None] * 6,
            [None] * 6,
            [None] * 6,
            ["Month", "HR coil", "CR coil", "HDG coil", None, "CR coil"],
            ["2026-08-01", 600, 700, 750, None, 690],
            ["2026-09-01", "610", 710, 760, None, 700],
            ["2026-10-01", None, None, None, None, None],
        ]
    )
    meps = parse_meps(raw)
    assert list(meps.columns) == ["MEPS_DE_HR", "L01", "L03", "MEPS_FR_CR"]
    assert meps.index.max() == pd.Timestamp("2026-09-01")  # empty month dropped
    assert meps.loc["2026-09-01", "MEPS_DE_HR"] == 610  # text converted to number


def test_parse_cru_stainless_adds_base_and_alloy():
    raw = pd.DataFrame(
        [
            ["CRU Stainless", "Germany", None, None, None],
            [None, "Grade 304", None, "Grade 430", None],
            [None] * 5,
            [None] * 5,
            ["Month", "BASE", "Alloy", "BASE", "Alloy"],
            ["2026-07-15", 1200, 1500, 1300, 300],
            ["2026-08-15", -100, 2800, 1300, 310],
        ]
    )
    l02 = parse_cru_stainless(raw)
    assert l02.name == "L02"
    assert list(l02.index) == [pd.Timestamp("2026-07-01"), pd.Timestamp("2026-08-01")]
    assert list(l02) == [2700, 2700]


def _bom() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_ref": ["RM6_X", "RM6_X", "RMAirSeT Y", "Total mass"],
            "plant_code": ["ETO_FR0900", "ETO_FR0900", "ETO_HU1100", None],
            "plant_name": ["a", "a", "b", None],
            "material_family": ["Carbon steel (to confirm)", "Copper", "Carbon steel", None],
            "share_pct": [np.nan, 0.25, 0.5, np.nan],
            "mass_kg": [np.nan, 50.0, 100.0, np.nan],
            "eu_series_ids": ["L01;S09", "D01;S07;L08", "L01;S09", None],
            "ww_series_ids": ["S04;S12", "S01", "S04;S12", None],
        }
    )


def test_clean_bom_keeps_material_rows_with_plant_country_and_price_series():
    bom = clean_bom(_bom(), pd.Index(["L01", "D01", "S09"]))
    assert len(bom) == 3  # total row dropped
    assert "plant_name" not in bom.columns
    assert list(bom["plant_country"]) == ["FR", "FR", "HU"]
    assert list(bom["price_series"]) == ["L01", "D01", "L01"]


def test_clean_bom_leaves_lines_without_a_series_unpriced():
    raw = _bom()
    raw.loc[1, ["eu_series_ids", "ww_series_ids"]] = np.nan  # e.g. brass
    assert pd.isna(clean_bom(raw, pd.Index(["L01"])).loc[1, "price_series"])


def test_target_ids_keeps_series_with_data_plus_extra_targets():
    available = pd.Index(["L01", "S01", "S09", "E01", "EPX_RESIN"])
    assert target_ids(_bom(), available) == ["EPX_RESIN", "L01", "S01", "S09"]


def test_build_catalog_fails_without_publication_lag():
    prices = pd.DataFrame({"NOT_IN_CONFIG": [1.0]}, index=pd.to_datetime(["2026-09-01"]))
    with pytest.raises(ValueError, match="publication lag"):
        build_catalog(prices, [], pd.DataFrame(columns=["source", "material", "region", "unit"]))


def test_build_catalog_measures_gap_to_origin():
    months = pd.date_range("2026-06-01", "2026-09-01", freq="MS")
    prices = pd.DataFrame({"S01": [1.0, 2, 3, 4], "L02": [1.0, 2, 3, np.nan]}, index=months)
    meta = pd.DataFrame(columns=["source", "material", "region", "unit"])
    catalog = build_catalog(prices, ["S01", "L02"], meta)
    assert catalog.loc["S01", "gap_months"] == 0
    assert catalog.loc["L02", "gap_months"] == 1
    assert list(catalog["needs_nowcast"]) == [False, True]


def _valid_inputs():
    months = pd.date_range("2026-01-01", "2026-09-01", freq="MS")
    prices = pd.DataFrame({"S01": np.linspace(9000, 10000, len(months))}, index=months)
    catalog = pd.DataFrame(
        {"is_target": [True], "first": [months[0]], "last": [months[-1]]}, index=["S01"]
    )
    return prices, catalog


def test_run_checks_passes_on_consistent_data():
    run_checks(*_valid_inputs(), expected_targets=("S01",))


def test_run_checks_reports_every_failure():
    prices, catalog = _valid_inputs()
    prices.loc[pd.Timestamp("2026-10-01")] = 9500.0  # after the origin
    prices.iloc[3, 0] = np.nan  # gap inside the target
    prices.iloc[4, 0] = -1.0  # not positive
    with pytest.raises(ValueError) as err:
        run_checks(prices, catalog, expected_targets=("S01", "L01"))
    message = str(err.value)
    assert "after the origin" in message
    assert "missing ['L01']" in message
    assert "gap(s)" in message
    assert "≤ 0" in message
