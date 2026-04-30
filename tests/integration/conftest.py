"""Fixture per test integration su Postgres reale (CHG-2026-04-30-019).

Pattern:
- `pg_engine` (session): legge `TALOS_DB_URL`, skip module-level se assente.
- `pg_conn` (function): connessione + transazione + rollback finale, con
  `SET LOCAL talos.tenant_id = '1'` di default. Garantisce isolamento per-test
  e zero side-effect sul DB (nessuna riga persistita tra test).

ADR-0019 raccomanda `pytest-postgresql`; per la fase corrente (container
ephemeral già lanciato manualmente) il pattern env-var → engine è sufficiente
e più semplice. Adozione di `pytest-postgresql` rimandata a CHG futuro.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, text

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Connection, Engine


@pytest.fixture(scope="session")
def pg_engine() -> Iterator[Engine]:
    """Engine Postgres da env var `TALOS_DB_URL`. Skip se assente."""
    db_url = os.getenv("TALOS_DB_URL")
    if not db_url:
        pytest.skip(
            "TALOS_DB_URL non settato — test integration skipped. "
            "Lancia: docker run -d --name talos-pg-test -e POSTGRES_PASSWORD=test "
            "-p 55432:5432 --tmpfs /var/lib/postgresql/data:rw postgres:16-alpine && "
            "export TALOS_DB_URL='postgresql+psycopg://postgres:test@localhost:55432/postgres'",
            allow_module_level=True,
        )
    engine = create_engine(db_url, pool_pre_ping=True, future=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def pg_conn(pg_engine: Engine) -> Iterator[Connection]:
    """Connessione transazionale con rollback finale.

    `SET LOCAL talos.tenant_id = '1'` come default. I test possono cambiarlo
    via `pg_conn.execute(text("SET LOCAL talos.tenant_id = '<n>'"))`.
    """
    with pg_engine.connect() as conn:
        trans = conn.begin()
        try:
            conn.execute(text("SET LOCAL talos.tenant_id = '1'"))
            yield conn
        finally:
            trans.rollback()
