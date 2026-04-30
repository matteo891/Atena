"""Integration test per `list_recent_sessions` + `fetch_recent_sessions_or_empty`.

CHG-2026-04-30-044. Verifica:
1. Lista vuota se nessuna sessione del tenant.
2. Sessioni inserite con `save_session_result` ricompaiono nella lista.
3. Ordine `started_at` DESC.
4. `n_cart_items` e `n_panchina_items` corretti.
5. `tenant_id` filter isola correttamente i tenant.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.persistence import (
    SessionSummary,
    list_recent_sessions,
    save_session_result,
)
from talos.ui.dashboard import fetch_recent_sessions_or_empty

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine


pytestmark = pytest.mark.integration


@pytest.fixture
def orm_session(pg_engine: Engine) -> Iterator[Session]:
    """Session ORM con rollback finale (test isolation)."""
    factory = sessionmaker(bind=pg_engine, future=True, expire_on_commit=False)
    sess = factory()
    try:
        yield sess
    finally:
        sess.rollback()
        sess.close()


def _samsung_listino(asin_prefix: str = "L") -> pd.DataFrame:
    """Mini-listino realistic 3 ASIN; prefix per generare hash diversi."""
    return pd.DataFrame(
        [
            (f"{asin_prefix}001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            (f"{asin_prefix}002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
            (f"{asin_prefix}003", 250.0, 240.0, 0.08, 25.0, 1, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def _save_one_session(orm_session: Session, *, asin_prefix: str, tenant_id: int = 1) -> int:
    """Helper: esegue + persiste una sessione, ritorna sid."""
    inp = SessionInput(listino_raw=_samsung_listino(asin_prefix), budget=2000.0)
    result = run_session(inp)
    return save_session_result(
        orm_session,
        session_input=inp,
        result=result,
        tenant_id=tenant_id,
    )


def test_list_returns_empty_for_unused_tenant(orm_session: Session) -> None:
    """Tenant senza sessioni -> lista vuota."""
    summaries = list_recent_sessions(orm_session, tenant_id=999)
    assert summaries == []


def test_list_returns_session_summary_after_save(orm_session: Session) -> None:
    """Sessione salvata -> appare in lista."""
    sid = _save_one_session(orm_session, asin_prefix="A")
    summaries = list_recent_sessions(orm_session, tenant_id=1, limit=50)

    assert len(summaries) >= 1
    s = next(s for s in summaries if s.id == sid)
    assert isinstance(s, SessionSummary)
    assert s.budget_eur == Decimal("2000.0")
    assert s.velocity_target == 15
    assert len(s.listino_hash) == 64
    assert s.n_cart_items >= 0
    assert s.n_panchina_items >= 0
    assert isinstance(s.started_at, datetime)


def test_list_orders_by_started_at_desc(orm_session: Session) -> None:
    """Ordine DESC su started_at: l'ultima salvata appare per prima."""
    sid_a = _save_one_session(orm_session, asin_prefix="X")
    sid_b = _save_one_session(orm_session, asin_prefix="Y")

    summaries = list_recent_sessions(orm_session, tenant_id=1, limit=50)
    ids_in_order = [s.id for s in summaries if s.id in (sid_a, sid_b)]
    # sid_b e' stata creata DOPO sid_a -> deve apparire prima
    assert ids_in_order == [sid_b, sid_a]


def test_list_respects_limit(orm_session: Session) -> None:
    """`limit` cap il numero di righe ritornate."""
    for i in range(3):
        _save_one_session(orm_session, asin_prefix=f"L{i}")

    summaries = list_recent_sessions(orm_session, tenant_id=1, limit=2)
    assert len(summaries) == 2


def test_list_invalid_limit_raises(orm_session: Session) -> None:
    """`limit <= 0` -> ValueError."""
    with pytest.raises(ValueError, match="limit"):
        list_recent_sessions(orm_session, tenant_id=1, limit=0)
    with pytest.raises(ValueError, match="limit"):
        list_recent_sessions(orm_session, tenant_id=1, limit=-5)


def test_list_filters_by_tenant_id(orm_session: Session) -> None:
    """Sessioni di tenant_id=1 NON appaiono in tenant_id=2."""
    sid_t1 = _save_one_session(orm_session, asin_prefix="T1", tenant_id=1)
    sid_t2 = _save_one_session(orm_session, asin_prefix="T2", tenant_id=2)

    only_t1 = list_recent_sessions(orm_session, tenant_id=1, limit=50)
    only_t2 = list_recent_sessions(orm_session, tenant_id=2, limit=50)

    ids_t1 = {s.id for s in only_t1}
    ids_t2 = {s.id for s in only_t2}
    assert sid_t1 in ids_t1
    assert sid_t1 not in ids_t2
    assert sid_t2 in ids_t2
    assert sid_t2 not in ids_t1


def test_list_n_cart_items_matches_actual_count(orm_session: Session) -> None:
    """Il count `n_cart_items` aggregato coincide con il numero reale."""
    inp = SessionInput(listino_raw=_samsung_listino("Z"), budget=10000.0)
    result = run_session(inp)
    sid = save_session_result(
        orm_session,
        session_input=inp,
        result=result,
        tenant_id=1,
    )

    summaries = list_recent_sessions(orm_session, tenant_id=1, limit=50)
    s = next(s for s in summaries if s.id == sid)
    assert s.n_cart_items == len(result.cart.items)
    assert s.n_panchina_items == len(result.panchina)


def test_fetch_recent_sessions_or_empty_returns_dicts(pg_engine) -> None:  # noqa: ARG001
    """Helper UI: ritorna list-of-dict utilizzabile da `pd.DataFrame`."""
    from talos.ui.dashboard import get_session_factory_or_none  # noqa: PLC0415

    factory = get_session_factory_or_none()
    assert factory is not None

    rows = fetch_recent_sessions_or_empty(factory, limit=5, tenant_id=1)
    assert isinstance(rows, list)
    if rows:
        first = rows[0]
        assert "id" in first
        assert "started_at" in first
        assert "budget_eur" in first
        assert "n_cart" in first
        assert "n_panchina" in first
        assert "hash" in first
