import pandas as pd


def naive_forecast(series: pd.Series, horizon: int) -> float:
    """Last observed value, used as the forecast for `horizon` months ahead."""
    observed = series.dropna()
    if observed.empty:
        raise ValueError("series has no observed values")
    return float(observed.iloc[-1])
