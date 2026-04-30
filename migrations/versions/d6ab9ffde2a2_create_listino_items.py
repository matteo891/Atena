"""create listino_items

Revision ID: d6ab9ffde2a2
Revises: d4a7e3cefbb1
Create Date: 2026-04-30

Crea la tabella `listino_items` come da Allegato A di ADR-0015.
Prima tabella con FK: `session_id → sessions.id ON DELETE CASCADE`.
Indice secondario `idx_listino_session` su `session_id` per le query
di scan-per-sessione.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d6ab9ffde2a2"
down_revision: str | None = "d4a7e3cefbb1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listino_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.BigInteger(),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asin", sa.CHAR(10), nullable=True),
        sa.Column("raw_title", sa.Text(), nullable=False),
        sa.Column("cost_eur", sa.Numeric(12, 2), nullable=False),
        sa.Column("qty_available", sa.Integer(), nullable=True),
        sa.Column("match_status", sa.Text(), nullable=True),
        sa.Column("match_reason", sa.Text(), nullable=True),
    )
    op.create_index(
        "idx_listino_session",
        "listino_items",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_listino_session", table_name="listino_items")
    op.drop_table("listino_items")
