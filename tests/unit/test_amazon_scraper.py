"""Test unit per `talos.io_.scraper` (CHG-2026-05-01-002, ADR-0017 canale 2).

Pattern: mock `BrowserPageProtocol` iniettato via parametro `page=`,
nessun network, nessun Chromium. selectors.yaml temporanei via
`tmp_path` per testare loader e fallback chain.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from talos.io_ import (
    AMAZON_IT_PRODUCT_URL,
    DEFAULT_DELAY_RANGE_S,
    DEFAULT_SELECTORS_YAML,
    DEFAULT_USER_AGENT,
    AmazonScraper,
    ScrapedProduct,
    SelectorMissError,
    load_selectors,
    parse_eur,
)
from talos.io_.scraper import _PlaywrightBrowserPage

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mock page
# ---------------------------------------------------------------------------


class _MockPage:
    """Mock di BrowserPageProtocol che mappa selector -> stringa."""

    def __init__(
        self,
        *,
        css_map: dict[str, str | None] | None = None,
        xpath_map: dict[str, str | None] | None = None,
    ) -> None:
        self.css_map = css_map or {}
        self.xpath_map = xpath_map or {}
        self.goto_calls: list[str] = []

    def goto(self, url: str) -> None:
        self.goto_calls.append(url)

    def query_selector_text(self, selector: str) -> str | None:
        return self.css_map.get(selector)

    def query_selector_xpath_text(self, xpath: str) -> str | None:
        return self.xpath_map.get(xpath)


# ---------------------------------------------------------------------------
# Helper YAML
# ---------------------------------------------------------------------------


def _write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "selectors.yaml"
    path.write_text(content, encoding="utf-8")
    return path


_MINIMAL_YAML = """
amazon_it:
  product_title:
    css:
      - "#productTitle"
      - "h1.title"
    xpath:
      - "//h1[@id='productTitle']"
  buybox_price:
    css:
      - "#price1"
      - "#price2"
    xpath:
      - "//*[@id='price-fallback']"
"""


# ---------------------------------------------------------------------------
# load_selectors
# ---------------------------------------------------------------------------


def test_load_selectors_default_yaml_parses() -> None:
    """Il file selectors.yaml in repo deve essere valido."""
    selectors = load_selectors(DEFAULT_SELECTORS_YAML)
    assert "product_title" in selectors
    assert "buybox_price" in selectors
    assert len(selectors["product_title"].css) >= 1
    assert len(selectors["product_title"].xpath) >= 1


def test_load_selectors_minimal_custom(tmp_path: Path) -> None:
    """Caricamento di un YAML custom con 2 campi."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    selectors = load_selectors(path)
    assert selectors["product_title"].css == ["#productTitle", "h1.title"]
    assert selectors["product_title"].xpath == ["//h1[@id='productTitle']"]
    assert selectors["buybox_price"].css == ["#price1", "#price2"]


def test_load_selectors_missing_amazon_it_raises(tmp_path: Path) -> None:
    """Manca chiave radice 'amazon_it' -> ValueError."""
    path = _write_yaml(tmp_path, "other_site:\n  foo: bar\n")
    with pytest.raises(ValueError, match="amazon_it"):
        load_selectors(path)


def test_load_selectors_amazon_it_not_mapping_raises(tmp_path: Path) -> None:
    """`amazon_it` non e' un dict -> TypeError."""
    path = _write_yaml(tmp_path, "amazon_it:\n  - just\n  - a list\n")
    with pytest.raises(TypeError, match="amazon_it"):
        load_selectors(path)


def test_load_selectors_field_not_mapping_raises(tmp_path: Path) -> None:
    """Campo non-dict (es. stringa diretta) -> TypeError."""
    path = _write_yaml(tmp_path, "amazon_it:\n  product_title: just_a_string\n")
    with pytest.raises(TypeError, match="product_title"):
        load_selectors(path)


def test_load_selectors_missing_file_raises(tmp_path: Path) -> None:
    """File inesistente -> FileNotFoundError dal layer file open."""
    with pytest.raises(FileNotFoundError):
        load_selectors(tmp_path / "missing.yaml")


# ---------------------------------------------------------------------------
# parse_eur
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("199,99", Decimal("199.99")),
        ("€ 199,99", Decimal("199.99")),
        ("199,99 €", Decimal("199.99")),
        ("EUR 199,99", Decimal("199.99")),
        ("1.234,56", Decimal("1234.56")),
        ("EUR 1.234,56", Decimal("1234.56")),
        ("1,234.56", Decimal("1234.56")),
        ("199.99", Decimal("199.99")),
        ("€\xa0199,99", Decimal("199.99")),  # non-breaking space
    ],
)
def test_parse_eur_valid(raw: str, expected: Decimal) -> None:
    assert parse_eur(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "€", "abc", "12,34,56"])
def test_parse_eur_invalid_returns_none(raw: str) -> None:
    """Input non parsabile -> None (R-01: caller decide)."""
    assert parse_eur(raw) is None


# ---------------------------------------------------------------------------
# AmazonScraper construction
# ---------------------------------------------------------------------------


def test_scraper_default_construction() -> None:
    """Default construct usa selectors in repo + UA + delay range."""
    scraper = AmazonScraper()
    assert scraper.user_agent == DEFAULT_USER_AGENT
    assert scraper.delay_range_s == DEFAULT_DELAY_RANGE_S


def test_scraper_custom_user_agent_and_delay(tmp_path: Path) -> None:
    """Custom UA + delay range vengono propagati alle property."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(
        user_agent="custom-ua/1.0",
        delay_range_s=(0.5, 1.0),
        selectors_path=path,
    )
    assert scraper.user_agent == "custom-ua/1.0"
    assert scraper.delay_range_s == (0.5, 1.0)


# ---------------------------------------------------------------------------
# Selector fallback chain
# ---------------------------------------------------------------------------


def test_scrape_first_css_match_wins(tmp_path: Path) -> None:
    """Primo selettore CSS ritorna stringa -> vince, no fallback."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage(
        css_map={
            "#productTitle": "Galaxy S24",
            "h1.title": "should-not-be-used",
            "#price1": "€ 199,99",
        },
    )
    product = scraper.scrape_product("B0CN3VDM4G", page=page)
    assert product.title == "Galaxy S24"
    assert product.buybox_eur == Decimal("199.99")


def test_scrape_falls_back_to_second_css(tmp_path: Path) -> None:
    """1° CSS None -> tenta 2° CSS."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage(
        css_map={
            "#productTitle": None,
            "h1.title": "Galaxy S24 (fallback)",
            "#price1": "199,99",
        },
    )
    product = scraper.scrape_product("X", page=page)
    assert product.title == "Galaxy S24 (fallback)"


def test_scrape_falls_back_to_xpath_when_all_css_miss(tmp_path: Path) -> None:
    """Tutti i CSS None/empty -> tenta XPath."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage(
        css_map={"#productTitle": None, "h1.title": "   "},
        xpath_map={"//h1[@id='productTitle']": "Galaxy via XPath"},
    )
    product = scraper.scrape_product("X", page=page)
    assert product.title == "Galaxy via XPath"


def test_scrape_returns_none_when_all_fail_optional(tmp_path: Path) -> None:
    """Public scrape_product usa missing_ok=True -> field=None, no raise."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage(css_map={}, xpath_map={})
    product = scraper.scrape_product("X", page=page)
    assert product == ScrapedProduct(asin="X", title=None, buybox_eur=None)


def test_resolve_field_required_raises_on_total_miss(tmp_path: Path) -> None:
    """`missing_ok=False` -> SelectorMissError con la lista di selettori provati."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage()
    with pytest.raises(SelectorMissError) as excinfo:
        scraper._resolve_field("X", "product_title", page, missing_ok=False)  # noqa: SLF001
    assert excinfo.value.field == "product_title"
    # Tutti i CSS + XPath del campo product_title sono stati tentati.
    assert len(excinfo.value.attempted) == 3  # 2 css + 1 xpath
    assert any("css:#productTitle" in s for s in excinfo.value.attempted)
    assert any("xpath://h1[@id='productTitle']" in s for s in excinfo.value.attempted)


def test_resolve_field_unknown_field_raises_keyerror(tmp_path: Path) -> None:
    """Campo non in selectors.yaml -> KeyError esplicito."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage()
    with pytest.raises(KeyError, match="missing_field"):
        scraper._resolve_field("X", "missing_field", page, missing_ok=True)  # noqa: SLF001


# ---------------------------------------------------------------------------
# scrape_product -> goto + parse_eur integration
# ---------------------------------------------------------------------------


def test_scrape_product_calls_goto_with_amazon_url(tmp_path: Path) -> None:
    """scrape_product naviga a https://www.amazon.it/dp/<asin>."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage()
    scraper.scrape_product("B0CN3VDM4G", page=page)
    assert page.goto_calls == [AMAZON_IT_PRODUCT_URL.format(asin="B0CN3VDM4G")]


def test_scrape_product_buybox_parsed_to_decimal(tmp_path: Path) -> None:
    """buybox_price parsata via parse_eur (italiano)."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage(css_map={"#productTitle": "T", "#price1": "€ 1.234,56"})
    product = scraper.scrape_product("X", page=page)
    assert product.buybox_eur == Decimal("1234.56")


def test_scrape_product_buybox_unparsable_returns_none(tmp_path: Path) -> None:
    """buybox stringa malformata -> buybox_eur=None (no raise)."""
    path = _write_yaml(tmp_path, _MINIMAL_YAML)
    scraper = AmazonScraper(selectors_path=path)
    page = _MockPage(css_map={"#productTitle": "T", "#price1": "abc"})
    product = scraper.scrape_product("X", page=page)
    assert product.buybox_eur is None
    assert product.title == "T"


# ---------------------------------------------------------------------------
# _PlaywrightBrowserPage skeleton — tutti i metodi raise NotImplementedError
# ---------------------------------------------------------------------------


def test_playwright_page_goto_raises_not_implemented() -> None:
    page = _PlaywrightBrowserPage()
    with pytest.raises(NotImplementedError, match="goto"):
        page.goto("https://www.amazon.it/dp/X")


def test_playwright_page_query_selector_raises_not_implemented() -> None:
    page = _PlaywrightBrowserPage()
    with pytest.raises(NotImplementedError, match="query_selector_text"):
        page.query_selector_text("#x")


def test_playwright_page_query_selector_xpath_raises_not_implemented() -> None:
    page = _PlaywrightBrowserPage()
    with pytest.raises(NotImplementedError, match="query_selector_xpath_text"):
        page.query_selector_xpath_text("//x")
