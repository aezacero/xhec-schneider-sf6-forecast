"""Score backtest results and compare models.

scores = score(results)                 # one row per target × horizon × period
compare(baseline_scores, scores, ...)   # models side by side, skill vs the baseline
"""

import numpy as np
import pandas as pd

from schneider_forecast.config import QUANTILES

KEYS = ["target", "horizon", "period"]
SKILL_METRICS = ["mae_log", "pinball", "interval_score"]


def pinball(actual: np.ndarray, forecast: np.ndarray, q: float) -> np.ndarray:
    """Quantile loss: under-forecasts cost q per unit, over-forecasts cost 1 − q."""
    diff = actual - forecast
    return np.maximum(q * diff, (q - 1) * diff)


def interval_score(
    actual: np.ndarray, lower: np.ndarray, upper: np.ndarray, alpha: float = 0.2
) -> np.ndarray:
    """Width of the band plus 2 / alpha × the distance of any miss (alpha 0.2 → 80 % band)."""
    below = np.maximum(lower - actual, 0)
    above = np.maximum(actual - upper, 0)
    return (upper - lower) + 2 / alpha * (below + above)


def forecast_errors(results: pd.DataFrame) -> pd.DataFrame:
    """Per-forecast errors; pinball and interval score on logs so all units compare."""
    y = np.log(results["actual"])
    logs = {q: np.log(results[f"p{round(q * 100)}"]) for q in QUANTILES}
    p10, p50, p90 = results["p10"], results["p50"], results["p90"]
    return pd.DataFrame(
        {
            "target": results["target"],
            "horizon": results["horizon"],
            "period": np.where(results["target_month"].dt.year <= 2022, "2020-22", "2023-26"),
            "abs_log_error": (y - logs[0.5]).abs(),
            "ape": (results["actual"] - p50).abs() / results["actual"],
            "pinball": sum(pinball(y, logs[q], q) for q in QUANTILES) / len(QUANTILES),
            "interval_score": interval_score(y, logs[0.1], logs[0.9]),
            "inside": results["actual"].between(p10, p90),
            "below_p10": results["actual"] < p10,
            "above_p90": results["actual"] > p90,
            "width": (p90 - p10) / p50,
            # random walk: tomorrow's price = last known value
            "rw_abs_log_error": (y - np.log(results["last_value"])).abs(),
        }
    )


def _aggregate(errors: pd.DataFrame) -> pd.DataFrame:
    table = errors.groupby(KEYS).agg(
        mae_log=("abs_log_error", "mean"),
        mape=("ape", "mean"),
        pinball=("pinball", "mean"),
        interval_score=("interval_score", "mean"),
        coverage=("inside", "mean"),
        below_p10=("below_p10", "mean"),
        above_p90=("above_p90", "mean"),
        width=("width", "mean"),
        n=("abs_log_error", "size"),
        rw_mae_log=("rw_abs_log_error", "mean"),
    )
    # overlapping h-month windows: about one independent error every h origins
    table["n_eff"] = table["n"] / table.index.get_level_values("horizon")
    table["skill_rw"] = 1 - table["mae_log"] / table["rw_mae_log"]
    return table


def score(results: pd.DataFrame, drop_flagged: bool = False) -> pd.DataFrame:
    """Metrics per target × horizon, for all target months and for 2020–22 vs 2023–26."""
    if drop_flagged:
        results = results[~results["flagged"]]
    errors = forecast_errors(results)
    table = pd.concat([_aggregate(errors), _aggregate(errors.assign(period="all"))]).sort_index()
    table.attrs["model"] = results["model"].iloc[0]
    return table


def compare(*scores: pd.DataFrame) -> pd.DataFrame:
    """Several `score` tables side by side; skill = 1 − error / baseline error (first table)."""
    baseline = scores[0][SKILL_METRICS]
    tables = []
    for table in scores:
        skill = 1 - table[SKILL_METRICS] / baseline.reindex(table.index)
        tables.append(table.join(skill.add_prefix("skill_")).assign(model=table.attrs["model"]))
    return pd.concat(tables).set_index("model", append=True).sort_index()
