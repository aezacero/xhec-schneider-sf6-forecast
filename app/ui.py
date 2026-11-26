"""Shared look, data loading and formatting for the decision tool pages."""

from html import escape
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from schneider_forecast import decision as D

STYLE = Path(__file__).with_name("style.css")
GREY = "#b5b5b5"
INK = "#000000"
MUTED = "#6b6b6b"
HAIRLINE = "#e6e6e6"
ACCENT = "#3f6b4f"  # field-forest: the one chart accent


def style() -> None:
    """Load the Canvas stylesheet."""
    st.html(f"<style>{STYLE.read_text()}</style>")


@st.cache_resource(show_spinner="Loading cost scenarios")
def load(demo: bool) -> tuple[D.Inputs, D.Model]:
    """Load the inputs and run the cost scenarios once per data source."""
    inputs = D.load_inputs(demo)
    return inputs, D.build_model(inputs)


@st.cache_resource(show_spinner="Loading 2021 replay")
def replay(demo: bool):
    """Load (or, on demo data, run) the 2021 replay once."""
    inputs, _ = load(demo)
    return D.load_replay(inputs)


def data() -> tuple[D.Inputs, D.Model]:
    """Return the inputs and model, or stop the page with a plain error."""
    try:
        return load(D.use_demo())
    except (OSError, ValueError, KeyError) as error:
        st.error(
            "Pricing inputs not found. Run `uv run python -m schneider_forecast.pricing` "
            "or start with `SCHNEIDER_DEMO=1`.\n\n"
            f"Detail: {error}"
        )
        st.stop()


def title(line: str, explainer: str, demo: bool) -> None:
    """Page title: a short black line, a grey explainer and, on demo data, a badge."""
    badge = '<div class="cv-badge">Demo data</div>' if demo else ""
    st.html(
        f'<div class="cv-top"><h1 class="cv-title">{escape(line)} '
        f"<span>{escape(explainer)}</span></h1>{badge}</div>"
    )


def heading(line: str, explainer: str) -> None:
    """Section heading in two tones."""
    st.html(f'<h2 class="cv-heading">{escape(line)} <span>{escape(explainer)}</span></h2>')


def field(label: str, value: str, note: str) -> None:
    """The main result: one big number on the mint field."""
    st.html(
        f'<div class="cv-field"><div class="cv-label">{escape(label)}</div>'
        f'<div class="cv-stat">{escape(value)}</div>'
        f'<div class="cv-note">{escape(note)}</div></div>'
    )


def stats(cells: list[tuple[str, str, str, str]]) -> None:
    """A row of stats: (label, value, unit, one-line hint) per cell."""
    html = "".join(
        f'<div class="cv-cell"><div class="cv-label">{escape(label)}</div>'
        f'<div class="cv-value">{escape(value)}<small>{escape(unit)}</small></div>'
        f'<div class="cv-hint">{escape(hint)}</div></div>'
        for label, value, unit, hint in cells
    )
    st.html(f'<div class="cv-stats" style="--cols:{len(cells)}">{html}</div>')


def note(text: str, muted: str = "") -> None:
    """A one-line note between hairlines."""
    st.html(f'<div class="cv-note-line">{escape(text)} <span>{escape(muted)}</span></div>')


def caption(text: str) -> None:
    """Small grey text."""
    st.html(f'<div class="cv-caption">{escape(text)}</div>')


def eur(value: float, sign: bool = False) -> str:
    """Format euros: €12,381 or, with ``sign``, +€148 / −€12."""
    text = f"€{abs(value):,.0f}"
    if sign:
        return ("−" if value < -0.5 else "+") + text
    return text


def pct(value: float, sign: bool = False, digits: int = 1) -> str:
    """Format a fraction as a percentage: 0.062 → 6.2 %."""
    text = f"{abs(value) * 100:.{digits}f} %"
    if sign and float(text[:-2]) == 0:
        return text
    if sign:
        return ("−" if value < 0 else "+") + text
    return text


def chart_theme(chart: alt.Chart) -> alt.Chart:
    """Greyscale chart styling: hairline grid, grey labels, no frame."""
    return (
        chart.configure_view(strokeWidth=0)
        .configure_axis(
            gridColor=HAIRLINE,
            domainColor=HAIRLINE,
            tickColor=HAIRLINE,
            labelColor=MUTED,
            titleColor=MUTED,
            labelFont="Inter, Helvetica Neue, Arial",
            titleFont="Inter, Helvetica Neue, Arial",
            titleFontWeight=400,
            labelFontSize=12,
            titleFontSize=12,
        )
        .configure_legend(
            labelColor=MUTED, labelFont="Inter, Helvetica Neue, Arial", orient="top", title=None
        )
    )


def amount(value: float, unit: str) -> tuple[str, str]:
    """Format a value in its series' unit: (number, unit suffix)."""
    if unit == "$ per €":
        return f"{value:,.3f}", unit
    for symbol in ("€", "$"):
        if unit.startswith(f"{symbol} per "):
            return f"{symbol}{value:,.0f}", unit[2:]
    return f"{value:,.1f}", unit


def fan(
    band: pd.DataFrame,
    y_title: str,
    y_format: str = ",.0f",
    history: pd.DataFrame | None = None,
    height: int = 300,
) -> None:
    """Fan chart: grey P10–P90 band, accent P50 line, optional black history line.

    ``band`` and ``history`` have a ``month`` column; ``band`` has ``p10``, ``p50``, ``p90``,
    ``history`` has ``value``.
    """
    ticks = (
        {"interval": "year", "step": 1} if history is not None else {"interval": "month", "step": 3}
    )
    x = alt.X("month:T", title=None, axis=alt.Axis(format="%b %Y", labelAngle=0, tickCount=ticks))
    y_axis = alt.Axis(format=y_format)
    area = (
        alt.Chart(band)
        .mark_area(color=HAIRLINE, opacity=0.9)
        .encode(
            x=x,
            y=alt.Y("p10:Q", title=y_title, axis=y_axis, scale=alt.Scale(zero=False)),
            y2="p90:Q",
            tooltip=[
                alt.Tooltip("month:T", format="%b %Y", title="Month"),
                alt.Tooltip("p10:Q", format=y_format, title="P10"),
                alt.Tooltip("p50:Q", format=y_format, title="P50"),
                alt.Tooltip("p90:Q", format=y_format, title="P90"),
            ],
        )
    )
    edges = alt.Chart(band).encode(x=x)
    layers = [
        area,
        edges.mark_line(color=GREY, strokeWidth=1).encode(y="p10:Q"),
        edges.mark_line(color=GREY, strokeWidth=1).encode(y="p90:Q"),
        edges.mark_line(
            color=ACCENT, strokeWidth=2.5, point=alt.OverlayMarkDef(color=ACCENT, size=36)
        ).encode(y="p50:Q"),
    ]
    if history is not None:
        line = alt.Chart(history).mark_line(color=INK, strokeWidth=1.5)
        tip = [
            alt.Tooltip("month:T", format="%b %Y", title="Month"),
            alt.Tooltip("value:Q", format=y_format, title="Price"),
        ]
        layers.insert(0, line.encode(x=x, y=alt.Y("value:Q", axis=y_axis), tooltip=tip))
    chart = alt.layer(*layers).properties(height=height)
    st.altair_chart(chart_theme(chart), use_container_width=True)


def bars(
    table: pd.DataFrame,
    label: str,
    value: str,
    x_title: str,
    x_format: str,
    tooltip: tuple[str, str] = ("Material", "€ per unit"),
) -> None:
    """Horizontal bars, largest first: the top bar in the accent, the rest grey."""
    order = list(table[label])
    colour = alt.condition(alt.datum[label] == order[0], alt.value(ACCENT), alt.value(GREY))
    base = alt.Chart(table).encode(
        y=alt.Y(f"{label}:N", sort=order, title=None),
        x=alt.X(f"{value}:Q", title=x_title, axis=alt.Axis(format=x_format)),
    )
    text = alt.Text(f"{value}:Q", format=x_format)
    right = base.transform_filter(f"datum.{value} >= 0").mark_text(
        align="left", dx=6, color=MUTED, fontSize=12
    )
    left = base.transform_filter(f"datum.{value} < 0").mark_text(
        align="right", dx=-6, color=MUTED, fontSize=12
    )
    chart = (
        base.mark_bar(height=18, cornerRadiusEnd=3).encode(
            color=colour,
            tooltip=[
                alt.Tooltip(f"{label}:N", title=tooltip[0]),
                alt.Tooltip(f"{value}:Q", format=x_format, title=tooltip[1]),
            ],
        )
        + right.encode(text=text)
        + left.encode(text=text)
    )
    st.altair_chart(chart_theme(chart.properties(height=36 * len(table))), use_container_width=True)
