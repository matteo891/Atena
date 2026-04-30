"""Test runtime della policy RLS `tenant_isolation` su `config_overrides`.

Postgres bypassa RLS in due casi: (1) per il **table owner** salvo `FORCE
ROW LEVEL SECURITY`, (2) per ruoli con attributo **`BYPASSRLS`** (incluso
ogni superuser). Per testare la policy effettivamente devo:

1. `ALTER TABLE config_overrides FORCE ROW LEVEL SECURITY` — copre l'owner.
2. `CREATE ROLE` non-superuser senza `BYPASSRLS` + `GRANT` minimo + `SET LOCAL
   ROLE` — copre il bypass del superuser.

Tutto in transazione, rollback finale ripristina catalog (FORCE off, role drop).

La policy esistente è `USING (tenant_id = current_setting('talos.tenant_id',
true)::bigint)` — solo USING, niente WITH CHECK. Quindi INSERT è libero anche
con `tenant_id` diverso da quello di sessione; SELECT/UPDATE/DELETE filtrano.

Riferimenti:
- CHG-2026-04-30-012 (`config_overrides` + RLS — policy installata)
- CHG-2026-04-30-019 (questo test)
- ADR-0015 (RLS Zero-Trust)
"""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

pytestmark = pytest.mark.integration

_RLS_SUBJECT_ROLE = "talos_rls_test_subject"


def _seed_two_tenants(conn: Connection) -> None:
    """Inserisce 2 righe (tenant 1 + tenant 2) come superuser, RLS bypassata."""
    conn.execute(
        text(
            "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
            "VALUES ('global', 'veto_roi_pct', 8, 1)"
        )
    )
    conn.execute(
        text(
            "INSERT INTO config_overrides (scope, key, value_numeric, tenant_id) "
            "VALUES ('global', 'veto_roi_pct', 10, 2)"
        )
    )


def _enter_rls_subject(conn: Connection) -> None:
    """Attiva FORCE RLS, crea un ruolo non-superuser, switcha la sessione.

    Postgres bypassa RLS per superuser e per il table owner. Per osservare
    la policy `tenant_isolation` la sessione deve eseguire le query da un
    ruolo NOSUPERUSER NOBYPASSRLS (default di CREATE ROLE) **e** la tabella
    deve avere FORCE attivo.

    Il rollback finale della fixture ripristina catalog: FORCE rimosso, role
    droppato. CREATE ROLE è transactional in Postgres 16.
    """
    conn.execute(text("ALTER TABLE config_overrides FORCE ROW LEVEL SECURITY"))
    conn.execute(text(f"CREATE ROLE {_RLS_SUBJECT_ROLE}"))
    conn.execute(text(f"GRANT SELECT, UPDATE, DELETE ON config_overrides TO {_RLS_SUBJECT_ROLE}"))
    # Trigger AFTER su UPDATE/DELETE inserisce in audit_log: serve INSERT
    # (e accesso alla sequence BIGSERIAL).
    conn.execute(text(f"GRANT INSERT ON audit_log TO {_RLS_SUBJECT_ROLE}"))
    conn.execute(text(f"GRANT USAGE ON SEQUENCE audit_log_id_seq TO {_RLS_SUBJECT_ROLE}"))
    conn.execute(text(f"SET LOCAL ROLE {_RLS_SUBJECT_ROLE}"))


def test_tenant_1_sees_only_tenant_1_rows(pg_conn: Connection) -> None:
    _seed_two_tenants(pg_conn)
    _enter_rls_subject(pg_conn)
    pg_conn.execute(text("SET LOCAL talos.tenant_id = '1'"))

    rows = pg_conn.execute(text("SELECT tenant_id FROM config_overrides")).all()

    assert len(rows) == 1
    assert rows[0][0] == 1


def test_tenant_2_sees_only_tenant_2_rows(pg_conn: Connection) -> None:
    _seed_two_tenants(pg_conn)
    _enter_rls_subject(pg_conn)
    pg_conn.execute(text("SET LOCAL talos.tenant_id = '2'"))

    rows = pg_conn.execute(text("SELECT tenant_id FROM config_overrides")).all()

    assert len(rows) == 1
    assert rows[0][0] == 2


def test_unknown_tenant_sees_zero_rows(pg_conn: Connection) -> None:
    _seed_two_tenants(pg_conn)
    _enter_rls_subject(pg_conn)
    pg_conn.execute(text("SET LOCAL talos.tenant_id = '999'"))

    rows = pg_conn.execute(text("SELECT tenant_id FROM config_overrides")).all()

    assert rows == []


def test_force_rls_applies_to_update_and_delete(pg_conn: Connection) -> None:
    """UPDATE/DELETE filtrano per tenant come SELECT."""
    _seed_two_tenants(pg_conn)
    _enter_rls_subject(pg_conn)
    pg_conn.execute(text("SET LOCAL talos.tenant_id = '1'"))

    upd = pg_conn.execute(text("UPDATE config_overrides SET value_numeric = 99"))
    assert upd.rowcount == 1

    pg_conn.execute(text("SET LOCAL talos.tenant_id = '2'"))
    rows_t2 = pg_conn.execute(text("SELECT value_numeric FROM config_overrides")).all()
    assert rows_t2[0][0] == 10

    deld = pg_conn.execute(text("DELETE FROM config_overrides"))
    assert deld.rowcount == 1
