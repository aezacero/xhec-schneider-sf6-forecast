"""Turn raw-material price forecasts into RMU cost indices, € per unit and quote rules.

Schneider quotes ring main units (RM6 with SF6, RM AirSeT without) months before it buys the
steel, copper and plastics inside them. This module answers: how much could the material cost
of one unit move in 3, 6 and 9 months, and how should a quote protect the margin?

Steps (docs/pricing.md):

1. ``cost_weights``: € per BOM line at the origin and its share of the product cost.
2. ``index_from_ratios``: product cost index, 100 at the origin.
3. ``simulate_index``: joint draws of the index from the material P10 / P50 / P90 forecasts.
4. ``cost_bridge``: € per unit and margin at risk.
5. ``quote_rules``: price adjustment, risk buffer, validity, indexation triggers.
6. ``sensitivity_table``: margin lost for each exposed share × margin.
7. ``run_sensitivities``: index and € cost under other BOM and price assumptions.
8. ``replay_quotes``: the quote rules replayed month by month over 2020–23 (the 2021 surge).
9. ``index_backtest``: our index bands against a naive index, every month since 2020.

Run ``uv run python -m schneider_forecast.pricing``. Forecasts come from the Sep 2026
files in ``outputs/forecasts/``; a series they lack gets a placeholder (last value with
volatility-scaled bands) and a warning. The index backtest reads their strict backtest rows from
``outputs/backtest/``.
"""

import warnings
from functools import partial

import numpy as np
import pandas as pd

from schneider_forecast.backtest import available_at, load_data, run_backtest
from schneider_forecast.bands import ewma_vol, rw_vol_scaled, target_logs
from schneider_forecast.config import (
    BACKTEST_DIR,
    BOM_CLEAN,
    BOM_REFERENCE,
    BOM_VERSIONS,
    DATA_PROCESSED,
    FORECASTS,
    HORIZONS,
    ORIGIN,
    RMU_PRICES,
    SEED,
)
from schneider_forecast.metrics import compare, score

# ---- settings (working assumptions, docs/pricing.md "Assumptions and open questions") ----

PRODUCT_NAMES = {"RMAirSeT IIQ 24kV IEC": "AirSeT", "RM6_NE_IQI_433520": "RM6"}
INDEX_SERIES = {"S11"}  # an index, not a € price: lines on it get a fixed € level
PLASTIC_PRICE_PER_KG = 3.0  # € per kg for plastics and epoxy at the origin (eda_findings.md §8)
FRANCE_STEEL = {"L01": "MEPS_FR_CR"}  # French plant: steel price level from MEPS France
SELLING_PRICE_BRAND = "SE"  # Schneider's P50 price in the RMU file is the selling price
SELLING_PRICE_YEAR = 2026
MARGIN = 0.20  # margin as a share of price (unknown: 10–30 % in the sensitivity)
TOLERANCE = 0.10  # a quote may lose at most this share of the margin before it is revised
SENSITIVITY_SHARES = (0.10, 0.17, 0.25)  # exposed shares tested besides each product's own
SENSITIVITY_MARGINS = (0.10, 0.20, 0.30)
N_DRAWS = 10_000
PLACEHOLDER_HALFLIFE = 3  # months; volatility-scaled band half-life (forecasting_other.md §2)
CRISIS_HALFLIFE = 3  # months; how fast "recent volatility" reacts in the crisis buffer
UNIT_CHECK_RANGE = (0.5, 2.0)  # a P50 outside 0.5–2 × today's value is almost surely a unit slip

# sensitivity settings
FLAT = "FLAT"  # series name for a line whose price never moves
BENCHMARK_PLASTIC_PRICES = {"PBT": 5.50, "ETP": 5.50, "PET": 3.20}  # € per kg (eda_findings.md §8)
OTHER_FLAT_PRICE = 4.0  # € per kg for AirSeT "Other" if kept flat (benchmark default rate)
BRASS_COPPER_SHARE = 0.63  # brass ≈ 63 % copper + 37 % zinc
MISSING_SLICE_SHARE = 0.45  # older BOMs: RM6's unlabelled largest slice (12 Nov file comment)

# what the selection scripts write (p2_selection, p3_selection)
TEAM_FORECAST_FILES = (
    FORECASTS / "p2_forecasts_202609.csv",
    FORECASTS / "p3_forecasts_202609.csv",
)
TEAM_BACKTEST_FILES = (
    BACKTEST_DIR / "p2_selected_strict.csv",
    BACKTEST_DIR / "p3_selected_strict.csv",
)


# ---- 1. cost weights ----


def price_level_series(series: str, plant_country: str) -> str:
    """Return the series that sets the € level of a BOM line.

    Parameters
    ----------
    series : str
        Series the line's price moves with (e.g. ``"L01"``).
    plant_country : str
        Country code of the plant that builds the product (``"FR"`` for RM6).

    Returns
    -------
    str
        The level series: MEPS France for steel bought by the French plant, else ``series``.
    """
    if plant_country == "FR" and series in FRANCE_STEEL:
        return FRANCE_STEEL[series]
    return series


def last_value(prices: pd.DataFrame, series: str) -> float:
    """Return the last observed value of a series.

    Parameters
    ----------
    prices : pandas.DataFrame
        Monthly prices, one column per series, cut at the origin.
    series : str
        Column to read.

    Returns
    -------
    float
        Latest non-missing value (L02 ends one month before the origin).
    """
    return float(prices[series].dropna().iloc[-1])


def brass_price_per_kg(prices: pd.DataFrame) -> float:
    """Price brass as a mix of copper and zinc.

    Parameters
    ----------
    prices : pandas.DataFrame
        Monthly prices with D01 (copper, €/t), S05 (zinc, $/t) and S06 ($ per €).

    Returns
    -------
    float
        € per kg of brass (63 % copper, 37 % zinc).
    """
    copper = last_value(prices, "D01")
    zinc = last_value(prices, "S05") / last_value(prices, "S06")
    return (BRASS_COPPER_SHARE * copper + (1 - BRASS_COPPER_SHARE) * zinc) / 1000


def fill_missing_mass(bom: pd.DataFrame) -> pd.DataFrame:
    """Give a priced BOM line with no mass a share of the product mass (older BOMs only).

    Parameters
    ----------
    bom : pandas.DataFrame
        BOM rows with ``product_ref``, ``share_pct``, ``mass_kg`` and ``price_series``.

    Returns
    -------
    pandas.DataFrame
        Copy of ``bom`` where a priced line without mass gets ``MISSING_SLICE_SHARE`` × product
        mass (product mass = median of mass ÷ share). The v1 BOM has no such line.
    """
    bom = bom.copy()
    total = (bom["mass_kg"] / bom["share_pct"]).groupby(bom["product_ref"]).transform("median")
    gap = bom["price_series"].notna() & bom["mass_kg"].isna()
    bom.loc[gap, "mass_kg"] = MISSING_SLICE_SHARE * total[gap]
    return bom


def cost_weights(
    bom: pd.DataFrame,
    prices: pd.DataFrame,
    plastic_prices: dict[str, float] | None = None,
    epoxy_on_resin_price: bool = False,
    other_flat_price: float | None = None,
    brass_proxy: bool = False,
) -> pd.DataFrame:
    """Price every BOM line at the origin and give its share of the product's material cost.

    Parameters
    ----------
    bom : pandas.DataFrame
        Clean BOM (``bom_clean.csv``): product, plant country, label, family, share, kg,
        price series.
    prices : pandas.DataFrame
        Monthly prices cut at the origin.
    plastic_prices : dict of str to float, optional
        € per kg by plastic name found in the label (e.g. ``{"PBT": 5.5}``); other plastics
        stay at ``PLASTIC_PRICE_PER_KG``.
    epoxy_on_resin_price : bool, default=False
        Price and move epoxy lines with the epoxy resin price (EPX_RESIN) instead of S11.
    other_flat_price : float, optional
        Keep AirSeT "Other" at this € per kg, never moving. Left out when None.
    brass_proxy : bool, default=False
        Price brass as copper + zinc and move it with copper. Left out when False.

    Returns
    -------
    pandas.DataFrame
        One row per priced line: ``product``, ``product_ref``, ``material_family``, ``label``,
        ``mass_kg``, ``series``, ``price_per_kg`` (€), ``cost`` (€ per unit) and ``weight``
        (share of the product's priced cost; sums to 1 per product).
    """
    bom = fill_missing_mass(bom)
    label = bom["material_label_source"].fillna("")
    series = bom["price_series"].copy()
    if epoxy_on_resin_price:
        series[label.str.contains("Epoxy")] = "EPX_RESIN"
    if other_flat_price is not None:
        series[bom["material_family"] == "Other"] = FLAT
    if brass_proxy:
        series[bom["material_family"] == "Brass"] = "D01"
    lines = bom.assign(series=series, label=label).dropna(subset=["series", "mass_kg"])
    lines["product"] = lines["product_ref"].map(PRODUCT_NAMES).fillna(lines["product_ref"])

    price_per_kg = []
    for _, line in lines.iterrows():
        if line["series"] == FLAT:
            price = other_flat_price
        elif line["material_family"] == "Brass":
            price = brass_price_per_kg(prices)
        elif line["series"] in INDEX_SERIES:
            price = PLASTIC_PRICE_PER_KG
            for name, rate in (plastic_prices or {}).items():
                if name in line["label"]:
                    price = rate
        else:
            level = price_level_series(line["series"], line["plant_country"])
            price = last_value(prices, level) / 1000
        price_per_kg.append(price)
    lines["price_per_kg"] = price_per_kg
    lines["cost"] = lines["mass_kg"] * lines["price_per_kg"]
    lines["weight"] = lines["cost"] / lines.groupby("product")["cost"].transform("sum")
    columns = ["product", "product_ref", "material_family", "label", "mass_kg", "series"]
    return lines[columns + ["price_per_kg", "cost", "weight"]].reset_index(drop=True)


# ---- 2. cost index ----


def index_from_ratios(lines: pd.DataFrame, ratios: pd.DataFrame) -> pd.DataFrame:
    """Compute each product's cost index from material price ratios.

    Parameters
    ----------
    lines : pandas.DataFrame
        Output of ``cost_weights``.
    ratios : pandas.DataFrame of shape (n_rows, n_series)
        One column per series, value = future price ÷ price at the origin. A flat line
        (series ``FLAT``) always has ratio 1.

    Returns
    -------
    pandas.DataFrame of shape (n_rows, n_products)
        Cost index per product, 100 = the origin: 100 × Σ weight × ratio.
    """
    ratios = ratios.assign(**{FLAT: 1.0})
    out = {}
    for product, group in lines.groupby("product", sort=False):
        weights = group.groupby("series")["weight"].sum()
        out[product] = 100 * ratios[weights.index].to_numpy() @ weights.to_numpy()
    return pd.DataFrame(out, index=ratios.index)


# ---- 3. scenarios from P10 / P50 / P90 ----


def placeholder_forecasts(
    prices: pd.DataFrame, series_list, origin: str = ORIGIN, horizons=HORIZONS
) -> pd.DataFrame:
    """Forecast every series with the team's random walk and volatility-scaled bands.

    Parameters
    ----------
    prices : pandas.DataFrame
        Monthly prices cut at ``origin`` (the 2021 replay passes earlier months).
    series_list : list of str
        Series to forecast.
    origin : str, default=ORIGIN
        Forecast origin, ``"YYYY-MM"``.
    horizons : tuple of int, default=HORIZONS
        Months ahead.

    Returns
    -------
    pandas.DataFrame
        ``target_id``, ``horizon_m``, ``p10``, ``p50``, ``p90``, ``model_name``.
    """
    origin = pd.Timestamp(origin)
    rows = []
    for series in series_list:
        for horizon in horizons:
            p10, p50, p90 = rw_vol_scaled(
                prices, series, horizon, origin, halflife=PLACEHOLDER_HALFLIFE
            )
            rows.append((series, horizon, p10, p50, p90))
    table = pd.DataFrame(rows, columns=["target_id", "horizon_m", "p10", "p50", "p90"])
    table["model_name"] = "placeholder_rw_vol"
    return table


HARNESS_COLUMNS = {"target": "target_id", "horizon": "horizon_m", "model": "model_name"}


def to_pricing_columns(table: pd.DataFrame) -> pd.DataFrame:
    """Read forecasts in the submission layout or in the backtest harness layout.

    Parameters
    ----------
    table : pandas.DataFrame
        Forecast rows. Harness files (``outputs/backtest/<model>.csv``) name the columns
        target / horizon / model and hold one row per origin.

    Returns
    -------
    pandas.DataFrame
        Rows at the forecast origin with ``target_id``, ``horizon_m``, ``p10``, ``p50``,
        ``p90``, ``model_name``.

    Raises
    ------
    ValueError
        If a quantile column is missing, or a row has P10 > P50, P50 > P90 or a value ≤ 0.
    """
    table = table.rename(columns=HARNESS_COLUMNS)
    if "origin" in table.columns:
        origin = pd.to_datetime(table["origin"]).dt.to_period("M")
        table = table[origin == pd.Period(ORIGIN, "M")]
    if "origin_month" in table.columns:
        table = table[table["origin_month"].astype(str) == ORIGIN]
    needed = ["target_id", "horizon_m", "p10", "p50", "p90"]
    missing = [c for c in needed if c not in table.columns]
    if missing:
        raise ValueError(f"forecast file lacks columns: {', '.join(missing)}")
    bad = (table["p10"] > table["p50"]) | (table["p50"] > table["p90"]) | (table["p10"] <= 0)
    if bad.any():
        raise ValueError(
            f"forecasts break P10 ≤ P50 ≤ P90 or are ≤ 0: {sorted(table[bad]['target_id'])}"
        )
    if "model_name" not in table.columns:
        table = table.assign(model_name="not given")
    return table.reset_index(drop=True)


def check_units(forecasts: pd.DataFrame, prices: pd.DataFrame) -> None:
    """Stop when a forecast is not in the series' own unit.

    Parameters
    ----------
    forecasts : pandas.DataFrame
        Output of ``to_pricing_columns``.
    prices : pandas.DataFrame
        Monthly prices cut at the origin.

    Raises
    ------
    ValueError
        If a P50 is outside ``UNIT_CHECK_RANGE`` × the series' last value: the usual cause is
        a forecast rebased to 100 or given in another currency.
    """
    ratio = forecasts["p50"] / forecasts["target_id"].map(lambda s: last_value(prices, s))
    low, high = UNIT_CHECK_RANGE
    wrong = sorted(set(forecasts.loc[(ratio < low) | (ratio > high), "target_id"]))
    if wrong:
        raise ValueError(f"forecasts not in the series' own unit (rebased?): {wrong}")


def load_forecasts(prices: pd.DataFrame, series_list, files=TEAM_FORECAST_FILES) -> pd.DataFrame:
    """Stack the Sep 2026 material forecasts and fill any gap with a placeholder.

    Parameters
    ----------
    prices : pandas.DataFrame
        Monthly prices cut at the origin.
    series_list : list of str
        Series the cost index needs.
    files : tuple of pathlib.Path, default=TEAM_FORECAST_FILES
        Forecast files to stack; missing files are skipped.

    Returns
    -------
    pandas.DataFrame
        One row per series and horizon (``target_id``, ``horizon_m``, ``p10``, ``p50``,
        ``p90``, ``model_name``). A warning names any series that got a placeholder.
    """
    found = [to_pricing_columns(pd.read_csv(path)) for path in files if path.exists()]
    given = pd.concat(found, ignore_index=True) if found else pd.DataFrame(columns=["target_id"])
    given = given[given["target_id"].isin(series_list)]
    if not given.empty:
        check_units(given, prices)
    missing = [s for s in series_list if s not in set(given["target_id"])]
    if not missing:
        return given.reset_index(drop=True)
    warnings.warn(f"no team forecast for {missing}: using placeholders", stacklevel=2)
    return pd.concat([given, placeholder_forecasts(prices, missing)], ignore_index=True)


def quantile_curve(u: np.ndarray, q10: float, q50: float, q90: float) -> np.ndarray:
    """Turn probabilities into values along straight lines through P10, P50 and P90.

    Parameters
    ----------
    u : numpy.ndarray
        Probabilities between 0 and 1.
    q10, q50, q90 : float
        The forecast's P10, P50 and P90 (here: log changes).

    Returns
    -------
    numpy.ndarray
        Value at each probability; the lines continue past P10 and P90 with the same slope.
    """
    low_slope = (q50 - q10) / 0.4
    high_slope = (q90 - q50) / 0.4
    slope = np.where(u < 0.5, low_slope, high_slope)
    return q50 + (u - 0.5) * slope


def past_changes(
    prices: pd.DataFrame, series_list, horizon: int, origin: str = ORIGIN
) -> pd.DataFrame:
    """Collect past h-month log changes of every series on the same start months.

    Parameters
    ----------
    prices : pandas.DataFrame
        Monthly prices cut at ``origin``.
    series_list : list of str
        Series to include.
    horizon : int
        Months ahead.
    origin : str, default=ORIGIN
        Forecast origin; a series ending earlier (L02) uses a longer change, as its forecast
        does.

    Returns
    -------
    pandas.DataFrame of shape (n_start_months, n_series)
        Log changes; known data errors (epoxy May 2026) are skipped via ``target_logs``.
    """
    origin = pd.Timestamp(origin).to_period("M")
    changes = {}
    for series in series_list:
        values = target_logs(prices, series)
        gap = (origin - values.dropna().index[-1].to_period("M")).n
        values = values.asfreq("MS")
        changes[series] = values.shift(-(horizon + gap)) - values
    return pd.DataFrame(changes).dropna()


def past_change_ranks(
    prices: pd.DataFrame, series_list, horizon: int, origin: str = ORIGIN
) -> pd.DataFrame:
    """Rank each past h-month change between 0 and 1 within its own series.

    Parameters
    ----------
    prices, series_list, horizon, origin
        As in ``past_changes``.

    Returns
    -------
    pandas.DataFrame of shape (n_start_months, n_series)
        Rank ÷ (count + 1): how high each month's move was for each material.
    """
    changes = past_changes(prices, series_list, horizon, origin)
    return changes.rank() / (len(changes) + 1)


def simulate_index(
    lines: pd.DataFrame,
    forecasts: pd.DataFrame,
    prices: pd.DataFrame,
    horizon: int,
    n_draws: int = N_DRAWS,
    seed: int = SEED,
    origin: str = ORIGIN,
) -> pd.DataFrame:
    """Draw joint scenarios of the cost index at one horizon.

    Each draw picks a past month at random and keeps how every material ranked in it, so
    materials move together as they did; the size of each move comes from its forecast band.

    Parameters
    ----------
    lines : pandas.DataFrame
        Output of ``cost_weights``.
    forecasts : pandas.DataFrame
        One forecast per series and horizon (``target_id``, ``horizon_m``, P10 / P50 / P90).
    prices : pandas.DataFrame
        Monthly prices cut at ``origin``.
    horizon : int
        Months ahead.
    n_draws : int, default=N_DRAWS
        Number of joint draws.
    seed : int, default=SEED
        Random seed, so a rerun gives the same numbers.
    origin : str, default=ORIGIN
        Forecast origin.

    Returns
    -------
    pandas.DataFrame of shape (n_draws, n_products)
        Cost index per draw and product, 100 = the origin.

    Raises
    ------
    ValueError
        If a series has no forecast, or more than one, at ``horizon``.
    """
    series_list = sorted(set(lines["series"]) - {FLAT})
    ranks = past_change_ranks(prices, series_list, horizon, origin)
    rng = np.random.default_rng(seed)
    picked = ranks.iloc[rng.integers(len(ranks), size=n_draws)].reset_index(drop=True)
    ratios = {}
    for series in series_list:
        row = forecasts[(forecasts["target_id"] == series) & (forecasts["horizon_m"] == horizon)]
        if len(row) != 1:
            raise ValueError(f"need one forecast for {series} at +{horizon}, found {len(row)}")
        start = last_value(prices, series)
        q10, q50, q90 = (np.log(row[q].iloc[0] / start) for q in ("p10", "p50", "p90"))
        ratios[series] = np.exp(quantile_curve(picked[series].to_numpy(), q10, q50, q90))
    return index_from_ratios(lines, pd.DataFrame(ratios))


def index_scenarios(draws_by_horizon: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Summarise the index draws as P10 / P50 / P90.

    Parameters
    ----------
    draws_by_horizon : dict of int to pandas.DataFrame
        Output of ``simulate_index`` per horizon.

    Returns
    -------
    pandas.DataFrame
        ``product``, ``horizon_m``, ``p10``, ``p50``, ``p90``.
    """
    rows = []
    for horizon, draws in draws_by_horizon.items():
        for product in draws.columns:
            p10, p50, p90 = np.quantile(draws[product], [0.1, 0.5, 0.9])
            rows.append((product, horizon, p10, p50, p90))
    return pd.DataFrame(rows, columns=["product", "horizon_m", "p10", "p50", "p90"])


# ---- 4. cost bridge: € per unit and margin at risk ----


def selling_price(rmu: pd.DataFrame) -> float:
    """Read Schneider's P50 unit price for the selling year.

    Parameters
    ----------
    rmu : pandas.DataFrame
        RMU price benchmark (``rmu_prices.csv``), synthetic, one price per brand and year.

    Returns
    -------
    float
        € per unit; used for both products (the file does not say which product it is).
    """
    row = rmu[(rmu["brand_id"] == SELLING_PRICE_BRAND) & (rmu["year"] == SELLING_PRICE_YEAR)]
    return float(row["p50"].iloc[0])


def cost_bridge(
    scenarios: pd.DataFrame, lines: pd.DataFrame, price: float, margin: float = MARGIN
) -> pd.DataFrame:
    """Turn index scenarios into € per unit and margin at risk at a fixed price.

    Parameters
    ----------
    scenarios : pandas.DataFrame
        Output of ``index_scenarios``.
    lines : pandas.DataFrame
        Output of ``cost_weights``.
    price : float
        Selling price per unit (€).
    margin : float, default=MARGIN
        Margin as a share of price.

    Returns
    -------
    pandas.DataFrame
        ``scenarios`` plus ``cost_now``, ``cost_p10/p50/p90`` (€), ``exposed_share`` (material
        cost ÷ price) and margin at risk at P90 as a share of price, in € and as a share of
        the margin.
    """
    table = scenarios.copy()
    cost_now = lines.groupby("product")["cost"].sum()
    table["cost_now"] = table["product"].map(cost_now)
    for q in ("p10", "p50", "p90"):
        table[f"cost_{q}"] = table["cost_now"] * table[q] / 100
    table["price"] = price
    table["exposed_share"] = table["cost_now"] / price
    table["margin_at_risk_share_of_price"] = table["exposed_share"] * (table["p90"] / 100 - 1)
    table["margin_at_risk_eur"] = table["margin_at_risk_share_of_price"] * price
    table["margin_at_risk_share_of_margin"] = table["margin_at_risk_share_of_price"] / margin
    return table


# ---- 5. quote rules ----


def volatility_ratio(prices: pd.DataFrame, series: str) -> float:
    """Compare a series' latest volatility with its usual level.

    Parameters
    ----------
    prices : pandas.DataFrame
        Monthly prices cut at the origin.
    series : str
        Column to read.

    Returns
    -------
    float
        Latest EWMA volatility ÷ the median volatility since the series began.
    """
    vol = ewma_vol(target_logs(prices, series), CRISIS_HALFLIFE).dropna()
    return float(vol.iloc[-1] / vol.median())


def crisis_factors(lines: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    """Scale each product's risk buffer up when markets are unusually volatile.

    Tested in the 2021 replay only, not used in the live quote rules: the team bands already
    widen with volatility, so this counts it twice and overprices after a shock.

    Parameters
    ----------
    lines : pandas.DataFrame
        Output of ``cost_weights``.
    prices : pandas.DataFrame
        Monthly prices cut at the origin.

    Returns
    -------
    pandas.Series
        Cost-weighted volatility ratio per product, never below 1.
    """
    moving = lines[lines["series"] != FLAT]
    ratios = moving["series"].map(lambda s: volatility_ratio(prices, s))
    weighted = (ratios * moving["weight"]).groupby(moving["product"]).sum()
    weighted /= moving.groupby("product")["weight"].sum()
    return weighted.clip(lower=1.0).rename("crisis_factor")


def quote_rules(
    bridge: pd.DataFrame,
    margin: float = MARGIN,
    tolerance: float = TOLERANCE,
    crisis: pd.Series | None = None,
) -> pd.DataFrame:
    """Build the price adjustment, risk buffer and quotes per product, horizon and scenario.

    Parameters
    ----------
    bridge : pandas.DataFrame
        Output of ``cost_bridge``.
    margin : float, default=MARGIN
        Margin as a share of price.
    tolerance : float, default=TOLERANCE
        Share of the margin a quote may lose before it must be revised.
    crisis : pandas.Series, optional
        Crisis factor per product (``crisis_factors``); 1 when None.

    Returns
    -------
    pandas.DataFrame
        Per product and horizon: ``price_adjustment`` (exposed share × P50 change),
        ``band_buffer`` (exposed share × (P90 − P50)), ``risk_buffer`` (band × crisis),
        quotes at P10 / P50 / P90, ``quote_with_buffer`` and ``within_tolerance``.
    """
    table = bridge[["product", "horizon_m", "price", "exposed_share", "p10", "p50", "p90"]].copy()
    share = table["exposed_share"]
    table["price_adjustment"] = share * (table["p50"] / 100 - 1)
    table["band_buffer"] = share * (table["p90"] - table["p50"]) / 100
    table["crisis_factor"] = 1.0 if crisis is None else table["product"].map(crisis).fillna(1.0)
    table["risk_buffer"] = table["band_buffer"] * table["crisis_factor"]
    for q in ("p10", "p50", "p90"):
        table[f"quote_{q}"] = table["price"] * (1 + share * (table[q] / 100 - 1))
    table["quote_with_buffer"] = table["price"] * (
        1 + table["price_adjustment"] + table["risk_buffer"]
    )
    table["within_tolerance"] = table["risk_buffer"] <= tolerance * margin
    return table


def quote_validity(rules: pd.DataFrame) -> pd.Series:
    """Find how long each product's quote can stay open.

    Parameters
    ----------
    rules : pandas.DataFrame
        Output of ``quote_rules``.

    Returns
    -------
    pandas.Series
        Longest horizon (months) whose risk buffer stays within the tolerance; 0 if none.
    """
    ok = rules[rules["within_tolerance"]]
    longest = ok.groupby("product")["horizon_m"].max()
    return longest.reindex(rules["product"].unique(), fill_value=0).rename("validity_months")


def index_triggers(
    lines: pd.DataFrame, price: float, margin: float = MARGIN, tolerance: float = TOLERANCE
) -> pd.DataFrame:
    """Find how far each price index can move before the quote must be revised.

    Parameters
    ----------
    lines : pandas.DataFrame
        Output of ``cost_weights``.
    price : float
        Selling price per unit (€).
    margin : float, default=MARGIN
        Margin as a share of price.
    tolerance : float, default=TOLERANCE
        Share of the margin a quote may lose.

    Returns
    -------
    pandas.DataFrame
        Per product and series: ``cost``, ``weight``, ``exposed_share`` and ``trigger_move``
        = tolerance × margin ÷ (exposed share × weight), as a fraction (0.5 = ±50 %).
    """
    table = lines.groupby(["product", "series"], as_index=False)[["cost", "weight"]].sum()
    exposed = table.groupby("product")["cost"].transform("sum") / price
    table["exposed_share"] = exposed
    table["trigger_move"] = tolerance * margin / (exposed * table["weight"])
    return table.sort_values(["product", "weight"], ascending=[True, False])


# ---- 6. sensitivity table ----


def sensitivity_table(bridge: pd.DataFrame) -> pd.DataFrame:
    """Show the margin lost at P90 for each exposed share × margin.

    Parameters
    ----------
    bridge : pandas.DataFrame
        Output of ``cost_bridge``.

    Returns
    -------
    pandas.DataFrame
        ``product``, ``horizon_m``, ``exposed_share``, ``margin``, ``margin_lost`` (share of
        the margin) for the product's own share and each value in ``SENSITIVITY_SHARES``.
    """
    rows = []
    for _, row in bridge.iterrows():
        cost_rise = row["p90"] / 100 - 1
        for share in (row["exposed_share"], *SENSITIVITY_SHARES):
            for margin in SENSITIVITY_MARGINS:
                lost = share * cost_rise / margin
                rows.append((row["product"], row["horizon_m"], share, margin, lost))
    columns = ["product", "horizon_m", "exposed_share", "margin", "margin_lost"]
    return pd.DataFrame(rows, columns=columns)


# ---- 7. BOM and price sensitivities ----

SENSITIVITIES = {
    "base": {},
    "epoxy_resin_price": {"epoxy_on_resin_price": True},
    "plastics_benchmark_rates": {"plastic_prices": BENCHMARK_PLASTIC_PRICES},
    "other_kept_flat": {"other_flat_price": OTHER_FLAT_PRICE},
    "brass_copper_zinc": {"brass_proxy": True},
}


def run_sensitivities(
    bom: pd.DataFrame, bom_versions: pd.DataFrame, prices: pd.DataFrame, n_draws: int = N_DRAWS
) -> pd.DataFrame:
    """Recompute cost and index under each BOM and price assumption.

    Parameters
    ----------
    bom : pandas.DataFrame
        Reference (v1) BOM.
    bom_versions : pandas.DataFrame
        All BOM versions stacked with a ``version`` column (``bom_versions.csv``).
    prices : pandas.DataFrame
        Monthly prices cut at the origin.
    n_draws : int, default=N_DRAWS
        Draws per horizon.

    Returns
    -------
    pandas.DataFrame
        ``case``, ``product``, ``cost_now``, ``horizon_m``, ``p10``, ``p50``, ``p90`` for the
        base, each ``cost_weights`` option and every older BOM version.
    """
    cases = [(name, bom, options) for name, options in SENSITIVITIES.items()]
    for version, old_bom in bom_versions.groupby("version"):
        if version != BOM_REFERENCE:
            cases.append((f"bom_{version.split()[0]}", old_bom, {}))
    tables = []
    for name, case_bom, options in cases:
        lines = cost_weights(case_bom, prices, **options)
        forecasts = load_forecasts(prices, sorted(set(lines["series"]) - {FLAT}))
        draws = {h: simulate_index(lines, forecasts, prices, h, n_draws) for h in HORIZONS}
        table = index_scenarios(draws)
        cost_now = table["product"].map(lines.groupby("product")["cost"].sum())
        tables.append(table.assign(case=name, cost_now=cost_now))
    columns = ["case", "product", "cost_now", "horizon_m", "p10", "p50", "p90"]
    return pd.concat(tables, ignore_index=True)[columns]


# ---- 8. the 2021 replay: what the quote rules would have done in the 2021–22 surge ----

REPLAY_START = "2020-01"
REPLAY_END = "2023-12"
REPLAY_HORIZON = 6  # months from the quote to when the material is bought
REPLAY_DRAWS = 2_000


def actual_index(
    lines: pd.DataFrame,
    history: pd.DataFrame,
    prices: pd.DataFrame,
    quote_month: pd.Timestamp,
    horizon: int,
) -> pd.Series:
    """Measure the cost index as it really turned out after a quote.

    Parameters
    ----------
    lines : pandas.DataFrame
        Output of ``cost_weights`` at the quote month.
    history : pandas.DataFrame
        Prices known at the quote month (the starting values).
    prices : pandas.DataFrame
        All prices (the realised values).
    quote_month : pandas.Timestamp
        Month the quote is made.
    horizon : int
        Months until the material is bought.

    Returns
    -------
    pandas.Series
        Realised index per product, 100 = the last known value at the quote; NaN when the
        target month has no price.
    """
    end = quote_month + pd.DateOffset(months=horizon)
    ratios = {}
    for series in sorted(set(lines["series"]) - {FLAT}):
        ratios[series] = [prices[series].get(end, np.nan) / last_value(history, series)]
    return index_from_ratios(lines, pd.DataFrame(ratios)).iloc[0]


def replay_quotes(
    bom: pd.DataFrame,
    prices: pd.DataFrame,
    catalog: pd.DataFrame,
    exposed_share: pd.Series,
    horizon: int = REPLAY_HORIZON,
    start: str = REPLAY_START,
    end: str = REPLAY_END,
    margin: float = MARGIN,
    n_draws: int = REPLAY_DRAWS,
) -> pd.DataFrame:
    """Replay the quote rules every month with only the data already published that month.

    Margin lost is a share of the margin (0.25 = a quarter of the margin gone; below 0 = the
    price ended above what cost needed, i.e. we overpriced). Three policies: fixed price
    (ignores raw materials), band buffer (P50 adjustment + P90 band buffer) and crisis buffer
    (band buffer × crisis factor). Forecasts are the team's random walk with volatility bands,
    refitted each month on the strict data cut (``available_at(strict=True)``), as in model
    selection.

    Parameters
    ----------
    bom : pandas.DataFrame
        Reference BOM.
    prices : pandas.DataFrame
        All monthly prices.
    catalog : pandas.DataFrame
        Series catalog with ``gap_months`` and ``pub_lag`` (publication lags).
    exposed_share : pandas.Series
        Material cost ÷ price per product (today's value, used as a fixed scale).
    horizon : int, default=REPLAY_HORIZON
        Months from quote to purchase.
    start, end : str
        First and last quote month, ``"YYYY-MM"``.
    margin : float, default=MARGIN
        Margin as a share of price.
    n_draws : int, default=REPLAY_DRAWS
        Draws per quote month.

    Returns
    -------
    pandas.DataFrame
        One row per product and quote month: forecast P10 / P50 / P90, actual index, crisis
        factor and margin lost under each policy.
    """
    rows = []
    for quote_month in pd.date_range(start, end, freq="MS"):
        history = available_at(prices, catalog, quote_month, strict=True)
        lines = cost_weights(bom, history)
        series_list = sorted(set(lines["series"]) - {FLAT})
        forecasts = placeholder_forecasts(history, series_list, quote_month, (horizon,))
        draws = simulate_index(lines, forecasts, history, horizon, n_draws, origin=quote_month)
        actual = actual_index(lines, history, prices, quote_month, horizon)
        crisis = crisis_factors(lines, history)
        for product in draws.columns:
            if pd.isna(actual[product]):
                continue
            p10, p50, p90 = np.quantile(draws[product], [0.1, 0.5, 0.9])
            share = exposed_share[product]
            cost_rise = share * (actual[product] / 100 - 1)
            adjustment = share * (p50 / 100 - 1)
            band_buffer = share * (p90 - p50) / 100
            crisis_buffer = band_buffer * crisis[product]
            rows.append(
                {
                    "product": product,
                    "quote_month": quote_month,
                    "target_month": quote_month + pd.DateOffset(months=horizon),
                    "p10": p10,
                    "p50": p50,
                    "p90": p90,
                    "actual_index": actual[product],
                    "crisis_factor": crisis[product],
                    "margin_lost_fixed_price": cost_rise / margin,
                    "margin_lost_band_buffer": (cost_rise - adjustment - band_buffer) / margin,
                    "margin_lost_crisis_buffer": (cost_rise - adjustment - crisis_buffer) / margin,
                }
            )
    return pd.DataFrame(rows)


def replay_period(month: pd.Timestamp) -> str:
    """Name the period a purchase month belongs to.

    Parameters
    ----------
    month : pandas.Timestamp
        Month the material is bought.

    Returns
    -------
    str
        ``"2020"``, ``"2021-22"`` (the surge) or ``"2023-24"``.
    """
    if month.year <= 2020:
        return "2020"
    if month.year <= 2022:
        return "2021-22"
    return "2023-24"


REPLAY_POLICIES = ("fixed_price", "band_buffer", "crisis_buffer")


def replay_summary(replay: pd.DataFrame) -> pd.DataFrame:
    """Summarise the replay per product, pricing policy and purchase period.

    Parameters
    ----------
    replay : pandas.DataFrame
        Output of ``replay_quotes``.

    Returns
    -------
    pandas.DataFrame
        ``avg_margin_lost``, ``worst_margin_lost``, ``avg_overpriced`` (how far the price
        ended above what cost needed, share of margin) and ``share_above_p90`` (how often cost
        beat the P90).
    """
    rows = []
    period = replay["target_month"].map(replay_period)
    for (product, when), group in replay.groupby([replay["product"], period]):
        above_p90 = (group["actual_index"] > group["p90"]).mean()
        for policy in REPLAY_POLICIES:
            lost = group[f"margin_lost_{policy}"]
            rows.append(
                {
                    "product": product,
                    "period": when,
                    "policy": policy,
                    "quotes": len(group),
                    "avg_margin_lost": lost.mean(),
                    "worst_margin_lost": lost.max(),
                    "avg_overpriced": (-lost).clip(lower=0).mean(),
                    "share_above_p90": above_p90,
                }
            )
    return pd.DataFrame(rows)


# ---- 9. index backtest: our index bands against a naive index ----

INDEX_MODEL = "p4_bom_index"
NAIVE_MODEL = "naive_index"


def load_material_backtest(series_list, files=TEAM_BACKTEST_FILES) -> pd.DataFrame:
    """Stack the selections' strict-run backtest rows for every BOM series.

    Parameters
    ----------
    series_list : list of str
        Series the cost index needs.
    files : tuple of pathlib.Path, default=TEAM_BACKTEST_FILES
        Harness backtest files; missing files are skipped.

    Returns
    -------
    pandas.DataFrame
        Harness rows (one per origin × series × horizon). A series the files lack gets the
        team baseline run here through the backtest harness, also strict, with a warning.
    """
    found = [
        pd.read_csv(path, parse_dates=["origin", "target_month"]) for path in files if path.exists()
    ]
    given = pd.concat(found, ignore_index=True) if found else pd.DataFrame(columns=["target"])
    given = given[given["target"].isin(series_list)]
    missing = [s for s in series_list if s not in set(given["target"])]
    if not missing:
        return given.reset_index(drop=True)
    warnings.warn(f"no team backtest for {missing}: running the baseline", stacklevel=2)
    model = partial(rw_vol_scaled, halflife=PLACEHOLDER_HALFLIFE)
    baseline = run_backtest(
        model, "p4_placeholder_rw_vol", targets=missing, strict=True, track_co2=False
    )
    return pd.concat([given, baseline], ignore_index=True)


def naive_index_band(
    lines: pd.DataFrame, history: pd.DataFrame, horizon: int, origin: pd.Timestamp
) -> pd.DataFrame:
    """Forecast the index naively: no change, with the basket's own past moves as the band.

    Parameters
    ----------
    lines : pandas.DataFrame
        Output of ``cost_weights`` at the origin.
    history : pandas.DataFrame
        Prices known at the origin.
    horizon : int
        Months ahead.
    origin : pandas.Timestamp
        Forecast origin.

    Returns
    -------
    pandas.DataFrame
        Per product: ``p10`` and ``p90`` (past h-month moves of the same basket), ``p50`` = 100.
    """
    series_list = sorted(set(lines["series"]) - {FLAT})
    moves = index_from_ratios(lines, np.exp(past_changes(history, series_list, horizon, origin)))
    low, high = moves.quantile(0.1), moves.quantile(0.9)
    return pd.DataFrame({"p10": low.clip(upper=100), "p50": 100.0, "p90": high.clip(lower=100)})


def index_backtest(
    material_results: pd.DataFrame,
    bom: pd.DataFrame,
    prices: pd.DataFrame,
    catalog: pd.DataFrame,
    n_draws: int = REPLAY_DRAWS,
    strict: bool = True,
) -> pd.DataFrame:
    """Backtest our cost index against a naive index at every past origin.

    Parameters
    ----------
    material_results : pandas.DataFrame
        Harness backtest rows for every BOM series (``load_material_backtest``).
    bom : pandas.DataFrame
        Reference BOM.
    prices : pandas.DataFrame
        All monthly prices.
    catalog : pandas.DataFrame
        Series catalog (publication lags for ``available_at``).
    n_draws : int, default=REPLAY_DRAWS
        Draws per origin.
    strict : bool, default=True
        Data cut; must match the material rows (the model selections use the strict run).

    Returns
    -------
    pandas.DataFrame
        Harness layout (one row per origin × horizon × product × model), so the harness's ``score``
        and ``compare`` work unchanged. Origins where a material has no forecast are skipped
        with a warning.
    """
    results = material_results.rename(columns=HARNESS_COLUMNS)
    rows = []
    skipped = 0
    for (origin, horizon), group in results.groupby(["origin", "horizon_m"]):
        history = available_at(prices, catalog, origin, strict)
        lines = cost_weights(bom, history)
        series_list = sorted(set(lines["series"]) - {FLAT})
        if not set(series_list) <= set(group["target_id"]):
            skipped += 1
            continue
        group = group.set_index("target_id").loc[series_list]
        draws = simulate_index(lines, group.reset_index(), history, horizon, n_draws, origin=origin)
        actual_ratios = pd.DataFrame([group["actual"] / group["last_value"]])
        actual = index_from_ratios(lines, actual_ratios).iloc[0]
        naive = naive_index_band(lines, history, horizon, origin)
        common = {
            "origin": origin,
            "horizon": horizon,
            "target_month": group["target_month"].iloc[0],
            "last_value": 100.0,
            "flagged": bool(group["flagged"].any()),
        }
        for product in draws.columns:
            p10, p50, p90 = np.quantile(draws[product], [0.1, 0.5, 0.9])
            rows.append(
                {"model": INDEX_MODEL, "target": product, **common, "actual": actual[product]}
                | {"p10": p10, "p50": p50, "p90": p90}
            )
            rows.append(
                {"model": NAIVE_MODEL, "target": product, **common, "actual": actual[product]}
                | naive.loc[product].to_dict()
            )
    if skipped:
        warnings.warn(f"{skipped} cells skipped: a material lacks a forecast", stacklevel=2)
    return pd.DataFrame(rows)


def index_backtest_scores(index_results: pd.DataFrame) -> pd.DataFrame:
    """Score both indices with the harness metrics.

    Parameters
    ----------
    index_results : pandas.DataFrame
        Output of ``index_backtest``.

    Returns
    -------
    pandas.DataFrame
        The harness's ``compare`` table: metrics per product × horizon × period, with
        skill = 1 − our error ÷ the naive index's error.
    """
    naive = score(index_results[index_results["model"] == NAIVE_MODEL])
    ours = score(index_results[index_results["model"] == INDEX_MODEL])
    return compare(naive, ours).reset_index()


# ---- outputs ----


def cost_gap(draws_by_horizon: dict[int, pd.DataFrame], lines: pd.DataFrame) -> pd.DataFrame:
    """Measure the AirSeT minus RM6 material cost per unit (Goal B input).

    Parameters
    ----------
    draws_by_horizon : dict of int to pandas.DataFrame
        Output of ``simulate_index`` per horizon (both products in the same draws).
    lines : pandas.DataFrame
        Output of ``cost_weights``.

    Returns
    -------
    pandas.DataFrame
        ``horizon_m``, ``gap_now`` and the gap's ``p10``, ``p50``, ``p90`` (€ per unit).
    """
    cost_now = lines.groupby("product")["cost"].sum()
    rows = []
    for horizon, draws in draws_by_horizon.items():
        gap = cost_now["AirSeT"] * draws["AirSeT"] / 100 - cost_now["RM6"] * draws["RM6"] / 100
        p10, p50, p90 = np.quantile(gap, [0.1, 0.5, 0.9])
        rows.append((horizon, cost_now["AirSeT"] - cost_now["RM6"], p10, p50, p90))
    return pd.DataFrame(rows, columns=["horizon_m", "gap_now", "p10", "p50", "p90"])


def bom_index_rows(scenarios: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """Write the 6 ``bom_index`` rows in the submission layout.

    Parameters
    ----------
    scenarios : pandas.DataFrame
        Output of ``index_scenarios``.
    lines : pandas.DataFrame
        Output of ``cost_weights`` (for the BOM ``product_ref``).

    Returns
    -------
    pandas.DataFrame
        Submission columns without ``team_id`` and ``ai_tools`` (``submit`` adds them).
    """
    refs = lines.drop_duplicates("product").set_index("product")["product_ref"]
    origin = pd.Period(ORIGIN, "M")
    return pd.DataFrame(
        {
            "target_type": "bom_index",
            "target_id": scenarios["product"].map(refs),
            "region": "EU",
            "origin_month": ORIGIN,
            "horizon_m": scenarios["horizon_m"],
            "target_month": [str(origin + h) for h in scenarios["horizon_m"]],
            "unit": "index (origin=100)",
            "p10": scenarios["p10"].round(2),
            "p50": scenarios["p50"].round(2),
            "p90": scenarios["p90"].round(2),
            "model_name": "bom_joint_sim_v1",
        }
    )


def main() -> None:
    """Run the whole pricing chain and write every table to ``data/processed/``."""
    prices, catalog, _ = load_data()
    bom = pd.read_csv(BOM_CLEAN)
    rmu = pd.read_csv(RMU_PRICES)

    lines = cost_weights(bom, prices)
    forecasts = load_forecasts(prices, sorted(lines["series"].unique()))
    draws = {h: simulate_index(lines, forecasts, prices, h) for h in HORIZONS}
    scenarios = index_scenarios(draws)
    price = selling_price(rmu)
    bridge = cost_bridge(scenarios, lines, price)
    # no crisis factor: the 2021 replay shows it double counts (the bands already widen with
    # volatility) and overprices after a shock
    rules = quote_rules(bridge)
    exposed = bridge.groupby("product")["exposed_share"].first()
    replay = replay_quotes(bom, prices, catalog, exposed)
    summary = replay_summary(replay)
    material_results = load_material_backtest(sorted(set(lines["series"]) - {FLAT}))
    index_results = index_backtest(material_results, bom, prices, catalog)
    index_scores = index_backtest_scores(index_results)

    outputs = {
        "pricing_cost_weights.csv": lines,
        "pricing_forecasts_used.csv": forecasts,
        "bom_index_rows.csv": bom_index_rows(scenarios, lines),
        "pricing_cost_bridge.csv": bridge,
        "quote_rules.csv": rules,
        "quote_validity.csv": quote_validity(rules).reset_index(),
        "index_triggers.csv": index_triggers(lines, price),
        "sensitivity_table.csv": sensitivity_table(bridge),
        "cost_gap.csv": cost_gap(draws, lines),
        "pricing_sensitivities.csv": run_sensitivities(bom, pd.read_csv(BOM_VERSIONS), prices),
        "replay_2021.csv": replay,
        "replay_2021_summary.csv": summary,
        "index_backtest.csv": index_results,
        "index_backtest_scores.csv": index_scores,
    }
    for name, table in outputs.items():
        table.to_csv(DATA_PROCESSED / name, index=False)

    used = forecasts["model_name"].unique()
    print(f"Forecasts used: {', '.join(used)}")
    print(lines.groupby("product")["cost"].sum().round(0).to_string())
    print(scenarios.round(1).to_string(index=False))
    print(summary.round(3).to_string(index=False))
    print(f"Written to {DATA_PROCESSED}: {', '.join(outputs)}")


if __name__ == "__main__":
    main()
