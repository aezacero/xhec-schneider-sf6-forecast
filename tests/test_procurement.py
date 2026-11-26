import numpy as np
import pandas as pd
import pytest

from schneider_forecast import procurement as P


def pitchbook_sheet(rows: dict[str, list], periods=("Dec 2024", "Dec 2023")) -> pd.DataFrame:
    """A small sheet laid out like the PitchBook exports: labels in column 2, values from 12."""
    sheet = pd.DataFrame(np.nan, index=range(10 + len(rows)), columns=range(14), dtype=object)
    sheet.iat[4, 2] = "Company: Secret Name Ltd"
    for k, period in enumerate(periods):
        sheet.iat[P.PERIOD_ROW, P.FIRST_VALUE_COLUMN + k] = period
    for i, (label, values) in enumerate(rows.items(), start=10):
        sheet.iat[i, P.LABEL_COLUMN] = f"    {label}"
        for k, value in enumerate(values):
            sheet.iat[i, P.FIRST_VALUE_COLUMN + k] = value
    return sheet


def write_supplier(path, ratios: dict[str, list], revenue: list | None) -> None:
    with pd.ExcelWriter(path) as writer:
        pitchbook_sheet(ratios).to_excel(writer, sheet_name="Ratios", header=False, index=False)
        if revenue is not None:
            pitchbook_sheet({"Total Revenue": revenue}).to_excel(
                writer, sheet_name="Income Statement", header=False, index=False
            )


STRONG = {
    "EBITDA Margin": [0.15, 0.12],
    "Current Ratio": [1.8, 1.7],
    "Quick Ratio": [0.9, 0.8],
    "Total Debt to Equity": [0, 0],
    "Interest Coverage": [np.nan, 9.0],
}


def test_latest_value_takes_the_newest_filled_year():
    sheet = pitchbook_sheet({"Current Ratio": [np.nan, 1.4]})
    value, period = P.latest_value(sheet, "Current Ratio")
    assert value == 1.4 and period == "Dec 2023"
    assert np.isnan(P.latest_value(sheet, "Quick Ratio")[0])


@pytest.mark.parametrize(
    ("changes", "group"),
    [
        ({}, "strong"),
        ({"ebitda_margin": -0.02}, "fragile"),
        ({"current_ratio": 0.9}, "fragile"),
        ({"interest_coverage": 1.0}, "fragile"),
        ({"ebitda_margin": 0.07}, "watch"),
        ({"interest_coverage": np.nan, "debt_to_equity": 0.5}, "watch"),
        ({"interest_coverage": np.nan, "debt_to_equity": np.nan}, "strong"),
    ],
)
def test_strength_groups_follow_the_rules(changes, group):
    values = {
        "ebitda_margin": 0.15,
        "current_ratio": 1.8,
        "debt_to_equity": 0.3,
        "interest_coverage": 9.0,
    }
    values.update(changes)
    assert P.strength_group(pd.Series(values)) == group


def test_supplier_table_hides_names_and_handles_gaps(tmp_path):
    write_supplier(
        tmp_path / "PitchBook_-_Secret_Name_Ltd_Company_Financials.xlsx", STRONG, [5000, 4000]
    )
    write_supplier(tmp_path / "PitchBook_-_Other_Firm_Company_Financials.xlsx", STRONG, None)
    table = P.supplier_strength(tmp_path)
    assert table["supplier"].tolist() == ["Supplier 1", "Supplier 2"]
    text = table.to_csv().lower()
    assert "secret" not in text and "other firm" not in text
    assert table.loc[1, "revenue_m_eur"] == 5.0  # files sorted by name; kEUR → € m
    assert np.isnan(table.loc[0, "revenue_m_eur"])  # no income statement
    assert table["debt_to_equity"].isna().all()  # 0 means "not reported"
    assert table.loc[0, "interest_coverage"] == 9.0  # newest filled year
    assert (table["group"] == "strong").all()


def test_back_to_back_links_steel_indices_to_our_series_and_triggers():
    parts = pd.DataFrame(
        {
            "buy_index": ["CR France", "CR France", "HDG Germany", "HR Spain"],
            "kind": ["CR", "CR", "HDG", "HR"],
            "country": ["France", "France", "Germany", "Spain"],
            "lead_time": [1, 1, 1, np.nan],
            "plant": ["France", "France", "Hungary", "Spain"],
        }
    )
    triggers = pd.DataFrame(
        {
            "product": ["RM6", "RM6", "RM6", "AirSeT"],
            "series": ["L01", "L03", "D01", "D01"],
            "trigger_move": [2.0, 14.0, 0.5, 0.7],
        }
    )
    table = P.back_to_back_table(parts, triggers).set_index("buy_index")
    assert table.loc["CR France", "parts"] == 2 and table.loc["CR France", "our_series"] == "L01"
    assert table.loc["CR France", "sell_trigger_RM6"] == 2.0
    assert pd.isna(table.loc["HR Spain", "our_series"])
    assert table["share_of_parts"].sum() == pytest.approx(1.0)
    metals = P.copper_and_aluminium_rows(triggers).set_index("our_series")
    assert metals.loc["D01", "sell_trigger_AirSeT"] == 0.7
