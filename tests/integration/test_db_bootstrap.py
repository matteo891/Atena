"""Integration test per `scripts/db_bootstrap.py` (CHG-2026-04-30-021).

Esegue lo script via subprocess e verifica lo stato del DB:
- Ruoli `talos_admin/talos_app/talos_audit` esistono con attributi corretti.
- `BYPASSRLS` su admin, NO BYPASSRLS su app/audit (lezione CHG-019).
- GRANT/REVOKE su `audit_log`: app=INSERT-only, audit=SELECT.
- FORCE RLS attivo sulle 3 tabelle con policy.
- Idempotenza: re-run senza errori.
- Missing env var → exit code != 0.
- Login funzionante con credenziali talos_app.

Cleanup module-scoped: droppa i 3 ruoli prima e dopo, ripristina NO FORCE RLS.
I ruoli sono globali al cluster Postgres, quindi cleanup esplicito è obbligatorio.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import psycopg
import pytest
from psycopg import sql

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = pytest.mark.integration

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "db_bootstrap.py"
_ROLES = ("talos_admin", "talos_app", "talos_audit")
_RLS_TABLES = ("config_overrides", "locked_in", "storico_ordini")


def _superuser_url() -> str:
    """URL psycopg per connessione superuser, derivato da TALOS_DB_URL."""
    url = os.environ["TALOS_DB_URL"]
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _drop_all_roles_and_force_rls() -> None:
    """Cleanup: droppa i 3 ruoli e disabilita FORCE RLS. Idempotente."""
    with psycopg.connect(_superuser_url(), autocommit=True) as conn, conn.cursor() as cur:
        for role in _ROLES:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            if cur.fetchone():
                cur.execute(
                    sql.SQL("REASSIGN OWNED BY {r} TO postgres").format(r=sql.Identifier(role))
                )
                cur.execute(sql.SQL("DROP OWNED BY {r}").format(r=sql.Identifier(role)))
                cur.execute(sql.SQL("DROP ROLE {r}").format(r=sql.Identifier(role)))
        for table in _RLS_TABLES:
            cur.execute(
                sql.SQL("ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY").format(
                    t=sql.Identifier(table)
                )
            )


@pytest.fixture(scope="module", autouse=True)
def _bootstrap_clean_slate() -> Iterator[None]:
    """Pulisce i ruoli prima e dopo i test del modulo."""
    _drop_all_roles_and_force_rls()
    try:
        yield
    finally:
        _drop_all_roles_and_force_rls()


def _run_bootstrap(env_extra: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Lancia lo script `db_bootstrap.py` con env var aggiuntive."""
    env = os.environ.copy()
    env["TALOS_DB_URL_SUPERUSER"] = _superuser_url()
    env.update(env_extra)
    return subprocess.run(  # noqa: S603 — args interi noti, no shell
        [sys.executable, str(_SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _passwords() -> dict[str, str]:
    return {
        "TALOS_ADMIN_PASSWORD": "admin_pwd_test_value",
        "TALOS_APP_PASSWORD": "app_pwd_test_value",
        "TALOS_AUDIT_PASSWORD": "audit_pwd_test_value",
    }


def test_bootstrap_completes_successfully() -> None:
    result = _run_bootstrap(_passwords())
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_roles_exist_with_correct_attributes() -> None:
    _run_bootstrap(_passwords())
    with psycopg.connect(_superuser_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT rolname, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole, rolcanlogin "
            "FROM pg_roles WHERE rolname = ANY(%s) ORDER BY rolname",
            (list(_ROLES),),
        )
        rows = {r[0]: r[1:] for r in cur.fetchall()}

    # talos_admin: NOSUPERUSER, BYPASSRLS, CREATEDB, CREATEROLE, LOGIN
    assert rows["talos_admin"] == (False, True, True, True, True)
    # talos_app: NOSUPERUSER, NOBYPASSRLS, NOCREATEDB, NOCREATEROLE, LOGIN
    assert rows["talos_app"] == (False, False, False, False, True)
    # talos_audit: NOSUPERUSER, NOBYPASSRLS, NOCREATEDB, NOCREATEROLE, LOGIN
    assert rows["talos_audit"] == (False, False, False, False, True)


def test_force_rls_active_on_three_tables() -> None:
    _run_bootstrap(_passwords())
    with psycopg.connect(_superuser_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT relname, relforcerowsecurity FROM pg_class "
            "WHERE relname = ANY(%s) ORDER BY relname",
            (list(_RLS_TABLES),),
        )
        rows = dict(cur.fetchall())
    assert all(rows[t] is True for t in _RLS_TABLES), rows


def test_audit_log_grants_app_insert_only() -> None:
    _run_bootstrap(_passwords())
    with psycopg.connect(_superuser_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT privilege_type FROM information_schema.role_table_grants "
            "WHERE table_name = 'audit_log' AND grantee = 'talos_app' ORDER BY privilege_type"
        )
        privs = [r[0] for r in cur.fetchall()]
    assert privs == ["INSERT"]


def test_audit_log_grants_audit_select_only() -> None:
    _run_bootstrap(_passwords())
    with psycopg.connect(_superuser_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT privilege_type FROM information_schema.role_table_grants "
            "WHERE table_name = 'audit_log' AND grantee = 'talos_audit' ORDER BY privilege_type"
        )
        privs = [r[0] for r in cur.fetchall()]
    assert privs == ["SELECT"]


def test_data_table_grants_app_full_crud() -> None:
    _run_bootstrap(_passwords())
    with psycopg.connect(_superuser_url()) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT privilege_type FROM information_schema.role_table_grants "
            "WHERE table_name = 'config_overrides' AND grantee = 'talos_app' "
            "ORDER BY privilege_type"
        )
        privs = sorted(r[0] for r in cur.fetchall())
    assert privs == ["DELETE", "INSERT", "SELECT", "UPDATE"]


def test_idempotent_rerun() -> None:
    _run_bootstrap(_passwords())
    second = _run_bootstrap(_passwords())
    assert second.returncode == 0, second.stderr


def test_missing_password_fails_with_exit_code() -> None:
    pwds = _passwords()
    del pwds["TALOS_APP_PASSWORD"]
    result = _run_bootstrap(pwds)
    assert result.returncode != 0
    assert "TALOS_APP_PASSWORD" in result.stderr


def test_talos_app_can_login() -> None:
    _run_bootstrap(_passwords())
    # Costruisco URL talos_app sostituendo user/password nell'URL superuser.
    base = _superuser_url()
    # Sostituzione semplice: postgresql://USER:PASS@HOST:PORT/DB
    # (dipende dal formato del container test, che è noto.)
    after_scheme = base.split("://", 1)[1]
    _, host_part = after_scheme.split("@", 1)
    app_url = f"postgresql://talos_app:app_pwd_test_value@{host_part}"

    with psycopg.connect(app_url) as conn, conn.cursor() as cur:
        cur.execute("SELECT current_user")
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "talos_app"
