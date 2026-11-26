"""Features for the pooled model: one row per series × month, all known at that month.

Every change is in volatility units (log change ÷ EWMA volatility × √months), so copper, steel
and price indices share one scale and can be pooled in one model. The target `y` is the log
change over the next `steps` months in the same units; it is NaN where the outcome is not known.

Groups and the steel season pattern come from `docs/eda_findings.md` (§5, §6). The season
pattern (March up, June–July down) was found on the full sample: a mild look-ahead, kept because
it also holds without 2021–22.

Volatility and the list of known data errors come from the shared `bands` module. A known error
month is filled log-linearly from its neighbours once the next month is known; an error in the
last month ends the series one month earlier (as in `bands.target_logs`).
"""

import numpy as np
import pandas as pd

from schneider_forecast.bands import ewma_vol, target_logs

HALFLIFE = 6  # months, EWMA volatility of the features and of the target y
BAND_HALFLIFE = 3  # months, the chosen band half-life (forecasting_other.md §2)
LAGS = (1, 3, 6)  # 12 months dropped: its sign flips at +9
SEASON = {3: 1.0, 6: -1.0, 7: -1.0}  # MEPS steel only (§5)

GROUPS = {
    **{s: "ppi" for s in ["S07", "S08", "S09", "S10", "S11", "S12", "S13"]},
    **{s: "metal" for s in ["S01", "S02", "S03", "S04", "S05", "D01", "D02"]},
    "L01": "steel",
    "L03": "steel",
    "L02": "stainless",
    "EPX_RESIN": "epoxy",
    "S06": "fx",
}
GROUP_NAMES = ("ppi", "metal", "steel", "stainless", "epoxy", "fx")

FEATURES = [
    *(f"mom_{k}" for k in LAGS),
    "mom_1_ppi",
    "mom_3_ppi",
    "ma_gap",
    "market_mom_3",
    "season",
    *(f"is_{g}" for g in GROUP_NAMES),
]


def clean_series(history: pd.DataFrame, name: str) -> pd.Series:
    """Prices of one series with known data errors removed (see module docstring)."""
    return np.exp(target_logs(history, name).interpolate(limit_area="inside"))


def _season(index: pd.DatetimeIndex, steps: int) -> np.ndarray:
    """Sum of the steel season pattern over the months after each date, up to `steps`."""
    months = index.month.to_numpy()
    return np.array(
        [sum(SEASON.get((m + j - 1) % 12 + 1, 0.0) for j in range(1, steps + 1)) for m in months]
    )


def series_features(series: pd.Series, steps: int, group: str) -> pd.DataFrame:
    """Features and target for one series, one row per observed month."""
    s = series.dropna()
    logp = np.log(s)
    vol = ewma_vol(logp, HALFLIFE)
    f = pd.DataFrame(index=s.index)
    for k in LAGS:
        f[f"mom_{k}"] = (logp - logp.shift(k)) / (vol * np.sqrt(k))
    f["ma_gap"] = (logp - logp.rolling(12).mean()) / vol
    f["season"] = _season(s.index, steps) if group == "steel" else 0.0
    f["vol"] = vol
    f["y"] = (logp.shift(-steps) - logp) / (vol * np.sqrt(steps))
    return f


def build_dataset(history: pd.DataFrame, series: list[str], steps: int) -> pd.DataFrame:
    """Stack `series_features` of every series; add market momentum and group terms.

    Rows with a known `y` are training rows; each series' last month is its prediction row.
    """
    frames = []
    for name in series:
        f = series_features(clean_series(history, name), steps, GROUPS.get(name, "other"))
        frames.append(f.assign(series=name, month=f.index).reset_index(drop=True))
    d = pd.concat(frames, ignore_index=True)
    d["market_mom_3"] = d.groupby("month")["mom_3"].transform("mean")
    groups = d["series"].map(GROUPS).fillna("other")
    for g in GROUP_NAMES:
        d[f"is_{g}"] = (groups == g).astype(float)
    for k in (1, 3):
        d[f"mom_{k}_ppi"] = d[f"mom_{k}"] * d["is_ppi"]
    return d
