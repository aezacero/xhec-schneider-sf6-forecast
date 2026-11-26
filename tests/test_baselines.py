import numpy as np
import pandas as pd
import pytest

from schneider_forecast.baselines import naive_forecast


def test_naive_forecast_returns_last_observed_value():
    s = pd.Series([1.0, 2.0, np.nan])
    assert naive_forecast(s, horizon=3) == 2.0


def test_naive_forecast_rejects_empty_series():
    with pytest.raises(ValueError):
        naive_forecast(pd.Series([np.nan, np.nan]), horizon=3)
