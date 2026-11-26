"""Rebuild everything from data/raw/ in one command: clean data → forecasts → pricing → CSV.

Run: uv run python -m schneider_forecast.run_all  (needs `uv sync --extra pretrained`)

Each step writes what the next one reads, so they run in this order and the first failure stops
the chain. The raw files are checked first, so a missing data pack fails with one clear message.
"""

import importlib
import time
from pathlib import Path

from schneider_forecast import config

STEPS = ("data", "p2_selection", "p3_selection", "pricing", "procurement", "submit")
RAW_FILES = (
    config.RM_PRICES_WIDE,
    config.ENERGY_PRICES_WIDE,
    config.RM_CATALOG,
    config.ENERGY_CATALOG,
    *config.BOM_FILES.values(),
    config.STEEL_WORKBOOK,
    config.EPOXY,
    config.LME,
    config.RMU_BENCHMARK,
    config.DATA_RAW / "supplier_balance_sheets",
)


def missing_raw_files(paths: tuple[Path, ...] = RAW_FILES) -> list[Path]:
    """Raw inputs that are not in data/raw/."""
    return [path for path in paths if not path.exists()]


def main() -> None:
    missing = missing_raw_files()
    if missing:
        names = "\n".join(f"  {path.relative_to(config.ROOT)}" for path in missing)
        raise SystemExit(
            f"The challenge data is not in data/raw/ ({len(missing)} missing):\n{names}\n"
            "Put the data pack there as shown in the README. Without it, run the tests or "
            "`SCHNEIDER_DEMO=1 uv run streamlit run app/main.py`."
        )
    for step in STEPS:
        start = time.perf_counter()
        print(f"== {step}")
        importlib.import_module(f"schneider_forecast.{step}").main()
        print(f"   done in {time.perf_counter() - start:.0f} s")


if __name__ == "__main__":
    main()
