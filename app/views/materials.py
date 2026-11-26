"""Materials page: one series' history, the team forecast and how well its model scored."""

import pandas as pd
import streamlit as st
import ui

from schneider_forecast import decision as D
from schneider_forecast.config import ORIGIN

inputs, model = ui.data()
origin = pd.Period(ORIGIN, "M")
series_list = D.material_list(inputs)

ui.title(
    "Materials.",
    f"Price history and the team forecast for each of the {len(series_list)} series.",
    inputs.demo,
)

a, b = st.columns([2, 3])
names = {s: D.material_info(inputs, s)["name"] for s in series_list}
series = a.selectbox(
    "Material",
    series_list,
    index=series_list.index("D01") if "D01" in series_list else 0,
    format_func=lambda s: f"{names[s]} · {s}",
)
info = D.material_info(inputs, series)
forecast, placeholder = D.material_forecast(inputs, series)
last_value = inputs.prices[series].dropna().iloc[-1]

end = forecast.iloc[-1]
value, unit = ui.amount(end["p50"], info["unit"])
p10, _ = ui.amount(end["p10"], info["unit"])
p90, _ = ui.amount(end["p90"], info["unit"])
now, _ = ui.amount(last_value, info["unit"])
ui.field(
    f"{info['name']} price, {end['target_month']:%b %Y}",
    value,
    f"P50 in {info['unit']} · range {p10} to {p90} (P10 to P90) · {now} in "
    f"{info['last_month']:%b %Y}",
)
if placeholder:
    ui.note("Random walk shown", "· no team forecast for this series.")

cells = []
for _, r in forecast.iterrows():
    v, u = ui.amount(r["p50"], info["unit"])
    lo, _ = ui.amount(r["p10"], info["unit"])
    hi, _ = ui.amount(r["p90"], info["unit"])
    move = r["p50"] / last_value - 1
    cells.append(
        (
            f"P50, {r['target_month']:%b %Y}",
            v,
            f"{ui.pct(move, sign=True)} on {info['last_month']:%b %Y}",
            f"Range {lo} to {hi} · {D.model_label(r['model_name'])}",
        )
    )
ui.stats(cells)

history = inputs.prices[series].dropna().loc["2016-01-01":].rename("value").reset_index()
history = history.rename(columns={history.columns[0]: "month"})
start = pd.DataFrame(
    {"month": [info["last_month"]], "p10": last_value, "p50": last_value, "p90": last_value}
)
band = pd.concat(
    [
        start,
        forecast[["target_month", "p10", "p50", "p90"]].rename(columns={"target_month": "month"}),
    ],
    ignore_index=True,
)
st.write("")
ui.fan(
    band,
    f"{info['name']} ({info['unit']})",
    ",.3f" if info["unit"] == "$ per €" else ",.0f",
    history=history,
)
ui.caption(
    "Black line: history since 2016. Grey band: range (P10 to P90). Green line: P50. "
    f"Region: {info['region']}."
)

# ---- track record ----
ui.heading("Track record.", "Chosen model against the naive forecast, every month since 2020.")
skill = D.material_skill(series, inputs.demo)
if skill.empty:
    ui.note("No track record yet", "· team backtest files are not in `outputs/backtest/`.")
else:
    ui.stats(
        [
            (
                f"Skill, {int(r['horizon'])} months",
                ui.pct(r["skill"], sign=True),
                "",
                f"{ui.pct(r['coverage'], digits=0)} coverage; target 80 %. "
                f"{int(r['n'])} forecasts.",
            )
            for _, r in skill.iterrows()
        ]
    )
    ui.caption(
        "Skill: 1 − forecast error ÷ naive forecast error. "
        "Zero: the naive forecast is the chosen model."
    )
