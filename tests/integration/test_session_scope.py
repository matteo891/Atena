"""Integration test runtime per `session_scope` + `with_tenant` (CHG-020).

Verifica end-to-end:
1. `session_scope` committa on success e rollbacka on exception.
2. `with_tenant` imposta `current_setting('talos.tenant_id')` come atteso.
3. `with_tenant` realizza l'isolamento RLS effettivo (riusa il pattern di
   CHG-019: FORCE + ruolo non-superuser).

Riferimenti:
- CHG-2026-04-30-019 (`tests/integration/` infrastruttura)
- CHG-2026-04-30-020 (questo test, primitive `engine`/`session`)
- ADR-0015 (Zero-Trust + RLS)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import text

from talos.persistence import (
    create_app_engine,
    make_session_factory,
    session_scope,
    with_tenant,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy import Engine
    from sqlalchemy.orm import Session, sessionmaker

pytestmark = pytest.mark.integration

_RLS_SUBJECT_ROLE = "talos_session_rls_subject"


@pytest.fixture
def app_engine() -> Iterator[Engine]:
    """Engine creato via la factory pubblica `create_app_engine` (no fallback)."""
    db_url = os.getenv("TALOS_DB_URL")
    assert db_url, "fixture skip dovrebbe essersi attivata in conftest"
    engine = create_app_engine(db_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def session_factory(app_engine: Engine) -> sessionmaker[Session]:
    return make_session_factory(app_engine)


def _cleanup_overrides(engine: Engine) -> None:
    """DELETE finale per i test che committano sul DB."""
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM config_overrides WHERE scope = 'session_test'"))


def test_session_scope_commits_on_success(
    app_engine: Engine,
    session_factory: sessionmaker[Session],
) -> None:
    try:
        with session_scope(session_factory) as session:
            session.execute(
                text(
                    "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
                    "VALUES ('session_test', 'k_commit', 1, 1)"
                )
            )

        # Nuova connessione: verifica persistenza.
        with app_engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM config_overrides "
                    "WHERE scope = 'session_test' AND key = 'k_commit'"
                )
            ).scalar()
        assert count == 1
    finally:
        _cleanup_overrides(app_engine)


def _insert_then_raise(session_factory: sessionmaker[Session]) -> None:
    """Inserisce una riga e solleva: il context manager deve rollbackare."""
    with session_scope(session_factory) as session:
        session.execute(
            text(
                "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
                "VALUES ('session_test', 'k_rollback', 2, 1)"
            )
        )
        msg = "forced rollback"
        raise RuntimeError(msg)


def test_session_scope_rolls_back_on_exception(
    app_engine: Engine,
    session_factory: sessionmaker[Session],
) -> None:
    try:
        with pytest.raises(RuntimeError, match="forced rollback"):
            _insert_then_raise(session_factory)

        # La riga NON deve essere persistita.
        with app_engine.connect() as conn:
            count = conn.execute(
                text(
                    "SELECT COUNT(*) FROM config_overrides "
                    "WHERE scope = 'session_test' AND key = 'k_rollback'"
                )
            ).scalar()
        assert count == 0
    finally:
        _cleanup_overrides(app_engine)


def test_with_tenant_sets_session_var(
    session_factory: sessionmaker[Session],
) -> None:
    """`with_tenant` deve far ritornare il valore atteso a `current_setting`."""
    session = session_factory()
    try:
        with with_tenant(session, 42) as s:
            value = s.execute(text("SELECT current_setting('talos.tenant_id', true)")).scalar()
        assert value == "42"
        # La transazione interna è stata aperta da `with_tenant`: rollback per
        # evitare di lasciare locks acquisiti.
        session.rollback()
    finally:
        session.close()


def test_with_tenant_isolates_rls_via_role_switch(
    session_factory: sessionmaker[Session],
) -> None:
    """End-to-end: `with_tenant(role=...)` realizza l'isolamento RLS effettivo.

    Crea un ruolo non-superuser, attiva FORCE RLS, semina 2 righe (tenant 1+2),
    poi entra con `with_tenant(s, 1, role=ROLE)` e verifica che SELECT veda
    solo tenant 1. Tutto in transazione, rollback finale ripristina catalog.
    """
    session = session_factory()
    try:
        # Setup catalog (FORCE + role + GRANT) come superuser.
        session.begin()
        session.execute(text("ALTER TABLE config_overrides FORCE ROW LEVEL SECURITY"))
        session.execute(text(f"CREATE ROLE {_RLS_SUBJECT_ROLE}"))
        session.execute(
            text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON config_overrides TO {_RLS_SUBJECT_ROLE}")
        )
        session.execute(text(f"GRANT INSERT ON audit_log TO {_RLS_SUBJECT_ROLE}"))
        session.execute(text(f"GRANT USAGE ON SEQUENCE audit_log_id_seq TO {_RLS_SUBJECT_ROLE}"))

        # Seed cross-tenant come superuser.
        session.execute(
            text(
                "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
                "VALUES ('rls_check', 'k', 1, 1)"
            )
        )
        session.execute(
            text(
                "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
                "VALUES ('rls_check', 'k', 2, 2)"
            )
        )

        # Entra come tenant 1 sotto ruolo non-superuser.
        with with_tenant(session, 1, role=_RLS_SUBJECT_ROLE) as s:
            rows = s.execute(
                text("SELECT tenant_id FROM config_overrides WHERE scope = 'rls_check'")
            ).all()
        assert len(rows) == 1
        assert rows[0][0] == 1

        session.rollback()  # ripristina catalog (FORCE off, role drop, righe)
    finally:
        session.close()
