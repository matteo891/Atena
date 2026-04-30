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
