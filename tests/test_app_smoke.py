"""The decision tool starts and reacts to input on demo data (no real data needed)."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app" / "main.py"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("SCHNEIDER_DEMO", "1")
    return AppTest.from_file(str(APP), default_timeout=120).run()


def html_of(app) -> str:
    return " ".join(element.proto.body for element in app.get("html"))


def test_guide_is_the_home_page(app):
    assert not app.exception
    html = html_of(app)
    assert "Demo data" in html and "Start here." in html and "Reading the numbers." in html
    links = [link.proto.page for link in app.get("page_link")]
    assert links == ["quote", "cost", "materials", "sf6"]


def test_guide_example_matches_the_quote_page(app):
    guide = html_of(app)
    app.switch_page("views/quote.py").run()
    quote = html_of(app)
    example = guide.split("Quote price ")[1].split(" / ")[0]  # Downside quote on the Guide
    assert example.startswith("€") and f"{example}</div>" in quote


def test_quote_reacts_to_price_and_moves(app):
    app.switch_page("views/quote.py").run()
    app.number_input[0].set_value(20_000.0).run()
    app.slider[1].set_value(30).run()  # copper +30 %
    assert not app.exception
    assert "€20," in html_of(app)


@pytest.mark.parametrize(
    ("page", "text"),
    [
        ("views/quote.py", "Quote price"),
        ("views/cost.py", "Material cost at risk"),
        ("views/materials.py", "No track record yet"),
        ("views/sf6.py", "Cost gap by material"),
    ],
)
def test_other_pages_run_in_demo_mode(app, page, text):
    app.switch_page(page).run()
    assert not app.exception
    html = html_of(app)
    assert "Demo data" in html and text in html


def test_materials_page_switches_series(app):
    app.switch_page("views/materials.py").run()
    app.selectbox[0].set_value("L02").run()
    assert not app.exception
    html = html_of(app)
    assert "Stainless steel" in html
