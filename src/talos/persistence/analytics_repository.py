"""Aggregate analytics — KPI storici multi-sessione (CHG-2026-05-02-021).

Helper per dashboard Demetra: riepiloghi cross-session per il CFO.
Pattern read-only su `storico_ordini` + join `vgp_results` per ROI medio.
RLS Zero-Trust via `with_tenant`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import distinct, func, select, text

from talos.persistence.models import StoricoOrdine
from talos.persistence.session import with_tenant

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class OrdersAggregateSummary:
    """KPI aggregati storico ordini per il CFO (last N days)."""

    days_window: int
    n_sessions: int
    n_orders: int
    total_qty: int
    total_eur: Decimal
    avg_roi: float | None  # weighted average; None se 0 ordini


@dataclass(frozen=True)
class AsinAggregate:
    """Riepilogo cumulativo per ASIN (top by qty)."""

    asin: str
    n_orders: int
    total_qty: int
    total_eur: Decimal


def aggregate_orders_last_days(
    db: Session,
    *,
    days: int = 30,
    tenant_id: int = 1,
) -> OrdersAggregateSummary:
    """KPI storico ordini ultimi N giorni del tenant.

    :raises ValueError: `days <= 0`.
    """
    if days <= 0:
        msg = f"days deve essere > 0 (ricevuto {days})"
        raise ValueError(msg)
    days_int = int(days)  # safe: int validato
    # Postgres INTERVAL non accetta bind parameter; interpolazione diretta su
    # int validato (no SQL injection: days_int è sicuro).
    interval_sql = text(f"NOW() - INTERVAL '{days_int} days'")
    with with_tenant(db, tenant_id):
        # Sessioni distinte + ordini + qty + total cost (in 1 query).
        agg = db.execute(
            select(
                func.count(distinct(StoricoOrdine.session_id)),
                func.count(StoricoOrdine.id),
                func.coalesce(func.sum(StoricoOrdine.qty), 0),
                func.coalesce(
                    func.sum(StoricoOrdine.qty * StoricoOrdine.unit_cost_eur),
                    0,
                ),
            ).where(
                StoricoOrdine.tenant_id == tenant_id,
                StoricoOrdine.ordered_at >= interval_sql,
            ),
        ).one()
        n_sessions = int(agg[0])
        n_orders = int(agg[1])
        total_qty = int(agg[2])
        total_eur = Decimal(agg[3])

        # ROI medio: weighted by qty (join via cart_item → vgp_result).
        # `days_int` è int validato a monte: f-string sicura (no injection).
        sql_roi = f"SELECT SUM(so.qty * vr.roi_pct) AS num, SUM(so.qty) AS den FROM storico_ordini so JOIN cart_items ci ON ci.id = so.cart_item_id JOIN vgp_results vr ON vr.id = ci.vgp_result_id WHERE so.tenant_id = :tid AND so.ordered_at >= NOW() - INTERVAL '{days_int} days'"  # noqa: E501, S608
        roi_agg = db.execute(text(sql_roi).bindparams(tid=tenant_id)).one()
        avg_roi: float | None = None
        if roi_agg.den and int(roi_agg.den) > 0 and roi_agg.num is not None:
            avg_roi = float(roi_agg.num) / float(roi_agg.den)

    return OrdersAggregateSummary(
        days_window=days,
        n_sessions=n_sessions,
        n_orders=n_orders,
        total_qty=total_qty,
        total_eur=total_eur,
        avg_roi=avg_roi,
    )


def top_asins_by_total_qty(
    db: Session,
    *,
    limit: int = 10,
    tenant_id: int = 1,
) -> list[AsinAggregate]:
    """Top N ASIN per qty cumulata (across sessions). Ordinato qty DESC."""
    if limit <= 0:
        msg = f"limit deve essere > 0 (ricevuto {limit})"
        raise ValueError(msg)
    with with_tenant(db, tenant_id):
        rows = db.execute(
            select(
                StoricoOrdine.asin,
                func.count(StoricoOrdine.id),
                func.sum(StoricoOrdine.qty),
                func.sum(StoricoOrdine.qty * StoricoOrdine.unit_cost_eur),
            )
            .where(StoricoOrdine.tenant_id == tenant_id)
            .group_by(StoricoOrdine.asin)
            .order_by(func.sum(StoricoOrdine.qty).desc())
            .limit(limit),
        ).all()
    return [
        AsinAggregate(
            asin=str(r[0]).strip(),
            n_orders=int(r[1]),
            total_qty=int(r[2]),
            total_eur=Decimal(r[3]),
        )
        for r in rows
    ]
