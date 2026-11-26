"""Backtest plots: rolling coverage and fan charts."""

import matplotlib.pyplot as plt
import pandas as pd

STYLE = "tableau-colorblind10"  # colourblind-safe palette


def _one(results: pd.DataFrame, target: str, horizon: int) -> pd.DataFrame:
    rows = results[(results["target"] == target) & (results["horizon"] == horizon)]
    return rows.sort_values("target_month").set_index("target_month")


def rolling_coverage(
    results: pd.DataFrame, target: str, horizon: int, window: int = 12
) -> plt.Figure:
    """Share of actuals inside P10–P90 over the last `window` target months."""
    rows = _one(results, target, horizon)
    inside = rows["actual"].between(rows["p10"], rows["p90"]).astype(float)
    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(inside.rolling(window).mean() * 100, label=f"rolling {window}-month coverage")
    ax.axhline(80, color="grey", ls="--", lw=1, label="target 80 %")
    ax.set(
        title=f"{target}, +{horizon} months: P10–P90 coverage",
        xlabel="Target month",
        ylabel="Coverage (%)",
        ylim=(0, 105),
    )
    ax.legend(fontsize=8)
    return fig


def fan_chart(results: pd.DataFrame, target: str, horizon: int, unit: str = "") -> plt.Figure:
    """Actual price against the P10–P90 band and P50 forecast made `horizon` months earlier."""
    rows = _one(results, target, horizon)
    with plt.style.context(STYLE):
        fig, ax = plt.subplots(figsize=(9, 4))
    ax.fill_between(rows.index, rows["p10"], rows["p90"], alpha=0.25, label="P10–P90")
    ax.plot(rows["p50"], label="P50")
    ax.plot(rows["actual"], color="black", lw=1.2, label="actual")
    ax.set(
        title=f"{target}: forecasts made {horizon} months ahead",
        xlabel="Target month",
        ylabel=f"Price ({unit})" if unit else "Price",
    )
    ax.legend(fontsize=8)
    return fig
