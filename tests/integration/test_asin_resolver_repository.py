"""Test integration `asin_resolver_repository` (CHG-2026-05-01-019).

Richiede `TALOS_DB_URL` (Postgres reale). Skip module-level senza.
Pattern coerente con `test_session_repository.py` / `test_config_repository.py`:
fixture transazionale + rollback, no commit cross-test.
"""

from __future__ import annotations

import os
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from talos.persistence.asin_resolver_repository import (
    compute_description_hash,
    find_resolution_by_hash,
    upsert_resolution,
)
from talos.persistence.engine import create_app_engine
from talos.persistence.session import make_session_factory

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.orm import Session

if not os.environ.get("TALOS_DB_URL"):
    pytest.skip(
        "TALOS_DB_URL non impostata; skip integration",
        allow_module_level=True,
    )

pytestmark = pytest.mark.integration


@pytest.fixture
def db() -> Iterator[Session]:
    """Sessione transazionale con rollback finale (no commit cross-test)."""
    engine = create_app_engine()
    factory = make_session_factory(engine)
    session = factory()
    try:
        yield session
        session.rollback()
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# `compute_description_hash`
# ---------------------------------------------------------------------------


def test_hash_is_deterministic_64_char_hex() -> None:
    """SHA-256 hex sempre 64 char esa, deterministico."""
    h1 = compute_description_hash("Galaxy S24")
    h2 = compute_description_hash("Galaxy S24")
    assert h1 == h2
    assert len(h1) == 64
    assert all(c in "0123456789abcdef" for c in h1)


def test_hash_normalizes_whitespace_and_case() -> None:
    """Trim + lowercase: spazi/case diverse -> stesso hash."""
    h_canon = compute_description_hash("galaxy s24")
    assert compute_description_hash("Galaxy S24") == h_canon
    assert compute_description_hash("  galaxy s24  ") == h_canon
    assert compute_description_hash("GALAXY S24") == h_canon


def test_hash_different_descriptions_different_hashes() -> None:
    """Descrizioni diverse -> hash diversi (cache miss attesa)."""
    h1 = compute_description_hash("Galaxy S24")
    h2 = compute_description_hash("Galaxy S24 256GB")
    h3 = compute_description_hash("Galaxy A55")
    assert h1 != h2 != h3


def test_hash_empty_raises() -> None:
    """Descrizione vuota / whitespace-only -> ValueError esplicito."""
    with pytest.raises(ValueError, match="description vuota"):
        compute_description_hash("")
    with pytest.raises(ValueError, match="description vuota"):
        compute_description_hash("   ")


# ---------------------------------------------------------------------------
# `find_resolution_by_hash`
# ---------------------------------------------------------------------------


def test_find_returns_none_when_no_row(db: Session) -> None:
    """Lookup miss -> None (cache miss)."""
    result = find_resolution_by_hash(
        db,
        tenant_id=1,
        description_hash="0" * 64,
    )
    assert result is None


def test_find_returns_row_after_upsert(db: Session) -> None:
    """Round-trip insert + lookup."""
    h = compute_description_hash("Samsung Galaxy S24 256GB")
    upsert_resolution(
        db,
        tenant_id=1,
        description_hash=h,
        asin="B0CSTC2RDW",
        confidence_pct=Decimal("95.50"),
    )
    db.flush()
    found = find_resolution_by_hash(db, tenant_id=1, description_hash=h)
    assert found is not None
    assert found.asin.strip() == "B0CSTC2RDW"
    assert found.confidence_pct == Decimal("95.50")
    assert found.tenant_id == 1


def test_find_filters_by_tenant(db: Session) -> None:
    """Tenant-scoped: tenant 1 non vede entry tenant 2."""
    h = compute_description_hash("X23 specifico tenant")
    upsert_resolution(
        db,
        tenant_id=2,
        description_hash=h,
        asin="B0TENANT02",
        confidence_pct=Decimal("80.00"),
    )
    db.flush()
    assert find_resolution_by_hash(db, tenant_id=1, description_hash=h) is None
    found_t2 = find_resolution_by_hash(db, tenant_id=2, description_hash=h)
    assert found_t2 is not None
    assert found_t2.asin.strip() == "B0TENANT02"


# ---------------------------------------------------------------------------
# `upsert_resolution` — UPSERT idempotency
# ---------------------------------------------------------------------------


def test_upsert_inserts_first_time_returns_id(db: Session) -> None:
    """Prima chiamata = INSERT, ritorna id BIGSERIAL > 0."""
    h = compute_description_hash("First insert test")
    row_id = upsert_resolution(
        db,
        tenant_id=1,
        description_hash=h,
        asin="B0FIRST001",
        confidence_pct=Decimal("70.00"),
    )
    assert row_id > 0


def test_upsert_overwrites_on_conflict(db: Session) -> None:
    """Seconda chiamata stesso (tenant, hash) = UPDATE, refresh asin/confidence."""
    h = compute_description_hash("Stesso hash, due asin diversi")

    id1 = upsert_resolution(
        db,
        tenant_id=1,
        description_hash=h,
        asin="B0FIRST001",
        confidence_pct=Decimal("70.00"),
    )
    id2 = upsert_resolution(
        db,
        tenant_id=1,
        description_hash=h,
        asin="B0SECOND01",
        confidence_pct=Decimal("85.00"),
    )
    db.flush()

    # Stesso id (UPDATE non INSERT)
    assert id1 == id2
    found = find_resolution_by_hash(db, tenant_id=1, description_hash=h)
    assert found is not None
    assert found.asin.strip() == "B0SECOND01"
    assert found.confidence_pct == Decimal("85.00")


def test_upsert_different_tenants_independent_rows(db: Session) -> None:
    """UNIQUE `(tenant_id, hash)`: stesso hash su tenant diversi = 2 righe."""
    h = compute_description_hash("Galaxy S24 cross-tenant")
    id1 = upsert_resolution(
        db,
        tenant_id=1,
        description_hash=h,
        asin="B0TENANT01",
        confidence_pct=Decimal("90.00"),
    )
    id2 = upsert_resolution(
        db,
        tenant_id=2,
        description_hash=h,
        asin="B0TENANT02",
        confidence_pct=Decimal("80.00"),
    )
    db.flush()
    assert id1 != id2
    found_t1 = find_resolution_by_hash(db, tenant_id=1, description_hash=h)
    found_t2 = find_resolution_by_hash(db, tenant_id=2, description_hash=h)
    assert found_t1 is not None
    assert found_t2 is not None
    assert found_t1.asin.strip() == "B0TENANT01"
    assert found_t2.asin.strip() == "B0TENANT02"
