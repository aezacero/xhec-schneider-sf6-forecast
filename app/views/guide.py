"""Guide page: what the tool does and how to read it, for a first-time visitor."""

from html import escape

import pandas as pd
import streamlit as st
import ui

from schneider_forecast import decision as D
from schneider_forecast.config import HORIZONS, ORIGIN

README = "https://github.com/aezacero/xhec-schneider-sf6-forecast#readme"
origin = pd.Period(ORIGIN, "M")
last = origin + max(HORIZONS)

# Examples always come from the demo data, so they match what a first-time visitor sees.
demo_inputs, demo_model = ui.load(True)
price = float(round(D.default_price(demo_inputs)))
example = {s: D.quote(demo_model, "RM6", 6, price, 0.2, s) for s in D.SCENARIOS}
q = example["Downside"]
fan = D.index_fan(demo_model, "RM6")
six = fan[fan["horizon_m"] == 6].iloc[0]


def card(title: str, question: str, controls: str, read: str, page: str, label: str) -> None:
    """One card per page: the question it answers, its controls and how to read it."""
    with st.container(border=True):
        st.html(
            f'<div class="cv-card"><div class="cv-card-title">{escape(title)}</div>'
            f'<div class="cv-card-question">{escape(question)}</div>'
            f'<div class="cv-label">Controls</div><div class="cv-hint">{escape(controls)}</div>'
            f'<div class="cv-label">Read</div><div class="cv-hint">{escape(read)}</div></div>'
        )
        st.page_link(page, label=label, icon=":material/arrow_forward:")


ui.title("Guide.", "How to read this tool in two minutes.", D.use_demo())
ui.note(
    f"This tool prices a ring main unit quote from the team's {origin:%b %Y} material forecasts,",
    "so you can see how much buffer a quote needs and how much margin is at risk.",
)

# ---- start here ----
ui.heading("Start here.", "From opening the tool to a quote price.")
steps = [
    "Open <b>Quote</b> and pick a product: RM6 or AirSeT.",
    "Set the quote validity (3, 6 or 9 months) and the list price. "
    "The default list price is Schneider's 2026 benchmark price.",
    "Pick a scenario. Downside is the safe default.",
    "Read the <b>Quote price</b> on the green panel, then the five numbers below it.",
]
st.html('<ol class="cv-steps">' + "".join(f"<li>{s}</li>" for s in steps) + "</ol>")

# ---- the pages ----
ui.heading("The pages.", "What each one answers.")
cards = [
    (
        "Quote",
        "What price should we put on this quote?",
        "Product, Quote validity, Scenario, List price.",
        "The Quote price: list price + price adjustment + buffer. Below it, Cost shock tests a "
        "copper or steel move, and 2021 replay shows the margin each pricing policy kept.",
        "views/quote.py",
        "Go to Quote",
    ),
    (
        "Cost outlook",
        f"How much could material cost move by {last:%b %Y}?",
        "Product, Horizon.",
        "The material cost per unit at P50 and its range. The bars show which material carries "
        "the most material cost at risk.",
        "views/cost.py",
        "Go to Cost outlook",
    ),
    (
        "Materials",
        "What is our forecast for one raw material, and how good has it been?",
        "Material.",
        "P50 and range at 3, 6 and 9 months against history. Track record shows skill against "
        "the naive forecast and coverage.",
        "views/materials.py",
        "Go to Materials",
    ),
    (
        "SF6-free",
        "How much more material cost does AirSeT carry than RM6?",
        "No controls.",
        f"The cost gap per unit today and its range to {last:%b %Y}, then which materials "
        "drive it.",
        "views/sf6.py",
        "Go to SF6-free",
    ),
]
for row in (cards[:2], cards[2:]):  # two rows, so cards side by side share one height
    for column, content in zip(st.columns(2, gap="medium"), row, strict=True):
        with column:
            card(*content)

# ---- reading the numbers ----
ui.heading(
    "Reading the numbers.",
    f"Example: RM6, 6-month quote, {ui.eur(price)} list price, 20 % margin, demo data.",
)
quotes = " / ".join(ui.eur(example[s]["quote"]) for s in D.SCENARIOS)
terms = [
    (
        "P10 / P50 / P90",
        "Forecast range: 1 time in 10 below P10, half the time below P50, 1 time in 10 above P90.",
        f"Material cost by {origin + 6:%b %Y}: P50 {ui.eur(six['cost_p50'])}, "
        f"range {ui.eur(six['cost_p10'])} to {ui.eur(six['cost_p90'])}.",
    ),
    (
        "Scenario",
        "The cost outcome the quote covers: Downside (P90), Baseline (P50) or Upside (P10).",
        f"Quote price {quotes}.",
    ),
    (
        "Buffer",
        "Extra cover above the expected move, set by the scenario.",
        f"{ui.eur(q['safety_buffer'], sign=True)} at Downside.",
    ),
    (
        "Margin at risk",
        "Margin lost per unit at list price if material costs reach P90.",
        f"{ui.eur(q['margin_at_risk'])}, {ui.pct(q['margin_at_risk_share'], digits=0)} of margin.",
    ),
    (
        "Reprice trigger",
        "The move in one material's price that costs 10 % of the margin. "
        "Past it, reprice or index.",
        f"±{q['trigger_move'] * 100:.0f} % {q['trigger_material'].lower()}.",
    ),
]
st.html(
    '<div class="cv-terms">'
    + "".join(
        f'<div class="cv-term">{escape(t)}</div><div>{escape(m)}</div>'
        f'<div class="cv-hint">{escape(e)}</div>'
        for t, m, e in terms
    )
    + "</div>"
)

# ---- what's behind it ----
ui.heading("What's behind it.", "Data, method and limits.")
behind = [
    ("Data", "19 raw-material price series and Schneider's bill of materials for RM6 and AirSeT."),
    ("Forecast origin", f"Every forecast starts from {origin:%b %Y}, at +3, +6 and +9 months."),
    (
        "Demo vs local data",
        "With the team's local files the tool uses real data. Without them, it runs on generated "
        'demo data and shows a "Demo data" badge. Nothing leaves your machine.',
    ),
    (
        "Limits",
        "Priced raw material is only about 8 % of the unit price. The unit price is a synthetic "
        "benchmark. Ranges are too narrow in price shocks such as 2020–22.",
    ),
]
st.html(
    '<div class="cv-terms cv-terms-two">'
    + "".join(f'<div class="cv-term">{escape(t)}</div><div>{escape(m)}</div>' for t, m in behind)
    + "</div>"
)
st.html(f'<a class="cv-link" href="{README}" target="_blank">More in the README →</a>')
