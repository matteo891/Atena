"""Repository `storico_ordini` (R-03 ORDER-DRIVEN MEMORY) — CHG-2026-05-02-017.

Sblocca il flow CFO end-to-end: sessione salvata → bottone "Conferma
ordini → registro" → riga in `storico_ordini` per ogni `cart_item`.
Lo storico è registro permanente (no CASCADE su FK, RLS Zero-Trust attiva).

Pattern idempotente: se la sessione ha già storico ordini, `record_orders_from_session`
è no-op (ritorna 0). Coerente con R-03: una sessione genera ordini una sola
volta. Decisione di "ri-ordinare" → nuova sessione (replay/duplicate UX).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import func, select

from talos.persistence.models import CartItem, StoricoOrdine, VgpResult
from talos.persistence.session import with_tenant

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class OrderSummary:
    """Riga riassuntiva storico_ordini per UI/export CSV (CHG-017)."""

    id: int
    session_id: int
    cart_item_id: int
    asin: str
    qty: int
    unit_cost_eur: Decimal
    total_cost_eur: Decimal
    ordered_at: datetime


def count_orders_for_session(
    db: Session,
    *,
    session_id: int,
    tenant_id: int = 1,
) -> int:
    """Conta `storico_ordini` per la sessione + tenant. Per idempotenza."""
    with with_tenant(db, tenant_id):
        result = db.execute(
            select(func.count())
            .select_from(StoricoOrdine)
            .where(
                StoricoOrdine.session_id == session_id,
                StoricoOrdine.tenant_id == tenant_id,
            ),
        ).scalar_one()
        return int(result)


def record_orders_from_session(
    db: Session,
    *,
    session_id: int,
    tenant_id: int = 1,
) -> int:
    """Inserisce `storico_ordini` per ogni `cart_item` della sessione.

    Pattern idempotente: se esiste già almeno una riga di storico per questa
    sessione, ritorna 0 (no-op). Caller può distinguere "registrato ora N"
    vs "già registrato in passato" tramite il return value.

    :returns: numero righe storico inserite. `0` se già confermato in passato.
    """
    with with_tenant(db, tenant_id):
        existing = db.execute(
            select(func.count())
            .select_from(StoricoOrdine)
            .where(
                StoricoOrdine.session_id == session_id,
                StoricoOrdine.tenant_id == tenant_id,
            ),
        ).scalar_one()
        if int(existing) > 0:
            return 0

        cart_rows = db.execute(
            select(
                CartItem.id,
                CartItem.qty,
                CartItem.unit_cost_eur,
                VgpResult.asin,
            )
            .join(VgpResult, CartItem.vgp_result_id == VgpResult.id)
            .where(CartItem.session_id == session_id),
        ).all()

        for cart_item_id, qty, unit_cost, asin in cart_rows:
            ordine = StoricoOrdine(
                session_id=session_id,
                cart_item_id=cart_item_id,
                asin=asin,
                qty=qty,
                unit_cost_eur=unit_cost,
                tenant_id=tenant_id,
            )
            db.add(ordine)
        db.flush()
        return len(cart_rows)


def list_recent_orders(
    db: Session,
    *,
    limit: int = 50,
    tenant_id: int = 1,
) -> list[OrderSummary]:
    """Lista ultimi `limit` ordini del tenant, ordinati per `ordered_at` DESC.

    :returns: lista di `OrderSummary` (vuota se nessun ordine).
    """
    if limit <= 0:
        msg = f"limit deve essere > 0 (ricevuto {limit})"
        raise ValueError(msg)
    with with_tenant(db, tenant_id):
        rows = db.execute(
            select(
                StoricoOrdine.id,
                StoricoOrdine.session_id,
                StoricoOrdine.cart_item_id,
                StoricoOrdine.asin,
                StoricoOrdine.qty,
                StoricoOrdine.unit_cost_eur,
                StoricoOrdine.ordered_at,
            )
            .where(StoricoOrdine.tenant_id == tenant_id)
            .order_by(StoricoOrdine.ordered_at.desc(), StoricoOrdine.id.desc())
            .limit(limit),
        ).all()
    return [
        OrderSummary(
            id=int(r[0]),
            session_id=int(r[1]),
            cart_item_id=int(r[2]),
            asin=str(r[3]).strip(),
            qty=int(r[4]),
            unit_cost_eur=Decimal(r[5]),
            total_cost_eur=Decimal(r[5]) * int(r[4]),
            ordered_at=r[6],
        )
        for r in rows
    ]
