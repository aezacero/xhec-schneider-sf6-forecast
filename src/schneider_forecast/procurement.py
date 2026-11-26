"""Procurement levers (Goal B, B4) from the supplier balance sheets and Schneider's parts mapping.

Two tables, written to data/processed/:
1. supplier_strength.csv: each supplier's latest financial ratios, a strength group (strong /
   watch / fragile) and the negotiation lever that fits it. Suppliers are numbered 1-9 in file
   order; their names never leave this module.
2. back_to_back_indexation.csv: which steel index Schneider already uses to buy each part (663
   parts), next to the index and trigger our quote rules use to sell. Same index on both
   sides = the margin is protected when prices jump (2021 replay).

Run: uv run python -m schneider_forecast.procurement  (after schneider_forecast.pricing)
"""

import glob

import numpy as np
import pandas as pd

from schneider_forecast.config import DATA_PROCESSED, DATA_RAW, STEEL_WORKBOOK

SUPPLIER_FOLDER = DATA_RAW / "supplier_balance_sheets"
LABEL_COLUMN = 2  # PitchBook sheets: row labels in column 2
FIRST_VALUE_COLUMN = 12  # values from here on, newest year first
PERIOD_ROW = 5  # e.g. "Dec 2024"

RATIOS = {
    "EBITDA Margin": "ebitda_margin",
    "Current Ratio": "current_ratio",
    "Quick Ratio": "quick_ratio",
    "Total Debt to Equity": "debt_to_equity",
    "Interest Coverage": "interest_coverage",
}

# strength groups, plain rules (thresholds are common credit rules of thumb)
FRAGILE_IF = {"ebitda_margin": 0.0, "current_ratio": 1.0, "interest_coverage": 1.5}  # below any
STRONG_IF = {"ebitda_margin": 0.10, "current_ratio": 1.2, "interest_coverage": 5.0}  # all met
LEVERS = {
    "strong": "Long contract with prices tied to a public index; ask for index-only price changes",
    "watch": "Index-tied contract with a quarterly review; keep a second source qualified",
    "fragile": "Do not squeeze on price; dual-source, short commitments, review finances often",
}

# buy-side steel index (parts mapping) → the series our pricing uses
STEEL_KIND_TO_SERIES = {"CR": "L01", "HDG": "L03"}
MATERIAL_NAMES = {
    "CR": "Cold-rolled coil",
    "HDG": "Hot-dip galvanised coil",
    "HR": "Hot-rolled coil",
    "EZ": "Electro-galvanised coil",
}


# ---- 1. supplier strength ----


def latest_value(sheet: pd.DataFrame, label: str) -> tuple[float, str]:
    """Newest filled value of a row and its period ('Dec 2024'); NaN if the row is empty."""
    labels = sheet[LABEL_COLUMN].astype(str).str.strip()
    rows = sheet[labels == label]
    if rows.empty:
        return np.nan, ""
    values = pd.to_numeric(rows.iloc[0, FIRST_VALUE_COLUMN:], errors="coerce").dropna()
    if values.empty:
        return np.nan, ""
    return float(values.iloc[0]), str(sheet.iat[PERIOD_ROW, values.index[0]])


def read_supplier(path: str, number: int) -> dict:
    """One supplier's latest ratios and revenue, under a number instead of its name."""
    sheets = pd.read_excel(path, sheet_name=None, header=None)  # some files lack a sheet
    record = {"supplier": f"Supplier {number}"}
    for label, name in RATIOS.items():
        record[name], period = latest_value(sheets["Ratios"], label)
        if name == "ebitda_margin":
            record["latest_year"] = period
    revenue = np.nan
    income = sheets.get("Income Statement")
    for label in ("Total Revenue", "Revenue"):
        if income is not None and np.isnan(revenue):
            revenue, _ = latest_value(income, label)
    record["revenue_m_eur"] = revenue / 1000  # files are in thousands of EUR
    # a total debt to equity of exactly 0 is how these exports show "not reported"
    if record["debt_to_equity"] == 0:
        record["debt_to_equity"] = np.nan
    return record


def strength_group(row: pd.Series) -> str:
    """fragile if any red flag; strong if every strength test is met (missing coverage counts as
    met only when the supplier reports no debt); watch otherwise."""
    for name, limit in FRAGILE_IF.items():
        if pd.notna(row[name]) and row[name] < limit:
            return "fragile"
    for name, limit in STRONG_IF.items():
        value = row[name]
        if pd.isna(value):
            if name == "interest_coverage" and pd.isna(row["debt_to_equity"]):
                continue
            return "watch"
        if value < limit:
            return "watch"
    return "strong"


def supplier_strength(folder=SUPPLIER_FOLDER) -> pd.DataFrame:
    """Anonymised table: one row per supplier, its ratios, group and lever."""
    files = sorted(glob.glob(str(folder / "*.xlsx")))
    table = pd.DataFrame([read_supplier(path, k) for k, path in enumerate(files, 1)])
    table["group"] = table.apply(strength_group, axis=1)
    table["lever"] = table["group"].map(LEVERS)
    columns = ["supplier", "latest_year", "revenue_m_eur", *RATIOS.values(), "group", "lever"]
    return table[columns]


# ---- 2. back-to-back indexation ----


def read_parts_mapping(path=STEEL_WORKBOOK) -> pd.DataFrame:
    """Schneider's purchased steel parts: index used to buy, lead time, plant country.
    Plant and part names are dropped."""
    parts = pd.read_excel(path, sheet_name="Reference to Index Mapping", header=1)
    parts.columns = [str(c).strip() for c in parts.columns]
    parts = parts.rename(
        columns={"Index": "buy_index", "Lead Time (Months)": "lead_time", "Plant country": "plant"}
    )
    parts["buy_index"] = parts["buy_index"].astype(str).str.strip()
    parts = parts[parts["buy_index"].ne("nan")]
    parts["kind"] = parts["buy_index"].str.split().str[0]
    parts["country"] = parts["buy_index"].str.split(n=1).str[1]
    return parts[["buy_index", "kind", "country", "lead_time", "plant"]]


def back_to_back_table(parts: pd.DataFrame, triggers: pd.DataFrame) -> pd.DataFrame:
    """One row per buy-side steel index: how many parts use it, their lead time, and the series
    and trigger our sell-side quote rules use for the same material."""
    table = (
        parts.groupby(["buy_index", "kind", "country"])
        .agg(parts=("buy_index", "size"), lead_time_months=("lead_time", "median"))
        .reset_index()
        .sort_values("parts", ascending=False)
    )
    table["share_of_parts"] = table["parts"] / table["parts"].sum()
    table["material"] = table["kind"].map(MATERIAL_NAMES)
    table["our_series"] = table["kind"].map(STEEL_KIND_TO_SERIES)
    trigger = triggers.pivot_table(index="series", columns="product", values="trigger_move")
    for product in trigger.columns:
        table[f"sell_trigger_{product}"] = table["our_series"].map(trigger[product])
    table["proposal"] = np.where(
        table["our_series"].notna(),
        "Quote clauses follow the same index, reviewed monthly, 1-month lag",
        "Not in the RMU BOM: no sell-side clause needed",
    )
    return table.reset_index(drop=True)


def copper_and_aluminium_rows(triggers: pd.DataFrame) -> pd.DataFrame:
    """Copper and aluminium are not in the steel mapping: proposed index = LME in EUR (D01, D02)."""
    rows = []
    for series, material in (("D01", "Copper"), ("D02", "Aluminium")):
        row = {"buy_index": f"LME {material.lower()} (EUR)", "material": material}
        row["our_series"] = series
        for product, value in (
            triggers[triggers["series"] == series].set_index("product")["trigger_move"].items()
        ):
            row[f"sell_trigger_{product}"] = value
        row["proposal"] = "Buy and sell on the same LME reference (cash or 3-month, to choose)"
        rows.append(row)
    return pd.DataFrame(rows)


def plants_for_products(parts: pd.DataFrame) -> pd.DataFrame:
    """Which buy-side indices the RM6 (France) and AirSeT (Hungary) plants use."""
    product_plants = {"RM6": "France", "AirSeT": "Hungary"}
    rows = []
    for product, country in product_plants.items():
        used = parts[parts["plant"] == country]["buy_index"].value_counts()
        rows.append({"product": product, "plant_country": country, "buy_indices": used.to_dict()})
    return pd.DataFrame(rows)


def main() -> None:
    strength = supplier_strength()
    parts = read_parts_mapping()
    triggers = pd.read_csv(DATA_PROCESSED / "index_triggers.csv")
    steel = back_to_back_table(parts, triggers)
    indexation = pd.concat([steel, copper_and_aluminium_rows(triggers)], ignore_index=True)
    strength.to_csv(DATA_PROCESSED / "supplier_strength.csv", index=False)
    indexation.to_csv(DATA_PROCESSED / "back_to_back_indexation.csv", index=False)
    print(strength.drop(columns="lever").round(2).to_string(index=False))
    print(strength["group"].value_counts().to_string())
    columns = ["buy_index", "parts", "lead_time_months", "our_series", "proposal"]
    print(indexation[columns].to_string(index=False))
    print(plants_for_products(parts).to_string(index=False))


if __name__ == "__main__":
    main()
