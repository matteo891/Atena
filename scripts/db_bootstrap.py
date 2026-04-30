#!/usr/bin/env python3
"""DB bootstrap idempotente: ruoli + GRANT/REVOKE + FORCE RLS (CHG-2026-04-30-021).

Da CHG-2026-04-30-031 le 4 env var DB fluiscono via `TalosSettings`
(`db_url_superuser`, `admin_password`, `app_password`, `audit_password`).

ADR-0015 sezione "Ruoli" — Zero-Trust matrix:
- talos_admin  : LOGIN, NOSUPERUSER, BYPASSRLS, CREATEDB, CREATEROLE  (DBA + Alembic)
- talos_app    : LOGIN, NOSUPERUSER, NOBYPASSRLS                       (pool applicativo)
- talos_audit  : LOGIN, NOSUPERUSER, NOBYPASSRLS                       (read-only audit)

Lezione CHG-2026-04-30-019: `BYPASSRLS` (default per superuser) supersede
anche `FORCE ROW LEVEL SECURITY`. `talos_app` deve essere NOBYPASSRLS
perché l'enforcement RLS sia effettivo nel pool applicativo.

Usage::

    export TALOS_DB_URL_SUPERUSER='postgresql://postgres:test@localhost:55432/postgres'
    export TALOS_ADMIN_PASSWORD='****'
    export TALOS_APP_PASSWORD='****'
    export TALOS_AUDIT_PASSWORD='****'
    uv run python scripts/db_bootstrap.py

Idempotente: rieseguibile senza errori.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final

import psycopg
from psycopg import sql

from talos.config import get_settings

if TYPE_CHECKING:
    from talos.config import TalosSettings

_DATA_TABLES: Final = (
    "sessions",
    "asin_master",
    "listino_items",
    "vgp_results",
    "cart_items",
    "panchina_items",
    "storico_ordini",
    "locked_in",
    "config_overrides",
)

_RLS_TABLES: Final = ("config_overrides", "locked_in", "storico_ordini")


def _resolve_superuser_url(settings: TalosSettings) -> str:
    """URL di connessione superuser. Strippa il prefisso `+psycopg` (forma SQLAlchemy).

    Priorità: `db_url_superuser` (TALOS_DB_URL_SUPERUSER) → `db_url` (TALOS_DB_URL).
    """
    url = settings.db_url_superuser or settings.db_url
    if not url:
        msg = (
            "TALOS_DB_URL_SUPERUSER (o TALOS_DB_URL) non settato. "
            "Esempio: postgresql://postgres:<pwd>@localhost:5432/talos"
        )
        raise RuntimeError(msg)
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def _check_required_settings(settings: TalosSettings) -> None:
    """Verifica che le 3 password ruoli siano presenti via env var TALOS_*."""
    missing: list[str] = []
    if not settings.admin_password:
        missing.append("TALOS_ADMIN_PASSWORD")
    if not settings.app_password:
        missing.append("TALOS_APP_PASSWORD")
    if not settings.audit_password:
        missing.append("TALOS_AUDIT_PASSWORD")
    if missing:
        msg = "Env var richieste assenti: " + ", ".join(missing)
        raise RuntimeError(msg)


def _ensure_role(
    cur: psycopg.Cursor,
    name: str,
    password: str,
    *,
    attrs_sql: sql.Composable,
) -> None:
    """Crea il ruolo se assente; ALTER per riallineare password e attributi."""
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (name,))
    exists = cur.fetchone() is not None
    if not exists:
        cur.execute(
            sql.SQL("CREATE ROLE {role} WITH LOGIN {attrs} PASSWORD {pwd}").format(
                role=sql.Identifier(name),
                attrs=attrs_sql,
                pwd=sql.Literal(password),
            )
        )
    cur.execute(
        sql.SQL("ALTER ROLE {role} WITH LOGIN {attrs} PASSWORD {pwd}").format(
            role=sql.Identifier(name),
            attrs=attrs_sql,
            pwd=sql.Literal(password),
        )
    )


def _grant_app_privileges(cur: psycopg.Cursor, db_name: str) -> None:
    """talos_app: CRUD su tabelle dati, INSERT-only su audit_log, sequenze."""
    cur.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {db} TO talos_app, talos_audit").format(
            db=sql.Identifier(db_name)
        )
    )
    cur.execute("GRANT USAGE ON SCHEMA public TO talos_app, talos_audit")

    data_tables = sql.SQL(", ").join(sql.Identifier(t) for t in _DATA_TABLES)
    cur.execute(
        sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON {tbls} TO talos_app").format(
            tbls=data_tables
        )
    )
    cur.execute("GRANT INSERT ON audit_log TO talos_app")
    cur.execute("REVOKE UPDATE, DELETE ON audit_log FROM talos_app")
    cur.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO talos_app")


def _grant_audit_privileges(cur: psycopg.Cursor) -> None:
    """talos_audit: SELECT-only ovunque (incluso audit_log)."""
    cur.execute("GRANT SELECT ON ALL TABLES IN SCHEMA public TO talos_audit")


def _grant_admin_privileges(cur: psycopg.Cursor) -> None:
    """talos_admin: privilegi gestionali (no superuser)."""
    cur.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO talos_admin")
    cur.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO talos_admin")


def _force_rls(cur: psycopg.Cursor) -> None:
    """ALTER TABLE ... FORCE ROW LEVEL SECURITY su tabelle con policy.

    Idempotente: rieseguito non fa nulla. Necessario perché l'ownership delle
    tabelle è del superuser (Postgres bypassa RLS per l'owner senza FORCE).
    """
    for table in _RLS_TABLES:
        cur.execute(
            sql.SQL("ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY").format(tbl=sql.Identifier(table))
        )


def bootstrap() -> None:
    """Entry point: idempotente, esce con 0 al successo, raise on failure."""
    settings = get_settings()
    _check_required_settings(settings)
    url = _resolve_superuser_url(settings)
    admin_pwd = settings.admin_password
    app_pwd = settings.app_password
    audit_pwd = settings.audit_password
    assert admin_pwd is not None  # noqa: S101 — narrowing post _check_required_settings
    assert app_pwd is not None  # noqa: S101 — narrowing post _check_required_settings
    assert audit_pwd is not None  # noqa: S101 — narrowing post _check_required_settings

    admin_attrs = sql.SQL("NOSUPERUSER BYPASSRLS CREATEDB CREATEROLE")
    app_attrs = sql.SQL("NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE")
    audit_attrs = sql.SQL("NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE")

    with psycopg.connect(url, autocommit=False) as conn, conn.cursor() as cur:
        _ensure_role(cur, "talos_admin", admin_pwd, attrs_sql=admin_attrs)
        _ensure_role(cur, "talos_app", app_pwd, attrs_sql=app_attrs)
        _ensure_role(cur, "talos_audit", audit_pwd, attrs_sql=audit_attrs)

        cur.execute("SELECT current_database()")
        db_row = cur.fetchone()
        assert db_row is not None  # noqa: S101 — invariante Postgres
        db_name = db_row[0]

        _grant_app_privileges(cur, db_name)
        _grant_audit_privileges(cur)
        _grant_admin_privileges(cur)
        _force_rls(cur)
        conn.commit()


def main() -> int:
    try:
        bootstrap()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)  # noqa: T201 — CLI output
        return 2
    except psycopg.Error as exc:
        print(f"ERROR (psycopg): {exc}", file=sys.stderr)  # noqa: T201 — CLI output
        return 3
    print("OK: bootstrap completato (idempotente).")  # noqa: T201 — CLI output
    return 0


if __name__ == "__main__":
    sys.exit(main())
