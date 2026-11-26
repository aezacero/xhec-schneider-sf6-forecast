from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_EXTERNAL = ROOT / "data" / "external"
OUTPUTS = ROOT / "outputs"
FIGURES = OUTPUTS / "figures"
FORECASTS = OUTPUTS / "forecasts"

RM_PRICES_LONG = DATA_RAW / "csv" / "rm_prices_monthly_long.csv"
RM_PRICES_WIDE = DATA_RAW / "csv" / "rm_prices_monthly_wide.csv"
ENERGY_PRICES_WIDE = DATA_RAW / "csv" / "energy_prices_monthly_wide.csv"
# BOM versions sent by Schneider, oldest first; the latest is the reference
BOM_FILES = {
    "2026-11-12 csv": DATA_RAW / "csv" / "bom_materials.csv",
    "2026-11-19 xlsx": DATA_RAW / "RM_Prices_XHEC_Challenge.xlsx",
    "2026-11-20 v1": DATA_RAW / "RM_Prices_XHEC_Challenge_v1.xlsx",
}
BOM_REFERENCE = "2026-11-20 v1"

HORIZONS = (3, 6, 9)
QUANTILES = (0.1, 0.5, 0.9)
SEED = 42

STEEL_WORKBOOK = DATA_RAW / "Copia de Europe Steel INDEXES.xlsx"
EPOXY = DATA_RAW / "Epoxy for student.xlsx"
LME = DATA_RAW / "LME_Copper_Aluminium_EU_Monthly_2016_2026.xlsx"
RMU_BENCHMARK = DATA_RAW / "RMU_IQI_EU_Price_Benchmark_2017-2026_Synthetic.xlsx"
RM_CATALOG = DATA_RAW / "csv" / "source_catalog.csv"
ENERGY_CATALOG = DATA_RAW / "csv" / "energy_source_catalog.csv"

PRICES_WIDE = DATA_PROCESSED / "prices_wide.csv"
SERIES_CATALOG = DATA_PROCESSED / "series_catalog.csv"
DATA_FLAGS = DATA_PROCESSED / "data_flags.csv"
BOM_CLEAN = DATA_PROCESSED / "bom_clean.csv"
BOM_VERSIONS = DATA_PROCESSED / "bom_versions.csv"
RMU_PRICES = DATA_PROCESSED / "rmu_prices.csv"

# forecast origin: last month of data used (slides p17); nothing after it enters the data
ORIGIN = "2026-09"

# targets beyond the BOM price proxies: epoxy (insulation) and EUR/USD (methodology §3.1)
EXTRA_TARGETS = ("EPX_RESIN", "S06")
# the full target list: the build stops if the BOM proxies + EXTRA_TARGETS ever differ from it
EXPECTED_TARGETS = (
    "D01", "D02", "EPX_RESIN", "L01", "L02", "L03", "S01", "S02", "S03", "S04", "S05", "S06",
    "S07", "S08", "S09", "S10", "S11", "S12", "S13",
)  # fmt: skip

# publication lag in months: a value for month m is known from month m + lag on
# (eda_findings.md §4). Every series in the processed data must have one.
_LAG_GROUPS = {
    0: [
        "LME_CU_STOCKS", "LME_AL_STOCKS", "LME_CU_SPREAD", "LME_AL_SPREAD",
        *[f"LME_{m}_{p}_{c}" for m in ("CU", "AL") for p in ("CASH", "3M") for c in ("USD", "EUR")],
    ],
    1: [
        "L01", "L03", "MEPS_DE_HR", "MEPS_DE_EG", "MEPS_FR_HR", "MEPS_FR_CR", "MEPS_FR_HDG",
        "MEPS_FR_EG", "S06", "E23", "E24", "E09", "E10", "E11", "E12", "ED05",
        "EPX_BENZENE", "EPX_ACETONE", "EPX_ECH", "EPX_OTHER", "EPX_RESIN",
    ],
    2: [
        "S01", "S02", "S03", "S04", "S05", "D01", "D02", "E01", "E02", "E03", "E04", "E05",
        "E06", "E07", "E08", "E22", "ED01", "ED02", "ED03", "ED04", "S07", "S08", "S09",
        "S10", "S11", "S12", "S13", "E13", "E14", "E15", "E16", "E17", "E18", "E19",
    ],
    3: ["L02"],
    4: ["E20", "E21", "ED06"],
}  # fmt: skip
PUB_LAG = {series: lag for lag, group in _LAG_GROUPS.items() for series in group}

BACKTEST_DIR = OUTPUTS / "backtest"
BACKTEST_START = "2020-01"
