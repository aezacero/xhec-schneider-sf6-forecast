"""Cost outlook page: material cost per unit to +9 months, and which material drives the risk."""

import pandas as pd
import streamlit as st
import ui

from schneider_forecast import decision as D
from schneider_forecast.config import HORIZONS, ORIGIN

inputs, model = ui.data()
products = sorted(model.lines["product"].unique(), key=lambda p: p != "RM6")
origin = pd.Period(ORIGIN, "M")
last = origin + max(HORIZONS)

ui.title(
    "Cost outlook.",
    f"Material cost per unit to {last:%b %Y} and the range a quote must cover.",
    inputs.demo,
)

a, b, _ = st.columns([2, 3, 2])
product = a.segmented_control("Product", products, default=products[0], key="cost_product")
horizon = b.segmented_control(
    "Horizon", HORIZONS, default=9, format_func=lambda m: f"{m} months", key="cost_horizon"
)
product, horizon = product or products[0], horizon or 9
when = origin + horizon

fan = D.index_fan(model, product)
row = fan[fan["horizon_m"] == horizon].iloc[0]
now = fan["cost_p50"].iloc[0]
ui.field(
    f"Material cost, {when:%b %Y}",
    ui.eur(row["cost_p50"]),
    f"P50 for one {product} unit · range {ui.eur(row['cost_p10'])} to {ui.eur(row['cost_p90'])} "
    f"(P10 to P90) · {ui.eur(now)} in {origin:%b %Y}",
)
price = D.default_price(inputs)
ui.stats(
    [
        (
            f"Material cost, {origin:%b %Y}",
            ui.eur(now),
            "per unit",
            "Priced raw material only.",
        ),
        (
            "Exposed share",
            ui.pct(now / price),
            "of list price",
            "Part of the price that moves with materials.",
        ),
        (
            "Cost index, P90",
            f"{row['p90']:.1f}",
            f"{origin:%b %Y} = 100",
            f"Worse only 1 time in 10 by {when:%b %Y}.",
        ),
        (
            "Cost index, P10",
            f"{row['p10']:.1f}",
            f"{origin:%b %Y} = 100",
            f"Better only 1 time in 10 by {when:%b %Y}.",
        ),
    ]
)

band = fan.assign(month=[(origin + h).to_timestamp() for h in fan["horizon_m"]])
band = band.rename(columns={"p10": "i10", "p50": "i50", "p90": "i90"}).rename(
    columns={"cost_p10": "p10", "cost_p50": "p50", "cost_p90": "p90"}
)
st.write("")
ui.fan(band, "Material cost (€ per unit)", ",.0f")
ui.caption("Grey band: range (P10 to P90). Green line: P50. 10,000 joint scenarios.")

# ---- € at risk by material ----
ui.heading("Material cost at risk.", "€ per unit each material adds if it alone reaches P90.")
risk = D.material_risk(inputs, model, product, horizon)
ui.bars(
    risk, "material", "eur_at_risk", f"Material cost at risk, {when:%b %Y} (€ per unit)", ",.0f"
)
top = risk.iloc[0]
ui.note(
    f"{top['material']}: largest material cost at risk",
    f"· {ui.pct(top['weight'], digits=0)} of material cost, "
    f"{ui.pct(top['p90_move'], sign=True, digits=0)} at P90.",
)

# ---- backtest ----
ui.heading("Track record.", "Cost index against the naive forecast, every month since 2020.")
skill = D.index_skill(product, inputs.demo)
if skill.empty:
    ui.note(
        "No track record yet",
        "· run `uv run python -m schneider_forecast.pricing` on real data.",
    )
else:
    ui.stats(
        [
            (
                f"Skill, {int(r['horizon'])} months",
                ui.pct(r["skill"], sign=True),
                "",
                f"{ui.pct(r['coverage'], digits=0)} coverage; target 80 %.",
            )
            for _, r in skill.iterrows()
        ]
    )
    ui.caption(
        "Skill: 1 − forecast error ÷ naive forecast error. Above zero beats the naive forecast."
    )
