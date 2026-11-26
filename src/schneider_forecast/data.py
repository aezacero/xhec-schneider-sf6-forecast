"""Build the clean monthly data in data/processed/ from the raw files.

Run with: uv run python -m schneider_forecast.data
"""

import pandas as pd

from schneider_forecast.config import (
    BOM_CLEAN,
    BOM_FILES,
    BOM_REFERENCE,
    BOM_VERSIONS,
    DATA_FLAGS,
    DATA_PROCESSED,
    ENERGY_CATALOG,
    ENERGY_PRICES_WIDE,
    EPOXY,
    EXPECTED_TARGETS,
    EXTRA_TARGETS,
    LME,
    ORIGIN,
    PRICES_WIDE,
    PUB_LAG,
    RM_CATALOG,
    RM_PRICES_WIDE,
    RMU_BENCHMARK,
    RMU_PRICES,
    SERIES_CATALOG,
    STEEL_WORKBOOK,
)

LICENSED = [f"L0{i}" for i in range(1, 9)]
MEPS_COUNTRIES = {"Germany": "DE", "France": "FR"}
# Germany CR and HDG coil are the BOM's carbon and galvanised steel: they fill L01 and L03
MEPS_TO_L = {"MEPS_DE_CR": "L01", "MEPS_DE_HDG": "L03"}

EPOXY_COLUMNS = {
    "BENZENE_EUROPE_EUR per TON": "EPX_BENZENE",
    "ACETONE_EUROPE_EUR per TON": "EPX_ACETONE",
    "EPYCHLORHYDRINE_EUROPE_EUR per TON": "EPX_ECH",
    "OTHER COSTS (€/T) for EUROPE\nCalculated": "EPX_OTHER",
    "EPOXY_RESIN_EUR per TON": "EPX_RESIN",
}
LME_COLUMNS = {
    **{
        f"{metal} {price} {cur}/t": f"LME_{metal.upper()}_{price.upper()}_{cur}"
        for metal in ("Cu", "Al")
        for price in ("cash", "3m")
        for cur in ("USD", "EUR")
    },
    "Cu avg stocks t": "LME_CU_STOCKS",
    "Al avg stocks t": "LME_AL_STOCKS",
    "Cu spread EUR/t": "LME_CU_SPREAD",
    "Al spread EUR/t": "LME_AL_SPREAD",
}
RMU_COLUMNS = {
    "ID": "brand_id",
    "Brand": "brand",
    "Year": "year",
    "P10 (ML)": "p10",
    "P50 (ML)": "p50",
    "P90 (ML)": "p90",
}

# metadata for series that are not in the provided catalogs: source, material, region, unit
EXTRA_META = {
    "L01": ("MEPS (steel workbook)", "Carbon steel, CR coil Germany", "EU", "EUR/t"),
    "L02": ("CRU (steel workbook)", "Stainless 304 CR 2 mm Germany, base + alloy", "EU", "EUR/t"),
    "L03": ("MEPS (steel workbook)", "Galvanised steel, HDG coil Germany", "EU", "EUR/t"),
    **{
        f"MEPS_{code}_{product}": (
            "MEPS (steel workbook)",
            f"{product} coil {country}",
            f"EU-{code}",
            "EUR/t",
        )
        for country, code in MEPS_COUNTRIES.items()
        for product in ("HR", "CR", "HDG", "EG")
    },
    "EPX_BENZENE": ("Epoxy file", "Benzene", "EU", "EUR/t"),
    "EPX_ACETONE": ("Epoxy file", "Acetone", "EU", "EUR/t"),
    "EPX_ECH": ("Epoxy file", "Epichlorohydrin", "EU", "EUR/t"),
    "EPX_OTHER": ("Epoxy file", "Other costs (resin minus inputs)", "EU", "EUR/t"),
    "EPX_RESIN": ("Epoxy file", "Epoxy resin", "EU", "EUR/t"),
    **{
        f"LME_{m}_{p}_{c}": ("LME file", f"{name} LME {label}", "WW", f"{c}/t")
        for m, name in (("CU", "Copper"), ("AL", "Aluminium"))
        for p, label in (("CASH", "cash"), ("3M", "3-month"))
        for c in ("USD", "EUR")
    },
    "LME_CU_STOCKS": ("LME file", "Copper LME stocks", "WW", "t"),
    "LME_AL_STOCKS": ("LME file", "Aluminium LME stocks", "WW", "t"),
    "LME_CU_SPREAD": ("LME file", "Copper 3-month minus cash", "WW", "EUR/t"),
    "LME_AL_SPREAD": ("LME file", "Aluminium 3-month minus cash", "WW", "EUR/t"),
}

# known data issues: values are kept as published, listed so modellers treat them on purpose
KNOWN_DATA_ISSUES = [
    ("2026-05", "EPX_ECH", "257 EUR/t vs about 2,500 before and after", "error: kept"),
    ("2026-05", "EPX_RESIN", "computed from epichlorohydrin, inherits its error", "error: kept"),
    ("2026-05", "EPX_OTHER", "resin minus inputs, inherits the same error", "error: kept"),
    ("2020-04", "E02", "WTI crude crash", "real event: keep"),
    ("2021-01", "E12", "Japan power price spike", "real event: keep"),
    ("2025-08", "E20", "EU imports of Russian crude outlier", "real event: keep"),
]


def to_month_start(index: pd.Index) -> pd.DatetimeIndex:
    """Label each date with its month (stored as the 1st), so sources line up by month."""
    return pd.DatetimeIndex(pd.to_datetime(index)).to_period("M").to_timestamp()


def cut_at_origin(df: pd.DataFrame, origin: str = ORIGIN) -> pd.DataFrame:
    """Drop every month after the forecast origin."""
    return df.loc[:origin]


def to_numbers(block: pd.DataFrame) -> pd.DataFrame:
    """Convert to numbers; raise if a non-empty cell cannot be read (no silent NaN)."""
    numbers = block.apply(pd.to_numeric, errors="coerce")
    unreadable = block.notna() & numbers.isna()
    if unreadable.any().any():
        examples = block[unreadable].stack().head(3).to_dict()
        raise ValueError(f"Unreadable values (row, column): {examples}")
    return numbers


def parse_block(block: pd.DataFrame) -> pd.DataFrame:
    """A 'month' column + value columns → numbers indexed by month; rows without a date dropped."""
    months = pd.to_datetime(block["month"], errors="coerce")
    values = to_numbers(block.drop(columns="month")[months.notna()])
    values.index = to_month_start(months[months.notna()])
    values.index.name = "month"
    return values


def load_rm_prices() -> pd.DataFrame:
    rm = pd.read_csv(RM_PRICES_WIDE, parse_dates=["month"], index_col="month")
    # L01–L08 are licensed series, empty in this release (L01–L03 are rebuilt from steel prices)
    return rm.drop(columns=["year", "month_num", *LICENSED])


def load_energy() -> pd.DataFrame:
    return pd.read_csv(ENERGY_PRICES_WIDE, parse_dates=["month"], index_col="month")


def parse_meps(raw: pd.DataFrame) -> pd.DataFrame:
    """MEPS sheet read with header=None → one column per coil product, Germany and France."""
    # one block per country: name in row 0 above the block ("x" closes it), product
    # (HR / CR / HDG / EG coil) in row 4, month in column 0 and €/t values from row 5
    country = raw.iloc[0].ffill()
    product = raw.iloc[4]
    names = {
        col: f"MEPS_{MEPS_COUNTRIES[country[col]]}_{str(product[col]).split()[0]}"
        for col in raw.columns[1:]
        if country[col] in MEPS_COUNTRIES and str(product[col]).endswith("coil")
    }
    meps = raw.iloc[5:, [0, *names]].set_axis(["month", *names.values()], axis=1)
    # date rows run past the last published month: fully empty months are dropped
    return parse_block(meps).dropna(how="all").rename(columns=MEPS_TO_L)


def parse_cru_stainless(
    raw: pd.DataFrame, country: str = "Germany", grade: str = "Grade 304"
) -> pd.Series:
    """CRU Stainless sheet read with header=None → transaction price base + alloy, €/t."""
    # country (row 0) and grade (row 1) sit above the first column of each block; each grade
    # has two columns from row 5: base price and alloy surcharge, dated on the 15th
    block_country = raw.iloc[0].ffill()
    block_grade = raw.iloc[1].ffill()
    cols = [c for c in raw.columns[1:] if block_country[c] == country and block_grade[c] == grade]
    ss = parse_block(raw.iloc[5:, [0, *cols]].set_axis(["month", "base", "alloy"], axis=1))
    # the surcharge passes nickel and chrome costs on: the price paid is base + alloy
    return (ss["base"] + ss["alloy"]).dropna().rename("L02")


def load_steel() -> pd.DataFrame:
    meps = parse_meps(pd.read_excel(STEEL_WORKBOOK, sheet_name="MEPS", header=None))
    stainless = parse_cru_stainless(
        pd.read_excel(STEEL_WORKBOOK, sheet_name="CRU Stainless", header=None)
    )
    return meps.join(stainless, how="outer")


def load_epoxy() -> pd.DataFrame:
    raw = pd.read_excel(EPOXY, index_col=0)
    epoxy = to_numbers(raw[list(EPOXY_COLUMNS)].rename(columns=EPOXY_COLUMNS))
    # observation day moves from the 1st to the 2nd–5th from Dec 2023
    epoxy.index = to_month_start(epoxy.index)
    return epoxy


def load_lme() -> pd.DataFrame:
    """LME file, completed months only (the last month is month-to-date)."""
    raw = pd.read_excel(LME, sheet_name="Monthly Prices", header=4)
    lme = raw[raw["Period status"] == "Completed month"].set_index("Month")
    lme = lme[list(LME_COLUMNS)].rename(columns=LME_COLUMNS)
    lme.index = to_month_start(lme.index)
    return lme


def build_prices() -> pd.DataFrame:
    """All monthly series side by side, one row per month, cut at the origin."""
    frames = [load_rm_prices(), load_energy(), load_steel(), load_epoxy(), load_lme()]
    prices = pd.concat(frames, axis=1).sort_index()
    prices.index.name = "month"
    return cut_at_origin(prices)


def target_ids(bom: pd.DataFrame, available: pd.Index) -> list[str]:
    """Series named as a price proxy in the BOM, plus the extra targets, that have data."""
    ids = pd.concat([bom["eu_series_ids"], bom["ww_series_ids"]]).dropna().str.split(";")
    named = {s.strip() for group in ids for s in group} | set(EXTRA_TARGETS)
    return sorted(named & set(available))


def series_metadata() -> pd.DataFrame:
    rm = pd.read_csv(RM_CATALOG, index_col="series_id")
    energy = pd.read_csv(ENERGY_CATALOG, index_col="series_id")
    meta = pd.concat(
        [
            rm.assign(source=rm["provider"])[["source", "material", "region", "unit"]],
            energy.rename(columns={"energy": "material"}).assign(source=energy["provider"])[
                ["source", "material", "region", "unit"]
            ],
        ]
    )
    extra = pd.DataFrame.from_dict(
        EXTRA_META, orient="index", columns=["source", "material", "region", "unit"]
    )
    # our own L01–L03 replace the empty licensed rows of the provided catalog
    return pd.concat([meta.drop(index=extra.index, errors="ignore"), extra])


def build_catalog(prices: pd.DataFrame, targets: list[str], meta: pd.DataFrame) -> pd.DataFrame:
    """One row per series in prices: metadata, coverage, time gaps, target flags."""
    missing_lag = sorted(set(prices.columns) - set(PUB_LAG))
    if missing_lag:
        raise ValueError(f"No publication lag in config.PUB_LAG for: {missing_lag}")
    observed = prices.apply(lambda s: s.dropna().index)
    catalog = meta.reindex(prices.columns)
    catalog.index.name = "series_id"
    catalog["first"] = observed.map(min)
    catalog["last"] = observed.map(max)
    catalog["n_obs"] = prices.notna().sum()
    # months between the last value and the origin in this snapshot: the backtest cuts each
    # series by the same gap at every past origin
    origin = pd.Period(ORIGIN, "M")
    catalog["gap_months"] = [(origin - last.to_period("M")).n for last in catalog["last"]]
    catalog["pub_lag"] = catalog.index.map(PUB_LAG)
    catalog["is_target"] = catalog.index.isin(targets)
    # a target that stops before the origin must first be brought up to it
    catalog["needs_nowcast"] = catalog["is_target"] & (catalog["gap_months"] > 0)
    return catalog


def read_bom(version: str) -> pd.DataFrame:
    """One BOM version as sent by Schneider (CSV, or the xlsx sheet BOM_Materials)."""
    path = BOM_FILES[version]
    if path.suffix == ".csv":
        return pd.read_csv(path)
    return pd.read_excel(path, sheet_name="BOM_Materials")


def clean_bom(raw: pd.DataFrame, available: pd.Index) -> pd.DataFrame:
    """Material rows only, plant country and preferred price series added."""
    # the last rows of the file are mass totals; real material rows have a plant code
    bom = raw[raw["plant_code"].notna()].drop(columns="plant_name").copy()
    # plant country decides the steel index (parts are priced on their plant country's index,
    # Hungary on Germany); codes look like ETO_HU1100
    bom.insert(1, "plant_country", bom["plant_code"].str.extract(r"_([A-Z]{2})\d", expand=False))
    # first BOM proxy that has data; none for unpriced lines (Other, brass, remainder)
    bom["price_series"] = bom["eu_series_ids"].fillna("") + ";" + bom["ww_series_ids"].fillna("")
    bom["price_series"] = bom["price_series"].map(
        lambda ids: next((s for s in ids.split(";") if s in available), pd.NA)
    )
    return bom


def bom_versions(available: pd.Index) -> pd.DataFrame:
    """Every BOM version stacked with a `version` column (versions disagree on every mass)."""
    return pd.concat(
        [clean_bom(read_bom(v), available).assign(version=v) for v in BOM_FILES],
        ignore_index=True,
    )


def load_rmu() -> pd.DataFrame:
    raw = pd.read_excel(RMU_BENCHMARK, sheet_name="ML_Trend", header=3)
    return raw[list(RMU_COLUMNS)].rename(columns=RMU_COLUMNS).dropna(subset=["year"])


def run_checks(
    prices: pd.DataFrame,
    catalog: pd.DataFrame,
    expected_targets: tuple[str, ...] = EXPECTED_TARGETS,
) -> None:
    """Raise if the data breaks an expected property; lists every failure at once."""
    failures = []
    idx = prices.index
    if not (idx.is_unique and idx.is_monotonic_increasing):
        failures.append("month index is not unique and sorted")
    if idx.max() > pd.Timestamp(ORIGIN):
        failures.append(f"data after the origin {ORIGIN}")

    targets = catalog[catalog["is_target"]]
    if set(targets.index) != set(expected_targets):
        missing = sorted(set(expected_targets) - set(targets.index))
        extra = sorted(set(targets.index) - set(expected_targets))
        failures.append(f"target list changed: missing {missing}, unexpected {extra}")
    for target in targets.index:
        series = prices[target].loc[targets.at[target, "first"] : targets.at[target, "last"]]
        if series.isna().any():
            failures.append(f"{target} has {series.isna().sum()} gap(s) inside its history")
        if (series <= 0).any():
            failures.append(f"{target} has values ≤ 0 (models work on logs)")

    if failures:
        raise ValueError("Data checks failed:\n- " + "\n- ".join(failures))


def main() -> None:
    prices = build_prices()
    bom = clean_bom(read_bom(BOM_REFERENCE), prices.columns)
    catalog = build_catalog(prices, target_ids(bom, prices.columns), series_metadata())
    run_checks(prices, catalog)
    flags = pd.DataFrame(KNOWN_DATA_ISSUES, columns=["month", "series_id", "issue", "treatment"])

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    prices.to_csv(PRICES_WIDE)
    catalog.to_csv(SERIES_CATALOG)
    flags.to_csv(DATA_FLAGS, index=False)
    bom.to_csv(BOM_CLEAN, index=False)
    bom_versions(prices.columns).to_csv(BOM_VERSIONS, index=False)
    load_rmu().to_csv(RMU_PRICES, index=False)

    first, last = prices.index.min(), prices.index.max()
    print(f"{len(prices)} months ({first:%Y-%m} → {last:%Y-%m}), {prices.shape[1]} series,")
    print(f"{int(catalog['is_target'].sum())} targets → {DATA_PROCESSED}")
    nowcast = list(catalog.index[catalog["needs_nowcast"]])
    if nowcast:
        print(f"Targets ending before {ORIGIN}: {nowcast}")


if __name__ == "__main__":
    main()
