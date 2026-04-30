"""Integration test per `find_session_by_hash` + UNIQUE INDEX (CHG-2026-04-30-047).

Verifica:
- `find_session_by_hash` ritorna `None` se nessuna sessione del tenant ha quel hash.
- Dopo `save_session_result`, `find_session_by_hash` ritorna `SessionSummary` corretto.
- UNIQUE INDEX `(tenant_id, listino_hash)` blocca insert duplicate (raise IntegrityError).
- Tenant diversi ammessi anche con stesso hash.
- `listino_hash` malformato → ValueError.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from talos.orchestrator import REQUIRED_INPUT_COLUMNS, SessionInput, run_session
from talos.persistence import (
    SessionSummary,
    find_session_by_hash,
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


def _samsung_listino() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("FH001", 1000.0, 600.0, 0.08, 60.0, 1, "MATCH"),
            ("FH002", 500.0, 300.0, 0.15, 30.0, 2, "MATCH"),
        ],
        columns=list(REQUIRED_INPUT_COLUMNS),
    )


def test_find_returns_none_for_unknown_hash(orm_session: Session) -> None:
    """Hash sha256 non presente → None."""
    fake_hash = hashlib.sha256(b"never seen").hexdigest()
    result = find_session_by_hash(orm_session, listino_hash=fake_hash, tenant_id=1)
    assert result is None


def test_find_invalid_hash_length_raises(orm_session: Session) -> None:
    """Hash di lunghezza != 64 → ValueError."""
    with pytest.raises(ValueError, match="listino_hash"):
        find_session_by_hash(orm_session, listino_hash="abc", tenant_id=1)
    with pytest.raises(ValueError, match="listino_hash"):
        find_session_by_hash(orm_session, listino_hash="x" * 63, tenant_id=1)


def test_find_returns_summary_after_save(orm_session: Session) -> None:
    """Dopo save, find_by_hash ritorna SessionSummary corretto."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    sid = save_session_result(orm_session, session_input=inp, result=result)

    # Calcola hash come fa il repository.
    from talos.persistence.session_repository import _listino_hash  # noqa: PLC0415

    h = _listino_hash(inp.listino_raw)

    found = find_session_by_hash(orm_session, listino_hash=h, tenant_id=1)
    assert found is not None
    assert isinstance(found, SessionSummary)
    assert found.id == sid
    assert found.budget_eur == Decimal("2000.0")
    assert found.listino_hash == h


def test_unique_index_blocks_duplicate_save(orm_session: Session) -> None:
    """Stesso (tenant_id, listino_hash) → IntegrityError sul secondo save."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    save_session_result(orm_session, session_input=inp, result=result, tenant_id=1)
    orm_session.flush()  # ensure first save committed to current tx

    # Secondo save STESSO listino + STESSO tenant → IntegrityError UNIQUE
    with pytest.raises(IntegrityError, match="ux_sessions_tenant_hash"):
        save_session_result(orm_session, session_input=inp, result=result, tenant_id=1)


def test_unique_index_allows_different_tenants(orm_session: Session) -> None:
    """Tenant diversi con stesso listino_hash → ammessi entrambi."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    sid_a = save_session_result(orm_session, session_input=inp, result=result, tenant_id=1)
    sid_b = save_session_result(orm_session, session_input=inp, result=result, tenant_id=2)

    assert sid_a != sid_b


def test_find_filters_by_tenant_id(orm_session: Session) -> None:
    """Sessione di tenant=1 NON viene trovata cercando con tenant=2."""
    inp = SessionInput(listino_raw=_samsung_listino(), budget=2000.0)
    result = run_session(inp)
    save_session_result(orm_session, session_input=inp, result=result, tenant_id=1)

    from talos.persistence.session_repository import _listino_hash  # noqa: PLC0415

    h = _listino_hash(inp.listino_raw)

    found_t1 = find_session_by_hash(orm_session, listino_hash=h, tenant_id=1)
    assert found_t1 is not None

    found_t2 = find_session_by_hash(orm_session, listino_hash=h, tenant_id=2)
    assert found_t2 is None
