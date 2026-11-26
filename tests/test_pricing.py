import numpy as np
import pandas as pd
import pytest

from schneider_forecast import pricing
from schneider_forecast.config import ORIGIN

MONTHS = pd.date_range("2015-01-01", ORIGIN, freq="MS", name="month")


def make_prices(seed: int = 0) -> pd.DataFrame:
    """Independent random walks for three series, plus a French steel price level."""
    rng = np.random.default_rng(seed)
    steps = rng.normal(0, 0.04, size=(len(MONTHS), 3))
    prices = pd.DataFrame(
        1000 * np.exp(steps.cumsum(axis=0)), index=MONTHS, columns=["L01", "D01", "S11"]
    )
    prices["MEPS_FR_CR"] = prices["L01"] * 1.1
    prices["EPX_RESIN"] = 5000.0
    prices["S05"] = 3000.0  # zinc, $/t
    prices["S06"] = 1.5  # $ per €
    return prices


def make_bom() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_ref": ["RMAirSeT IIQ 24kV IEC"] * 3 + ["RM6_NE_IQI_433520"] * 4,
            "plant_country": ["HU"] * 3 + ["FR"] * 4,
            "material_label_source": ["Steel", "Copper", "Other", "Steel", "Copper"]
            + ["Epoxy Resin EU", "Brass"],
            "material_family": ["Carbon steel", "Copper", "Other", "Carbon steel", "Copper"]
            + ["Plastic", "Brass"],
            "share_pct": [0.5, 0.05, 0.1, 0.5, 0.2, 0.05, 0.02],
            "mass_kg": [100.0, 10.0, 20.0, 50.0, 20.0, 5.0, 2.0],
            "price_series": ["L01", "D01", np.nan, "L01", "D01", "S11", np.nan],
        }
    )


def flat_forecasts(prices: pd.DataFrame, width: float) -> pd.DataFrame:
    """P50 = last value, P10 / P90 = last value × (1 ∓ width) for every series and horizon."""
    rows = []
    for series in ["L01", "D01", "S11"]:
        last = prices[series].iloc[-1]
        for horizon in (3, 6, 9):
            rows.append((series, horizon, last * (1 - width), last, last * (1 + width)))
    return pd.DataFrame(rows, columns=["target_id", "horizon_m", "p10", "p50", "p90"])


def test_cost_weights_sum_to_one_and_skip_unpriced_lines():
    prices = make_prices()
    lines = pricing.cost_weights(make_bom(), prices)
    assert "Other" not in set(lines["material_family"])
    assert lines.groupby("product")["weight"].sum().round(10).eq(1).all()
    rm6 = lines[lines["product"] == "RM6"].set_index("series")
    assert rm6.loc["S11", "price_per_kg"] == pricing.PLASTIC_PRICE_PER_KG
    assert rm6.loc["L01", "price_per_kg"] == pytest.approx(prices["MEPS_FR_CR"].iloc[-1] / 1000)


def test_index_is_100_when_prices_do_not_move():
    lines = pricing.cost_weights(make_bom(), make_prices())
    ratios = pd.DataFrame({"L01": [1.0], "D01": [1.0], "S11": [1.0]})
    index = pricing.index_from_ratios(lines, ratios)
    assert index.round(10).eq(100).all().all()


def test_quantile_curve_goes_through_the_three_points_and_beyond():
    u = np.array([0.1, 0.5, 0.9, 0.0, 1.0])
    values = pricing.quantile_curve(u, -1.0, 0.0, 2.0)
    assert values[:3].tolist() == pytest.approx([-1.0, 0.0, 2.0])
    assert values[3] == pytest.approx(-1.25) and values[4] == pytest.approx(2.5)


def test_simulated_index_is_100_when_bands_have_no_width():
    prices = make_prices()
    lines = pricing.cost_weights(make_bom(), prices)
    draws = pricing.simulate_index(lines, flat_forecasts(prices, 0.0), prices, 6, n_draws=500)
    assert np.allclose(draws.to_numpy(), 100)


def test_index_band_is_narrower_than_adding_up_the_material_bands():
    prices = make_prices()
    lines = pricing.cost_weights(make_bom(), prices)
    draws = pricing.simulate_index(lines, flat_forecasts(prices, 0.2), prices, 6)
    p90 = pricing.index_scenarios({6: draws}).set_index("product")["p90"]
    # every material at its own P90 would give 120; independent materials rarely peak together
    assert (p90 < 120).all() and (p90 > 100).all()


def test_simulation_needs_a_forecast_for_every_series():
    prices = make_prices()
    lines = pricing.cost_weights(make_bom(), prices)
    forecasts = flat_forecasts(prices, 0.1).query("target_id != 'D01'")
    with pytest.raises(ValueError, match="D01"):
        pricing.simulate_index(lines, forecasts, prices, 3, n_draws=10)


def test_quote_rules_and_validity_follow_the_formulas():
    bridge = pd.DataFrame(
        {
            "product": ["A", "A", "A"],
            "horizon_m": [3, 6, 9],
            "price": [1000.0] * 3,
            "exposed_share": [0.1] * 3,
            "p10": [95.0, 90.0, 85.0],
            "p50": [102.0, 104.0, 106.0],
            "p90": [110.0, 130.0, 160.0],
        }
    )
    rules = pricing.quote_rules(bridge, margin=0.2, tolerance=0.1)
    first = rules.iloc[0]
    assert first["price_adjustment"] == pytest.approx(0.002)  # 0.1 × 2 %
    assert first["risk_buffer"] == pytest.approx(0.008)  # 0.1 × (110 − 102) %
    assert first["quote_with_buffer"] == pytest.approx(1010.0)
    # tolerance = 0.1 × 0.2 = 2 % of price; buffers are 0.8 % (+3), 2.6 % (+6): only +3 fits
    assert pricing.quote_validity(rules)["A"] == 3


def test_trigger_move_is_tolerance_over_exposed_weight():
    lines = pd.DataFrame(
        {"product": ["A", "A"], "series": ["D01", "L01"], "cost": [60.0, 40.0]}
    ).assign(weight=lambda t: t["cost"] / 100)
    triggers = pricing.index_triggers(lines, price=1000.0, margin=0.2, tolerance=0.1)
    copper = triggers.set_index("series").loc["D01"]
    assert copper["exposed_share"] == pytest.approx(0.1)
    assert copper["trigger_move"] == pytest.approx(0.02 / (0.1 * 0.6))


def test_sensitivity_cell_is_share_times_cost_rise_over_margin():
    bridge = pd.DataFrame(
        {"product": ["A"], "horizon_m": [6], "exposed_share": [0.08], "p90": [120.0]}
    )
    table = pricing.sensitivity_table(bridge)
    cell = table[(table["exposed_share"] == 0.17) & (table["margin"] == 0.20)]
    assert cell["margin_lost"].iloc[0] == pytest.approx(0.17 * 0.2 / 0.2)
    assert len(table) == (1 + len(pricing.SENSITIVITY_SHARES)) * len(pricing.SENSITIVITY_MARGINS)


def test_bom_index_rows_have_the_submission_columns():
    lines = pricing.cost_weights(make_bom(), make_prices())
    scenarios = pd.DataFrame(
        {
            "product": ["AirSeT", "RM6"] * 3,
            "horizon_m": [3, 3, 6, 6, 9, 9],
            "p10": 95.0,
            "p50": 100.0,
            "p90": 110.0,
        }
    )
    rows = pricing.bom_index_rows(scenarios, lines)
    assert len(rows) == 6
    assert set(rows["target_month"]) == {"2026-12", "2027-03", "2027-06"}
    assert set(rows["target_id"]) == {"RMAirSeT IIQ 24kV IEC", "RM6_NE_IQI_433520"}
    assert (rows["unit"] == "index (origin=100)").all()


def test_epoxy_option_prices_epoxy_on_the_resin_price():
    lines = pricing.cost_weights(make_bom(), make_prices(), epoxy_on_resin_price=True)
    epoxy = lines[lines["label"] == "Epoxy Resin EU"].iloc[0]
    assert epoxy["series"] == "EPX_RESIN" and epoxy["price_per_kg"] == pytest.approx(5.0)


def test_plastic_prices_option_matches_the_label():
    lines = pricing.cost_weights(make_bom(), make_prices(), plastic_prices={"Epoxy": 7.0})
    assert lines.set_index("label").loc["Epoxy Resin EU", "price_per_kg"] == 7.0


def test_brass_option_mixes_copper_and_zinc():
    prices = make_prices()
    lines = pricing.cost_weights(make_bom(), prices, brass_proxy=True)
    brass = lines[lines["material_family"] == "Brass"].iloc[0]
    expected = (0.63 * prices["D01"].iloc[-1] + 0.37 * 3000 / 1.5) / 1000
    assert brass["series"] == "D01" and brass["price_per_kg"] == pytest.approx(expected)


def test_flat_line_keeps_its_cost_and_damps_the_index():
    lines = pricing.cost_weights(make_bom(), make_prices(), other_flat_price=4.0)
    airset = lines[lines["product"] == "AirSeT"].set_index("series")
    assert airset.loc[pricing.FLAT, "cost"] == pytest.approx(80.0)  # 20 kg × 4 €
    ratios = pd.DataFrame({"L01": [2.0], "D01": [2.0], "S11": [2.0]})
    index = pricing.index_from_ratios(lines, ratios)["AirSeT"].iloc[0]
    assert index == pytest.approx(100 * (2 - airset.loc[pricing.FLAT, "weight"]))


def test_fill_missing_mass_uses_the_share_of_the_product_mass():
    bom = make_bom()
    bom.loc[3, "mass_kg"] = np.nan  # RM6 steel unknown, as in the older BOMs
    filled = pricing.fill_missing_mass(bom)
    # RM6 mass ÷ share on the other lines: 100, 100, 100 → 0.45 × 100
    assert filled.loc[3, "mass_kg"] == pytest.approx(45.0)


def test_harness_file_keeps_only_the_origin_rows_and_renames_columns():
    harness = pd.DataFrame(
        {
            "model": ["m", "m"],
            "target": ["L01", "L01"],
            "origin": ["2026-06-01", f"{ORIGIN}-01"],
            "horizon": [3, 3],
            "p10": [1.0, 2.0],
            "p50": [1.5, 2.5],
            "p90": [2.0, 3.0],
        }
    )
    table = pricing.to_pricing_columns(harness)
    assert len(table) == 1 and table["p50"].iloc[0] == 2.5
    assert {"target_id", "horizon_m", "model_name"} <= set(table.columns)


def test_submission_layout_passes_through_and_bad_files_are_refused():
    table = pricing.to_pricing_columns(
        pd.DataFrame({"target_id": ["D01"], "horizon_m": [6], "p10": [1], "p50": [2], "p90": [3]})
    )
    assert table["model_name"].iloc[0] == "not given"
    with pytest.raises(ValueError, match="p90"):
        pricing.to_pricing_columns(pd.DataFrame({"target_id": ["D01"], "horizon_m": [6]}))


def test_crisis_factor_grows_when_recent_volatility_is_high_and_never_shrinks():
    prices = make_prices()
    calm = pricing.crisis_factors(pricing.cost_weights(make_bom(), prices), prices)
    stormy_prices = prices.copy()
    shocks = np.where(np.arange(12) % 2 == 0, 1.4, 0.7)  # big swings in the last 12 months
    stormy_prices.iloc[-12:, :3] = stormy_prices.iloc[-13, :3].to_numpy() * shocks[:, None]
    stormy = pricing.crisis_factors(pricing.cost_weights(make_bom(), stormy_prices), stormy_prices)
    assert (calm >= 1).all()
    assert (stormy > 2).all()


def test_crisis_factor_scales_the_risk_buffer():
    bridge = pd.DataFrame(
        {
            "product": ["A"],
            "horizon_m": [3],
            "price": [1000.0],
            "exposed_share": [0.1],
            "p10": [95.0],
            "p50": [100.0],
            "p90": [110.0],
        }
    )
    rules = pricing.quote_rules(bridge, crisis=pd.Series({"A": 2.0}))
    assert rules["band_buffer"].iloc[0] == pytest.approx(0.01)
    assert rules["risk_buffer"].iloc[0] == pytest.approx(0.02)
    assert rules["quote_with_buffer"].iloc[0] == pytest.approx(1020.0)


def test_replay_compares_the_three_pricing_policies():
    prices = make_prices()
    share = pd.Series({"AirSeT": 0.1, "RM6": 0.1})
    catalog = pd.DataFrame({"gap_months": 0, "pub_lag": 0}, index=prices.columns)
    replay = pricing.replay_quotes(
        make_bom(), prices, catalog, share, horizon=3, start="2018-01", end="2018-06", n_draws=200
    )
    assert len(replay) == 6 * 2  # 6 quote months × 2 products
    fixed = 0.1 * (replay["actual_index"] / 100 - 1) / pricing.MARGIN
    assert np.allclose(replay["margin_lost_fixed_price"], fixed)
    # the crisis factor is never below 1, so the crisis buffer never covers less
    assert (replay["margin_lost_crisis_buffer"] <= replay["margin_lost_band_buffer"] + 1e-12).all()
    summary = pricing.replay_summary(replay)
    assert set(summary["policy"]) == set(pricing.REPLAY_POLICIES)
    assert (summary["avg_overpriced"] >= 0).all()


def test_replay_periods_follow_the_purchase_month():
    assert pricing.replay_period(pd.Timestamp("2020-12-01")) == "2020"
    assert pricing.replay_period(pd.Timestamp("2021-01-01")) == "2021-22"
    assert pricing.replay_period(pd.Timestamp("2023-03-01")) == "2023-24"


def test_index_backtest_scores_our_index_against_the_naive_index():
    prices = make_prices()
    catalog = pd.DataFrame({"gap_months": 0, "pub_lag": 0}, index=prices.columns)
    rows = []
    for origin in pd.date_range("2019-01-01", "2019-06-01", freq="MS"):
        target_month = origin + pd.DateOffset(months=3)
        for series in ["L01", "D01", "S11"]:
            last, actual = prices.loc[origin, series], prices.loc[target_month, series]
            rows.append(
                {
                    "model": "m",
                    "target": series,
                    "origin": origin,
                    "horizon": 3,
                    "target_month": target_month,
                    "p10": last * 0.9,
                    "p50": last,
                    "p90": last * 1.1,
                    "actual": actual,
                    "last_value": last,
                    "flagged": False,
                }
            )
    results = pricing.index_backtest(pd.DataFrame(rows), make_bom(), prices, catalog, n_draws=200)
    assert len(results) == 6 * 2 * 2  # origins × products × (ours, naive)
    naive = results[results["model"] == pricing.NAIVE_MODEL]
    assert (naive["p50"] == 100).all()
    assert (results["p10"] <= results["p50"]).all() and (results["p50"] <= results["p90"]).all()
    scores = pricing.index_backtest_scores(results)
    assert {"skill_interval_score", "coverage"} <= set(scores.columns)


def test_forecasts_from_two_team_files_are_stacked_and_gaps_get_placeholders(tmp_path):
    prices = make_prices()
    columns = ["target_id", "origin_month", "horizon_m", "p10", "p50", "p90", "model_name"]
    steel, copper = prices["L01"].iloc[-1], prices["D01"].iloc[-1]
    p2 = pd.DataFrame(
        [["L01", "2026-09", 3, steel * 0.9, steel, steel * 1.1, "steel"]], columns=columns
    )
    p3 = pd.DataFrame(
        [["D01", "2026-09", 3, copper * 0.9, copper, copper * 1.1, "copper"]], columns=columns
    )
    p2.to_csv(tmp_path / "p2.csv", index=False)
    p3.to_csv(tmp_path / "p3.csv", index=False)
    files = (tmp_path / "p2.csv", tmp_path / "p3.csv", tmp_path / "missing.csv")
    with pytest.warns(UserWarning, match="S11"):
        table = pricing.load_forecasts(prices, ["L01", "D01", "S11"], files=files)
    models = table.set_index(["target_id", "horizon_m"])["model_name"]
    assert models[("L01", 3)] == "steel" and models[("D01", 3)] == "copper"
    assert (table[table["target_id"] == "S11"]["model_name"] == "placeholder_rw_vol").all()


def test_team_backtest_files_are_stacked_without_rerunning(tmp_path):
    row = {
        "model": "m",
        "origin": "2020-01-01",
        "horizon": 3,
        "target_month": "2020-04-01",
        "p10": 1.0,
        "p50": 2.0,
        "p90": 3.0,
        "actual": 2.0,
        "last_value": 2.0,
        "flagged": False,
    }
    pd.DataFrame([{**row, "target": "L01"}]).to_csv(tmp_path / "p2.csv", index=False)
    pd.DataFrame([{**row, "target": "D01"}, {**row, "target": "S99"}]).to_csv(
        tmp_path / "p3.csv", index=False
    )
    table = pricing.load_material_backtest(
        ["L01", "D01"], files=(tmp_path / "p2.csv", tmp_path / "p3.csv")
    )
    assert sorted(table["target"]) == ["D01", "L01"]  # S99 is not a BOM series
    assert table["origin"].dtype.kind == "M"


def test_forecasts_with_crossed_quantiles_or_wrong_units_are_refused():
    crossed = pd.DataFrame(
        {"target_id": ["L01"], "horizon_m": [3], "p10": [5], "p50": [4], "p90": [6]}
    )
    with pytest.raises(ValueError, match="P10"):
        pricing.to_pricing_columns(crossed)
    prices = make_prices()
    rebased = pd.DataFrame(
        {"target_id": ["L01"], "horizon_m": [3], "p10": [0.9], "p50": [1.0], "p90": [1.1]}
    )
    with pytest.raises(ValueError, match="own unit"):
        pricing.check_units(rebased, prices.assign(L01=1000.0))


def test_replay_only_uses_data_published_by_the_quote_month():
    prices = make_prices()
    catalog = pd.DataFrame({"gap_months": 0, "pub_lag": 0}, index=prices.columns)
    catalog.loc["L01", "pub_lag"] = 2  # L01 is published two months late
    share = pd.Series({"AirSeT": 0.1, "RM6": 0.1})
    quote = pd.Timestamp("2018-06-01")
    replay = pricing.replay_quotes(
        make_bom(), prices, catalog, share, horizon=3, start="2018-06", end="2018-06", n_draws=100
    )
    # the realised move must start from L01's last published value (April), not June's
    known = prices.loc[:quote].copy()
    known.loc[known.index > pd.Timestamp("2018-04-01"), "L01"] = np.nan
    lines = pricing.cost_weights(make_bom(), known)
    expected = pricing.actual_index(lines, known, prices, quote, 3)
    got = replay.set_index("product")["actual_index"]
    assert got["AirSeT"] == pytest.approx(expected["AirSeT"])
