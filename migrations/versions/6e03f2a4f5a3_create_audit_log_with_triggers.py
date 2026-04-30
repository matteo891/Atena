"""create audit_log with triggers

Revision ID: 6e03f2a4f5a3
Revises: e7a92c0260fa
Create Date: 2026-04-30

Crea la tabella `audit_log` come da Allegato A di ADR-0015.
Append-only: ogni INSERT/UPDATE/DELETE su `storico_ordini`, `locked_in`,
`config_overrides` produce automaticamente una riga in `audit_log` via
trigger AFTER. La funzione `record_audit_log()` cattura `session_user`
come `actor`, mappa `TG_OP` su 'I'/'U'/'D' e serializza OLD/NEW in JSONB.

NOTE — Out-of-scope di questa migration:
- I ruoli `talos_admin`/`talos_app`/`talos_audit` non sono creati qui.
- I `GRANT INSERT ON audit_log` / `REVOKE UPDATE,DELETE ON audit_log`
  che rendono effettiva la disciplina append-only NON sono in questa
  migration: richiedono ruoli pre-esistenti. Sono gestiti da setup
  bootstrap esterno (futuro CHG su `scripts/db-bootstrap.sh`).

L'append-only si chiude solo in produzione con il bootstrap dei ruoli.
In sviluppo (utente superuser/admin) la tabella è scrivibile da
chiunque — protezione di default Postgres.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6e03f2a4f5a3"
down_revision: str | None = "e7a92c0260fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_AUDITED_TABLES: tuple[str, ...] = ("storico_ordini", "locked_in", "config_overrides")

_FUNCTION_BODY = """
CREATE OR REPLACE FUNCTION record_audit_log()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (actor, table_name, op, row_id, before_data, after_data)
    VALUES (
        session_user,
        TG_TABLE_NAME,
        CASE TG_OP
            WHEN 'INSERT' THEN 'I'
            WHEN 'UPDATE' THEN 'U'
            WHEN 'DELETE' THEN 'D'
        END,
        COALESCE(NEW.id, OLD.id),
        CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE row_to_json(OLD)::jsonb END,
        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE row_to_json(NEW)::jsonb END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("op", sa.CHAR(1), nullable=False),
        sa.Column("row_id", sa.BigInteger(), nullable=True),
        sa.Column("before_data", postgresql.JSONB, nullable=True),
        sa.Column("after_data", postgresql.JSONB, nullable=True),
        sa.Column(
            "at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Funzione PL/pgSQL che alimenta audit_log dai trigger
    op.execute(_FUNCTION_BODY)
    # Trigger AFTER su tabelle critiche (Allegato A: storico_ordini,
    # locked_in, config_overrides). Nome trigger: trg_audit_<table>.
    for table_name in _AUDITED_TABLES:
        op.execute(
            f"""
            CREATE TRIGGER trg_audit_{table_name}
            AFTER INSERT OR UPDATE OR DELETE ON {table_name}
            FOR EACH ROW EXECUTE FUNCTION record_audit_log()
            """,
        )


def downgrade() -> None:
    for table_name in _AUDITED_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_audit_{table_name} ON {table_name}")
    op.execute("DROP FUNCTION IF EXISTS record_audit_log()")
    op.drop_table("audit_log")
