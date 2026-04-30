"""create config_overrides with RLS

Revision ID: 027a145f76a8
Revises: d6ab9ffde2a2
Create Date: 2026-04-30

Crea la tabella `config_overrides` come da Allegato A di ADR-0015.
Prima tabella con Row-Level Security (RLS) attiva: policy `tenant_isolation`
filtra per `tenant_id = current_setting('talos.tenant_id', true)::bigint`.

Indice UNIQUE composito `idx_config_unique` su (tenant_id, scope, scope_key, key)
garantisce univocità della chiave di config a livello tenant.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "027a145f76a8"
down_revision: str | None = "d6ab9ffde2a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "config_overrides",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("scope_key", sa.Text(), nullable=True),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("value_numeric", sa.Numeric(12, 4), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.BigInteger(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_config_unique",
        "config_overrides",
        ["tenant_id", "scope", "scope_key", "key"],
        unique=True,
    )
    # Row-Level Security (Zero-Trust, ADR-0015) — Postgres-specifico
    op.execute("ALTER TABLE config_overrides ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON config_overrides
            USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)
        """,
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON config_overrides")
    op.execute("ALTER TABLE config_overrides DISABLE ROW LEVEL SECURITY")
    op.drop_index("idx_config_unique", table_name="config_overrides")
    op.drop_table("config_overrides")
