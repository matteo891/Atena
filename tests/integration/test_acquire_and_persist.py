"""Test integration per `acquire_and_persist` (CHG-2026-05-01-010, ADR-0017 + ADR-0015).

Sentinella e2e dell'orchestratore Fase 1 Path B: dato un batch di
ASIN + mock chains (Keepa adapter mock, BrowserPageProtocol mock),
verifica che il flusso `lookup_products` -> `parse_title` ->
`build_asin_master_input` -> `upsert_asin_master` produca il
risultato atteso su Postgres reale.

Fase 1 Path B: zero setup di sistema (nessun Chromium, nessun
Tesseract, nessuna sandbox API key Keepa). I live adapter
restano skeleton (`NotImplementedError`).
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from talos.extract import (
    SamsungExtractor,
    acquire_and_persist,
)
from talos.io_ import (
    AmazonScraper,
    KeepaClient,
    KeepaProduct,
)
from talos.persistence.models.asin_master import AsinMaster

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from pathlib import Path

    from sqlalchemy import Engine

pytestmark = pytest.mark.integration


_TEST_ASINS = ["B0ACQ0001", "B0ACQ0002", "B0ACQ0003"]


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class _PerAsinKeepaAdapter:
    """Mock Keepa che ritorna un KeepaProduct diverso per ogni ASIN."""

    def __init__(self, products_by_asin: dict[str, KeepaProduct]) -> None:
        self.products_by_asin = products_by_asin

    def query(self, asin: str) -> KeepaProduct:
        if asin not in self.products_by_asin:
            msg = f"Mock keepa: ASIN {asin!r} non configurato"
            raise KeyError(msg)
        return self.products_by_asin[asin]


class _PerAsinPage:
    """Mock BrowserPageProtocol che ritorna title diverso per ASIN navigato."""

    def __init__(self, titles_by_url: Mapping[str, str | None]) -> None:
        self.titles_by_url = titles_by_url
        self._current_url: str | None = None

    def goto(self, url: str) -> None:
        self._current_url = url

    def query_selector_text(self, selector: str) -> str | None:
        if selector == "#productTitle" and self._current_url is not None:
            return self.titles_by_url.get(self._current_url)
        return None

    def query_selector_xpath_text(self, xpath: str) -> str | None:  # noqa: ARG002
        return None

    def query_selector_all_text(self, selector: str) -> list[str]:  # noqa: ARG002
        return []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def orm_session(pg_engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    sess = factory()
    sess.execute(
        text("DELETE FROM asin_master WHERE asin = ANY(:asins)"),
        {"asins": _TEST_ASINS},
    )
    sess.commit()
    try:
        yield sess
    finally:
        sess.execute(
            text("DELETE FROM asin_master WHERE asin = ANY(:asins)"),
            {"asins": _TEST_ASINS},
        )
        sess.commit()
        sess.close()


@pytest.fixture
def selectors_yaml(tmp_path: Path) -> Path:
    content = """
amazon_it:
  product_title:
    css: ["#productTitle"]
    xpath: []
  buybox_price:
    css: ["#corePrice"]
    xpath: []
"""
    p = tmp_path / "selectors.yaml"
    p.write_text(content, encoding="utf-8")
    return p


def _make_keepa(products_by_asin: dict[str, KeepaProduct]) -> KeepaClient:
    return KeepaClient(
        api_key="test",
        rate_limit_per_minute=1000,
        adapter_factory=lambda _key: _PerAsinKeepaAdapter(products_by_asin),
        retry_wait_min_s=0.0,
        retry_wait_max_s=0.0,
    )


# ---------------------------------------------------------------------------
# Sentinelle e2e
# ---------------------------------------------------------------------------


def test_acquire_and_persist_empty_list_is_noop(
    orm_session: Session,
) -> None:
    """Lista vuota → nessuna chiamata, nessuna riga, ritorna []."""
    keepa = _make_keepa({})  # niente ASIN configurati, ma non viene chiamato
    persisted = acquire_and_persist([], db=orm_session, keepa=keepa, brand="Samsung")
    orm_session.commit()
    assert persisted == []


def test_acquire_and_persist_batch_round_trip(
    orm_session: Session,
    selectors_yaml: Path,
) -> None:
    """3 ASIN, mock full → tutti persistiti con dati attesi."""
    products = {
        "B0ACQ0001": KeepaProduct(
            asin="B0ACQ0001",
            buybox_eur=Decimal("799.00"),
            bsr=42,
            fee_fba_eur=Decimal("3.50"),
        ),
        "B0ACQ0002": KeepaProduct(
            asin="B0ACQ0002",
            buybox_eur=Decimal("499.00"),
            bsr=120,
            fee_fba_eur=Decimal("3.00"),
        ),
        "B0ACQ0003": KeepaProduct(
            asin="B0ACQ0003",
            buybox_eur=Decimal("1299.00"),
            bsr=8,
            fee_fba_eur=Decimal("4.50"),
        ),
    }
    titles = {
        "https://www.amazon.it/dp/B0ACQ0001": (
            "Samsung Galaxy S24 12GB RAM 256GB Titanium Black 5G"
        ),
        "https://www.amazon.it/dp/B0ACQ0002": ("Samsung Galaxy A55 8GB RAM 128GB Awesome Lilac 5G"),
        "https://www.amazon.it/dp/B0ACQ0003": (
            "Samsung Galaxy Z Fold5 12GB RAM 512GB Phantom Black 5G"
        ),
    }
    keepa = _make_keepa(products)
    scraper = AmazonScraper(selectors_path=selectors_yaml)
    page = _PerAsinPage(titles)
    extractor = SamsungExtractor()

    persisted = acquire_and_persist(
        _TEST_ASINS,
        db=orm_session,
        keepa=keepa,
        brand="Samsung",
        scraper=scraper,
        page=page,
        extractor=extractor,
        category_node="electronics/smartphones",
    )
    orm_session.commit()

    assert persisted == _TEST_ASINS

    # Verifica round-trip per ogni ASIN
    row1 = orm_session.get(AsinMaster, "B0ACQ0001")
    assert row1 is not None
    assert row1.brand == "Samsung"
    assert row1.model == "Galaxy S24"
    assert row1.ram_gb == 12
    assert row1.rom_gb == 256
    assert row1.color_family == "Titanium Black"
    assert row1.connectivity == "5G"
    assert row1.category_node == "electronics/smartphones"

    row2 = orm_session.get(AsinMaster, "B0ACQ0002")
    assert row2 is not None
    assert row2.model == "Galaxy A55"
    assert row2.rom_gb == 128

    row3 = orm_session.get(AsinMaster, "B0ACQ0003")
    assert row3 is not None
    assert row3.model == "Galaxy Z Fold5"
    assert row3.rom_gb == 512


def test_acquire_and_persist_uses_title_fallback_when_scrape_misses(
    orm_session: Session,
    selectors_yaml: Path,
) -> None:
    """ASIN con title scrape None → caller passa title_fallbacks[asin]."""
    products = {
        "B0ACQ0001": KeepaProduct(
            asin="B0ACQ0001",
            buybox_eur=Decimal("799.00"),
            bsr=42,
            fee_fba_eur=Decimal("3.50"),
        ),
    }
    keepa = _make_keepa(products)
    scraper = AmazonScraper(selectors_path=selectors_yaml)
    page = _PerAsinPage({"https://www.amazon.it/dp/B0ACQ0001": None})  # scrape miss

    persisted = acquire_and_persist(
        ["B0ACQ0001"],
        db=orm_session,
        keepa=keepa,
        brand="Samsung",
        scraper=scraper,
        page=page,
        title_fallbacks={"B0ACQ0001": "Samsung Listino Fornitore Generic"},
    )
    orm_session.commit()
    assert persisted == ["B0ACQ0001"]

    row = orm_session.get(AsinMaster, "B0ACQ0001")
    assert row is not None
    assert row.title == "Samsung Listino Fornitore Generic"


def test_acquire_and_persist_raises_when_no_title_and_no_fallback(
    orm_session: Session,
    selectors_yaml: Path,
) -> None:
    """ASIN con scrape miss + nessun fallback → ValueError fail-fast."""
    products = {
        "B0ACQ0002": KeepaProduct(
            asin="B0ACQ0002",
            buybox_eur=Decimal("499.00"),
            bsr=120,
            fee_fba_eur=Decimal("3.00"),
        ),
    }
    keepa = _make_keepa(products)
    scraper = AmazonScraper(selectors_path=selectors_yaml)
    page = _PerAsinPage({"https://www.amazon.it/dp/B0ACQ0002": None})

    with pytest.raises(ValueError, match="title is None"):
        acquire_and_persist(
            ["B0ACQ0002"],
            db=orm_session,
            keepa=keepa,
            brand="Samsung",
            scraper=scraper,
            page=page,
        )
    orm_session.rollback()

    row = orm_session.get(AsinMaster, "B0ACQ0002")
    assert row is None  # nulla persistito


def test_acquire_and_persist_without_extractor_leaves_nullable_fields_none(
    orm_session: Session,
    selectors_yaml: Path,
) -> None:
    """Senza `extractor`, model/ram/rom/color/connectivity restano None."""
    products = {
        "B0ACQ0001": KeepaProduct(
            asin="B0ACQ0001",
            buybox_eur=Decimal("799.00"),
            bsr=42,
            fee_fba_eur=Decimal("3.50"),
        ),
    }
    keepa = _make_keepa(products)
    scraper = AmazonScraper(selectors_path=selectors_yaml)
    page = _PerAsinPage(
        {"https://www.amazon.it/dp/B0ACQ0001": "Samsung Galaxy S24 256GB"},
    )

    persisted = acquire_and_persist(
        ["B0ACQ0001"],
        db=orm_session,
        keepa=keepa,
        brand="Samsung",
        scraper=scraper,
        page=page,
    )
    orm_session.commit()
    assert persisted == ["B0ACQ0001"]

    row = orm_session.get(AsinMaster, "B0ACQ0001")
    assert row is not None
    assert row.title == "Samsung Galaxy S24 256GB"
    assert row.model is None
    assert row.ram_gb is None
    assert row.rom_gb is None
    assert row.color_family is None
    assert row.connectivity is None
