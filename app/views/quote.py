"""Quote page: price one quote, test a cost shock, replay a 2021 quote."""

import altair as alt
import pandas as pd
import streamlit as st
import ui

from schneider_forecast import decision as D
from schneider_forecast.config import HORIZONS, ORIGIN
from schneider_forecast.pricing import MARGIN, TOLERANCE

inputs, model = ui.data()
products = sorted(model.lines["product"].unique(), key=lambda p: p != "RM6")
origin = pd.Period(ORIGIN, "M")
tolerance = ui.pct(TOLERANCE, digits=0)

ui.title(
    "Quote.", f"Price for a ring main unit, from {origin:%b %Y} material forecasts.", inputs.demo
)

# ---- inputs ----
left, right = st.columns([3, 2], gap="large")
with left:
    a, b = st.columns([2, 3])
    product = a.segmented_control("Product", products, default=products[0], key="product")
    horizon = b.segmented_control(
        "Quote validity", HORIZONS, default=6, format_func=lambda m: f"{m} months", key="horizon"
    )
    scenario = st.segmented_control("Scenario", list(D.SCENARIOS), default="Downside", key="scen")
    product, horizon, scenario = product or products[0], horizon or 6, scenario or "Downside"
    st.caption(D.SCENARIO_HINTS[scenario])
with right:
    price = st.number_input(
        "List price (€)",
        min_value=1_000.0,
        max_value=200_000.0,
        value=float(round(D.default_price(inputs))),
        step=100.0,
        format="%.0f",
        help="Default is Schneider's 2026 benchmark price.",
    )
    margin = st.slider("Target margin (%)", 5, 40, 20, step=1, format="%d %%") / 100

q = D.quote(model, product, horizon, price, margin, scenario)
purchase = origin + horizon

# ---- result ----
buffer_share = q["safety_buffer"] / price
ui.field(
    "Quote price",
    ui.eur(q["quote"]),
    f"Includes a {ui.pct(buffer_share, sign=buffer_share < 0)} buffer for a {horizon}-month "
    f"{product} quote · {ui.pct(q['quote'] / price - 1, sign=True)} on list price",
)
ui.stats(
    [
        (
            "Price adjustment",
            ui.eur(q["price_adjustment"], sign=True),
            "",
            f"Expected cost move by {purchase:%b %Y}.",
        ),
        ("Buffer", ui.eur(q["safety_buffer"], sign=True), "", f"Covers the {scenario} scenario."),
        (
            "Margin at risk",
            ui.eur(q["margin_at_risk"]),
            f"{ui.pct(q['margin_at_risk_share'], digits=0)} of margin",
            "At list price, if costs reach P90.",
        ),
        (
            "Safe validity",
            str(q["safe_validity_months"]),
            "months",
            f"Longer quotes put over {tolerance} of margin at risk.",
        ),
        (
            "Reprice trigger",
            f"±{q['trigger_move'] * 100:.0f} %",
            q["trigger_material"].lower(),
            f"A move this size costs {tolerance} of the margin.",
        ),
    ]
)

if horizon > q["safe_validity_months"]:
    ui.note(
        "Validity above safe limit",
        f"· shorten to {q['safe_validity_months']} months or add indexation.",
    )

st.write("")
summary = D.quote_summary(q, inputs.demo)
col_a, _ = st.columns([1, 3])
col_a.download_button(
    "Export CSV",
    summary.to_csv(index=False).encode(),
    file_name=f"quote_{product}_{horizon}m.csv",
    mime="text/csv",
    type="primary",
)
with st.expander("How it is calculated"):
    st.markdown(
        f"""
- **Material cost**: kg of each material × its {origin:%b %Y} price
  ({ui.eur(q["material_cost_now"])} per unit). **Exposed share** = material cost ÷ list price
  ({ui.pct(q["exposed_share"])}).
- **Price adjustment** = exposed share × expected (P50) cost move by the purchase month.
- **Buffer** = exposed share × (scenario cost move − expected move). Downside uses P90, upside
  P10.
- **Quote price** = list price + price adjustment + buffer.
- **Margin at risk** = exposed share × P90 cost move × list price.
- **Safe validity**: longest validity whose P90 buffer stays under {tolerance} of the margin.
- **Reprice trigger** = {tolerance} × margin ÷ (exposed share × the material's share of cost),
  for the material that triggers first.
- **Cost moves**: 10,000 joint scenarios of the team's P10 / P50 / P90 forecasts, with materials
  moving together as in the past.
"""
    )
for text in model.notes:
    ui.caption(text)

# ---- cost shock ----
ui.heading("Cost shock.", "The price needed to hold margin if copper or steel moves.")
c1, c2 = st.columns(2, gap="large")
copper = c1.slider("Copper move (%)", -50, 50, 0, step=5, format="%+d %%") / 100
steel = c2.slider("Steel move (%)", -50, 50, 0, step=5, format="%+d %%") / 100
w = D.what_if(model, product, price, margin, copper, steel)
ui.stats(
    [
        (
            "Material cost change",
            ui.eur(w["cost_change"], sign=True),
            "",
            f"Other materials held at {origin:%b %Y} prices.",
        ),
        (
            "Quote price to hold margin",
            ui.eur(w["price_needed"]),
            "",
            f"{ui.pct(w['price_needed'] / price - 1, sign=True)} on list price.",
        ),
        (
            "Margin at risk",
            ui.pct(max(w["margin_lost"], 0.0), digits=0),
            "of margin",
            "At list price, after the shock.",
        ),
    ]
)

# ---- 2021 replay ----
ui.heading("2021 replay.", "Margin kept by each pricing policy, buying 6 months after the quote.")
past = ui.replay(inputs.demo)
past = past[past["product"] == product]
months = list(past["quote_month"])
default = pd.Timestamp("2021-03-01")
month = st.select_slider(
    "Quote month",
    options=months,
    value=default if default in months else months[len(months) // 2],
    format_func=lambda m: m.strftime("%b %Y"),
)
r = D.replay_view(past, product, month)


def lost(value: float) -> tuple[str, str]:
    """Value and unit for a margin-lost cell (below 0 = priced above cost need)."""
    if value < -0.005:
        return "0 %", f"lost · {ui.pct(-value, digits=0)} of margin above cost need"
    if value < 0.005:
        return "0 %", "of margin lost"
    return ui.pct(value, digits=0), "of margin lost"


cells = []
for label, key, hint in (
    ("Fixed price", "fixed", "List price held, materials ignored."),
    ("Quote price", "buffer", "Price adjustment plus Downside buffer."),
    ("Indexation", "indexation", "Customer carries the cost move."),
):
    value, unit = lost(r[key])
    cells.append((label, value, unit, hint))
ui.stats(cells)
ui.note(
    f"{ui.pct(r['actual'], sign=True)} material cost, {month:%b %Y} to {r['target_month']:%b %Y}",
    f"· forecast was {ui.pct(r['p50'], sign=True)} (P50), {ui.pct(r['p90'], sign=True)} (P90).",
)

lines = past.melt(
    id_vars="quote_month",
    value_vars=["margin_lost_fixed_price", "margin_lost_band_buffer"],
    var_name="policy",
    value_name="lost",
)
lines["policy"] = lines["policy"].map(
    {"margin_lost_fixed_price": "Fixed price", "margin_lost_band_buffer": "Quote price"}
)
base = alt.Chart(lines).encode(
    x=alt.X("quote_month:T", title="Quote month"),
    y=alt.Y("lost:Q", title="Margin lost (% of margin)", axis=alt.Axis(format="%")),
    color=alt.Color(
        "policy:N",
        scale=alt.Scale(domain=["Fixed price", "Quote price"], range=[ui.GREY, ui.ACCENT]),
    ),
)
zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color=ui.MUTED).encode(y="y:Q")
pick = (
    alt.Chart(pd.DataFrame({"x": [month]}))
    .mark_rule(color=ui.INK, strokeDash=[3, 3])
    .encode(x="x:T")
)
chart = (base.mark_line(strokeWidth=2) + zero + pick).properties(height=260)
st.altair_chart(ui.chart_theme(chart), use_container_width=True)
ui.caption(
    f"Below zero: price ended above cost need. Replay uses a {ui.pct(MARGIN, digits=0)} margin."
)
