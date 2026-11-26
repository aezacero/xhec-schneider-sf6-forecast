"""Inputs and quote numbers for the decision tool in ``app/``.

A salesperson or buyer picks a product, a quote validity, a list price, a margin and a cost
scenario; this module returns the recommended quote and the numbers behind it. Every formula
comes from ``pricing.py``: this module only loads inputs and picks rows.

The tool reads only local, git-ignored files (``data/processed/``, ``outputs/``). When they are
missing, or ``SCHNEIDER_DEMO=1`` is set, it runs on generated demo data with the same columns,
so it starts anywhere, CI included.
"""

import os
import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from schneider_forecast import pricing as P
from schneider_forecast.backtest import load_data
from schneider_forecast.config import (
    BOM_CLEAN,
    DATA_PROCESSED,
    EXPECTED_TARGETS,
    HORIZONS,
    ORIGIN,
    PRICES_WIDE,
    PUB_LAG,
    RMU_PRICES,
    SEED,
    SERIES_CATALOG,
)
from schneider_forecast.metrics import score

# scenario name → the cost quantile the quote covers
SCENARIOS = {"Downside": "p90", "Baseline": "p50", "Upside": "p10"}
SCENARIO_HINTS = {
    "Downside": "Covers costs up to P90; worse only 1 time in 10.",
    "Baseline": "Covers the expected cost (P50) with no buffer.",
    "Upside": "Assumes costs fall to P10; lowest price, highest risk.",
}
REAL_FILES = (PRICES_WIDE, SERIES_CATALOG, BOM_CLEAN, RMU_PRICES)
REPLAY_FILE = DATA_PROCESSED / "replay_2021.csv"
WHAT_IF_FAMILIES = {"copper": ("Copper",), "steel": ("steel",)}  # matched in material_family
DEMO_REPLAY_DRAWS = 300


@dataclass
class Inputs:
    """Everything the pricing chain reads."""

    prices: pd.DataFrame
    catalog: pd.DataFrame
    bom: pd.DataFrame
    rmu: pd.DataFrame
    demo: bool


@dataclass
class Model:
    """The cost scenarios, computed once and reused for every quote."""

    lines: pd.DataFrame
    forecasts: pd.DataFrame
    draws: dict[int, pd.DataFrame]
    scenarios: pd.DataFrame
    notes: list[str]


# ---- inputs ----


def use_demo() -> bool:
    """Decide whether the tool runs on demo data.

    Returns
    -------
    bool
        True when ``SCHNEIDER_DEMO=1`` or any processed input file is missing.
    """
    return os.environ.get("SCHNEIDER_DEMO") == "1" or not all(p.exists() for p in REAL_FILES)


def load_inputs(demo: bool) -> Inputs:
    """Read the processed inputs, or build demo ones.

    Parameters
    ----------
    demo : bool
        Build demo data instead of reading ``data/processed/``.

    Returns
    -------
    Inputs
        Prices, series catalog, clean BOM and RMU price benchmark.
    """
    if demo:
        return demo_inputs()
    prices, catalog, _ = load_data()
    return Inputs(prices, catalog, pd.read_csv(BOM_CLEAN), pd.read_csv(RMU_PRICES), demo=False)


DEMO_LEVELS = {  # € per t (S11 is an index): start levels for the demo random walks
    "L01": 600.0,
    "MEPS_FR_CR": 620.0,
    "L02": 2000.0,
    "L03": 620.0,
    "D01": 6000.0,
    "D02": 1800.0,
    "S11": 100.0,
}
DEMO_BOM = [  # product_ref, plant, label, family, kg, series: made-up masses
    ("RMAirSeT IIQ 24kV IEC", "HU", "Steel sheet", "Carbon steel", 300.0, "L01"),
    ("RMAirSeT IIQ 24kV IEC", "HU", "Stainless sheet", "Stainless steel", 70.0, "L02"),
    ("RMAirSeT IIQ 24kV IEC", "HU", "Copper bars", "Copper", 30.0, "D01"),
    ("RMAirSeT IIQ 24kV IEC", "HU", "Aluminium parts", "Aluminium", 20.0, "D02"),
    ("RMAirSeT IIQ 24kV IEC", "HU", "Plastic parts", "Plastic", 60.0, "S11"),
    ("RM6_NE_IQI_433520", "FR", "Steel sheet", "Carbon steel", 280.0, "L01"),
    ("RM6_NE_IQI_433520", "FR", "Galvanised sheet", "Galvanised steel", 90.0, "L03"),
    ("RM6_NE_IQI_433520", "FR", "Stainless sheet", "Stainless steel", 40.0, "L02"),
    ("RM6_NE_IQI_433520", "FR", "Copper bars", "Copper", 25.0, "D01"),
    ("RM6_NE_IQI_433520", "FR", "Aluminium parts", "Aluminium", 15.0, "D02"),
    ("RM6_NE_IQI_433520", "FR", "Plastic parts", "Plastic", 50.0, "S11"),
]
DEMO_PRICE = 12_000.0
DEMO_NAMES = {
    "L01": "Carbon steel",
    "MEPS_FR_CR": "Carbon steel, France",
    "L02": "Stainless steel",
    "L03": "Galvanised steel",
    "D01": "Copper",
    "D02": "Aluminium",
    "S11": "Plastics",
}


def demo_prices(seed: int = SEED) -> pd.DataFrame:
    """Generate monthly demo prices with a 2021 surge, in the ``prices_wide`` layout.

    Parameters
    ----------
    seed : int, default=SEED
        Random seed.

    Returns
    -------
    pandas.DataFrame of shape (n_months, n_series)
        One column per demo series, monthly from 2012 to the origin.
    """
    months = pd.date_range("2012-01-01", ORIGIN, freq="MS", name="month")
    rng = np.random.default_rng(seed)
    surge = np.where((months >= "2021-01-01") & (months < "2022-07-01"), 0.025, 0.0)
    fall = np.where((months >= "2022-07-01") & (months < "2023-07-01"), -0.015, 0.0)
    common = rng.normal(0, 0.02, len(months))
    data = {}
    for series, level in DEMO_LEVELS.items():
        steps = surge + fall + common + rng.normal(0, 0.025, len(months))
        steps[0] = 0.0
        data[series] = level * np.exp(np.cumsum(steps))
    return pd.DataFrame(data, index=months)


def demo_inputs() -> Inputs:
    """Build demo inputs with the same columns as the processed files.

    Returns
    -------
    Inputs
        Demo prices, catalog (no gaps, team publication lags), BOM and RMU price.
    """
    prices = demo_prices()
    catalog = pd.DataFrame(
        {
            "gap_months": 0,
            "pub_lag": [PUB_LAG.get(s, 1) for s in prices.columns],
            "material": [DEMO_NAMES[s] for s in prices.columns],
            "region": "EU",
            "unit": ["Index 2021=100" if s == "S11" else "EUR/t" for s in prices.columns],
        },
        index=pd.Index(prices.columns, name="series_id"),
    )
    columns = ["product_ref", "plant_country", "material_label_source", "material_family"]
    bom = pd.DataFrame(DEMO_BOM, columns=[*columns, "mass_kg", "price_series"])
    bom["share_pct"] = bom["mass_kg"] / bom.groupby("product_ref")["mass_kg"].transform("sum")
    rmu = pd.DataFrame({"brand_id": ["SE"], "year": [P.SELLING_PRICE_YEAR], "p50": [DEMO_PRICE]})
    return Inputs(prices, catalog, bom, rmu, demo=True)


# ---- the cost scenarios (the slow part, cached by the app) ----


def team_forecasts(inputs: Inputs, series_list: list[str]) -> tuple[pd.DataFrame, list[str]]:
    """Load the material forecasts, or the team baseline on demo data.

    Parameters
    ----------
    inputs : Inputs
        Output of ``load_inputs``.
    series_list : list of str
        Series the cost index needs.

    Returns
    -------
    forecasts : pandas.DataFrame
        One row per series and horizon with P10 / P50 / P90 and ``model_name``.
    notes : list of str
        Warnings raised while loading (e.g. a series that got a placeholder).
    """
    if inputs.demo:
        return P.placeholder_forecasts(inputs.prices, series_list), []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        forecasts = P.load_forecasts(inputs.prices, series_list)
    notes = [str(w.message) for w in caught if "no team forecast" not in str(w.message)]
    placeholders = forecasts.loc[forecasts["model_name"] == "placeholder_rw_vol", "target_id"]
    if not placeholders.empty:
        names = ", ".join(sorted(set(placeholders)))
        notes.append(f"Placeholder forecast for {names}; no team forecast available.")
    return forecasts, notes


def build_model(inputs: Inputs, n_draws: int = P.N_DRAWS) -> Model:
    """Run the cost scenarios once: weights, forecasts and joint index draws.

    Parameters
    ----------
    inputs : Inputs
        Output of ``load_inputs``.
    n_draws : int, default=pricing.N_DRAWS
        Joint draws per horizon.

    Returns
    -------
    Model
        Cost lines, forecasts used, draws and P10 / P50 / P90 index per product and horizon.
    """
    lines = P.cost_weights(inputs.bom, inputs.prices)
    series_list = sorted(set(lines["series"]) - {P.FLAT})
    forecasts, notes = team_forecasts(inputs, series_list)
    draws = {h: P.simulate_index(lines, forecasts, inputs.prices, h, n_draws) for h in HORIZONS}
    return Model(lines, forecasts, draws, P.index_scenarios(draws), notes)


# ---- one quote (fast, recomputed on every change) ----


def material_names(lines: pd.DataFrame) -> dict[str, str]:
    """Name each price series by the material it prices.

    Parameters
    ----------
    lines : pandas.DataFrame
        Output of ``pricing.cost_weights``.

    Returns
    -------
    dict of str to str
        Series → material family (plastic families grouped as "Plastics").
    """
    names = lines.groupby("series")["material_family"].first().to_dict()
    return {s: "Plastics" if "plastic" in n.lower() else n for s, n in names.items()}


def default_price(inputs: Inputs) -> float:
    """Return the list price the tool starts with.

    Parameters
    ----------
    inputs : Inputs
        Output of ``load_inputs``.

    Returns
    -------
    float
        Schneider's P50 unit price for the selling year (€).
    """
    return P.selling_price(inputs.rmu)


def quote(
    model: Model,
    product: str,
    horizon: int,
    price: float,
    margin: float,
    scenario: str,
    tolerance: float = P.TOLERANCE,
) -> dict:
    """Price one quote from the cost scenarios.

    Parameters
    ----------
    model : Model
        Output of ``build_model``.
    product : str
        ``"RM6"`` or ``"AirSeT"``.
    horizon : int
        Quote validity in months (3, 6 or 9): when the material is bought.
    price : float
        List price per unit (€).
    margin : float
        Target margin as a share of price.
    scenario : str
        A key of ``SCENARIOS``.
    tolerance : float, default=pricing.TOLERANCE
        Share of the margin a quote may lose before it must be revised.

    Returns
    -------
    dict
        Recommended ``quote`` (€) and ``price_adjustment``, ``safety_buffer``,
        ``margin_at_risk`` (€ per unit), ``margin_at_risk_share`` (of the margin),
        ``safe_validity_months``, ``trigger_material`` and ``trigger_move`` (fraction).
    """
    bridge = P.cost_bridge(model.scenarios, model.lines, price, margin)
    rules = P.quote_rules(bridge, margin, tolerance)
    pick = (rules["product"] == product) & (rules["horizon_m"] == horizon)
    rule, cost = rules[pick].iloc[0], bridge[pick].iloc[0]
    q = SCENARIOS[scenario]
    triggers = P.index_triggers(model.lines, price, margin, tolerance)
    first = triggers[triggers["product"] == product].sort_values("trigger_move").iloc[0]
    return {
        "product": product,
        "validity_months": horizon,
        "list_price": price,
        "margin": margin,
        "scenario": scenario,
        "quote": rule[f"quote_{q}"],
        "price_adjustment": rule["price_adjustment"] * price,
        "safety_buffer": rule[f"quote_{q}"] - rule["quote_p50"],
        "margin_at_risk": cost["margin_at_risk_eur"],
        "margin_at_risk_share": cost["margin_at_risk_share_of_margin"],
        "safe_validity_months": int(P.quote_validity(rules)[product]),
        "trigger_material": material_names(model.lines)[first["series"]],
        "trigger_move": first["trigger_move"],
        "material_cost_now": cost["cost_now"],
        "material_cost_scenario": cost[f"cost_{q}"],
        "exposed_share": cost["exposed_share"],
    }


SUMMARY_ROWS = [  # key, item (unit in the name), kind: "eur", "pct" or "" (as is)
    ("product", "Product", ""),
    ("validity_months", "Quote validity (months)", ""),
    ("scenario", "Scenario", ""),
    ("list_price", "List price (€)", "eur"),
    ("margin", "Target margin (%)", "pct"),
    ("quote", "Quote price (€)", "eur"),
    ("price_adjustment", "Price adjustment (€)", "eur"),
    ("safety_buffer", "Buffer (€)", "eur"),
    ("margin_at_risk", "Margin at risk (€)", "eur"),
    ("margin_at_risk_share", "Margin at risk (% of margin)", "pct"),
    ("safe_validity_months", "Safe validity (months)", ""),
    ("trigger_material", "Reprice trigger material", ""),
    ("trigger_move", "Reprice trigger (± %)", "pct"),
    ("material_cost_now", f"Material cost, {pd.Period(ORIGIN, 'M'):%b %Y} (€)", "eur"),
    ("material_cost_scenario", "Material cost at purchase (€)", "eur"),
]


def quote_summary(numbers: dict, demo: bool) -> pd.DataFrame:
    """Lay out a quote as a table to export.

    Parameters
    ----------
    numbers : dict
        Output of ``quote``.
    demo : bool
        Whether the numbers come from demo data.

    Returns
    -------
    pandas.DataFrame
        ``item`` (unit in the name) and ``value``; euros rounded to the euro, percentages to
        0.1.
    """
    rows = []
    for key, item, kind in SUMMARY_ROWS:
        value = numbers[key]
        if kind == "eur":
            value = round(float(value))
        elif kind == "pct":
            value = round(float(value) * 100, 1)
        rows.append((item, value))
    rows.append(("Forecast origin", f"{pd.Period(ORIGIN, 'M'):%b %Y}"))
    rows.append(("Data", "Demo" if demo else "Team forecasts"))
    return pd.DataFrame(rows, columns=["item", "value"])


def what_if(
    model: Model, product: str, price: float, margin: float, copper: float, steel: float
) -> dict:
    """Price a quote after copper and steel move by a given share, all else flat.

    Parameters
    ----------
    model : Model
        Output of ``build_model``.
    product : str
        ``"RM6"`` or ``"AirSeT"``.
    price : float
        List price per unit (€).
    margin : float
        Target margin as a share of price.
    copper, steel : float
        Price moves as fractions (0.2 = +20 %).

    Returns
    -------
    dict
        ``index`` (100 = today), ``cost_change`` (€ per unit), ``price_needed`` (€ to keep
        the margin) and ``margin_lost`` (share of the margin at list price).
    """
    names = model.lines.groupby("series")["material_family"].first()
    ratios = {}
    for series, family in names.drop(P.FLAT, errors="ignore").items():
        move = 0.0
        if any(word in family for word in WHAT_IF_FAMILIES["copper"]):
            move = copper
        elif any(word in family.lower() for word in WHAT_IF_FAMILIES["steel"]):
            move = steel
        ratios[series] = 1 + move
    index = P.index_from_ratios(model.lines, pd.DataFrame([ratios]))[product].iloc[0]
    flat = pd.DataFrame({"product": [product], "horizon_m": [0]}).assign(
        p10=index, p50=index, p90=index
    )
    bridge = P.cost_bridge(flat, model.lines, price, margin)
    rules = P.quote_rules(bridge, margin)
    return {
        "index": index,
        "cost_change": bridge["cost_p50"].iloc[0] - bridge["cost_now"].iloc[0],
        "price_needed": rules["quote_p50"].iloc[0],
        "margin_lost": bridge["margin_at_risk_share_of_margin"].iloc[0],
    }


# ---- the 2021 replay ----


def load_replay(inputs: Inputs) -> pd.DataFrame:
    """Read the 2021 replay, or run it on demo data.

    Parameters
    ----------
    inputs : Inputs
        Output of ``load_inputs``.

    Returns
    -------
    pandas.DataFrame
        ``pricing.replay_quotes`` output: one row per product and quote month.
    """
    if not inputs.demo and REPLAY_FILE.exists():
        return pd.read_csv(REPLAY_FILE, parse_dates=["quote_month", "target_month"])
    lines = P.cost_weights(inputs.bom, inputs.prices)
    exposed = lines.groupby("product")["cost"].sum() / default_price(inputs)
    draws = DEMO_REPLAY_DRAWS if inputs.demo else P.REPLAY_DRAWS
    return P.replay_quotes(inputs.bom, inputs.prices, inputs.catalog, exposed, n_draws=draws)


def replay_view(replay: pd.DataFrame, product: str, month: pd.Timestamp) -> dict:
    """Compare three pricing policies for one past quote.

    Parameters
    ----------
    replay : pandas.DataFrame
        Output of ``load_replay``.
    product : str
        ``"RM6"`` or ``"AirSeT"``.
    month : pandas.Timestamp
        Quote month.

    Returns
    -------
    dict
        ``target_month``, the forecast ``p50`` / ``p90`` and ``actual`` cost moves (fractions)
        and margin lost (share of the margin; below 0 = priced above need) under ``fixed``
        price, ``buffer`` (adjustment + safety buffer) and ``indexation`` (price follows the
        index, so the customer carries the move).
    """
    row = replay[(replay["product"] == product) & (replay["quote_month"] == month)].iloc[0]
    return {
        "target_month": row["target_month"],
        "p50": row["p50"] / 100 - 1,
        "p90": row["p90"] / 100 - 1,
        "actual": row["actual_index"] / 100 - 1,
        "fixed": row["margin_lost_fixed_price"],
        "buffer": row["margin_lost_band_buffer"],
        "indexation": 0.0,
    }


# ---- cost outlook ----

INDEX_SCORES_FILE = DATA_PROCESSED / "index_backtest_scores.csv"


def index_fan(model: Model, product: str) -> pd.DataFrame:
    """Lay out a product's cost index from today to +9 months.

    Parameters
    ----------
    model : Model
        Output of ``build_model``.
    product : str
        ``"RM6"`` or ``"AirSeT"``.

    Returns
    -------
    pandas.DataFrame
        ``horizon_m`` (0 = today), index ``p10`` / ``p50`` / ``p90`` (100 = today) and the
        same in € per unit (``cost_p10`` …).
    """
    rows = model.scenarios[model.scenarios["product"] == product]
    today = pd.DataFrame({"product": [product], "horizon_m": [0], "p10": 100.0})
    table = pd.concat([today.assign(p50=100.0, p90=100.0), rows], ignore_index=True)
    cost_now = model.lines.groupby("product")["cost"].sum()[product]
    for q in ("p10", "p50", "p90"):
        table[f"cost_{q}"] = cost_now * table[q] / 100
    return table


def material_risk(inputs: Inputs, model: Model, product: str, horizon: int) -> pd.DataFrame:
    """Measure the € each material adds per unit if it alone reaches its P90.

    Parameters
    ----------
    inputs : Inputs
        Output of ``load_inputs``.
    model : Model
        Output of ``build_model``.
    product : str
        ``"RM6"`` or ``"AirSeT"``.
    horizon : int
        Months ahead.

    Returns
    -------
    pandas.DataFrame
        One row per material: ``material``, ``cost`` (€ per unit today), ``weight`` (share of
        material cost), ``p90_move`` (fraction) and ``eur_at_risk`` (€ per unit), largest first.
    """
    lines = model.lines[model.lines["product"] == product]
    forecasts = model.forecasts[model.forecasts["horizon_m"] == horizon].set_index("target_id")
    names = material_names(model.lines)
    cost_now = lines["cost"].sum()
    series_list = sorted(set(lines["series"]) - {P.FLAT})
    rows = []
    for series in series_list:
        move = forecasts.loc[series, "p90"] / P.last_value(inputs.prices, series) - 1
        ratios = pd.DataFrame([{s: 1 + move if s == series else 1.0 for s in series_list}])
        index = P.index_from_ratios(lines, ratios)[product].iloc[0]
        share = lines.loc[lines["series"] == series, ["cost", "weight"]].sum()
        rows.append(
            {
                "material": names[series],
                "cost": share["cost"],
                "weight": share["weight"],
                "p90_move": move,
                "eur_at_risk": cost_now * (index / 100 - 1),
            }
        )
    return pd.DataFrame(rows).sort_values("eur_at_risk", ascending=False, ignore_index=True)


def index_skill(product: str, demo: bool) -> pd.DataFrame:
    """Read how our cost index scored against a naive index (no change) since 2020.

    Parameters
    ----------
    product : str
        ``"RM6"`` or ``"AirSeT"``.
    demo : bool
        Demo data has no backtest.

    Returns
    -------
    pandas.DataFrame
        ``horizon``, ``skill`` (1 − our error ÷ naive error, all months) and ``coverage``
        (share of outcomes inside P10–P90); empty when there is no backtest.
    """
    if demo or not INDEX_SCORES_FILE.exists():
        return pd.DataFrame(columns=["horizon", "skill", "coverage"])
    scores = pd.read_csv(INDEX_SCORES_FILE)
    pick = (
        (scores["model"] == P.INDEX_MODEL)
        & (scores["target"] == product)
        & (scores["period"] == "all")
    )
    table = scores[pick].rename(columns={"skill_rw": "skill"})
    return table[["horizon", "skill", "coverage"]].reset_index(drop=True)


# ---- materials ----


def material_list(inputs: Inputs) -> list[str]:
    """List the materials the tool can show.

    Parameters
    ----------
    inputs : Inputs
        Output of ``load_inputs``.

    Returns
    -------
    list of str
        The 19 forecast targets on real data; the demo series on demo data.
    """
    if inputs.demo:
        return [s for s in inputs.prices.columns if s != "MEPS_FR_CR"]
    return [s for s in EXPECTED_TARGETS if s in inputs.prices.columns]


def reader_unit(unit: str) -> str:
    """Write a catalog unit for the reader.

    Parameters
    ----------
    unit : str
        Catalog unit, e.g. ``"EUR/t"``, ``"USD per EUR"``, ``"Index 2021=100"``.

    Returns
    -------
    str
        ``"€ per t"``, ``"$ per €"``, ``"index, 2021 = 100"`` and so on.
    """
    if unit.lower().startswith("index"):
        return "index, " + unit[6:].replace("=", " = ")
    unit = unit.replace("EUR", "€").replace("USD", "$")
    return unit.replace("/", " per ")


MODEL_NAMES = {
    "random_walk": "Random walk",
    "placeholder_rw_vol": "Random walk (baseline)",
    "chronos2": "Chronos-2",
    "blend_ets_chronos2": "ETS + Chronos-2 blend",
    "blend_ets_chronos2_volband": "ETS + Chronos-2 blend (volatility bands)",
    "meps_pooled": "MEPS pooled",
    "meps_pooled_3m_held": "MEPS pooled (3-month P50 held)",
    "steel_ppi_lead": "Steel PPI lead",
    "steel_ppi_lead_6m_held": "Steel PPI lead (6-month P50 held)",
}


def model_label(model_name: str) -> str:
    """Name a forecast model for the reader.

    Parameters
    ----------
    model_name : str
        Model id from the forecast files.

    Returns
    -------
    str
        Readable name; an unknown id is shown with spaces instead of underscores.
    """
    return MODEL_NAMES.get(model_name, model_name.replace("_", " "))


def material_info(inputs: Inputs, series: str) -> dict:
    """Describe a series in words.

    Parameters
    ----------
    inputs : Inputs
        Output of ``load_inputs``.
    series : str
        Series id.

    Returns
    -------
    dict
        ``name``, ``region``, ``unit`` (written by ``reader_unit``) and ``last_month``.
    """
    row = inputs.catalog.loc[series]
    last = inputs.prices[series].dropna().index[-1]
    return {
        "name": str(row.get("material", series)),
        "region": str(row.get("region", "")),
        "unit": reader_unit(str(row.get("unit", ""))),
        "last_month": last,
    }


def material_forecast(inputs: Inputs, series: str) -> tuple[pd.DataFrame, bool]:
    """Read the team's Sep 2026 forecast for one material.

    Parameters
    ----------
    inputs : Inputs
        Output of ``load_inputs``.
    series : str
        Series id.

    Returns
    -------
    forecast : pandas.DataFrame
        ``horizon_m``, ``target_month``, ``p10``, ``p50``, ``p90``, ``model_name``.
    placeholder : bool
        True when no team forecast exists and the team baseline is shown instead.
    """
    found = pd.DataFrame()
    if not inputs.demo:
        files = [pd.read_csv(f) for f in P.TEAM_FORECAST_FILES if f.exists()]
        if files:
            found = P.to_pricing_columns(pd.concat(files, ignore_index=True))
            found = found[found["target_id"] == series]
    placeholder = found.empty
    if placeholder:
        found = P.placeholder_forecasts(inputs.prices, [series])
    found = found.sort_values("horizon_m").reset_index(drop=True)
    origin = pd.Period(ORIGIN, "M")
    found["target_month"] = [(origin + h).to_timestamp() for h in found["horizon_m"]]
    return found[["horizon_m", "target_month", "p10", "p50", "p90", "model_name"]], placeholder


def material_skill(series: str, demo: bool) -> pd.DataFrame:
    """Score the team's chosen model for one material against the random walk since 2020.

    Parameters
    ----------
    series : str
        Series id.
    demo : bool
        Demo data has no backtest.

    Returns
    -------
    pandas.DataFrame
        ``horizon``, ``skill`` (1 − our error ÷ random walk error, all months),
        ``coverage`` (share inside P10–P90) and ``n`` (forecasts scored); empty when there
        is no backtest for the series.
    """
    empty = pd.DataFrame(columns=["horizon", "skill", "coverage", "n"])
    if demo:
        return empty
    files = [f for f in P.TEAM_BACKTEST_FILES if f.exists()]
    rows = [pd.read_csv(f, parse_dates=["origin", "target_month"]) for f in files]
    rows = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["target"])
    rows = rows[rows["target"] == series]
    if rows.empty:
        return empty
    table = score(rows).reset_index()
    table = table[table["period"] == "all"].rename(columns={"skill_rw": "skill"})
    return table[["horizon", "skill", "coverage", "n"]].reset_index(drop=True)


# ---- SF6-free ----


def sf6_gap(model: Model) -> pd.DataFrame:
    """Measure the AirSeT minus RM6 material cost per unit, today and at each horizon.

    Parameters
    ----------
    model : Model
        Output of ``build_model``.

    Returns
    -------
    pandas.DataFrame
        ``horizon_m`` (0 = today) and the gap's ``p10``, ``p50``, ``p90`` (€ per unit).
    """
    gap = P.cost_gap(model.draws, model.lines)
    now = gap["gap_now"].iloc[0]
    today = pd.DataFrame({"horizon_m": [0], "p10": [now], "p50": [now], "p90": [now]})
    return pd.concat([today, gap[["horizon_m", "p10", "p50", "p90"]]], ignore_index=True)
