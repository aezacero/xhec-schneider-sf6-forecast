"""Smoke test of the submission build on the real files (skipped where they are absent, e.g. CI)."""

import pandas as pd
import pytest

from schneider_forecast import submit
from schneider_forecast.config import EXPECTED_TARGETS, PRICES_WIDE, SERIES_CATALOG

NEEDED = (PRICES_WIDE, SERIES_CATALOG, submit.BOM_INDEX_FILE, *submit.MATERIAL_FILES)
pytestmark = pytest.mark.skipif(
    not all(path.exists() for path in NEEDED), reason="needs the real data and forecast files"
)


def test_real_submission_has_every_target_and_passes_the_checks():
    """19 materials + 2 products, 3 horizons each, every check passing."""
    prices = pd.read_csv(PRICES_WIDE, parse_dates=["month"], index_col="month")
    catalog = pd.read_csv(SERIES_CATALOG, index_col="series_id")
    table = submit.build_submission(
        submit.read_csvs(submit.MATERIAL_FILES),
        submit.read_csvs([submit.BOM_INDEX_FILE]),
        prices,
        catalog,
    )
    submit.check_submission(table)
    assert len(table) == (len(EXPECTED_TARGETS) + len(submit.PRODUCTS)) * 3
