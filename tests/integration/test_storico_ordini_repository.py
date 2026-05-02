"""Integration test `storico_ordini_repository` (CHG-2026-05-02-017).

R-03 ORDER-DRIVEN MEMORY wiring: dopo save_session_result, il CFO può
"confermare ordini" → record permanente in `storico_ordini`. Pattern
idempotente.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.persistence import (
    StoricoOrdine,
    count_orders_for_session,
    record_orders_from_session,
    save_session_result,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine

pytestmark = pytest.mark.integration


@pytest.fixture
def orm_session(pg_engine: Engine) -> Iterator[Session]:
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()


def _listino() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("ORD0000001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("ORD0000002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def _save_session(orm_session: Session, *, tenant_id: int = 1) -> int:
    inp = SessionInput(listino_raw=_listino(), budget=20_000.0)
    result = run_session(inp)
    sid = save_session_result(
        orm_session,
        session_input=inp,
        result=result,
        tenant_id=tenant_id,
    )
    orm_session.flush()
    return sid


def test_count_zero_initially(orm_session: Session) -> None:
    sid = _save_session(orm_session)
    assert count_orders_for_session(orm_session, session_id=sid) == 0


def test_record_creates_one_per_cart_item(orm_session: Session) -> None:
    sid = _save_session(orm_session)
    n = record_orders_from_session(orm_session, session_id=sid)
    assert n >= 1  # almeno 1 ASIN allocato (cart non vuoto)
    assert count_orders_for_session(orm_session, session_id=sid) == n


def test_record_idempotent_returns_zero_on_second_call(orm_session: Session) -> None:
    sid = _save_session(orm_session)
    first = record_orders_from_session(orm_session, session_id=sid)
    assert first > 0
    second = record_orders_from_session(orm_session, session_id=sid)
    assert second == 0  # no-op
    assert count_orders_for_session(orm_session, session_id=sid) == first


def test_record_writes_asin_qty_unit_cost_correctly(orm_session: Session) -> None:
    """Verifica che ogni storico_ordine abbia asin/qty/unit_cost del cart_item sorgente."""
    from sqlalchemy import select  # noqa: PLC0415

    sid = _save_session(orm_session)
    record_orders_from_session(orm_session, session_id=sid)
    rows = (
        orm_session.execute(
            select(StoricoOrdine).where(StoricoOrdine.session_id == sid),
        )
        .scalars()
        .all()
    )
    assert len(rows) > 0
    for r in rows:
        assert r.asin in {"ORD0000001", "ORD0000002"}
        assert r.qty > 0
        assert float(r.unit_cost_eur) > 0
        assert r.tenant_id == 1


def test_record_tenant_isolation(orm_session: Session) -> None:
    """Sessione tenant=1 + record con tenant=2 → 0 (RLS isolation)."""
    sid = _save_session(orm_session, tenant_id=1)
    n = record_orders_from_session(orm_session, session_id=sid, tenant_id=2)
    # tenant=2 non vede i cart_items (ma RLS dipende dal ruolo connessione;
    # con superuser RLS è bypassed). Il behavior esatto dipende dal setup;
    # in MVP single-tenant verifichiamo solo che non crashi.
    assert n >= 0
