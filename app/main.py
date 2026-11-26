"""Decision tool: test a pricing decision with the team's forecasts.

Run from the repo root with ``uv run streamlit run app/main.py``.
"""

from pathlib import Path

import streamlit as st
import ui

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
ui.style()
st.logo(str(Path(__file__).parent / "assets" / "logo.png"), size="large")

pages = [
    st.Page("views/guide.py", title="Guide", default=True),
    st.Page("views/quote.py", title="Quote"),
    st.Page("views/cost.py", title="Cost outlook"),
    st.Page("views/materials.py", title="Materials"),
    st.Page("views/sf6.py", title="SF6-free"),
]
page = st.navigation(pages, position="top")
st.set_page_config(page_title=f"{page.title} · RMU pricing")
page.run()
