"""Build the forecast CSV Schneider scores: material and cost-index forecasts in one checked file.

Schneider tracks our 3 / 6 / 9-month P10 / P50 / P90 forecasts after the jury, so the file must
follow the layout in the README ("Forecast CSV") exactly. One command stacks:

- ``outputs/forecasts/p2_forecasts_202609.csv`` and ``p3_forecasts_202609.csv`` (material
  forecasts from the steel and other-material model selections);
- ``data/processed/bom_index_rows.csv`` (the 6 BOM cost index rows from the pricing step);
- ``data/processed/prices_wide.csv`` and ``series_catalog.csv`` (data pipeline: each series' value
  at the origin, for rebasing, and its region).

It writes ``outputs/forecasts/team_05_forecast_202609.csv`` and stops with a list of every
problem if a check fails. Run ``uv run python -m schneider_forecast.submit``.
"""

from pathlib import Path

import pandas as pd

from schneider_forecast.config import (
    DATA_PROCESSED,
    EXPECTED_TARGETS,
    FORECASTS,
    HORIZONS,
    ORIGIN,
    PRICES_WIDE,
    SERIES_CATALOG,
)

TEAM_ID = "team_05"  # the only place the team ID is set; file name and team_id column use it
MATERIAL_FILES = (
    FORECASTS / "p2_forecasts_202609.csv",
    FORECASTS / "p3_forecasts_202609.csv",
)
BOM_INDEX_FILE = DATA_PROCESSED / "bom_index_rows.csv"
PRODUCTS = ("RMAirSeT IIQ 24kV IEC", "RM6_NE_IQI_433520")

COLUMNS = [
    "team_id",
    "target_type",
    "target_id",
    "region",
    "origin_month",
    "horizon_m",
    "target_month",
    "unit",
    "p10",
    "p50",
    "p90",
    "model_name",
    "ai_tools",
]
EUR_UNIT = "EUR/t"
INDEX_UNIT = "index (origin=100)"  # the only two units the format allows
TARGET_TYPES = ("material", "bom_index")
REGIONS = ("EU", "WW")
AI_TOOLS_FOR_ALL = ("claude-code",)  # used to write the code (docs/models_and_licenses.md)


def output_path(team_id: str = TEAM_ID) -> Path:
    """Return where the submission file is written.

    Parameters
    ----------
    team_id : str, default=TEAM_ID
        Team identifier used in the file name.

    Returns
    -------
    pathlib.Path
        ``outputs/forecasts/<team>_forecast_202609.csv``.
    """
    return FORECASTS / f"{team_id}_forecast_{ORIGIN.replace('-', '')}.csv"


def read_csvs(files) -> pd.DataFrame:
    """Stack CSV files into one table.

    Parameters
    ----------
    files : iterable of pathlib.Path
        Files to read, in order.

    Returns
    -------
    pandas.DataFrame
        All rows, one after the other.

    Raises
    ------
    FileNotFoundError
        If any file is missing (the message lists them all).
    """
    missing = [str(path) for path in files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing forecast files: {', '.join(missing)}")
    return pd.concat([pd.read_csv(path) for path in files], ignore_index=True)


def simple_region(catalog_region: str) -> str:
    """Reduce a catalog region to the two regions the format allows.

    Parameters
    ----------
    catalog_region : str
        Region in ``series_catalog.csv`` (EU, EU-DE, WW, WW (US), WW in EUR).

    Returns
    -------
    str
        ``"EU"`` or ``"WW"``.

    Raises
    ------
    ValueError
        If the region starts with neither.
    """
    for region in REGIONS:
        if str(catalog_region).startswith(region):
            return region
    raise ValueError(f"unknown region: {catalog_region}")


def value_at_origin(prices: pd.DataFrame, series: str) -> float:
    """Read a series' last known value at or before the origin month.

    Parameters
    ----------
    prices : pandas.DataFrame
        Monthly prices, one column per series.
    series : str
        Column to read.

    Returns
    -------
    float
        The value that becomes 100 when the series is rebased.
    """
    return float(prices.loc[:ORIGIN, series].dropna().iloc[-1])


def to_allowed_units(table: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
    """Express every row in EUR/t or as an index with 100 = the origin.

    Parameters
    ----------
    table : pandas.DataFrame
        Material forecast rows in each series' own unit.
    prices : pandas.DataFrame
        Monthly prices (for the value at the origin).

    Returns
    -------
    pandas.DataFrame
        EUR/t rows unchanged; every other row (USD prices, PPIs, EUR/USD) divided by its value
        at the origin and × 100, with ``unit`` = ``index (origin=100)``.
    """
    table = table.copy()
    to_index = table["unit"] != EUR_UNIT
    for row in table.index[to_index]:
        base = value_at_origin(prices, table.at[row, "target_id"])
        for q in ("p10", "p50", "p90"):
            table.at[row, q] = 100 * table.at[row, q] / base
    table.loc[to_index, "unit"] = INDEX_UNIT
    return table


def ai_tools(model_name: str) -> str:
    """List the AI tools behind a forecast row.

    Parameters
    ----------
    model_name : str
        Model that produced the row.

    Returns
    -------
    str
        ``;``-separated tools: ``chronos-2`` when the model uses it, plus the coding assistant
        used for the whole repo.
    """
    tools = ["chronos-2"] if "chronos" in str(model_name).lower() else []
    return "; ".join(tools + list(AI_TOOLS_FOR_ALL))


def build_submission(
    materials: pd.DataFrame,
    bom_rows: pd.DataFrame,
    prices: pd.DataFrame,
    catalog: pd.DataFrame,
    team_id: str = TEAM_ID,
) -> pd.DataFrame:
    """Put the material rows and the 6 BOM index rows in the submission layout.

    Parameters
    ----------
    materials : pandas.DataFrame
        Material forecast rows (``target_type``, ``target_id``, ``origin_month``,
        ``horizon_m``, ``target_month``, ``unit``, ``p10``, ``p50``, ``p90``, ``model_name``).
    bom_rows : pandas.DataFrame
        The pricing step's ``bom_index`` rows (already with ``region`` and the index unit).
    prices : pandas.DataFrame
        Monthly prices (for rebasing).
    catalog : pandas.DataFrame
        Series catalog indexed by series id (for ``region``).
    team_id : str, default=TEAM_ID
        Team identifier written on every row.

    Returns
    -------
    pandas.DataFrame
        One row per target and horizon, columns in ``COLUMNS`` order, materials first.
    """
    materials = to_allowed_units(materials, prices)
    materials["region"] = materials["target_id"].map(catalog["region"]).map(simple_region)
    table = pd.concat([materials, bom_rows], ignore_index=True)
    table["team_id"] = team_id
    table["ai_tools"] = table["model_name"].map(ai_tools)
    table["origin_month"] = table["origin_month"].astype(str)
    table["target_month"] = table["target_month"].astype(str)
    for q in ("p10", "p50", "p90"):
        table[q] = table[q].astype(float).round(4)
    table = table.sort_values(
        ["target_type", "target_id", "horizon_m"], ascending=[False, True, True]
    )
    return table[COLUMNS].reset_index(drop=True)


def check_submission(table: pd.DataFrame, targets=EXPECTED_TARGETS) -> None:
    """Check the submission and stop with every problem found.

    Parameters
    ----------
    table : pandas.DataFrame
        Output of ``build_submission``.
    targets : tuple of str, default=EXPECTED_TARGETS
        Material series that must all be present (the 19 targets).

    Raises
    ------
    ValueError
        On missing columns, blanks, duplicates, horizons other than 3 / 6 / 9, wrong months,
        units, regions or target types, P10 > P50 or P50 > P90, values ≤ 0, a missing or
        unexpected material target, fewer than the 6 BOM index rows, or more than one team.
    """
    problems = []
    missing = [c for c in COLUMNS if c not in table.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")

    blank = table[COLUMNS].isna() | table[COLUMNS].astype(str).apply(
        lambda col: col.str.strip() == ""
    )
    if blank.any().any():
        problems.append(f"blank cells in: {', '.join(blank.columns[blank.any()])}")

    duplicated = table.duplicated(["target_type", "target_id", "horizon_m"], keep=False)
    if duplicated.any():
        problems.append(f"duplicate rows for: {sorted(set(table.loc[duplicated, 'target_id']))}")

    horizons = table.groupby("target_id")["horizon_m"].apply(lambda h: sorted(h) == list(HORIZONS))
    if not horizons.all():
        problems.append(f"not exactly horizons {HORIZONS}: {list(horizons.index[~horizons])}")

    if (table["origin_month"] != ORIGIN).any():
        problems.append(f"origin_month is not {ORIGIN} everywhere")
    expected = [str(pd.Period(ORIGIN, "M") + int(h)) for h in table["horizon_m"]]
    if (table["target_month"] != expected).any():
        problems.append("target_month is not origin_month + horizon_m everywhere")

    for column, allowed in (
        ("unit", (EUR_UNIT, INDEX_UNIT)),
        ("region", REGIONS),
        ("target_type", TARGET_TYPES),
    ):
        wrong = sorted(set(table[column]) - set(allowed))
        if wrong:
            problems.append(f"{column} not allowed: {wrong}")

    quantiles = table[["p10", "p50", "p90"]].astype(float)
    if not ((quantiles["p10"] <= quantiles["p50"]) & (quantiles["p50"] <= quantiles["p90"])).all():
        problems.append("P10 ≤ P50 ≤ P90 fails on some rows")
    if (quantiles <= 0).any().any():
        problems.append("values at or below 0")

    materials = set(table.loc[table["target_type"] == "material", "target_id"])
    if materials != set(targets):
        lacking, extra = sorted(set(targets) - materials), sorted(materials - set(targets))
        problems.append(f"material targets differ: missing {lacking}, unexpected {extra}")

    bom = table[table["target_type"] == "bom_index"]
    wanted = {(product, h) for product in PRODUCTS for h in HORIZONS}
    found = set(zip(bom["target_id"], bom["horizon_m"], strict=True))
    if found != wanted:
        problems.append(
            f"bom_index rows: need {len(wanted)} (2 products × 3 horizons), found {len(found)}"
        )

    if table["team_id"].nunique() != 1:
        problems.append("more than one team_id")

    if problems:
        raise ValueError("submission check failed:\n- " + "\n- ".join(problems))


def main() -> None:
    """Build, check and write the submission CSV."""
    prices = pd.read_csv(PRICES_WIDE, parse_dates=["month"], index_col="month")
    catalog = pd.read_csv(SERIES_CATALOG, index_col="series_id")
    materials = read_csvs(MATERIAL_FILES)
    bom_rows = read_csvs([BOM_INDEX_FILE])
    table = build_submission(materials, bom_rows, prices, catalog)
    check_submission(table)
    path = output_path()
    FORECASTS.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False)
    counts = table.groupby("target_type").size().to_dict()
    print(f"{len(table)} rows ({counts}), all checks passed → {path}")


if __name__ == "__main__":
    main()
