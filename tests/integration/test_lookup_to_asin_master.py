"""Sentinella e2e: `lookup_product` -> `parse_title` -> `build_asin_master_input` -> DB.

CHG-2026-05-01-008 — primo flusso end-to-end della Fase 1 Path B.
Dimostra che le primitive isolate dei CHG-001..007 si compongono in
un percorso utilizzabile, con DB Postgres reale ma SENZA live
adapters (Keepa mock, Scraper mock con BrowserPageProtocol mock).

Lo scenario simula l'integratore Fase 3: per ogni ASIN, la fallback
chain risolve `ProductData` -> SamsungExtractor estrae le entita'
dal titolo Amazon -> bridge costruisce `AsinMasterInput` ->
`upsert_asin_master` persiste su Postgres con merge `COALESCE`.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from talos.extract import (
    SamsungExtractor,
    build_asin_master_input,
    upsert_asin_master,
)
from talos.io_ import (
    AmazonScraper,
    KeepaClient,
    KeepaProduct,
    lookup_product,
)
from talos.persistence.models.asin_master import AsinMaster

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from sqlalchemy import Engine

pytestmark = pytest.mark.integration


_TEST_ASIN = "B0E2E0001"


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------


class _KeepaAdapter:
    def __init__(self, product: KeepaProduct) -> None:
        self.product = product

    def query(self, asin: str) -> KeepaProduct:  # noqa: ARG002 — mock
        return self.product


class _ScrapedPage:
    """Mock BrowserPageProtocol che ritorna un titolo fisso."""

    def __init__(self, title: str | None) -> None:
        self.title = title

    def goto(self, url: str) -> None:  # noqa: ARG002 — mock
        return None

    def query_selector_text(self, selector: str) -> str | None:
        if selector == "#productTitle":
            return self.title
        return None

    def query_selector_xpath_text(self, xpath: str) -> str | None:  # noqa: ARG002 — mock
        return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def orm_session(pg_engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    sess = factory()
    sess.execute(
        text("DELETE FROM asin_master WHERE asin = :asin"),
        {"asin": _TEST_ASIN},
    )
    sess.commit()
    try:
        yield sess
    finally:
        sess.execute(
            text("DELETE FROM asin_master WHERE asin = :asin"),
            {"asin": _TEST_ASIN},
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


# ---------------------------------------------------------------------------
# Sentinella e2e
# ---------------------------------------------------------------------------


def test_e2e_lookup_to_asin_master_round_trip(
    orm_session: Session,
    selectors_yaml: Path,
) -> None:
    """Mock Keepa+Scraper -> lookup_product -> parse_title -> bridge -> upsert -> DB."""
    keepa_product = KeepaProduct(
        asin=_TEST_ASIN,
        buybox_eur=Decimal("799.00"),
        bsr=42,
        fee_fba_eur=Decimal("3.50"),
    )
    keepa = KeepaClient(
        api_key="test",
        rate_limit_per_minute=1000,
        adapter_factory=lambda _key: _KeepaAdapter(keepa_product),
        retry_wait_min_s=0.0,
        retry_wait_max_s=0.0,
    )
    scraper = AmazonScraper(selectors_path=selectors_yaml)
    page = _ScrapedPage(title="Samsung Galaxy S24 12GB RAM 256GB Titanium Black 5G")

    # 1) Acquisizione: fallback chain
    product_data = lookup_product(_TEST_ASIN, keepa=keepa, scraper=scraper, page=page)
    assert product_data.asin == _TEST_ASIN
    assert product_data.buybox_eur == Decimal("799.00")
    assert product_data.bsr == 42
    assert product_data.fee_fba_eur == Decimal("3.50")
    assert product_data.title == "Samsung Galaxy S24 12GB RAM 256GB Titanium Black 5G"

    # 2) Estrazione entita' Samsung dal titolo Amazon
    extractor = SamsungExtractor()
    entities = extractor.parse_title(product_data.title)
    assert entities.model == "Galaxy S24"
    assert entities.ram_gb == 12
    assert entities.rom_gb == 256
    assert entities.color == "Titanium Black"
    assert entities.connectivity == "5G"

    # 3) Bridge -> AsinMasterInput
    inp = build_asin_master_input(
        product_data,
        brand="Samsung",
        enterprise=False,
        samsung_entities=entities,
        category_node="electronics/smartphones",
    )

    # 4) Persistenza
    returned = upsert_asin_master(orm_session, data=inp)
    orm_session.commit()
    assert returned == _TEST_ASIN

    # 5) Round-trip: query verifica
    row = orm_session.get(AsinMaster, _TEST_ASIN)
    assert row is not None
    assert row.title == "Samsung Galaxy S24 12GB RAM 256GB Titanium Black 5G"
    assert row.brand == "Samsung"
    assert row.enterprise is False
    assert row.model == "Galaxy S24"
    assert row.ram_gb == 12
    assert row.rom_gb == 256
    assert row.connectivity == "5G"
    assert row.color_family == "Titanium Black"
    assert row.category_node == "electronics/smartphones"


def test_e2e_second_pass_merges_via_coalesce(
    orm_session: Session,
    selectors_yaml: Path,
) -> None:
    """Pass 1: insert con tutti i campi. Pass 2: lookup miss su title -> merge preserva."""
    # Pass 1 — full insert
    keepa_full = KeepaClient(
        api_key="test",
        rate_limit_per_minute=1000,
        adapter_factory=lambda _key: _KeepaAdapter(
            KeepaProduct(
                asin=_TEST_ASIN,
                buybox_eur=Decimal("799.00"),
                bsr=42,
                fee_fba_eur=Decimal("3.50"),
            ),
        ),
        retry_wait_min_s=0.0,
        retry_wait_max_s=0.0,
    )
    scraper = AmazonScraper(selectors_path=selectors_yaml)
    page1 = _ScrapedPage(title="Samsung Galaxy S24 12GB RAM 256GB Titanium Black 5G")
    pd1 = lookup_product(_TEST_ASIN, keepa=keepa_full, scraper=scraper, page=page1)
    ents1 = SamsungExtractor().parse_title(pd1.title or "")
    inp1 = build_asin_master_input(pd1, brand="Samsung", samsung_entities=ents1)
    upsert_asin_master(orm_session, data=inp1)
    orm_session.commit()

    # Pass 2 — Keepa+Scraper rispondono ma SamsungExtractor non riceve titolo informativo
    # (es. titolo nuovo, modello non identificato). Bridge passa samsung_entities=None
    # -> merge COALESCE D5.b preserva model/ram/rom/connectivity/color_family.
    page2 = _ScrapedPage(title="Some Updated Title Without Samsung Markers")
    pd2 = lookup_product(_TEST_ASIN, keepa=keepa_full, scraper=scraper, page=page2)
    inp2 = build_asin_master_input(pd2, brand="Samsung", samsung_entities=None)
    upsert_asin_master(orm_session, data=inp2)
    orm_session.commit()

    row = orm_session.get(AsinMaster, _TEST_ASIN)
    assert row is not None
    # Title overwrite (NOT NULL).
    assert row.title == "Some Updated Title Without Samsung Markers"
    # Nullable fields preservati via COALESCE (D5.b).
    assert row.model == "Galaxy S24"
    assert row.ram_gb == 12
    assert row.rom_gb == 256
    assert row.color_family == "Titanium Black"
    assert row.connectivity == "5G"
