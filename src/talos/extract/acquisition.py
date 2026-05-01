"""Orchestratore Fase 1 Path B: acquisizione + persistenza anagrafica.

CHG-2026-05-01-010 chiude la Fase 1: dati una lista di ASIN +
client Keepa + opzionalmente scraper/page/extractor, popola
`asin_master` componendo le primitive dei CHG-006..009.

Pipeline per ogni ASIN:

    1. `lookup_product` (CHG-006) -> `ProductData`
    2. Se `extractor` e' fornito e `product_data.title` non None:
       `extractor.parse_title(title)` -> `SamsungEntities`;
       altrimenti `entities = None`.
    3. `build_asin_master_input(product_data, ..., samsung_entities)`
       (CHG-008) -> `AsinMasterInput`. Solleva `ValueError` se
       `product_data.title is None` e nessun `title_fallback`
       per quell'asin (R-01 NO SILENT DROPS).
    4. `upsert_asin_master(db, data=input)` (CHG-005) -> persiste
       sul DB (UPSERT atomico, merge `COALESCE` D5.b).

Pattern Unit-of-Work: il caller controlla commit/rollback. Questa
funzione esegue solo `INSERT ... ON CONFLICT DO UPDATE` ma NON
chiama `db.commit()`. La logica di commit per-batch vs per-asin
e' caller-side.

Eccezioni propagate:
    - `KeepaRateLimitExceededError` / `KeepaTransientError` (da
      `lookup_products`): fail-fast.
    - `ValueError` (da `build_asin_master_input`): title None e
      fallback assente; fail-fast con asin nel messaggio.
    - `IntegrityError` SQLAlchemy: vincoli DB falliti (es. brand
      vuoto). Caller decide rollback.

`acquire_and_persist([], ...)` ritorna `[]` (no-op).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from talos.extract.asin_master_writer import (
    build_asin_master_input,
    upsert_asin_master,
)
from talos.io_.fallback_chain import lookup_products

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from talos.extract.samsung import SamsungExtractor
    from talos.io_.keepa_client import KeepaClient
    from talos.io_.scraper import AmazonScraper, BrowserPageProtocol


def acquire_and_persist(  # noqa: PLR0913 — orchestratore: 7 hint indipendenti
    asin_list: list[str],
    *,
    db: Session,
    keepa: KeepaClient,
    brand: str,
    enterprise: bool = False,
    scraper: AmazonScraper | None = None,
    page: BrowserPageProtocol | None = None,
    extractor: SamsungExtractor | None = None,
    title_fallbacks: dict[str, str] | None = None,
    category_node: str | None = None,
) -> list[str]:
    """Acquisisce e persiste anagrafica per `asin_list`.

    Per ogni ASIN: `lookup_product` -> (opzionale) `parse_title`
    -> `build_asin_master_input` -> `upsert_asin_master`.

    Il caller gestisce commit/rollback via `session_scope`
    (pattern Unit-of-Work, coerente con `save_session_result`
    CHG-2026-04-30-042).

    Args:
        asin_list: lista ASIN target (anche vuota).
        db: SQLAlchemy `Session` aperta. Caller commits.
        keepa: client Keepa configurato.
        brand: stringa NOT NULL (es. "Samsung"); applicata a
          tutti gli ASIN del batch.
        enterprise: bool, default False; applicato a tutti.
        scraper: AmazonScraper opzionale.
        page: BrowserPageProtocol opzionale, condivisa fra le
          chiamate (riuso context Chromium).
        extractor: SamsungExtractor opzionale. Se fornito e
          `product_data.title` non None, parse_title popola
          `SamsungEntities` per il bridge.
        title_fallbacks: mapping `{asin: title_str}` opzionale.
          Se `product_data.title is None`, viene usato
          `title_fallbacks[asin]` come fallback. Se assente per
          un asin con title None -> `ValueError`.
        category_node: stringa opzionale applicata a tutti gli
          ASIN del batch (mapping Browse Node ad ad-hoc).

    Returns:
        list[str]: ASIN persistiti con successo, in ordine.

    Raises:
        ValueError: title None senza fallback per un ASIN
          (`build_asin_master_input` raise).
        KeepaRateLimitExceededError / KeepaTransientError: rate
          limit / errore transitorio post-retry.
    """
    products = lookup_products(asin_list, keepa=keepa, scraper=scraper, page=page)
    fallbacks = title_fallbacks or {}
    persisted: list[str] = []
    for product_data in products:
        entities = (
            extractor.parse_title(product_data.title)
            if extractor is not None and product_data.title is not None
            else None
        )
        inp = build_asin_master_input(
            product_data,
            brand=brand,
            enterprise=enterprise,
            samsung_entities=entities,
            title_fallback=fallbacks.get(product_data.asin),
            category_node=category_node,
        )
        upsert_asin_master(db, data=inp)
        persisted.append(product_data.asin)
    return persisted
