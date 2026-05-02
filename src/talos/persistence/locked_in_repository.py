"""Repository `locked_in` (R-04 Manual Override) — CHG-2026-05-02-019.

ASIN che il CFO vuole **permanentemente** forzati nel carrello a Priorità ∞,
ortogonale al text_input transient della UI (sessione-singola). A run-time
il flow Demetra carica gli ASIN da DB + quelli typati al volo, fa l'unione,
li passa al Tetris allocator (R-04).

CRUD minimal: add (insert), list (read all per tenant), delete (by id).
RLS Zero-Trust attiva via `with_tenant`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal  # noqa: F401 — coerenza con altri repository
from typing import TYPE_CHECKING

from sqlalchemy import select

from talos.persistence.models import LockedInItem
from talos.persistence.session import with_tenant

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class LockedInSummary:
    """Riga locked_in per UI/list."""

    id: int
    asin: str
    qty_min: int
    notes: str | None
    created_at: datetime


def add_locked_in(
    db: Session,
    *,
    asin: str,
    qty_min: int,
    notes: str | None = None,
    tenant_id: int = 1,
) -> int:
    """Inserisce ASIN locked-in. Ritorna `id` riga creata.

    :raises ValueError: asin con lunghezza !=10 o qty_min<=0.
    """
    asin_clean = asin.strip().upper()
    expected_asin_len = 10
    if len(asin_clean) != expected_asin_len:
        msg = f"asin invalido (deve essere 10 chars): {asin_clean!r}"
        raise ValueError(msg)
    if qty_min <= 0:
        msg = f"qty_min deve essere > 0 (ricevuto {qty_min})"
        raise ValueError(msg)
    with with_tenant(db, tenant_id):
        item = LockedInItem(
            asin=asin_clean,
            qty_min=qty_min,
            notes=notes,
            tenant_id=tenant_id,
        )
        db.add(item)
        db.flush()
        return int(item.id)


def list_locked_in(db: Session, *, tenant_id: int = 1) -> list[LockedInSummary]:
    """Lista tutti i locked_in del tenant, ordinati per `created_at` DESC."""
    with with_tenant(db, tenant_id):
        rows = db.execute(
            select(
                LockedInItem.id,
                LockedInItem.asin,
                LockedInItem.qty_min,
                LockedInItem.notes,
                LockedInItem.created_at,
            )
            .where(LockedInItem.tenant_id == tenant_id)
            .order_by(LockedInItem.created_at.desc(), LockedInItem.id.desc()),
        ).all()
    return [
        LockedInSummary(
            id=int(r[0]),
            asin=str(r[1]).strip(),
            qty_min=int(r[2]),
            notes=str(r[3]) if r[3] is not None else None,
            created_at=r[4],
        )
        for r in rows
    ]


def list_locked_in_asins(db: Session, *, tenant_id: int = 1) -> list[str]:
    """Helper: solo gli ASIN (per `SessionInput.locked_in`)."""
    return [item.asin for item in list_locked_in(db, tenant_id=tenant_id)]


def delete_locked_in(db: Session, *, item_id: int, tenant_id: int = 1) -> bool:
    """Cancella riga locked_in. Ritorna True se trovata + cancellata."""
    with with_tenant(db, tenant_id):
        existing = db.execute(
            select(LockedInItem)
            .where(LockedInItem.id == item_id, LockedInItem.tenant_id == tenant_id)
            .limit(1),
        ).scalar_one_or_none()
        if existing is None:
            return False
        db.delete(existing)
        db.flush()
        return True
