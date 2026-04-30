"""create locked_in with RLS

Revision ID: e7a92c0260fa
Revises: a074ee67895c
Create Date: 2026-04-30

Crea la tabella `locked_in` come da Allegato A di ADR-0015.
R-04 Manual Override: ASIN che il CFO ha forzato a entrare nel
carrello con Priorità ∞ (entrano per primi, riservando il loro
budget al di fuori del ranking VGP).

Standalone (no FK). RLS attiva con policy `tenant_isolation`.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a92c0260fa"
down_revision: str | None = "a074ee67895c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "locked_in",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("asin", sa.CHAR(10), nullable=False),
        sa.Column("qty_min", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
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
    # Row-Level Security (Zero-Trust, ADR-0015)
    op.execute("ALTER TABLE locked_in ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON locked_in
            USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)
        """,
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON locked_in")
    op.execute("ALTER TABLE locked_in DISABLE ROW LEVEL SECURITY")
    op.drop_table("locked_in")
