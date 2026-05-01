"""asin_master writer — UPSERT merge no-audit (ADR-0017 + ADR-0015).

CHG-2026-05-01-005. Decisioni di design (D5 ratificata "default" Leader
2026-04-30 sera, memory `project_io_extract_design_decisions.md`):

- D5.a UPSERT: A = `INSERT ... ON CONFLICT (asin) DO UPDATE`
  (Postgres-native, atomico).
- D5.b Conflict resolution: C = merge (input non-null vince,
  null preserva valori esistenti via `COALESCE(EXCLUDED.field,
  asin_master.field)`).
- D5.c Audit trigger: B = NO trigger su `asin_master`
  (anagrafica relativamente stabile, audit costoso e poco
  informativo).

Il writer e' invocato dalla fallback chain (CHG futuro): a valle
di `KeepaClient.fetch_*` / `AmazonScraper.scrape_product` /
`SamsungExtractor.parse_title`, popola/aggiorna l'anagrafica per
ogni ASIN risolto.

`title` e `brand` sono campi obbligatori (NOT NULL nel modello);
sempre overwrite. `enterprise` e' bool NOT NULL: il caller decide
esplicitamente true/false. Tutti gli altri campi sono opzionali
e usano la merge `COALESCE`. `last_seen_at` e' sempre aggiornato
a `NOW()` (refresh dell'anagrafica).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from talos.persistence.models.asin_master import AsinMaster

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from talos.extract.samsung import SamsungEntities
    from talos.io_.fallback_chain import ProductData


@dataclass(frozen=True)
class AsinMasterInput:
    """Input per `upsert_asin_master`.

    `asin`/`title`/`brand`/`enterprise` sono obbligatori (mappano
    su NOT NULL). Gli altri sono opzionali: se `None` in update,
    il valore esistente e' preservato (D5.b merge).
    """

    asin: str
    title: str
    brand: str
    enterprise: bool = False
    model: str | None = None
    rom_gb: int | None = None
    ram_gb: int | None = None
    connectivity: str | None = None
    color_family: str | None = None
    category_node: str | None = None


def upsert_asin_master(db: Session, *, data: AsinMasterInput) -> str:
    """UPSERT su `asin_master` con merge `COALESCE` per i campi nullable.

    Pattern (D5.a + D5.b):

        INSERT INTO asin_master (asin, title, brand, ...)
        VALUES (...)
        ON CONFLICT (asin) DO UPDATE SET
            title = EXCLUDED.title,
            brand = EXCLUDED.brand,
            enterprise = EXCLUDED.enterprise,
            model = COALESCE(EXCLUDED.model, asin_master.model),
            ...
            last_seen_at = NOW();

    `last_seen_at` viene sempre aggiornato a `NOW()` (refresh
    timestamp anagrafica). Il caller deve fare il commit/rollback
    via `session_scope` (Unit of Work, pattern coerente con
    `save_session_result`).

    Returns:
        L'ASIN inserito/aggiornato (per consistenza con il caller).
    """
    stmt = pg_insert(AsinMaster).values(
        asin=data.asin,
        title=data.title,
        brand=data.brand,
        enterprise=data.enterprise,
        model=data.model,
        rom_gb=data.rom_gb,
        ram_gb=data.ram_gb,
        connectivity=data.connectivity,
        color_family=data.color_family,
        category_node=data.category_node,
    )
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        index_elements=[AsinMaster.asin],
        set_={
            # Field NOT NULL: sempre overwrite (input vince).
            "title": excluded.title,
            "brand": excluded.brand,
            "enterprise": excluded.enterprise,
            # Field nullable: merge — input non-null vince, null preserva esistente.
            "model": func.coalesce(excluded.model, AsinMaster.model),
            "rom_gb": func.coalesce(excluded.rom_gb, AsinMaster.rom_gb),
            "ram_gb": func.coalesce(excluded.ram_gb, AsinMaster.ram_gb),
            "connectivity": func.coalesce(excluded.connectivity, AsinMaster.connectivity),
            "color_family": func.coalesce(excluded.color_family, AsinMaster.color_family),
            "category_node": func.coalesce(excluded.category_node, AsinMaster.category_node),
            # last_seen_at sempre refresh.
            "last_seen_at": func.now(),
        },
    )
    db.execute(stmt)
    return data.asin


def build_asin_master_input(  # noqa: PLR0913 — bridge-by-design: caller fornisce
    # 5 hint indipendenti (brand, enterprise, samsung_entities, title_fallback,
    # category_node) sopra il `product_data` posizionale; raggruppare in un
    # dataclass intermedio creerebbe solo un wrapper inerte.
    product_data: ProductData,
    *,
    brand: str,
    enterprise: bool = False,
    samsung_entities: SamsungEntities | None = None,
    title_fallback: str | None = None,
    category_node: str | None = None,
) -> AsinMasterInput:
    """Costruisce un `AsinMasterInput` componendo `ProductData` + entita' brand.

    Bridge architetturale CHG-2026-05-01-008 fra il lato `io_/` (output
    di `lookup_product`) e il lato writer (`upsert_asin_master`).

    Mapping:
        - `asin` <- `product_data.asin`
        - `title` <- `product_data.title` se non None, altrimenti
          `title_fallback`. Se entrambi None solleva `ValueError`
          (R-01 NO SILENT DROPS: `AsinMaster.title` e' NOT NULL,
          il bridge non inventa stringhe vuote).
        - `brand`, `enterprise`, `category_node` <- parametri caller
          (non derivabili da `ProductData` ne' dal `KeepaProduct` /
          `ScrapedProduct` correnti).
        - `model`, `rom_gb`, `ram_gb`, `connectivity`,
          `color_family` <- da `samsung_entities` se fornito (output
          `SamsungExtractor.parse_title`); altrimenti `None` (la
          merge `COALESCE` di `upsert_asin_master` D5.b preserva
          eventuali valori esistenti).

    Note di design:
        - `samsung_entities.color` -> `AsinMasterInput.color_family`:
          mapping diretto (es. "Titanium Black"). La distinzione
          color/color_family e' un dettaglio del modello DB; il
          test integration in CHG-005 documenta il pattern.
        - `enterprise` di `samsung_entities` (se fornito)
          attualmente NON viene letto: prevale il parametro
          esplicito `enterprise` del bridge. Razionale: il caller
          (CFO o integratore Fase 3) lo conosce dal listino
          fornitore, non dal titolo Amazon. Caller che vogliono
          pre-popolare via NLP devono passarlo esplicitamente.
        - `category_node` non e' mai derivato qui (richiede
          mapping Amazon Browse Node al sistema interno; scope
          futuro).

    Args:
        product_data: output di `lookup_product` (CHG-006).
        brand: stringa NOT NULL, fornita dal caller (es. "Samsung").
        enterprise: bool, default False.
        samsung_entities: opzionale, output di
          `SamsungExtractor.parse_title(scraped_title)`.
        title_fallback: stringa da usare se `product_data.title is
          None`. Se entrambi None -> `ValueError`.
        category_node: opzionale, per popolazione futura.

    Returns:
        AsinMasterInput pronto per essere passato a
        `upsert_asin_master(db, data=...)`.

    Raises:
        ValueError: `product_data.title is None` e
          `title_fallback is None` (vincolo NOT NULL su
          `AsinMaster.title`).
    """
    title = product_data.title if product_data.title is not None else title_fallback
    if title is None:
        msg = (
            f"build_asin_master_input: title is None for asin={product_data.asin!r} "
            "and no title_fallback provided. AsinMaster.title is NOT NULL."
        )
        raise ValueError(msg)
    return AsinMasterInput(
        asin=product_data.asin,
        title=title,
        brand=brand,
        enterprise=enterprise,
        model=samsung_entities.model if samsung_entities is not None else None,
        rom_gb=samsung_entities.rom_gb if samsung_entities is not None else None,
        ram_gb=samsung_entities.ram_gb if samsung_entities is not None else None,
        connectivity=samsung_entities.connectivity if samsung_entities is not None else None,
        color_family=samsung_entities.color if samsung_entities is not None else None,
        category_node=category_node,
    )
