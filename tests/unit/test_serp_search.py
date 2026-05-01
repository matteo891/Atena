"""Test unit per `talos.io_.serp_search` (CHG-2026-05-01-017).

Mock-only via `SerpBrowserProtocol` (`evaluate` ritorna payload
preconfezionato). Pattern coerente con `test_amazon_scraper.py`.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from talos.io_.serp_search import (
    AMAZON_IT_SEARCH_URL_TEMPLATE,
    DEFAULT_SERP_MAX_RESULTS,
    AmazonSerpAdapter,
    SerpResult,
    _LiveAmazonSerpAdapter,
    _parse_serp_payload,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mock browser
# ---------------------------------------------------------------------------


class _MockSerpBrowser:
    """Mock `SerpBrowserProtocol`: registra goto + evaluate, ritorna payload."""

    def __init__(self, payload: object) -> None:
        self._payload = payload
        self.goto_url: str | None = None
        self.eval_expression: str | None = None

    def goto(self, url: str) -> None:
        self.goto_url = url

    def evaluate(self, expression: str) -> object:
        self.eval_expression = expression
        return self._payload


def _make_factory(payload: object) -> tuple[_MockSerpBrowser, AmazonSerpAdapter]:
    """Costruisce mock browser + adapter live che lo ottiene tramite factory."""
    browser = _MockSerpBrowser(payload)
    adapter = _LiveAmazonSerpAdapter(browser_factory=lambda: browser)
    return browser, adapter


# ---------------------------------------------------------------------------
# Costanti modulo
# ---------------------------------------------------------------------------


def test_default_max_results_is_5() -> None:
    """Default top-N SERP = 5 (compromesso fra confidence diversity e cost)."""
    assert DEFAULT_SERP_MAX_RESULTS == 5


def test_search_url_template_uses_amazon_it() -> None:
    """URL template Amazon.it (italiano)."""
    assert AMAZON_IT_SEARCH_URL_TEMPLATE.startswith("https://www.amazon.it/s?k=")


# ---------------------------------------------------------------------------
# `_parse_serp_payload`
# ---------------------------------------------------------------------------


def test_parse_serp_payload_happy_path() -> None:
    """Payload valido -> SerpResult con asin/title/price."""
    payload = [
        {"asin": "B0CSTC2RDW", "title": "Galaxy S24 5G 256GB", "priceText": "549,00 €"},
        {"asin": "B0CN3VDM4G", "title": "Galaxy A55", "priceText": "299,00 €"},
    ]
    results = _parse_serp_payload(payload, max_results=5)
    assert len(results) == 2
    assert results[0] == SerpResult(
        asin="B0CSTC2RDW",
        title="Galaxy S24 5G 256GB",
        price_displayed=Decimal("549.00"),
        position=0,
    )
    assert results[1].position == 1
    assert results[1].price_displayed == Decimal("299.00")


def test_parse_serp_payload_skips_missing_asin() -> None:
    """Risultato senza asin (banner/sponsored) -> skippato silentemente."""
    payload = [
        {"asin": "", "title": "Banner Sponsored", "priceText": ""},
        {"asin": "B0CSTC2RDW", "title": "Galaxy S24", "priceText": "549,00 €"},
    ]
    results = _parse_serp_payload(payload, max_results=5)
    assert len(results) == 1
    assert results[0].asin == "B0CSTC2RDW"


def test_parse_serp_payload_skips_missing_title() -> None:
    """Risultato senza titolo -> skippato (non utile per fuzzy match)."""
    payload = [{"asin": "B0CSTC2RDW", "title": "", "priceText": "549 €"}]
    assert _parse_serp_payload(payload, max_results=5) == []


def test_parse_serp_payload_no_price_results_in_none() -> None:
    """Risultato senza prezzo SERP -> price_displayed=None (non scartato)."""
    payload = [{"asin": "B0CSTC2RDW", "title": "Galaxy S24", "priceText": ""}]
    results = _parse_serp_payload(payload, max_results=5)
    assert len(results) == 1
    assert results[0].price_displayed is None


def test_parse_serp_payload_invalid_price_text_returns_none() -> None:
    """Prezzo non parsable (es. 'Non disp.') -> None, no raise."""
    payload = [{"asin": "B0CSTC2RDW", "title": "Galaxy S24", "priceText": "Non disponibile"}]
    results = _parse_serp_payload(payload, max_results=5)
    assert len(results) == 1
    assert results[0].price_displayed is None


def test_parse_serp_payload_caps_at_max_results() -> None:
    """Top-N filter applicato anche se JS ritorna piu' (defensive)."""
    payload = [
        {"asin": f"B0CSTC2RD{i}", "title": f"Item {i}", "priceText": "100,00 €"} for i in range(10)
    ]
    results = _parse_serp_payload(payload, max_results=3)
    assert len(results) == 3


def test_parse_serp_payload_non_list_returns_empty() -> None:
    """Payload non-list (None / dict / string) -> [] esplicito (R-01)."""
    assert _parse_serp_payload(None, max_results=5) == []
    assert _parse_serp_payload({"asin": "B0"}, max_results=5) == []
    assert _parse_serp_payload("garbage", max_results=5) == []


def test_parse_serp_payload_skips_non_dict_items() -> None:
    """Item non-dict (es. string in lista) -> skippato senza raise."""
    payload = [
        "garbage_string",
        {"asin": "B0CSTC2RDW", "title": "Galaxy S24", "priceText": "549,00 €"},
    ]
    results = _parse_serp_payload(payload, max_results=5)
    assert len(results) == 1
    assert results[0].asin == "B0CSTC2RDW"


# ---------------------------------------------------------------------------
# `_LiveAmazonSerpAdapter.search`
# ---------------------------------------------------------------------------


def test_search_builds_correct_url_and_calls_evaluate() -> None:
    """`search` costruisce URL Amazon.it/s?k=<encoded> + chiama evaluate."""
    browser, adapter = _make_factory(payload=[])
    adapter.search("Galaxy S24 256GB")
    assert browser.goto_url == "https://www.amazon.it/s?k=Galaxy%20S24%20256GB"
    assert browser.eval_expression is not None
    assert "MAX_RESULTS" not in browser.eval_expression  # template sostituito


def test_search_returns_top_n_serp_results() -> None:
    """End-to-end mock: payload -> top-N SerpResult."""
    payload = [
        {"asin": "B0CSTC2RDW", "title": "Galaxy S24 5G", "priceText": "549,00 €"},
        {"asin": "B0CN3VDM4G", "title": "Galaxy A55", "priceText": "299,00 €"},
    ]
    _, adapter = _make_factory(payload)
    results = adapter.search("Galaxy S24")
    assert [r.asin for r in results] == ["B0CSTC2RDW", "B0CN3VDM4G"]
    assert results[0].price_displayed == Decimal("549.00")


def test_search_max_results_param_caps_output() -> None:
    """`max_results=2` su payload di 5 -> ritorna solo 2."""
    payload = [
        {"asin": f"B0CSTC2RD{i}", "title": f"Item {i}", "priceText": "100,00 €"} for i in range(5)
    ]
    _, adapter = _make_factory(payload)
    results = adapter.search("query", max_results=2)
    assert len(results) == 2


def test_search_empty_query_raises() -> None:
    """Query vuota / whitespace -> ValueError esplicito (R-01)."""
    _, adapter = _make_factory(payload=[])
    with pytest.raises(ValueError, match="query SERP vuota"):
        adapter.search("")
    with pytest.raises(ValueError, match="query SERP vuota"):
        adapter.search("   ")


def test_search_max_results_zero_raises() -> None:
    """`max_results <= 0` -> ValueError esplicito."""
    _, adapter = _make_factory(payload=[])
    with pytest.raises(ValueError, match="max_results"):
        adapter.search("query", max_results=0)
    with pytest.raises(ValueError, match="max_results"):
        adapter.search("query", max_results=-1)


def test_search_url_encodes_special_chars() -> None:
    """Caratteri speciali (accenti, simboli) URL-encoded."""
    browser, adapter = _make_factory(payload=[])
    adapter.search("caffè & té")
    assert browser.goto_url is not None
    assert "caff%C3%A8" in browser.goto_url
    assert "%26" in browser.goto_url  # `&` encoded


def test_search_zero_results_returns_empty_list() -> None:
    """Zero risultati SERP (payload []) -> [] esplicito, no raise."""
    _, adapter = _make_factory(payload=[])
    results = adapter.search("ProdottoInesistente12345")
    assert results == []
