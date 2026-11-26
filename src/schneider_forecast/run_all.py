"""Rebuild everything from data/raw/ in one command: clean data → forecasts → pricing → CSV.

Run: uv run python -m schneider_forecast.run_all  (needs `uv sync --extra pretrained`)

Each step writes what the next one reads, so they run in this order and the first failure stops
the chain.
"""

import importlib
import time

STEPS = ("data", "p2_selection", "p3_selection", "pricing", "procurement", "submit")


def main() -> None:
    for step in STEPS:
        start = time.perf_counter()
        print(f"== {step}")
        importlib.import_module(f"schneider_forecast.{step}").main()
        print(f"   done in {time.perf_counter() - start:.0f} s")


if __name__ == "__main__":
    main()
