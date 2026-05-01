"""Test unit per `talos.io_.fallback_chain` (CHG-2026-05-01-006, ADR-0017).

Pattern: mock `KeepaApiAdapter` iniettato via `adapter_factory` del
`KeepaClient`, mock `BrowserPageProtocol` passato a `lookup_product`
via `page=`. Nessun network, nessun Chromium, nessuna sleep reale
(retry wait azzerati).
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from talos.io_ import (
    SOURCE_KEEPA,
    SOURCE_SCRAPER,
    AmazonScraper,
    BsrEntry,
    KeepaClient,
    KeepaProduct,
    KeepaRateLimitExceededError,
    KeepaTransientError,
    ProductData,
    lookup_product,
    lookup_products,
)

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class _FixedKeepaAdapter:
    """Adapter Keepa che ritorna sempre lo stesso prodotto."""

    def __init__(self, product: KeepaProduct) -> None:
        self.product = product
        self.calls = 0

    def query(self, asin: str) -> KeepaProduct:  # noqa: ARG002 — mock
        self.calls += 1
        return self.product


class _RaisingKeepaAdapter:
    """Adapter Keepa che solleva un'eccezione fissa al primo query."""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.calls = 0

    def query(self, asin: str) -> KeepaProduct:  # noqa: ARG002 — mock
        self.calls += 1
        raise self.exc


class _MockPage:
    """Mock di BrowserPageProtocol per AmazonScraper."""

    def __init__(
        self,
        *,
        css_map: dict[str, str | None] | None = None,
        xpath_map: dict[str, str | None] | None = None,
        css_all_map: dict[str, list[str]] | None = None,
    ) -> None:
        self.css_map = css_map or {}
        self.xpath_map = xpath_map or {}
        self.css_all_map = css_all_map or {}
        self.goto_calls: list[str] = []

    def goto(self, url: str) -> None:
        self.goto_calls.append(url)

    def query_selector_text(self, selector: str) -> str | None:
        return self.css_map.get(selector)

    def query_selector_xpath_text(self, xpath: str) -> str | None:
        return self.xpath_map.get(xpath)

    def query_selector_all_text(self, selector: str) -> list[str]:
        return self.css_all_map.get(selector, [])


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _make_keepa(
    product: KeepaProduct,
    *,
    rate_limit: int = 1000,
) -> KeepaClient:
    """Crea un KeepaClient con `_FixedKeepaAdapter` mockato."""
    return KeepaClient(
        api_key="test",
        rate_limit_per_minute=rate_limit,
        adapter_factory=lambda _key: _FixedKeepaAdapter(product),
        retry_wait_min_s=0.0,
        retry_wait_max_s=0.0,
    )


def _make_keepa_raising(exc: Exception) -> KeepaClient:
    return KeepaClient(
        api_key="test",
        rate_limit_per_minute=1000,
        adapter_factory=lambda _key: _RaisingKeepaAdapter(exc),
        retry_wait_min_s=0.0,
        retry_wait_max_s=0.0,
    )


def _full_keepa_product(asin: str = "B0FULL") -> KeepaProduct:
    return KeepaProduct(
        asin=asin,
        buybox_eur=Decimal("199.99"),
        bsr=42,
        fee_fba_eur=Decimal("3.50"),
    )


# ---------------------------------------------------------------------------
# ProductData shape
# ---------------------------------------------------------------------------


def test_product_data_is_frozen() -> None:
    pd = ProductData(
        asin="X",
        buybox_eur=None,
        bsr=None,
        fee_fba_eur=None,
        title=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        pd.asin = "Y"  # type: ignore[misc]


def test_product_data_default_factories_are_independent() -> None:
    """sources/notes default factory non condividono lo stesso oggetto."""
    a = ProductData(asin="A", buybox_eur=None, bsr=None, fee_fba_eur=None, title=None)
    b = ProductData(asin="B", buybox_eur=None, bsr=None, fee_fba_eur=None, title=None)
    a.sources["x"] = "1"
    a.notes.append("note-a")
    assert b.sources == {}
    assert b.notes == []


# ---------------------------------------------------------------------------
# Keepa primary success
# ---------------------------------------------------------------------------


def test_lookup_keepa_success_all_fields_populated() -> None:
    keepa = _make_keepa(_full_keepa_product("B0AAA"))
    result = lookup_product("B0AAA", keepa=keepa)
    assert result.asin == "B0AAA"
    assert result.buybox_eur == Decimal("199.99")
    assert result.bsr == 42
    assert result.fee_fba_eur == Decimal("3.50")
    assert result.title is None  # Keepa non espone title
    assert result.sources == {
        "buybox_eur": SOURCE_KEEPA,
        "bsr": SOURCE_KEEPA,
        "fee_fba_eur": SOURCE_KEEPA,
    }
    assert result.notes == []


def test_lookup_no_scraper_means_no_title_even_if_buybox_present() -> None:
    """Senza scraper il title resta None anche se Keepa ha tutto il resto."""
    keepa = _make_keepa(_full_keepa_product())
    result = lookup_product("B0NOSC", keepa=keepa)
    assert result.title is None
    assert "title" not in result.sources


# ---------------------------------------------------------------------------
# Keepa miss → notes
# ---------------------------------------------------------------------------


def test_lookup_keepa_miss_buybox_records_note() -> None:
    keepa = _make_keepa(
        KeepaProduct(asin="X", buybox_eur=None, bsr=10, fee_fba_eur=Decimal("2.00")),
    )
    result = lookup_product("X", keepa=keepa)
    assert result.buybox_eur is None
    assert result.bsr == 10
    assert result.fee_fba_eur == Decimal("2.00")
    assert "buybox_eur" not in result.sources
    assert any("buybox" in n for n in result.notes)


def test_lookup_keepa_miss_all_three_records_three_notes() -> None:
    keepa = _make_keepa(
        KeepaProduct(asin="Y", buybox_eur=None, bsr=None, fee_fba_eur=None),
    )
    result = lookup_product("Y", keepa=keepa)
    assert result.buybox_eur is None
    assert result.bsr is None
    assert result.fee_fba_eur is None
    assert result.sources == {}
    assert len(result.notes) == 3
    joined = " ".join(result.notes)
    assert "buybox" in joined
    assert "bsr" in joined
    assert "fee_fba" in joined


# ---------------------------------------------------------------------------
# Eccezioni Keepa che propagano (non miss)
# ---------------------------------------------------------------------------


def test_lookup_propagates_rate_limit_exceeded() -> None:
    """Rate-limit hit propaga al caller (R-01 fail-now)."""
    exc = KeepaRateLimitExceededError("Z", rate_limit_per_minute=60)
    keepa = _make_keepa_raising(exc)
    with pytest.raises(KeepaRateLimitExceededError):
        lookup_product("Z", keepa=keepa)


def test_lookup_propagates_transient_after_retries_exhausted() -> None:
    """Transient error dopo retry esauriti propaga al caller."""
    exc = KeepaTransientError("server 503")
    keepa = _make_keepa_raising(exc)
    with pytest.raises(KeepaTransientError):
        lookup_product("Q", keepa=keepa)


# ---------------------------------------------------------------------------
# Scraper fallback
# ---------------------------------------------------------------------------


def _build_scraper(tmp_path: Path) -> AmazonScraper:
    """Scraper minimale con selectors.yaml temporaneo."""
    yaml_content = """
amazon_it:
  product_title:
    css:
      - "#productTitle"
    xpath: []
  buybox_price:
    css:
      - "#corePrice"
    xpath: []
  bsr_root:
    css:
      - "#bsr-root"
    xpath: []
  bsr_sub:
    css:
      - "ul.zg_hrsr li"
    xpath: []
"""
    path = tmp_path / "selectors.yaml"
    path.write_text(yaml_content, encoding="utf-8")
    return AmazonScraper(selectors_path=path)


def test_lookup_scraper_fills_title_when_keepa_has_buybox(tmp_path: Path) -> None:
    """Keepa fornisce buybox/bsr/fee, scraper aggiunge title."""
    keepa = _make_keepa(_full_keepa_product("B0SCT"))
    scraper = _build_scraper(tmp_path)
    page = _MockPage(
        css_map={
            "#productTitle": "Galaxy S24 Titanium Black",
            "#corePrice": None,  # buybox non serve, Keepa l'ha
        },
    )
    result = lookup_product("B0SCT", keepa=keepa, scraper=scraper, page=page)
    assert result.title == "Galaxy S24 Titanium Black"
    assert result.sources["title"] == SOURCE_SCRAPER
    assert result.sources["buybox_eur"] == SOURCE_KEEPA
    assert page.goto_calls == ["https://www.amazon.it/dp/B0SCT"]


def test_lookup_scraper_fills_buybox_when_keepa_misses(tmp_path: Path) -> None:
    """Keepa miss buybox -> scraper risolve via selettore CSS."""
    keepa = _make_keepa(
        KeepaProduct(asin="B0SCB", buybox_eur=None, bsr=5, fee_fba_eur=Decimal("4.00")),
    )
    scraper = _build_scraper(tmp_path)
    page = _MockPage(
        css_map={
            "#productTitle": "Some Product",
            "#corePrice": "€ 249,90",
        },
    )
    result = lookup_product("B0SCB", keepa=keepa, scraper=scraper, page=page)
    assert result.buybox_eur == Decimal("249.90")
    assert result.sources["buybox_eur"] == SOURCE_SCRAPER
    assert result.title == "Some Product"
    assert result.bsr == 5  # da Keepa


def test_lookup_scraper_skipped_if_keepa_has_buybox_and_no_title_needed(
    tmp_path: Path,
) -> None:
    """Lo scraper viene comunque invocato perche' title e' sempre None pre-scrape."""
    keepa = _make_keepa(_full_keepa_product())
    scraper = _build_scraper(tmp_path)
    page = _MockPage(
        css_map={"#productTitle": "T", "#corePrice": "€ 100,00"},
    )
    lookup_product("B0XXX", keepa=keepa, scraper=scraper, page=page)
    # Lo scraper viene invocato (per title), goto chiamato.
    assert page.goto_calls == ["https://www.amazon.it/dp/B0XXX"]


def test_lookup_scraper_not_invoked_when_page_is_none(tmp_path: Path) -> None:
    """Scraper fornito ma page=None -> graceful, scraper non invocato."""
    keepa = _make_keepa(_full_keepa_product())
    scraper = _build_scraper(tmp_path)
    result = lookup_product("B0NPG", keepa=keepa, scraper=scraper, page=None)
    assert result.title is None  # scraper non invocato


def test_lookup_scraper_miss_total_no_crash(tmp_path: Path) -> None:
    """Keepa miss buybox + scraper miss buybox/title: campo resta None, no exception."""
    keepa = _make_keepa(
        KeepaProduct(asin="B0DRY", buybox_eur=None, bsr=None, fee_fba_eur=None),
    )
    scraper = _build_scraper(tmp_path)
    page = _MockPage(css_map={"#productTitle": None, "#corePrice": None})
    result = lookup_product("B0DRY", keepa=keepa, scraper=scraper, page=page)
    assert result.buybox_eur is None
    assert result.title is None
    assert result.bsr is None
    assert result.fee_fba_eur is None
    # Notes annotano i 3 keepa miss; lo scrape miss e' loggato dal scraper
    # (telemetria scrape.selector_fail) ma non si traduce in note qui.
    assert len(result.notes) == 3


def test_lookup_with_ocr_param_does_not_invoke_ocr() -> None:
    """OCR e' parametro placeholder in CHG-006: passarlo non altera il risultato."""

    class _ExplodingOcr:
        def process_image(self, image: object) -> object:  # noqa: ARG002
            msg = "OCR not invoked"
            raise AssertionError(msg)

    keepa = _make_keepa(_full_keepa_product())
    result = lookup_product("B0OCR", keepa=keepa, ocr=_ExplodingOcr())  # type: ignore[arg-type]
    assert result.buybox_eur == Decimal("199.99")  # KeepaClient invocato regolarmente


# ---------------------------------------------------------------------------
# Asin propagation
# ---------------------------------------------------------------------------


def test_lookup_propagates_asin_to_result() -> None:
    keepa = _make_keepa(_full_keepa_product("DOES_NOT_MATTER"))
    result = lookup_product("CALLER_ASIN", keepa=keepa)
    # `asin` di ProductData usa il parametro al call site (non il KeepaProduct).
    assert result.asin == "CALLER_ASIN"


# ---------------------------------------------------------------------------
# lookup_products bulk wrapper (CHG-2026-05-01-009)
# ---------------------------------------------------------------------------


def test_lookup_products_empty_list_returns_empty() -> None:
    """No-op su lista vuota (no chiamate ai canali)."""
    keepa = _make_keepa_raising(KeepaTransientError("would fire if called"))
    result = lookup_products([], keepa=keepa)
    assert result == []


def test_lookup_products_preserves_order_and_cardinality() -> None:
    keepa = _make_keepa(_full_keepa_product())
    asins = ["B0BULK01", "B0BULK02", "B0BULK03"]
    results = lookup_products(asins, keepa=keepa)
    assert [r.asin for r in results] == asins
    assert len(results) == 3
    for r in results:
        assert r.buybox_eur == Decimal("199.99")
        assert r.bsr == 42


def test_lookup_products_propagates_rate_limit_at_first_failure() -> None:
    """Rate limit fail-fast: il batch si interrompe al primo ASIN che lo trigger."""
    exc = KeepaRateLimitExceededError("X", rate_limit_per_minute=60)
    keepa = _make_keepa_raising(exc)
    with pytest.raises(KeepaRateLimitExceededError):
        lookup_products(["A1", "A2", "A3"], keepa=keepa)


# ---------------------------------------------------------------------------
# BSR chain propagation (CHG-2026-05-01-013)
# ---------------------------------------------------------------------------


def test_lookup_propagates_bsr_chain_from_scraper(tmp_path: Path) -> None:
    """Scraper popola bsr_chain multi-livello -> ProductData.bsr_chain."""
    keepa = _make_keepa(_full_keepa_product("B0BSR1"))
    scraper = _build_scraper(tmp_path)
    page = _MockPage(
        css_map={"#productTitle": "Galaxy", "#corePrice": None},
        css_all_map={
            "ul.zg_hrsr li": [
                "n. 15 in Cellulari",
                "n. 3 in Smartphone Samsung",
            ],
            "#bsr-root": ["n. 1.234 in Elettronica"],
        },
    )
    result = lookup_product("B0BSR1", keepa=keepa, scraper=scraper, page=page)
    # Sort per rank crescente: specifico -> ampio.
    assert result.bsr_chain == [
        BsrEntry(category="Smartphone Samsung", rank=3),
        BsrEntry(category="Cellulari", rank=15),
        BsrEntry(category="Elettronica", rank=1234),
    ]
    # Keepa ha gia' fornito bsr (root) → non viene sovrascritto da scraper.
    assert result.bsr == 42  # KeepaProduct mock
    assert result.sources["bsr"] == SOURCE_KEEPA
    assert result.sources["bsr_chain"] == SOURCE_SCRAPER


def test_lookup_uses_scraper_bsr_when_keepa_misses(tmp_path: Path) -> None:
    """Keepa miss bsr → ProductData.bsr = bsr_chain[0].rank (più specifico)."""
    keepa = _make_keepa(
        KeepaProduct(asin="B0NOK", buybox_eur=Decimal(100), bsr=None, fee_fba_eur=None),
    )
    scraper = _build_scraper(tmp_path)
    page = _MockPage(
        css_map={"#productTitle": "T", "#corePrice": None},
        css_all_map={
            "ul.zg_hrsr li": ["n. 7 in Smartphone Samsung"],
            "#bsr-root": ["n. 1.000 in Elettronica"],
        },
    )
    result = lookup_product("B0NOK", keepa=keepa, scraper=scraper, page=page)
    assert result.bsr == 7  # bsr_chain[0] = Smartphone Samsung (più specifico)
    assert result.sources["bsr"] == SOURCE_SCRAPER
    assert result.bsr_chain[0] == BsrEntry(category="Smartphone Samsung", rank=7)


def test_lookup_bsr_chain_empty_when_no_scraper() -> None:
    """Senza scraper, bsr_chain resta lista vuota."""
    keepa = _make_keepa(_full_keepa_product())
    result = lookup_product("B0NS", keepa=keepa)
    assert result.bsr_chain == []


def test_lookup_bsr_chain_empty_when_scraper_misses_total(tmp_path: Path) -> None:
    """Scraper invocato ma BSR selettori miss totale → chain vuota."""
    keepa = _make_keepa(_full_keepa_product())
    scraper = _build_scraper(tmp_path)
    page = _MockPage(css_map={"#productTitle": "T", "#corePrice": None})
    result = lookup_product("B0NB", keepa=keepa, scraper=scraper, page=page)
    assert result.bsr_chain == []
    assert "bsr_chain" not in result.sources


def test_product_data_bsr_chain_default_empty() -> None:
    """ProductData backward compat: bsr_chain default lista vuota."""
    pd = ProductData(
        asin="X",
        buybox_eur=None,
        bsr=None,
        fee_fba_eur=None,
        title=None,
    )
    assert pd.bsr_chain == []


def test_lookup_products_threads_scraper_and_page_through(
    tmp_path: Path,
) -> None:
    """Scraper+page condivisi fra le chiamate; goto chiamato per ogni ASIN."""
    keepa = _make_keepa(_full_keepa_product())
    scraper = _build_scraper(tmp_path)
    page = _MockPage(
        css_map={"#productTitle": "Galaxy", "#corePrice": "€ 100,00"},
    )
    asins = ["B0PG01", "B0PG02"]
    results = lookup_products(asins, keepa=keepa, scraper=scraper, page=page)
    assert len(results) == 2
    assert page.goto_calls == [
        "https://www.amazon.it/dp/B0PG01",
        "https://www.amazon.it/dp/B0PG02",
    ]
    for r in results:
        assert r.title == "Galaxy"
