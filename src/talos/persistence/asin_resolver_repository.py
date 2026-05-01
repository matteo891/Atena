"""Repository `description_resolutions` (CHG-2026-05-01-019, ADR-0015).

Cache descrizione->ASIN per `asin_resolver` (CHG-018). Funzioni:

- `compute_description_hash(description) -> str`: SHA-256 hex (64
  char) di `description.strip().lower()`. Deterministico
  cross-platform. Caller normalizza prima di hashing.
- `find_resolution_by_hash(db, *, tenant_id, description_hash) ->
  DescriptionResolution | None`: lookup tenant-scoped.
- `upsert_resolution(db, *, tenant_id, description_hash, asin,
  confidence_pct) -> int`: UPSERT idempotente con
  `pg_insert.on_conflict_do_update` su UNIQUE
  `(tenant_id, description_hash)`. Refresh `resolved_at = NOW()`.

Pattern Unit-of-Work: il repository NON committa, il caller chiama
via `session_scope()`. Coerente con `save_session_result`,
`set_config_override_*`, `upsert_asin_master`.

Decisioni Leader 2026-05-01 round 4 ratificate (alpha=A NO RLS,
beta=A UNIQUE tenant+hash, gamma=A NO audit). Vedi change doc
CHG-019 per il razionale.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from talos.persistence.models import DescriptionResolution

if TYPE_CHECKING:
    from decimal import Decimal

    from sqlalchemy.orm import Session

DEFAULT_TENANT_ID: int = 1


def compute_description_hash(description: str) -> str:
    """SHA-256 hex (64 char) di `description.strip().lower()`.

    Normalizzazione: trim whitespace + lowercase. Equivalenze:
    - "Galaxy S24" == "galaxy s24" == " galaxy s24 "
    - "Galaxy S24" != "Galaxy S24 256GB" (descrizioni diverse =
      hash diversi, cache miss = re-resolve atteso).

    R-01 NO SILENT DROPS: descrizione vuota -> ValueError esplicito.
    """
    cleaned = description.strip().lower()
    if not cleaned:
        msg = "description vuota / whitespace-only non hashabile"
        raise ValueError(msg)
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def find_resolution_by_hash(
    db: Session,
    *,
    tenant_id: int,
    description_hash: str,
) -> DescriptionResolution | None:
    """Cache lookup tenant-scoped. None se miss (caller fa re-resolve)."""
    stmt = select(DescriptionResolution).where(
        DescriptionResolution.tenant_id == tenant_id,
        DescriptionResolution.description_hash == description_hash,
    )
    return db.execute(stmt).scalar_one_or_none()


def upsert_resolution(
    db: Session,
    *,
    tenant_id: int,
    description_hash: str,
    asin: str,
    confidence_pct: Decimal,
) -> int:
    """Cache write idempotente. Ritorna l'id della riga (insert o update).

    Pattern Postgres-native `pg_insert.on_conflict_do_update` su
    UNIQUE `(tenant_id, description_hash)`. Su conflitto: refresh
    `asin`/`confidence_pct`/`resolved_at = NOW()` (le risoluzioni
    nuove vincono sulle vecchie). Coerente con `upsert_asin_master`
    CHG-005 (D5.a).
    """
    insert_stmt = pg_insert(DescriptionResolution).values(
        tenant_id=tenant_id,
        description_hash=description_hash,
        asin=asin,
        confidence_pct=confidence_pct,
    )
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["tenant_id", "description_hash"],
        set_={
            "asin": insert_stmt.excluded.asin,
            "confidence_pct": insert_stmt.excluded.confidence_pct,
            "resolved_at": insert_stmt.excluded.resolved_at,
        },
    ).returning(DescriptionResolution.id)
    result = db.execute(upsert_stmt)
    row_id = result.scalar_one()
    return int(row_id)
