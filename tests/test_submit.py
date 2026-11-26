import pandas as pd
import pytest

from schneider_forecast import submit
from schneider_forecast.config import ORIGIN

MONTHS = pd.date_range("2026-01-01", ORIGIN, freq="MS", name="month")
TARGET_MONTHS = {3: "2026-12", 6: "2027-03", 9: "2027-06"}
TARGETS = ("L01", "S09", "S06")  # the made-up material targets below


def make_prices() -> pd.DataFrame:
    return pd.DataFrame({"L01": 800.0, "S09": 105.0, "S06": 1.15}, index=MONTHS)


def make_catalog() -> pd.DataFrame:
    return pd.DataFrame(
        {"region": ["EU", "EU-DE", "WW (US)"]},
        index=pd.Index(["L01", "S09", "S06"], name="series_id"),
    )


def material_rows(series: str, unit: str, middle: float, model: str = "random_walk") -> list[dict]:
    return [
        {
            "target_type": "material",
            "target_id": series,
            "origin_month": ORIGIN,
            "horizon_m": h,
            "target_month": TARGET_MONTHS[h],
            "unit": unit,
            "p10": middle * 0.9,
            "p50": middle,
            "p90": middle * 1.1,
            "model_name": model,
        }
        for h in (3, 6, 9)
    ]


def make_materials() -> pd.DataFrame:
    return pd.DataFrame(
        material_rows("L01", "EUR/t", 800.0, "meps_pooled")
        + material_rows("S09", "Index 2021=100", 105.0)
        + material_rows("S06", "USD per EUR", 1.15, "chronos2")
    )


def make_bom_rows() -> pd.DataFrame:
    rows = []
    for product in submit.PRODUCTS:
        for h in (3, 6, 9):
            rows.append(
                {
                    "target_type": "bom_index",
                    "target_id": product,
                    "region": "EU",
                    "origin_month": ORIGIN,
                    "horizon_m": h,
                    "target_month": TARGET_MONTHS[h],
                    "unit": "index (origin=100)",
                    "p10": 95.0,
                    "p50": 100.0,
                    "p90": 110.0,
                    "model_name": "bom_joint_sim_v1",
                }
            )
    return pd.DataFrame(rows)


def build() -> pd.DataFrame:
    return submit.build_submission(make_materials(), make_bom_rows(), make_prices(), make_catalog())


def test_build_gives_the_format_columns_and_passes_the_checks():
    table = build()
    assert list(table.columns) == submit.COLUMNS
    assert len(table) == 9 + 6
    assert (table["team_id"] == submit.TEAM_ID).all()
    assert submit.TEAM_ID == "team_05"
    submit.check_submission(table, targets=TARGETS)


def test_eur_rows_keep_prices_and_other_units_become_an_index():
    table = build().set_index(["target_id", "horizon_m"])
    assert table.loc[("L01", 3), "unit"] == "EUR/t"
    assert table.loc[("L01", 3), "p50"] == 800.0
    assert table.loc[("S09", 6), "unit"] == "index (origin=100)"
    assert table.loc[("S09", 6), "p50"] == pytest.approx(100.0)
    assert table.loc[("S06", 9), "p90"] == pytest.approx(110.0)


def test_regions_are_simplified_to_eu_or_ww():
    regions = build().drop_duplicates("target_id").set_index("target_id")["region"]
    assert regions["S09"] == "EU" and regions["S06"] == "WW"
    with pytest.raises(ValueError, match="unknown region"):
        submit.simple_region("Asia")


def test_ai_tools_name_chronos_when_the_model_uses_it():
    assert submit.ai_tools("chronos2") == "chronos-2; claude-code"
    assert submit.ai_tools("random_walk") == "claude-code"


def test_file_name_follows_the_format():
    assert submit.output_path().name == "team_05_forecast_202609.csv"


@pytest.mark.parametrize(
    ("break_it", "message"),
    [
        (lambda t: t.drop(columns="ai_tools"), "missing columns"),
        (lambda t: t.assign(model_name=[""] + list(t["model_name"][1:])), "blank cells"),
        (lambda t: pd.concat([t, t.iloc[[0]]]), "duplicate rows"),
        (lambda t: t.assign(horizon_m=t["horizon_m"].replace(9, 12)), "horizons"),
        (lambda t: t.assign(p10=t["p90"] + 1), "P10 ≤ P50 ≤ P90"),
        (lambda t: t[t["target_type"] == "material"], "bom_index rows"),
        (lambda t: t.assign(unit="USD/t"), "unit not allowed"),
        (lambda t: t.assign(origin_month="2026-08"), "origin_month"),
    ],
)
def test_checks_catch_each_problem(break_it, message):
    with pytest.raises(ValueError, match=message):
        submit.check_submission(break_it(build()), targets=TARGETS)


def test_missing_forecast_file_stops_the_build(tmp_path):
    with pytest.raises(FileNotFoundError, match="missing forecast files"):
        submit.read_csvs([tmp_path / "p2_forecasts_202609.csv"])


def test_a_missing_material_target_is_caught():
    table = build()
    with pytest.raises(ValueError, match=r"missing \['S06'\]"):
        submit.check_submission(table[table["target_id"] != "S06"], targets=TARGETS)
