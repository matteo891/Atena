"""create storico_ordini with RLS

Revision ID: a074ee67895c
Revises: 618105641c27
Create Date: 2026-04-30

Crea la tabella `storico_ordini` come da Allegato A di ADR-0015.
Registro permanente degli ordini (R-03 ORDER-DRIVEN MEMORY): le FK
verso `sessions` e `cart_items` **non** hanno ON DELETE CASCADE
(aderenza letterale all'Allegato A): cancellare una sessione o un
cart_item referenziato da uno storico_ordini fallisce a livello DB
(default RESTRICT) — comportamento desiderato per un registro
permanente.

RLS attiva: policy `tenant_isolation` — isolamento per tenant_id.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a074ee67895c"
down_revision: str | None = "618105641c27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "storico_ordini",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        # Aderenza letterale Allegato A: NO ON DELETE CASCADE (registro permanente).
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("sessions.id"),
            nullable=False,
        ),
        sa.Column(
            "cart_item_id",
            sa.BigInteger(),
            sa.ForeignKey("cart_items.id"),
            nullable=False,
        ),
        sa.Column("asin", sa.CHAR(10), nullable=False),
        sa.Column("qty", sa.Integer(), nullable=False),
        sa.Column("unit_cost_eur", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "ordered_at",
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
    # Row-Level Security (Zero-Trust, ADR-0015) — Postgres-specifico
    op.execute("ALTER TABLE storico_ordini ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON storico_ordini
            USING (tenant_id = current_setting('talos.tenant_id', true)::bigint)
        """,
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON storico_ordini")
    op.execute("ALTER TABLE storico_ordini DISABLE ROW LEVEL SECURITY")
    op.drop_table("storico_ordini")
