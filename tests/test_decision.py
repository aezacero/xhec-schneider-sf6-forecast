import pandas as pd
import pytest

from schneider_forecast import decision as D


@pytest.fixture(scope="module")
def demo():
    inputs = D.demo_inputs()
    return inputs, D.build_model(inputs, n_draws=2_000)


def test_demo_mode_is_forced_by_the_env_var(monkeypatch):
    monkeypatch.setenv("SCHNEIDER_DEMO", "1")
    assert D.use_demo()


def test_quote_is_list_price_plus_adjustment_plus_buffer(demo):
    inputs, model = demo
    price = D.default_price(inputs)
    for scenario in D.SCENARIOS:
        q = D.quote(model, "RM6", 6, price, 0.2, scenario)
        assert q["quote"] == pytest.approx(price + q["price_adjustment"] + q["safety_buffer"])
    down = D.quote(model, "RM6", 6, price, 0.2, "Downside")
    up = D.quote(model, "RM6", 6, price, 0.2, "Upside")
    assert up["quote"] < down["quote"]
    assert down["safe_validity_months"] in (0, 3, 6, 9)


def test_what_if_without_moves_keeps_the_list_price(demo):
    _, model = demo
    flat = D.what_if(model, "AirSeT", 12_000.0, 0.2, 0.0, 0.0)
    assert flat["price_needed"] == pytest.approx(12_000.0)
    up = D.what_if(model, "AirSeT", 12_000.0, 0.2, 0.3, 0.0)
    assert up["cost_change"] > 0 and up["price_needed"] > 12_000.0


def test_quote_summary_has_one_row_per_item(demo):
    inputs, model = demo
    q = D.quote(model, "AirSeT", 3, 12_000.0, 0.2, "Baseline")
    table = D.quote_summary(q, demo=True)
    assert list(table.columns) == ["item", "value"]
    assert table["item"].is_unique
    assert "Demo" in set(table["value"])


def test_replay_view_reads_one_quote():
    replay = pd.DataFrame(
        {
            "product": ["RM6"],
            "quote_month": [pd.Timestamp("2021-03-01")],
            "target_month": [pd.Timestamp("2021-09-01")],
            "p50": [101.0],
            "p90": [110.0],
            "actual_index": [125.0],
            "margin_lost_fixed_price": [0.4],
            "margin_lost_band_buffer": [0.1],
        }
    )
    view = D.replay_view(replay, "RM6", pd.Timestamp("2021-03-01"))
    assert view["actual"] == pytest.approx(0.25)
    assert (view["fixed"], view["buffer"], view["indexation"]) == (0.4, 0.1, 0.0)


def test_page_tables_on_demo_data(demo):
    inputs, model = demo
    fan = D.index_fan(model, "RM6")
    assert list(fan["horizon_m"]) == [0, 3, 6, 9] and fan["p50"].iloc[0] == 100.0
    assert (fan["p10"] <= fan["p50"]).all() and (fan["p50"] <= fan["p90"]).all()
    risk = D.material_risk(inputs, model, "RM6", 9)
    assert risk["eur_at_risk"].is_monotonic_decreasing and risk["weight"].sum() == pytest.approx(1)
    forecast, placeholder = D.material_forecast(inputs, "D01")
    assert placeholder and len(forecast) == 3
    assert D.material_skill("D01", demo=True).empty and D.index_skill("RM6", demo=True).empty
    gap = D.sf6_gap(model)
    assert gap["p50"].iloc[0] == pytest.approx(
        model.lines.groupby("product")["cost"].sum().pipe(lambda c: c["AirSeT"] - c["RM6"])
    )
