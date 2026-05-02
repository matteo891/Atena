"""Integration test `locked_in_repository` (CHG-2026-05-02-019)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.persistence import (
    LockedInSummary,
    add_locked_in,
    delete_locked_in,
    list_locked_in,
    list_locked_in_asins,
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


def test_list_empty_initially(orm_session: Session) -> None:
    assert list_locked_in(orm_session, tenant_id=1) == []
    assert list_locked_in_asins(orm_session, tenant_id=1) == []


def test_add_then_list(orm_session: Session) -> None:
    add_locked_in(
        orm_session,
        asin="B0CSTC2RDW",
        qty_min=5,
        notes="Strategic flagship",
        tenant_id=1,
    )
    items = list_locked_in(orm_session, tenant_id=1)
    assert len(items) == 1
    assert isinstance(items[0], LockedInSummary)
    assert items[0].asin == "B0CSTC2RDW"
    assert items[0].qty_min == 5
    assert items[0].notes == "Strategic flagship"


def test_add_normalizes_uppercase(orm_session: Session) -> None:
    add_locked_in(orm_session, asin="b0cstc2rdw", qty_min=1, tenant_id=1)
    items = list_locked_in(orm_session, tenant_id=1)
    assert items[0].asin == "B0CSTC2RDW"


def test_add_invalid_asin_length_raises(orm_session: Session) -> None:
    with pytest.raises(ValueError, match="asin"):
        add_locked_in(orm_session, asin="TOO_SHORT", qty_min=1, tenant_id=1)


def test_add_invalid_qty_min_raises(orm_session: Session) -> None:
    with pytest.raises(ValueError, match="qty_min"):
        add_locked_in(orm_session, asin="B0CSTC2RDW", qty_min=0, tenant_id=1)


def test_delete_returns_true_when_found(orm_session: Session) -> None:
    item_id = add_locked_in(orm_session, asin="B0CSTC2RDW", qty_min=1, tenant_id=1)
    assert delete_locked_in(orm_session, item_id=item_id, tenant_id=1) is True
    assert list_locked_in(orm_session, tenant_id=1) == []


def test_delete_returns_false_when_not_found(orm_session: Session) -> None:
    assert delete_locked_in(orm_session, item_id=999_999, tenant_id=1) is False


def test_list_locked_in_asins_helper(orm_session: Session) -> None:
    add_locked_in(orm_session, asin="B0CSTC2RDW", qty_min=1, tenant_id=1)
    add_locked_in(orm_session, asin="B0BLP2GS6K", qty_min=2, tenant_id=1)
    asins = list_locked_in_asins(orm_session, tenant_id=1)
    assert set(asins) == {"B0CSTC2RDW", "B0BLP2GS6K"}
