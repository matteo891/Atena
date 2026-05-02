"""Integration test `analytics_repository` (CHG-2026-05-02-021)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.persistence import (
    aggregate_orders_last_days,
    record_orders_from_session,
    save_session_result,
    top_asins_by_total_qty,
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


def _seed_session_with_orders(orm_session: Session) -> int:
    listino = pd.DataFrame(
        [
            ("AGG0000001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("AGG0000002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )
    inp = SessionInput(listino_raw=listino, budget=20_000.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result, tenant_id=1)
    orm_session.flush()
    record_orders_from_session(orm_session, session_id=sid)
    return sid


def test_aggregate_zero_initially(orm_session: Session) -> None:
    s = aggregate_orders_last_days(orm_session, days=30, tenant_id=1)
    assert s.n_sessions == 0
    assert s.n_orders == 0
    assert s.total_qty == 0
    assert float(s.total_eur) == 0.0
    assert s.avg_roi is None


def test_aggregate_after_seed(orm_session: Session) -> None:
    _seed_session_with_orders(orm_session)
    s = aggregate_orders_last_days(orm_session, days=30, tenant_id=1)
    assert s.n_sessions == 1
    assert s.n_orders >= 1
    assert s.total_qty > 0
    assert float(s.total_eur) > 0
    assert s.avg_roi is None or isinstance(s.avg_roi, float)


def test_aggregate_invalid_days_raises(orm_session: Session) -> None:
    with pytest.raises(ValueError, match="days"):
        aggregate_orders_last_days(orm_session, days=0, tenant_id=1)


def test_top_asins_empty_initially(orm_session: Session) -> None:
    assert top_asins_by_total_qty(orm_session, limit=10, tenant_id=1) == []


def test_top_asins_after_seed(orm_session: Session) -> None:
    _seed_session_with_orders(orm_session)
    asins = top_asins_by_total_qty(orm_session, limit=10, tenant_id=1)
    assert len(asins) >= 1
    assert asins[0].total_qty >= asins[-1].total_qty
    assert all(a.total_qty > 0 for a in asins)


def test_top_asins_invalid_limit_raises(orm_session: Session) -> None:
    with pytest.raises(ValueError, match="limit"):
        top_asins_by_total_qty(orm_session, limit=0, tenant_id=1)
