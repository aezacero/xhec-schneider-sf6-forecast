"""SF6-free page: the extra material cost of AirSeT over RM6 and its range."""

import pandas as pd
import ui

from schneider_forecast import decision as D
from schneider_forecast.config import HORIZONS, ORIGIN

inputs, model = ui.data()
origin = pd.Period(ORIGIN, "M")
last = origin + max(HORIZONS)

ui.title(
    "SF6-free.",
    "Extra material cost of AirSeT, the SF6-free unit, over RM6.",
    inputs.demo,
)

gap = D.sf6_gap(model)
gap["month"] = [(origin + h).to_timestamp() for h in gap["horizon_m"]]
now = gap["p50"].iloc[0]
end = gap.iloc[-1]
cost = model.lines.groupby("product")["cost"].sum()
price = D.default_price(inputs)

ui.field(
    "Cost gap",
    ui.eur(now),
    f"AirSeT carries {ui.eur(now)} more material cost than RM6 · P50 {ui.eur(end['p50'])} by "
    f"{last:%b %Y}, range {ui.eur(end['p10'])} to {ui.eur(end['p90'])} (P10 to P90)",
)
ui.stats(
    [
        ("AirSeT material cost", ui.eur(cost["AirSeT"]), "per unit", f"{origin:%b %Y} prices."),
        ("RM6 material cost", ui.eur(cost["RM6"]), "per unit", f"{origin:%b %Y} prices."),
        (
            "Cost gap vs list price",
            ui.pct(now / price),
            "",
            f"At the {ui.eur(price)} benchmark price.",
        ),
        (
            f"Cost gap at P90, {last:%b %Y}",
            ui.eur(end["p90"]),
            "per unit",
            f"{ui.pct(end['p90'] / price)} of list price; worse only 1 time in 10.",
        ),
    ]
)
ui.fan(gap, "Cost gap (€ per unit)", ",.0f", height=280)
ui.caption("Material cost only; excludes SF6 gas, handling, end-of-life and carbon costs.")

ui.heading("Cost gap by material.", f"Where the gap comes from, at {origin:%b %Y} prices.")
by_material = model.lines.assign(material=model.lines["series"].map(D.material_names(model.lines)))
split = by_material.pivot_table(index="material", columns="product", values="cost", aggfunc="sum")
split = split.fillna(0.0)
split["gap"] = split["AirSeT"] - split["RM6"]
split = split.sort_values("gap", ascending=False).reset_index()
ui.bars(split, "material", "gap", "AirSeT minus RM6 (€ per unit)", ",.0f")
ui.caption("Below zero: RM6 carries more of that material.")
