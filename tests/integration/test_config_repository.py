"""Integration test per `config_repository` (CHG-2026-04-30-050).

Verifica:
- get_config_override_numeric ritorna None se assente.
- set_config_override_numeric persiste il valore.
- UPSERT: secondo set sostituisce il valore esistente (no IntegrityError).
- Filtro tenant_id isola sessioni.
- Scope invalido → ValueError.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.orm import Session, sessionmaker

from talos.persistence import (
    SCOPE_GLOBAL,
    get_config_override_numeric,
    set_config_override_numeric,
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


def test_get_returns_none_for_missing_key(orm_session: Session) -> None:
    """Chiave non presente → None."""
    val = get_config_override_numeric(orm_session, key="nonexistent_key", tenant_id=1)
    assert val is None


def test_set_then_get_roundtrip(orm_session: Session) -> None:
    """SET di un valore numerico → GET ritorna lo stesso valore."""
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=Decimal("0.10"),
        tenant_id=1,
    )
    orm_session.flush()

    val = get_config_override_numeric(orm_session, key="veto_roi_pct", tenant_id=1)
    assert val == Decimal("0.1000")


def test_upsert_overwrites_existing_value(orm_session: Session) -> None:
    """SET due volte sulla stessa chiave → secondo valore sovrascrive il primo."""
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=0.08,
        tenant_id=1,
    )
    orm_session.flush()
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=0.15,
        tenant_id=1,
    )
    orm_session.flush()

    val = get_config_override_numeric(orm_session, key="veto_roi_pct", tenant_id=1)
    assert val == Decimal("0.1500")


def test_filters_by_tenant_id(orm_session: Session) -> None:
    """Tenant 1 e tenant 2 hanno spazi di config indipendenti."""
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=0.10,
        tenant_id=1,
    )
    set_config_override_numeric(
        orm_session,
        key="veto_roi_pct",
        value=0.20,
        tenant_id=2,
    )
    orm_session.flush()

    v1 = get_config_override_numeric(orm_session, key="veto_roi_pct", tenant_id=1)
    v2 = get_config_override_numeric(orm_session, key="veto_roi_pct", tenant_id=2)
    assert v1 == Decimal("0.1000")
    assert v2 == Decimal("0.2000")


def test_set_with_float_converts_to_decimal(orm_session: Session) -> None:
    """`value: float` accettato ma convertito a `Decimal(str(value))` (no drift)."""
    set_config_override_numeric(
        orm_session,
        key="float_to_decimal",
        value=0.123456789,
        tenant_id=1,
    )
    orm_session.flush()

    val = get_config_override_numeric(orm_session, key="float_to_decimal", tenant_id=1)
    # Numeric(12, 4) → 4 decimali (truncato da Postgres).
    assert val == Decimal("0.1235")


def test_invalid_scope_raises(orm_session: Session) -> None:
    """Scope non in {global, category, asin} → ValueError."""
    with pytest.raises(ValueError, match="scope"):
        get_config_override_numeric(orm_session, key="x", scope="bad_scope")
    with pytest.raises(ValueError, match="scope"):
        set_config_override_numeric(orm_session, key="x", value=1.0, scope="bad_scope")


def test_scope_global_default(orm_session: Session) -> None:
    """Default scope=`global`, scope_key=None."""
    set_config_override_numeric(orm_session, key="default_scope_test", value=42.0, tenant_id=1)
    orm_session.flush()

    val = get_config_override_numeric(
        orm_session,
        key="default_scope_test",
        tenant_id=1,
        scope=SCOPE_GLOBAL,
        scope_key=None,
    )
    assert val == Decimal("42.0000")
