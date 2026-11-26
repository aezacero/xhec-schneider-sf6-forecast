"""Loaders for the data-overview notebook (01_data_overview.ipynb), as tidy pandas objects.

The pipeline in src/schneider_forecast/data.py is what the models use; this module only serves
the notebook.

Conventions
- Monthly series are indexed by a month-start ``DatetimeIndex`` named ``month`` (sources that stamp
  the 3rd or the 15th of the month are snapped to the 1st).
- Values are numeric; placeholders such as ``"-"`` become NaN. Nothing is interpolated.
- Supplier names are never exposed: suppliers are labelled ``Supplier A``, ``Supplier B``, ...
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

DATA_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
# file locations as the data pack ships them (the pipeline in src/ reads the same files)
config = SimpleNamespace(
    RM_PRICES_WIDE=DATA_RAW / "csv" / "rm_prices_monthly_wide.csv",
    ENERGY_PRICES_WIDE=DATA_RAW / "csv" / "energy_prices_monthly_wide.csv",
    BOM=DATA_RAW / "csv" / "bom_materials.csv",
    SOURCE_CATALOG=DATA_RAW / "csv" / "source_catalog.csv",
    ENERGY_CATALOG=DATA_RAW / "csv" / "energy_source_catalog.csv",
    BOM_XLSX=DATA_RAW / "RM_Prices_XHEC_Challenge.xlsx",
    STEEL=DATA_RAW / "Copia de Europe Steel INDEXES.xlsx",
    EPOXY=DATA_RAW / "Epoxy for student.xlsx",
    LME=DATA_RAW / "LME_Copper_Aluminium_EU_Monthly_2016_2026.xlsx",
    RMU_PANEL=DATA_RAW / "RMU_IQI_EU_Price_Benchmark_2017-2026_Synthetic.xlsx",
    BENCHMARK=DATA_RAW
    / (
        "benchmark-modules-fonctionnels-rm6-ne-iqi-3-fonctions-400a-appareillage-"
        "isolement-et-coupure-dans-le-gaz-sf6.xlsx"
    ),
    SUPPLIERS_DIR=DATA_RAW / "supplier_balance_sheets",
)

# --------------------------------------------------------------------------------------------
# Generic helpers (pure functions, unit-tested on synthetic data)
# --------------------------------------------------------------------------------------------


def to_month_start(values) -> pd.DatetimeIndex:
    """Snap any date-like values to the first day of their month."""
    return pd.DatetimeIndex(pd.to_datetime(values)).to_period("M").to_timestamp()


def to_numeric_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce every column to float; non-numeric placeholders ('-', '', 'n/a') become NaN."""
    return df.apply(lambda c: pd.to_numeric(c, errors="coerce")).astype(float)


def clean_label(value) -> str | None:
    """Strip whitespace/newlines from a header cell; separators ('x', blanks) become None."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return None if text in {"", "x", "nan"} else text


def ffill_labels(row: pd.Series) -> list[str | None]:
    """Forward-fill a merged-cell header row (e.g. a country spanning several columns)."""
    return pd.Series([clean_label(v) for v in row]).ffill().tolist()


def _monthly_block(raw: pd.DataFrame, first_data_row: int, columns: dict[int, str]) -> pd.DataFrame:
    """Cut the data rows of a sheet into a month-indexed frame with the given column names."""
    body = raw.iloc[first_data_row:]
    dates = pd.to_datetime(body.iloc[:, 0], errors="coerce")
    body = body[dates.notna()]
    out = to_numeric_frame(body[list(columns)]).rename(columns=columns)
    out.index = to_month_start(dates[dates.notna()])
    out.index.name = "month"
    out = out.dropna(how="all")  # sheets carry empty date rows up to 2028-29
    return out.groupby(level=0).mean()  # guard against duplicate months after snapping


# --------------------------------------------------------------------------------------------
# Layer 1: market prices
# --------------------------------------------------------------------------------------------


def load_rm_prices(path: Path = config.RM_PRICES_WIDE) -> pd.DataFrame:
    """RM series S01-S13, D01-D02, L01-L08 (L empty on purpose), month-indexed."""
    df = pd.read_csv(path, parse_dates=["month"]).set_index("month")
    return df.drop(columns=["year", "month_num"])


def load_energy_prices(path: Path = config.ENERGY_PRICES_WIDE) -> pd.DataFrame:
    """Energy series E01-E24, ED01-ED06, month-indexed."""
    df = pd.read_csv(path, parse_dates=["month"]).set_index("month")
    return df.drop(columns=[c for c in ("year", "month_num") if c in df.columns])


def load_catalog(kind: str = "rm") -> pd.DataFrame:
    """Series metadata: kind='rm' (S/D/L series) or 'energy' (E/ED series)."""
    path = config.SOURCE_CATALOG if kind == "rm" else config.ENERGY_CATALOG
    return pd.read_csv(path).set_index("series_id")


_FLAT_PRODUCTS = {"HR coil", "CR coil", "HDG coil", "EG coil"}


def load_steel_meps(path: Path = config.STEEL) -> pd.DataFrame:
    """MEPS flat-steel monthly prices (low values), one column per product x country.

    Columns are named like ``MEPS_CR_coil_Germany``. Units: EUR/t, except ``UK (GBP)`` in GBP/t.
    Only the main country blocks are kept (sparse Nordic/Sweden, wire rod, Turkey and short
    stainless blocks on the right of the sheet are dropped).
    """
    raw = pd.read_excel(path, sheet_name="MEPS", header=None)
    countries = ffill_labels(raw.iloc[0])
    products = [clean_label(v) for v in raw.iloc[4]]
    keep = {"Germany", "France", "Italy", "Spain", "UK (GBP)", "Belgium"}
    cols = {
        j: f"MEPS_{products[j].replace(' ', '_')}_{countries[j].replace(' (GBP)', '_GBP')}"
        for j in range(1, raw.shape[1])
        if products[j] in _FLAT_PRODUCTS and countries[j] in keep
    }
    return _monthly_block(raw, 5, cols)


def load_steel_cru_flat(path: Path = config.STEEL) -> pd.DataFrame:
    """CRU flat steel: monthly AVERAGE of weekly domestic quotes, EUR/t (``CRU_CR_coil_Italy``)."""
    raw = pd.read_excel(path, sheet_name="CRU Flat", header=None)
    countries = ffill_labels(raw.iloc[0])
    kind, product, market = (
        [clean_label(v) for v in raw.iloc[i]] for i in (1, 2, 4)
    )  # AVERAGE/WEEK n, product, Domestic/Import
    cols = {
        j: f"CRU_{product[j].replace(' ', '_')}_{countries[j].title()}"
        for j in range(1, raw.shape[1])
        if kind[j] == "AVERAGE" and market[j] == "Domestic" and product[j] in _FLAT_PRODUCTS
    }
    return _monthly_block(raw, 6, cols)


def load_steel_cru_stainless(path: Path = config.STEEL) -> pd.DataFrame:
    """CRU stainless CR-2mm sheet: base price, alloy surcharge and total (= base + alloy).

    Columns like ``CRU_SS304_Germany_base``, ``..._alloy``, ``..._total``. EUR/t (UK in GBP/t).
    The total is what a buyer pays and is the proxy for the empty licensed series L02.
    """
    raw = pd.read_excel(path, sheet_name="CRU Stainless", header=None)
    countries = ffill_labels(raw.iloc[0])
    grades = ffill_labels(raw.iloc[1])
    parts = [clean_label(v) for v in raw.iloc[4]]
    cols = {}
    for j in range(1, raw.shape[1]):
        if parts[j] in {"BASE", "Alloy"} and grades[j]:
            grade = grades[j].replace("Grade ", "SS")
            cols[j] = f"CRU_{grade}_{countries[j]}_{parts[j].lower()}"
    out = _monthly_block(raw, 5, cols)
    for base_col in [c for c in out.columns if c.endswith("_base")]:
        stem = base_col[: -len("_base")]
        out[f"{stem}_total"] = out[base_col] + out[f"{stem}_alloy"]
    return out.sort_index(axis=1)


def load_steel(path: Path = config.STEEL) -> pd.DataFrame:
    """All parsed steel market prices (MEPS flat, CRU flat, CRU stainless) on one month index."""
    return pd.concat(
        [load_steel_meps(path), load_steel_cru_flat(path), load_steel_cru_stainless(path)], axis=1
    ).sort_index()


def load_steel_part_mapping(path: Path = config.STEEL) -> pd.DataFrame:
    """Schneider purchased steel parts -> plant, steel index, lead time, weight (no names)."""
    raw = pd.read_excel(path, sheet_name="Reference to Index Mapping", header=None)
    header_row = next(
        i for i in range(min(15, len(raw))) if raw.iloc[i].astype(str).str.contains("Index").any()
    )
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = [clean_label(c) or f"col{j}" for j, c in enumerate(raw.iloc[header_row])]
    return df.dropna(how="all").reset_index(drop=True)


def load_epoxy(path: Path = config.EPOXY) -> pd.DataFrame:
    """Epoxy resin and its chemical inputs, EUR/t, month-indexed (Jan 2018 ->)."""
    raw = pd.read_excel(path, header=None)
    names = {
        2: "benzene",
        3: "acetone",
        4: "epichlorohydrin",
        5: "epoxy_other_costs",
        6: "epoxy_resin",
    }
    return _monthly_block(raw, 1, names)


def load_lme(path: Path = config.LME, completed_only: bool = True) -> pd.DataFrame:
    """LME copper/aluminium cash and 3-month prices (USD and EUR), stocks, FX.

    ``completed_only=True`` drops the provisional month-to-date row (Nov 2026).
    """
    raw = pd.read_excel(path, sheet_name="Monthly Prices", header=None)
    header = [clean_label(v) for v in raw.iloc[4]]
    df = raw.iloc[5:].copy()
    df.columns = header
    df = df[pd.to_datetime(df["Month"], errors="coerce").notna()]
    if completed_only:
        df = df[df["Period status"] == "Completed month"]
    idx = to_month_start(df["Month"])
    num = to_numeric_frame(df.drop(columns=["Month", "Period status", "FX coverage"]))
    num.index = idx
    num.index.name = "month"
    num.columns = [
        c.lower().replace(" ", "_").replace("/", "_per_").replace("usd_per_eur", "eurusd")
        for c in num.columns
    ]
    return num


# --------------------------------------------------------------------------------------------
# Layer 2: product recipe
# --------------------------------------------------------------------------------------------


def load_bom(version: str = "csv") -> pd.DataFrame:
    """Material shares and masses per product.

    version='csv'  -> data/raw/csv/bom_materials.csv (inside data.zip)
    version='xlsx' -> data/raw/RM_Prices_XHEC_Challenge.xlsx (standalone, different masses)
    Summary rows ('Total labelled mass', 'Implied total mass') are dropped.
    """
    if version == "csv":
        df = pd.read_csv(config.BOM)
    elif version == "xlsx":
        df = pd.read_excel(config.BOM_XLSX)
    else:
        raise ValueError("version must be 'csv' or 'xlsx'")
    df = df[~df["product_ref"].astype(str).str.match(r"(Total|Implied)")].copy()
    df["product"] = np.where(df["product_ref"].str.startswith("RM6"), "RM6", "RM AirSeT")
    return df.reset_index(drop=True)


# --------------------------------------------------------------------------------------------
# Layer 3: product and market context
# --------------------------------------------------------------------------------------------


def load_rmu_panel(path: Path = config.RMU_PANEL) -> pd.DataFrame:
    """Synthetic yearly RMU price panel 2017-2026 by brand: P10/P50/P90 in EUR ex-VAT."""
    raw = pd.read_excel(path, sheet_name="ML_Trend", header=None)
    df = raw.iloc[4:, :7].copy()
    df.columns = ["brand_id", "brand", "year", "p10", "p50", "p90", "yoy_p50"]
    df = df.dropna(subset=["year"])
    df["year"] = df["year"].astype(int)
    df[["p10", "p50", "p90", "yoy_p50"]] = to_numeric_frame(df[["p10", "p50", "p90", "yoy_p50"]])
    df["sf6_free"] = df["brand_id"].eq("ETN")  # Eaton Xiria is the only SF6-free unit
    return df.reset_index(drop=True)


_BENCHMARK_FIELDS = {
    "total": "should_cost_total",
    "material": "should_cost_material",
    "process": "should_cost_process",
    "labour": "should_cost_labour",
    "overhead": "should_cost_overhead",
    "List price": "list_price_eur",
    "Mass (g)": "mass_g",
    "Made in": "made_in",
    "Insulation / technology": "insulation",
    "Rated busbar current Ir (A)": "busbar_current_a",
}


def load_benchmark(path: Path = config.BENCHMARK) -> pd.DataFrame:
    """Competitor should-cost benchmark: one row per product (Schneider RM6 = reference)."""
    raw = pd.read_excel(path, sheet_name="Benchmark", header=None)
    products = [clean_label(v) for v in raw.iloc[4, 1:7]]
    rows = {}
    for i in range(5, len(raw)):
        field = clean_label(raw.iloc[i, 0])
        if field in _BENCHMARK_FIELDS and _BENCHMARK_FIELDS[field] not in rows:
            rows[_BENCHMARK_FIELDS[field]] = raw.iloc[i, 1:7].tolist()
    df = pd.DataFrame(rows, index=products)
    df.index.name = "product"
    for c in df.columns:
        if c.startswith(("should_cost", "list_price", "mass")):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["material_share"] = df["should_cost_material"] / df["should_cost_total"]
    df["brand"] = [p.split(" ")[0].capitalize() for p in df.index]
    return df


def load_supplier_financials(directory: Path = config.SUPPLIERS_DIR) -> pd.DataFrame:
    """Long table of supplier financials: supplier (anonymised), sheet, metric, year, value.

    Amounts are in thousands of EUR; ratios are fractions. Supplier order follows sorted file
    names, so labels are stable across runs. Never re-attach the real names in shared outputs.
    """
    frames = []
    files = sorted(directory.glob("*.xlsx"))
    for k, file in enumerate(files):
        label = f"Supplier {chr(ord('A') + k)}"
        xls = pd.ExcelFile(file)
        for sheet in xls.sheet_names:
            if sheet in {"Overview", "Disclaimer"}:
                continue
            raw = pd.read_excel(xls, sheet_name=sheet, header=None)
            period_row = next(
                (
                    i
                    for i in range(min(12, len(raw)))
                    if raw.iloc[i].astype(str).str.match(r"^[A-Z][a-z]{2} \d{4}$").any()
                ),
                None,
            )
            if period_row is None:
                continue
            periods = raw.iloc[period_row]
            year_cols = {
                j: int(str(v)[-4:])
                for j, v in periods.items()
                if re.match(r"^\w{3} \d{4}$", str(v))
            }
            for i in range(period_row + 1, len(raw)):
                metric = clean_label(raw.iloc[i, 2])
                if not metric:
                    continue
                for j, year in year_cols.items():
                    value = pd.to_numeric(raw.iloc[i, j], errors="coerce")
                    if pd.notna(value):
                        frames.append((label, sheet, metric, year, float(value)))
    return pd.DataFrame(frames, columns=["supplier", "sheet", "metric", "year", "value"])


# --------------------------------------------------------------------------------------------
# One monthly panel for modelling
# --------------------------------------------------------------------------------------------

# Free proxies for the empty licensed steel series (see docs/data_catalog.md)
STEEL_PROXIES = {
    "L01_proxy": "MEPS_CR_coil_Germany",  # CR coil, EUR/t
    "L02_proxy": "CRU_SS304_Germany_total",  # stainless 304 base + alloy surcharge, EUR/t
    "L03_proxy": "MEPS_HDG_coil_Germany",  # HDG coil Germany, EUR/t
}


def load_monthly_panel() -> pd.DataFrame:
    """RM + energy + steel proxies + epoxy on one month index (outer join, NaN kept)."""
    rm = load_rm_prices().drop(columns=[f"L0{i}" for i in range(1, 9)])
    steel = load_steel()
    proxies = pd.DataFrame({k: steel[v] for k, v in STEEL_PROXIES.items()})
    epoxy = load_epoxy()
    energy = load_energy_prices().drop(columns=["E23"])  # E23 duplicates S06 (EUR/USD)
    return pd.concat([rm, proxies, epoxy, energy], axis=1).sort_index()
